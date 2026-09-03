import pytest

from rate_limiter import TokenRateLimiter


@pytest.fixture
def limiter(tmp_path):
    return TokenRateLimiter(
        db_path=str(
            tmp_path / "test_rate_limits.db"
        )
    )


def test_tokens_allowed_below_limit(limiter):
    allowed, remaining = limiter.consume(
        "tenant-a",
        10_000,
        now=1000,
    )

    assert allowed is True
    assert remaining == 40_000


def test_exact_50000_tokens_allowed(limiter):
    allowed, remaining = limiter.consume(
        "tenant-a",
        50_000,
        now=1000,
    )

    assert allowed is True
    assert remaining == 0


def test_over_50000_tokens_rejected(limiter):
    limiter.consume(
        "tenant-a",
        40_000,
        now=1000,
    )

    allowed, remaining = limiter.consume(
        "tenant-a",
        10_001,
        now=1010,
    )

    assert allowed is False
    assert remaining == 10_000


def test_tenants_have_independent_limits(limiter):
    allowed_a, _ = limiter.consume(
        "tenant-a",
        50_000,
        now=1000,
    )

    allowed_b, remaining_b = limiter.consume(
        "tenant-b",
        20_000,
        now=1000,
    )

    assert allowed_a is True
    assert allowed_b is True
    assert remaining_b == 30_000


def test_sliding_window_expires_old_usage(limiter):
    limiter.consume(
        "tenant-a",
        50_000,
        now=1000,
    )

    allowed, remaining = limiter.consume(
        "tenant-a",
        10_000,
        now=1061,
    )

    assert allowed is True
    assert remaining == 40_000


def test_usage_persists_in_sqlite(tmp_path):
    db = tmp_path / "persistent.db"

    first = TokenRateLimiter(
        db_path=str(db)
    )

    first.consume(
        "tenant-a",
        20_000,
        now=1000,
    )

    second = TokenRateLimiter(
        db_path=str(db)
    )

    assert second.get_usage(
        "tenant-a",
        now=1010,
    ) == 20_000


def test_invalid_token_count_rejected(limiter):
    with pytest.raises(ValueError):
        limiter.consume(
            "tenant-a",
            0,
        )

import asyncio

from providers import (
    ProviderError,
    ProviderRateLimited,
    ProviderRouter,
)


@pytest.mark.asyncio
async def test_primary_provider_success():
    async def primary(payload):
        return {"message": "primary response"}

    async def secondary(payload):
        return {"message": "secondary response"}

    router = ProviderRouter(
        primary,
        secondary,
        timeout_seconds=0.1,
    )

    response = await router.call(
        {"prompt": "hello"}
    )

    assert response.provider == "primary"
    assert response.data["message"] == "primary response"


@pytest.mark.asyncio
async def test_429_fails_over_to_secondary():
    async def primary(payload):
        raise ProviderRateLimited()

    async def secondary(payload):
        return {"message": "secondary response"}

    router = ProviderRouter(
        primary,
        secondary,
        timeout_seconds=0.1,
    )

    response = await router.call(
        {"prompt": "hello"}
    )

    assert response.provider == "secondary"
    assert response.data["message"] == "secondary response"


@pytest.mark.asyncio
async def test_primary_timeout_fails_over():
    async def primary(payload):
        await asyncio.sleep(0.2)
        return {"message": "too late"}

    async def secondary(payload):
        return {"message": "secondary response"}

    router = ProviderRouter(
        primary,
        secondary,
        timeout_seconds=0.05,
    )

    response = await router.call(
        {"prompt": "hello"}
    )

    assert response.provider == "secondary"
    assert response.data["message"] == "secondary response"


@pytest.mark.asyncio
async def test_secondary_failure_is_sanitized():
    async def primary(payload):
        raise ProviderRateLimited(
            "PRIMARY_SECRET_API_KEY"
        )

    async def secondary(payload):
        raise RuntimeError(
            "SECONDARY_SECRET_API_KEY"
        )

    router = ProviderRouter(
        primary,
        secondary,
        timeout_seconds=0.1,
    )

    with pytest.raises(
        ProviderError,
        match="All providers unavailable",
    ) as exc:
        await router.call(
            {"prompt": "hello"}
        )

    message = str(exc.value)

    assert "PRIMARY_SECRET_API_KEY" not in message
    assert "SECONDARY_SECRET_API_KEY" not in message

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from gateway import app


client = TestClient(app)


def test_missing_api_key_rejected():
    response = client.post(
        "/v1/completions",
        json={
            "prompt": "hello",
            "tokens": 100,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_http_primary_success():
    with patch(
        "gateway.router.call",
        new_callable=AsyncMock,
    ) as mock_call:

        from providers import ProviderResponse

        mock_call.return_value = ProviderResponse(
            provider="primary",
            data={"message": "success"},
        )

        response = client.post(
            "/v1/completions",
            headers={
                "X-API-Key": "http-primary-test"
            },
            json={
                "prompt": "hello",
                "tokens": 100,
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "primary"
    assert data["result"]["message"] == "success"


def test_http_rate_limit_rejected():
    api_key = "http-rate-limit-test"

    first = client.post(
        "/v1/completions",
        headers={"X-API-Key": api_key},
        json={
            "prompt": "hello",
            "tokens": 50000,
        },
    )

    assert first.status_code == 200

    second = client.post(
        "/v1/completions",
        headers={"X-API-Key": api_key},
        json={
            "prompt": "hello again",
            "tokens": 1,
        },
    )

    assert second.status_code == 429
    assert (
        second.json()["error"]["code"]
        == "RATE_LIMIT_EXCEEDED"
    )


def test_provider_error_is_sanitized_at_http_boundary():
    with patch(
        "gateway.router.call",
        new_callable=AsyncMock,
    ) as mock_call:

        mock_call.side_effect = ProviderError(
            "SECRET_PROVIDER_KEY internal failure"
        )

        response = client.post(
            "/v1/completions",
            headers={
                "X-API-Key": "sanitized-error-test"
            },
            json={
                "prompt": "hello",
                "tokens": 100,
            },
        )

    assert response.status_code == 503

    body = response.text

    assert "SECRET_PROVIDER_KEY" not in body
    assert "internal failure" not in body

    assert (
        response.json()["error"]["code"]
        == "PROVIDER_UNAVAILABLE"
    )

    assert (
        response.json()["error"]["message"]
        == "The service is temporarily unavailable."
    )
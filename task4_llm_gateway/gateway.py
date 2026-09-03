import asyncio
import logging
import sys

import uvicorn
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from providers import (
    ProviderError,
    ProviderRateLimited,
    ProviderRouter,
)
from rate_limiter import TokenRateLimiter


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Tenant LLM Gateway")

rate_limiter = TokenRateLimiter(
    db_path="rate_limits.db"
)


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1)
    tokens: int = Field(gt=0)


async def primary_provider(payload: dict) -> dict:
    """
    Mock primary LLM provider.

    Special prompt values are used to test failover.
    """

    prompt = payload["prompt"]

    if prompt == "simulate-429":
        raise ProviderRateLimited()

    if prompt == "simulate-timeout":
        await asyncio.sleep(3.5)

    return {
        "message": f"Primary response: {prompt}"
    }


async def secondary_provider(payload: dict) -> dict:
    return {
        "message": (
            f"Secondary response: {payload['prompt']}"
        )
    }


router = ProviderRouter(
    primary=primary_provider,
    secondary=secondary_provider,
    timeout_seconds=3.0,
)


def error_response(
    status_code: int,
    code: str,
    message: str,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@app.post("/v1/completions")
async def completion(
    request: CompletionRequest,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
):
    if not x_api_key:
        return error_response(
            401,
            "UNAUTHORIZED",
            "API key is required.",
        )

    try:
        allowed, remaining = rate_limiter.consume(
            tenant_key=x_api_key,
            tokens=request.tokens,
        )

        if not allowed:
            return error_response(
                429,
                "RATE_LIMIT_EXCEEDED",
                "Token rate limit exceeded.",
            )

        provider_response = await router.call(
            {
                "prompt": request.prompt,
                "tokens": request.tokens,
            }
        )

        return {
            "provider": provider_response.provider,
            "remaining_tokens": remaining,
            "result": provider_response.data,
        }

    except ProviderError:
        logger.exception(
            "Provider request failed"
        )

        return error_response(
            503,
            "PROVIDER_UNAVAILABLE",
            "The service is temporarily unavailable.",
        )

    except Exception:
        logger.exception(
            "Unexpected gateway error"
        )

        return error_response(
            500,
            "INTERNAL_ERROR",
            "An internal error occurred.",
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "gateway:app",
        host="127.0.0.1",
        port=8003,
        reload=False,
    )
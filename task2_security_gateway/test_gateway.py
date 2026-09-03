from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from gateway import app

import httpx
import pytest

GATEWAY_URL = "http://127.0.0.1:8000/mcp"


@pytest.mark.asyncio
async def test_tools_list_forwarded():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            json=payload,
            headers={"Authorization": "Bearer user-token"},
        )

    data = response.json()

    assert "result" in data
    assert len(data["result"]["tools"]) == 2


@pytest.mark.asyncio
async def test_normal_tool_allowed_for_user():
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_customer_record",
            "arguments": {"customer_id": "CUST-12345"},
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            json=payload,
            headers={"Authorization": "Bearer user-token"},
        )

    data = response.json()

    assert "result" in data
    assert data["id"] == 2


@pytest.mark.asyncio
async def test_admin_tool_blocked_for_user():
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "admin_delete_customer",
            "arguments": {"customer_id": "CUST-12345"},
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            json=payload,
            headers={"Authorization": "Bearer user-token"},
        )

    data = response.json()

    assert data["error"]["code"] == -32001
    assert data["error"]["message"] == "Unauthorized Tool Call"


@pytest.mark.asyncio
async def test_admin_tool_allowed_for_admin():
    payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "admin_delete_customer",
            "arguments": {"customer_id": "CUST-12345"},
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        )

    data = response.json()

    assert "result" in data
    assert data["id"] == 4


@pytest.mark.asyncio
async def test_missing_bearer_token_rejected():
    payload = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/list",
        "params": {},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GATEWAY_URL,
            json=payload,
        )

    data = response.json()

    assert data["error"]["code"] == -32000
    assert data["error"]["message"] == "Unauthorized"

def test_unauthorized_admin_call_never_reaches_downstream():
    client = TestClient(app)

    payload = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "admin_delete_customer",
            "arguments": {
                "customer_id": "CUST-12345"
            },
        },
    }

    with patch(
        "gateway.forward_downstream",
        new_callable=AsyncMock,
    ) as mock_forward:

        response = client.post(
            "/mcp",
            json=payload,
            headers={
                "Authorization": "Bearer user-token"
            },
        )

        data = response.json()

        assert data["error"]["code"] == -32001
        assert (
            data["error"]["message"]
            == "Unauthorized Tool Call"
        )

        mock_forward.assert_not_awaited()
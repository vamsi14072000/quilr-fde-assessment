import pytest
from mcp import MCPError
from mcp.types import CallToolRequestParams, INVALID_PARAMS

from server import call_tool


@pytest.mark.asyncio
async def test_invalid_customer_id_returns_invalid_params():
    params = CallToolRequestParams(
        name="get_customer_record",
        arguments={"customer_id": "ABC-12345"},
    )

    with pytest.raises(MCPError) as exc:
        await call_tool(None, params)

    assert exc.value.error.code == INVALID_PARAMS


@pytest.mark.asyncio
async def test_negative_refund_returns_invalid_params():
    params = CallToolRequestParams(
        name="trigger_refund",
        arguments={
            "customer_id": "CUST-12345",
            "amount": -10,
            "reason": "Customer requested refund",
        },
    )

    with pytest.raises(MCPError) as exc:
        await call_tool(None, params)

    assert exc.value.error.code == INVALID_PARAMS


@pytest.mark.asyncio
async def test_short_reason_returns_invalid_params():
    params = CallToolRequestParams(
        name="trigger_refund",
        arguments={
            "customer_id": "CUST-12345",
            "amount": 50,
            "reason": "damaged",
        },
    )

    with pytest.raises(MCPError) as exc:
        await call_tool(None, params)

    assert exc.value.error.code == INVALID_PARAMS
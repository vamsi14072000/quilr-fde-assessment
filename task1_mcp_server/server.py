import asyncio
import json
import logging
import sys
import uuid

from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)
from pydantic import ValidationError

from models import CustomerRecordInput, RefundInput


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
# stdout is reserved for MCP / JSON-RPC.
# All application logging goes to stderr.
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Mock customer database
# ---------------------------------------------------------
CUSTOMERS = {
    "CUST-12345": {
        "customer_id": "CUST-12345",
        "name": "John Smith",
        "email": "john.smith@example.com",
        "status": "active",
    },
    "CUST-54321": {
        "customer_id": "CUST-54321",
        "name": "Sarah Johnson",
        "email": "sarah.johnson@example.com",
        "status": "active",
    },
}


# ---------------------------------------------------------
# MCP Tool Definitions
# ---------------------------------------------------------
GET_CUSTOMER_RECORD = Tool(
    name="get_customer_record",
    description="Retrieve a customer record by customer ID.",
    input_schema={
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "pattern": r"^CUST-\d{5}$",
                "description": "Customer ID in CUST-XXXXX format",
            }
        },
        "required": ["customer_id"],
        "additionalProperties": False,
    },
)


TRIGGER_REFUND = Tool(
    name="trigger_refund",
    description="Trigger a refund for an existing customer.",
    input_schema={
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "pattern": r"^CUST-\d{5}$",
                "description": "Customer ID in CUST-XXXXX format",
            },
            "amount": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Refund amount must be greater than zero",
            },
            "reason": {
                "type": "string",
                "minLength": 10,
                "description": "Refund reason must contain at least 10 characters",
            },
        },
        "required": [
            "customer_id",
            "amount",
            "reason",
        ],
        "additionalProperties": False,
    },
)


# ---------------------------------------------------------
# tools/list
# ---------------------------------------------------------
async def list_tools(
    ctx: ServerRequestContext,
    params: PaginatedRequestParams | None,
) -> ListToolsResult:

    return ListToolsResult(
        tools=[
            GET_CUSTOMER_RECORD,
            TRIGGER_REFUND,
        ]
    )


# ---------------------------------------------------------
# Validation helper
# ---------------------------------------------------------
def invalid_params(error: ValidationError) -> MCPError:
    """
    Convert Pydantic validation errors into
    standard JSON-RPC -32602 Invalid Params errors.
    """

    details = []

    for item in error.errors():
        details.append(
            {
                "field": ".".join(str(x) for x in item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
        )

    return MCPError(
        INVALID_PARAMS,
        f"Invalid params: {json.dumps(details)}",
    )


# ---------------------------------------------------------
# tools/call
# ---------------------------------------------------------
async def call_tool(
    ctx: ServerRequestContext,
    params: CallToolRequestParams,
) -> CallToolResult:

    arguments = params.arguments or {}

    # -----------------------------------------------------
    # get_customer_record
    # -----------------------------------------------------
    if params.name == "get_customer_record":

        try:
            validated = CustomerRecordInput.model_validate(arguments)

        except ValidationError as exc:
            logger.warning(
                "Invalid get_customer_record parameters: %s",
                exc,
            )
            raise invalid_params(exc)

        logger.info(
            "Looking up customer %s",
            validated.customer_id,
        )

        customer = CUSTOMERS.get(validated.customer_id)

        if customer is None:
            result = {
                "success": False,
                "error": "CUSTOMER_NOT_FOUND",
                "message": "Customer record was not found.",
            }

        else:
            result = {
                "success": True,
                "customer": customer,
            }

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result),
                )
            ],
            structured_content=result,
        )

    # -----------------------------------------------------
    # trigger_refund
    # -----------------------------------------------------
    if params.name == "trigger_refund":

        try:
            validated = RefundInput.model_validate(arguments)

        except ValidationError as exc:
            logger.warning(
                "Invalid trigger_refund parameters: %s",
                exc,
            )
            raise invalid_params(exc)

        logger.info(
            "Processing refund for %s",
            validated.customer_id,
        )

        customer = CUSTOMERS.get(validated.customer_id)

        if customer is None:
            result = {
                "success": False,
                "error": "CUSTOMER_NOT_FOUND",
                "message": "Customer record was not found.",
            }

        else:
            refund_id = (
                f"REF-{uuid.uuid4().hex[:8].upper()}"
            )

            result = {
                "success": True,
                "refund": {
                    "refund_id": refund_id,
                    "customer_id": validated.customer_id,
                    "amount": validated.amount,
                    "reason": validated.reason,
                    "status": "approved",
                },
            }

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(result),
                )
            ],
            structured_content=result,
        )

    # Unknown tool
    raise MCPError(
        INVALID_PARAMS,
        f"Unknown tool: {params.name}",
    )


# ---------------------------------------------------------
# Create MCP Server
# ---------------------------------------------------------
server = Server(
    "Customer Service MCP Server",
    version="1.0.0",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


# ---------------------------------------------------------
# stdio entry point
# ---------------------------------------------------------
async def main() -> None:

    logger.info(
        "Starting Customer Service MCP Server"
    )

    async with stdio_server() as (
        read_stream,
        write_stream,
    ):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
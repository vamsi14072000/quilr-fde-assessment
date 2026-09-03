from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Mock Downstream MCP Server")

# Used by tests to prove blocked calls never reach downstream.
CALL_LOG = []


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    payload = await request.json()

    method = payload.get("method")
    request_id = payload.get("id")

    CALL_LOG.append(payload)

    if method == "tools/list":
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "get_customer_record",
                            "description": "Get a customer record",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "customer_id": {
                                        "type": "string"
                                    }
                                },
                                "required": ["customer_id"],
                            },
                        },
                        {
                            "name": "admin_delete_customer",
                            "description": "Administrative customer deletion",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "customer_id": {
                                        "type": "string"
                                    }
                                },
                                "required": ["customer_id"],
                            },
                        },
                    ]
                },
            }
        )

    if method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name")

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Executed {tool_name}",
                        }
                    ]
                },
            }
        )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not found",
            },
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "downstream_server:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
    )
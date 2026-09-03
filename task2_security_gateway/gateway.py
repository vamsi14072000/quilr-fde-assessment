import logging
import sys

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="MCP Security Gateway")

DOWNSTREAM_URL = "http://127.0.0.1:8001/mcp"

# Demo bearer tokens mapped to roles.
TOKENS = {
    "user-token": "user",
    "admin-token": "admin",
}

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def jsonrpc_error(request_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def get_role(request: Request):
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:].strip()
    return TOKENS.get(token)


async def forward_downstream(payload: dict):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            DOWNSTREAM_URL,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


@app.post("/mcp")
async def gateway(request: Request):
    payload = await request.json()

    request_id = payload.get("id")
    method = payload.get("method")
    role = get_role(request)

    if role is None:
        return JSONResponse(
            jsonrpc_error(
                request_id,
                -32000,
                "Unauthorized",
            )
        )

    # tools/list always forwards for authenticated users.
    if method == "tools/list":
        result = await forward_downstream(payload)
        return JSONResponse(result)

    if method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name", "")

        # Block admin tools before making any downstream request.
        if tool_name.startswith("admin_") and role != "admin":
            logger.warning(
                "Blocked unauthorized tool call: %s",
                tool_name,
            )

            return JSONResponse(
                jsonrpc_error(
                    request_id,
                    -32001,
                    "Unauthorized Tool Call",
                )
            )

        result = await forward_downstream(payload)
        return JSONResponse(result)

    # Other JSON-RPC methods are proxied downstream.
    result = await forward_downstream(payload)
    return JSONResponse(result)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "gateway:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
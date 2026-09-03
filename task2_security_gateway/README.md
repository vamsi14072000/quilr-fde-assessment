# Task 2 - MCP Security Gateway

## Overview

This project implements an HTTP/JSON-RPC security gateway that sits between an MCP client and a downstream MCP server.

The gateway authenticates requests using bearer tokens and applies role-based authorization before forwarding tool calls downstream.

## Authorization

Demo bearer tokens:

- `user-token` -> `user`
- `admin-token` -> `admin`

## Behavior

### tools/list

Authenticated requests are forwarded to the downstream MCP server.

### tools/call

Normal tools are available to authenticated users.

Tools whose names begin with `admin_` require the `admin` role.

If a non-admin attempts to call an `admin_*` tool, the gateway returns:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Unauthorized Tool Call"
  }
}
```

The unauthorized request is rejected before any downstream request is made.

## Run

Start the mock downstream server:

```bash
python downstream_server.py
```

It runs on:

```text
127.0.0.1:8001
```

Start the gateway in another terminal:

```bash
python gateway.py
```

It runs on:

```text
127.0.0.1:8000
```

## Tests

Run:

```bash
pytest test_gateway.py -v
```

The tests verify:

- `tools/list` forwarding
- Normal user tool calls
- Non-admin `admin_*` rejection
- Admin access to `admin_*` tools
- Missing bearer-token rejection
- Unauthorized admin calls never reach downstream
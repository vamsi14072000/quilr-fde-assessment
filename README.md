# Quilr Forward Deployed Engineer Practical Assessment

This repository contains my implementation of the four tasks in the Quilr practical assessment.

## Project Structure

```text
quilr-fde-assessment/
├── task1_mcp_server/
├── task2_security_gateway/
├── task3_pii_streaming/
├── task4_llm_gateway/
└── README.md
```

## Task 1 - Custom MCP Server

Implements a custom MCP server using the official Python MCP SDK.

### Tools

- `get_customer_record(customer_id)`
- `trigger_refund(customer_id, amount, reason)`

### Key Features

- Strict Pydantic validation
- `CUST-XXXXX` customer ID validation
- Positive refund amount validation
- Minimum 10-character refund reason
- JSON-RPC `-32602 Invalid Params` error mapping
- STDIO transport
- Application logs isolated to stderr
- No application logging written to the MCP stdout protocol channel

### Tests

```bash
cd task1_mcp_server
pytest -v
```

20 tests verify validation, tool behavior, and JSON-RPC error handling.

---

## Task 2 - MCP Security Gateway

Implements an HTTP/JSON-RPC authorization gateway between an MCP client and downstream MCP server.

### Key Features

- Bearer-token authentication
- Role-based authorization
- `tools/list` forwarding
- Standard tool calls forwarded downstream
- `admin_*` tools restricted to the admin role
- Unauthorized admin calls return JSON-RPC `-32001`
- Unauthorized calls are blocked before any downstream request occurs

### Tests

```bash
cd task2_security_gateway
pytest -v
```

6 tests verify authentication, forwarding, role enforcement, and downstream isolation.

---

## Task 3 - Streaming PII Redaction

Implements a chunk-aware streaming LLM response redaction gateway.

### Supported PII

- Email addresses
- Social Security Numbers
- Credit card numbers

### Key Features

- Incremental stream processing
- Rolling-buffer boundary protection
- Detects PII split across multiple chunks
- Does not accumulate the complete LLM response
- Low-latency streaming using a bounded 64-character buffer

### Tests

```bash
cd task3_pii_streaming
pytest -v
```

10 tests verify redaction, chunk-boundary handling, normal-text preservation, and early streaming.

---

## Task 4 - Multi-Tenant LLM Gateway

Implements a persistent multi-tenant LLM gateway with rate limiting and provider failover.

### Key Features

- 50,000 tokens/minute per tenant API key
- Rolling 60-second token window
- SQLite persistence
- Independent tenant limits
- Primary LLM provider routing
- Automatic secondary-provider failover on primary 429
- Automatic secondary-provider failover when primary exceeds 3000 ms
- Sanitized client-facing provider errors
- No internal provider details or credentials exposed to clients

### Tests

```bash
cd task4_llm_gateway
pytest -v
```

15 tests verify rate limiting, persistence, tenant isolation, provider routing, failover, and error sanitization.

---

## Test Summary

| Task | Tests |
|---|---:|
| Task 1 | 20 passed |
| Task 2 | 6 passed |
| Task 3 | 10 passed |
| Task 4 | 15 passed |
| **Total** | **51 passed** |

## Environment

Python 3.11+ is recommended.

Each task includes its own `requirements.txt`.

Example setup:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies for the task being reviewed:

```bash
pip install -r requirements.txt
```

Then run:

```bash
pytest -v
```

## Design Approach

The implementation keeps each assessment task isolated so that it can be reviewed, executed, and tested independently.

The focus throughout the assessment is protocol correctness, explicit validation, security boundaries, streaming behavior, tenant isolation, persistence, failover behavior, and automated verification.
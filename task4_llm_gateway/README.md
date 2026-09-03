# Task 4 - Multi-Tenant LLM Gateway

## Overview

This project implements a multi-tenant LLM gateway with persistent token rate limiting, provider failover, and sanitized client-facing errors.

## Rate Limiting

Each tenant is identified by the `X-API-Key` request header.

The gateway enforces a sliding-window limit of:

- 50,000 tokens
- Per tenant API key
- Per rolling 60-second window

Usage is persisted in SQLite.

Concurrent updates use SQLite transactions and an application lock to prevent accidental limit overruns.

## Provider Failover

Requests are sent to the primary provider first.

The gateway fails over to the secondary provider when:

- The primary provider returns/runs into a 429 rate-limit condition
- The primary provider does not complete within 3 seconds

Successful primary requests do not invoke the secondary provider.

## Error Sanitization

Internal provider exceptions, credentials, and implementation details are never returned to clients.

Provider failures return:

```json
{
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "The service is temporarily unavailable."
  }
}
```

## API

### POST /v1/completions

Header:

```text
X-API-Key: <tenant-api-key>
```

Example body:

```json
{
  "prompt": "hello",
  "tokens": 1000
}
```

## Run

```bash
python gateway.py
```

The gateway runs on:

```text
127.0.0.1:8003
```

## Tests

Run:

```bash
pytest test_gateway.py -v
```

Tests cover:

- 50K token limit
- Sliding 60-second window
- Independent tenant limits
- SQLite persistence
- Primary provider success
- 429 provider failover
- Primary timeout failover
- Missing API key handling
- HTTP rate-limit enforcement
- Sanitized provider errors
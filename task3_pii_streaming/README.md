# Task 3 - Streaming PII Redaction Gateway

## Overview

This project implements a streaming LLM gateway that redacts sensitive PII while preserving streaming behavior.

Supported PII:

- Email addresses
- Social Security Numbers
- Credit card numbers

## Streaming Design

The gateway processes incoming LLM chunks incrementally instead of accumulating the full response.

A small rolling buffer is retained to detect PII that may be split across chunk boundaries.

The gateway uses a 64-character rolling buffer to balance PII detection with low time-to-first-token latency.

## Redaction

PII is replaced with:

- `[REDACTED_EMAIL]`
- `[REDACTED_SSN]`
- `[REDACTED_CARD]`

## Run

```bash
python gateway.py
```

The gateway runs on:

```text
127.0.0.1:8002
```

Test the stream:

```bash
curl.exe -N http://127.0.0.1:8002/stream
```

## Tests

Run:

```bash
pytest test_redactor.py -v
```

Tests cover:

- Email redaction
- SSN redaction
- Credit card redaction
- PII split across stream chunks
- Multiple PII types
- Preservation of normal text
- Early streaming before the full response is accumulated
- Chunk-boundary protection with the low-latency buffer
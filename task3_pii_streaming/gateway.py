import asyncio
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from redactor import StreamingPIIRedactor


app = FastAPI(title="Streaming PII Redaction Gateway")


async def mock_llm_stream() -> AsyncIterator[str]:
    """
    Simulates an upstream LLM streaming response.

    PII is intentionally split across chunks to verify
    chunk-boundary protection.
    """

    chunks = [
        "Customer details: ",
        "email john.smith",
        "@example.",
        "com, SSN 123-",
        "45-",
        "6789, card 4111 ",
        "1111 1111 ",
        "1111. End of response.",
    ]

    for chunk in chunks:
        await asyncio.sleep(0.01)
        yield chunk


async def redacted_llm_stream() -> AsyncIterator[str]:
    """
    Process the upstream response incrementally.

    The complete LLM response is never accumulated.
    """

    redactor = StreamingPIIRedactor(
        buffer_size=64
    )

    async for chunk in mock_llm_stream():
        safe_output = redactor.process(chunk)

        if safe_output:
            yield safe_output

    final_output = redactor.flush()

    if final_output:
        yield final_output


@app.get("/stream")
async def stream():
    return StreamingResponse(
        redacted_llm_stream(),
        media_type="text/plain",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "gateway:app",
        host="127.0.0.1",
        port=8002,
        reload=False,
    )
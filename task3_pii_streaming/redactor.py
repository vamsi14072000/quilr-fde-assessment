import re
from collections.abc import Iterable, Iterator


EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

SSN_RE = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

CREDIT_CARD_RE = re.compile(
    r"\b(?:\d[ -]?){13,19}\b"
)


def redact_pii(text: str) -> str:
    """Redact supported PII from a complete text segment."""

    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = SSN_RE.sub("[REDACTED_SSN]", text)
    text = CREDIT_CARD_RE.sub("[REDACTED_CARD]", text)

    return text


class StreamingPIIRedactor:
    """
    Chunk-aware streaming PII redactor.

    A small rolling buffer is retained so PII split across
    chunk boundaries can still be detected without buffering
    the complete LLM response.
    """

    def __init__(self, buffer_size: int = 128):
        if buffer_size <= 0:
            raise ValueError("buffer_size must be greater than zero")

        self.buffer_size = buffer_size
        self.buffer = ""

    def process(self, chunk: str) -> str:
        """
        Process one incoming chunk and return text that is safe
        to emit immediately.
        """

        if not chunk:
            return ""

        self.buffer += chunk

        if len(self.buffer) <= self.buffer_size:
            return ""

        safe_length = len(self.buffer) - self.buffer_size

        safe_text = self.buffer[:safe_length]
        self.buffer = self.buffer[safe_length:]

        return redact_pii(safe_text)

    def flush(self) -> str:
        """Redact and emit the remaining buffered text."""

        if not self.buffer:
            return ""

        output = redact_pii(self.buffer)
        self.buffer = ""

        return output


def redact_stream(
    chunks: Iterable[str],
    buffer_size: int = 128,
) -> Iterator[str]:
    """Redact PII from an iterable of streaming text chunks."""

    redactor = StreamingPIIRedactor(
        buffer_size=buffer_size
    )

    for chunk in chunks:
        output = redactor.process(chunk)

        if output:
            yield output

    final_output = redactor.flush()

    if final_output:
        yield final_output
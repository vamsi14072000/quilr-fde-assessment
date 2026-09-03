from redactor import redact_pii, redact_stream


def collect(chunks):
    return "".join(redact_stream(chunks))


def test_email_redaction():
    result = redact_pii(
        "Contact john.smith@example.com for help."
    )

    assert "john.smith@example.com" not in result
    assert "[REDACTED_EMAIL]" in result


def test_ssn_redaction():
    result = redact_pii(
        "SSN is 123-45-6789."
    )

    assert "123-45-6789" not in result
    assert "[REDACTED_SSN]" in result


def test_credit_card_redaction():
    result = redact_pii(
        "Card number is 4111 1111 1111 1111."
    )

    assert "4111 1111 1111 1111" not in result
    assert "[REDACTED_CARD]" in result


def test_email_split_across_chunks():
    result = collect(
        [
            "Contact john.smith",
            "@example.",
            "com for help.",
        ]
    )

    assert "john.smith@example.com" not in result
    assert "[REDACTED_EMAIL]" in result


def test_ssn_split_across_chunks():
    result = collect(
        [
            "SSN is 123-",
            "45-",
            "6789.",
        ]
    )

    assert "123-45-6789" not in result
    assert "[REDACTED_SSN]" in result


def test_card_split_across_chunks():
    result = collect(
        [
            "Card: 4111 1111 ",
            "1111 ",
            "1111.",
        ]
    )

    assert "4111 1111 1111 1111" not in result
    assert "[REDACTED_CARD]" in result


def test_normal_text_preserved():
    text = "This response contains no sensitive information."

    assert collect([text]) == text


def test_multiple_pii_types():
    result = collect(
        [
            "Email: test@example.com ",
            "SSN: 123-45-6789 ",
            "Card: 4111-1111-1111-1111",
        ]
    )

    assert "test@example.com" not in result
    assert "123-45-6789" not in result
    assert "4111-1111-1111-1111" not in result

    assert "[REDACTED_EMAIL]" in result
    assert "[REDACTED_SSN]" in result
    assert "[REDACTED_CARD]" in result

def test_stream_emits_before_full_response():
    chunks = [
        "A" * 80,
        "B" * 80,
        "C" * 80,
    ]

    stream = redact_stream(
        chunks,
        buffer_size=64,
    )

    first_output = next(stream)

    assert first_output
    assert len(first_output) > 0

    # The first output is produced before all
    # input chunks need to be accumulated.
    assert len(first_output) < 240

def test_chunk_boundary_redaction_with_low_latency_buffer():
    chunks = [
        "A" * 70 + " Contact test",
        "@example.",
        "com for additional information.",
    ]

    result = "".join(
        redact_stream(
            chunks,
            buffer_size=64,
        )
    )

    assert "test@example.com" not in result
    assert "[REDACTED_EMAIL]" in result
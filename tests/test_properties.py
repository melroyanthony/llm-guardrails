"""Bounded properties for redaction, parsing, and request-body handling."""

from __future__ import annotations

import asyncio
import json

from hypothesis import given
from hypothesis import strategies as st

from api.body_limit import _buffer_body
from api.pii_store import MappingStore, mapping_nbytes
from llm_guardrails.injection_detector import InjectionDetector
from llm_guardrails.output_validator import OutputValidator, ValidationRules
from llm_guardrails.pii_redactor import PIIRedactor

_PLAIN = st.text(
    alphabet=st.characters(max_codepoint=255, exclude_characters="<"),
    max_size=24,
)
_CHUNKS = st.lists(st.binary(max_size=8), max_size=5)
_MAPS = st.dictionaries(
    st.text(min_size=1, max_size=4),
    st.text(max_size=4),
    max_size=2,
)


@given(_PLAIN)
def test_redaction_round_trip_without_placeholder_markers(text: str) -> None:
    redactor = PIIRedactor()
    redacted, mapping = redactor.redact(text)
    for placeholder, original in mapping.items():
        assert placeholder.startswith("<<") and placeholder.endswith(">>")
        assert original in text
        assert placeholder in redacted
    assert redactor.restore(redacted, mapping) == text


@given(_PLAIN)
def test_injection_score_matches_analyse_and_ignores_zero_width(text: str) -> None:
    detector = InjectionDetector(threshold=0.5)
    score = detector.score(text)
    assert 0.0 <= score <= 1.0
    analysed = detector.analyse(text)
    assert analysed.score == score
    assert analysed.is_injection is (score >= 0.5)
    assert detector.score(f"\u200b{text}\ufeff") == score


@given(_PLAIN)
def test_json_object_rule_follows_the_parser(text: str) -> None:
    rules = ValidationRules(
        json_schema={"type": "object", "required": ["ok"]},
        check_hallucination=False,
    )
    result = OutputValidator().validate(text, rules)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        assert result.is_valid is False
        assert any("not valid JSON" in issue.message for issue in result.issues)
        return
    if isinstance(parsed, dict):
        missing = "ok" not in parsed
        assert any("Required key missing" in issue.message for issue in result.issues) is missing
        assert result.is_valid is not missing
        return
    assert result.is_valid is False
    assert any("Expected a JSON object" in issue.message for issue in result.issues)


@given(_CHUNKS)
def test_body_chunks_under_the_cap_are_replayed(chunks: list[bytes]) -> None:
    pending = list(chunks)

    async def receive() -> dict:
        if not pending:
            return {"type": "http.request", "body": b"", "more_body": False}
        piece = pending.pop(0)
        return {
            "type": "http.request",
            "body": piece,
            "more_body": bool(pending),
        }

    async def run() -> None:
        cap = 16
        total = sum(len(piece) for piece in chunks)
        buffered, too_large = await _buffer_body(receive, cap)
        if total > cap:
            assert too_large is True
            assert buffered == []
            return
        assert too_large is False
        body = b"".join(
            message.get("body", b"") for message in buffered if message["type"] == "http.request"
        )
        assert body == b"".join(chunks)
        assert len(buffered) == 1

    asyncio.run(run())


@given(_MAPS)
def test_mapping_store_returns_what_it_accepted(mapping: dict[str, str]) -> None:
    store = MappingStore(max_entries=4, max_bytes=40, max_entry_bytes=16)
    size = mapping_nbytes(mapping)
    token = store.put(mapping, 3600)
    if not mapping or size > store.max_entry_bytes or size > store.max_bytes:
        assert token is None
        assert store.nbytes == 0
        return
    assert token is not None
    assert store.nbytes == size
    assert store.pop(token, 3600) == mapping
    assert store.pop(token, 3600) is None
    assert store.nbytes == 0

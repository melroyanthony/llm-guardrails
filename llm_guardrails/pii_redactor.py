"""PII / PHI redaction with reversible placeholder mapping.

Design goals
------------
* **GDPR-compliant**: PII is never persisted -- only held in a transient
  mapping dictionary that the caller controls.
* **Reversible**: ``restore()`` re-inserts the original values so that
  downstream consumers can see the real data when authorised.
* **Extensible**: add new patterns to ``_PATTERNS`` without touching the
  core ``redact`` / ``restore`` logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class PIIRedactor:
    """Detect and redact personally identifiable information from text.

    The redactor replaces each PII match with a deterministic placeholder
    such as ``<<EMAIL_1>>`` and returns a mapping that allows exact
    restoration later.

    Example
    -------
    >>> redactor = PIIRedactor()
    >>> redacted, mapping = redactor.redact("Call me at 555-123-4567")
    >>> redacted
    'Call me at <<PHONE_1>>'
    >>> redactor.restore(redacted, mapping)
    'Call me at 555-123-4567'
    """

    # Each entry: (label, compiled regex)
    # Order matters -- more specific patterns should come first to avoid
    # partial matches (e.g. SSN before plain number sequences).
    _PATTERNS: ClassVar[list[tuple[str, re.Pattern[str]]]] = [
        (
            "SSN",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        ),
        (
            "CREDIT_CARD",
            re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        ),
        (
            "EMAIL",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        ),
        (
            "PHONE",
            re.compile(
                r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
            ),
        ),
        (
            "IP_ADDRESS",
            re.compile(
                r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
            ),
        ),
        (
            "DATE_OF_BIRTH",
            re.compile(
                r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b"
            ),
        ),
        (
            "NAME",
            # Simple heuristic: two or more consecutive capitalised words that
            # are not at the very start of a sentence (preceded by ". " or at
            # position 0).  This is intentionally conservative to minimise
            # false positives.
            re.compile(r"(?<=[.!?]\s|[:,]\s)(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)"),
        ),
    ]

    # Internal counters reset on every ``redact`` call.
    _counters: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def redact(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace PII tokens with placeholders.

        Returns
        -------
        redacted_text : str
            The input with all detected PII replaced by ``<<LABEL_N>>``
            placeholders.
        mapping : dict[str, str]
            ``{placeholder: original_value}`` -- pass this to ``restore``
            to recover the original text.
        """
        self._counters = {}
        mapping: dict[str, str] = {}

        for label, pattern in self._PATTERNS:
            text = self._replace(text, pattern, label, mapping)

        return text, mapping

    @staticmethod
    def restore(text: str, mapping: dict[str, str]) -> str:
        """Re-insert original PII values from *mapping* into *text*."""
        for placeholder, original in mapping.items():
            text = text.replace(placeholder, original)
        return text

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _next_placeholder(self, label: str) -> str:
        count = self._counters.get(label, 0) + 1
        self._counters[label] = count
        return f"<<{label}_{count}>>"

    def _replace(
        self,
        text: str,
        pattern: re.Pattern[str],
        label: str,
        mapping: dict[str, str],
    ) -> str:
        """Replace all *pattern* matches in *text* and record in *mapping*."""

        def _sub(match: re.Match[str]) -> str:
            original = match.group(0)
            # Avoid re-redacting an already-replaced placeholder.
            if original.startswith("<<") and original.endswith(">>"):
                return original
            placeholder = self._next_placeholder(label)
            mapping[placeholder] = original
            return placeholder

        return pattern.sub(_sub, text)

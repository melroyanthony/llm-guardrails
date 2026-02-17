"""PII / PHI redaction with reversible placeholder mapping.

Thin Python wrapper around the Rust ``_core`` implementation for
high-performance regex-based PII detection.
"""

from __future__ import annotations

from llm_guardrails._core import pii_redact, pii_restore


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
        return pii_redact(text)

    @staticmethod
    def restore(text: str, mapping: dict[str, str]) -> str:
        """Re-insert original PII values from *mapping* into *text*."""
        return pii_restore(text, mapping)

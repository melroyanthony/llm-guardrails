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

    ``allow_entities`` limits detection to those labels. An empty list
    raises ``ValueError`` because it would redact nothing. ``deny_entities``
    skips those labels. A denied label wins when it is also allowed.
    A label outside the built-in set raises ``ValueError`` and names the
    unknown label. Card numbers must pass the Luhn check. An SSN whose area
    is ``000``, ``666``, or ``9xx``, whose group is ``00``, or whose serial
    is ``0000`` is left alone. A name or date of birth is redacted only when
    a context word such as ``name``, ``born``, ``DOB``, ``Dr.``, or ``Ms.``
    sits next to it. ``Jane Doe called`` is not redacted. There is no switch
    that restores the old match of every title-case pair or every date.

    Example
    -------
    >>> redactor = PIIRedactor()
    >>> redacted, mapping = redactor.redact("Call me at 555-123-4567")
    >>> redacted
    'Call me at <<PHONE_1>>'
    >>> redactor.restore(redacted, mapping)
    'Call me at 555-123-4567'
    """

    def __init__(
        self,
        allow_entities: list[str] | None = None,
        deny_entities: list[str] | None = None,
    ) -> None:
        # Reject an empty allow list and unknown labels before any text is kept.
        pii_redact("", allow_entities, deny_entities)
        self.allow_entities = allow_entities
        self.deny_entities = deny_entities

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
        return pii_redact(text, self.allow_entities, self.deny_entities)

    @staticmethod
    def restore(text: str, mapping: dict[str, str]) -> str:
        """Re-insert original PII values from *mapping* into *text*."""
        return pii_restore(text, mapping)

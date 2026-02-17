"""Prompt-injection detection via pattern matching and heuristic scoring.

Thin Python wrapper around the Rust ``_core`` implementation.  The Rust
engine provides compiled regex matching for all detection rules.
"""

from __future__ import annotations

from pydantic import BaseModel

from llm_guardrails._core import (
    injection_analyse,
    injection_list_rules,
    injection_score,
)


class InjectionResult(BaseModel):
    """Result of an injection-detection scan."""

    score: float
    """Injection-likelihood score in [0.0, 1.0]."""

    is_injection: bool
    """Whether the score exceeds the configured threshold."""

    matched_rules: list[str]
    """Human-readable labels of the rules that fired."""


class InjectionDetector:
    """Score and classify user prompts for injection risk.

    Parameters
    ----------
    threshold : float
        Score at or above which ``detect`` returns ``True``.
        Defaults to ``0.5``.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def score(self, text: str) -> float:
        """Return an injection-likelihood score in ``[0.0, 1.0]``."""
        return injection_score(text)

    def detect(self, text: str, threshold: float | None = None) -> bool:
        """Return ``True`` if the text is classified as a prompt injection."""
        effective = threshold if threshold is not None else self.threshold
        return self.score(text) >= effective

    def analyse(self, text: str, threshold: float | None = None) -> InjectionResult:
        """Full analysis with score, boolean flag, and matched-rule labels."""
        effective = threshold if threshold is not None else self.threshold
        score, is_injection, matched_rules = injection_analyse(text, effective)
        return InjectionResult(
            score=score,
            is_injection=is_injection,
            matched_rules=matched_rules,
        )

    def list_rules(self) -> list[dict[str, str | float]]:
        """Return a human-readable list of all active detection rules."""
        return injection_list_rules()

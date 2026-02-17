"""Bias detection and scoring for LLM-generated text.

Thin Python wrapper around the Rust ``_core`` implementation for
high-performance pattern-based bias detection.
"""

from __future__ import annotations

from pydantic import BaseModel

from llm_guardrails._core import bias_score as _bias_score


class BiasReport(BaseModel):
    """Structured result of a bias scan."""

    score: float
    """Aggregate bias-risk score in [0.0, 1.0].  Higher = more concern."""

    flags: list[str]
    """Human-readable descriptions of each detected signal."""


class BiasScorer:
    """Score LLM output for demographic bias indicators.

    The implementation checks three categories:

    1. **Stereotyping language** -- phrases that reinforce common stereotypes.
    2. **Unbalanced demographic references** -- significant asymmetry in
       how often different demographic groups are mentioned.
    3. **Absolute generalisation markers** -- language such as "all X are ..."
       that paints entire groups with a single brush.
    """

    def score(self, text: str) -> BiasReport:
        """Analyse *text* and return a :class:`BiasReport`."""
        score_val, flags = _bias_score(text)
        return BiasReport(score=score_val, flags=flags)

"""Bias detection and scoring for LLM-generated text.

This module inspects model output for signals of demographic bias,
stereotyping language, and unbalanced demographic references.  It is
intended as a **post-processing** guard that flags potentially harmful
content before it reaches end users.

The scorer is deliberately conservative: it will surface *potential*
issues for human review rather than silently censoring output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from pydantic import BaseModel


class BiasReport(BaseModel):
    """Structured result of a bias scan."""

    score: float
    """Aggregate bias-risk score in [0.0, 1.0].  Higher = more concern."""

    flags: list[str]
    """Human-readable descriptions of each detected signal."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_tokens(text: str, tokens: list[str]) -> int:
    """Case-insensitive count of how many *tokens* appear in *text*."""
    lower = text.lower()
    return sum(1 for t in tokens if t.lower() in lower)


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

@dataclass
class BiasScorer:
    """Score LLM output for demographic bias indicators.

    The implementation checks three categories:

    1. **Stereotyping language** -- phrases that reinforce common
       stereotypes.
    2. **Unbalanced demographic references** -- significant asymmetry in
       how often different demographic groups are mentioned.
    3. **Absolute generalisation markers** -- language such as "all X
       are ..." or "X never ..." that paints entire groups with a single
       brush.
    """

    # ---- Stereotyping patterns ------------------------------------------
    _STEREOTYPE_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(
                r"\b(women|men|girls|boys)\s+(are|aren't|can't|should|shouldn't)\s+"
                r"(naturally|inherently|biologically|always|never)",
                re.IGNORECASE,
            ),
            "Gender-stereotyping language detected",
        ),
        (
            re.compile(
                r"\b(all|every|no)\s+(men|women|asians?|blacks?|whites?|latinos?|hispanics?"
                r"|muslims?|christians?|jews?|hindus?)\s+(are|have|lack|need)",
                re.IGNORECASE,
            ),
            "Absolute generalisation about a demographic group",
        ),
        (
            re.compile(
                r"\b(typical|stereotypical|expected)\s+(of|for)\s+(a|an|the)\s+"
                r"(man|woman|asian|black|white|latino|hispanic|muslim|christian|jew|hindu)",
                re.IGNORECASE,
            ),
            "Explicit stereotyping framing detected",
        ),
        (
            re.compile(
                r"\b(elderly|old\s+people|seniors?)\s+(are|can't|shouldn't|always|never)\b",
                re.IGNORECASE,
            ),
            "Age-stereotyping language detected",
        ),
        (
            re.compile(
                r"\b(disabled|handicapped)\s+(people|persons?|individuals?)\s+"
                r"(can't|are\s+unable|should\s+not|never)",
                re.IGNORECASE,
            ),
            "Disability-stereotyping language detected",
        ),
    ]

    # ---- Demographic-reference balance ----------------------------------
    _GENDER_TOKENS: ClassVar[dict[str, list[str]]] = {
        "male": ["he", "him", "his", "man", "men", "boy", "boys", "male", "father", "husband"],
        "female": [
            "she", "her", "hers", "woman", "women", "girl", "girls", "female", "mother", "wife",
        ],
    }

    _IMBALANCE_THRESHOLD: ClassVar[float] = 3.0  # ratio triggering a flag

    # ---- Generalisation markers -----------------------------------------
    _GENERALISATION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(all|every|no|none\s+of\s+the|always|never)\s+"
        r"(men|women|people\s+from|members\s+of|those\s+who)\b",
        re.IGNORECASE,
    )

    # ---- Weights for final score ----------------------------------------
    _STEREOTYPE_WEIGHT: ClassVar[float] = 0.40
    _IMBALANCE_WEIGHT: ClassVar[float] = 0.25
    _GENERALISATION_WEIGHT: ClassVar[float] = 0.35

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, text: str) -> BiasReport:
        """Analyse *text* and return a :class:`BiasReport`."""
        flags: list[str] = []
        raw_scores: list[float] = []

        # 1. Stereotyping patterns
        stereotype_hits = 0
        for pattern, description in self._STEREOTYPE_PATTERNS:
            if pattern.search(text):
                flags.append(description)
                stereotype_hits += 1
        # Normalise: 1 hit -> 0.5, 2+ -> 1.0
        if stereotype_hits:
            raw_scores.append(min(stereotype_hits * 0.5, 1.0) * self._STEREOTYPE_WEIGHT)

        # 2. Gender-reference imbalance
        male_count = _count_tokens(text, self._GENDER_TOKENS["male"])
        female_count = _count_tokens(text, self._GENDER_TOKENS["female"])
        if male_count and female_count:
            ratio = max(male_count, female_count) / min(male_count, female_count)
            if ratio >= self._IMBALANCE_THRESHOLD:
                dominant = "male" if male_count > female_count else "female"
                flags.append(
                    f"Gender-reference imbalance: {dominant} references "
                    f"outnumber the other by {ratio:.1f}x"
                )
                raw_scores.append(
                    min((ratio - self._IMBALANCE_THRESHOLD) / 5.0 + 0.3, 1.0)
                    * self._IMBALANCE_WEIGHT
                )

        # 3. Absolute generalisations
        gen_matches = self._GENERALISATION_PATTERN.findall(text)
        if gen_matches:
            flags.append(
                f"Absolute generalisation marker(s) found ({len(gen_matches)} occurrence(s))"
            )
            raw_scores.append(
                min(len(gen_matches) * 0.4, 1.0) * self._GENERALISATION_WEIGHT
            )

        total = min(sum(raw_scores), 1.0) if raw_scores else 0.0

        return BiasReport(score=round(total, 4), flags=flags)

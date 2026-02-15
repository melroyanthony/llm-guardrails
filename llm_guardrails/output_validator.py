"""Output validation for LLM-generated responses.

This module provides post-generation checks:

* **JSON schema validation** -- ensures structured output matches an
  expected schema.
* **Hallucination-indicator scoring** -- flags hedging language that
  may signal fabricated information.
* **Length constraints** -- rejects responses that exceed a maximum
  character or token budget.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    """A single validation problem."""

    rule: str
    message: str
    severity: str = "error"  # "error" | "warning"


class ValidationResult(BaseModel):
    """Aggregate result of all validation checks."""

    is_valid: bool
    issues: list[ValidationIssue] = []
    hallucination_score: float = 0.0
    """Hedging-language score in [0.0, 1.0].  Higher = more hedging."""


# ---------------------------------------------------------------------------
# Validation-rule definitions
# ---------------------------------------------------------------------------

class ValidationRules(BaseModel):
    """Configuration object describing which checks to run."""

    json_schema: dict[str, Any] | None = None
    """If provided, the output must be valid JSON matching this schema."""

    max_length: int | None = None
    """Maximum allowed character count."""

    check_hallucination: bool = True
    """Whether to run the hedging-language heuristic."""

    hallucination_threshold: float = 0.6
    """Score at or above which hedging is flagged as a warning."""

    required_keywords: list[str] | None = None
    """If provided, each keyword must appear in the output (case-insensitive)."""

    blocked_keywords: list[str] | None = None
    """If provided, none of these keywords may appear in the output."""


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

@dataclass
class OutputValidator:
    """Validate LLM-generated text against a set of configurable rules."""

    # Hedging / hallucination-indicator phrases.
    _HEDGING_PHRASES: ClassVar[list[str]] = [
        "I think",
        "I believe",
        "I'm not sure",
        "I am not sure",
        "it is possible that",
        "it might be",
        "probably",
        "perhaps",
        "maybe",
        "as far as I know",
        "to the best of my knowledge",
        "I cannot confirm",
        "I don't have access",
        "I do not have access",
        "reportedly",
        "allegedly",
        "it seems",
        "it appears",
    ]

    _hedging_patterns: list[re.Pattern[str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._hedging_patterns = [
            re.compile(re.escape(phrase), re.IGNORECASE)
            for phrase in self._HEDGING_PHRASES
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, text: str, rules: ValidationRules | None = None) -> ValidationResult:
        """Run all enabled checks and return a :class:`ValidationResult`."""
        if rules is None:
            rules = ValidationRules()

        issues: list[ValidationIssue] = []
        hallucination_score = 0.0

        # 1. Max-length check
        if rules.max_length is not None and len(text) > rules.max_length:
            issues.append(
                ValidationIssue(
                    rule="max_length",
                    message=(
                        f"Output length ({len(text)}) exceeds maximum "
                        f"({rules.max_length})"
                    ),
                )
            )

        # 2. JSON-schema validation
        if rules.json_schema is not None:
            issues.extend(self._check_json(text, rules.json_schema))

        # 3. Hallucination-indicator scoring
        if rules.check_hallucination:
            hallucination_score = self._hallucination_score(text)
            if hallucination_score >= rules.hallucination_threshold:
                issues.append(
                    ValidationIssue(
                        rule="hallucination",
                        message=(
                            f"High hedging-language score "
                            f"({hallucination_score:.2f}), possible "
                            f"hallucination"
                        ),
                        severity="warning",
                    )
                )

        # 4. Required keywords
        if rules.required_keywords:
            lower_text = text.lower()
            for kw in rules.required_keywords:
                if kw.lower() not in lower_text:
                    issues.append(
                        ValidationIssue(
                            rule="required_keyword",
                            message=f"Required keyword missing: '{kw}'",
                        )
                    )

        # 5. Blocked keywords
        if rules.blocked_keywords:
            lower_text = text.lower()
            for kw in rules.blocked_keywords:
                if kw.lower() in lower_text:
                    issues.append(
                        ValidationIssue(
                            rule="blocked_keyword",
                            message=f"Blocked keyword found: '{kw}'",
                        )
                    )

        has_errors = any(i.severity == "error" for i in issues)

        return ValidationResult(
            is_valid=not has_errors,
            issues=issues,
            hallucination_score=round(hallucination_score, 4),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_json(
        self, text: str, schema: dict[str, Any]
    ) -> list[ValidationIssue]:
        """Minimal JSON-schema check (type + required fields)."""
        issues: list[ValidationIssue] = []
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue(
                    rule="json_schema",
                    message=f"Output is not valid JSON: {exc}",
                )
            )
            return issues

        # Check top-level type
        expected_type = schema.get("type")
        if expected_type == "object" and not isinstance(data, dict):
            issues.append(
                ValidationIssue(
                    rule="json_schema",
                    message="Expected a JSON object at top level",
                )
            )
        elif expected_type == "array" and not isinstance(data, list):
            issues.append(
                ValidationIssue(
                    rule="json_schema",
                    message="Expected a JSON array at top level",
                )
            )

        # Check required keys (one level deep)
        if isinstance(data, dict):
            for key in schema.get("required", []):
                if key not in data:
                    issues.append(
                        ValidationIssue(
                            rule="json_schema",
                            message=f"Required key missing: '{key}'",
                        )
                    )

        return issues

    def _hallucination_score(self, text: str) -> float:
        """Return a 0-1 score based on hedging-phrase density."""
        if not text:
            return 0.0
        hits = sum(1 for p in self._hedging_patterns if p.search(text))
        # Normalise: at 5+ hits we max out.
        return min(hits / 5.0, 1.0)

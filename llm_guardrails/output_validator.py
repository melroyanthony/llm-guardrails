"""Output validation for LLM-generated responses.

Thin Python wrapper around the Rust ``_core`` implementation.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from llm_guardrails._core import output_validate as _output_validate


class ValidationIssue(BaseModel):
    """A single validation problem."""

    rule: str
    message: str
    severity: str = "error"


class ValidationResult(BaseModel):
    """Aggregate result of all validation checks."""

    is_valid: bool
    issues: list[ValidationIssue] = []
    hallucination_score: float = 0.0


class ValidationRules(BaseModel):
    """Configuration object describing which checks to run."""

    json_schema: dict[str, Any] | None = None
    max_length: int | None = None
    check_hallucination: bool = True
    hallucination_threshold: float = 0.6
    required_keywords: list[str] | None = None
    blocked_keywords: list[str] | None = None


class OutputValidator:
    """Validate LLM-generated text against a set of configurable rules."""

    def validate(self, text: str, rules: ValidationRules | None = None) -> ValidationResult:
        """Run all enabled checks and return a :class:`ValidationResult`."""
        if rules is None:
            rules = ValidationRules()

        schema_str = json.dumps(rules.json_schema) if rules.json_schema else None

        is_valid, issues_raw, hallucination_score = _output_validate(
            text,
            json_schema=schema_str,
            max_length=rules.max_length,
            check_hallucination=rules.check_hallucination,
            hallucination_threshold=rules.hallucination_threshold,
            required_keywords=rules.required_keywords,
            blocked_keywords=rules.blocked_keywords,
        )

        issues = [
            ValidationIssue(
                rule=i["rule"],
                message=i["message"],
                severity=i["severity"],
            )
            for i in issues_raw
        ]

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            hallucination_score=hallucination_score,
        )

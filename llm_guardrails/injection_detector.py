"""Prompt-injection detection via pattern matching and heuristic scoring.

This module provides a lightweight, deterministic detector for common
prompt-injection techniques.  It is designed to run **before** user input
reaches the LLM, acting as the first line of defence.

Each detection rule carries a *weight* (0.0 -- 1.0) that reflects how
strongly its presence signals an injection attempt.  The final score is
the maximum weight among all matched rules, optionally boosted when
multiple rules fire simultaneously.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import BaseModel


class InjectionResult(BaseModel):
    """Result of an injection-detection scan."""

    score: float
    """Injection-likelihood score in [0.0, 1.0]."""

    is_injection: bool
    """Whether the score exceeds the configured threshold."""

    matched_rules: list[str]
    """Human-readable labels of the rules that fired."""


@dataclass
class _Rule:
    label: str
    pattern: re.Pattern[str]
    weight: float
    explanation: str


@dataclass
class InjectionDetector:
    """Score and classify user prompts for injection risk.

    Parameters
    ----------
    threshold : float
        Score at or above which ``detect`` returns ``True``.
        Defaults to ``0.5``.
    """

    threshold: float = 0.5

    # Each rule: (label, regex, weight 0-1, human explanation)
    _RULES: ClassVar[list[_Rule]] = [
        _Rule(
            label="ignore_previous",
            pattern=re.compile(
                r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+"
                r"(instructions?|directives?|rules?|prompts?)",
                re.IGNORECASE,
            ),
            weight=0.95,
            explanation=(
                "Attempts to override the system prompt by telling the model "
                "to disregard its original instructions."
            ),
        ),
        _Rule(
            label="reveal_system_prompt",
            pattern=re.compile(
                r"(show|reveal|display|print|output|repeat|tell\s+me)\s+"
                r"(the\s+)?(system\s+prompt|initial\s+instructions?|hidden\s+prompt)",
                re.IGNORECASE,
            ),
            weight=0.90,
            explanation=(
                "Tries to exfiltrate the system prompt or internal instructions."
            ),
        ),
        _Rule(
            label="role_play_attack",
            pattern=re.compile(
                r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|"
                r"from\s+now\s+on\s+you\s+are|switch\s+to|enter\s+.*?mode)",
                re.IGNORECASE,
            ),
            weight=0.70,
            explanation=(
                "Instructs the model to adopt a new persona or mode, which "
                "may bypass safety constraints."
            ),
        ),
        _Rule(
            label="developer_mode",
            pattern=re.compile(
                r"(developer|debug|admin|maintenance|god)\s*mode",
                re.IGNORECASE,
            ),
            weight=0.85,
            explanation=(
                "Requests activation of a privileged mode that does not exist."
            ),
        ),
        _Rule(
            label="encoding_evasion",
            pattern=re.compile(
                r"(base64|hex|rot13|encode|decode|translate)\s+(the\s+following|this)",
                re.IGNORECASE,
            ),
            weight=0.60,
            explanation=(
                "May attempt to smuggle instructions through encoding schemes."
            ),
        ),
        _Rule(
            label="do_anything_now",
            pattern=re.compile(r"\bDAN\b|do\s+anything\s+now", re.IGNORECASE),
            weight=0.95,
            explanation=(
                "References the well-known 'DAN' (Do Anything Now) jailbreak."
            ),
        ),
        _Rule(
            label="system_role_injection",
            pattern=re.compile(
                r"<\|?(system|im_start|im_end)\|?>|"
                r"\[INST\]|\[/INST\]|"
                r"###\s*(system|instruction)",
                re.IGNORECASE,
            ),
            weight=0.90,
            explanation=(
                "Injects raw chat-markup tokens to impersonate a system message."
            ),
        ),
        _Rule(
            label="token_smuggling",
            pattern=re.compile(
                r"(ignore|bypass|override)\s+(safety|content|filter|guardrail|moderation)",
                re.IGNORECASE,
            ),
            weight=0.85,
            explanation=(
                "Directly asks the model to bypass its safety mechanisms."
            ),
        ),
    ]

    # Bonus added when 2+ rules fire at once (capped at 1.0).
    _MULTI_MATCH_BONUS: ClassVar[float] = 0.10

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    rules: list[_Rule] = field(default_factory=lambda: list(InjectionDetector._RULES))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(self, text: str) -> float:
        """Return an injection-likelihood score in ``[0.0, 1.0]``.

        The score equals the heaviest matched rule weight, plus a small
        bonus when multiple rules fire.
        """
        matched_weights = [
            rule.weight for rule in self.rules if rule.pattern.search(text)
        ]
        if not matched_weights:
            return 0.0
        base = max(matched_weights)
        bonus = self._MULTI_MATCH_BONUS if len(matched_weights) >= 2 else 0.0
        return min(base + bonus, 1.0)

    def detect(self, text: str, threshold: float | None = None) -> bool:
        """Return ``True`` if the text is classified as a prompt injection."""
        effective = threshold if threshold is not None else self.threshold
        return self.score(text) >= effective

    def analyse(self, text: str, threshold: float | None = None) -> InjectionResult:
        """Full analysis with score, boolean flag, and matched-rule labels."""
        effective = threshold if threshold is not None else self.threshold
        matched = [rule for rule in self.rules if rule.pattern.search(text)]
        matched_weights = [r.weight for r in matched]

        if not matched_weights:
            s = 0.0
        else:
            bonus = self._MULTI_MATCH_BONUS if len(matched_weights) >= 2 else 0.0
            s = min(max(matched_weights) + bonus, 1.0)

        return InjectionResult(
            score=s,
            is_injection=s >= effective,
            matched_rules=[r.label for r in matched],
        )

    def list_rules(self) -> list[dict[str, str | float]]:
        """Return a human-readable list of all active detection rules."""
        return [
            {
                "label": r.label,
                "weight": r.weight,
                "explanation": r.explanation,
            }
            for r in self.rules
        ]

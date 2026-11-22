"""Guard base class and registry.

Built-in checks register as guards. A pipeline starts with those four
concerns and can take more. The whitespace of a name is the registry key.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from llm_guardrails.bias_scorer import BiasScorer
from llm_guardrails.injection_detector import InjectionDetector, InjectionResult
from llm_guardrails.output_validator import OutputValidator, ValidationResult, ValidationRules
from llm_guardrails.pii_redactor import PIIRedactor


class GuardStage(StrEnum):
    """Where a guard runs."""

    INPUT = "input"
    OUTPUT = "output"


class GuardContext(BaseModel):
    """Values a guard may read or update for the rest of this call."""

    model_config = {"arbitrary_types_allowed": True}

    pii_mapping: dict[str, str] = Field(default_factory=dict)
    injection_threshold: float = 0.5
    validation_rules: ValidationRules | None = None


class GuardResult(BaseModel):
    """One guard's verdict.

    ``text`` is what the next guard sees. ``blocks`` stops the remaining
    guards on this call when ``passed`` is false.
    """

    model_config = {"arbitrary_types_allowed": True}

    name: str
    passed: bool
    blocks: bool = False
    score: float = 0.0
    reason: str = ""
    text: str
    extra: dict[str, Any] = Field(default_factory=dict)


class Guard(ABC):
    """Base class for a named check at one stage."""

    name: str
    stage: GuardStage

    @abstractmethod
    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        """Score or rewrite ``text``."""


class GuardRegistry:
    """Ordered map of guards. Each name is registered once."""

    def __init__(self) -> None:
        self._guards: dict[str, Guard] = {}

    def register(self, guard: Guard) -> None:
        """Add ``guard``. A second registration of the same name is an error."""
        if not isinstance(guard, Guard):
            raise TypeError("registry accepts Guard instances")
        if guard.name in self._guards:
            raise ValueError(f"guard {guard.name!r} is already registered")
        self._guards[guard.name] = guard

    def remove(self, name: str) -> None:
        """Drop a registered guard."""
        if name not in self._guards:
            raise KeyError(name)
        del self._guards[name]

    def get(self, name: str) -> Guard:
        """Return the guard registered as ``name``."""
        if name not in self._guards:
            raise KeyError(name)
        return self._guards[name]

    def names(self) -> list[str]:
        """Registration order."""
        return list(self._guards)

    def for_stage(self, stage: GuardStage) -> list[Guard]:
        """Guards for ``stage``, in registration order."""
        return [guard for guard in self._guards.values() if guard.stage == stage]

    @classmethod
    def builtins(
        cls,
        *,
        pii_allow_entities: list[str] | None = None,
        pii_deny_entities: list[str] | None = None,
    ) -> GuardRegistry:
        """The PII, injection, validation, and bias guards, plus PII restore."""
        registry = cls()
        registry.register(PiiGuard(pii_allow_entities, pii_deny_entities))
        registry.register(InjectionGuard())
        registry.register(OutputValidationGuard())
        registry.register(BiasGuard())
        registry.register(PiiRestoreGuard())
        return registry


class PiiGuard(Guard):
    """Redact PII and store the placeholder map on the context."""

    name = "pii"
    stage = GuardStage.INPUT

    def __init__(
        self,
        allow_entities: list[str] | None = None,
        deny_entities: list[str] | None = None,
    ) -> None:
        self._redactor = PIIRedactor(allow_entities=allow_entities, deny_entities=deny_entities)

    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        sanitised, mapping = self._redactor.redact(text)
        context.pii_mapping.clear()
        context.pii_mapping.update(mapping)
        return GuardResult(
            name=self.name,
            passed=True,
            blocks=False,
            text=sanitised,
            extra={"mapping": mapping},
        )


class InjectionGuard(Guard):
    """Block when the injection score reaches the context threshold."""

    name = "injection"
    stage = GuardStage.INPUT

    def __init__(self) -> None:
        self._detector = InjectionDetector()

    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        injection = self._detector.analyse(text, threshold=context.injection_threshold)
        return GuardResult(
            name=self.name,
            passed=not injection.is_injection,
            blocks=injection.is_injection,
            score=injection.score,
            reason=", ".join(injection.matched_rules),
            text=text,
            extra={"injection": injection},
        )


class OutputValidationGuard(Guard):
    """Validate model text. A failure is reported and does not stop later guards."""

    name = "output_validation"
    stage = GuardStage.OUTPUT

    def __init__(self) -> None:
        self._validator = OutputValidator()

    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        validation = self._validator.validate(text, context.validation_rules)
        return GuardResult(
            name=self.name,
            passed=validation.is_valid,
            blocks=False,
            score=validation.hallucination_score,
            text=text,
            extra={"validation": validation},
        )


class BiasGuard(Guard):
    """Score bias patterns. The score does not stop the pipeline."""

    name = "bias"
    stage = GuardStage.OUTPUT

    def __init__(self) -> None:
        self._scorer = BiasScorer()

    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        bias = self._scorer.score(text)
        return GuardResult(
            name=self.name,
            passed=True,
            blocks=False,
            score=bias.score,
            text=text,
            extra={"bias": bias},
        )


class PiiRestoreGuard(Guard):
    """Put original PII back when the context still holds a map."""

    name = "pii_restore"
    stage = GuardStage.OUTPUT

    def check(self, text: str, *, context: GuardContext) -> GuardResult:
        restored = PIIRedactor.restore(text, context.pii_mapping) if context.pii_mapping else text
        return GuardResult(name=self.name, passed=True, blocks=False, text=restored)


def empty_injection() -> InjectionResult:
    """Injection result used when that guard does not run."""
    return InjectionResult(score=0.0, is_injection=False, matched_rules=[])


def empty_validation() -> ValidationResult:
    """Validation result used when that guard does not run."""
    return ValidationResult(is_valid=True)

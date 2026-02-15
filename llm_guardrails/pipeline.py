"""GuardrailsPipeline -- chains all guards into a unified pre/post workflow.

Typical usage::

    pipeline = GuardrailsPipeline()

    # Before sending to the LLM
    pre = pipeline.pre_process(user_input)
    if pre.blocked:
        return "Request blocked by safety guardrails."

    llm_response = call_llm(pre.sanitised_text)

    # After receiving from the LLM
    post = pipeline.post_process(llm_response, pre.pii_mapping)

    return post.final_text
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from llm_guardrails.bias_scorer import BiasReport, BiasScorer
from llm_guardrails.injection_detector import InjectionDetector, InjectionResult
from llm_guardrails.output_validator import (
    OutputValidator,
    ValidationResult,
    ValidationRules,
)
from llm_guardrails.pii_redactor import PIIRedactor


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

class PreProcessResult(BaseModel):
    """Outcome of pre-processing (input guardrails)."""

    sanitised_text: str
    """The user input after PII redaction."""

    pii_mapping: dict[str, str]
    """Mapping from placeholder to original PII value."""

    injection: InjectionResult
    """Full injection-detection analysis."""

    blocked: bool
    """If ``True`` the input should **not** be forwarded to the LLM."""


class PostProcessResult(BaseModel):
    """Outcome of post-processing (output guardrails)."""

    final_text: str
    """The LLM output after PII restoration."""

    validation: ValidationResult
    """Output-validation results."""

    bias: BiasReport
    """Bias-scoring results."""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class GuardrailsPipeline:
    """Configurable chain of Responsible-AI guardrails.

    Parameters
    ----------
    pii_enabled : bool
        Run PII redaction/restoration.
    injection_enabled : bool
        Run prompt-injection detection.
    bias_enabled : bool
        Run bias scoring on LLM output.
    output_validation_enabled : bool
        Run output validation on LLM output.
    injection_threshold : float
        Score threshold for blocking input.
    validation_rules : ValidationRules | None
        Rules passed to the :class:`OutputValidator`.
    """

    pii_enabled: bool = True
    injection_enabled: bool = True
    bias_enabled: bool = True
    output_validation_enabled: bool = True

    injection_threshold: float = 0.5
    validation_rules: ValidationRules | None = None

    # Guards (lazily initialised for convenience)
    _pii: PIIRedactor = field(default_factory=PIIRedactor, init=False, repr=False)
    _injection: InjectionDetector = field(
        default_factory=InjectionDetector, init=False, repr=False
    )
    _bias: BiasScorer = field(default_factory=BiasScorer, init=False, repr=False)
    _validator: OutputValidator = field(
        default_factory=OutputValidator, init=False, repr=False
    )

    # ------------------------------------------------------------------
    # Pre-processing (input guardrails)
    # ------------------------------------------------------------------

    def pre_process(self, text: str) -> PreProcessResult:
        """Run input-side guardrails.

        Steps
        -----
        1. PII redaction (if enabled).
        2. Injection detection (if enabled).
        """
        # 1. PII redaction
        if self.pii_enabled:
            sanitised, pii_map = self._pii.redact(text)
        else:
            sanitised, pii_map = text, {}

        # 2. Injection detection
        if self.injection_enabled:
            injection = self._injection.analyse(sanitised, threshold=self.injection_threshold)
        else:
            injection = InjectionResult(score=0.0, is_injection=False, matched_rules=[])

        blocked = injection.is_injection

        return PreProcessResult(
            sanitised_text=sanitised,
            pii_mapping=pii_map,
            injection=injection,
            blocked=blocked,
        )

    # ------------------------------------------------------------------
    # Post-processing (output guardrails)
    # ------------------------------------------------------------------

    def post_process(
        self,
        text: str,
        pii_mapping: dict[str, str] | None = None,
    ) -> PostProcessResult:
        """Run output-side guardrails.

        Steps
        -----
        1. Output validation (if enabled).
        2. Bias scoring (if enabled).
        3. PII restoration (if enabled and mapping is provided).
        """
        # 1. Output validation
        if self.output_validation_enabled:
            validation = self._validator.validate(text, self.validation_rules)
        else:
            validation = ValidationResult(is_valid=True)

        # 2. Bias scoring
        if self.bias_enabled:
            bias = self._bias.score(text)
        else:
            bias = BiasReport(score=0.0, flags=[])

        # 3. PII restoration
        if self.pii_enabled and pii_mapping:
            final_text = self._pii.restore(text, pii_mapping)
        else:
            final_text = text

        return PostProcessResult(
            final_text=final_text,
            validation=validation,
            bias=bias,
        )

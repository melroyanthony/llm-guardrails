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

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from pydantic import BaseModel, Field

from llm_guardrails.bias_scorer import BiasReport
from llm_guardrails.guards import (
    Guard,
    GuardContext,
    GuardRegistry,
    GuardResult,
    GuardStage,
    empty_injection,
    empty_validation,
)
from llm_guardrails.injection_detector import InjectionResult
from llm_guardrails.output_validator import ValidationResult, ValidationRules

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


class OutputStreamEvent(BaseModel):
    """One chunk of model output after the output guards have seen it.

    ``text`` is the concatenation of chunks so far, before PII restoration.
    ``blocked`` is true when a guard asked to stop the stream.
    """

    chunk: str
    text: str
    blocked: bool
    results: list[GuardResult] = Field(default_factory=list)


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
    pii_allow_entities : list[str] | None
        When set, only these PII labels are redacted.
    pii_deny_entities : list[str] | None
        PII labels that are never redacted.
    """

    pii_enabled: bool = True
    injection_enabled: bool = True
    bias_enabled: bool = True
    output_validation_enabled: bool = True

    injection_threshold: float = 0.5
    validation_rules: ValidationRules | None = None
    pii_allow_entities: list[str] | None = None
    pii_deny_entities: list[str] | None = None
    registry: GuardRegistry | None = None

    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = GuardRegistry.builtins(
                pii_allow_entities=self.pii_allow_entities,
                pii_deny_entities=self.pii_deny_entities,
            )

    def register(self, guard: Guard) -> None:
        """Add a guard to this pipeline's registry."""
        assert self.registry is not None
        self.registry.register(guard)

    # ------------------------------------------------------------------
    # Pre-processing (input guardrails)
    # ------------------------------------------------------------------

    def pre_process(self, text: str) -> PreProcessResult:
        """Run input-side guards in registry order.

        Built-in PII redaction runs before injection detection when both
        are enabled. A later guard can still block a clean injection score.
        """
        context = self._context()
        sanitised, results, blocked = self._run(GuardStage.INPUT, text, context, restore=False)
        injection = empty_injection()
        for result in results:
            found = result.extra.get("injection")
            if isinstance(found, InjectionResult):
                injection = found
        return PreProcessResult(
            sanitised_text=sanitised,
            pii_mapping=dict(context.pii_mapping),
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
        """Run output-side guards, then restore PII when a map is present."""
        context = self._context(pii_mapping)
        final_text, results, _blocked = self._run(GuardStage.OUTPUT, text, context, restore=True)
        validation = empty_validation()
        bias = BiasReport(score=0.0, flags=[])
        for result in results:
            found_validation = result.extra.get("validation")
            if isinstance(found_validation, ValidationResult):
                validation = found_validation
            found_bias = result.extra.get("bias")
            if isinstance(found_bias, BiasReport):
                bias = found_bias
        return PostProcessResult(
            final_text=final_text,
            validation=validation,
            bias=bias,
        )

    def stream_output(self, chunks: Iterable[str]) -> Iterator[OutputStreamEvent]:
        """Check each chunk of model output against the output guards.

        The text is the concatenation so far, before PII restoration.
        A guard that blocks ends the iterator before the next chunk is read.
        """
        parts: list[str] = []
        for chunk in chunks:
            parts.append(chunk)
            text = "".join(parts)
            _current, results, blocked = self._run(
                GuardStage.OUTPUT,
                text,
                self._context(),
                restore=False,
            )
            yield OutputStreamEvent(
                chunk=chunk,
                text=text,
                blocked=blocked,
                results=results,
            )
            if blocked:
                return

    def _context(self, pii_mapping: dict[str, str] | None = None) -> GuardContext:
        return GuardContext(
            pii_mapping=dict(pii_mapping or {}),
            injection_threshold=self.injection_threshold,
            validation_rules=self.validation_rules,
        )

    def _guard_enabled(self, name: str) -> bool:
        if name in {"pii", "pii_restore"}:
            return self.pii_enabled
        if name == "injection":
            return self.injection_enabled
        if name == "bias":
            return self.bias_enabled
        if name == "output_validation":
            return self.output_validation_enabled
        return True

    def _run(
        self,
        stage: GuardStage,
        text: str,
        context: GuardContext,
        *,
        restore: bool,
    ) -> tuple[str, list[GuardResult], bool]:
        assert self.registry is not None
        current = text
        results: list[GuardResult] = []
        blocked = False
        for guard in self.registry.for_stage(stage):
            if guard.name == "pii_restore" and not restore:
                continue
            if not self._guard_enabled(guard.name):
                continue
            result = guard.check(current, context=context)
            results.append(result)
            current = result.text
            if result.blocks and not result.passed:
                blocked = True
                break
        return current, results, blocked

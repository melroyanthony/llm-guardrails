"""FastAPI demo service for the LLM Guardrails library.

Run with::

    uvicorn api.main:app --reload

Endpoints
---------
POST /guard/input   -- Run input guardrails (PII redaction + injection detection)
POST /guard/output  -- Run output guardrails (validation + bias scoring + PII restore)
POST /guard/full    -- Full pipeline: input guards -> simulated LLM -> output guards
GET  /health        -- Health check

``/guard/input`` returns an opaque ``pii_mapping_id``. A non-empty map that
fits the entry and byte budgets stays in this process for
``MAPPING_TTL_SECONDS`` and is popped on the first ``/guard/output`` call.
A map that does not fit is not stored, and it does not remove another
caller's id. The id is not shared across workers.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.body_limit import LimitRequestBody
from api.pii_store import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_ENTRY_BYTES,
    MappingStore,
)
from llm_guardrails.pipeline import GuardrailsPipeline

MAX_TEXT_LENGTH = 8_000
MAX_BODY_BYTES = 32 * 1024
MAPPING_TTL_SECONDS = 15 * 60
MAX_MAPPING_ENTRIES = DEFAULT_MAX_ENTRIES
MAX_MAPPING_BYTES = DEFAULT_MAX_BYTES
MAX_MAPPING_ENTRY_BYTES = DEFAULT_MAX_ENTRY_BYTES

_pipeline: GuardrailsPipeline | None = None
_store = MappingStore(
    max_entries=MAX_MAPPING_ENTRIES,
    max_bytes=MAX_MAPPING_BYTES,
    max_entry_bytes=MAX_MAPPING_ENTRY_BYTES,
)


def package_version() -> str:
    """Installed distribution version. Maturin reads it from Cargo.toml."""
    try:
        return version("ferroguard")
    except PackageNotFoundError:
        return "0.0.0"


def get_pipeline() -> GuardrailsPipeline:
    """Build the pipeline on first use, not at import."""
    global _pipeline
    if _pipeline is None:
        _pipeline = GuardrailsPipeline()
    return _pipeline


def reset_for_tests() -> None:
    """Drop the cached pipeline and any stored mappings."""
    global _pipeline
    _pipeline = None
    _store.clear()


app = FastAPI(
    title="LLM Guardrails API",
    description=(
        "Responsible AI toolkit -- PII redaction, injection detection, "
        "bias scoring, output validation. PII mappings stay on the server."
    ),
    version=package_version(),
)
app.add_middleware(LimitRequestBody, max_bytes=MAX_BODY_BYTES)


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InputRequest(_RequestModel):
    text: str = Field(..., max_length=MAX_TEXT_LENGTH, description="User prompt to guard.")


class OutputRequest(_RequestModel):
    text: str = Field(
        ...,
        max_length=MAX_TEXT_LENGTH,
        description="LLM-generated output to validate.",
    )
    pii_mapping_id: str | None = Field(
        None,
        description=(
            "Opaque id returned by /guard/input. The placeholder map stays in this "
            f"process for {MAPPING_TTL_SECONDS} seconds. The id works once. "
            "Omit it when /guard/input stored nothing."
        ),
    )


class FullRequest(_RequestModel):
    text: str = Field(
        ...,
        max_length=MAX_TEXT_LENGTH,
        description="User prompt to run through the full pipeline.",
    )
    simulated_llm_response: str | None = Field(
        None,
        max_length=MAX_TEXT_LENGTH,
        description=(
            "Optional canned LLM response. If omitted the API returns "
            "a stub response for demonstration purposes."
        ),
    )


class InputResponse(BaseModel):
    sanitised_text: str
    pii_mapping_id: str | None
    injection_score: float
    is_injection: bool
    matched_rules: list[str]
    blocked: bool


class OutputResponse(BaseModel):
    final_text: str
    is_valid: bool
    validation_issues: list[dict[str, str]]
    hallucination_score: float
    bias_score: float
    bias_flags: list[str]


class FullResponse(BaseModel):
    input_guard: InputResponse
    output_guard: OutputResponse | None = None
    blocked: bool


class HealthResponse(BaseModel):
    status: str
    version: str


def _input_response(text: str, *, remember: bool) -> tuple[InputResponse, dict[str, str], bool]:
    pre = get_pipeline().pre_process(text)
    mapping_id = _store.put(pre.pii_mapping, MAPPING_TTL_SECONDS) if remember else None
    response = InputResponse(
        sanitised_text=pre.sanitised_text,
        pii_mapping_id=mapping_id,
        injection_score=pre.injection.score,
        is_injection=pre.injection.is_injection,
        matched_rules=pre.injection.matched_rules,
        blocked=pre.blocked,
    )
    return response, pre.pii_mapping, pre.blocked


def _output_response(text: str, mapping: dict[str, str]) -> OutputResponse:
    post = get_pipeline().post_process(text, mapping or None)
    return OutputResponse(
        final_text=post.final_text,
        is_valid=post.validation.is_valid,
        validation_issues=[
            {"rule": issue.rule, "message": issue.message, "severity": issue.severity}
            for issue in post.validation.issues
        ],
        hallucination_score=post.validation.hallucination_score,
        bias_score=post.bias.score,
        bias_flags=post.bias.flags,
    )


def _load_mapping(mapping_id: str | None) -> dict[str, str]:
    if not mapping_id:
        return {}
    mapping = _store.pop(mapping_id, MAPPING_TTL_SECONDS)
    if mapping is None:
        raise HTTPException(status_code=404, detail="Unknown or expired PII mapping id.")
    return mapping


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    """Health check. ``version`` is the installed package version."""
    return HealthResponse(status="ok", version=package_version())


@app.post("/guard/input", response_model=InputResponse, tags=["guardrails"])
async def guard_input(req: InputRequest):
    """Run input-side guardrails on user text."""
    response, _mapping, _blocked = _input_response(req.text, remember=True)
    return response


@app.post("/guard/output", response_model=OutputResponse, tags=["guardrails"])
async def guard_output(req: OutputRequest):
    """Run output-side guardrails on LLM-generated text."""
    mapping = _load_mapping(req.pii_mapping_id)
    return _output_response(req.text, mapping)


@app.post("/guard/full", response_model=FullResponse, tags=["guardrails"])
async def guard_full(req: FullRequest):
    """Full pipeline: input guardrails -> (simulated) LLM -> output guardrails."""
    input_result, mapping, blocked = _input_response(req.text, remember=False)
    if blocked:
        return FullResponse(input_guard=input_result, blocked=True)

    llm_output = req.simulated_llm_response or (
        f"[Simulated LLM response to]: {input_result.sanitised_text}"
    )
    return FullResponse(
        input_guard=input_result,
        output_guard=_output_response(llm_output, mapping),
        blocked=False,
    )

"""FastAPI demo service for the LLM Guardrails library.

Run with::

    uvicorn api.main:app --reload

Endpoints
---------
POST /guard/input   -- Run input guardrails (PII redaction + injection detection)
POST /guard/output  -- Run output guardrails (validation + bias scoring + PII restore)
POST /guard/full    -- Full pipeline: input guards -> simulated LLM -> output guards
GET  /health        -- Health check
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_guardrails.pipeline import GuardrailsPipeline

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Guardrails API",
    description="Responsible AI toolkit -- PII redaction, injection detection, bias scoring, output validation.",
    version="0.1.0",
)

pipeline = GuardrailsPipeline()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class InputRequest(BaseModel):
    text: str = Field(..., description="User prompt to guard.")


class OutputRequest(BaseModel):
    text: str = Field(..., description="LLM-generated output to validate.")
    pii_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Placeholder-to-original PII mapping from the input stage.",
    )


class FullRequest(BaseModel):
    text: str = Field(..., description="User prompt to run through the full pipeline.")
    simulated_llm_response: str | None = Field(
        None,
        description=(
            "Optional canned LLM response.  If omitted the API returns "
            "a stub response for demonstration purposes."
        ),
    )


class InputResponse(BaseModel):
    sanitised_text: str
    pii_mapping: dict[str, str]
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
    status: str = "ok"
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    """Health check."""
    return HealthResponse()


@app.post("/guard/input", response_model=InputResponse, tags=["guardrails"])
async def guard_input(req: InputRequest):
    """Run input-side guardrails on user text."""
    pre = pipeline.pre_process(req.text)
    return InputResponse(
        sanitised_text=pre.sanitised_text,
        pii_mapping=pre.pii_mapping,
        injection_score=pre.injection.score,
        is_injection=pre.injection.is_injection,
        matched_rules=pre.injection.matched_rules,
        blocked=pre.blocked,
    )


@app.post("/guard/output", response_model=OutputResponse, tags=["guardrails"])
async def guard_output(req: OutputRequest):
    """Run output-side guardrails on LLM-generated text."""
    post = pipeline.post_process(req.text, req.pii_mapping or None)
    return OutputResponse(
        final_text=post.final_text,
        is_valid=post.validation.is_valid,
        validation_issues=[
            {"rule": i.rule, "message": i.message, "severity": i.severity}
            for i in post.validation.issues
        ],
        hallucination_score=post.validation.hallucination_score,
        bias_score=post.bias.score,
        bias_flags=post.bias.flags,
    )


@app.post("/guard/full", response_model=FullResponse, tags=["guardrails"])
async def guard_full(req: FullRequest):
    """Full pipeline: input guardrails -> (simulated) LLM -> output guardrails."""
    pre = pipeline.pre_process(req.text)

    input_result = InputResponse(
        sanitised_text=pre.sanitised_text,
        pii_mapping=pre.pii_mapping,
        injection_score=pre.injection.score,
        is_injection=pre.injection.is_injection,
        matched_rules=pre.injection.matched_rules,
        blocked=pre.blocked,
    )

    if pre.blocked:
        return FullResponse(input_guard=input_result, blocked=True)

    # Use the caller-provided LLM response or a stub.
    llm_output = req.simulated_llm_response or (
        f"[Simulated LLM response to]: {pre.sanitised_text}"
    )

    post = pipeline.post_process(llm_output, pre.pii_mapping or None)

    output_result = OutputResponse(
        final_text=post.final_text,
        is_valid=post.validation.is_valid,
        validation_issues=[
            {"rule": i.rule, "message": i.message, "severity": i.severity}
            for i in post.validation.issues
        ],
        hallucination_score=post.validation.hallucination_score,
        bias_score=post.bias.score,
        bias_flags=post.bias.flags,
    )

    return FullResponse(
        input_guard=input_result,
        output_guard=output_result,
        blocked=False,
    )

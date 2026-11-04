"""Types for the Rust extension ``llm_guardrails._core``.

``list[str] | tuple[str, ...]`` matches PyO3 ``Vec<String>``. A bare ``str``
is not a list of labels: extracting one raises ``TypeError``.
"""

def pii_redact(
    text: str,
    allow_entities: list[str] | tuple[str, ...] | None = None,
    deny_entities: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, dict[str, str]]: ...
def pii_restore(text: str, mapping: dict[str, str]) -> str: ...
def injection_score(text: str) -> float: ...
def injection_analyse(text: str, threshold: float) -> tuple[float, bool, list[str]]: ...
def injection_list_rules() -> list[dict[str, str | float]]: ...
def bias_score(text: str) -> tuple[float, list[str]]: ...
def output_validate(
    text: str,
    json_schema: str | None = None,
    max_length: int | None = None,
    check_hallucination: bool = True,
    hallucination_threshold: float = 0.6,
    required_keywords: list[str] | tuple[str, ...] | None = None,
    blocked_keywords: list[str] | tuple[str, ...] | None = None,
) -> tuple[bool, list[dict[str, str]], float]: ...

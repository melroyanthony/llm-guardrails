---
name: evaluation-framework
description: |
  Patterns for automated quality evaluation using golden test sets, RAGAS metrics, and
  domain-specific assertions. Applicable to RAG, chatbots, code generation, and summarization.
  Use when building evaluation pipelines or measuring output quality programmatically.
  Triggers on: evaluation, golden test, RAGAS, metrics, faithfulness, hallucination, benchmark.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Evaluation Framework

## Principle

Without evaluation metrics, you can't distinguish between a system that retrieves well and one that generates plausible-sounding nonsense. Measure quality systematically, not anecdotally.

## 1. Golden Test Set Design

### Structure

```json
[
  {
    "id": "qt-001",
    "question": "What medications am I currently taking?",
    "expected_answer": "Based on your records, you are currently prescribed metformin 500mg twice daily.",
    "context": ["FHIR MedicationRequest: metformin 500mg, frequency: BID, status: active"],
    "metadata": {
      "category": "medication_query",
      "source_type": "fhir",
      "difficulty": "easy",
      "requires_reasoning": false
    }
  }
]
```

### Coverage Requirements

| Category | Minimum | Examples |
|---|---|---|
| Happy path queries | 5+ | Standard questions with clear answers |
| Multi-source queries | 3+ | Questions requiring data from multiple sources |
| Edge cases | 3+ | Empty results, ambiguous queries, very long context |
| Adversarial queries | 2+ | Prompt injection attempts, out-of-scope questions |
| Exact-match queries | 2+ | IDs, codes, specific dates (tests BM25/keyword search) |

### Scale Targets

| Stage | Count | Purpose |
|---|---|---|
| MVP / Demo | 15-20 | Smoke test, basic quality signal |
| Beta | 50-100 | Coverage across all query types and sources |
| Production | 200+ | Statistical significance, regression detection |

## 2. RAGAS Metrics

### Core Metrics

| Metric | What It Measures | How to Compute | Target |
|---|---|---|---|
| **Faithfulness** | Answer uses only retrieved context, no fabrication | Check each claim in answer against context | > 0.8 |
| **Answer Relevancy** | Answer addresses the actual question asked | Semantic similarity between answer and question | > 0.8 |
| **Context Precision** | Retrieved chunks are relevant to the question | Fraction of retrieved chunks that are useful | > 0.7 |
| **Context Recall** | All relevant information was retrieved | Fraction of golden context found in retrieval | > 0.7 |

### Domain-Specific Metrics

| Metric | Domain | What It Measures |
|---|---|---|
| PII Leakage Rate | Healthcare, Finance | Sensitive data in responses (target: 0) |
| Topic Compliance | Any with restrictions | Responses stay within allowed topics |
| Citation Accuracy | Knowledge bases | Sources cited match actual retrieval |
| Hallucination Rate | Any generative | Claims not supported by retrieved context |

## 3. Evaluation Script Pattern

```python
"""evaluate.py — Automated quality evaluation against golden test set."""

import json
from pathlib import Path

def evaluate(golden_path: str, pipeline) -> dict:
    golden = json.loads(Path(golden_path).read_text())
    results = []

    for qa in golden:
        # Run the pipeline
        response = pipeline.query(
            question=qa["question"],
            context_override=qa.get("context"),  # Optional: use golden context
        )

        # Score each metric
        result = {
            "id": qa["id"],
            "faithfulness": score_faithfulness(response.answer, response.context),
            "relevancy": score_relevancy(response.answer, qa["question"]),
            "context_precision": score_precision(response.context, qa["context"]),
            "domain_check": domain_check(response.answer, qa["metadata"]),
        }
        results.append(result)

    return aggregate(results)


def score_faithfulness(answer: str, context: list[str]) -> float:
    """What fraction of answer claims are supported by context?"""
    answer_words = set(normalize(answer).split()) - STOP_WORDS
    context_words = set(normalize(" ".join(context)).split())
    if not answer_words:
        return 1.0
    supported = sum(1 for w in answer_words if w in context_words)
    return supported / len(answer_words)


def aggregate(results: list[dict]) -> dict:
    """Compute mean, min, max, and std for each metric."""
    if not results:
        return {}

    metrics = {}
    for key in results[0]:
        if key == "id":
            continue
        values = [r.get(key) for r in results if isinstance(r.get(key), (int, float))]
        if not values:
            continue
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        metrics[key] = {
            "mean": mean,
            "min": min(values),
            "max": max(values),
            "std": variance ** 0.5,
        }
    return metrics
```

## 4. Integration with SDLC Pipeline

### Stage 4 (Testing)
- Generate `data/golden_qa_set.json` from architecture docs
- Run evaluation script after E2E tests pass
- Include metrics in `stage-4-validation.md`

### Stage 5 (Review)
- Include evaluation metrics in PR description
- Flag any metric below threshold as a review finding

### Continuous (Post-Launch)
- Run evaluation on every deployment
- Track metric trends over time
- Alert on regression (metric drops > 10% from baseline)

## 5. Anti-Hallucination Patterns

### Grounding Check

```python
def is_grounded(response: str, context: list[str], threshold: float = 0.3) -> bool:
    """Verify response content words overlap with context."""
    response_words = set(normalize(response).split()) - STOP_WORDS
    context_words = set(normalize(" ".join(context)).split())
    if not response_words:
        return True
    overlap = sum(1 for w in response_words if w in context_words)
    return (overlap / len(response_words)) >= threshold
```

### Source Attribution

Every claim in the response should trace back to a specific retrieved chunk:
```json
{
  "answer": "You are taking metformin 500mg twice daily.",
  "citations": [
    {"chunk_id": "c-001", "source_type": "fhir", "text": "MedicationRequest: metformin 500mg BID"}
  ]
}
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Manual testing is sufficient" | Manual testing doesn't scale and misses regressions. Automate it. |
| "15 test cases is enough" | 15 is enough for a demo. Production needs 100+ for statistical significance. |
| "Faithfulness > 0.5 is acceptable" | 0.5 means half the answer is potentially fabricated. Target > 0.8. |
| "We'll add evaluation after the MVP" | Without evaluation, you don't know if the MVP works. It's not optional. |

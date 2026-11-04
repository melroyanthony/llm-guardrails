---
name: rag-patterns
description: |
  Production-grade RAG architecture patterns: hybrid retrieval, pluggable backends, token budget
  context windowing, guardrails pipeline, and evaluation framework.
  Use when building retrieval-augmented generation pipelines or knowledge base search.
  Triggers on: RAG, retrieval, embedding, vector, chatbot, knowledge base, search + generate.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, WebFetch
---

# RAG Architecture Patterns

Production-grade patterns for Retrieval-Augmented Generation systems, extracted from real-world implementations.

## Architecture Overview

```
Query → Embed → Retrieve (hybrid) → Rerank → Budget Context → Generate → Guardrails → Response
```

## 1. Hybrid Retrieval (Vector + BM25)

Semantic search alone misses exact-match requirements. Combine both strategies:

### When to Use Hybrid
- Domain-specific terminology (medical codes, legal citations, product IDs)
- Mixed query types (natural language + exact identifiers)
- Any domain where exact-match precision matters alongside semantic understanding

### Implementation Pattern

```python
class HybridRetriever:
    def retrieve(self, query: str, filters: dict, top_k: int = 20) -> list[Result]:
        # 1. Vector search: semantic similarity
        vector_results = self._vector.retrieve(query, filters, top_k=top_k)

        # 2. BM25 search: keyword/exact match
        bm25_results = self._bm25.retrieve(query, filters, top_k=top_k)

        # 3. Merge + deduplicate by source_id
        merged = self._merge_and_deduplicate(vector_results, bm25_results)

        return merged
```

### Score Normalization
- Normalize each strategy independently to 0..1 (min-max per result set)
- Prevents one strategy from dominating the merged results
- On duplicate (same `source_id` from both), keep the higher normalized score

## 2. Pluggable Backend Architecture

Swap entire components via environment variables — zero code change:

### Factory Pattern
```python
def create_vector_db(settings: Settings) -> BaseVectorDB:
    match settings.vector_backend:
        case "chroma":    return ChromaVectorDB(settings)
        case "s3vectors": return S3VectorsVectorDB(settings)
        case "pgvector":  return PgVectorDB(settings)
        case _: raise ValueError(f"Unknown backend: {settings.vector_backend}")
```

### Registry Pattern (for extensible loaders)
```python
_REGISTRY: dict[str, type[BaseDataLoader]] = {}

def register_loader(source_type: str):
    def decorator(cls):
        _REGISTRY[source_type] = cls
        return cls
    return decorator

@register_loader("pdf")
class PDFLoader(BaseDataLoader): ...

def get_loader(source_type: str) -> BaseDataLoader:
    return _REGISTRY[source_type]()
```

### Abstract Base Classes

Define these interfaces — all backends must implement them:

| Interface | Methods |
|---|---|
| `BaseVectorDB` | `create_collection`, `upsert_documents`, `query`, `delete_collection`, `list_collections` |
| `BaseEmbedder` | `embed_query`, `embed_documents`, `get_dimensions` |
| `BaseGenerator` | `generate(system_prompt, context, question)` |
| `BaseReranker` | `rerank(query, results, top_k)` |

## 3. Token Budget Context Windowing

Prevent LLM timeouts by capping context size:

```python
def budget_context(chunks: list[str], max_tokens: int = 3000) -> list[str]:
    """Include chunks up to token budget. Always include at least 1 when chunks are available."""
    if not chunks:
        return []  # No chunks available — nothing to budget

    budgeted = []
    remaining = max_tokens

    for chunk in chunks:
        estimated_tokens = len(chunk.split()) * 1.3  # Conservative estimate
        if estimated_tokens <= remaining:
            budgeted.append(chunk)
            remaining -= estimated_tokens
        elif not budgeted:
            # Always include at least 1 chunk (truncated if needed)
            words = chunk.split()[:int(remaining / 1.3)]
            budgeted.append(" ".join(words))
            break
        else:
            break

    return budgeted
```

### Key Rules
- 1 word ≈ 1.3 tokens (conservative for English)
- Always include at least 1 chunk when chunks are available (empty input returns `[]`)
- Make `max_tokens` configurable (default 3000)
- Truncate by words, not characters (preserves semantic boundaries)

## 4. Guardrails Pipeline

Apply safety checks to every LLM response before the user sees it:

```python
def apply_guardrails(response: str, context: list[str]) -> tuple[str, bool]:
    # Layer 1: PII/PHI redaction (defense-in-depth)
    cleaned = redact_sensitive_data(response)

    # Layer 2: Topic restriction
    if contains_denied_topic(cleaned):
        return (DENIAL_MESSAGE, False)

    # Layer 3: Grounding check (anti-hallucination)
    if not is_grounded(cleaned, context, threshold=0.3):
        return (UNGROUNDED_MESSAGE, False)

    return (cleaned, True)
```

### Grounding Check
- Extract content words from response (remove stop words)
- Calculate overlap ratio with context words
- Threshold: 30% overlap = grounded (tune per domain)
- Below threshold = likely hallucination, reject response

### Guardrail Composition
- Each guardrail is independent (can be added/removed)
- Pipeline short-circuits on first failure
- Always apply redaction first (defense-in-depth)

## 5. Graceful Degradation Chains

Define fallback chains for each component:

| Component | Primary | Secondary | Tertiary |
|---|---|---|---|
| Embedder | Bedrock Titan V2 | sentence-transformers (local) | — |
| Generator | Bedrock Claude | Anthropic API (direct) | Mock response |
| PII Detection | Comprehend Medical | Regex patterns | Skip with WARNING |
| Reranker | Cohere Rerank | Cross-encoder (local) | Return vector results |

### Rules
- Use WARNING logs for expected failures (not ERROR)
- Mock responses for dev/test when APIs are unavailable
- Document why each fallback is acceptable
- Test fallback paths explicitly

## 6. Evaluation Framework (RAGAS)

### Golden Test Set Design
```json
{
  "question": "What medications am I currently taking?",
  "expected_answer": "Based on your records, you are taking metformin 500mg...",
  "context": ["FHIR MedicationRequest resource..."],
  "metadata": {"source_type": "fhir", "patient_id": "test-patient-1"}
}
```

### Metrics
| Metric | Measures | Target |
|---|---|---|
| Faithfulness | Answer uses only retrieved context | > 0.8 |
| Answer Relevancy | Answer addresses the question | > 0.8 |
| Context Precision | Retrieved chunks are relevant | > 0.7 |
| Context Recall | All relevant info was retrieved | > 0.7 |
| Domain-specific | PII leakage, topic compliance | 0 violations |

### Minimum Coverage
- 15 Q&A pairs for MVP / demo
- 100+ for production deployment
- Cover all data sources and query types
- Include adversarial queries (injection attempts, out-of-scope)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Vector search alone is good enough" | It misses exact-match queries (codes, IDs, drug names). Add BM25. |
| "We don't need guardrails for internal use" | Internal users still see hallucinations. Grounding checks prevent confident wrong answers. |
| "Token budgeting is premature optimization" | One oversized context = one LLM timeout = one failed request. Budget from the start. |
| "Evaluation can wait until after launch" | Without metrics, you don't know if your RAG is retrieving well or just generating plausible text. |

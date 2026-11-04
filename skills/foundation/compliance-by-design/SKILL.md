---
name: compliance-by-design
description: |
  Architectural patterns for HIPAA, GDPR, and SOC2 compliance that are enforced by design —
  impossible to bypass, not bolted on as middleware afterthoughts.
  Use when building systems that handle PII, PHI, or require regulatory compliance.
  Triggers on: HIPAA, GDPR, SOC2, compliance, patient data, PII, PHI, data isolation, audit trail.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Compliance-by-Design

Compliance controls that are architecturally enforced — impossible to bypass, not optional middleware.

## Principle

If a compliance requirement can be violated by a developer forgetting to call a function, the architecture is wrong. Compliance must be structural, not procedural.

## 1. Mandatory Data Isolation

### Pattern: Identity from Token, Never from Input

```python
# CORRECT: Identity extracted from JWT (middleware-injected, not user-controlled)
def get_tenant_id(authorization: str = Header(...)) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    claims = decode_jwt(token)
    return claims["tenant_id"]  # Injected by auth provider

# WRONG: Identity from request body (user-controlled, spoofable)
def query(request: QueryRequest):
    results = db.query(tenant_id=request.tenant_id)  # NEVER DO THIS
```

### Enforcement Points

1. **Middleware**: Extract identity from authentication token (JWT, session)
2. **Dependency injection**: Inject identity into every data access function as a required parameter
3. **Database layer**: All queries include isolation filter (`WHERE tenant_id = ?`)
4. **Required parameter**: Identity is NOT optional — missing identity = 401, not unfiltered query

### Verification Test

```python
def test_zero_cross_tenant_leakage(db, embedder):
    """Verify that tenant A can NEVER see tenant B's data."""
    # Setup: 2 tenants with 2 documents each
    ingest(tenant_id="A", docs=["doc-A1", "doc-A2"])
    ingest(tenant_id="B", docs=["doc-B1", "doc-B2"])

    # Query as tenant A
    results = query(tenant_id="A", question="show me everything")

    # Assert: zero cross-tenant leakage
    leaked = [r for r in results if r.metadata["tenant_id"] != "A"]
    assert len(leaked) == 0, f"Cross-tenant leakage detected: {leaked}"
```

## 2. Sensitive Data Redaction Before Storage

### Pattern: Redact-Then-Store

```
Raw text → Redact PII/PHI → Embed/Index → Store
                                              ↑ PII never enters the store
```

### Implementation

```python
def ingest_document(text: str, metadata: dict) -> None:
    # Step 1: Redact BEFORE embedding (PII never enters vector store)
    redacted = redact_pii(text)

    # Step 2: Embed the redacted text
    embedding = embedder.embed(redacted)

    # Step 3: Store redacted text + embedding
    vector_db.upsert(text=redacted, embedding=embedding, metadata=metadata)
```

### Detection Layers

| Layer | Tool | Environment | Patterns |
|---|---|---|---|
| Primary | AWS Comprehend Medical / Google DLP | Production | ML-based entity detection |
| Fallback | Regex patterns | Dev/Test | SSN, phone, email, MRN, DOB |
| Defense-in-depth | Post-generation redaction | All | Re-scan LLM output before returning to user |

### Regex Fallback Patterns

```python
PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    (r"\b\d{3}-\d{3}-\d{4}\b", "[REDACTED_PHONE]"),
    (r"\bMRN[:\s]*\d+\b", "[REDACTED_MRN]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[REDACTED_DOB]"),
]
```

## 3. Guardrails Pipeline

Post-generation safety checks applied to every output:

```python
def apply_guardrails(response: str, context: list[str]) -> tuple[str, bool]:
    # Layer 1: Re-redact PII (defense-in-depth — LLM may reconstruct from context)
    cleaned = redact_pii(response)

    # Layer 2: Topic restriction (deny list for out-of-scope responses)
    if is_denied_topic(cleaned):
        return (DENIAL_MESSAGE, False)

    # Layer 3: Grounding check (response must reference retrieved context)
    if not is_grounded(cleaned, context):
        return (UNGROUNDED_MESSAGE, False)

    return (cleaned, True)
```

## 4. Audit Trail

| Requirement | Implementation |
|---|---|
| All data access logged | Structured log entry per query: identity, timestamp, action, resource |
| No PII in logs | Redact before logging (same PII patterns as storage) |
| Immutable storage | CloudTrail (AWS), Cloud Audit Logs (GCP), append-only table |
| Retention period | Configurable per compliance framework (HIPAA: 6 years, GDPR: varies) |

## Compliance Framework Mapping

| Pattern | HIPAA | GDPR | SOC2 |
|---|---|---|---|
| Data isolation | Patient isolation (45 CFR 164) | Tenant isolation (Art. 25) | Access control (CC6.1) |
| PII redaction | PHI de-identification | Data minimization (Art. 5) | Data classification (CC6.5) |
| Audit trail | Access logs (45 CFR 164.312) | Processing records (Art. 30) | Monitoring (CC7.2) |
| Auth enforcement | BAA requirement | Consent management (Art. 7) | Authentication (CC6.1) |
| Encryption at rest | Required (45 CFR 164.312) | Required (Art. 32) | Required (CC6.1) |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll add compliance controls before launch" | Retrofitting compliance onto existing architecture costs 10x. Design it in from Stage 2. |
| "This is just a prototype, compliance doesn't apply" | Prototypes with real data need real compliance. If you touch PII, you need isolation. |
| "The middleware handles it" | If the middleware can be bypassed by a direct function call, it's not enforcement — it's a suggestion. |
| "We only need compliance for production" | Dev environments with real data copies need the same isolation guarantees. |

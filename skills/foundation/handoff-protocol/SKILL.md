---
name: handoff-protocol
description: |
  Structured handoff protocol for inter-agent communication. Defines the contract for how agents
  pass context, decisions, and artifacts between pipeline stages.
  Use when transitioning between pipeline stages or passing work between agents.
  Triggers on: "handoff", "inter-agent", "stage transition", "pass context", "agent contract".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Inter-Agent Handoff Protocol

## Handoff Document Format

Every agent must produce a handoff document when completing its stage:

```markdown
# Handoff: {source_agent} → {target_agent}
## Stage: {stage_number} — {stage_name}
## Status: COMPLETE | PARTIAL | BLOCKED
## Timestamp: {ISO 8601}

### Context
Brief summary of what was accomplished and the overall approach taken.

### Key Decisions
| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| {what} | {chosen option} | {why} | {other options and why not} |

### Artifacts Produced
| File | Purpose | Status |
|------|---------|--------|
| {path} | {description} | {complete/partial/placeholder} |

### Validation Results
- {check}: {PASS/FAIL} — {details}

### Open Questions
- {question}: {context and impact if unresolved}

### Definition of done
- {observable outcome the next agent must reach}

### Constraints
- {constraint that limits acceptable solutions}

### Hypothesis (non-binding)
- {labelled guess, or "none" — the next agent may discard it}

### Risks & Concerns
- {risk}: {severity} — {mitigation suggestion}
```

## Handoff Validation Rules

Before accepting a handoff, the receiving agent MUST verify:

1. **All required artifacts exist** and are non-empty
2. **Status is COMPLETE** (PARTIAL handoffs require orchestrator approval)
3. **No CRITICAL open questions** that block the next stage
4. **Validation results show no failures** on required criteria

## Stage-Specific Handoff Requirements

### Stage 1 → Stage 2 (PM → Architect)
Required artifacts:
- `requirements.md` with numbered requirements
- `mvp-scope.md` with acceptance criteria
- RICE scores for all features
- MoSCoW categorization

### Stage 2 → Stage 3 (Architect → Developers)
Required artifacts:
- `openapi.yaml` with all MVP endpoints
- `database-schema.md` with tables, relationships, indexes
- `system-design.md` with component diagram
- At least 2 ADRs (tech stack + key design decision)

### Stage 3 → Stage 4 (Developers → Tester)
Required artifacts:
- Working backend with all MVP endpoints
- Working frontend with all MVP pages
- `docker-compose.yml` that builds successfully
- Both Dockerfiles building without errors

### Stage 4 → Stage 5 (Tester → Finalization)
Required artifacts:
- All tests passing (unit + E2E)
- `stage-4-validation.md` with test report
- Docker Compose stack starts and stays healthy
- E2E happy path script executes successfully

## Outcome handoffs

Give the next agent the symptom, how to reproduce it, the constraints, and the definition of done. Decisions already made stay in Key Decisions. A root-cause guess is a hypothesis the receiver may discard. Do not prescribe the patch.

When the work already has an owner (an agent and a branch), follow up with that owner. Start a new agent only when the owner is gone or the work is unrelated.

## Handoff Best Practices
- **Be explicit about what's incomplete**: Don't hide partial work
- **Include exact file paths**: Not "the API file" but `solution/backend/app/api/routes.py`
- **Document failed approaches**: What was tried and why it didn't work
- **Provide runnable commands**: Not "run tests" but `cd solution/backend && uv run pytest -q`
- **Flag breaking changes**: If a decision changes the API contract, call it out prominently

## Requirement Evolution Process

When new requirements are discovered during implementation:

### Step 1: Document the Discovery
Create a GitHub issue:
```bash
gh issue create \
  --title "REQUIREMENT: <what was discovered>" \
  --label "feature" \
  --body "## Discovery
<How this was found during implementation>

## Impact
<What changes if we don't address this>

## Proposed Change
<What to implement>

## Acceptance Criteria
- [ ] <criterion>"
```

### Step 2: Update Requirements Docs
- Add to `solution/requirements/requirements.md` as a new FR or HR (hidden requirement)
- Update `solution/requirements/mvp-scope.md` if scope changes
- Create or update ADR if a design decision is needed

### Step 3: Implement with Traceability
- Reference the issue in commits: `Refs #N`
- Add test cases validating the new requirement
- Update checkpoint validation

### Step 4: Close the Loop
- Close the issue when the fix is merged
- Update the stage checkpoint document

### Example
```
Discovery: <requirement found during implementation> (Issue #N)
  → Updated requirements.md with FR-XXX
  → Created ADR-NNN (<decision title>)
  → Added test: test_<behavior_under_test>
  → Updated stage-2.5 checkpoint
  → Closed Issue #N with PR #M
```

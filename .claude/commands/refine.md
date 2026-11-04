---
description: "Pre-pipeline ideation: diverge → converge → refine problem statement"
argument-hint: "[path to problem file]"
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, WebFetch, WebSearch, AskUserQuestion
model: opus
---

# Refine

Structured divergent→convergent thinking to transform a vague problem statement into a refined, stress-tested proposal with explicit scope boundaries. Run this BEFORE `/orchestrate`.

## Input

$ARGUMENTS — path to problem file. Defaults to `problem/PROBLEM.md` if not provided.

## Phase 1: Understand the Problem

1. Read the problem file thoroughly
2. Identify:
   - **Core need**: What is the user actually trying to achieve?
   - **Constraints**: Time, budget, team size, infrastructure, compliance
   - **Ambiguities**: What's unclear or could be interpreted multiple ways?
   - **Hidden assumptions**: What does the problem take for granted?

Output a brief problem digest:
```
Core need: [1 sentence]
Constraints: [list]
Ambiguities: [list — these become questions for Phase 3]
Hidden assumptions: [list]
```

## Phase 2: Diverge (Expand)

Generate 5-8 distinct solution approaches. Each approach should differ meaningfully, not just in technology choice:

| # | Approach | Architecture | Trade-off |
|---|----------|-------------|-----------|
| 1 | Monolith MVP | Single FastAPI app + PostgreSQL | Fast to build, harder to scale |
| 2 | Serverless event-driven | Lambda + DynamoDB + SQS | Zero idle cost, cold starts |
| 3 | Managed platform | Supabase/Firebase + React | Fastest, vendor lock-in |
| 4 | API-first headless | FastAPI + OpenAPI, frontend later | Backend solid, no user-facing demo |
| 5 | Existing solution + glue | Combine 2-3 SaaS APIs | Least code, most dependencies |

For each, note:
- Time to MVP (hours)
- Biggest risk
- What it optimizes for (speed, cost, scalability, simplicity)

### "How Might We" Questions
Generate 3-5 reframing questions:
- "How might we solve this without a database?"
- "How might we make this work for 10x the expected users?"
- "How might we deliver value with half the features?"

## Phase 3: Resolve Ambiguities

For each ambiguity identified in Phase 1, present options to the user:

```
Ambiguity: "The problem mentions 'real-time' but doesn't specify latency requirements."
Options:
  A) Sub-second (WebSocket, SSE) — adds complexity
  B) Near-real-time (polling every 5s) — simple, good enough for most cases
  C) Batch (process every N minutes) — simplest, may not meet expectations

Recommendation: B — unless the problem explicitly requires sub-second updates.
```

Use `AskUserQuestion` for critical ambiguities that materially affect architecture.

## Phase 4: Converge (Focus)

Evaluate the top 3 approaches against constraints:

| Criterion | Weight | Approach A | Approach B | Approach C |
|---|---|---|---|---|
| Time to MVP | 30% | 8/10 | 6/10 | 9/10 |
| Scalability | 20% | 5/10 | 9/10 | 3/10 |
| Simplicity | 20% | 7/10 | 4/10 | 8/10 |
| Cost | 15% | 6/10 | 9/10 | 7/10 |
| Extensibility | 15% | 7/10 | 8/10 | 4/10 |

Select the approach with the highest weighted score, with a brief justification for why it wins.

## Phase 5: Stress Test

Ask these questions about the selected approach:
1. **What breaks at 10x scale?** — Identify the first bottleneck
2. **What's the hardest part?** — Identify the highest-risk component
3. **What happens if a key dependency is unavailable?** — Fallback strategy
4. **What's the simplest version that still delivers value?** — Absolute minimum scope
5. **What would make us throw this away and start over?** — Identify invalidating assumptions

## Phase 6: Output

Write `problem/REFINED.md` with:

```markdown
# Refined Problem Statement

## Core Need
[1-2 sentences — the essential problem, stripped of solution bias]

## Selected Approach
[Approach name + 1-paragraph justification]

## Scope

### Doing (MVP)
- [Feature 1]
- [Feature 2]
- ...

### Not Doing (Explicit Exclusions)
- [Excluded feature 1] — why excluded
- [Excluded feature 2] — why excluded

### Deferred (Post-MVP)
- [Deferred feature 1] — when to revisit
- [Deferred feature 2] — when to revisit

## Constraints
- [Constraint 1]
- [Constraint 2]

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| [Risk 1] | High/Med/Low | High/Med/Low | [Mitigation strategy] |

## Resolved Ambiguities
| Question | Decision | Rationale |
|---|---|---|
| [Ambiguity 1] | [Decision] | [Why] |

## Stress Test Results
- 10x scale bottleneck: [what breaks first]
- Highest-risk component: [what's hardest]
- Minimum viable scope: [absolute minimum that delivers value]
```

Commit the refined problem statement:
```bash
git add problem/REFINED.md
git commit -m "docs(stage-0): refine problem statement

Selected approach: [approach name]
MVP scope: [N] features, [M] explicit exclusions
Key risks: [top 2 risks]"
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The problem is clear, we can skip refinement" | If it takes 10 minutes to refine and saves 2 hours of building the wrong thing, that's a 12x return. |
| "We don't have time to explore 5 approaches" | You don't have time to build the wrong approach. 15 minutes of divergent thinking prevents days of rework. |
| "The Not Doing list is unnecessary" | Without explicit exclusions, scope creeps silently through every stage. |
| "Stress testing is overkill for an MVP" | Knowing what breaks at 10x tells you what to architect carefully now vs what to defer. |

## Red Flags

- Only 1-2 approaches generated (not enough divergence)
- No "Not Doing" list (scope will creep)
- No risks identified (every project has risks)
- Ambiguities resolved by assumption instead of asking the user
- Selected approach is "the obvious one" without evaluating alternatives

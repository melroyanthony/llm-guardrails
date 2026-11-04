# Prioritization Deep Dive

## Framework Selection

Choose the right framework based on problem context:

| Context | Recommended Framework | Reason |
|---------|----------------------|--------|
| Time-constrained (2-4h) | RICE + MoSCoW | Quick, actionable |
| Multiple stakeholders | Weighted Scoring | Different value perspectives |
| Technical complexity | ICE (Impact, Confidence, Ease) | Engineering-focused |
| User-facing product | KANO Model | User satisfaction focus |

## RICE Deep Dive

### Reach Scoring Guide

| Score | Meaning | Example |
|-------|---------|---------|
| 10 | All users, every session | Login functionality |
| 8 | Most users, frequently | Dashboard view |
| 6 | Many users, sometimes | Report generation |
| 4 | Some users, occasionally | Admin features |
| 2 | Few users, rarely | Edge case handling |

### Impact Scoring Guide

| Score | Meaning | Example |
|-------|---------|---------|
| 3.0 | Massive - product doesn't work without it | Core CRUD operations |
| 2.0 | High - significantly improves experience | Real-time updates |
| 1.0 | Medium - noticeable improvement | Better error messages |
| 0.5 | Low - nice to have | UI polish |

### Confidence Scoring Guide

| Score | Meaning | When to use |
|-------|---------|-------------|
| 100% | High - done this before, clear requirements | Standard patterns |
| 80% | Medium - some unknowns but manageable | Familiar domain, new tech |
| 50% | Low - significant unknowns | New domain, experimental |

### Effort Estimation

Use T-shirt sizes mapped to hours:

| Size | Hours | Example |
|------|-------|---------|
| XS | 0.5-1h | Add a field, minor UI change |
| S | 1-2h | Simple CRUD endpoint |
| M | 2-4h | Feature with validation logic |
| L | 4-8h | Complex feature with multiple components |
| XL | 8h+ | Break this down further |

## MoSCoW Decision Tree

```
Is the product usable without this feature?
├── No → MUST HAVE
└── Yes
    └── Does it significantly improve the core experience?
        ├── Yes → SHOULD HAVE
        └── No
            └── Does it add polish or handle edge cases?
                ├── Yes → COULD HAVE
                └── No → WON'T HAVE
```

## Common Prioritization Mistakes

### 1. Everything is Must-Have
**Problem**: No real prioritization
**Solution**: If everything is Must-Have, nothing is. Be ruthless.

### 2. Underestimating Effort
**Problem**: Optimistic estimates lead to overscoping
**Solution**: Add 50% buffer to all estimates

### 3. Ignoring Dependencies
**Problem**: Can't build feature B without feature A
**Solution**: Map dependencies, order accordingly

### 4. Not Documenting Won't-Haves
**Problem**: Looks like oversight, not decision
**Solution**: Explicitly document what you're not building

## Value vs Effort Matrix

Plot all features on a 2x2 grid:

```
         High Value
             │
   Quick     │    Big Bets
   Wins ★    │    (commit fully)
   DO FIRST  │    PLAN CAREFULLY
             │
─────────────┼─────────────
             │
   Fill-ins  │    Money Pits
   (time     │    (avoid/defer)
   permitting│    DOCUMENT WHY NOT
             │
         Low Value
    Low Effort     High Effort
```

**How to use:**
1. Score each feature on Value (1-10) and Effort (1-10)
2. Plot on the matrix
3. Work through quadrants in order: Quick Wins → Big Bets → Fill-ins → (skip Money Pits)

## Kano Model

Classify features by how they affect user satisfaction:

| Category | Absent | Present | Strategy |
|----------|--------|---------|----------|
| **Basic** (expected) | Strong dissatisfaction | Neutral | Must implement — users won't thank you but will punish absence |
| **Performance** (linear) | Proportional dissatisfaction | Proportional satisfaction | More = better, optimize for time |
| **Delighter** (unexpected) | No effect | Disproportionate satisfaction | High ROI if quick to implement |
| **Indifferent** | No effect | No effect | Skip entirely |
| **Reverse** | Satisfaction | Dissatisfaction | Avoid — actively harms some users |

**Kano questionnaire approach:** For each feature, ask:
1. "How would you feel if this feature were present?" (functional)
2. "How would you feel if this feature were absent?" (dysfunctional)

Cross-reference answers to classify.

## Impact Mapping

Connect features to measurable outcomes:

```
WHY?     →  Business Goal: [measurable objective]
WHO?     →  Actors: [users/stakeholders who influence the goal]
HOW?     →  Impacts: [behavior changes needed from actors]
WHAT?    →  Deliverables: [features/capabilities that cause impacts]
```

**Key insight:** Multiple deliverables can achieve the same impact. Choose the simplest one.

## Assumption Mapping

| Quadrant | Known | Unknown |
|----------|-------|---------|
| **High Impact** | Validate early, design for | **CRITICAL**: Spike/prototype immediately |
| **Low Impact** | Proceed with confidence | Monitor, don't invest in validation |

For each high-impact unknown:
- Can you build a 30-minute spike to validate?
- Can you design the system to be flexible if the assumption is wrong?
- What's the cost of being wrong vs the cost of validating?

## Critical Evaluation Checklist

Before finalizing prioritization, verify:

- [ ] **No "everything is Must-Have" syndrome** — Must-Haves should be ≤40% of total features
- [ ] **Dependencies are mapped** — No feature depends on something lower-priority
- [ ] **Effort estimates include buffer** — Add 50% to all estimates for unknowns
- [ ] **Won't-Haves are documented** — Explicit exclusions show mature thinking
- [ ] **Assumptions are surfaced** — Each risky assumption has a validation plan
- [ ] **Happy path is clear** — Can trace a complete user journey through Must-Haves only
- [ ] **Technical feasibility confirmed** — No Must-Have depends on unknown/unproven tech
- [ ] **Evaluation criteria mapped** — Each evaluator criterion maps to at least one Must-Have

## Interview Challenge Specific

For take-home challenges, prioritize:

1. **What evaluators explicitly asked for** (reread the brief!)
2. **What demonstrates core competency** (data modeling, API design)
3. **What shows product thinking** (trade-off documentation)
4. **What makes the app actually work** (happy path first)

General interview tips:
- End users work under pressure → UX matters
- Evaluators assess data handling → model carefully
- They want to see prioritization → document decisions

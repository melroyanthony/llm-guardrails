---
name: grilling
description: |
  Relentless interview loop that resolves every branch of a decision tree before building.
  Use when a plan, design, or idea is underspecified and must be sharpened with the human.
  Triggers on: "grill", "interview me", "stress-test", "are we sure", "decision tree".
---

# Grilling

Reusable interview loop behind `/grill` and other alignment flows. One question at a time until every decision branch is resolved.

## Rules

1. **Recommend an answer** for each question — never lazy open-ended prompts.
2. **Explore the codebase** before asking the human when code/docs can answer.
3. **Ask one question at a time.** Wait for the response.
4. **Walk the design tree** — high-level first, then drill; resolve dependencies as you go.
5. **Push back on vagueness** — "it depends" is not done until dependencies are named and resolved.
6. **Track decisions** in a running summary.

## Process

### 1. Understand
Read the plan/spec/conversation context and related code. List major decision branches.

### 2. Interrogate
For each branch:

```
Question: [specific decision]
My recommendation: [concrete suggestion]
Why: [brief rationale]
```

Record agreement, or dig until resolved.

### 3. Summarize

```markdown
## Decisions Made
| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|

## Open Questions
- …

## Next Steps
- …
```

## Completion criterion

Every identified decision branch has a recorded choice, or an explicit open question with an owner.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We can figure it out while coding" | Misalignment is cheapest to fix before code |
| "Ask everything at once" | Batching buries dependencies; one at a time |

## Verification

- [ ] Recommended answers provided for each question
- [ ] Codebase checked before human questions where possible
- [ ] Decision table written

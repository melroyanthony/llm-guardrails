---
name: ask-sdlc
description: Router over user-invoked SDLC flows — pick the right skill for the situation.
disable-model-invocation: true
---

# Ask SDLC

Help the human choose the right **user-invoked** flow. Recommend one primary skill and optional model-invoked companions.

## Router

| Situation | Invoke |
|-----------|--------|
| Unclear what they want / need alignment | Load `grilling` (or `/grill`) |
| Conversation already aligned → write a spec | `/to-spec` → `to-spec` |
| Spec/plan → work items with blockers | `/to-tickets` → `to-tickets` |
| Tickets/spec ready to build | `/implement` → `implement` |
| Issue or external PR needs a state and a brief | `/triage` → `triage` |
| Work bigger than one session; path unclear | `/wayfinder` → `wayfinder` |
| Full greenfield from problem statement | `/orchestrate` (Stages 0–5) |
| Only need TDD discipline mid-change | model skill `tdd` |
| Terminology / domain drift | model skill `domain-modeling` |
| Module boundaries / deep design | model skill `codebase-design` |
| Authoring skills | `/` or load `writing-great-skills` |

## Process

1. Ask what outcome they need (one question) if unclear.
2. Recommend **one** user-invoked skill with rationale.
3. List model-invoked skills that skill should load.
4. Stop — do not start the other user-invoked skill yourself; tell the human to invoke it (or the matching slash command).

## Verification

- [ ] Single primary recommendation
- [ ] No user-invoked → user-invoked chain executed by this skill

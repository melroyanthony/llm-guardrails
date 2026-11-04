---
name: to-tickets
description: Break a plan or spec into tracer-bullet tickets with explicit blocking edges.
disable-model-invocation: true
---

# To Tickets

Turn a spec/plan into vertical-slice tickets. Prefer end-to-end slices over horizontal layers (API-only, UI-only).

## Process

1. Read the spec/plan (path from user or recent `to-spec` output).
2. Identify tracer bullets — each ticket delivers a thin slice of user-visible value or a necessary investigation.
3. For each ticket declare:
   - Title + outcome
   - Acceptance criteria
   - Seams under test
   - Blocked-by / blocks edges
   - AFK (agent-safe) vs HITL (needs human)
4. Publish tickets:
   - GitHub issues with blocking links when `gh` is available, **or**
   - Local file `docs/tickets/<slug>.md` / `solution/docs/tickets.md`
   - When the repo has `scripts/github-delivery.py`, follow `github-delivery` for labels and the project board. Do not publish packages.
5. Order by critical path (unblockers first).

## Ticket template

```markdown
### T-<n>: <title>
- **Outcome:** …
- **Acceptance:** …
- **Seams:** …
- **Blocked by:** …
- **Blocks:** …
- **Class:** AFK | HITL
```

## Completion criterion

Every acceptance criterion from the spec maps to ≥1 ticket; every ticket has blocker edges; first ticket is unblocked.

## Next

Recommend `/implement` for the first unblocked AFK ticket — do not run it yourself.

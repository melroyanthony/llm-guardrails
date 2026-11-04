---
name: to-spec
description: Turn the current conversation into a spec artifact. No interview — synthesize what was already decided.
disable-model-invocation: true
---

# To Spec

Synthesize an already-discussed change into a durable spec. If alignment is missing, tell the user to run `/grill` first — do not start grilling from here.

## Process

1. Collect decisions from the conversation (and any grill summary).
2. If critical branches are unresolved, **stop** and recommend `/grill`.
3. Ask which modules/seams this change touches (brief).
4. Write the spec to:
   - Daily: `docs/specs/<slug>.md` or path the user names
   - Pipeline: `solution/requirements/` or `solution/docs/architecture/` as appropriate
5. Optionally open/update a tracker issue if the project uses GitHub issues.

## Spec shape

```markdown
# <Title>

## Problem
## Goals / Non-goals
## Decisions
## Seams / Modules touched
## Acceptance criteria
## Out of scope
## Open questions
```

When a flow, sequence, or state is clearer than a paragraph, add a fenced `mermaid` block in the spec. Follow the `diagrams` skill, and change that block when the behavior it describes changes.

## Completion criterion

Spec file exists with acceptance criteria that a stranger could implement; unresolved questions are explicit.

## Next

Recommend `/to-tickets` to break the spec into tracer-bullet work — do not run it yourself.

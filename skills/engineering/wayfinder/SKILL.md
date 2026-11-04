---
name: wayfinder
description: Plan work larger than one session as a map of investigation tickets until the path is clear.
disable-model-invocation: true
---

# Wayfinder

For fog-of-war work: you do not yet know enough to write an implementation spec. Create a **map of investigation tickets**, resolve them one at a time, then graduate to `to-spec` / `to-tickets`.

## Process

1. State the destination outcome in one sentence.
2. List unknowns that block a confident design (each becomes an investigation ticket).
3. Publish investigation tickets (local doc or GitHub) with:
   - Question to answer
   - Method (read code, spike, prototype, research)
   - Done when (evidence)
   - Blocked-by edges
4. Resolve the highest-leverage unblocked investigation (read/spike only — avoid production code).
5. Update the map; repeat until the path to an implementation spec is clear.
6. Recommend `/to-spec` when unknowns are closed enough — do not run it yourself.

## Completion criterion

Destination sentence stable; remaining unknowns documented; enough answers exist to write a spec without guessing critical branches.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Just start coding and discover" | Wayfinder exists so discovery is tracked and resumable across sessions |
| "One giant research spike" | Prefer small investigation tickets with evidence |

## Verification

- [ ] Map artifact written
- [ ] Each investigation has a done-when
- [ ] Next action is a single unblocked ticket or `/to-spec`

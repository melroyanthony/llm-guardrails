---
name: implement
description: Implement work from a spec or tickets using TDD at agreed seams, then review before commit.
disable-model-invocation: true
---

# Implement

Build the work described by a spec or ticket set.

## Process

1. Read the target ticket(s)/spec and the surrounding code. Confirm scope with the user if ambiguous.
2. Agree **seams** under test before writing tests.
3. Drive **`tdd`**: red → green per vertical slice. For a bug, the failing test must fail on the current code and pin that bug. Load `skills/foundation/tdd/SKILL.md`.
4. Make the smallest change that meets the acceptance criteria. Match existing patterns. Leave drive-by refactors out. Handle edge cases explicitly. A TODO stays only when it links an issue.
5. Run typecheck, lint, and the relevant tests before pushing. Run the full suite once at the end.
6. For a UI or behavior change, verify the flow and attach evidence (screenshot, recording, or command output).
7. Apply **`codebase-design`** when adding a non-trivial module.
8. Review on two axes — Standards and Spec fidelity. Spawn `code-reviewer`, or follow its checklist. Report the axes separately so one cannot hide the other (Matt Pocock's `code-review`, MIT).
9. Commit on the current branch with the hybrid subject in `git-workflow` (`✨ feat(scope): ...`). One logical change.

## Rules

- One ticket at a time unless the user asks for a batch.
- Do not expand scope past acceptance criteria.
- Prefer vertical slices over horizontal layers.
- If confidence in the cause is low, stop and report findings. Load `debugging` instead of shipping a guess.
- Ask before merging, deleting data or branches, force-pushing, changing production config, or sending a message as someone else.
- State what you ran and what you did not verify. A claim of success needs the command output from this session (Jesse Vincent, `verification-before-completion`, MIT, https://github.com/obra/superpowers).

## Completion criterion

Acceptance criteria met; tests green at agreed seams; review findings addressed or explicitly deferred with a reason; commit created when the user wants one. The report names the real state (drafted, open, blocked) and the checks that were and were not run. Merging is a separate decision.

## Next

If more tickets remain, stop and report the next unblocked ticket — do not auto-chain another user-invoked skill.

# AGENTS.md

Portable instructions for Claude Code, Cursor, Codex, Copilot, and other Agent Skills hosts. This file is the source of truth for the catalog, the pipeline, and how changes land.

**Version:** see `.version`

## What this repository is

`llm_guardrails` is a Python library. The Rust crate in `src/` implements PII redaction, prompt-injection scoring, bias scoring, and output validation, and PyO3 exports it as `llm_guardrails._core`. The modules under `llm_guardrails/` are thin wrappers. `api/` is a FastAPI demo that calls `GuardrailsPipeline`. It does not call a model.

Do not rename the import `llm_guardrails` or the distribution name in `pyproject.toml`. Do not publish to PyPI from this tree. The demo does not read `.env-template`.

This is an existing library. Use the daily engineering flow. Do not create a greenfield `solution/` tree here.

## Build and check

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pytest
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
python3 scripts/release_subject.py --self-test
python3 scripts/release_publish.py --self-test
```

Python is installed with uv. `.python-version` is 3.14. CI also runs 3.11. Rust comes from `rust-toolchain.toml`.

## Catalog

One real tree: `skills/{foundation,meta,engineering,generated}/<name>/SKILL.md`. Edit there. Skill names are unique.

`.claude/skills/<name>` is a symlink to `skills/<category>/<name>`. That is the only committed discovery root.

Cursor loads `.agents/skills/`, `.cursor/skills/`, and for compatibility `.claude/skills/` and `.codex/skills/` ([docs](https://cursor.com/docs/skills)). Copilot loads `.github/skills/`, `.claude/skills/`, or `.agents/skills/` ([cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)). Neither documents de-duplication. This repo does not commit `.agents/skills/`, `.cursor/skills/`, or `.github/skills/`.

Codex auto-loads `.agents/skills/` and follows symlinks ([docs](https://developers.openai.com/codex/skills)). It does not read `.claude/skills/`. This repository does not vendor `scripts/install-harness.sh`. For a local Codex tree, symlink each `skills/<category>/<name>` to `.agents/skills/<name>`. `.gitignore` ignores that directory. With the tree present, Cursor and Copilot list each skill twice. Without it, open `skills/<category>/<name>/SKILL.md` from the table. Codex still reads this file.

Claude Code discovers `.claude/skills/<name>/SKILL.md`. It does not scan `.agents/skills/` or a category directory under `.claude/skills/`.

## Product posture

| Mode | When | Entry |
|------|------|--------|
| Greenfield pipeline | New app from a problem statement | Stages 0–5, `skills/meta/orchestrator/SKILL.md`, `/orchestrate` |
| Daily engineering | Change on an existing codebase | grill → to-spec → to-tickets → implement |

When an intent matches, load that skill.

## Intent → skill

| Intent | Skill | Invocation |
|--------|-------|------------|
| Unsure which flow to use | `engineering/ask-sdlc` | user |
| Align on a plan / design | `engineering/grilling` (via ask or `/grill`) | model |
| Build shared domain language | `engineering/domain-modeling` | model |
| Deepen module boundaries | `engineering/codebase-design` | model |
| Turn discussion into a spec | `engineering/to-spec` | user |
| Break work into tracer tickets | `engineering/to-tickets` | user |
| Implement tickets/spec with TDD | `engineering/implement` | user |
| Triage an issue or PR into an agent brief | `engineering/triage` | user |
| Multi-session unknown path | `engineering/wayfinder` | user |
| Test-first implementation | `foundation/tdd` | model |
| Debug / root-cause | `foundation/debugging` | model |
| Opt-in stack guardrails (uv, ruff, TypeScript, Railway, changesets) | `foundation/stack-guardrails` | model |
| GitHub issues, project board, labels, docs site | `foundation/github-delivery` | model |
| Mermaid for architecture, flows, sequences, or state | `foundation/diagrams` | model |
| Full greenfield pipeline | `meta/orchestrator` | user (`/orchestrate`) |
| Quality gate between stages | `meta/judge` | model / command |
| Author or edit skills | `meta/writing-great-skills` | user |
| Review loop through squash-merge | `foundation/review-loop-to-squash-merge` | model |

## Core behaviours

1. **Surface assumptions** before non-trivial work.
2. **Stop on confusion.** Name the conflict. Do not pick an interpretation in silence.
3. **Push back** with a concrete downside and an alternative.
4. **Scope discipline.** Touch only what the task requires. Do not reformat neighbours, add features you were not asked for, or delete comments you did not write.
5. **Verification.** Build, typecheck, lint, and test before claiming done. Read the output. Say what ran and what did not. If a tool or fact is missing, say so. For a UI change, exercise the flow.
6. **Security.** No secrets in code or logs. Validate inputs at boundaries.
7. **Own the loop.** A coordinating session is done when the pull request is merged, the work is abandoned, or the human takes it back.
8. **Commit subject.** `<emoji> <type>(<scope>): <lower-case imperative>`. Under 72 characters. No trailing period. The body says why. No `Co-authored-by` or `Generated with` trailer. Commit a meaningful unit when it is green.
9. **Pull request.** The title uses that subject. One label: `feature`, `bug`, `refactor`, `upgrade`, `docs`, `internal`, `breaking`, or `security`. Link `Closes #N`. Include evidence and whether the change is reversible. Add a diagram when the architecture or the data flow changes.
10. **Merge.** Required CI is green and the independent reviewer has confirmed the current full head SHA, or the lead has waived a hold on that SHA. A new push needs a new confirmation. A reviewer hold blocks the merge until it is fixed or the lead waives that SHA. Before squash-merge, append `Reviewed by <reviewer> at \`<full sha>\`` and the findings. `<reviewer>` is the Independent reviewer named under `## Review`. A waiver appends `Lead waived the hold at \`<full sha>\`` and the findings instead. When the human asks, use `gh pr merge <number> --squash --delete-branch`. The commit on `main` is the pull request title plus ` (#N)`. GitHub still allows merge commits and rebase, and it does not delete the head branch on its own. The loop is `skills/foundation/review-loop-to-squash-merge/SKILL.md`.
11. **Ask first** before merging, deleting, force-pushing, changing production config, or sending a message as someone else. Do not force-push a shared branch or skip hooks unless the human says so.
12. **Hand off** symptoms, a repro, constraints, and done. Label a root-cause guess as a hypothesis. Do not start the next pipeline stage without the judge or the human. Prefer the simplest change that meets the requirement.

## Review

Agreed 2026-11-03 by Melroy and the Engineering Lead.

- Independent reviewer: the team's SWE reviewer
- GitHub login:
- Channel: the team room
- Lead: the Engineering Lead

The author mentions the independent reviewer in that channel with the pull request link and the full head SHA. That request is not confirmation. Confirmation is a message from that reviewer, in the channel, that quotes the full head SHA and explicitly confirms it. A hold or a request-changes message does not confirm. A blank GitHub login is fine. The loop is `skills/foundation/review-loop-to-squash-merge/SKILL.md`.

## Stack and dependency guardrails

Opt-in stack checks live in `skills/foundation/stack-guardrails/SKILL.md`. The same Python pin is repeated in that skill and in `.claude/commands/upgrade.md`. Cursor, Copilot, and Codex read this file; their adapters point here instead of copying the rule.

A dependency sweep takes libraries and language runtimes to the latest stable release. Python is the exception: it is pinned to 3.14 (Melroy's decision, 2026-10-24, agreed by EL and SWE) because wheels for 3.15 are still catching up. The decision treated 3.15 as only at 3.15.0 and set the revisit at 3.15.1 or 3.15.2. python.org published 3.15.1 on 2026-10-21. The pin stays until that revisit is recorded. Until then, a dependency sweep must not bump `requires-python`, `.python-version`, `python-version` for `astral-sh/setup-uv` or `actions/setup-python`, or Ruff `target-version` past 3.14.

Rust is the stable channel in `rust-toolchain.toml`, with rustfmt and clippy. CI passes that channel into `dtolnay/rust-toolchain` because the action is pinned by commit SHA.

## Pipeline

The greenfield pipeline reads `problem/PROBLEM.md` and writes `solution/`. This repository is not that pipeline. Between stages of a pipeline that does run, the judge proceeds at 70 or above, asks for a revision from 50 through 69, and escalates below 50. Entry for a new app: `skills/meta/orchestrator/SKILL.md`.

## Layout

```
src/                 Rust core (PyO3 cdylib)
llm_guardrails/      Python wrappers and GuardrailsPipeline
api/                 FastAPI demo
tests/               pytest
skills/              canonical skill tree
.claude/skills/      symlinks into skills/
```

Harness notes for the conf live in its `docs/harness/`. Prefer a `SKILL.md` at or under 350 lines. Above 500 lines is a failure.

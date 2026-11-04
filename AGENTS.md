# AGENTS.md

Guidance for any coding agent or contributor working in this repository. Tool-agnostic:
nothing here is specific to a particular assistant. Claude Code loads it through `CLAUDE.md`.

## What this repository is

`llm-guardrails` is a Python library with a Rust core. The import name is `llm_guardrails`
and the distribution name in `pyproject.toml` is `llm_guardrails`. Do not rename either.

The Rust crate `llm-guardrails-core` (`src/`) implements PII redaction, prompt-injection
scoring, bias scoring, and output validation. PyO3 exports that crate as `llm_guardrails._core`.
The modules under `llm_guardrails/` are thin wrappers. `api/` is a FastAPI demo, not a second
implementation of the guards.

This is an existing library. Work it as daily engineering: grill, spec, tickets, implement.
Do not scaffold a greenfield `solution/` tree, and do not treat the demo API as an application
framework.

## Layout

| Path | Purpose |
| --- | --- |
| `src/` | Rust core and `cargo test` |
| `llm_guardrails/` | Python wrappers and `GuardrailsPipeline` |
| `api/` | FastAPI demo (`uvicorn api.main:app`) |
| `tests/` | pytest, against the built extension |
| `scripts/release_subject.py` | Classifies a squash subject and consumes `## Unreleased` |
| `.github/workflows/` | CI, security, CodeQL, release pull requests |
| `.claude/` | Skills, agents, and commands for this repo |

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
10. **Merge.** When the human asks, use `gh pr merge <number> --squash --delete-branch`. The commit on `main` is the pull request title plus ` (#N)`. GitHub still allows merge commits and rebase, and it does not delete the head branch on its own.
11. **Ask first** before merging, deleting, force-pushing, changing production config, or sending a message as someone else. Do not force-push a shared branch or skip hooks unless the human says so.
12. **Hand off** symptoms, a repro, constraints, and done. Label a root-cause guess as a hypothesis. Do not start the next pipeline stage without the judge or the human. Prefer the simplest change that meets the requirement.

When an intent matches a skill under `.claude/skills/`, load that skill. A success claim needs
command output from this session. A forge refusal is the result: report it and do not route
around it. Red CI blocks a pull request. Read the log and do not blind re-run.

## Commands

Python is installed with uv. The committed interpreter pin is `.python-version` (`3.14`).
CI also runs 3.11. Do not select a Python newer than that pin, and do not add a
`requires-python` upper bound. Rust comes from `rust-toolchain.toml` (`stable`, with rustfmt and clippy).

```bash
uv sync --locked --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pytest
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
python3 scripts/release_subject.py --self-test
```

`uv sync` builds the PyO3 extension through maturin. pytest imports `llm_guardrails._core`,
so a sync has to succeed before the tests can pass. `cargo test` covers the Rust functions
without the Python wrappers.

## Code conventions

- **Rust.** `cargo fmt` and `cargo clippy --all-targets -- -D warnings` must pass. Fallible
  library paths return `Result`. `Regex::new(...).unwrap()` inside a `Lazy` static is the
  exception already in the tree: a broken pattern is a compile-time mistake, not a runtime
  input. Do not add `unwrap` on I/O or on caller input. Keep `pyo3`'s `extension-module`
  feature where `Cargo.toml` sets it so maturin can build the cdylib.
- **Python.** uv only, never pip or poetry, for installs, locks, and tools. Ruff is the
  linter and formatter (`target-version = "py311"`, line length 100). Wrappers stay thin:
  detection logic belongs in `src/`. Prefer pydantic models for results that cross the API
  boundary. Tests are pytest, arranged as the existing files are.
- **Boundaries.** The demo reads constructor arguments on `GuardrailsPipeline`. It does not
  load `.env-template`. Do not document those variables as live configuration unless a change
  actually reads them.
- **Comments** explain constraints and intent, never what the next line does.
- **Dependencies.** A crate or package earns its place by removing a real problem. Lockfiles
  (`uv.lock`, `Cargo.lock`) stay committed. Do not hand-edit them.

## Security

No hard-coded secrets. No `eval` of model output. The guards are regex and heuristic checks.
They are not a complete control against prompt injection, bias, or hallucination, and they do
not make a deployment HIPAA or GDPR compliant by themselves. PII mappings live in process
memory and are returned to the caller. Do not log the mapping or the original text.

JSON checks in the output validator look at top-level `type` and `required` only. Do not
describe that as full JSON Schema.

## Commit messages

Conventional Commits with a leading gitmoji, in the style of tiangolo's repositories:

```
<emoji> <type>(<scope>): <imperative, lower-case subject>
```

Emoji first, then the Conventional Commits header. Imperative mood, lower case, no trailing
period, under 72 characters. The body explains why. Breaking changes take a `!` or a
`BREAKING CHANGE:` footer. No `Co-authored-by` or "Generated with" trailer.

| Type | Emoji | Release |
| --- | --- | --- |
| `feat` | ✨ | minor |
| `fix` | 🐛 | patch |
| `docs` | 📝 | patch |
| `style` | 🎨 | patch |
| `refactor` | ♻️ | patch |
| `perf` | ⚡️ | patch |
| `test` | ✅ | patch |
| `build` | 📦 | patch |
| `ci` | 👷 | patch |
| `chore` | 🔧 | patch |
| `deps` | ⬆️ | patch |
| `security` | 🔒️ | patch |
| `revert` | ⏪️ | patch |

A `!` or a `BREAKING CHANGE:` footer is major. `chore(release):` does not release again.
Other emoji are fine when they describe the change better, with the same type: 🔥 🚚 🚨 💚 🎉 🔖.

Scopes: `core`, `api`, `ci`, `docs`, `deps`, `release`, `agents`, `security`. Omit the scope
when a change is genuinely repo-wide.

Examples:

```
✨ feat(core): redact credit-card numbers before the prompt is scored
🐛 fix(api): return the bias flags on /guard/output
👷 ci: add ruff and cargo test workflow
```

## Pull requests

Title is the commit subject. One logical change. Body:

- **What and why**, with `Closes #N` when an issue exists.
- **Evidence.** Before, after, and what was not verified.
- **Merge danger.** One-way or two-way door, blast radius, rollback.
- **Breaking changes, migrations, config.**

A diagram belongs in the body when the architecture or the data flow changes.

Branches: `feat/issue-N-short-name` or `fix/issue-N-short-name`, or the `cursor/<topic>-*`
branch this agent was given. Keep the branch current with `main`. Never force-push. Never
push to `main`.

## Releases

`.version` is the current release (`0.2.0` today). `CHANGELOG.md` starts with an empty
`## Unreleased` section. Put human notes there. On push to `main`,
`.github/workflows/release.yml` classifies the squash subject with
`scripts/release_subject.py`. A releasable commit opens a pull request from `release/vX.Y.Z`
that moves `## Unreleased` into the new version. Merging that pull request tags `vX.Y.Z`.
The workflow does not push to `main`. Publishing to PyPI is a separate change. The import
name stays `llm_guardrails`.

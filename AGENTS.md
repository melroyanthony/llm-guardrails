# AGENTS.md

Guidance for any coding agent or contributor working in this repository.
Tool-agnostic: nothing here is specific to a particular assistant.

## What this repository is

`llm_guardrails` is a Python library. The Rust crate in `src/` implements PII
redaction, prompt-injection scoring, bias scoring, and output validation, and
PyO3 exports it as `llm_guardrails._core`. The modules under `llm_guardrails/`
are thin wrappers. `api/` is a FastAPI demo that calls `GuardrailsPipeline`.
It does not call a model, and it does not read `.env-template`.

Do not rename the import `llm_guardrails` or the distribution name in
`pyproject.toml`. Do not publish a wheel from this tree.

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

When an intent matches a skill under `.claude/skills/`, read that skill before acting. User-invoked skills do not chain into another user-invoked skill.

## Library conventions

- **Rust.** `cargo fmt` and `cargo clippy --all-targets -- -D warnings` must pass. Guard behaviour lives in `src/`. Fallible paths return `Result`. `Regex::new` inside a `Lazy` static may panic: a bad pattern is a programmer error. Do not add `unwrap` on caller input.
- **Python.** Wrappers stay thin. Detection logic does not move back into `llm_guardrails/`. Tooling is `uv` only. Ruff lints and formats. `target-version` is `py311`.
- **API.** `api/main.py` calls `GuardrailsPipeline`. It does not grow its own checks and it does not load environment variables.
- **Release.** A releasable push to `main` commits the version bump and publishes the tag in one run. The highest bump since the last tag wins. `chore(release)` does not bump again. The job pushes that commit to `main` without force, then pushes the tag. It does not publish a wheel.

## Delivery process

**Roles.** Melroy (owner) sets direction and makes the owner-only calls: credentials, repo settings, licensing, and anything public, costly, or irreversible. Engineering Lead owns scope, priorities, merge order, and tie-breaks, and does not write code. Shipwright executes: specs, issues, cloud agents, the Copilot loop, squash-merge, releases, and dependency upkeep. SWE is the independent reviewer and CI diagnostician. Its findings go to the channel in Second-reviewer gate, not GitHub, unless the owner says otherwise.

**PR flow.**

1. Open the PR and run the Copilot review loop until CI is green and Copilot's review of the head commit is clean, with zero unresolved threads.
2. When the Second-reviewer gate applies, post the PR link and head SHA, plus the major-bump commit SHAs with package and from/to versions, and hold the merge until that reviewer confirms that exact SHA. A new head needs a fresh confirmation. A hold blocks the merge until it is fixed or the project lead waives it.
3. Squash-merge with the title `<emoji> type(scope): subject (#N)`, delete the branch, and let the release workflow cut the version.
4. Escalate to Engineering Lead after 5 Copilot rounds or a disagreement. Only owner-only items go to the owner.

**Dependencies.** Keep libraries and the Rust toolchain at the latest stable for the current month. Use one PR per ecosystem. Dependabot runs weekly and grouped. Python is pinned to 3.14 until EL/Melroy revisit at 3.15.1+; deps sweeps must not bump `requires-python`, `.python-version`, `python-version` for `astral-sh/setup-uv`, or Ruff `target-version` past 3.14. CI also runs 3.11.

## Second-reviewer gate

- Reviewer: SWE (independent reviewer bot)
- Channel: the melroyanthony/llm-guardrails group chat
- Scope: file format, wire contract, auth or secrets, or a major dependency bump (conf default)
- Project lead: Engineering Lead
- Tie-breaker: Engineering Lead

## Commit messages

Conventional Commits with a leading gitmoji, in the style of tiangolo's repositories:

```
<emoji> <type>(<scope>): <imperative, lower-case subject>
```

| Type | Emoji | Use for |
| --- | --- | --- |
| `feat` | ✨ | New capability |
| `fix` | 🐛 | Bug fix |
| `refactor` | ♻️ | Behaviour-preserving restructuring |
| `perf` | ⚡️ | Performance work |
| `docs` | 📝 | Documentation |
| `test` | ✅ | Tests |
| `ci` | 👷 | GitHub Actions and other CI config |
| `build` | 📦 | Build pipeline |
| `chore` | 🔧 | Tooling and config that is none of the above |
| `deps` | ⬆️ | Dependency bumps |
| `style` | 🎨 | Formatting only |
| `revert` | ⏪️ | Reverts |
| `security` | 🔒️ | Security hardening |

Other emoji are fine where they describe the change better, keeping the same type: 🔥 removing code, 🚚 moving or renaming, 🚨 fixing warnings, 💚 fixing CI, 🎉 initial commit, 🔖 a release commit.

Scopes are warn-level in `.commitlintrc.json`. `feat` bumps minor. A `!` before the colon, or a footer line that starts with `BREAKING CHANGE: ` or `BREAKING-CHANGE: ` followed by text, bumps minor while the version is below 1.0, and major from 1.0.0 up. A mention in prose or backticks does not. The changelog section is still Breaking changes. Every other type above bumps patch, including `test`, `ci`, `docs`, and `chore`.

## Commands

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
python3 scripts/test_guardrails.py
```

## Layout

| Path | Purpose |
| --- | --- |
| `src/` | Rust core, exported through PyO3 |
| `llm_guardrails/` | Python wrappers and `GuardrailsPipeline` |
| `api/` | FastAPI demo |
| `tests/` | pytest |
| `scripts/` | Release classifier and harness checks |
| `.github/workflows/` | CI at the repository root |
| `.claude/` | Slim agent harness: two skills, agents, commands, hooks |

## Harness provenance

The full skill catalog lives in `melroyanthony/sdlc-claude-code-conf` and is
installed per user or as a plugin. It is not copied into this repository. A
second skill tree would make Cursor and Copilot list every skill twice.

`.claude/skills/` holds the two skills this repo runs. `.cursor/skills/` and
`.agents/skills/` are symlinks to those directories, not copies.

When you have a local checkout of the conf, refresh a review copy with:

```bash
scripts/install-harness-from.sh /path/to/sdlc-claude-code-conf
```

That script copies the checkout into `.claude/upstream/` for review. It does not replace `.claude/` or `AGENTS.md`. Read its header before you run it.

Known harness bugs this repo does not repeat:

- Workflows live at `.github/workflows/`, not `solution/.github/workflows/`.
- `uv.lock`, `Cargo.lock`, and `.claude/` are committed. They are not gitignored.
- The release job pushes the version commit to `main` without force, then tags that commit. It does not rewrite a plugin manifest and it does not publish a wheel.
- Claude settings do not pre-approve `curl`, `kubectl`, `helm`, or `terraform`.

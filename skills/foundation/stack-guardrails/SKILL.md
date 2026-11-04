---
name: stack-guardrails
description: |
  Opt-in per-stack guardrails, Claude Code hooks, and a read-only verify harness.
  Use when a repo uses changesets, uv, ruff, TypeScript 7 or tsgo, nvm, Railway, pnpm, biome, pyright, or mypy.
  Triggers on: "stack guardrails", "uv lock", "ruff", "tsgo", "tsc", "nvmrc", "railway", "changesets", "biome", "pyright".
---

# Stack guardrails

Opt-in checks for the tools a solution repo actually uses. The executable policy is `.claude/hooks/scripts/stack_guardrails.py`. This skill is the map. Hooks no-op until the repo opts in. They never push, force-push, publish, or deploy.

## Python 3.14 pin

Agents apply this pin during a sweep. The hooks leave version files alone. The wording matches `AGENTS.md` and `.claude/commands/upgrade.md`.

A dependency sweep takes libraries and language runtimes to the latest stable release. Python is the exception: it is pinned to 3.14 (Melroy's decision, 2026-10-24, agreed by EL and SWE) because wheels for 3.15 are still catching up. The decision treated 3.15 as only at 3.15.0 and set the revisit at 3.15.1 or 3.15.2. python.org published 3.15.1 on 2026-10-21. The pin stays until that revisit is recorded. Until then, a dependency sweep must not bump `requires-python`, `.python-version`, `python-version` for `astral-sh/setup-uv` or `actions/setup-python`, or Ruff `target-version` past 3.14.

## Opt in

Either of these turns the hooks on:

- `SDLC_STACK_GUARDRAILS=1` in the environment
- a committed empty file `.claude/stack-guardrails.enabled` at the git root

`SDLC_STACK_GUARDRAILS=0` forces them off. `SDLC_HOOK_PROFILE=minimal` skips the hook the same way the other hooks do. The shell checks both before it starts Python, so a repo that has not opted in does not crash on Python 3.9 or 3.10 (those releases have no `tomllib`). When the hook does run on 3.9 or 3.10, `[tool.uv]`, `[tool.ruff]`, `[tool.pyright]`, and `[tool.mypy]` are detected with a regex.

Run the harness any time, opted in or not:

```bash
bash .claude/hooks/scripts/stack-verify.sh
bash .claude/hooks/scripts/stack-verify.sh --railway-plan
```

`--railway-plan` is the only network call, and it is `railway config plan` (a preview). It does not apply.

## Levels

| Level | When | What the agent sees |
|---|---|---|
| Block (exit 2) | Deploy and publish commands. This blocks in **standard and strict**. Other hooks in this repo only block in strict; these commands are the exception because exit 0 would still deploy | Hook JSON `permissionDecision: deny`, plus the reason on stderr |
| Warn (exit 0) | Lockfile hand-edits and ruff on the saved file | Hook JSON `additionalContext`. stderr with exit 0 is not shown to the model |
| Strict | `SDLC_HOOK_PROFILE=strict` | Those warnings become blocks |

## Detection

The harness prints every marker it found. A stack that is not present is not checked.

Markers are read at the git root and, when those directories exist, in `solution/`, `solution/backend`, `solution/frontend`, `backend/`, `frontend/`, `server/`, `client/`, and one level under `packages/`, `apps/`, `services/`, `solution/packages/`, and `solution/apps/`. Pipeline apps keep their manifests in `solution/`, not the git root. The opt-in file stays at the git root.

| Stack | Applies when |
|---|---|
| changesets | `.changeset/config.json` |
| uv | `uv.lock` or `[tool.uv]` |
| ruff | `ruff.toml`, `.ruff.toml`, or `[tool.ruff]` |
| TypeScript | `typescript` in package.json, `@typescript/native-preview`, or `tsconfig.json` |
| nvm | `.nvmrc` or `.node-version` |
| pnpm | `pnpm-lock.yaml` or `packageManager` starts with `pnpm@` |
| biome | `biome.json` or `biome.jsonc` |
| pyright / mypy | `pyrightconfig.json`, `[tool.pyright]`, `[tool.mypy]` |
| Railway | `railway.toml`, `railway.json`, or `.railway/` |
| pre-commit | `.pre-commit-config.yaml` (reported, not executed) |

## Per stack

### changesets

Patterns from [changesets/changesets](https://github.com/changesets/changesets) (`changeset status` is the read-only check).

- Pre-commit / harness: `npx --no-install changeset status` in the directory that has `.changeset/config.json`
- Block: `changeset publish` (including `npx`, `pnpm exec`, `pnpm dlx`, `yarn`, `bunx`), plus `npm publish`, `pnpm publish`, `yarn publish`, `uv publish`. `npm publish --dry-run` (and the pnpm, yarn, and uv forms) is not a publish
- Failure: add a changeset with `npx changeset` if the change should release. Do not publish from the agent
- Not run: `changeset version` (it rewrites package versions)

### uv

Patterns from [astral-sh/uv](https://github.com/astral-sh/uv) (`uv lock --check`).

- Pre-edit: warn on a direct edit of `uv.lock`
- Harness: `uv lock --check`
- Failure: change `pyproject.toml` and run `uv lock`. Do not hand-merge the lock. This hook does not install uv

### ruff

Patterns from [astral-sh/ruff](https://github.com/astral-sh/ruff). Post-edit runs `ruff check <file>` only when `ruff` is already on PATH, the saved file is an existing `.py` file, and `ruff.toml`, `.ruff.toml`, or `[tool.ruff]` sits in that file's directory or a parent up to the git root. Timeout is 20s. `quality-gate.sh` may also lint Python when the binary exists; this hook is the one that stays quiet unless the project declared ruff.

- Harness: `ruff check .` and `ruff format --check .`. If `ruff` is not on PATH but `.venv` already exists, `uv run --frozen --no-sync ruff ...`. Otherwise the tool is reported missing. The harness does not sync and does not create `.venv` or `uv.lock`
- Failure: fix the printed rules. The hook does not pass `--fix` or `format` without `--check`, so it cannot loop on its own rewrite

### TypeScript 7 and tsgo

Checked against the [TypeScript 7.0 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/) (8 July 2026) and the typescript-go discussion where the `tsgo` name was retired.

- TypeScript **7.0 stable** (announced 8 July 2026) is the `typescript` package. The CLI is **`tsc`** (`npx tsc --noEmit`). It is not `tsgo`.
- **`tsgo`** is the binary from `@typescript/native-preview`, the pre-stable package. The TypeScript 7.0 announcement installs `typescript` and runs `npx tsc`. Ryan Cavanaugh, on [typescript-go#4576](https://github.com/microsoft/typescript-go/discussions/4576): the `tsgo` name is effectively gone once 7.0 is stable.
- Harness: `npx --no-install tsc --noEmit --pretty false` when `typescript` is 7 or newer, or when only `tsconfig.json` exists. `npx --no-install tsgo --noEmit` only when the preview package is installed and stable `typescript` 7 is not.
- The harness passes `--no-install`. It does not add the dependency.
- Post-edit does not typecheck the whole project (too slow for a hook). Use the harness.

### nvm and .nvmrc

Patterns from [nvm-sh/nvm](https://github.com/nvm-sh/nvm).

- The pre-commit hook does not compare Node. `node -v` in the hook process is not the nvm shell, and a mismatch used to block every commit in strict mode
- Harness only: compare the major of `node` on PATH to `.nvmrc` or `.node-version`, and print the mismatch. It does not block `git commit`
- Failure: `nvm use` in a shell that already has nvm. The harness does not run `nvm install`

### Railway

Patterns from Railway's config-as-code and infrastructure-as-code docs (checked October 2026).

- `railway.toml` / `railway.json` are deprecated config-as-code. Existing files keep working until **2026-12-01**. New work belongs in `.railway/railway.ts` (`.py` and `.go` are beta).
- Block, by argv of each shell segment (a quoted mention in `git commit -m` or `echo` is not a command): `railway up`, `railway deploy`, `railway redeploy`, `railway down`, `railway variables --set`, `railway config apply`, `railway config migrate --apply`. The same verbs via `npx`, `pnpm dlx`, or `bunx @railway/cli`. `railway config migrate` without `--apply` is left alone. `railway config plan` is left alone. `bash -c` / `sh -c` is the only place a quoted string is inspected
- Safe preview: `railway config plan`. The harness prints that command and runs it only with `--railway-plan`
- Static check: a secret-shaped assignment fails the harness. A deprecated `railway.toml` / `railway.json`, or a `.railway/` directory with no authoring file, is reported and does not fail the run
- The hook does not call the Railway API on save

### Related stacks

- **pnpm** ([pnpm/pnpm](https://github.com/pnpm/pnpm)): warn on a hand-edit of `pnpm-lock.yaml`. Harness runs `pnpm install --frozen-lockfile --ignore-scripts --offline --lockfile-only` when `pnpm` is on PATH. `--frozen-lockfile` is the CI check from the pnpm docs. `--lockfile-only` keeps it from writing `node_modules`. A failure means the lock is stale. Run `pnpm install` yourself and commit the lock. No network install from the hook.
- **biome** ([biomejs/biome](https://github.com/biomejs/biome)): harness runs `biome ci` (read-only). Not `biome check --write`.
- **pyright** ([microsoft/pyright](https://github.com/microsoft/pyright)) and **mypy**: harness only. The binary on PATH, or `uv run --frozen --no-sync` when `.venv` already exists. A missing tool is reported. Nothing is synced. Too slow for post-edit.
- **pre-commit** ([pre-commit/pre-commit](https://github.com/pre-commit/pre-commit)): if `.pre-commit-config.yaml` exists, the harness tells you to run `pre-commit run`. It does not execute the framework, because hooks there can rewrite files.

## What a hook must not do

- `git push`, `git push --force`, `railway up`, `railway config apply`, `changeset publish`
- install a missing toolchain (`nvm install`, `npm install`, `uv sync`, `pip install`)
- pass a fixer (`ruff check --fix`, `biome check --write`, `changeset version`)

Force-push and `--no-verify` are already handled by `git-guardrails.sh`, which is on whether or not stack guardrails are enabled.

## Failure output

Every failure line names the command that failed and the command a human runs next. A missing binary is a failure of the harness with an install pointer, not an automatic install.

## Verification

- [ ] Hooks exit 0 when neither the env var nor `.claude/stack-guardrails.enabled` is set
- [ ] `railway up` is blocked when guardrails are on
- [ ] `railway config plan` is not blocked
- [ ] `uv.lock` edits warn
- [ ] `python3 .claude/hooks/scripts/stack_guardrails.py --self-test` passes
- [ ] `stack-verify.sh` prints detected stacks and does not deploy

---
name: stack-guardrails
description: Opt-in blocks for publish and deploy, plus the uv, ruff, and cargo checks this library expects. Use before publishing, deploying, or changing the toolchain.
---

# Stack guardrails

Opt in by committing an empty `.claude/stack-guardrails.enabled` at the git root, or export `SDLC_STACK_GUARDRAILS=1`. This repository commits the marker, so the blocks are on.

The hook exits 2, in every profile, for:

- `npm publish`, `pnpm publish`, `yarn publish`, `uv publish`, `changeset publish` (a `--dry-run` is allowed)
- `railway up`, `deploy`, `redeploy`, `down`, `variables --set`, `config apply`, `config migrate --apply`

It warns on a hand edit of `uv.lock` or `pnpm-lock.yaml`. `Cargo.lock` is committed on purpose. Do not gitignore it. Regenerate `uv.lock` with `uv lock`, do not hand-edit it.

## Python and Rust

Python is 3.11 in CI and 3.14 in `.python-version`. Do not select a newer interpreter. Do not raise `requires-python`, the setup-uv `python-version`, or Ruff `target-version` past 3.14. Ruff's `target-version` is `py311`. Tooling is `uv`.

Lint and format with `uv run ruff check .` and `uv run ruff format --check .`. Test with `uv run pytest`.

Rust's bar is `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, and `cargo test`. The stable channel is `rust-toolchain.toml`. CI passes that channel into `dtolnay/rust-toolchain` because the action is pinned by commit SHA.

There is no TypeScript app and no Node toolchain.

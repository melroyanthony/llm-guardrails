---
name: stack-guardrails
description: Commands and files that must stay true for the uv and cargo toolchain. Use before adding a dependency, a workflow, or a publish step.
---

# Stack guardrails

This repo opts in by documenting the toolchain here. There is no separate enable file.

## Python

- uv only. Commit `uv.lock`. CI runs `uv sync --locked`.
- Interpreters: 3.11 in CI, 3.14 in `.python-version` and as the other CI cell. Do not go
  past that pin. `requires-python` is `>=3.11` with no upper bound.
- Ruff `target-version` is `py311`.
- Do not hand-edit `uv.lock`.
- Do not run `uv publish`. Publishing is out of scope until the PyPI name change is decided.

## Rust

- `rust-toolchain.toml` channel is `stable`, with rustfmt and clippy.
- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`.
- `Cargo.lock` stays committed.
- `deny.toml` is the license and advisory gate. A new license is a reviewed edit to `deny.toml`, not a warning to ignore.

## GitHub Actions

- Pin every action to a full commit SHA with a trailing version comment (`# v1.2.3`).
- Top of each workflow: `permissions: {}`. Each job sets the permissions it needs.
- Release automation pushes a release branch and a tag. It does not push to `main`.

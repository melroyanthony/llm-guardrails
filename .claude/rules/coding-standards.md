---
description: Size, typing, and test shape for Python and Rust
paths: "**/*.py, **/*.rs"
---

# Coding standards

- Functions stay within about 30 lines. Files stay within about 300 lines.
- No magic numbers. Name them.
- `TODO` comments name an issue: `TODO(#123)`.
- Python tooling is `uv` only. Ruff lints and formats. Scripts under `scripts/` that ship in CI are stdlib, so CI does not need a venv for those scripts.
- Rust: `cargo fmt` and `cargo clippy --all-targets -- -D warnings`. Guard logic stays in `src/`.
- Tests are arrange, act, assert. One assertion. No logic in the test.

There is no TypeScript in this repository.

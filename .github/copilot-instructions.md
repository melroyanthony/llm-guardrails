Read `AGENTS.md` and follow it. It is the operating manual for this repository.

Python tooling is uv and ruff. The import name is `llm_guardrails`. Rust lives in `src/` and is exported through PyO3. `cargo fmt` and `cargo clippy --all-targets -- -D warnings` must pass.

Workflows live in `.github/workflows/` at the repository root. The release workflow pushes the version commit to `main` without force, then tags that commit. The same run publishes the `ferroguard` wheels to PyPI. The import name stays `llm_guardrails`.

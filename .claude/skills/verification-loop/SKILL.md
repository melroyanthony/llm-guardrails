---
name: verification-loop
description: The six checks before a change is called done. Use before committing or opening a PR.
---

# Verification loop

Run the phases that the diff can affect. Record pass, fail, or not run, with the command.

1. **Build.** `uv sync --locked --all-extras`. That builds the PyO3 extension. `cargo check` when Rust changed and uv did not already compile it.
2. **Types.** No Python typechecker is configured. Do not add one as a drive-by. Rust types are the compiler.
3. **Lint.** `uv run ruff check .`, `uv run ruff format --check .`, `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`.
4. **Test.** `uv run pytest` and `cargo test`.
5. **Security.** `cargo deny check` when Rust deps changed. `uv export --frozen --all-extras --no-emit-project -o /tmp/requirements.txt` and `uvx pip-audit==2.9.0 -r /tmp/requirements.txt` when Python deps changed. No new secrets in the diff.
6. **Diff.** Read `git diff`. Confirm the import name is still `llm_guardrails`, the distribution name is still `llm_guardrails`, and no workflow or `requires-python` bound selects a Python newer than `.python-version`.

`python3 scripts/release_subject.py --self-test` when `scripts/release_subject.py`, `scripts/commit-types.json`, or `.commitlintrc.json` changed.

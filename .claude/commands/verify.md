---
description: Run the library verification loop and report each phase.
---

Run, in order, and record pass or fail from the command output:

1. `cargo fmt --check`
2. `cargo clippy --all-targets -- -D warnings`
3. `cargo test`
4. `uv run ruff check .`
5. `uv run ruff format --check .`
6. `uv run pytest`
7. `python3 scripts/release_subject.py --self-test`
8. `python3 scripts/release_publish.py --self-test`
9. `python3 scripts/test_guardrails.py`

Say what you did not run. Do not claim a phase passed without its output.

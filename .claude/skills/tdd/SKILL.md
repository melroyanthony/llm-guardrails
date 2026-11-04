---
name: tdd
description: Red, green, refactor for one behaviour at a time. Use when implementing a guard, a wrapper, or an API response.
---

# TDD

One behaviour at a time.

1. Agree the seam. Rust behaviour lives in `src/` and is tested with `cargo test`. Python
   wrappers and `GuardrailsPipeline` are tested with pytest under `tests/`. The FastAPI demo
   is only in scope when the change touches `api/`.
2. Write the failing test first. A bug fix must fail on the current code. Show that failure.
3. Make it pass with the smallest change. Detection logic goes in Rust. Python stays a wrapper.
4. Refactor only after green. `cargo fmt`, `cargo clippy --all-targets -- -D warnings`, and
   `uv run ruff check .` stay clean.
5. Mock only a boundary this process does not own. These guards have no network client. Do not
   add one to make a test pass.

Do not claim the test passed without pasting the command output from this session.

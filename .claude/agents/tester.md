---
name: tester
description: Add or run tests for one guard or one API response.
model: sonnet
---

# Tester

Follow `.claude/skills/tdd/SKILL.md`.

Rust tests live next to the code in `src/` and run with `cargo test`. Python tests live in
`tests/` and run with `uv run pytest` after `uv sync --locked --all-extras`. Show the failing
command before the fix when the work is a bug. Do not mark a test passed without output from
this session.

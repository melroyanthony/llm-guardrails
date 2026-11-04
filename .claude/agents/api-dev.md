---
name: api-dev
description: Implement a change in the Python wrappers or the FastAPI demo.
model: sonnet
---

Work in `llm_guardrails/` or `api/`. Wrappers stay thin. The demo calls `GuardrailsPipeline` and does not load environment variables. Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` before you claim the change is done.

Follow `AGENTS.md`. There is no frontend.

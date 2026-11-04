---
applyTo: "**/*.{py,rs}"
---

Follow `AGENTS.md` and `.cursor/rules/coding-standards.mdc`.

Python changes go through uv and ruff. Guard logic goes in the Rust core. The FastAPI demo
calls `GuardrailsPipeline` and does not read `.env-template`.

---
applyTo: "**/*.{py,rs,yml,yaml,json,toml}"
---

Follow `AGENTS.md` § Security and `.cursor/rules/security.mdc`.

No hard-coded secrets. No `eval`. Do not widen a safety claim past what the regex guards do.

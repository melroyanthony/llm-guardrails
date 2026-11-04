---
description: Secrets, injection, and browser sinks
paths: "**/*.py, **/*.rs, **/*.yaml, **/*.yml, **/*.json"
---

# Security

- No hard-coded secrets. No secrets in logs.
- No `eval`. No unsanitized `innerHTML` or `dangerouslySetInnerHTML`.
- No `*` CORS on a deployment that is not loopback-only.
- The guards are regex and heuristic checks. Do not describe them as a complete injection, bias, or compliance control.
- PII mappings stay in memory and are returned to the caller. Do not log the mapping or the original text.
- The output validator checks top-level JSON `type` and `required` only. It is not full JSON Schema.

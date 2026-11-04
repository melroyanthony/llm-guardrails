---
description: Review the diff for secrets, unsafe input handling, and over-claimed safety.
---

# Security review

Look for:

- secrets, tokens, or live PII in code, fixtures, or logs
- `eval`, shell injection, or unsanitized HTML in the demo
- a new crate or package with no `deny.toml` or audit story
- README or API copy that calls the regex guards a complete injection, bias, or HIPAA control

The output validator is not a full JSON Schema validator. Say so if a change implies it is.

Report findings by severity. Do not merge.

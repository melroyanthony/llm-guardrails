---
name: ai-integration
description: |
  Patterns for integrating LLM APIs: model selection, structured output, embeddings, and known API limitations.
  Use when calling OpenAI/Anthropic/other model APIs from application code.
  Triggers on: "LLM API", "OpenAI", "embeddings", "structured output", "gpt-", "chat completion".
---

# AI Model Integration

Guide application-code integration with LLM APIs (not agent model routing — see `meta/model-routing` for that).

## When to Use

- Choosing chat vs embedding models for a product feature
- Implementing structured JSON output from an LLM
- Handling reasoning-model API quirks (no system message, etc.)

## Reference

Load detailed model tables, code samples, and limitation notes from:

→ [`MODELS.md`](MODELS.md)

## Rules

1. Prefer structured output / JSON schema modes over brittle free-text parsing.
2. Validate and sanitize all model outputs at the trust boundary before persistence or tool use.
3. Never hardcode API keys — use environment variables / secret managers.
4. Log model name + request id for debugging; do not log full prompts if they contain PII.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll hardcode the model name for now" | Model IDs change; centralize in config |
| "Temperature doesn't matter" | Some models reject non-default temperature — check `MODELS.md` |

## Verification

- [ ] Model choice documented with cost/quality rationale
- [ ] Secrets not in source
- [ ] Output validated before use
- [ ] Limitations from `MODELS.md` checked for the chosen model

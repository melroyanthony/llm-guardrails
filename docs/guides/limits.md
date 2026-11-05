# Limits

Ferroguard is a library of heuristics. Use it as one check in your own system.

- It does not call a model, and it does not decide that a prompt or a reply is safe.
- It does not claim GDPR compliance, SOC 2 coverage, or a benchmark score.
- PII detection is regex and context rules. It misses text outside those rules and it can redact text you did not expect.
- Injection detection is a score over known patterns. Novel wording can score under `0.5` and still be unwanted.
- Bias scoring covers a few patterns. Silence is not evidence of fair output.
- Output validation is not a full schema language.

## HTTP demo

`api/` is a FastAPI app that calls `GuardrailsPipeline`. It is not a hosted service.

| Method | Path | Behaviour |
| --- | --- | --- |
| `GET` | `/health` | Status and the installed `ferroguard` version |
| `POST` | `/guard/input` | PII placeholders, an injection score, and an opaque `pii_mapping_id` |
| `POST` | `/guard/output` | Validation, bias score, and PII restore for that id |
| `POST` | `/guard/full` | Input guards, then a stub or a caller-supplied response, then output guards |

`text` is limited to 8000 characters (`422` above that). A body over 32768 bytes is `413`. `/guard/input` does not return the placeholder map. The map stays in that process for 15 minutes, or it is not stored when it is empty. The id is single-use: a second `/guard/output` is `404`. The store is not shared across workers and it is lost on restart. `/guard/full` does not store a map.

`GuardrailsPipeline` in Python still returns `pii_mapping` to the caller. Only the HTTP demo hides it.

This line is here so a narrow viewport can scroll the code block instead of the page:

```text
ferroguard-placeholder-token-<<EMAIL_1>>-continues-without-wrapping-the-whole-layout-on-a-narrow-screen
```

---
title: Ferroguard
hide:
  - navigation
  - toc
---

# Check a prompt before you send it.

Install the `ferroguard` package. Import `llm_guardrails`. The library redacts some PII, scores a few injection patterns, and runs a small set of output checks. It does not call a model.

```text
pip install ferroguard
```

The import name is `llm_guardrails`, not `ferroguard`.

```python title="quickstart.py"
--8<-- "examples/quickstart.py"
```

```text
Mail <<EMAIL_1>> about the notes.
blocked False
```

[Guards](guides/guards.md) · [What the checks leave out](guides/limits.md)

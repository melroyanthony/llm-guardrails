---
title: Ferroguard
hide:
  - navigation
  - toc
---

<div class="fg-hero" markdown="1">

<p class="fg-kicker">Python library</p>

# Check a prompt before you send it.

Install the `ferroguard` package. Import `llm_guardrails`. The library redacts some PII, scores a few injection patterns, and runs a small set of output checks. It does not call a model.

<div class="fg-install">
<code id="fg-install-cmd">pip install ferroguard</code>
<button type="button" id="fg-copy">Copy</button>
</div>

<p class="fg-note">The import name is <code>llm_guardrails</code>, not <code>ferroguard</code>.</p>

</div>

<div class="fg-stage" markdown="1">

```python title="quickstart.py"
--8<-- "examples/quickstart.py"
```

```text
Mail <<EMAIL_1>> about the notes.
blocked False
```

</div>

<div class="fg-features" markdown="1">

### Placeholders for some PII

Emails, phone numbers, and other built-in labels can become tokens such as `<<EMAIL_1>>`. A name or a date is redacted only when a context word sits next to it. Card numbers have to pass a Luhn check.

### A score for injection patterns

`GuardrailsPipeline` scores the sanitised prompt. The default block line is `0.5`. The score is a pattern match, not a proof that a prompt is safe.

### A few output checks

After a reply, the pipeline can restore placeholders, score a handful of bias patterns, and validate a small set of rules. Those checks are narrow on purpose.

</div>

<p class="fg-more"><a href="guides/limits/">What the checks leave out</a> · <a href="https://pypi.org/project/ferroguard/">PyPI</a> · <a href="https://github.com/melroyanthony/llm-guardrails">GitHub</a></p>

---
name: writing-great-skills
description: Reference for writing and editing skills well — vocabulary and principles that make a skill predictable.
disable-model-invocation: true
---

# Writing Great Skills

A skill wrangles determinism out of a stochastic system. **Predictability** — the agent taking the same *process* every run — is the root virtue.

**Bold terms** are defined in [`GLOSSARY.md`](GLOSSARY.md).

## Invocation

- **Model-invoked** — keep a trigger-rich `description`; omit `disable-model-invocation`. Pays **context load** (description always in the catalog).
- **User-invoked** — set `disable-model-invocation: true`; one-line human summary; strip trigger lists. Zero catalog context load; human pays **cognitive load**.

Pick model-invocation only when the agent must reach the skill alone, or another skill must. User-invoked skills may invoke model-invoked skills; never another user-invoked skill.

When user-invoked skills multiply, add a **router skill** (`ask-sdlc`) that names them.

## Writing the description

Model-invoked descriptions: state what the skill is, then list **branches** that should trigger it.

- Front-load the skill’s **leading word**.
- One trigger per branch — collapse synonym duplication.
- Do not put process steps in the description (agents may follow the summary and skip the body).
- Max 1024 characters.

User-invoked descriptions: one human-facing line. No “Use when…” / “Triggers on:” lists.

## Information hierarchy

1. **In-skill step** — ordered action with a checkable **completion criterion**.
2. **In-skill reference** — rules/facts consulted on demand.
3. **External reference** — sibling file via a **context pointer** (progressive disclosure).

Push branch-specific material behind pointers; keep what every branch needs inline.

## Size budget

| Tier | Limit |
|------|-------|
| Target | ≤350 lines in `SKILL.md` |
| Hard fail | >500 lines |

Move bulk into `references/` or named siblings (`PATTERNS.md`, `tests.md`). One level deep only.

## Recommended body sections

1. Overview
2. When to Use / When NOT
3. Core process (steps + completion criteria)
4. Common Rationalizations (excuse → reality table)
5. Red Flags
6. Verification checklist

## Failure modes

- **Premature completion** — vague exit criteria; sharpen them or split steps.
- **Duplication** — same meaning in two places; single source of truth.
- **Sediment** — stale layers; prune aggressively.
- **Sprawl** — too long even when live; disclose or split.
- **No-op** — line the model already obeys; delete.
- **Negation** — prefer positive target behavior over “don’t do X”.

## Verification

- [ ] Invocation mode chosen deliberately
- [ ] Description matches mode (triggers vs one-liner)
- [ ] Every step has a checkable completion criterion
- [ ] `SKILL.md` ≤500 lines
- [ ] No user-invoked → user-invoked dependency

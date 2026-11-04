---
name: domain-modeling
description: |
  Actively build and sharpen a project's domain model — glossary, edge cases, CONTEXT.md, and ADRs.
  Use when terminology drifts, ubiquitous language is unclear, or hard decisions need domain docs.
  Triggers on: "domain model", "glossary", "CONTEXT.md", "ubiquitous language", "terminology".
---

# Domain Modeling

Active discipline for shared language. Merely *reading* a glossary is not this skill — challenging terms, stress-testing edge cases, and updating docs inline is.

## Artifacts

| Artifact | Location (pipeline) | Location (daily) |
|----------|---------------------|------------------|
| Glossary | `solution/UBIQUITOUS_LANGUAGE.md` | `CONTEXT.md` at repo root (preferred for ongoing products) |
| ADRs | `solution/docs/decisions/ADR-*.md` | `docs/decisions/` or `solution/docs/decisions/` |

If `CONTEXT.md` exists, prefer it as the living domain doc. Also see `foundation/ubiquitous-language` for glossary extraction templates.

## Process

1. **Inventory terms** in requirements, code, and conversation.
2. **Challenge collisions** — same word, two meanings → rename or define NOT-list.
3. **Stress-test** with edge-case scenarios; update definitions when they break.
4. **Write/update ADR** for irreversible or contested decisions.
5. **Apply language** in new code/names in the same session.

## Completion criterion

Every contested term has a definition + NOT-list; ADRs cover decisions that are hard to reverse; new names in the change match the glossary.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll rename later" | Drift compounds across agents and PRs |
| "CONTEXT.md is enough without ADRs" | ADRs capture *why*; glossary captures *what words mean* |

## Verification

- [ ] Glossary/CONTEXT.md updated
- [ ] Ambiguities table current
- [ ] At least one edge-case scenario exercised against terms
- [ ] Related ADR written or linked when needed

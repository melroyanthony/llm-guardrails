---
name: diagrams
description: When to add a Mermaid diagram. Use when a change alters architecture or data flow.
---

# Diagrams

Add a Mermaid diagram to the pull request body, and to `README.md` when the picture there would
become false, when either of these changes:

- which component owns a guard (Rust core, Python wrapper, FastAPI demo)
- the order of pre-process or post-process steps

Use `flowchart` for ownership and `sequenceDiagram` for a request. Do not diagram a rename or
a lint fix. Keep labels to the names in the code: `PIIRedactor`, `InjectionDetector`,
`BiasScorer`, `OutputValidator`, `GuardrailsPipeline`.

---
name: codebase-design
description: |
  Shared discipline for designing deep modules — much behavior behind a small interface at a clean seam.
  Use when defining module boundaries, refactoring structure, or reviewing interface depth.
  Triggers on: "deep module", "module boundary", "seam", "interface design", "ball of mud".
---

# Codebase Design

Vocabulary and rules for keeping agent-accelerated codebases changeable. Inspired by Ousterhout’s deep modules: **a lot of behavior behind a small interface**.

## Leading words

| Term | Meaning |
|------|---------|
| **Deep module** | Simple interface, rich implementation |
| **Shallow module** | Interface complexity ≈ implementation complexity — usually a smell |
| **Seam** | Public boundary you test and depend on |
| **Adapter** | Thin translation at a seam to an external system |
| **Information hiding** | Secrets of the implementation stay inside the module |

## Process

1. Name the **seam** under design (API, package, component props).
2. List responsibilities that belong *behind* vs *outside* that seam.
3. Shrink the interface: fewer methods/params; more behavior inside.
4. Place adapters at the edge; keep domain logic deep.
5. Confirm the seam is testable without reaching into internals.

## When designing interfaces

- Prefer one obvious way to do the common case.
- Make illegal states unrepresentable at the type/schema layer.
- Do not leak storage/transport details through the seam.

## Completion criterion

The module’s public surface is listed; each public member earns its place; tests can target the seam without mocking internals.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Expose everything for flexibility" | Wide interfaces become shallow and fragile |
| "We'll clean boundaries after it works" | Entropy accelerates with agents — invest daily |

## Verification

- [ ] Seam named and documented
- [ ] Interface inventory reviewed for shallowness
- [ ] Tests planned at the seam

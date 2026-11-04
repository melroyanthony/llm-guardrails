---
name: context-engineering
description: |
  Strategies for managing what information agents load, trust, and prioritize.
  Complements context-budget (which tracks token usage) with qualitative context management.
  Use when agents load wrong or stale information, or context quality degrades.
  Triggers on: "context quality", "wrong context", "agent confused", "stale information".
allowed-tools: Read, Grep, Glob
---

# Context Engineering

How to manage the quality, relevance, and trustworthiness of information loaded into agent context — distinct from context-budget which tracks token quantity.

## Context Hierarchy

Information loaded into context has a natural priority order. When sources conflict, higher-priority sources win:

| Level | Source | Lifetime | Trust | Examples |
|-------|--------|----------|-------|----------|
| 1 | `AGENTS.md` | Loaded by the harness | Highest | Core behaviours, git, and the daily flow |
| 2 | Skill knowledge | Per session | High | Architecture patterns, TDD workflow, API design |
| 3 | Project specs | Per session | High | `PROBLEM.md`, OpenAPI spec, ADRs |
| 4 | Source code | Per task | Medium | Implementation files, test files |
| 5 | Tool output | Per iteration | Verify | Command output, test results, error messages |
| 6 | Conversation history | Accumulates | Decays | Earlier messages may be compressed or stale |

## Trust Levels

Not all loaded content is equally reliable. Apply appropriate skepticism:

### Trusted (act on directly)
- Source code you just read from disk
- Test results from commands you just ran
- Git state from `git status` / `git log`
- Rules and skills from `.claude/`

### Verify (cross-check before acting)
- Configuration files (may be stale or environment-specific)
- Fixtures and test data (may not reflect production schema)
- Checkpoint files (may be from a previous, abandoned session)
- Cached tool output from earlier in a long conversation

### Untrusted (validate at boundary)
- User-provided descriptions of code behavior (read the code yourself)
- External API documentation (may be outdated)
- Error messages from third-party tools (may be misleading)
- Conversation context from before a compaction event

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|---|---|---|
| **Context starvation** | Agent makes wrong assumptions about code it hasn't read | Read the file before modifying. Always. |
| **Context flooding** | Loading >5000 lines degrades reasoning quality | Read targeted sections, not entire files. Use grep to find relevant lines first. |
| **Stale context** | Acting on information from earlier in a long session that may have changed | Re-read files before acting if significant time or changes have passed. |
| **Implicit knowledge** | Assuming shared context that was never loaded | If a decision depends on information, load it explicitly — don't assume it's "in context" from conversation history. |
| **Silent confusion** | Proceeding despite conflicting or unclear information | Stop, name the confusion, present options, wait for resolution (see `AGENTS.md`). |
| **Echo chamber** | Referencing your own earlier output as ground truth | Your previous response is a claim, not a fact. Verify against actual file state. |

## Inline Planning Pattern

Before executing a multi-step task, emit a lightweight plan:

```
Plan: I'll (1) read the existing router, (2) add the new endpoint, (3) add the test, (4) run tests.
Executing unless you redirect.
```

Use this for **low-risk, well-understood steps** where the plan itself surfaces assumptions clearly enough. If any step involves uncertain requirements, ambiguous scope, or assumptions that materially affect correctness, follow `AGENTS.md`: state the assumptions explicitly and **wait for confirmation** before proceeding. The distinction: "I'll add the endpoint at `/users`" is safe to proceed on; "I'll use JWT auth instead of session cookies" requires a stop-and-confirm.

## Confusion Management Protocol

When you encounter conflicting information:

1. **Stop** — Do not proceed on a guess
2. **Name it** — "The OpenAPI spec says `GET /users/:id` returns 404, but the router returns 400"
3. **Present options** — "We can (a) align the router to the spec, (b) update the spec to match, or (c) investigate which is correct"
4. **Wait** — Let the user or upstream agent resolve

This costs 30 seconds. Guessing wrong costs an hour of rework.

## Per-Stage Curation Strategy

Each pipeline stage has different context needs. Load what's relevant, unload what's stale:

| Stage | Load | Unload | Context Priority |
|---|---|---|---|
| 0 (Setup) | Rules only | — | Minimal |
| 1 (Requirements) | Problem statement, PM skill | — | Low |
| 2 (Architecture) | Stage 1 output, arch skills, system-design | Problem raw text (keep summary) | Medium |
| 3 (Implementation) | OpenAPI spec, DB schema, dev skills, source-driven-dev | Requirements prose, architecture narratives | High |
| 4 (Testing) | Test results, Stage 3 code, evaluation-framework | Architecture docs, implementation details | High |
| 5 (Review) | Git diff, review skills, launch-readiness | Full implementation (keep diff only) | Medium |

### Stage Transition Protocol
1. Before advancing to next stage, identify what context is no longer needed
2. Checkpoint files carry forward only the essential decisions
3. If context budget > 70%, consider `/save-session` before the next stage

## Integration with Context Budget

Context-engineering (this skill) governs **what** goes into context and how to evaluate it. Context-budget governs **how much** context you have left and when to save/resume. Use both:

- **Before loading**: Is this information relevant? (context-engineering)
- **After loading**: Am I approaching token limits? (context-budget)
- **When confused**: Is this information trustworthy? (context-engineering)
- **When slow**: Am I running out of capacity? (context-budget)

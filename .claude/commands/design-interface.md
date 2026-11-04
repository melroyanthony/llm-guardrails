---
description: "Spawn parallel sub-agents with competing design constraints to produce multiple interface designs"
argument-hint: "<module or interface to design>"
allowed-tools: Read, Glob, Grep, Write, Bash, Agent, AskUserQuestion
model: opus
---

# Design Interface

Spawn 3+ sub-agents with different design constraints to produce competing interface designs, then compare trade-offs. Based on John Ousterhout's "Design It Twice" from *A Philosophy of Software Design*.

## Input

$ARGUMENTS — the module, interface, or API boundary to design. If empty, ask the user.

## Process

### Phase 1: Understand the Context

1. Read any existing code, architecture docs, or OpenAPI specs related to the interface
2. Identify the consumers of this interface (who calls it, what do they need?)
3. Identify the implementation constraints (database, external APIs, performance requirements)
4. Summarize the design problem in 2-3 sentences

### Phase 2: Spawn Competing Design Agents

Launch 3-4 sub-agents in parallel, each with a different design constraint. To ensure true parallel execution, send all Agent tool calls in a single message rather than launching them one at a time:

**Agent 1 — Minimize Surface Area:**
"Design this interface with the fewest methods possible (aim for 1-3). Hide everything else as implementation details."

**Agent 2 — Maximize Flexibility:**
"Design this interface to support the widest range of use cases. Favor composition and configuration over specialized methods."

**Agent 3 — Optimize for Common Case:**
"Design this interface for the most common usage pattern. Make the 80% case trivially easy, even if the 20% case requires more work."

**Agent 4 — Draw from Prior Art:**
"Design this interface taking inspiration from a well-known library or framework that solves a similar problem. Cite the inspiration."

Each agent outputs:

    ## Design: [Constraint Name]

    ### Interface
    [interface/class/function signatures in a code block]

    ### Usage Example
    [how a consumer would use this interface in a code block]

    ### What It Hides
    - [Implementation detail 1 hidden from consumers]
    - [Implementation detail 2]

    ### Trade-offs
    - **Pros**: [what this design optimizes for]
    - **Cons**: [what it sacrifices]

### Phase 3: Compare and Decide

Present all designs side-by-side:

```markdown
## Comparison

| Criterion | Minimal | Flexible | Common Case | Prior Art |
|---|---|---|---|---|
| Method count | 2 | 8 | 4 | 5 |
| Learning curve | Low | High | Low | Medium |
| Extensibility | Low | High | Medium | Medium |
| Common case ergonomics | Medium | Medium | High | Medium |
| Test complexity | Low | High | Medium | Medium |
```

Ask the user: "Which design best fits your needs? Or should we combine aspects of multiple designs?"

### Phase 4: Refine Selected Design

Based on the user's choice:
1. Flesh out the full interface with types, error handling, and edge cases
2. Write the interface definition (not the implementation)
3. If applicable, create a GitHub issue RFC for the design decision

## Integration Points

- **Stage 2 (architect)**: For critical module boundaries — database access layer, API client, auth middleware
- **Standalone**: Any interface design decision where trade-offs matter
- **After `/grill`**: When grilling surfaces a design decision that needs exploration

## When to Use vs When to Skip

| Use `/design-interface` | Skip (just implement) |
|---|---|
| Module boundary between teams/services | Internal utility function |
| API consumed by external clients | Private helper method |
| Database access layer | Simple CRUD wrapper |
| Auth/security middleware | Config/settings class |
| Core domain interface (DDD) | One-off script |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The obvious design is fine" | The obvious design is the first one you thought of. It may not be the best. 15 minutes of exploration prevents weeks of living with a bad interface. |
| "We can refactor the interface later" | Interface changes break every consumer. Internal refactoring is cheap; interface changes are expensive. Design it twice now. |
| "Spawning 4 agents is wasteful" | 4 parallel agents take the same wall-clock time as 1. The cost is tokens, not time — and a bad interface costs far more. |

## Red Flags

- All designs look nearly identical (constraints weren't different enough)
- No trade-offs identified (every design has trade-offs — if you can't find them, look harder)
- User picks a design without reading the comparison table
- Implementation details leak into the interface signatures

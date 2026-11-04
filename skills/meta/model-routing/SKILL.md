---
name: model-routing
description: |
  Guidelines for routing tasks to the optimal model based on complexity, risk, and cost.
  Balances capability with efficiency.
  Use when deciding which model to assign to a task based on complexity and cost.
  Triggers on: "which model", "model selection", "use opus", "use haiku", "route task".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Model Routing

## Routing Table

| Task Type | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| Architecture decisions | Opus | Requires deep reasoning, high-stakes |
| Code review | Opus | Needs nuanced judgment |
| Security review | Opus | Critical path, must catch subtle issues |
| Complex debugging | Opus | Multi-step reasoning needed |
| Implementation (business logic) | Sonnet | Good balance of quality and speed |
| API endpoint implementation | Sonnet | Well-defined patterns |
| Frontend components | Sonnet | Pattern-heavy, well-suited |
| Test writing | Sonnet | Structured, pattern-based |
| Formatting/linting fixes | Haiku | Mechanical, low-risk |
| Documentation generation | Haiku | Templated, low complexity |
| Simple CRUD operations | Haiku | Boilerplate-heavy |
| Git operations | Haiku | Deterministic, low-risk |

## Decision Framework

### Use Opus When:
- The task involves architectural decisions with long-term consequences
- Security or correctness is critical (auth, payments, data integrity)
- Complex reasoning across multiple files or systems is needed
- The output will be reviewed by stakeholders (design docs, ADRs)
- Debugging a subtle or intermittent issue

### Use Sonnet When:
- Implementing well-scoped features from clear specifications
- Writing tests for defined behavior
- Performing code review on non-security-critical code
- Building UI components from designs
- Standard refactoring (extract method, rename, move)

### Use Haiku When:
- The task is mechanical or template-based
- Low risk of error (formatting, simple renames, boilerplate)
- High volume of similar small tasks
- Speed matters more than nuance
- The output is immediately verifiable

## Cost Awareness
- Opus: ~$15/M input, ~$75/M output — use deliberately
- Sonnet: ~$3/M input, ~$15/M output — default workhorse
- Haiku: ~$0.25/M input, ~$1.25/M output — use for volume

## Agent Model Assignments

```yaml
orchestrator: opus       # Coordinates entire pipeline
product-manager: sonnet  # Requirements analysis
architect: opus          # System design decisions
backend-dev: sonnet      # Implementation
frontend-dev: sonnet     # Implementation
tester: sonnet           # Test writing and validation
judge: opus              # Quality gate evaluation
code-reviewer: opus      # Thorough code review
security-reviewer: opus  # Security analysis
refactor: sonnet         # Pattern-based refactoring
planner: opus            # Complex task decomposition
git-deployer: haiku      # Mechanical git operations
```

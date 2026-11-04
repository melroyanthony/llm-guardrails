---
name: autonomous-loops
description: |
  Patterns for autonomous agent loops: sequential pipelines, continuous PR loops,
  parallel worktree execution, and self-healing build loops.
  Use when designing agent workflows that run without human intervention.
  Triggers on: "autonomous", "agent loop", "self-healing", "parallel agents", "worktree", "PR loop".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Autonomous Loop Patterns

## Pattern 1: Sequential Pipeline
Chain agents in a defined order with structured handoffs.

```
planner → backend-dev → frontend-dev → tester → code-reviewer
```

Each agent produces a handoff document:
- **Context**: What was done and why
- **Files Modified**: List of changes with purposes
- **Open Questions**: Unresolved decisions
- **Recommendations**: Suggestions for the next agent
- **Status**: COMPLETE | PARTIAL | BLOCKED

## Pattern 2: Continuous Build Loop
Self-healing loop that monitors builds and fixes failures.

```
while build_fails:
    1. Capture build error output
    2. Analyze root cause
    3. Apply targeted fix
    4. Re-run build
    5. If same error persists 3 times → escalate to user
```

**Key rules:**
- Maximum 5 iterations before escalating
- Never apply the same fix twice
- Log each attempt with error and fix applied
- Track which files were modified in each iteration

## Pattern 3: PR Review Loop
Automated PR creation with CI monitoring and auto-fix.

```
1. Create PR with `gh pr create`
2. Wait for CI checks to complete
3. If CI fails:
   a. Read the failing log. Do not re-run a red check blindly
   b. If an agent already owns the branch, reply to that agent with the symptom, the log, and the definition of done
   c. Push the fix commit that agent produces
   d. A flake gets an issue; the test stays enabled
   e. Return to step 2
4. If CI passes:
   a. Run code review
   b. Address review findings
   c. Push improvements
   d. Mark ready for human review
```

## Pattern 4: Parallel Worktree Execution
Run multiple agents in parallel using git worktrees for isolation.

```
1. Create worktree per agent: `git worktree add ../worker-N branch-N`
2. Each agent works in its own worktree (no conflicts)
3. Agents communicate via coordination files
4. When all complete, merge branches sequentially
5. Clean up worktrees: `git worktree remove ../worker-N`
```

**Use cases:**
- Backend + frontend development in parallel
- Multiple independent feature implementations
- Parallel test suite execution across modules

## Pattern 5: De-Sloppify (Two-Pass Pattern)
Two focused agents outperform one constrained agent.

```
Pass 1 (Builder): Implement the feature freely
Pass 2 (Reviewer): Clean up, remove debug code, fix style, verify tests
```

**Why this works:** Adding constraints like "don't leave console.logs" makes the builder less effective. Better to let it focus on implementation, then have a separate agent clean up.

## Pattern 6: Eval-Driven Loop
Use evaluations to guide iterative improvement.

```
while eval_score < threshold:
    1. Run eval suite
    2. Identify lowest-scoring criteria
    3. Focus improvement on that criteria
    4. Re-run eval
    5. If score decreased on other criteria → revert
```

## Pattern 7: Chase tick

A host (the human, or a scheduler outside this catalog) invokes one tick. This skill does not create a 30-minute cron.

For each in-flight item, check agent status, PR state, required CI, reviews, and staleness. Reply to the owning agent for a reversible fix (red CI, review comments, a conflict with the base). Interrupt the human only when blocked on them, when the PR is ready to merge (required CI green and the independent reviewer has confirmed the current head SHA), or when the work is finished or abandoned. The loop is `review-loop-to-squash-merge`. Ask before merging.

## Anti-Patterns
- **Infinite retry**: Always set max iterations and escalation paths
- **Silent failure**: Always log what was tried and why it failed
- **Context loss**: Use session persistence between loop iterations
- **Same fix repeated**: Track attempted fixes, never repeat one that didn't work
- **No exit condition**: Every loop must have a clear termination criteria
- **Respawn**: a fresh agent for a branch that already has an owner throws away the branch context. Follow up instead
- **Blind CI re-run**: re-running a red check without reading the log hides a real failure

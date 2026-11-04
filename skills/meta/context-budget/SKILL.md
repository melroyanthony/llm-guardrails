---
name: context-budget
description: |
  Context window management for long-running pipeline sessions.
  Provides token budget estimates, compaction strategies, and session continuity patterns.
  Use when a pipeline session is running long and may exceed context limits.
  Triggers on: "context budget", "running out of context", "session too long".
allowed-tools: Read, Grep, Glob
---

# Context Budget Management

Strategies for managing context window consumption during multi-stage SDLC pipeline sessions.

## Context Window Limits

> **Note:** Exact context/output limits may change over time. The table below is qualitative to avoid hardcoding stale numbers.

| Model | Relative Context Capacity | Typical Use |
|-------|---------------------------|-------------|
| Opus | Highest | Long, complex multi-stage sessions with heavy reasoning |
| Sonnet | High | Most SDLC pipelines and day-to-day development flows |
| Haiku | Moderate | Shorter tasks, focused tool usage, or parallelized workloads |

For planning purposes, assume a **200K token default context window**.

## Token Budget Per Pipeline Stage

Empirical estimates for a typical SDLC pipeline run:

| Stage | Estimated Tokens | Cumulative | % of 200K |
|-------|-----------------|------------|-----------|
| 0: Setup | ~2K | ~2K | 1% |
| 1: Requirements | ~15K | ~17K | 8% |
| 2: Architecture | ~25K | ~42K | 21% |
| 2.5: Issues | ~8K | ~50K | 25% |
| 3: Backend | ~40K | ~90K | 45% |
| 3: Frontend | ~35K | ~125K | 62% |
| 4: Testing | ~30K | ~155K | 77% |
| 5: Finalization | ~20K | ~175K | 87% |

**Warning thresholds:**
- **70% (~140K)**: Consider saving session state
- **85% (~170K)**: Compact or save/resume immediately
- **95% (~190K)**: Critical — session may die before completion

## Compaction Strategies

### 1. Server-Side Compaction

Use context compaction for automatic summarization of earlier conversation:
- Triggers when context approaches capacity
- Preserves key decisions and artifacts
- Transparent to the conversation flow

### 2. Save/Resume at Natural Boundaries

Best split points in the pipeline:
- **After Stage 2.5** (planning complete, implementation about to start)
- **After Stage 3** (implementation complete, testing about to start)
- **After Stage 4** (tests pass, finalization about to start)

Use `/save-session` at these boundaries, then `/resume-session` in a fresh context.

### 3. Parallel Worktrees (Reduce Accumulated Context)

Using `/parallel-stage3` spawns backend and frontend in isolated agents, each with their own fresh context window. This avoids the single-session accumulation problem.

## Warning Signs

Watch for these indicators that context is running low:
- Agent responses becoming shorter or less detailed
- Tool calls failing with timeout errors
- Loss of earlier conversation context (forgetting decisions)
- Increased latency in responses

## Recovery Patterns

### If Session Dies Mid-Pipeline

1. Check `solution/checkpoints/` for the last completed stage
2. Check git log for the last commit (shows stage progress)
3. Resume with `/orchestrate N` from the next stage
4. The checkpoint files contain all decisions needed to continue

### Proactive Session Split

```
Stage 0-2.5: Session 1 (planning — ~50K tokens)
  → /save-session
Stage 3: Session 2 (implementation — ~75K tokens)
  → /save-session
Stage 4-5: Session 3 (testing + finalization — ~50K tokens)
```

## Integration with Pipeline

The orchestrator should check context budget at stage boundaries:
- Display estimated remaining capacity after each stage
- Suggest save/resume when approaching 70% threshold
- Automatically recommend parallel execution for Stage 3 when budget is tight

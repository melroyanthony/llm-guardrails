---
name: session-persistence
description: |
  Save and resume session state for long-running SDLC pipelines.
  Captures progress, decisions, blockers, and failed approaches to enable seamless continuation.
  Use when saving or resuming long-running pipeline sessions.
  Triggers on: "save session", "resume session", "context window", "pause", "continue later".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Session Persistence

## Purpose
Long-running SDLC pipelines (2-4 hours) often exceed context windows or get interrupted. Session persistence captures structured state so work can resume without losing context.

## Save Session

When saving a session, capture ALL of the following sections:

### 1. What We're Building
- One-sentence project description
- Link to problem statement
- Current SDLC stage and step

### 2. What WORKED (with evidence)
- Approaches that succeeded
- Key decisions made and their rationale
- Commands/configurations that were validated
- Test results that passed

### 3. What Did NOT Work (and why)
**THIS IS THE MOST CRITICAL SECTION**
- Approaches that failed with EXACT error messages
- Why they failed (root cause, not symptoms)
- What was tried to fix them
- Why those fixes didn't work
- This prevents blind retries that waste time

### 4. Current State of Files
- Key files created/modified (with paths)
- Their purpose and status (complete/partial/broken)
- Any temporary files that should be cleaned up

### 5. Decisions Made
- Architecture decisions with rationale
- Technology choices with justification
- Trade-offs accepted and their reasoning

### 6. Blockers
- Current blockers preventing progress
- Potential solutions identified but not yet tried
- External dependencies or questions for the user

### 7. Exact Next Step
- The SPECIFIC next action to take (not a general direction)
- Any prerequisites for that action
- Expected outcome of that action

## File Format
Save to: `solution/checkpoints/session-{timestamp}.md`

```markdown
# Session State — {timestamp}

## Project: {name}
## Stage: {current_stage} / Step: {current_step}
## Status: {IN_PROGRESS | BLOCKED | PAUSED}

## What We're Building
{description}

## What WORKED
- {item with evidence}

## What Did NOT Work
- **Approach**: {what was tried}
  **Error**: {exact error}
  **Root Cause**: {why it failed}
  **Lesson**: {what to do differently}

## Current Files
| File | Status | Purpose |
|------|--------|---------|
| {path} | {complete/partial/broken} | {purpose} |

## Decisions
- {decision}: {rationale}

## Blockers
- {blocker}: {potential solutions}

## Exact Next Step
{specific action to take}
```

## Resume Session
When resuming:
1. Read the most recent session file
2. Present a structured briefing to the user
3. Confirm the next step before proceeding
4. Check if any blockers have been resolved
5. Verify file state matches expectations (files may have been modified externally)

## Auto-Save Triggers
Save automatically when:
- Completing an SDLC stage (before starting the next)
- Encountering a blocker that requires user input
- Context window is approaching limits (suggest `/compact` after save)
- User requests a pause
- An unexpected error occurs during pipeline execution

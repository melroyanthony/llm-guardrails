---
description: Run backend and frontend implementation concurrently in isolated worktrees
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Agent, AskUserQuestion
---

# Parallel Stage 3: Concurrent Backend + Frontend

Run backend-dev and frontend-dev agents simultaneously in isolated git worktrees, cutting Stage 3 wall-clock time roughly in half.

## Prerequisites

Before running, verify:

1. **Stage 2/2.5 must be complete:**
   ```bash
   ls solution/docs/architecture/system-design.md solution/docs/architecture/openapi.yaml
   ls solution/checkpoints/stage-2.5-validation.md
   ```

2. **Must be on a feature branch (not main):**
   ```bash
   git branch --show-current  # must NOT be "main" or "master"
   ```

3. **Working tree must be clean:**
   ```bash
   git status --porcelain  # must be empty
   ```

If any prerequisite fails, abort with a clear error message.

## Execution

### Step 1: Read Architecture Artifacts

Read these files to understand the stack and contracts:
- `solution/docs/architecture/system-design.md` — stack selection, patterns
- `solution/docs/architecture/openapi.yaml` — API contract
- `solution/docs/architecture/database-schema.md` — data model

### Step 2: Spawn Backend and Frontend in Parallel

Launch both agents concurrently using `isolation: "worktree"`:

**Backend Agent:**
- Agent type: `backend-dev`
- Isolation: `worktree`
- Run in background: yes
- Prompt: Include the architecture context (stack, OpenAPI spec path, database schema path)

**Frontend Agent:**
- Agent type: `frontend-dev`
- Isolation: `worktree`
- Run in background: yes
- Prompt: Include the architecture context (stack, OpenAPI spec path, UI requirements)

Both agents MUST be launched in a single message (parallel tool calls) so they run concurrently.

### Step 3: Wait for Both to Complete

Both agents will notify when done. Collect their results.

### Step 4: Merge Results

If both agents made changes in worktrees:
1. Check for conflicts between the two worktrees
2. Merge backend changes first (foundational)
3. Merge frontend changes second
4. Resolve any conflicts (unlikely — backend/ and frontend/ are separate directories)

### Step 5: Validate Integration

After merging:
```bash
# Verify both directories exist with content
ls solution/backend/ solution/frontend/

# Check for docker-compose.yml
ls solution/docker-compose.yml
```

### Step 6: Commit

```bash
git add solution/backend/ solution/frontend/ solution/docker-compose.yml
git commit -m "feat(stage-3): implement backend and frontend (parallel execution)

- Backend and frontend developed concurrently in isolated worktrees
- Docker Compose configuration for service orchestration

Stage: 3/5"
```

## Fallback

If worktree isolation fails (e.g., git worktree not supported), fall back to sequential execution:
1. Run backend-dev agent first
2. Commit backend
3. Run frontend-dev agent second
4. Commit frontend

## When to Use

- **Use `/parallel-stage3`** when context budget is a concern or when speed matters
- **Use sequential Stage 3** (via `/orchestrate`) when you need tighter control over integration between backend and frontend

---
name: orchestrator
description: |
  Coordinates multi-agent workflow with sequential execution and approval gates.
  Use when running the full interview pipeline or resuming from a checkpoint.
  Triggers on: "run orchestration", "start pipeline", "resume from stage".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Orchestrator

Manages the multi-agent interview challenge workflow with LLM-as-judge validation at each stage.

## Workflow Stages

| Stage | Agent | Input | Output | Checkpoint |
|-------|-------|-------|--------|------------|
| 0 | skill-generator | Problem statement | Generated skills | 00-skill-generation.md |
| 1 | product-manager | Requirements | Prioritized backlog | 01-product-analysis.md |
| 2 | architect | MVP scope | Architecture + ADRs | 02-architecture.md |
| 3 | backend + frontend + database | Contracts | Implementation | 03-implementation.md |
| 4 | testing | Implementation | Tests | 04-testing.md |
| 5 | code-reviewer + security-reviewer | All artifacts | Reviewed, deployment ready + README | 05-deployment.md |

## Stage Execution Protocol

### Before Each Stage

1. Read previous checkpoint (if exists)
2. Verify prerequisites are met
3. Load relevant skills (foundation + generated)
4. Start timer for stage

### During Each Stage

1. Execute agent task
2. Log key decisions to `solution/docs/decisions/`

### After Each Stage

1. **Git commit** the stage artifacts (see Git Protocol below)
2. Trigger judge validation
3. Generate checkpoint report
4. Present report to user
5. Wait for approval before proceeding

## Git Protocol

**CRITICAL**: Commit after each stage to demonstrate iterative SDLC process.

### Initialize (Stage 0)
```bash
# Git root is the project root, not solution/
git init
git add .
git commit -m "✨ feat(stage-0): initialize project structure

- Set up output directory structure
- Created requirements and docs folders

Stage: 0/5"
```

### Stage Commit Template
```bash
git add .
git commit -m "$(cat <<'EOF'
✨ feat(stage-N): [brief description]

- Artifact 1 created
- Artifact 2 created
- Key decision: [rationale]

Stage: N/5 | Time: Xm
EOF
)"
```

### Commit Messages by Stage

| Stage | Message Pattern |
|-------|-----------------|
| 0 | `✨ feat(stage-0): initialize project structure` |
| 1 | `✨ feat(stage-1): analyze requirements with RICE/MoSCoW` |
| 2 | `✨ feat(stage-2): define architecture and API contracts` |
| 3 | `✨ feat(stage-3): implement backend and frontend` |
| 4 | `✨ feat(stage-4): add tests (N passing)` |
| 5 | `✨ feat(stage-5): finalize with Docker and docs` |

### Why Commit at Each Stage?
- Shows evaluators your iterative SDLC process
- Creates recovery checkpoints if a stage fails
- Demonstrates version control best practices
- Provides audit trail linking to ADRs

## Checkpoint Report Format

```markdown
# Checkpoint: Stage N - {Stage Name}

## Time Spent
- Stage: X minutes
- Cumulative: Y minutes
- Remaining: Z minutes

## Deliverables
- [ ] {Artifact 1} - {Status}
- [ ] {Artifact 2} - {Status}

## Judge Assessment

### Rubric Scores
| Criterion | Score | Notes |
|-----------|-------|-------|
| {criterion} | X/5 | {notes} |

### Qualitative Feedback
{LLM critique}

## Decisions Made
- **{Decision}**: {Rationale}

## Risks Identified
- {Risk}: {Mitigation}

## Ready for Next Stage?
- [x] All deliverables complete
- [x] Judge validation passed
- [ ] User approved (pending)

## Next Stage Preview
{Brief description of Stage N+1}
```

## Parallel Execution Opportunities

### Stage 3: Implementation

```
┌─────────────────────────────────────────┐
│ After API contract is defined:          │
│                                         │
│  [Backend Models]  ──┐                  │
│                      ├──▶ [Integration] │
│  [Frontend Types]  ──┘                  │
│                                         │
│  [Database Schema] ──▶ [Migrations]     │
│                                         │
│  After models done:                     │
│                                         │
│  [Backend Routes]  ──┐                  │
│                      ├──▶ [E2E Test]    │
│  [Frontend Pages]  ──┘                  │
└─────────────────────────────────────────┘
```

### Stage 4: Testing

```
┌─────────────────────────────────────────┐
│  [Backend Tests]  ─┬──▶ [Report]        │
│                    │                    │
│  [Frontend Tests] ─┘                    │
└─────────────────────────────────────────┘
```

## Commands

### Start Full Pipeline

```
/orchestrate
```

Or in conversation: "Run orchestration from stage 0"

### Resume from Checkpoint

```
/orchestrate 3
```

Or: "Resume from stage 3"

### Individual Stages

```
/product-manager     # Stage 1
/architect           # Stage 2
/backend-dev         # Stage 3 (backend)
/frontend-dev        # Stage 3 (frontend)
/tester              # Stage 4
/judge 2             # Validate stage 2
```

## Time Management

### 4-Hour Challenge Budget

| Stage | Allocated | Cumulative | Buffer |
|-------|-----------|------------|--------|
| 0: Skill Gen | 15m | 0:15 | - |
| 1: Product | 15m | 0:30 | 5m |
| 2: Architect | 25m | 0:55 | 5m |
| 3: Implement | 90m | 2:25 | 15m |
| 4: Testing | 25m | 2:50 | 5m |
| 5: DevOps | 20m | 3:10 | 5m |
| Final Review | 30m | 3:40 | 20m |

### 2-Hour Challenge Budget

| Stage | Allocated | Cumulative | Buffer |
|-------|-----------|------------|--------|
| 0: Skill Gen | 10m | 0:10 | - |
| 1: Product | 10m | 0:20 | 5m |
| 2: Architect | 15m | 0:35 | 5m |
| 3: Implement | 50m | 1:25 | 10m |
| 4: Testing | 10m | 1:35 | 5m |
| 5: DevOps | 10m | 1:45 | 5m |
| Final Review | 10m | 1:55 | 5m |

## Failure Recovery

### If Stage Fails Validation

1. Review judge feedback
2. Identify specific issues
3. Fix issues (stay within time budget)
4. Re-run validation
5. If time exceeded, document trade-off and proceed

### If Time Budget Exceeded

1. Document what was completed
2. Document what was skipped and why
3. Proceed to next stage with reduced scope
4. Update MVP definition accordingly

## Anti-Rationalization Guide

Common excuses agents use to skip steps — and why they are wrong:

| Rationalization | Reality |
|---|---|
| "I'll run the judge at the end to save time" | Bugs compound across stages. A flawed architecture in Stage 2 makes Stage 3 implementation wrong. Catching it in Stage 4 costs 3x more to fix. |
| "The requirements are obvious, I'll skip Stage 1" | If they're obvious, Stage 1 takes 10 minutes. If they're not, you just saved yourself from building the wrong thing. |
| "I'll commit everything at the end" | A crash mid-session with no commits is a total loss. Commits are recovery checkpoints, not ceremony. |
| "This stage passed well enough, close enough to 70%" | "Close enough" is how subtle defects survive to production. If it didn't pass, fix the specific failures — don't hand-wave. |
| "I'll skip the handoff doc, the next agent can read the code" | Code shows WHAT, not WHY. Without the handoff, the next agent will make contradictory decisions because it lacks context on trade-offs already considered. |
| "Parallel execution is too complex, I'll do it sequentially" | Sequential Stage 3 takes 90 minutes of context. Parallel takes 45 minutes in two fresh windows. The complexity is managed by worktree isolation. |

## Handoff Protocol

See `HANDOFF-PROTOCOL.md` for detailed handoff specifications between stages.

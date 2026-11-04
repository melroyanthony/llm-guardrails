---
name: research-loops
description: |
  Autonomous agent self-learning patterns: hypothesis-test-accumulate loops, git-as-state-machine
  experimentation, knowledge accumulation across sessions, and stuck-recovery protocols.
  Use when running experiments, benchmarks, or iterative optimization loops.
  Triggers on: experiment, optimize, research, iterate, improve, benchmark, "try different approaches".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Autonomous Research Loops

Patterns for iterative experimentation where an agent autonomously generates hypotheses, tests them, and accumulates knowledge.

## Core Pattern: Hypothesis-Test-Accumulate

```
1. Read current state (code, metrics, experiment log)
2. Generate hypothesis ("batch queries to reduce N+1")
3. Implement change (edit target files)
4. Commit hypothesis (git commit — captures intent)
5. Run validation (tests, benchmarks)
6. Extract metric from output (structured grep)
7. Log result to experiment log (TSV/JSON)
8. If improved → keep (branch advances)
9. If worse → revert (git reset to prior commit)
10. Repeat
```

## 1. Git-as-State-Machine

Git is the experiment state management system. Each experiment is a commit. Branch tip always represents the current best version.

### Commit Before Running
```bash
# Capture the hypothesis as a commit
git add -A
git commit -m "experiment: batch database queries in list endpoint"

# Run validation
uv run pytest tests/ > test_output.log 2>&1
RESULT=$(grep "passed" test_output.log)

# If improvement: branch advances naturally (commit stays)
# If regression: clean rollback
git reset --hard HEAD~1
```

### Why This Works
- Agent never needs to "remember" what the best version looked like — git IS the memory
- Rollback is one command, not manual file restoration
- Full history of hypotheses is preserved in reflog
- Diffs are reviewable by humans after the experiment run

## 2. Experiment Log (Persistent Memory)

```tsv
# experiment-results.tsv (gitignored — experiment journal, not code)
commit	metric	delta	status	description
a1b2c3d	185ms	-15ms	keep	Batch DB queries in list endpoint
e4f5g6h	210ms	+10ms	revert	Add caching layer (overhead > benefit)
i7j8k9l	crash	N/A	crash	Missing import after refactor — fixed and retried
l0m1n2o	172ms	-13ms	keep	Connection pooling with asyncpg
```

### Rules
- Gitignored (not part of code state)
- Persists across sessions (file on disk)
- Agent reads BEFORE generating new hypotheses (avoid repeating failures)
- Enables combining partial successes ("X helped, Y helped, try X+Y")

## 3. Single-Metric Fitness Function

Every experiment needs ONE metric for evaluation:

| Task Type | Metric | Measurement |
|---|---|---|
| Performance | Response time (p95 ms) | `curl -w "%{time_total}"` or benchmark |
| Bundle size | Gzipped JS size (KB) | `next build` output |
| Test coverage | Coverage percentage | `pytest --cov` |
| Code complexity | Cyclomatic complexity | `radon cc` or `complexity-report` |
| Query speed | Execution time (ms) | `EXPLAIN ANALYZE` |

### Fixed Budget
- Define a max iteration count (default: 10)
- Each experiment runs within a fixed time budget
- Prevents infinite loops and wasted resources

### Simplicity Tiebreaker
When metric is equal (within noise threshold):
- Change that **reduces** LOC → **keep** (simpler is better)
- Change that **increases** LOC → **revert** (not worth the complexity)
- Deletion that maintains performance → **always keep**

## 4. Graduated Crash Recovery

When an experiment fails to run:

### Level 1: Trivial Fix (max 2 attempts)
- Typo, missing import, syntax error
- Fix the issue, re-run the same experiment
- If it fails again after 2 attempts → Level 2

### Level 2: Fundamental Failure
- The approach itself is broken (wrong algorithm, incompatible library)
- Log as "crash" in experiment log
- Revert to prior commit
- Move to next hypothesis

### Level 3: Hang (> 2x expected time)
- Kill the process
- Log as "timeout" in experiment log
- Revert and move on

## 5. Stuck-Recovery Escalation

When the agent runs out of obvious hypotheses:

1. **Re-read the specification** — Missed requirements often suggest new approaches
2. **Analyze experiment log** — Look for patterns in what worked vs. failed
3. **Try the opposite** — If the last 3 experiments added code, try removing code
4. **Combine partial successes** — Experiment 3 improved X, experiment 7 improved Y, try both
5. **Try a more radical approach** — Different algorithm, different architecture
6. **Ask the human** — Only after exhausting steps 1-5

## 6. Scope Constraint

Lock the agent to specific files during experiments:

```
/experiment --target solution/backend/app/api/routes/query.py
```

### Why Constrain Scope
- Single-file experiments are easiest to reason about and revert
- Prevents the agent from creating tangled cross-file dependencies
- Makes diffs reviewable by humans
- Reduces the blast radius of failed experiments

## 7. Output Isolation in Loops

Every experiment iteration should:

```bash
# Redirect output (don't flood context)
command > experiment_output.log 2>&1

# Extract only the metric
grep "^METRIC:" experiment_output.log

# On crash: read only tail for diagnosis
tail -n 50 experiment_output.log
```

See the `output-isolation` skill for detailed patterns.

## Integration with SDLC Pipeline

| Command | How Research Loops Apply |
|---|---|
| `/experiment` | Primary consumer — full loop with git-as-state-machine |
| `/tdd` | RED→GREEN→REFACTOR is a research loop (hypothesis: this test should pass) |
| `/investigate` | Debugging is hypothesis-driven (hypothesis: this is the root cause) |
| `/verify` | Each fix cycle is a mini-experiment (hypothesis: this fix resolves the issue) |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I know which approach will work — no need to experiment" | Your intuition is a hypothesis, not a fact. Test it. The experiment takes 2 minutes. |
| "The experiment log is overhead" | One line per experiment prevents repeating failures across sessions. Net time savings. |
| "Reverting is wasteful — I'll fix it forward" | Fixing forward on a broken hypothesis wastes more time than reverting to known-good state. |
| "10 iterations isn't enough" | If 10 experiments don't improve the metric, the approach may be wrong. Step back and rethink. |
| "I ran out of ideas, let me stop" | Read the stuck-recovery protocol. You haven't tried the opposite, combined partials, or gone radical yet. |

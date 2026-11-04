---
description: "Autonomous research loop: commit hypothesis, run validation, keep/revert, accumulate knowledge"
argument-hint: "--metric <metric> --target <path> [--budget <N>] [--command <cmd>]"
allowed-tools: Read, Glob, Grep, Edit, Write, Bash, Agent
---

# Experiment

Autonomous iterative improvement loop using git-as-state-machine. Commit hypotheses, run validation, keep improvements, revert regressions, accumulate knowledge.

## Input

Parse from $ARGUMENTS:
- `--metric` (required): Single metric to optimize (e.g., `response_time_ms`, `bundle_size_kb`, `coverage_pct`)
- `--target` (required): File(s) the agent may modify (scope constraint)
- `--budget` (optional, default: 10): Maximum iterations
- `--command` (optional): Validation command that emits `METRIC:<name>=<value>` lines. If omitted, the agent auto-detects the test runner and wraps it to extract the metric:
  - `pyproject.toml` exists → run `uv run pytest tests/ -v`, parse summary for pass/fail counts
  - `package.json` exists → run `npm test`, parse output
  - `Makefile` exists → run `make test`, parse output
  - The agent is responsible for writing the `METRIC:` line to stdout/log after parsing command output (e.g., extracting response time from curl, coverage % from pytest-cov, bundle size from build output)
- `--threshold` (optional, default: 1%): Minimum improvement to keep a change

## Prerequisites

Before starting the loop:

1. **Clean git state**: `git status` must show no uncommitted changes
2. **Baseline measurement**: Run the validation command once and extract the baseline metric
3. **Experiment branch**: Create or verify we're on an experiment branch (not main)

```bash
# Parse arguments (agent does this from $ARGUMENTS)
METRIC="response_time_ms"           # from --metric
TARGET="solution/backend/app/"      # from --target
BUDGET=10                           # from --budget (default 10)
COMMAND="uv run pytest tests/ -v"   # from --command (or auto-detected)

# Verify clean state
git status --porcelain  # Must be empty

# Create experiment branch if on main
BRANCH=$(git branch --show-current)
if [ "$BRANCH" = "main" ]; then
  git checkout -b "experiment/$(date +%Y%m%d)-${METRIC}"
fi

# Run baseline — validation command must emit lines in format: METRIC:<name>=<value>
${COMMAND} > experiment_output.log 2>&1
BASELINE=$(grep "^METRIC:${METRIC}=" experiment_output.log | head -1)
echo "BASELINE: ${BASELINE}"
# Example expected output: METRIC:response_time_ms=200
```

## Experiment Loop

```
LOOP (iteration 1 to BUDGET):

  1. READ CONTEXT
     - Current target file(s)
     - Experiment log (if exists) — avoid repeating failed approaches
     - Last 3 experiment results for pattern detection

  2. GENERATE HYPOTHESIS
     - Specific and testable ("batch DB queries" not "make it faster")
     - Informed by experiment log (don't repeat failures)
     - If stuck: apply escalation protocol (see below)

  3. IMPLEMENT CHANGE
     - Edit ONLY the target file(s) — no infrastructure changes
     - Keep changes focused on the hypothesis

  4. COMMIT HYPOTHESIS
     git add <target-files>
     git commit -m "experiment: <hypothesis description>"

  5. RUN VALIDATION
     ${COMMAND} > experiment_output.log 2>&1
     EXIT_CODE=$?

  6. EXTRACT METRIC
     RESULT=$(grep "^METRIC:${METRIC}=" experiment_output.log | head -1)
     - If empty output or crash → go to CRASH RECOVERY

  7. LOG RESULT
     Append a tab-separated row to experiment-results.tsv:
     iteration<TAB>commit<TAB>metric_value<TAB>delta<TAB>status<TAB>loc_delta<TAB>description

  8. EVALUATE
     - If improved by > threshold → KEEP (branch advances)
     - If equal (within threshold):
       - LOC decreased → KEEP (simpler is better)
       - LOC increased → REVERT (not worth complexity)
     - If worse → REVERT
       git reset --hard HEAD~1

  9. REPEAT
```

## Experiment Log

Maintain `experiment-results.tsv` in the working directory (gitignored):

```tsv
iteration	commit	metric	delta	status	loc_delta	description
1	a1b2c3d	185ms	-15ms	keep	-5	Batch DB queries in list endpoint
2	e4f5g6h	210ms	+10ms	revert	+20	Add caching layer (overhead > benefit)
3	i7j8k9l	crash	N/A	crash	0	Missing import after refactor — fixed
4	l0m1n2o	172ms	-13ms	keep	+3	Connection pooling with asyncpg
```

### Log Rules
- Must be gitignored — prefer `.git/info/exclude` for local-only experiment artifacts (idempotent):
  ```bash
  grep -qxF 'experiment-results.tsv' .git/info/exclude 2>/dev/null || echo "experiment-results.tsv" >> .git/info/exclude
  grep -qxF 'experiment_output.log' .git/info/exclude 2>/dev/null || echo "experiment_output.log" >> .git/info/exclude
  ```
- Persists across sessions (file on disk)
- Read BEFORE generating hypotheses (avoid repeating failures)
- Include LOC delta for simplicity tiebreaker decisions

## Crash Recovery Protocol

### Level 1: Trivial Fix (max 2 attempts)
- Symptom: typo, missing import, syntax error
- Action: fix the issue, re-run the same experiment
- If fails after 2 attempts → Level 2

### Level 2: Fundamental Failure
- Symptom: wrong algorithm, incompatible library, design flaw
- Action: log as "crash" in experiment log, revert to prior commit, move to next hypothesis

### Level 3: Hang (> 2x expected time)
- Symptom: command hasn't returned after double the baseline duration
- Action: kill the process, log as "timeout", revert, move on

## Stuck-Recovery Escalation

When running out of hypotheses (no improvement in last 3 iterations):

1. **Re-read the target files** — look for patterns you haven't tried
2. **Analyze experiment log** — what do successful experiments have in common?
3. **Try the opposite** — if last 3 experiments added code, try removing code
4. **Combine partial successes** — experiment N improved X, experiment M improved Y, try both
5. **Try a radical approach** — different algorithm, different data structure
6. **Report to user** — only after exhausting steps 1-5

## Simplicity Tiebreaker

When metric improvement is within the noise threshold:

| LOC Change | Action | Rationale |
|---|---|---|
| Reduced | **Keep** | Simpler code with same performance is always a win |
| Same | **Revert** | No improvement, no point |
| Increased | **Revert** | More complexity without meaningful improvement |
| Deletion that maintains metric | **Always keep** | Less code to maintain |

## Output Isolation

Every iteration uses redirect-extract-summarize:

```bash
# Redirect ALL output
${COMMAND} > experiment_output.log 2>&1

# Extract only the metric
grep "^METRIC:" experiment_output.log

# On crash: only tail for diagnosis
tail -n 50 experiment_output.log
```

## Completion

When the loop ends (budget exhausted or user interrupt):

1. **Summary report**: Print experiment log with best result highlighted
2. **Net improvement**: Compare final metric vs baseline
3. **Branch state**: Branch tip is the best version (all regressions reverted)
4. **Recommend**: If net improvement > threshold, suggest merging. Otherwise, suggest discarding.

```
Experiment Complete (N iterations)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Baseline:  200ms
Best:      158ms (iteration 7)
Final:     162ms (iteration 10)
Net:       -38ms (-19.0%)
Kept:      6 of 10 experiments
Crashed:   1 (fixed and retried)
Reverted:  3

Recommendation: Merge — 19% improvement with 12 fewer LOC.
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I know which approach will work — skip the loop" | Your intuition is a hypothesis, not a fact. Test it. The experiment takes 2 minutes. |
| "The experiment log is overhead" | One line per experiment prevents repeating failures. Net time savings. |
| "Reverting is wasteful — fix forward" | Fixing forward on a broken hypothesis wastes more time than reverting to known-good state. |
| "10 iterations isn't enough" | If 10 experiments don't improve the metric, the approach may be wrong. Step back and rethink. |

## Red Flags

- Editing files outside the target scope (infrastructure creep)
- Not reading experiment log before generating hypotheses (repeating failures)
- Keeping changes with < threshold improvement (noise, not signal)
- Crash recovery exceeding 2 attempts on the same hypothesis
- All experiments adding code, none removing (complexity bias)

---
name: output-isolation
description: |
  Patterns for isolating and selectively extracting results from subprocess output.
  Prevents context window pollution from verbose command output.
  Use when subprocess output is too verbose and pollutes the context window.
  Triggers on: "too much output", subprocess, log parsing, command output, context pollution.
allowed-tools: Read, Grep, Glob, Bash
---

# Output Isolation

## Principle

Context window is the scarcest resource in LLM-driven pipelines. A 5-minute build produces thousands of lines of output. Selective extraction (2-3 lines of metrics) is dramatically more effective than flooding context with raw output.

## Pattern: Redirect-Extract-Summarize

### 1. Redirect ALL Output to File

```bash
# CORRECT: Redirect to file, read selectively
uv run pytest tests/ -v > test_output.log 2>&1
echo "EXIT_CODE: $?"

# WRONG: Pipe raw output into context
uv run pytest tests/ -v  # Hundreds of lines flood the context
```

### 2. Extract Structured Metrics

```bash
# Extract only the pytest summary line
grep -E "^=+ .* (passed|failed|error|errors|skipped|xfailed|xpassed|deselected|warnings|no tests ran)" test_output.log

# Extract specific metrics
grep "^METRIC:" test_output.log

# Extract passed count (portable — no PCRE)
grep -Eo '[0-9]+ passed' test_output.log
```

### 3. On Failure: Read Only Tail

```bash
# Only read last 50 lines for error diagnosis
tail -n 50 test_output.log
```

## Structured Output Convention

Commands that emit structured lines for machine parsing:

```
METRIC: response_time_ms=185
METRIC: test_count=35
METRIC: coverage_pct=82.5
STATUS: PASS
ERROR: connection refused on port 5432
WARNING: deprecated API usage in app/main.py:42
```

### Rules
- Prefix structured lines with `METRIC:`, `STATUS:`, `ERROR:`, `WARNING:`
- One key=value pair per line
- Use consistent naming (snake_case)
- Always emit a `STATUS:` line (PASS/FAIL/ERROR)

## Per-Command Extraction Patterns

### pytest
```bash
uv run pytest tests/ -v > pytest.log 2>&1
# Extract: pass/fail counts, duration
grep -E "passed|failed|error" pytest.log | tail -1
# On failure: last 30 lines
tail -n 30 pytest.log
```

### Docker Compose
```bash
docker compose up -d > docker.log 2>&1
# Extract: service status
docker compose ps --format json 2>/dev/null || docker compose ps
# On failure: service logs
docker compose logs --tail=20 failing-service
```

### npm/uv build
```bash
npm run build > build.log 2>&1
# Extract: bundle size, warnings count
grep -E "Size|Warning|Error" build.log
# On failure: last errors
grep -A2 "ERROR" build.log
```

### Terraform
```bash
terraform plan -out=tfplan > plan.log 2>&1
# Extract: resource changes
grep -E "Plan:|to add|to change|to destroy" plan.log
# On failure: specific error
grep -A5 "Error:" plan.log
```

### Database Queries
```bash
psql -c "EXPLAIN ANALYZE SELECT ..." > query.log 2>&1
# Extract: execution time, scan type
grep -E "Execution Time|Seq Scan|Index Scan" query.log
```

## Integration Points

### Hook Scripts
Hook scripts should always:
1. Redirect subprocess output to a temp file
2. Parse for specific patterns
3. Return only the relevant summary to the agent

### Agent Subprocess Calls
When an agent runs a command:
1. Default to file redirect for any command expected to produce > 20 lines
2. Extract structured metrics (grep for patterns)
3. Only read full output if extraction shows errors

### Context Budget Alignment
- Output isolation reduces context consumption by 90%+ for verbose commands
- Combine with context-budget skill for long pipelines
- Log files can be re-read later if deeper investigation needed

## Anti-Patterns

| Anti-Pattern | Impact | Fix |
|---|---|---|
| Piping raw `pytest -v` into context | 100+ lines consumed | Redirect to file, grep summary |
| Reading entire Docker build output | 500+ lines consumed | Extract only errors and final status |
| Not capturing stderr separately | Errors mixed with output | Use `2>&1` to combine, or `2>err.log` to separate |
| Re-reading full log after each iteration | Stale context accumulation | Only read tail on failure |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I need to see the full output to understand the error" | The last 50 lines contain the error. The first 500 lines are setup noise. |
| "Redirecting to files adds complexity" | One `> output.log 2>&1` saves hundreds of context tokens. Net simplicity gain. |
| "Structured output conventions are overhead" | A `METRIC:` prefix costs 7 characters and saves grep gymnastics every time. |

---
name: agent-telemetry
description: |
  Pipeline execution telemetry: track stage durations, judge scores, failure modes, and fix cycle
  counts across runs. Enables data-driven improvement of agent definitions and skills.
  Use when analyzing pipeline performance or identifying bottleneck stages.
  Triggers on: telemetry, metrics, pipeline performance, agent effectiveness, bottleneck.
allowed-tools: Read, Glob, Grep, Write, Bash
---

# Agent Telemetry

Track pipeline execution metrics across runs to identify bottlenecks, common failure modes, and improvement opportunities.

## Principle

You can't improve what you don't measure. Telemetry closes the feedback loop between pipeline execution and agent/skill refinement.

## Telemetry Schema

After each pipeline run, emit a JSON file at `solution/metrics/pipeline-telemetry.json`:

```json
{
  "run_id": "uuid-v4",
  "timestamp": "2026-04-11T10:00:00Z",
  "problem": "problem/PROBLEM.md",
  "stages": {
    "stage-0": {
      "duration_s": 30,
      "status": "complete",
      "agent": "orchestrator",
      "model": "opus"
    },
    "stage-1": {
      "duration_s": 180,
      "status": "complete",
      "judge_score": 88,
      "agent": "product-manager",
      "model": "sonnet",
      "artifacts": ["requirements.md", "mvp-scope.md", "rice-scores.md"]
    },
    "stage-2": {
      "duration_s": 420,
      "status": "complete",
      "judge_score": 85,
      "agent": "architect",
      "model": "opus",
      "artifacts": ["openapi.yaml", "database-schema.md", "ADR-001.md", "ADR-002.md"]
    },
    "stage-3": {
      "duration_s": 2400,
      "status": "complete",
      "judge_score": 78,
      "agent": "backend-dev",
      "model": "sonnet",
      "parallel": false,
      "endpoints_implemented": 8,
      "test_count": 35
    },
    "stage-4": {
      "duration_s": 900,
      "status": "complete",
      "tests_passed": 35,
      "tests_failed": 0,
      "e2e_passed": 9,
      "bug_fixes": 3,
      "agent": "tester",
      "model": "sonnet"
    },
    "stage-5": {
      "duration_s": 600,
      "status": "complete",
      "agent": "code-reviewer",
      "model": "opus",
      "review_findings": 5,
      "security_findings": 1,
      "fix_cycles": 1,
      "pr_created": true,
      "pr_number": 42
    }
  },
  "totals": {
    "duration_s": 4530,
    "commits": 12,
    "context_saves": 0,
    "failure_modes": ["stage-3: hallucinated API pattern", "stage-4: flaky E2E test"]
  }
}
```

## Collection Points

### Per-Stage (orchestrator records)
| Metric | When | How |
|---|---|---|
| `duration_s` | Stage start/end | Timestamp diff |
| `judge_score` | After judge validation | From judge verdict |
| `status` | After completion | complete / blocked / skipped |
| `agent` / `model` | At stage dispatch | From agent definition |
| `artifacts` | After commit | List of files created |

### Per-Run (orchestrator aggregates)
| Metric | When | How |
|---|---|---|
| `totals.duration_s` | Pipeline end | Sum of stage durations |
| `commits` | Pipeline end | `git log --oneline` count |
| `context_saves` | Pipeline end | Count of `/save-session` calls |
| `failure_modes` | Pipeline end | Collected from stage issues |

## Analysis Patterns

### Bottleneck Detection
```
Sort stages by duration_s descending.
If stage-3 > 60% of total → implementation is the bottleneck.
If stage-4 > 30% of total → testing/bug-fixing is the bottleneck.
If stage-5 fix_cycles > 1 → code quality at stage-3 needs improvement.
```

### Quality Trends (across multiple runs)
```
Track judge_score per stage over last N runs.
If scores trending down → agent definition may have regressed.
If scores consistently low for one stage → that agent/skill needs improvement.
If fix_cycles trending up → review quality or implementation quality declining.
```

### Failure Mode Frequency
```
Aggregate failure_modes across runs.
Top 3 most common → prioritize fixes in agent definitions or skills.
Example: "hallucinated API" appears in 30% of runs → strengthen source-driven-dev skill.
```

### Model Efficiency
```
Compare stage duration and quality across model assignments.
If sonnet produces same judge scores as opus for stage-X → keep sonnet (cheaper).
If haiku produces lower scores → upgrade to sonnet for that stage.
```

## Integration

### Orchestrator
The orchestrator agent records telemetry as it runs each stage. At pipeline end, it writes the telemetry file:

```bash
# Create metrics directory
mkdir -p solution/metrics

# Write telemetry (agent constructs JSON from collected data)
# File is committed as part of Stage 5 finalization
```

### Session Persistence
Include telemetry data in `/save-session` output so long-running pipelines don't lose metrics on context reset.

### Gitignore Consideration
`pipeline-telemetry.json` is typically worth **committing** in project repos because it supports retrospectives across runs. In repos where telemetry artifacts should remain local-only, add an explicit ignore for `solution/metrics/pipeline-telemetry.json` (or `solution/metrics/`) instead of assuming that ignore rule already exists.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Telemetry is overhead for a single run" | A single run's data is noise. 10 runs reveal patterns. Start collecting now. |
| "I can estimate bottlenecks from experience" | Your estimate of "stage 3 is slow" doesn't tell you if it's 60% or 30% of total time. Measure. |
| "Judge scores are subjective anyway" | Subjective scores tracked over time reveal trends. A 10-point drop across 5 runs is signal, not noise. |

## Red Flags

- No telemetry file produced after a pipeline run
- All judge scores above 90% (rubber-stamping, not useful signal)
- Failure modes list is always empty (not recording issues honestly)
- Telemetry only collected for successful runs (failures are the most valuable data)

---
name: judge
description: |
  Validates stage outputs using rubrics and qualitative critique.
  Use when assessing stage quality before proceeding to the next stage.
  Triggers on: "validate stage", "judge output", "review checkpoint".
allowed-tools: Read, Grep, Glob, Write
---

# Judge (LLM-as-Judge)

Provides objective validation of stage outputs using structured rubrics and qualitative analysis.

## Validation Approach

1. **Rubric-based scoring**: Quantitative assessment against defined criteria
2. **Qualitative critique**: Open-ended analysis of strengths and weaknesses
3. **Actionable feedback**: Specific improvements if validation fails

## Invocation

```
Validate stage N output
```

or

```
Judge the {stage-name} deliverables
```

## Validation Process

### Step 1: Load Stage Rubric

From `RUBRICS.md`, load criteria for the specific stage.

### Step 2: Score Each Criterion

For each criterion:
1. Read relevant artifacts
2. Assess against the criterion
3. Assign score (1-5)
4. Note specific evidence

### Step 3: Generate Qualitative Critique

Using `CRITIQUE-PROMPTS.md`, analyze:
- What was done well
- What could be improved
- Critical issues (if any)
- Suggestions for code review discussion

### Step 4: Determine Pass/Fail

- **Pass**: All criteria ≥3, no critical issues
- **Conditional Pass**: Minor issues, can proceed with notes
- **Fail**: Any criterion <2 or critical issues present

### Step 5: Generate Report

Write checkpoint report to `solution/checkpoints/{stage}.md`

## Output Format

```markdown
# Validation Report: Stage N - {Name}

## Summary
- **Status**: {PASS | CONDITIONAL PASS | FAIL}
- **Score**: {X}/5 average
- **Time**: {elapsed} / {budgeted}

## Rubric Scores

| Criterion | Score | Evidence |
|-----------|-------|----------|
| {name} | {1-5}/5 | {specific evidence} |

## Qualitative Assessment

### Strengths
- {strength with specific example}

### Areas for Improvement
- {improvement with actionable suggestion}

### Critical Issues
- {issue requiring immediate attention} (if any)

## Recommendations

### For Code Review
- Be prepared to discuss: {key decision}
- Highlight: {notable approach}
- Acknowledge: {known limitation}

### For Next Stage
- {specific guidance for next stage}

## Verdict

{PROCEED | REVISE | ESCALATE}

{If REVISE: specific items to fix}
{If ESCALATE: why user input is needed}
```

## Gate Logic (aligned with judge agent + CLAUDE.md)

| Score | Verdict | Action |
|-------|---------|--------|
| ≥ 70% | **PROCEED** | Advance (may include warnings) |
| 50–69% | **REVISE** | Do not advance until fixes re-judged |
| < 50% | **ESCALATE** | Human input or major rework required |

≥70% is required to pass a stage gate. There is no “proceed with warnings” path below 70%.

## Stage-Specific Focus

### Stage 0: Skill Generation
- Are generated skills relevant to problem domain?
- Do skills have proper structure and triggers?
- Is requirement extraction complete?

### Stage 1: Product Analysis
- Is RICE scoring consistent and justified?
- Is MVP scope realistic for time budget?
- Are trade-offs clearly documented?

### Stage 2: Architecture
- Does C4 diagram accurately represent system?
- Is OpenAPI spec complete and consistent?
- Are ADRs meaningful (not boilerplate)?

### Stage 3: Implementation
- Does code follow patterns from skills?
- Are there obvious bugs or type errors?
- Is code idiomatic and readable?

### Stage 4: Testing
- Do tests cover critical paths?
- Are tests meaningful (not trivial)?
- Do tests pass?

### Stage 5: DevOps
- Does docker-compose work?
- Is README clear and complete?
- Are setup instructions accurate?

## Scoring Guide

| Score | Meaning | Action |
|-------|---------|--------|
| 5 | Exceptional | Proceed, highlight in review |
| 4 | Good | Proceed |
| 3 | Adequate | Proceed with notes |
| 2 | Needs work | Fix before proceeding |
| 1 | Critical gap | Must fix, may need scope reduction |

## See Also

- `RUBRICS.md` for detailed scoring criteria
- `CRITIQUE-PROMPTS.md` for qualitative analysis prompts

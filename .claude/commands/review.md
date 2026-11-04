---
description: "Run code review on files, directories, or git diffs"
allowed-tools: Read, Glob, Grep, Bash, Agent
---

# Code Review

Perform a thorough staff-level code review.

## Input
$ARGUMENTS — Target for review. Can be:
- A file path: `solution/backend/app/api/routes.py`
- A directory: `solution/backend/`
- A git range: `HEAD~3..HEAD`
- Empty (defaults to all uncommitted changes)

## Process

1. **Spawn code-reviewer agent** to perform the review
2. If $ARGUMENTS is empty, review `git diff HEAD` (all uncommitted changes)
3. If $ARGUMENTS is a git range, review `git diff $ARGUMENTS`
4. If $ARGUMENTS is a file or directory, review all code in that path

The code-reviewer agent will:
- Review for correctness, maintainability, performance, and security
- Score quality 1-10
- Provide findings with severity levels (critical/warning/suggestion/nitpick)
- Include specific line references and suggested fixes

## Output
Structured review report with actionable findings.

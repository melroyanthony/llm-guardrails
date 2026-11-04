---
name: verification-loop
description: |
  6-phase verification pipeline: Build → Type Check → Lint → Test → Security Scan → Diff Review.
  Run after implementation to catch issues before commit.
  Use when running quality checks before committing or after implementation.
  Triggers on: "verify", "check quality", "pre-commit", "verification loop", "quality gate".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Verification Loop

## Overview
A systematic 6-phase quality verification pipeline. Run this after any significant code change to catch issues before they reach review.

Evidence before claims. Identify the command that proves the claim, run it fresh, read the exit code and the failures, then state the result with that output. A previous run, a linter pass, or an agent saying "success" is not the proof. Adapted from Jesse Vincent's `verification-before-completion` (MIT, https://github.com/obra/superpowers).

## Phase 1: Build
- **Python**: `uv run python -c "import app"` or `uv run python -m py_compile <file>`
- **TypeScript**: `npx tsc --noEmit`
- **Docker**: `docker compose build`
- **Gate**: Build must succeed. Stop and fix before proceeding.

## Phase 2: Type Check
- **Python**: `uv run mypy --strict <path>` or `uv run pyright <path>`
- **TypeScript**: `npx tsc --noEmit --strict`
- **Gate**: Zero type errors. Warnings acceptable but should be reviewed.

## Phase 3: Lint
- **Python**: `uv run ruff check <path>` + `uv run ruff format --check <path>`
- **TypeScript**: `npx biome check <path>` or `npx eslint <path>`
- **Gate**: Zero errors. Auto-fix where possible (`--fix`), manual fix the rest.

## Phase 4: Test Suite
- **Python**: `uv run pytest --tb=short -q`
- **TypeScript**: `npx vitest run`
- **Coverage target**: 80%+ for business logic, 100% for auth/security/financial
- **Gate**: All tests pass. Coverage meets threshold.

## Phase 5: Security Scan
- **Python**: `uv run bandit -r <path>` or `uv run safety check`
- **TypeScript**: `npm audit` or `npx snyk test`
- **Manual**: Check for hardcoded secrets, SQL injection, XSS vectors
- **Gate**: No high/critical findings. Medium findings documented.

## Phase 6: Diff Review
- Run `git diff --staged` or `git diff HEAD`
- Review every changed line for:
  - Unintended changes or leftover debug code
  - Missing error handling at boundaries
  - Breaking API contract changes
  - Missing or outdated tests for changed code
- **Gate**: All changes are intentional and complete.

## Stack harness

For a repo that uses uv, ruff, TypeScript, changesets, pnpm, biome, pyright, mypy, nvm, or Railway, run `bash .claude/hooks/scripts/stack-verify.sh`. It selects the read-only command for each detected tool (`tsc` for TypeScript 7, `tsgo` only for `@typescript/native-preview`). It does not deploy, publish, or rewrite a lockfile. The block and warn rules live in `stack-guardrails`.

## Execution Strategy
- Run phases sequentially (each depends on previous passing)
- On failure: fix the issue, then restart from the failed phase (not from scratch)
- Log results to `solution/checkpoints/verification-report.md`
- If all 6 phases pass → code is ready for commit/review

## Quick Reference

| Phase | Python | TypeScript |
|-------|--------|------------|
| Build | `uv run python -m py_compile` | `npx tsc --noEmit` |
| Type | `uv run mypy --strict` | `npx tsc --noEmit --strict` |
| Lint | `uv run ruff check && ruff format --check` | `npx biome check` |
| Test | `uv run pytest -q` | `npx vitest run` |
| Security | `uv run bandit -r` | `npm audit` |
| Diff | `git diff --staged` | `git diff --staged` |

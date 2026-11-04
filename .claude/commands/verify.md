---
description: "Run the 6-phase verification loop: Build → Type Check → Lint → Test → Security → Diff Review"
allowed-tools: Read, Glob, Grep, Bash, Agent
---

# Verification Loop

Run the full 6-phase verification pipeline.

## Input
$ARGUMENTS — Optional: specific phase to start from (1-6) or path to verify. Defaults to full pipeline on `solution/`.

## Process

1. **Load verification-loop skill** from `skills/foundation/verification-loop/SKILL.md`
2. **Detect project stack**:
   - Check for `pyproject.toml` → Python stack
   - Check for `package.json` → Node.js stack
   - Check for both → full-stack
3. **Execute phases sequentially**:

### Phase 1: Build
- Python: `cd solution/backend && uv sync && uv run python -c "import app"`
- TypeScript: `cd solution/frontend && npm ci && npx tsc --noEmit`
- Docker: `cd solution && docker compose build`

### Phase 2: Type Check
- Python: `cd solution/backend && uv run mypy app/`
- TypeScript: `cd solution/frontend && npx tsc --noEmit --strict`

### Phase 3: Lint
- Python: `cd solution/backend && uv run ruff check app/ && uv run ruff format --check app/`
- TypeScript: `cd solution/frontend && npx biome check src/` or `npx eslint src/`

### Phase 4: Test Suite
- Python: `cd solution/backend && uv run pytest --tb=short -q`
- TypeScript: `cd solution/frontend && npx vitest run`

### Phase 5: Security Scan
- Python: `cd solution/backend && uv run bandit -r app/`
- TypeScript: `cd solution/frontend && npm audit`

### Phase 6: Diff Review
- `git diff --staged` review for unintended changes

4. **On failure**: Stop at the failing phase, report the error, and suggest fixes
5. **On success**: Report all phases passed

## Output
Verification report with pass/fail status for each phase and details on any failures.

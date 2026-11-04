# Project Structure Reference

**CRITICAL**: Git is initialized at PROJECT ROOT. All generated artifacts go in `solution/`.

## Full Project Structure

```
project-root/                        # Git repository root
├── .git/                            # Git initialized HERE
├── .gitignore                       # Project-wide ignores
├── problem/                         # Problem statement & supporting files
│   ├── PROBLEM.md                   # Main problem statement (required)
│   ├── *.pdf                        # Supplementary PDFs
│   ├── *.png, *.jpg                 # Diagrams, screenshots
│   └── data/                        # Example data files (optional)
├── .claude/                         # Claude Code config (if copied)
│
└── solution/                        # All generated artifacts
    ├── .github/
    │   └── workflows/               # Stage 5: CI/CD
    │       └── ci.yml               # GitHub Actions workflow
    │
    ├── requirements/                # Stage 1: Product Manager
    │   ├── requirements.md          # Functional & non-functional requirements
    │   ├── rice-scores.md           # RICE prioritization
    │   ├── moscow.md                # MoSCoW categorization
    │   └── mvp-scope.md             # MVP definition
    │
    ├── docs/
    │   ├── architecture/            # Stage 2: Architect
    │   │   ├── system-design.md     # Scale estimates, patterns, trade-offs
    │   │   ├── openapi.yaml         # API specification (OpenAPI 3.1)
    │   │   ├── database-schema.md   # Tables, indexes, relationships
    │   │   └── workspace.dsl        # C4 diagrams (Structurizr DSL)
    │   │
    │   └── decisions/               # Architecture Decision Records
    │       ├── ADR-001-*.md
    │       ├── ADR-002-*.md
    │       └── ADR-003-*.md
    │
    ├── backend/                     # Stage 3: Backend Developer
    │   │                            # Python (FastAPI) OR Node.js (Express)
    │   ├── app/ (Python)            # FastAPI application
    │   │   ├── main.py
    │   │   ├── models.py
    │   │   ├── database.py
    │   │   └── routers/
    │   ├── src/ (Node.js)           # Express.js application
    │   │   ├── index.ts
    │   │   ├── routes/
    │   │   └── utils/
    │   ├── tests/                   # Unit tests
    │   │   ├── conftest.py (Python)
    │   │   ├── test_*.py (Python)
    │   │   └── *.test.ts (Node.js)
    │   ├── pyproject.toml (Python)
    │   ├── package.json (Node.js)
    │   └── Dockerfile
    │
    ├── frontend/                    # Stage 3: Frontend Developer
    │   │                            # Next.js OR React+Vite
    │   ├── app/ (Next.js)           # App Router pages
    │   ├── src/ (Vite)              # React components
    │   ├── components/
    │   ├── tests/                   # Frontend tests
    │   │   └── *.test.tsx
    │   ├── package.json
    │   ├── nginx.conf (Vite only)   # For production SPA routing
    │   └── Dockerfile
    │
    ├── scripts/                     # Utility scripts
    │   └── test-e2e.sh              # E2E test script
    │
    ├── checkpoints/                 # Stage validations & reports
    │   ├── stage-0-validation.md
    │   ├── stage-1-validation.md
    │   ├── stage-2-validation.md
    │   ├── stage-3-validation.md
    │   ├── stage-4-validation.md
    │   ├── stage-4-bugs.md          # Bug fixes documented (if any)
    │   └── test-results.md          # Test output summary
    │
    ├── docker-compose.yml           # Container orchestration
    ├── docker-compose.dev.yml       # Dev overrides (optional)
    ├── README.md                    # Project documentation
    └── CHANGELOG.md                 # Version history
```

## Git Structure

**IMPORTANT**: Git is at PROJECT ROOT, not inside solution/

```
project-root/
├── .git/              # Git repository
├── .gitignore         # At project root
├── problem/           # Problem statement & files
│   ├── PROBLEM.md     # Main problem statement
│   └── ...            # Supporting files
└── solution/          # All artifacts (tracked by git)
```

## Files at Project Root

Only these should be at project root:
- `.git/` - Git repository
- `.gitignore` - Ignore patterns
- `problem/` - Problem statement folder
- `.claude/` - Claude Code configuration (optional)

## Files Allowed in solution/ Root

Only these files should be in the `solution/` root:
- `docker-compose.yml`
- `docker-compose.dev.yml` (optional)
- `README.md`
- `CHANGELOG.md`

## Files That MUST NOT Be in solution/ Root

These should go in subdirectories:
- Test results → `checkpoints/test-results.md`
- Stage summaries → `checkpoints/stage-N-validation.md`
- Bug reports → `checkpoints/stage-4-bugs.md`
- E2E scripts → `scripts/test-e2e.sh`
- Any `.md` documentation → appropriate subdirectory

## Naming Conventions

### Architecture Decision Records
```
ADR-{NNN}-{slug}.md
Example: ADR-001-database-postgresql.md
```

### Stage Checkpoints
```
stage-{N}-validation.md
stage-{N}-bugs.md (if bugs found)
```

### Test Files
```
# Backend (Python/pytest)
test_{module}.py
Example: test_items.py, test_users.py

# Backend (Node.js/Vitest)
{module}.test.ts
Example: validators.test.ts, events.test.ts

# Frontend (TypeScript/Vitest)
{Component}.test.tsx
Example: Button.test.tsx, ItemList.test.tsx
```

## Agent Responsibilities

| Stage | Agent | Output Directory |
|-------|-------|------------------|
| 0 | Orchestrator | Git init at root, creates `solution/` structure |
| 1 | Product Manager | `solution/requirements/` |
| 2 | Architect | `solution/docs/architecture/`, `solution/docs/decisions/` |
| 3 | Backend Dev | `solution/backend/` |
| 3 | Frontend Dev | `solution/frontend/` |
| 4 | Tester | `solution/backend/tests/`, `solution/frontend/tests/`, `solution/scripts/`, `solution/checkpoints/` |
| 5 | Orchestrator | `solution/README.md`, `solution/CHANGELOG.md`, `solution/.github/workflows/` |

## Working Directory Notes

**CRITICAL**: Stay at PROJECT ROOT throughout the pipeline. Do NOT cd into solution/.

- **Working directory**: Always PROJECT ROOT (where PROBLEM.md lives)
- **Git commands**: Run from project root
- **Output paths**: Use `solution/` prefix (e.g., `solution/requirements/`)
- **Docker commands**: `cd solution && docker compose up` (temporary cd, return to root)
- **Backend commands (Python)**: `cd solution/backend && uv run pytest` (temporary cd)
- **Backend commands (Node.js)**: `cd solution/backend && npm test` (temporary cd)
- **Frontend commands**: `cd solution/frontend && npm run dev` (temporary cd)

**Why stay at project root?**
- `problem/` folder with PROBLEM.md and supporting files must remain accessible
- Git repository is at project root
- Consistent path references across all stages

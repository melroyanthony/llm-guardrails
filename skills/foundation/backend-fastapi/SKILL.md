---
name: backend-fastapi
description: |
  Implements async FastAPI backends with SQLModel, Pydantic v2, and asyncpg.
  Use when building API endpoints, database models, or business logic.
  Triggers on: "FastAPI", "backend", "API", "endpoint", "SQLModel".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---


# Backend FastAPI Agent

Builds production-ready async FastAPI applications with SQLModel 0.0.22+ and Pydantic v2.

## Version Matrix (December 2025)

| Package | Version | Notes |
|---------|---------|-------|
| FastAPI | 0.115.x | Async-first |
| SQLModel | 0.0.22+ | Full Pydantic v2 support |
| Pydantic | 2.9.x | `field_validator`, `model_validator` |
| SQLAlchemy | 2.0.x | Required for async |
| asyncpg | 0.29.x | PostgreSQL async driver |
| Alembic | 1.17.x | Use `render_as_batch=True` |
| Python | 3.13.x | Use slim-bookworm for Docker |

## CRITICAL: Always Use `uv` for Python

**NEVER use these commands:**
- ❌ `python3 -m venv venv`
- ❌ `pip install`
- ❌ `pip freeze`

**ALWAYS use `uv` instead:**
- ✅ `uv init --app` (new project)
- ✅ `uv add <package>` (add deps — auto-creates .venv)
- ✅ `uv sync` (install from lockfile)
- ✅ `uv run <command>` (execute in venv)

## Project Initialization

**IMPORTANT**: Always use `uv` for Python project scaffolding. Never manually create pyproject.toml.

### Step 1: Initialize and Add Dependencies

```bash
cd solution

# Initialize project (creates pyproject.toml, .python-version)
uv init backend --app --python 3.13
cd backend

# Core dependencies (auto-creates .venv, updates uv.lock)
uv add fastapi uvicorn[standard] sqlmodel asyncpg pydantic-settings httpx alembic greenlet

# Dev dependencies
uv add --dev pytest pytest-asyncio aiosqlite ruff psycopg2-binary
```

### For Existing Project (pyproject.toml exists)

```bash
cd solution/backend

# Install all dependencies from lockfile (auto-creates .venv if needed)
uv sync
```

**CRITICAL**: `uv add` and `uv sync` auto-create the virtual environment. Never use `uv venv`, `python -m venv`, or `virtualenv` directly.

### Step 3: Initialize Alembic

```bash
# Initialize Alembic for migrations
uv run alembic init alembic
```

### Step 4: Create Directory Structure

```bash
# Create app structure
mkdir -p app/{api/v1,models,services,scripts}
touch app/__init__.py app/api/__init__.py app/api/v1/__init__.py
touch app/models/__init__.py app/services/__init__.py

# Create test structure
mkdir -p tests/api
touch tests/__init__.py tests/conftest.py
```

## Project Structure (Cognita-inspired modular pattern)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # pydantic-settings singleton
│   ├── database.py          # Async engine & session
│   ├── constants.py         # App-wide constants
│   ├── models/              # SQLModel tables
│   │   ├── __init__.py      # Export all models
│   │   └── {entity}.py
│   ├── modules/             # Pluggable feature modules (Cognita pattern)
│   │   ├── __init__.py
│   │   └── {feature}/
│   │       ├── __init__.py
│   │       ├── router.py    # Feature routes
│   │       ├── service.py   # Business logic
│   │       └── schemas.py   # Request/response models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py    # Aggregates all routes
│   │       └── {resource}.py
│   └── services/            # Shared business logic
│       ├── __init__.py
│       └── {domain}.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── api/
├── alembic/
│   ├── versions/
│   └── env.py
├── alembic.ini
├── pyproject.toml
└── Dockerfile
```

## When NOT to Use
- **Express.js/Node.js required**: See architect agent for Express.js stack — no dedicated Express skill exists yet
- **Serverless Lambda**: Use `backend-serverless-ts` skill — FastAPI is not optimized for Lambda cold starts
- **GraphQL API**: FastAPI can serve GraphQL via Strawberry, but for GraphQL-first projects consider dedicated frameworks
- **Static file serving**: Use nginx or CDN, not FastAPI
- **Long-running background tasks**: Use Celery/ARQ workers, not FastAPI endpoints with `BackgroundTasks` for >30s operations

## See Also

- `database` skill for Alembic migrations and query patterns
- `devops` skill for Docker and docker-compose setup

## References (progressive disclosure)

Load only when needed:

- [`references/core-patterns.md`](references/core-patterns.md)


## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll skip the reference docs and improvise" | Load the linked reference for the stack you're on — improvisation causes drift |
| "This is too small for the checklist" | Run the verification checklist anyway; small skips compound |

## Red Flags

- Implementing from memory instead of loading the relevant `references/` file
- Skipping health checks, CI, or project structure conventions in the skill

## Verification

- [ ] Version matrix followed for the chosen stack
- [ ] Required reference file(s) loaded for the work in progress
- [ ] Quality / When-NOT checklist reviewed

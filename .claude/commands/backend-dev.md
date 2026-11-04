---
description: Implement FastAPI backend with SQLModel (Stage 3)
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Backend Developer

Implement production-ready FastAPI backend based on architecture specs.

## Tech Stack
- Python 3.13 with `uv`
- FastAPI 0.115.x
- SQLModel 0.0.22+ (async)
- PostgreSQL with asyncpg

## Project Setup

```bash
cd solution
uv init backend --app --python 3.13
cd backend
uv add fastapi uvicorn[standard] sqlmodel asyncpg pydantic-settings httpx alembic greenlet
uv add --dev pytest pytest-asyncio aiosqlite ruff psycopg2-binary
```

## Code Structure
```
backend/
├── app/
│   ├── api/v1/          # Routers
│   ├── models/          # SQLModel definitions
│   ├── services/        # Business logic
│   ├── config.py        # Settings
│   ├── database.py      # Async engine
│   └── main.py          # FastAPI app
├── alembic/             # Migrations
└── tests/               # pytest tests
```

## Critical Patterns

### Async Database Sessions
```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

async_engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(bind=async_engine, class_=AsyncSession)
```

### Eager Loading (MUST use .unique())
```python
stmt = select(Parent).options(joinedload(Parent.children))
result = await db.execute(stmt)
items = result.scalars().unique().all()  # <-- MUST use unique()
```

### Explicit Joins
```python
stmt = (
    select(func.sum(Movement.quantity))
    .select_from(Movement)  # <-- Required
    .join(Item, Movement.item_id == Item.id)
)
```

## Implementation Flow (TDD)

Follow RED → GREEN → REFACTOR per endpoint. Do NOT write all code first.

1. Set up project structure (models, config, database, conftest.py)
2. For each endpoint in OpenAPI spec:
   - Write test (RED): `tests/test_<resource>.py`
   - Run test — must fail
   - Implement route + model (GREEN)
   - Run test — must pass
   - Commit with tests included
3. Create Dockerfile (multi-stage build)
4. Run linting: `uv run ruff check --fix`
5. Verify all pass: `uv run pytest tests/ -v`

## Run Commands
```bash
uv run uvicorn app.main:app --reload
```

## Input
- OpenAPI spec from `solution/docs/architecture/openapi.yaml`
- Database schema from `solution/docs/architecture/database-schema.md`

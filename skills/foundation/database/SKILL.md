---
name: database
description: |
  Manages PostgreSQL databases with Alembic migrations, asyncpg, and seed data.
  Use when creating migrations, seeding data, or optimizing queries.
  Triggers on: "database", "migration", "Alembic", "schema", "seed", "PostgreSQL".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Database Agent

Manages PostgreSQL databases with async patterns, Alembic migrations, and data seeding.

## Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| PostgreSQL | 17.x | Latest stable |
| asyncpg | 0.29.x | Async driver |
| SQLAlchemy | 2.0.x | Async support |
| SQLModel | 0.0.22+ | Pydantic v2 |
| Alembic | 1.17.x | `render_as_batch=True` |

## Project Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   └── {hash}_{description}.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
└── app/
    ├── database.py
    ├── models/
    └── scripts/
        └── seed.py
```

## Alembic Configuration

### alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
```

### alembic/env.py (Critical Settings)

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# Import all models so Alembic can detect them
from app.models import *  # noqa

config = context.config
fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # CRITICAL: For SQLite compatibility
        render_as_batch=True,
        # CRITICAL: For SQLModel types
        user_module_prefix="sqlmodel.sql.sqltypes.",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # CRITICAL: For SQLite compatibility
        render_as_batch=True,
        # CRITICAL: For SQLModel types
        user_module_prefix="sqlmodel.sql.sqltypes.",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### alembic/script.py.mako (Template)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes  # CRITICAL: Required for SQLModel types
${imports if imports else ""}

# revision identifiers
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

## Migration Commands

```bash
# Create new migration (using uv)
uv run alembic revision --autogenerate -m "add items table"

# Apply all migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current revision
uv run alembic current

# Show migration history
uv run alembic history
```

## Seed Data Pattern

### app/scripts/seed.py

```python
import asyncio
import csv
import json
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import async_session, init_db
from app.models import Location, MenuItem, Ingredient, Staff


async def load_csv(path: Path) -> list[dict]:
    """Load data from CSV file."""
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


async def load_json(path: Path) -> list[dict]:
    """Load data from JSON file."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


async def seed_locations(db: AsyncSession, data: list[dict]) -> dict[str, int]:
    """Seed locations and return name->id mapping."""
    location_map = {}

    for row in data:
        # Check if already exists
        stmt = select(Location).where(Location.name == row['name'])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            location_map[row['name']] = existing.id
            continue

        location = Location(
            name=row['name'],
            address=row.get('address', ''),
        )
        db.add(location)
        await db.flush()  # Get ID without committing
        location_map[row['name']] = location.id

    await db.commit()
    return location_map


async def seed_all(data_dir: Path) -> None:
    """Seed all data from directory."""
    async with async_session() as db:
        print("Seeding locations...")
        locations_data = await load_csv(data_dir / 'locations.csv')
        location_map = await seed_locations(db, locations_data)
        print(f"  Created {len(location_map)} locations")

        # Continue with other entities...
        print("Seeding complete!")


async def main():
    await init_db()

    data_dir = Path(__file__).parent.parent.parent / 'data'
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return

    await seed_all(data_dir)


if __name__ == '__main__':
    asyncio.run(main())
```

## Google Sheets Import (Optional)

```python
import httpx
import csv
from io import StringIO

SHEET_ID = "1r1XIqd82B8-2zVBBeXE1AkPoYmedLGqhHkGoTrqId7Y"

async def fetch_sheet_as_csv(sheet_name: str) -> list[dict]:
    """Fetch a Google Sheet tab as CSV."""
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

    reader = csv.DictReader(StringIO(response.text))
    return list(reader)


async def import_from_sheets():
    """Import all data from Google Sheets."""
    locations = await fetch_sheet_as_csv("Locations")
    ingredients = await fetch_sheet_as_csv("Ingredients")
    menu_items = await fetch_sheet_as_csv("Menu")
    # ... process and seed
```

## Connection Pooling

### Development (docker-compose)

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 5s
      retries: 5
```

### Production Pool Settings

```python
async_engine = create_async_engine(
    settings.database_url,
    pool_size=10,           # Base connections
    max_overflow=20,        # Burst capacity
    pool_pre_ping=True,     # Validate connections
    pool_recycle=300,       # Recycle after 5 min
    pool_use_lifo=True,     # Reuse recent connections
)
```

## Query Patterns

### Eager Loading (Avoid N+1)

```python
from sqlalchemy.orm import selectinload

stmt = (
    select(MenuItem)
    .options(selectinload(MenuItem.ingredients))
    .where(MenuItem.location_id == location_id)
)
result = await db.execute(stmt)
menu_items = result.scalars().all()
```

### Aggregations

```python
from sqlalchemy import func

stmt = (
    select(
        InventoryMovement.type,
        func.sum(InventoryMovement.quantity).label("total"),
        func.sum(InventoryMovement.cost).label("total_cost"),
    )
    .where(InventoryMovement.location_id == location_id)
    .group_by(InventoryMovement.type)
)
result = await db.execute(stmt)
summary = result.all()
```

## When NOT to Use
- **DynamoDB for key-value lookups**: Use `dynamodb-patterns` skill — PostgreSQL is overkill for simple key-value access
- **Aurora Serverless for Lambda**: Use `database-aurora-serverless` skill — it covers RDS Proxy and connection pooling patterns specific to serverless
- **Full-text search**: Use OpenSearch/Elasticsearch, not PostgreSQL (unless using pg_trgm for basic search)
- **Time-series data at scale**: Use TimescaleDB or InfluxDB
- **Graph relationships**: Use Neo4j or Neptune for heavily connected data

## Common Errors & Recovery

### Error: Alembic Migration Conflict
- **Symptom**: `alembic upgrade head` fails with "Can't locate revision"
- **Root Cause**: Multiple developers generated migrations from different branch points
- **Recovery**: `alembic merge heads -m "merge"` then `alembic upgrade head`
- **Prevention**: Always pull latest migrations before generating new ones

### Error: Async Session Deadlock
- **Symptom**: Request hangs indefinitely, no error logged
- **Root Cause**: Using sync operations inside async session (e.g., `session.execute()` without `await`)
- **Recovery**: Ensure all session operations use `await`; use `async_sessionmaker` not `sessionmaker`
- **Prevention**: Enable SQLAlchemy `echo=True` in dev to see all SQL queries

### Error: Foreign Key Constraint Violation
- **Symptom**: `IntegrityError: insert or update on table violates foreign key constraint`
- **Root Cause**: Referenced record doesn't exist or was deleted
- **Recovery**: Check data integrity; ensure parent records exist before child inserts
- **Prevention**: Use `ON DELETE CASCADE` or `SET NULL` in schema; validate references in application layer

## Quality Checklist

- [ ] All models have proper relationships defined
- [ ] Alembic env.py has `render_as_batch=True`
- [ ] Alembic env.py has `user_module_prefix`
- [ ] Migration runs cleanly on empty database
- [ ] Seed data loads without errors
- [ ] Foreign keys have proper indexes

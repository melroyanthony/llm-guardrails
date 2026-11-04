---
name: {{domain}}-backend
description: |
  Implements {{domain}} backend with FastAPI, SQLModel, and async patterns.
  Use when building API endpoints, database models, or business logic.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {{Domain}} Backend

## Extends

- `foundation/backend-fastapi`

## Domain Context

{{domain_context}}

## Project Structure

All code goes in `solution/backend/`:

```
solution/backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Settings with pydantic-settings
│   ├── database.py             # Async engine & session
│   ├── models/                 # SQLModel table definitions
│   │   ├── __init__.py
{{#models}}
│   │   ├── {{snake_name}}.py   # {{description}}
{{/models}}
│   ├── schemas/                # Pydantic request/response
│   │   ├── __init__.py
{{#schemas}}
│   │   ├── {{snake_name}}.py
{{/schemas}}
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # API router aggregation
{{#routers}}
│   │       ├── {{snake_name}}.py
{{/routers}}
│   └── services/               # Business logic
│       ├── __init__.py
{{#services}}
│       ├── {{snake_name}}.py
{{/services}}
├── tests/
│   ├── conftest.py
│   └── api/
├── alembic/
├── alembic.ini
├── pyproject.toml
└── Dockerfile
```

## Models

{{#models}}
### {{name}}

```python
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .{{related_import}} import {{related_model}}

class {{name}}Base(SQLModel):
    {{#fields}}
    {{name}}: {{type}}{{#default}} = {{default}}{{/default}}
    {{/fields}}

class {{name}}Create({{name}}Base):
    pass

class {{name}}Public({{name}}Base):
    id: int
    created_at: datetime

class {{name}}({{name}}Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    {{#relationships}}
    {{name}}: "{{type}}" = Relationship(back_populates="{{back_populates}}")
    {{/relationships}}
```

{{/models}}

## API Endpoints

{{#endpoints}}
### {{method}} {{path}}

**Purpose:** {{description}}

```python
@router.{{method_lower}}("{{path}}", response_model={{response_model}})
async def {{function_name}}(
    {{#params}}
    {{name}}: {{type}},
    {{/params}}
    db: AsyncSession = Depends(get_db)
) -> {{response_model}}:
    """{{description}}"""
    {{implementation_hint}}
```

{{/endpoints}}

## Business Rules

{{#business_rules}}
- **{{name}}**: {{description}}
  - Implementation: {{implementation}}
{{/business_rules}}

## Validation Criteria

{{#validation_criteria}}
- [ ] {{criterion}}
{{/validation_criteria}}

---
name: {{domain}}-testing
description: |
  Tests {{domain}} functionality with pytest-asyncio and Vitest.
  Use when writing tests, setting up fixtures, or validating behavior.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {{Domain}} Testing

## Extends

- `foundation/testing`

## Test Strategy

**Time Budget:** {{test_time_minutes}} minutes
**Focus:** Critical paths only (MVP features)

### Priority Order

1. **API contract tests** - Endpoints return expected shapes
2. **Business rule tests** - Core domain logic validation
3. **Integration tests** - End-to-end happy paths
4. **Edge cases** - Only for Must-Have features

## Backend Tests (pytest-asyncio)

### Fixtures

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db
from app.models import SQLModel

@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
```

### Test Cases

{{#backend_tests}}
#### {{name}}

```python
@pytest.mark.asyncio
async def test_{{snake_name}}(client: AsyncClient, db_session):
    """{{description}}"""
    # Arrange
    {{arrange}}

    # Act
    response = await client.{{method}}("{{path}}", json={{payload}})

    # Assert
    assert response.status_code == {{expected_status}}
    {{assertions}}
```

{{/backend_tests}}

## Frontend Tests (Vitest)

### Setup

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
  },
});
```

### Test Cases

{{#frontend_tests}}
#### {{name}}

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { {{component}} } from '@/components/{{path}}';

describe('{{component}}', () => {
  it('{{description}}', async () => {
    // Arrange
    {{arrange}}

    // Act
    render(<{{component}} {{props}} />);
    {{actions}}

    // Assert
    {{assertions}}
  });
});
```

{{/frontend_tests}}

## Validation Criteria

{{#validation_criteria}}
- [ ] {{criterion}}
{{/validation_criteria}}

---
name: testing
description: |
  Writes tests with pytest-asyncio for backend and Vitest for frontend.
  Use when writing tests, setting up fixtures, or validating behavior.
  Triggers on: "test", "pytest", "Vitest", "fixture", "coverage", "TDD".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Testing Agent

Implements testing strategies for time-constrained interview challenges.

## Philosophy for Interview Challenges

**Time is limited. Test strategically.**

1. **API contract tests** - Endpoints return expected shapes (highest ROI)
2. **Business rule tests** - Core domain logic (shows understanding)
3. **Happy path E2E** - One complete flow works
4. **Skip**: Edge cases, error handling (unless trivial)

## Backend Testing (pytest-asyncio)

### Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| pytest | 8.x | Core framework |
| pytest-asyncio | 0.24.x | `asyncio_mode = "auto"` |
| httpx | 0.27.x | Async test client |

### pyproject.toml

```toml
[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115.0",
    "sqlmodel>=0.0.22",
    "asyncpg>=0.29.0",
    "uvicorn>=0.32.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]
```

### tests/conftest.py

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.main import app
from app.api.deps import get_db


@pytest.fixture
async def db_engine():
    """Create fresh database engine for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for each test."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """Create test client with overridden database."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,  # CRITICAL: handles FastAPI 307 redirects
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_item():
    """Sample item data for tests."""
    return {
        "name": "Test Item",
        "quantity": 10,
    }
```

### Test Patterns

#### API Contract Test

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_items_returns_array(client: AsyncClient):
    """GET /items returns an array."""
    response = await client.get("/api/v1/items")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_item_returns_created(
    client: AsyncClient,
    sample_item: dict,
):
    """POST /items returns 201 with created item."""
    response = await client.post("/api/v1/items", json=sample_item)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_item["name"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """GET /items/{id} returns 404 for missing item."""
    response = await client.get("/api/v1/items/99999")

    assert response.status_code == 404
```

#### Business Rule Test

```python
@pytest.mark.asyncio
async def test_cannot_sell_without_stock(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Cannot sell item when insufficient stock."""
    # Arrange: Create item with 0 stock
    item = Item(name="Empty Item", quantity=0)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    # Act: Try to sell
    response = await client.post(
        f"/api/v1/items/{item.id}/sell",
        json={"quantity": 1},
    )

    # Assert: Rejected
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()
```

### Pre-Test Setup

```bash
cd solution/backend

# Install all dependencies from lockfile (auto-creates .venv if needed)
uv sync
```

### Running Tests

```bash
# Run all tests (using uv)
cd solution/backend && uv run pytest

# Run with output
uv run pytest -v

# Run specific test
uv run pytest tests/api/test_items.py::test_create_item

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing
```

**CRITICAL**: Always run `uv sync` before testing to ensure all dependencies are installed.

## Frontend Testing (Vitest)

### Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| Vitest | 2.x | Test runner |
| @testing-library/react | 16.x | React testing |
| @vitejs/plugin-react | 4.x | Required plugin |

### package.json

```json
{
  "devDependencies": {
    "vitest": "^2.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "jsdom": "^25.0.0"
  },
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

### vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
    include: ['**/*.test.{ts,tsx}'],
  },
});
```

### tests/setup.ts

```typescript
import '@testing-library/jest-dom/vitest';
```

### Component Test

```typescript
// components/items/__tests__/item-card.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ItemCard } from '../item-card';

describe('ItemCard', () => {
  it('renders item name and quantity', () => {
    const item = { id: 1, name: 'Test Item', quantity: 10 };

    render(<ItemCard item={item} />);

    expect(screen.getByText('Test Item')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('shows low stock warning when quantity < 5', () => {
    const item = { id: 1, name: 'Low Stock', quantity: 3 };

    render(<ItemCard item={item} />);

    expect(screen.getByText(/low stock/i)).toBeInTheDocument();
  });
});
```

### Pre-Test Setup (Frontend)

```bash
cd solution/frontend

# Load nvm and set Node version
source ~/.nvm/nvm.sh
nvm use 22 || nvm install 22

# Install dependencies
npm install
```

### Running Frontend Tests

```bash
# Run tests
cd solution/frontend && npm test

# Watch mode
npm run test:watch
```

**CRITICAL**: Always run `npm install` before testing to ensure all dependencies are installed.

## Time-Boxed Testing Strategy

For a 2-hour challenge (30 min testing budget):

| Test Type | Time | Count |
|-----------|------|-------|
| API contract tests | 10m | 5-6 tests |
| Business rule tests | 15m | 2-3 tests |
| Component tests | 5m | 1-2 tests |

For a 4-hour challenge (45 min testing budget):

| Test Type | Time | Count |
|-----------|------|-------|
| API contract tests | 15m | 8-10 tests |
| Business rule tests | 20m | 4-5 tests |
| Component tests | 10m | 3-4 tests |

## When NOT to Use
- **Serverless Lambda testing**: Use `testing-serverless` skill — it covers Lambda event mocking, DynamoDB Local, and LocalStack
- **Generated/boilerplate code**: Don't write tests for auto-generated code (Drizzle migrations, OpenAPI clients)
- **UI screenshot testing**: Use Playwright, not pytest/Vitest unit tests
- **Load/performance testing**: Use k6 or Artillery, not unit test frameworks

## Quality Checklist

- [ ] All MVP endpoints have contract tests
- [ ] Core business rules are tested
- [ ] Tests pass on clean database
- [ ] No flaky tests
- [ ] Test names describe behavior

## Algorithm & Numerical Testing

### Worked Examples as Ground Truth
When the problem statement provides worked examples with expected outputs, use them as regression tests:

```python
# Python — expected value from PROBLEM.md worked example
EXPECTED_LATENCY = 6553.6  # From Example 1A in PROBLEM.md

def test_example_1a_baseline():
    """Regression test from PROBLEM.md Example 1A."""
    problem = load_problem("examples/example_1a.json")
    result = solve(problem)
    assert abs(result.total_latency - EXPECTED_LATENCY) < 1.0  # Tolerance: 1.0
```

```typescript
// TypeScript — expected value from PROBLEM.md worked example
const EXPECTED_LATENCY = 6553.6; // From Example 1A in PROBLEM.md

test('example 1a baseline matches expected latency', () => {
  const problem = loadProblem('examples/example_1a.json');
  const result = solve(problem);
  expect(Math.abs(result.totalLatency - EXPECTED_LATENCY)).toBeLessThan(1.0);
});
```

### Tolerance-Based Assertions
For floating-point results, always use tolerance:

| Framework | Syntax | Notes |
|-----------|--------|-------|
| pytest | `assert abs(actual - expected) < delta` | Explicit delta |
| pytest | `pytest.approx(expected, abs=delta)` | Built-in |
| Vitest | `expect(actual).toBeCloseTo(expected, digits)` | Decimal places |
| Rust | `assert!((actual - expected).abs() < delta)` | Manual |

### Testing Intermediate Results
Don't just test final output — test intermediate computation:

```python
# Test the latency model, not just the optimizer
def test_latency_calculation():
    latency = compute_latency(subgraph, granularity)
    assert abs(latency - expected_latency) < 0.5

# Test the memory model
def test_working_set_within_capacity():
    ws = compute_working_set(subgraph, retained_tensors)
    assert ws <= problem.fast_memory_capacity

# Test constraint satisfaction
def test_all_ops_covered():
    solution = optimize(problem)
    covered = set()
    for sg in solution.subgraphs:
        covered.update(sg)
    assert covered == set(range(problem.num_ops))
```

### Optimization Testing Pattern
For optimizers, test that:
1. **Baseline is correct** (trivial solution satisfies all constraints)
2. **Optimized beats baseline** (strictly, not equal)
3. **Constraints are never violated** (even after optimization)
4. **Edge cases handled** (single op, all separate, fully merged)

```python
def test_optimizer_beats_baseline():
    baseline = solve_baseline(problem)
    optimized = solve_optimized(problem)
    assert optimized.total_latency < baseline.total_latency

def test_optimizer_respects_memory():
    solution = solve_optimized(problem)
    for sg in solution.subgraphs:
        ws = compute_working_set(sg)
        assert ws <= problem.memory_capacity
```

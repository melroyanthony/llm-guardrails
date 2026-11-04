---
description: Write tests, validate Docker, run E2E happy path, and fix bugs (Stage 4)
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# QA Engineer

Comprehensive testing including unit tests, Docker validation, and E2E happy path.

## Output Structure (CRITICAL)

**Follow this structure - NO files in solution/ root:**
```
solution/
├── backend/tests/          # Unit tests
├── scripts/                # E2E and utility scripts
│   └── test-e2e.sh
├── checkpoints/            # Test reports
│   ├── stage-4-validation.md
│   ├── stage-4-bugs.md
│   └── test-results.md
└── ...
```

## Stage 4 Flow

### 4.1: Write Unit Tests

#### Backend (pytest-asyncio)

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
```

**Critical**: Use `follow_redirects=True`:
```python
async with AsyncClient(
    transport=ASGITransport(app=app),
    base_url="http://test",
    follow_redirects=True,  # <-- CRITICAL for FastAPI
) as ac:
    yield ac
```

#### Run Unit Tests
```bash
cd solution/backend
uv sync
uv run pytest tests/ -v
```

---

### 4.2: Docker Compose Validation

**Start all services:**
```bash
cd solution
docker compose up --build -d
```

**Verify services are healthy:**
```bash
docker compose ps
# All services should show "Up" status
```

**Check for errors in logs:**
```bash
docker compose logs --tail=100
# Look for: connection errors, import errors, startup failures
```

**Common issues to fix:**
- Database connection timing (add healthcheck/wait)
- Missing environment variables
- Port conflicts
- Import errors in Python/Node

---

### 4.3: Happy Path E2E Test

With Docker running, test ONE complete CRUD flow:

```bash
# 1. Health check
curl -s http://localhost:8000/health
# Expected: {"status": "healthy"} or 200 OK

# 2. Create a resource
curl -s -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "quantity": 10}'
# Expected: 201 with created item

# 3. List resources
curl -s http://localhost:8000/api/v1/items
# Expected: Array containing the created item

# 4. Get single resource
curl -s http://localhost:8000/api/v1/items/1
# Expected: The created item

# 5. Update resource
curl -s -X PUT http://localhost:8000/api/v1/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Item", "quantity": 20}'
# Expected: 200 with updated item

# 6. Delete resource
curl -s -X DELETE http://localhost:8000/api/v1/items/1
# Expected: 200 or 204

# 7. Verify deletion
curl -s http://localhost:8000/api/v1/items/1
# Expected: 404 Not Found
```

---

### 4.4: Bug Fix Loop

**If ANY test or E2E step fails:**

1. **Document the bug:**
```bash
echo "## Bug: [description]
- Symptom: [what failed]
- Cause: [root cause]
- Fix: [what was changed]
" >> solution/checkpoints/stage-4-bugs.md
```

2. **Fix the issue** in the relevant code

3. **Re-run tests:**
```bash
cd solution/backend && uv run pytest tests/ -v
```

4. **Commit the fix:**
```bash
cd solution && git add . && git commit -m "fix: [description of bug fix]"
```

5. **Repeat** until:
   - All unit tests pass
   - Docker Compose starts cleanly
   - Happy path E2E works completely

---

### 4.5: Final Validation

```bash
# Run all tests one final time
cd solution/backend && uv run pytest tests/ -v

# Verify Docker still works
cd solution && docker compose up -d
curl -s http://localhost:8000/health
docker compose down
```

---

## Testing Priorities

1. **Critical Path**: Main business workflows (CRUD)
2. **Error Cases**: 404, 400, 422 responses
3. **Validation**: Required fields, constraints
4. **Edge Cases**: Empty states, boundary values
5. **Business Logic**: Domain-specific rules

---

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| 307 instead of 200 | Missing `follow_redirects=True` | Add to AsyncClient |
| State leaks between tests | `scope="session"` fixtures | Use `scope="function"` |
| Database not ready | No healthcheck | Add `depends_on` with condition |
| Import errors | Missing `__init__.py` | Add init files |

---

## Write Stage 4 Checkpoint

**Create `solution/checkpoints/stage-4-validation.md`:**
```markdown
# Stage 4: Testing & Validation

## Summary
- **Status**: PASS
- **Unit Tests**: [N] passing
- **Docker**: All services healthy
- **E2E**: Happy path verified

## Test Results
[Paste pytest output summary]

## Bug Fixes Applied
[List fixes or "None"]

## Ready for Stage 5: Yes
```

**If creating E2E script, place in `solution/scripts/test-e2e.sh`**

---

## Handoff Summary

```
Stage 4 Complete

Unit Tests: [N] passing
Docker: All services healthy
E2E Happy Path: CRUD flow verified
Bug Fixes: [M] issues resolved

Ready for Stage 5: Finalization
```

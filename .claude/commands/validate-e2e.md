---
description: Validate Docker Compose and run E2E happy path test
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# E2E Validation

Validate that Docker Compose works and run a happy path E2E test.

## Usage

Run this after implementation to verify the full stack works:
```
/validate-e2e
```

## Validation Steps

### 1. Start Docker Compose

```bash
cd solution
docker compose up --build -d
```

Wait for services to be ready (up to 30 seconds):
```bash
sleep 10
docker compose ps
```

### 2. Check Service Health

```bash
# Check all services are running
docker compose ps

# Check logs for errors
docker compose logs --tail=50

# Verify backend is responding
curl -s http://localhost:8000/health || echo "Backend not ready"

# Verify frontend is responding (if applicable)
curl -s http://localhost:3000 || echo "Frontend not ready"
```

### 3. Happy Path E2E Test

Run a complete CRUD flow against the API:

```bash
echo "=== E2E Happy Path Test ==="

# 1. Health check
echo "1. Health check..."
curl -s http://localhost:8000/health
echo ""

# 2. Create resource
echo "2. Creating resource..."
CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "E2E Test Item", "quantity": 100}')
echo "$CREATE_RESPONSE"
echo ""

# 3. List resources
echo "3. Listing resources..."
curl -s http://localhost:8000/api/v1/items
echo ""

# 4. Get single resource
echo "4. Getting single resource..."
curl -s http://localhost:8000/api/v1/items/1
echo ""

# 5. Update resource
echo "5. Updating resource..."
curl -s -X PUT http://localhost:8000/api/v1/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated E2E Item", "quantity": 200}'
echo ""

# 6. Delete resource
echo "6. Deleting resource..."
curl -s -X DELETE http://localhost:8000/api/v1/items/1
echo ""

# 7. Verify deletion
echo "7. Verifying deletion (should 404)..."
curl -s http://localhost:8000/api/v1/items/1
echo ""

echo "=== E2E Test Complete ==="
```

### 4. Cleanup

```bash
docker compose down
```

## Expected Results

| Step | Expected |
|------|----------|
| Health check | 200 OK or `{"status": "healthy"}` |
| Create | 201 Created with resource |
| List | 200 with array containing resource |
| Get | 200 with single resource |
| Update | 200 with updated resource |
| Delete | 200 or 204 |
| Verify deletion | 404 Not Found |

## If Tests Fail

1. Check Docker logs: `docker compose logs backend`
2. Identify the failing step
3. Fix the issue in the code
4. Re-run: `/validate-e2e`

## Output

On success:
```
E2E Validation Passed

- Docker Compose: All services healthy
- Health check: OK
- CRUD operations: All working
- Cleanup: Complete
```

On failure:
```
E2E Validation Failed

- Failed step: [step name]
- Error: [error message]
- Suggested fix: [what to check]
```

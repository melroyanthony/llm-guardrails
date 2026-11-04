---
name: performance-optimization
description: |
  Measure-first performance profiling workflows for backend, frontend, and database.
  Core Web Vitals, query optimization, bundle analysis, cold start reduction.
  Use when diagnosing slowness or optimizing backend, frontend, or database performance.
  Triggers on: "slow", "performance", "optimize", "latency", "bundle size", "N+1", "cold start".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, WebFetch
---

# Performance Optimization

## Principle

Measure first, optimize second. Never optimize without a baseline metric. Never assume you know the bottleneck — profile it.

## Workflow

### 1. Establish Baseline

Before any optimization, measure the current state:

```bash
# Backend: response time
curl -w "\n%{time_total}s" http://localhost:8000/api/v1/endpoint

# Frontend: bundle size
npx next build 2>&1 | grep "First Load JS"
# or
npx vite build --report

# Database: query execution
psql -c "EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';"
```

Record the baseline in a structured format:
```
BASELINE: endpoint=/api/v1/users, p50=45ms, p95=120ms, p99=350ms
BASELINE: bundle_size=245KB (gzipped), first_load_js=89KB
BASELINE: query=user_by_email, rows=1, time=2.3ms, seq_scan=false
```

### 2. Identify Bottleneck

| Symptom | Likely Cause | Investigation |
|---|---|---|
| Slow API response (>200ms) | N+1 queries, missing index, sync I/O | Check query count per request, `EXPLAIN ANALYZE` |
| Large bundle (>500KB gzip) | Unused dependencies, no tree-shaking | Bundle analyzer, `import` audit |
| Slow cold start (>3s) | Large dependency tree, no lazy loading | Lambda layers, provisioned concurrency |
| High memory usage | Unbounded collections, no pagination | Memory profiling, cursor-based pagination |
| Slow database queries | Missing indexes, full table scans | `EXPLAIN ANALYZE`, check index coverage |

### 3. Apply Fix

Fix the specific bottleneck identified — do NOT apply general "optimization tips."

### 4. Measure Again

Compare against baseline. If improvement is < 5%, the fix may not be worth the complexity.

## Backend Performance

### N+1 Query Detection

```python
# BAD: N+1 — one query per user's posts
users = db.query(User).all()
for user in users:
    posts = db.query(Post).filter(Post.user_id == user.id).all()  # N queries

# GOOD: Eager loading — one query total
users = db.query(User).options(joinedload(User.posts)).all()
```

### Database Index Strategy

| Query Pattern | Index Type | Example |
|---|---|---|
| Equality (`WHERE x = ?`) | B-tree (default) | `CREATE INDEX idx_email ON users(email)` |
| Range (`WHERE x > ?`) | B-tree | `CREATE INDEX idx_created ON orders(created_at)` |
| Full-text search | GIN | `CREATE INDEX idx_search ON docs USING gin(tsv)` |
| JSON field access | GIN | `CREATE INDEX idx_meta ON items USING gin(metadata)` |
| Composite filter | Composite B-tree | `CREATE INDEX idx_tenant_date ON orders(tenant_id, created_at)` |

### Connection Pooling

| Environment | Solution | Config |
|---|---|---|
| FastAPI + PostgreSQL | asyncpg pool | `min_size=5, max_size=15` |
| Lambda + PostgreSQL | RDS Proxy | Managed, IAM auth |
| Express + PostgreSQL | pg-pool | `max: 20, idleTimeoutMillis: 30000` |

### Serverless Cold Start Reduction

| Technique | Impact | Cost |
|---|---|---|
| Provisioned concurrency | Eliminates cold start | ~$5.80/month per instance |
| Lambda layers | Reduces deployment size | Free (complexity cost) |
| Lazy imports | Faster module load | Free |
| ARM64 architecture | 20% faster, 20% cheaper | Free (change platform) |

## Frontend Performance

### Core Web Vitals Targets

| Metric | Good | Needs Improvement | Poor |
|---|---|---|---|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5s - 4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | 200ms - 500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1 - 0.25 | > 0.25 |

### Bundle Optimization

| Technique | When to Apply |
|---|---|
| Code splitting (dynamic import) | Routes, modals, heavy components |
| Tree shaking | Always (verify with bundle analyzer) |
| Image optimization (next/image, sharp) | Any page with images |
| Font subsetting | Custom fonts > 50KB |
| CSS purging (Tailwind JIT) | Always enabled by default |

## Database Performance

### Query Optimization Checklist

- [ ] All `WHERE` columns have appropriate indexes
- [ ] All `JOIN` columns have indexes on both sides
- [ ] All `ORDER BY` columns are indexed (or composite with WHERE columns)
- [ ] No `SELECT *` — only select needed columns
- [ ] Pagination uses cursor-based (not OFFSET) for large tables
- [ ] No N+1 queries (use eager loading or batch queries)
- [ ] `EXPLAIN ANALYZE` shows index scans, not sequential scans

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Premature optimization is the root of all evil" | Measurement is not optimization. Measure first, then decide if optimization is needed. |
| "It's fast enough on my machine" | Your machine has 32GB RAM and NVMe. Production has network latency, concurrent users, and cold starts. |
| "We can optimize later if it's slow" | N+1 queries at scale require schema changes. Designing efficient queries now costs minutes; fixing later costs days. |
| "Adding an index will fix it" | Indexes speed up reads but slow writes. Profile first to confirm reads are the bottleneck. |

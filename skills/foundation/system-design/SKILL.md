---
name: system-design
description: |
  System design fundamentals for architecture decisions.
  Use when designing scalable, reliable, and maintainable systems.
  Triggers on: "system design", "scalability", "reliability", "load balancing", "caching", "CAP theorem".
  Reference: github.com/donnemartin/system-design-primer
allowed-tools: Read, Glob, Grep, Write
---

# System Design Knowledge Base

Reference this skill during Stage 2 (Architecture) to make informed design decisions.

## Core Trade-offs

### Performance vs Scalability
- **Performance**: How fast a single request is handled
- **Scalability**: How the system handles increased load

| Approach | When to Use |
|----------|-------------|
| Vertical scaling | Simple apps, quick wins, < 10k users |
| Horizontal scaling | High availability, > 10k users |

### Latency vs Throughput
- **Latency**: Time to complete a single request (ms)
- **Throughput**: Requests handled per second (RPS)
- **Goal**: Maximize throughput while keeping latency acceptable

### Availability vs Consistency (CAP Theorem)

| Pattern | Availability | Consistency | Use Case |
|---------|--------------|-------------|----------|
| CP | Sacrifice availability | Strong consistency | Banking, inventory |
| AP | Always available | Eventual consistency | Social feeds, analytics |

**For coding challenges**: Default to **CP** (consistency) unless requirements specify otherwise.

---

## Scalability Patterns

### Database Scaling

#### Read Replicas
```
┌─────────┐     ┌─────────┐
│ Primary │────▶│ Replica │ (reads)
│  (R/W)  │     └─────────┘
└─────────┘     ┌─────────┐
                │ Replica │ (reads)
                └─────────┘
```

**When**: Read-heavy workloads (> 10:1 read/write ratio)
**ADR**: Document if implementing read replicas

#### Sharding (Partitioning)
```
┌─────────────────────────────────────┐
│           Shard Router              │
└─────────────────────────────────────┘
        │           │           │
   ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
   │Shard A │  │Shard B │  │Shard C │
   │ A-H    │  │ I-P    │  │ Q-Z    │
   └────────┘  └────────┘  └────────┘
```

**When**: Single database can't handle load
**Shard keys**: User ID, tenant ID, geographic region
**ADR**: Document sharding strategy if needed

### Caching Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Cache-aside | App checks cache, then DB | General purpose |
| Write-through | Write to cache and DB | Data consistency critical |
| Write-behind | Write to cache, async to DB | High write throughput |
| Refresh-ahead | Proactively refresh before expiry | Predictable access patterns |

**Default for challenges**: Cache-aside with Redis/in-memory

```python
# Cache-aside pattern
async def get_item(item_id: int) -> Item:
    # Check cache first
    cached = await cache.get(f"item:{item_id}")
    if cached:
        return cached

    # Cache miss - fetch from DB
    item = await db.get(item_id)
    await cache.set(f"item:{item_id}", item, ttl=300)
    return item
```

### Load Balancing

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| Round robin | Rotate through servers | Equal server capacity |
| Least connections | Route to least busy | Variable request duration |
| IP hash | Same client → same server | Session affinity |
| Weighted | Distribute by capacity | Mixed server specs |

**For Docker Compose**: Use Traefik or nginx as reverse proxy

---

## Communication Patterns

### Synchronous (REST/HTTP)

```
Client ──▶ API Gateway ──▶ Service A
                      └──▶ Service B
```

**Use for**: User-facing APIs, CRUD operations
**Default for challenges**: REST with OpenAPI spec

### Asynchronous (Message Queue)

```
Producer ──▶ Queue ──▶ Consumer
              │
              └──▶ Consumer
```

**Use for**:
- Long-running tasks (email, reports)
- Decoupling services
- Handling traffic spikes

**Technologies**: Redis Queue, RabbitMQ, Celery

---

## Database Selection

### When to Use SQL (PostgreSQL)

✅ ACID transactions required
✅ Complex queries with JOINs
✅ Structured data with relationships
✅ Data integrity is critical

**Default for challenges**: PostgreSQL

### When to Use NoSQL

| Type | Use Case | Example |
|------|----------|---------|
| Document (MongoDB) | Flexible schema, nested data | User profiles, product catalogs |
| Key-Value (Redis) | Caching, sessions, counters | Shopping carts, rate limiting |
| Graph (Neo4j) | Relationships are the data | Social networks, recommendations |
| Time-series (InfluxDB) | Metrics, logs, IoT | Monitoring, analytics |

---

## Security Fundamentals

### API Security Checklist

- [ ] Authentication (JWT, OAuth2)
- [ ] Authorization (RBAC, permissions)
- [ ] Input validation (Pydantic)
- [ ] Rate limiting
- [ ] HTTPS only
- [ ] CORS configuration
- [ ] SQL injection prevention (ORM)
- [ ] XSS prevention (escape output)

### Default Security Setup

```python
# FastAPI security
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected")
async def protected_route(token: str = Security(security)):
    # Validate token
    pass
```

---

## Back-of-Envelope Calculations

### Quick Estimates

| Metric | Value |
|--------|-------|
| Read from memory | 100 ns |
| Read from SSD | 100 μs |
| Read from disk | 10 ms |
| Network round trip | 1-100 ms |

### Capacity Planning

```
Users: 100,000
Active daily: 10% = 10,000
Requests/user/day: 10
Total requests/day: 100,000

Requests/second: 100,000 / 86,400 ≈ 1.2 RPS
Peak (10x): 12 RPS

Single server can handle: 100-1000 RPS
→ Single server sufficient for MVP
```

---

## Architecture Decision Record (ADR) Templates

### ADR: Database Choice

```markdown
# ADR-001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
Need a database for [application type].
Expected load: [X] users, [Y] transactions/day.

## Decision
Use PostgreSQL because:
- ACID compliance for [reason]
- Rich query capabilities for [use case]
- Strong ecosystem (SQLModel, Alembic)

## Consequences
- Need to manage connection pooling
- Schema migrations required
- Good: Mature tooling, team familiarity
```

### ADR: Caching Strategy

```markdown
# ADR-002: Implement Cache-Aside with Redis

## Status
Accepted

## Context
[Endpoint/feature] has high read frequency.
Current latency: [X]ms, target: [Y]ms.

## Decision
Implement cache-aside pattern with Redis.
TTL: [duration] based on data freshness requirements.

## Consequences
- Cache invalidation needed on writes
- Additional infrastructure (Redis container)
- Good: Significant latency reduction
```

---

## Design Checklist for Stage 2

Before completing architecture:

### Scalability
- [ ] Identified potential bottlenecks
- [ ] Database can handle expected load
- [ ] Caching strategy defined (if needed)
- [ ] Stateless services for horizontal scaling

### Reliability
- [ ] Single points of failure identified
- [ ] Error handling strategy defined
- [ ] Health check endpoints planned
- [ ] Retry/timeout policies considered

### Data
- [ ] Data model normalized appropriately
- [ ] Indexes planned for query patterns
- [ ] Backup/recovery considered
- [ ] Data consistency requirements clear

### Security
- [ ] Authentication method chosen
- [ ] Authorization model defined
- [ ] Input validation planned
- [ ] Sensitive data handling addressed

---

## Quick Reference: Technology Choices

### For 2-4 Hour Challenges (Default Stack)

| Layer | Technology | Reason |
|-------|------------|--------|
| Frontend | Next.js 15 | SSR, TypeScript, fast setup |
| Backend | FastAPI | Async, auto-docs, Pydantic |
| Database | PostgreSQL | ACID, mature, SQLModel |
| Cache | Redis (optional) | Simple, fast, Docker-ready |
| Container | Docker Compose | Single command deploy |

### When to Deviate

| Requirement | Consider |
|-------------|----------|
| Real-time updates | WebSockets, SSE |
| File uploads | S3-compatible storage |
| Full-text search | Elasticsearch, PostgreSQL FTS |
| Graph relationships | Neo4j, or PostgreSQL with recursive CTEs |
| High write volume | Write-behind caching, queue processing |

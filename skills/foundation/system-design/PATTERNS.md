# System Design Patterns

Quick reference for common architectural patterns.

## API Design Patterns

### RESTful Resource Naming

```
GET    /api/v1/items          # List
POST   /api/v1/items          # Create
GET    /api/v1/items/{id}     # Read
PUT    /api/v1/items/{id}     # Update (full)
PATCH  /api/v1/items/{id}     # Update (partial)
DELETE /api/v1/items/{id}     # Delete

# Nested resources
GET    /api/v1/users/{id}/orders
POST   /api/v1/users/{id}/orders

# Actions (when CRUD doesn't fit)
POST   /api/v1/orders/{id}/cancel
POST   /api/v1/users/{id}/activate
```

### Pagination Patterns

```python
# Offset-based (simple, good for small datasets)
GET /api/v1/items?offset=0&limit=20

# Cursor-based (better for large datasets)
GET /api/v1/items?cursor=abc123&limit=20

# Response format
{
  "data": [...],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "next_cursor": "abc124"
  }
}
```

### Error Response Pattern

```python
# Consistent error format
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}

# FastAPI implementation
from fastapi import HTTPException

class APIError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message}
        )
```

---

## Database Patterns

### Repository Pattern

```python
# Abstract data access from business logic
class ItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, item_id: int) -> Item | None:
        return await self.db.get(Item, item_id)

    async def list(self, skip: int = 0, limit: int = 100) -> list[Item]:
        stmt = select(Item).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, item: ItemCreate) -> Item:
        db_item = Item(**item.model_dump())
        self.db.add(db_item)
        await self.db.commit()
        await self.db.refresh(db_item)
        return db_item
```

### Unit of Work Pattern

```python
# Coordinate multiple operations
class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.items = ItemRepository(session)
        self.orders = OrderRepository(session)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

# Usage
async with UnitOfWork(db) as uow:
    item = await uow.items.create(item_data)
    order = await uow.orders.create(order_data)
    await uow.commit()
```

### Soft Delete Pattern

```python
class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    deleted_at: datetime | None = None  # Soft delete marker

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

# Query active items only
stmt = select(Item).where(Item.deleted_at.is_(None))
```

---

## Service Patterns

### Service Layer Pattern

```python
# Business logic separate from API handlers
class ItemService:
    def __init__(self, repo: ItemRepository, cache: Cache):
        self.repo = repo
        self.cache = cache

    async def get_item(self, item_id: int) -> Item:
        # Check cache
        cached = await self.cache.get(f"item:{item_id}")
        if cached:
            return cached

        # Fetch from DB
        item = await self.repo.get(item_id)
        if not item:
            raise ItemNotFoundError(item_id)

        # Cache result
        await self.cache.set(f"item:{item_id}", item)
        return item

    async def create_item(self, data: ItemCreate) -> Item:
        # Business validation
        await self._validate_item(data)

        # Create
        item = await self.repo.create(data)

        # Side effects (events, notifications)
        await self._notify_item_created(item)

        return item
```

### Dependency Injection Pattern

```python
# FastAPI dependency injection
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

def get_item_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ItemService:
    return ItemService(
        repo=ItemRepository(db),
        cache=get_cache(settings),
    )

@app.get("/items/{id}")
async def get_item(
    id: int,
    service: ItemService = Depends(get_item_service),
):
    return await service.get_item(id)
```

---

## Resilience Patterns

### Circuit Breaker

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self.failures = 0
        self.threshold = failure_threshold
        self.is_open = False

    async def call(self, func, *args, **kwargs):
        if self.is_open:
            raise ServiceUnavailableError()

        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.threshold:
                self.is_open = True
            raise

# Using tenacity for retries
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def call_external_service():
    # Will retry 3 times with exponential backoff
    pass
```

### Timeout Pattern

```python
import asyncio

async def with_timeout(coro, timeout_seconds: float):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise ServiceTimeoutError()

# Usage
result = await with_timeout(external_api.call(), timeout_seconds=5.0)
```

### Bulkhead Pattern

```python
# Limit concurrent requests to protect resources
from asyncio import Semaphore

class Bulkhead:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = Semaphore(max_concurrent)

    async def execute(self, func, *args, **kwargs):
        async with self.semaphore:
            return await func(*args, **kwargs)

# Usage
db_bulkhead = Bulkhead(max_concurrent=20)
result = await db_bulkhead.execute(query_database, params)
```

---

## Event Patterns

### Event Sourcing (Simplified)

```python
class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    aggregate_id: str
    event_type: str
    payload: dict
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderEventStore:
    async def append(self, order_id: str, event_type: str, data: dict):
        event = Event(
            aggregate_id=order_id,
            event_type=event_type,
            payload=data,
        )
        self.db.add(event)
        await self.db.commit()

    async def get_history(self, order_id: str) -> list[Event]:
        stmt = select(Event).where(Event.aggregate_id == order_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
```

### Outbox Pattern (for reliable events)

```python
class Outbox(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_type: str
    payload: dict
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# In transaction: write to outbox
async def create_order_with_event(order_data: OrderCreate):
    async with db.begin():
        order = Order(**order_data.model_dump())
        db.add(order)

        # Add to outbox (same transaction)
        outbox = Outbox(
            event_type="order.created",
            payload={"order_id": order.id},
        )
        db.add(outbox)

# Separate worker: process outbox
async def process_outbox():
    events = await get_unprocessed_events()
    for event in events:
        await publish_event(event)
        event.processed = True
        await db.commit()
```

---

## Caching Patterns

### Cache-Aside (Lazy Loading)

```python
async def get_item(item_id: int) -> Item:
    cache_key = f"item:{item_id}"

    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        return Item.model_validate_json(cached)

    # Cache miss
    item = await db.get(Item, item_id)
    if item:
        await redis.setex(cache_key, 300, item.model_dump_json())

    return item
```

### Write-Through

```python
async def update_item(item_id: int, data: ItemUpdate) -> Item:
    # Update DB
    item = await db.get(Item, item_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()

    # Update cache (synchronously)
    cache_key = f"item:{item_id}"
    await redis.setex(cache_key, 300, item.model_dump_json())

    return item
```

### Cache Invalidation

```python
async def delete_item(item_id: int):
    # Delete from DB
    await db.delete(Item, item_id)
    await db.commit()

    # Invalidate cache
    await redis.delete(f"item:{item_id}")

    # Invalidate related caches
    await redis.delete("items:list")
```

---

## Logging Patterns

### Secure Logger with PII Redaction

**CRITICAL**: Never log sensitive data. Implement automatic redaction.

```typescript
// TypeScript (Node.js)
const SENSITIVE_PATTERNS = [
  { regex: /\b[\w.-]+@[\w.-]+\.\w{2,}\b/gi, replacement: '[EMAIL]' },
  { regex: /\b(sk-|pk_|api[_-]?key)[a-zA-Z0-9]{20,}/gi, replacement: '[API_KEY]' },
  { regex: /\b\d{13,16}\b/g, replacement: '[CARD]' },
  { regex: /\b\d{3}-\d{2}-\d{4}\b/g, replacement: '[SSN]' },
  { regex: /\+?\d{10,15}/g, replacement: '[PHONE]' },
];

const SENSITIVE_KEYS = ['password', 'apiKey', 'secret', 'token', 'authorization'];

function redact(value: unknown): unknown {
  if (typeof value === 'string') {
    let result = value.length > 500 ? value.slice(0, 500) + '...[TRUNCATED]' : value;
    return SENSITIVE_PATTERNS.reduce(
      (str, { regex, replacement }) => str.replace(regex, replacement),
      result
    );
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [
        k,
        SENSITIVE_KEYS.some((key) => k.toLowerCase().includes(key)) ? '[REDACTED]' : redact(v),
      ])
    );
  }
  return value;
}
```

### Structured JSON Logging

```typescript
const LOG_LEVELS = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
const currentLevel = LOG_LEVELS[process.env.LOG_LEVEL || 'INFO'];

export const logger = {
  debug: (component: string, message: string, context?: object) => {
    if (currentLevel <= LOG_LEVELS.DEBUG) {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'DEBUG',
        component,
        message,
        ...(context && { context: redact(context) }),
      }));
    }
  },
  info: (component: string, message: string, context?: object) => {
    if (currentLevel <= LOG_LEVELS.INFO) {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'INFO',
        component,
        message,
        ...(context && { context: redact(context) }),
      }));
    }
  },
  warn: (component: string, message: string, context?: object) => {
    if (currentLevel <= LOG_LEVELS.WARN) {
      console.warn(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'WARN',
        component,
        message,
        ...(context && { context: redact(context) }),
      }));
    }
  },
  error: (component: string, message: string, error?: unknown) => {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'ERROR',
      component,
      message,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    }));
  },
};
```

### Python Logging

```python
import logging
import json
import re
from datetime import datetime

SENSITIVE_PATTERNS = [
    (re.compile(r'\b[\w.-]+@[\w.-]+\.\w{2,}\b', re.I), '[EMAIL]'),
    (re.compile(r'\b(sk-|pk_|api[_-]?key)[a-zA-Z0-9]{20,}', re.I), '[API_KEY]'),
    (re.compile(r'\b\d{13,16}\b'), '[CARD]'),
]

def redact(value: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value[:500] + '...[TRUNCATED]' if len(value) > 500 else value

class SecureJsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'component': record.name,
            'message': redact(record.getMessage()),
        })

# Setup
handler = logging.StreamHandler()
handler.setFormatter(SecureJsonFormatter())
logger = logging.getLogger('app')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

---

## When to Apply These Patterns

### For 2-4 Hour Challenges

**Always use:**
- Repository pattern (clean data access)
- Dependency injection (testability)
- Consistent error responses
- Secure logging with PII redaction

**Use if needed:**
- Service layer (complex business logic)
- Caching (performance requirements)
- Pagination (list endpoints)

**Skip unless required:**
- Event sourcing
- Circuit breaker
- Outbox pattern

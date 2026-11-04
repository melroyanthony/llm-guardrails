---
name: {{domain}}-devops
description: |
  Deploys {{domain}} application with Docker and docker-compose.
  Use when containerizing, setting up local dev, or preparing for production.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {{Domain}} DevOps

## Extends

- `foundation/devops`

## Local Development

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: {{db_user}}
      POSTGRES_PASSWORD: {{db_password}}
      POSTGRES_DB: {{db_name}}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{db_user}} -d {{db_name}}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://{{db_user}}:{{db_password}}@db:5432/{{db_name}}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend/app:/app/app  # Hot reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next

volumes:
  postgres_data:
```

## Dockerfiles

### Backend (FastAPI)

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.13-slim-bookworm AS runner

WORKDIR /app
RUN adduser --system --uid 1001 appuser

# Copy full project including .venv; use .dockerignore to exclude __pycache__/, .git/, local .venv/
COPY --from=builder --chown=appuser:appuser /app/ /app/
ENV PATH="/app/.venv/bin:$PATH"

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Next.js)

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
```

## Makefile Commands

```makefile
.PHONY: dev build test clean

dev:
	docker-compose up --build

build:
	docker-compose build

test:
	docker-compose run --rm backend pytest
	docker-compose run --rm frontend npm test

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python -m app.scripts.seed

clean:
	docker-compose down -v
```

## Environment Variables

| Variable | Development | Production |
|----------|-------------|------------|
{{#env_vars}}
| `{{name}}` | `{{dev_value}}` | `{{prod_value}}` |
{{/env_vars}}

## Health Checks

### Backend

```python
# app/api/v1/health.py
@router.get("/health/live")
async def liveness():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(503, detail=str(e))
```

## Validation Criteria

{{#validation_criteria}}
- [ ] {{criterion}}
{{/validation_criteria}}

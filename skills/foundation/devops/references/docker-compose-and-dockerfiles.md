## docker-compose.yml (Cognita-inspired pattern)

```yaml
# docker-compose.yml
# Pattern: Service health dependencies, network isolation, volume persistence

services:
  db:
    image: postgres:17-alpine
    container_name: ${PROJECT_NAME:-app}-db
    environment:
      POSTGRES_USER: ${DB_USER:-app}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}  # Fails fast if unset
      POSTGRES_DB: ${DB_NAME:-app}
    ports:
      - "5432:5432"
    volumes:
      - ./volumes/pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-app} -d ${DB_NAME:-app}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development
    container_name: ${PROJECT_NAME:-app}-backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-app}:${DB_PASSWORD:?DB_PASSWORD is required}@db:5432/${DB_NAME:-app}
      DEBUG: ${DEBUG:-true}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./backend/app:/app/app  # Hot reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    container_name: ${PROJECT_NAME:-app}-frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

# Volumes stored in ./volumes/ for easy inspection
# Add to .gitignore: volumes/
```

## Backend Dockerfile (FastAPI + uv)

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim-bookworm AS base

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files (both needed for uv sync --locked)
COPY pyproject.toml uv.lock ./

# ──────────────────────────────────────────────────────────
# Development stage
FROM base AS development

# Install deps only (no project install — source not copied yet, for layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

COPY . .

# Now install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ──────────────────────────────────────────────────────────
# Production build stage
FROM base AS builder

# Install deps only first (layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY . .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ──────────────────────────────────────────────────────────
# Production runtime stage
FROM python:3.13-slim-bookworm AS production

WORKDIR /app

# Create non-root user
RUN adduser --system --uid 1001 appuser

# Copy full project including .venv from builder
# Use .dockerignore to exclude __pycache__/, .git/, and any local .venv/ from the build context
COPY --from=builder --chown=appuser:appuser /app/ /app/

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000

# Use exec form for proper signal handling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Node.js Stack (Express.js + SQLite)

### docker-compose.yml (Node.js variant)

```yaml
# docker-compose.yml for Node.js + SQLite
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development
    container_name: ${PROJECT_NAME:-app}-backend
    ports:
      - "3001:3001"
    environment:
      DATABASE_PATH: /app/data/database.sqlite
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      - ./backend/src:/app/src
      - ./backend/data:/app/data
    command: npx tsx watch src/index.ts
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    container_name: ${PROJECT_NAME:-app}-frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:3001
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### Backend Dockerfile (Express.js + TypeScript)

```dockerfile
# backend/Dockerfile
FROM node:22-alpine AS base
WORKDIR /app

# ─────────────────────────────────────────
# Dependencies stage
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# ─────────────────────────────────────────
# Development stage
FROM base AS development
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
EXPOSE 3001
CMD ["npx", "tsx", "watch", "src/index.ts"]

# ─────────────────────────────────────────
# Builder stage
FROM base AS builder
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# ─────────────────────────────────────────
# Production stage
FROM base AS production
ENV NODE_ENV=production

RUN adduser --system --uid 1001 appuser

COPY --from=deps --chown=appuser:appuser /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appuser /app/dist ./dist
COPY --from=builder --chown=appuser:appuser /app/package.json ./

# Create data directory for SQLite
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
EXPOSE 3001
CMD ["node", "dist/index.js"]
```

---

## Frontend Dockerfile (Next.js)

```dockerfile
# frontend/Dockerfile
FROM node:22-alpine AS base

WORKDIR /app

# ──────────────────────────────────────────────────────────
# Dependencies stage
FROM base AS deps

COPY package.json package-lock.json* ./
RUN npm ci

# ──────────────────────────────────────────────────────────
# Development stage
FROM base AS development

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NODE_ENV=development
EXPOSE 3000

CMD ["npm", "run", "dev"]

# ──────────────────────────────────────────────────────────
# Build stage
FROM base AS builder

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ──────────────────────────────────────────────────────────
# Production stage
FROM base AS production

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application (standalone output)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000
ENV PORT=3000

# Direct node execution for proper signal handling
CMD ["node", "server.js"]
```

## Frontend Dockerfile (React + Vite with Nginx)

```dockerfile
# frontend/Dockerfile (for React + Vite SPA)
FROM node:22-alpine AS base
WORKDIR /app

# ─────────────────────────────────────────
# Dependencies stage
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci

# ─────────────────────────────────────────
# Development stage
FROM base AS development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=development
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]

# ─────────────────────────────────────────
# Builder stage
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
RUN npm run build

# ─────────────────────────────────────────
# Production stage (Nginx)
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### nginx.conf (for React + Vite SPA)

```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy (if needed)
    location /api {
        proxy_pass http://backend:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## .dockerignore Files

### backend/.dockerignore

```
.git
.gitignore
.env
.env.*
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
.mypy_cache
.ruff_cache
*.egg-info
dist
build
.venv
venv
```

### frontend/.dockerignore

```
.git
.gitignore
.env
.env.*
node_modules
.next
.turbo
coverage
.nyc_output
*.log
```

## Makefile

```makefile
.PHONY: dev build test clean migrate seed logs

# Development
dev:
	docker compose up --build

dev-detach:
	docker compose up --build -d

logs:
	docker compose logs -f

stop:
	docker compose stop

# Database
migrate:
	docker compose exec backend uv run alembic upgrade head

seed:
	docker compose exec backend uv run python -m app.scripts.seed

reset-db:
	docker compose down -v
	docker compose up -d db
	sleep 3
	$(MAKE) migrate
	$(MAKE) seed

# Testing
test:
	docker compose exec backend uv run pytest -v

test-frontend:
	docker compose exec frontend npm test

# Production build
build:
	docker compose -f docker-compose.yml build

# Cleanup
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Utility
shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

shell-db:
	docker compose exec db psql -U app -d app
```

## Environment Variables

### .env.example

```bash
# Database
DB_USER=app
DB_PASSWORD=secret
DB_NAME=app

# Backend
DATABASE_URL=postgresql+asyncpg://app:secret@db:5432/app
SECRET_KEY=change-me-in-production

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Health Checks

### Backend Health Endpoints

Already included in backend-fastapi skill. Ensure `/health/live` and `/health/ready` exist.

### Docker Compose Health Check

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ready"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 30s
```


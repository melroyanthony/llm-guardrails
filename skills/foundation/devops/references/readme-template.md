## README Template (Cognita-inspired structure)

```markdown
# Project Name

> Brief one-line description of what this project does.

![Demo](docs/images/demo.gif) <!-- Optional: Add demo GIF/screenshot -->

## Why This Project?

[2-3 sentences explaining the problem and how this solution addresses it]

---

## Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Architecture](#-architecture)
- [Development](#-development)
- [What Was Built](#-what-was-built)
- [Key Decisions](#-key-decisions)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional, for convenience commands)

### Run with Docker (Recommended)

\`\`\`bash
# Clone and setup
git clone <repo>
cd <project>
cp .env.example .env

# Start all services
docker compose up --build

# In another terminal, run migrations
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m app.scripts.seed
\`\`\`

The app is now running:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Database | localhost:5432 |

---

## ✨ Features

- **Feature 1**: Description
- **Feature 2**: Description
- **Feature 3**: Description

---

## 🏗️ Architecture

\`\`\`
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Database   │
│  (Next.js)  │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
\`\`\`

See `docs/architecture/` for detailed diagrams.

---

## ⚒️ Development

\`\`\`bash
docker compose up --build        # Start all services with hot reload
docker compose logs -f           # View logs
docker compose stop              # Stop services
docker compose down -v           # Remove containers and volumes

# Run tests
docker compose exec backend uv run pytest -v
docker compose exec frontend npm test
\`\`\`

### Project Structure

\`\`\`
.
├── backend/           # FastAPI application
├── frontend/          # Next.js application
├── docs/              # Architecture, ADRs
│   ├── architecture/
│   └── decisions/
├── docker-compose.yml
└── Makefile
\`\`\`

---

## ✅ What Was Built

- [x] Feature 1 - Description
- [x] Feature 2 - Description
- [x] Feature 3 - Description

## 🚫 What Was Not Built (and Why)

| Feature | Reason | Future Approach |
|---------|--------|-----------------|
| Feature X | Time constraint | Would use approach Y |
| Feature Y | Out of MVP scope | Could add in v2 |

---

## 📋 Key Decisions

See `docs/decisions/` for Architecture Decision Records (ADRs).

| Decision | Rationale |
|----------|-----------|
| PostgreSQL over MongoDB | Relational data with complex joins |
| FastAPI over Django | Async-first, auto OpenAPI docs |

---

## 🤖 AI Tools Disclosure

This project was built with AI assistance. All code was reviewed and tested before submission.
\`\`\`


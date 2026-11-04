---
description: Generate README and CHANGELOG for the output directory
allowed-tools: Read, Glob, Grep, Write
---

# Documentation Generator

Generate comprehensive README.md and CHANGELOG.md for the `solution/` directory.

## What This Command Does

1. Scans the output directory to discover all generated files
2. Reads key artifacts to understand what was built
3. Generates `solution/README.md` with full documentation
4. Generates `solution/CHANGELOG.md` with version history and bug fixes

---

## Step 1: Gather Information

Use these tools to collect information:

```
1. Glob: Find all files in solution/
2. Read: solution/requirements/requirements.md (project description)
3. Read: solution/requirements/mvp-scope.md (features)
4. Read: solution/docs/architecture/openapi.yaml (API endpoints)
5. Read: solution/docs/architecture/database-schema.md (DB info)
6. Read: solution/docs/decisions/ADR-*.md (architecture decisions)
7. Read: solution/checkpoints/stage-4-bugs.md (bug fixes, if exists)
8. Read: solution/checkpoints/*.md (stage completion info)
```

---

## Step 2: Generate README.md

Create `solution/README.md` with this structure:

```markdown
# [Project Name]

> [One-line description from requirements]

## Quick Start

### Prerequisites
- Python 3.13+ with uv
- Node.js 22+ with npm
- Docker and Docker Compose

### Using Docker Compose (Recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Features

- [Feature 1 from MVP scope]
- [Feature 2 from MVP scope]
- [Feature 3 from MVP scope]

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/items | List all items |
| POST | /api/v1/items | Create item |
| ... | ... | ... |

## Project Structure

```
.
├── backend/           # FastAPI application
├── frontend/          # Next.js application
├── docs/              # Architecture documentation
├── docker-compose.yml
├── README.md
└── CHANGELOG.md
```

## Architecture

[Brief summary from ADRs]

See `docs/architecture/` for detailed diagrams.

## Testing

```bash
# Backend tests
cd backend && uv run pytest tests/ -v

# E2E validation
docker compose up -d
curl http://localhost:8000/health
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, Tailwind |
| Backend | FastAPI, SQLModel, PostgreSQL |
| Container | Docker Compose |

## License

[License info]
```

---

## Step 3: Generate CHANGELOG.md

Create `solution/CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project are documented here.

## [1.0.0] - YYYY-MM-DD

### Added
- Initial implementation of [project name]
- [Feature 1]: [brief description]
- [Feature 2]: [brief description]
- [Feature 3]: [brief description]
- API endpoints for [resource] CRUD operations
- Docker Compose configuration
- Comprehensive test suite

### Fixed
[Read from solution/checkpoints/stage-4-bugs.md if it exists]
- [Bug 1]: [description of fix]
- [Bug 2]: [description of fix]

### Technical Details
- Backend: FastAPI with SQLModel ORM
- Frontend: Next.js 15 with App Router
- Database: PostgreSQL
- Testing: pytest-asyncio with [N] tests passing
```

---

## Step 4: Check for Bug Fixes

**Important**: Read `solution/checkpoints/stage-4-bugs.md` if it exists.

If bugs were fixed during Stage 4:
- Add them to the "Fixed" section in CHANGELOG.md
- Optionally mention significant fixes in README.md

---

## Output

Write files:
- `solution/README.md`
- `solution/CHANGELOG.md`

Display summary:
```
Documentation Generated

Files created:
- solution/README.md
- solution/CHANGELOG.md

README sections:
- Quick Start
- Features
- API Endpoints
- Project Structure
- Testing

CHANGELOG includes:
- Features added: [N]
- Bug fixes: [M]

Ready for deployment
```

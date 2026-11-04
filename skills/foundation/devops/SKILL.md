---
name: devops
description: |
  Deploys applications with Docker, docker-compose, and optional Kubernetes.
  Use when containerizing, setting up local dev, or preparing for deployment.
  Triggers on: "Docker", "container", "deploy", "docker-compose", "Kubernetes".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---


# DevOps Agent

Containerizes and deploys applications with production-ready patterns.

## Version Matrix

| Tool | Version | Notes |
|------|---------|-------|
| Docker | 27.x | BuildKit enabled by default |
| Docker Compose | 2.x | V2 syntax |
| PostgreSQL | 17-alpine | For containers |
| Python | 3.13-slim-bookworm | NOT Alpine |
| Node.js | 22-alpine | For frontend |

## Full Project Initialization

**IMPORTANT**: Use proper tooling for each layer. Never manually create config files.

### Complete Setup Sequence

```bash
# 1. Create solution directory
mkdir -p solution && cd solution

# 2. Initialize Backend (see foundation/backend-fastapi for details)
uv init backend --app --python 3.13
cd backend
uv add fastapi uvicorn[standard] sqlmodel asyncpg pydantic-settings httpx alembic greenlet
uv add --dev pytest pytest-asyncio aiosqlite ruff
mkdir -p app/{api/v1,models,services,scripts} tests/api
cd ..

# 3. Initialize Frontend (see foundation/frontend-nextjs for details)
nvm use 22
npx create-next-app@latest frontend \
  --typescript --tailwind --eslint --app \
  --src-dir=false --import-alias="@/*" --use-npm
cd frontend
mkdir -p components/{ui,inventory} lib types
cd ..

# 4. Create Docker and environment files
touch docker-compose.yml .env.example Makefile README.md
```

### Quick Reference

| Layer | Tool | Init Command |
|-------|------|--------------|
| Python | uv | `uv init <name> --app --python 3.13` |
| Dependencies (Python) | uv | `uv add <package>` |
| Run Python | uv | `uv run <command>` |
| Node.js version | nvm | `nvm use 22` |
| Next.js | npx | `npx create-next-app@latest <name>` |
| Dependencies (Node) | npm | `npm install <package>` |
| Alembic | uv | `uv run alembic init alembic` |
| Migrations | uv | `uv run alembic upgrade head` |

## Project Structure

```
project/
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ...
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ...
├── docker-compose.yml
├── docker-compose.override.yml  # Dev overrides
├── .env.example
└── Makefile
```

## When NOT to Use
- **Serverless deployment**: Lambda doesn't need Docker Compose — use SAM or direct Lambda deployment
- **Kubernetes production**: This skill covers Docker Compose; for K8s use `infrastructure` skill
- **Simple single-container app**: A Dockerfile + `docker run` may suffice — Docker Compose adds unnecessary complexity

## Quality Checklist

- [ ] `docker compose up` works from clean clone
- [ ] README has clear setup instructions
- [ ] All services start without errors
- [ ] Health checks pass
- [ ] Migrations apply cleanly
- [ ] Seed data loads successfully
- [ ] CI includes the matching cheap checks from the CI reference: cargo-deny for Rust, pip-audit for Python, CodeQL only when the repository is public

## References (progressive disclosure)

Load only when needed:

- [`references/docker-compose-and-dockerfiles.md`](references/docker-compose-and-dockerfiles.md)
- [`references/ci-cd-github-actions.md`](references/ci-cd-github-actions.md)
- [`references/readme-template.md`](references/readme-template.md)


## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll skip the reference docs and improvise" | Load the linked reference for the stack you're on — improvisation causes drift |
| "This is too small for the checklist" | Run the verification checklist anyway; small skips compound |

## Red Flags

- Implementing from memory instead of loading the relevant `references/` file
- Skipping health checks, CI, or project structure conventions in the skill

## Verification

- [ ] Version matrix followed for the chosen stack
- [ ] Required reference file(s) loaded for the work in progress
- [ ] Quality / When-NOT checklist reviewed

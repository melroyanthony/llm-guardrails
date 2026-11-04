## CI/CD with GitHub Actions

### Directory Structure
```
solution/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Continuous Integration
│       ├── deploy.yml       # Deployment (optional)
│       └── release.yml      # Release automation (optional)
```

### CI Workflow (ci.yml)

The workflow below is the build and test gate. Add the cheap checks from the next section when the stack matches: cargo-deny for Rust, pip-audit for Python, and CodeQL only when the repository is public.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─────────────────────────────────────────
  # Backend Tests
  # ─────────────────────────────────────────
  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.13

      - name: Install dependencies
        run: uv sync

      - name: Run linting
        run: uv run ruff check .

      - name: Run type checking
        run: uv run mypy app --ignore-missing-imports

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
        run: uv run pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
          fail_ci_if_error: false

  # ─────────────────────────────────────────
  # Frontend Tests
  # ─────────────────────────────────────────
  frontend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run linting
        run: npm run lint

      - name: Run type checking
        run: npm run type-check || true

      - name: Run tests
        run: npm test -- --run

      - name: Build
        run: npm run build

  # ─────────────────────────────────────────
  # Docker Build
  # ─────────────────────────────────────────
  docker-build:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          target: production
          push: false
          tags: backend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          target: production
          push: false
          tags: frontend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─────────────────────────────────────────
  # Integration Tests
  # ─────────────────────────────────────────
  integration-test:
    runs-on: ubuntu-latest
    needs: [docker-build]

    steps:
      - uses: actions/checkout@v4

      - name: Start services
        run: docker compose up -d --build

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8000/health; do sleep 2; done'

      - name: Run E2E tests
        run: |
          # Health check
          curl -f http://localhost:8000/health

          # Create item
          curl -f -X POST http://localhost:8000/api/v1/items \
            -H "Content-Type: application/json" \
            -d '{"name": "CI Test", "quantity": 1}'

          # List items
          curl -f http://localhost:8000/api/v1/items

      - name: Show logs on failure
        if: failure()
        run: docker compose logs

      - name: Cleanup
        if: always()
        run: docker compose down -v
```

### Deploy Workflow (Optional)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          target: production
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          target: production
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Cheap checks

Add the jobs that match the stack. They are required checks. The blocks below are `jobs:` entries. Pin `actions/checkout`, `astral-sh/setup-uv`, `EmbarkStudios/cargo-deny-action`, and `github/codeql-action` by full commit SHA with a version comment, the same way `.github/workflows/ci.yml` pins checkout. Point `working-directory` at the Python project. The sample layout uses `backend`. Keep a CodeQL language only when the repository contains it.

#### cargo-deny (Rust)

Include this when the repository has a `Cargo.toml`. Commit a `deny.toml` at the repository root (`cargo deny init` writes a starting file). The action runs `cargo deny check` and defaults `--all-features`. Set `manifest-path` when the manifest is not `./Cargo.toml`. Source: [EmbarkStudios/cargo-deny-action](https://github.com/embarkstudios/cargo-deny-action) `v2.1.1`.

```yaml
  cargo-deny:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: EmbarkStudios/cargo-deny-action@3c6349835b2b7b196a839186cb8b78e02f7b5f25 # v2.1.1
```

#### pip-audit (Python)

Include this when the repository has a Python project. Export the lockfile with uv, then audit that file. `--frozen` refuses to update `uv.lock`. `--no-emit-project` leaves the local project out of the audit. `--no-hashes` keeps hash lines out of the file pip-audit reads. `--no-deps` audits the exported closure without resolving again. A project that only has `requirements.txt`, or that uses Poetry or pip-tools, exports a requirements file and runs `uvx pip-audit --requirement <file> --no-deps`. Use the project's pinned Python. This catalog stays on 3.14 until the revisit recorded in `AGENTS.md`. `version` is the current stable uv release, `0.13.7`.

```yaml
  pip-audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          version: "0.13.7"
      - name: Export locked requirements
        working-directory: backend
        run: uv export --frozen --no-emit-project --no-hashes --format requirements.txt -o "$RUNNER_TEMP/requirements-audit.txt"
      - name: Audit Python dependencies
        run: uvx pip-audit --requirement "$RUNNER_TEMP/requirements-audit.txt" --no-deps
```

#### CodeQL (public repositories)

Include this only when the repository is public. CodeQL upload on a private repository needs GitHub Code Security. The job runs when `github.event.repository.visibility` is `public` and skips otherwise, including when that field is absent. Keep `python`. Add `rust` with `build-mode: none` when the repository is Rust. Drop a language the repository does not contain. Source: [github/codeql-action](https://github.com/github/codeql-action) `v4.39.2`.

The job id is `codeql`. While the matrix runs, the checks are `codeql (<language>)`. When the job is skipped it is not reported as `codeql (python)` or `codeql (<language>)`, so a private repository does not require those names.

```yaml
  codeql:
    name: codeql (${{ matrix.language }})
    if: github.event.repository.visibility == 'public'
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        include:
          # Keep python. Add the rust row when the repository is Rust.
          # Drop a row the repository does not contain.
          - language: python
            build-mode: none
          - language: rust
            build-mode: none
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: github/codeql-action/init@1fc58d04a4d4374f921bdac573c3811c240f9c26 # v4.39.2
        with:
          languages: ${{ matrix.language }}
          build-mode: ${{ matrix.build-mode }}
      - uses: github/codeql-action/analyze@1fc58d04a4d4374f921bdac573c3811c240f9c26 # v4.39.2
        with:
          category: "/language:${{ matrix.language }}"
```

### CI/CD Checklist

- [ ] `.github/workflows/ci.yml` created
- [ ] Backend tests run in CI
- [ ] Frontend tests run in CI
- [ ] Docker images build successfully
- [ ] Integration tests pass
- [ ] Rust repositories run cargo-deny
- [ ] Python repositories run pip-audit
- [ ] Public repositories run CodeQL for `python`, and for `rust` with `build-mode: none` when the repository is Rust
- [ ] Private and internal repositories skip CodeQL. A skipped job is not reported as `codeql (python)` or `codeql (<language>)`, so those names are not required checks
- [ ] `actions/checkout`, `astral-sh/setup-uv`, `EmbarkStudios/cargo-deny-action`, and `github/codeql-action` are pinned by full commit SHA
- [ ] (Optional) Deploy workflow configured

---


---
description: Start or resume the SDLC multi-agent pipeline for coding challenges
allowed-tools: Read, Glob, Grep, Write, Edit, Bash, Task, AskUserQuestion
argument-hint: [stage-number]
---

# SDLC Orchestrator

Coordinate the multi-stage coding challenge pipeline.

## Usage

- `/orchestrate` - Start from Stage 0
- `/orchestrate 3` - Resume from Stage 3

---

## Pipeline Stages

| Stage | Agent | Output |
|-------|-------|--------|
| 0 | Setup + Git Init | Git at root, solution/ structure created |
| 1 | product-manager | Requirements, RICE, MoSCoW, MVP scope |
| 2 | architect | C4 diagrams, OpenAPI, database schema, ADRs |
| 2.5 | Issue Creation + Branch | GitHub issues from MVP, feature branch created |
| 3 | backend-dev + frontend-dev | Implementation on feature branch |
| 4 | tester | Unit tests + E2E validation |
| 5 | Finalization + PR | README, CHANGELOG, push, create PR |

---

## Project Structure (CRITICAL)

**Git is initialized at PROJECT ROOT, solution/ contains all generated artifacts:**
```
project-root/              # Git repository root
├── .git/                  # Git initialized here
├── .gitignore             # Project-wide ignores
├── problem/               # Problem statement & supporting files
│   ├── PROBLEM.md         # Main problem statement (required)
│   ├── *.pdf              # Supplementary PDFs
│   ├── *.png, *.jpg       # Diagrams, screenshots
│   └── data/              # Example data files (optional)
├── solution/              # All generated artifacts
│   ├── requirements/      # Stage 1
│   ├── docs/
│   │   ├── architecture/  # Stage 2
│   │   └── decisions/     # ADRs
│   ├── backend/           # Stage 3
│   ├── frontend/          # Stage 3
│   ├── scripts/           # Utility scripts
│   ├── checkpoints/       # Stage validations
│   ├── .github/workflows/ # CI/CD
│   ├── docker-compose.yml # Root file OK
│   ├── README.md          # Root file OK
│   └── CHANGELOG.md       # Root file OK
└── .claude/               # Claude Code config (if copied)
```

**Working Directory:** Stay at PROJECT ROOT throughout. Reference `solution/` for output paths. Problem files are in `problem/` folder.

---

## Stage 0: Project Setup & Git Initialization

### Step 1: Initialize Git at Project Root
```bash
# Initialize git in current directory (project root)
git init
```

### Step 2: Create .gitignore at Project Root
```bash
# Create comprehensive .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.env
.env.*
!.env.example
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyo
*.pyd
.Python
pip-log.txt

# Node
node_modules/
.next/
out/
dist/
build/
.npm/
.npmrc
*.tsbuildinfo
.turbo/
.vercel/
.cache/

# Package managers
package-lock.json
yarn.lock
pnpm-lock.yaml
uv.lock

# IDE
.idea/
.vscode/
*.swp
*.swo
*.sublime-*
.project
.settings/

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
ehthumbs.db

# Docker
*.log
docker-compose.override.yml

# Coverage
htmlcov/
.coverage
.coverage.*
coverage/
*.cover
*.lcov

# Testing
.tox/
.nox/
.hypothesis/

# Secrets (never commit)
*.pem
*.key
secrets/
credentials.json

# Claude Code config (copy separately)
.claude/
EOF
```

### Step 3: Create Solution Directory Structure
```bash
mkdir -p solution/{requirements,checkpoints,scripts,docs/{architecture,decisions}}
```

**IMPORTANT**: Stay at project root - do NOT cd into solution/. Problem files in `problem/` must remain accessible.

### Step 4: Ask User for GitHub URL
Use **AskUserQuestion** tool:
- Question: "What is your GitHub repository URL? (Leave blank to skip remote setup)"
- If provided: `git remote add origin <URL>`

### Step 5: Initial Commit
```bash
git add .
git commit -m "feat(stage-0): initialize project structure

- Git repository initialized at project root
- Created solution/ directory structure
- Added comprehensive .gitignore

Stage: 0/5"
```

### Stage 0 Checkpoint (from project root)
Create `solution/checkpoints/stage-0-validation.md` (use full path from project root):
```markdown
# Stage 0: Project Setup

## Summary
- **Status**: COMPLETE
- **Git**: Initialized at project root
- **Remote**: [URL or "Not configured"]
- **Structure**: solution/ directories created

## Ready for Stage 1: Yes
```

---

## Stage 1: Requirements Analysis

Delegate to **product-manager** agent:
- **Discover problem statement** (checks for `problem/PROBLEM.md` and supporting files)
- Parse problem statement
- RICE scoring and MoSCoW prioritization
- Define MVP scope

Output: `solution/requirements/`

**Git commit after Stage 1:**
```bash
git add .
git commit -m "feat(stage-1): analyze requirements with RICE/MoSCoW

- Created requirements.md with functional requirements
- RICE scores for feature prioritization
- MoSCoW categorization
- MVP scope defined with acceptance criteria

Stage: 1/5"
```

---

## Stage 2: Architecture & System Design (CRITICAL)

**Before designing, read the knowledge base (in order):**
```
skills/foundation/system-design/APPROACH.md   # Design methodology
skills/foundation/system-design/SKILL.md      # Core concepts
skills/foundation/system-design/PATTERNS.md   # Implementation patterns
skills/foundation/language-selection/SKILL.md  # Language decision framework
```

**For specialized project types, also read:**
- Algorithm/optimization: `skills/foundation/numerical-computing/SKILL.md`, `skills/foundation/optimization-algorithms/SKILL.md`
- Multi-language: `skills/foundation/polyglot-coordination/SKILL.md`

Delegate to **architect** agent with these steps:

### 2.1: Scale Analysis
- Estimate users, RPS, data volume
- Determine if single server sufficient

### 2.2: Trade-off Decisions
- Consistency vs Availability (default: CP)
- Latency vs Throughput (default: low latency)
- Complexity vs Speed (default: simplicity)

### 2.3: Technology Stack Selection
Select based on project requirements:
- **Backend**: FastAPI (Python) or Express.js (Node.js)
- **Frontend**: Next.js (SSR) or React+Vite (SPA)
- **Database**: PostgreSQL or SQLite

### 2.4: Pattern Selection
- Repository pattern (always)
- Caching strategy (if read-heavy)
- Pagination (for list endpoints)
- Health checks (always)

### 2.5: Output Artifacts
- `docs/architecture/system-design.md` - Scale estimates & patterns
- `docs/architecture/workspace.dsl` - C4 diagrams
- `docs/architecture/openapi.yaml` - API specification
- `docs/architecture/database-schema.md` - Tables & indexes
- `docs/decisions/ADR-*.md` - Key decisions (2-3 required)

**Git commit after Stage 2:**
```bash
git add .
git commit -m "feat(stage-2): define architecture and API contracts

- C4 workspace with context and container views
- OpenAPI spec with API endpoints
- Database schema with tables and indexes
- System design overview with scale estimates
- ADRs documenting key decisions

Stage: 2/5"
```

---

## Stage 2.5: Issue Creation & Branch Setup

**This stage bridges planning (on main) and implementation (on feature branch).**

After Stage 2 is committed to main and judge-validated:

### Step 1: Ensure Labels Exist
```bash
gh label create "feature" --color "0075ca" --description "New feature" 2>/dev/null || true
gh label create "bug" --color "d73a4a" --description "Bug fix" 2>/dev/null || true
```

### Step 2: Break Architecture into Vertical Slices

- Read `solution/docs/architecture/system-design.md` and `solution/docs/decisions/ADR-*.md`
- Read `solution/requirements/mvp-scope.md`
- **Vertical slices, not horizontal layers**: Each issue cuts through ALL integration layers end-to-end (API + DB + UI + tests). Do NOT create separate "backend models", "API routes", "frontend pages" issues.
- Create a work breakdown:
  - **From MVP scope**: Each Must-Have feature becomes a vertical slice issue
  - **From architecture**: First slice is a thin end-to-end tracer bullet (e.g., health-check). Foundational setup (scaffolding, DB migration, auth) may be captured as its own issue when it can't meaningfully span all layers.
  - **From ADRs**: Each decision that requires implementation becomes an issue
- **Classify each issue** as AFK (agent-implementable) or HITL (needs human judgment)
- Order by dependency (foundational slices first, AFK before HITL)
- Target 5-10 issues for MVP. Each should represent 1-4 hours and be independently testable.

### Step 2.5: Create Labels for Classification
```bash
gh label create "AFK" --color "0e8a16" --description "Agent can implement without human interaction" 2>/dev/null || true
gh label create "HITL" --color "fbca04" --description "Requires human judgment or review" 2>/dev/null || true
```

### Step 3: Create GitHub Issues as Vertical Slices

```bash
gh issue create --title "feat: <vertical slice description>" --label "feature,AFK" --body "## Vertical Slice
<What this slice delivers end-to-end>

## Layers
- [ ] Database: <model/migration>
- [ ] API: <endpoint(s)>
- [ ] Frontend: <page/component>
- [ ] Tests: <unit + integration for this slice>

## Acceptance Criteria
- [ ] <criterion from mvp-scope.md>

## Classification: AFK
Agent can implement this slice without human interaction.

## Source
Requirements: solution/requirements/mvp-scope.md
ADR: <linked ADR if applicable>"
```

For HITL issues (requires human judgment, design review, external access):
```bash
gh issue create --title "feat: <slice requiring human input>" --label "feature,HITL" --body "## Vertical Slice
<What this slice delivers>

## Why HITL
<What requires human judgment>

## Layers
- [ ] <affected layers>

## Acceptance Criteria
- [ ] <criteria>

## Classification: HITL
Requires human judgment or review before implementation."
```

Collect all issue numbers. Group: AFK issues first (can be parallelized), then HITL issues.

### Step 4: Ask User to Confirm

Use **AskUserQuestion** tool:
- Show created issues list with AFK/HITL classification
- Propose branch name: `feat/issue-<first-issue>-<project-slug>`
- Question: "Issues created (N AFK, M HITL). Ready to create feature branch and start implementation? (Confirm branch name or suggest alternative)"

### Step 5: Checkout Main and Pull Latest
```bash
git checkout main
# Pull latest — abort if pull fails
if git remote get-url origin &>/dev/null; then
  git pull origin main || { echo "ERROR: pull failed — resolve before continuing"; exit 1; }
fi
```

### Step 6: Create Feature Branch
```bash
git checkout -b <branch-name>
```

### Step 7: Create Stage 2.5 Checkpoint and Commit

Create `solution/checkpoints/stage-2.5-validation.md`:
```markdown
# Stage 2.5: Issue Creation & Branch Setup

## Summary
- **Status**: COMPLETE
- **Issues Created**: #N, #M, ...
- **Branch**: <branch-name>
- **Base**: main (at commit <sha>)

## Issues
| # | Title | Classification | Labels |
|---|-------|---------------|--------|
| N | feat: ... | AFK | feature, AFK |
| M | feat: ... | HITL | feature, HITL |

## Slice Strategy: Vertical (end-to-end per feature)
## Ready for Stage 3: Yes
```

Commit the checkpoint on the feature branch:
```bash
git add solution/checkpoints/stage-2.5-validation.md
git commit -m "chore(stage-2.5): create issues and feature branch

- Created GitHub issues: #N, #M, ...
- Feature branch: <branch-name>

Stage: 2.5/5"
```

---

## Stage 3: Implementation

> **Tip:** For faster execution, use `/parallel-stage3` to run backend and
> frontend concurrently in isolated worktrees.
>
> **Long session?** Run `/context-budget` to check remaining capacity and
> get save/resume recommendations before starting implementation.

**Stack Detection**: Check `solution/docs/architecture/system-design.md` for selected stack.

Delegate to **backend-dev** and **frontend-dev** agents:
- Implement based on OpenAPI spec + selected stack
- Follow patterns from system design
- Create Docker Compose configuration in `solution/`

**Git commit after Stage 3:**
```bash
git add .
git commit -m "feat(stage-3): implement backend and frontend

- Backend (FastAPI/Express.js) with database models
- Frontend (Next.js/React+Vite) with TypeScript
- Docker Compose configuration
- Multi-stage Dockerfiles

Stage: 3/5"
```

---

## Stage 4: Testing & Validation (CRITICAL)

This stage has multiple sub-phases.

**Stack Detection**: Detect backend stack before running tests:
```bash
# Python backend
ls solution/backend/pyproject.toml 2>/dev/null && echo "PYTHON"

# Node.js backend
ls solution/backend/package.json 2>/dev/null && echo "NODEJS"
```

### 4.1: Unit Tests
```bash
# Python backend
cd solution/backend && uv run pytest tests/ -v

# Node.js backend
cd solution/backend && npm test
```

### 4.2: Docker Compose Validation

**Start all services:**
```bash
cd solution && docker compose up --build -d
```

**Wait for services to be healthy:**
```bash
docker compose ps
# Verify all services are "Up" and healthy
```

**Check logs for errors:**
```bash
docker compose logs --tail=50
```

### 4.3: Happy Path E2E Test

Run ONE complete user flow to verify the system works end-to-end:

1. **Health check**: `curl http://localhost:8000/health`
2. **Create resource**: POST to main endpoint
3. **List resources**: GET to verify creation
4. **Update resource**: PUT/PATCH
5. **Delete resource**: DELETE
6. **Verify deletion**: GET returns 404 or empty

Example:
```bash
# Health check
curl -s http://localhost:8000/health

# Create
curl -s -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Item", "quantity": 10}'

# List
curl -s http://localhost:8000/api/v1/items

# Cleanup
cd solution && docker compose down
```

### 4.4: Bug Fix Loop

**If any issues found:**

1. **Document the bug** in `solution/checkpoints/stage-4-bugs.md`
2. **Fix the issue** in backend or frontend code
3. **Re-run tests** to verify fix
4. **Commit the fix**:
```bash
git add . && git commit -m "fix: [description of bug fix]"
```
5. **Repeat** until all tests pass and happy path works

### 4.5: Final Test Run

After all fixes:
```bash
# Python backend
cd solution/backend && uv run pytest tests/ -v

# Node.js backend
cd solution/backend && npm test

# All tests must pass before proceeding
```

**Commit Stage 4:**
```bash
git add . && git commit -m "feat(stage-4): add tests and validate E2E flow

- Unit tests: N passing
- Docker Compose validated
- Happy path E2E tested
- Bug fixes applied (if any)

Stage: 4/5"
```

---

## Stage 5: Review, Finalization & PR

### 5.1: Code Review + Security Review (Pre-PR Gate)

**Run staff-level review BEFORE creating the PR to ensure it arrives clean.**

1. **Spawn code-reviewer agent** on `solution/backend/` and `solution/frontend/`:
   - Focus: correctness, maintainability, performance, error handling

2. **Spawn security-reviewer agent** on the same directories:
   - Focus: OWASP Top 10, injection, auth flaws, secrets, input validation

3. **Apply fixes** for actionable findings (max **2 review→fix cycles**)

4. **Re-verify** with `/verify` after fixes (Build → Type → Lint → Test → Security → Diff)

5. **Commit fixes** (if any):
   ```bash
   git add . && git commit -m "refactor: apply code review and security review fixes"
   ```

6. **Document remaining findings** (if any) for inclusion in PR description.

### 5.2: Generate/Update Documentation

1. **Create README.md** in `solution/` - Comprehensive project documentation

2. **Create CHANGELOG.md** in `solution/`:
```markdown
# Changelog

## [1.0.0] - YYYY-MM-DD

### Added
- Initial implementation
- [List of features]

### Fixed
- [List of bug fixes from Stage 4, if any]
```

### 5.3: CI/CD Pipeline

**Create GitHub Actions at `solution/.github/workflows/ci.yml`:**

```bash
mkdir -p solution/.github/workflows
```

Reference: `skills/foundation/devops/SKILL.md` and `skills/foundation/devops/references/ci-cd-github-actions.md`.

Workflow includes:
- Backend tests (pytest + PostgreSQL)
- Frontend tests (vitest)
- Docker build verification
- Integration tests
- pip-audit when the project is Python
- cargo-deny when the project is Rust
- CodeQL only when the repository is public (`python`, and `rust` with `build-mode: none` on a Rust repository). A skipped job is not reported as `codeql (python)` or `codeql (<language>)`, so a private repository does not require those check names.

Copy the cheap-check jobs that match the stack from the CI reference. Those jobs pin `actions/checkout`, `astral-sh/setup-uv`, `EmbarkStudios/cargo-deny-action`, and `github/codeql-action` by full commit SHA.

### 5.4: Final Docker Validation

Quick sanity check:
```bash
cd solution && docker compose up --build -d
curl -s http://localhost:8000/health
docker compose down
```

### 5.5: Final Commit

```bash
git add . && git commit -m "feat(stage-5): finalize with docs, CI/CD, and changelog

- Pre-PR code review and security review applied
- README.md generated
- CHANGELOG.md created
- CI/CD workflow added
- Final validation passed

Stage: 5/5 - Complete"
```

### 5.6: Push & Create Pull Request

1. **Push feature branch:**
```bash
git push -u origin <branch-name>
```

2. **Create Pull Request** with Mermaid diagrams:
   - Title: `✨ feat(stage-5): ship the mvp` (hybrid subject, under 72 characters)
   - Body includes:
     - Summary of what was built
     - `Closes #N, Closes #M, ...` for all issues from Stage 2.5
     - Architecture diagram (Mermaid)
     - API endpoints summary
     - Test results summary
   - Use `gh pr create` with heredoc body

3. **Self-review, then the independent reviewer.** Follow `skills/foundation/review-loop-to-squash-merge/SKILL.md`. Review the diff for correctness, edge cases, tests, security, and docs. Fold those fixes into one push. Mention the independent reviewer in the `Channel` from `## Review` with the pull request link and the full head SHA. That request is not confirmation. Confirmation is a later message from that reviewer, in the channel, that quotes the full head SHA and explicitly confirms it. A hold or a request-changes message does not confirm. A blank GitHub login is fine when the channel is set. Full review when the diff touches auth or secrets, a file format, a wire contract, a migration, a release workflow or script, or a major dependency bump. A lighter pass otherwise. Lockfile-only bumps and docs get a quick pass.

4. **Merge gate.** Required CI is green and the named independent reviewer has explicitly confirmed the current full head SHA in the review channel. A new push needs a new confirmation. A hold blocks the merge until it is fixed or the lead waives that SHA. Round 3 without confirmation, or any disagreement, escalates to the lead. Ask only when the gate is clear: "Ready to merge: <url>, CI green, reviewer confirmed <sha>. Squash-merge and delete the branch?" When they say yes, append `Reviewed by <reviewer> at \`<sha>\`` and the findings. `<reviewer>` is the Independent reviewer named under `## Review`. A waiver appends `Lead waived the hold at \`<sha>\`` instead. Then `gh pr merge <number> --squash --delete-branch`.

5. **Review comments.** `/resolve-review` fixes one round: fetch comments, categorize each as fix / acknowledge / dismiss, reply inline with `in_reply_to`, and push once. A new push needs a new review of that head. Stop at round 3, and stop on a disagreement.

---

## Git Commit Messages

| Stage | Commit Message |
|-------|----------------|
| 0 | `feat(stage-0): initialize project structure` |
| 1 | `feat(stage-1): analyze requirements with RICE/MoSCoW` |
| 2 | `feat(stage-2): define architecture and API contracts` |
| 2.5 | (no commit — branch creation is the artifact) |
| 3 | `feat(stage-3): implement backend and frontend` |
| 4 | `feat(stage-4): add tests and validate E2E flow` |
| - | `fix: [bug description]` (as needed) |
| 5 | `feat(stage-5): finalize with docs, CI/CD, and changelog` |

---

## Time Management

Display at checkpoints:
```
⏱️ Time: [elapsed] / [budget]
📍 Stage: [N] of 5
✅ Completed: [list]
⏳ Remaining: [list]
```

---

## Resume from Stage N

When resuming (`/orchestrate N`):
1. Verify git is initialized at project root
2. Verify `solution/` exists
3. Check existing checkpoints in `solution/checkpoints/`
4. If resuming from 3+, verify on a feature branch (not main)
5. Continue from stage N

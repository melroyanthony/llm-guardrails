# Handoff Protocol

Defines artifacts and validation criteria for stage transitions.

**IMPORTANT**: All artifacts go inside `solution/` directory.

## Stage 0 → Stage 1

**From:** Orchestrator (Setup)
**To:** Product Manager

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| Project structure | `solution/` | Directories created |
| Git initialized | `.git/` at the project root | Git repo initialized |

### Handoff Checklist

- [ ] `solution/` directory created with subdirs
- [ ] Git initialized at the project root
- [ ] `.gitignore` created
- [ ] Initial commit made

---

## Stage 1 → Stage 2

**From:** Product Manager
**To:** Architect

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| Requirements | `solution/requirements/requirements.md` | All FRs extracted |
| RICE scores | `solution/requirements/rice-scores.md` | All features scored |
| MoSCoW | `solution/requirements/moscow.md` | Categories assigned |
| MVP scope | `solution/requirements/mvp-scope.md` | Must-haves defined |

### Handoff Checklist

- [ ] All features prioritized with RICE
- [ ] MoSCoW categories assigned
- [ ] MVP scope clearly defined
- [ ] Out-of-scope items documented with rationale
- [ ] Time budget allocated per feature

---

## Stage 2 → Stage 2.5

**From:** Architect
**To:** Orchestrator (Issue + Branch Setup)

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| System design | `solution/docs/architecture/system-design.md` | Scale estimates documented |
| OpenAPI spec | `solution/docs/architecture/openapi.yaml` | Valid OpenAPI 3.1 |
| DB schema | `solution/docs/architecture/database-schema.md` | All entities mapped |
| MVP scope | `solution/requirements/mvp-scope.md` | Features with acceptance criteria |

### Handoff Checklist

- [ ] Architecture committed to main
- [ ] Judge validation passed (≥70%)
- [ ] MVP scope has clear feature list with acceptance criteria

---

## Stage 2.5 → Stage 3

**From:** Orchestrator (Issue + Branch Setup)
**To:** Backend + Frontend

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| GitHub labels | GitHub | `feature` and `bug` labels exist (created if missing) |
| GitHub issues | GitHub | Issues created with `feature` label |
| Feature branch | git | Branch exists, based on latest main |
| Stage 2.5 checkpoint | `solution/checkpoints/stage-2.5-validation.md` | Committed on feature branch |
| All Stage 2 artifacts | `solution/docs/` | Available on feature branch |

### Handoff Checklist

- [ ] GitHub issues created for all Must-Have features
- [ ] Feature branch created from latest main
- [ ] Currently on feature branch (not main)
- [ ] All architecture artifacts available on branch
- [ ] User confirmed branch name and issue list

---

## Stage 3 → Stage 4

**From:** Backend + Frontend
**To:** Testing

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| Backend code | `solution/backend/` | App starts, endpoints respond |
| Frontend code | `solution/frontend/` | App builds, pages render |
| Docker Compose | `solution/docker-compose.yml` | Services start |

### Handoff Checklist

- [ ] `docker compose up` starts all services
- [ ] Database migrations apply without error
- [ ] All MVP endpoints return expected responses
- [ ] Frontend pages render without errors
- [ ] No TypeScript/Python type errors

---

## Stage 4 → Stage 5

**From:** Testing
**To:** Finalization

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| Backend tests | `solution/backend/tests/` | Critical paths covered |
| Test checkpoint | `solution/checkpoints/stage-4-validation.md` | Pass rate documented |
| Bug fixes (if any) | `solution/checkpoints/stage-4-bugs.md` | Issues documented |

### Handoff Checklist

- [ ] Unit tests pass
- [ ] Docker Compose validated
- [ ] Happy path E2E tested
- [ ] Bug fixes committed (if any)

---

## Stage 5 → Final

**From:** Finalization
**To:** Deployment

### Artifacts Required

| Artifact | Path | Validation |
|----------|------|------------|
| README | `solution/README.md` | Setup instructions |
| CHANGELOG | `solution/CHANGELOG.md` | Features and fixes |
| Docker Compose | `solution/docker-compose.yml` | Services start |

### Handoff Checklist

- [ ] `docker compose up` works from clean state
- [ ] README has clear setup instructions
- [ ] README documents what was built
- [ ] CHANGELOG lists features and bug fixes
- [ ] All commits follow conventional format
- [ ] Git history tells coherent story
- [ ] Pushed to GitHub (if configured)

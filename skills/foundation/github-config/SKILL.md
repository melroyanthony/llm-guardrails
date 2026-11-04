---
name: github-config
description: |
  Generate comprehensive .github/ configuration for a project: PR template,
  issue templates, release-please semantic versioning, and path-based auto-labeler.
  Use when setting up GitHub repository configuration for a new or existing project.
  Triggers on: "github config", "set up github", "PR template", "issue templates", "release automation".
allowed-tools: Read, Grep, Glob, Write, Bash
---

# GitHub Configuration Generator

Generate a complete `.github/` suite for a project: PR template, YAML issue templates, release-please semantic versioning, and path-based auto-labeling.

## When to Use

- Stage 5 of the SDLC pipeline (alongside CI/CD)
- Setting up a new repository
- Adding release automation to an existing project

## Files to Generate

### 1. PR Template

**File**: `solution/.github/PULL_REQUEST_TEMPLATE.md`

Keep it concise (~30 lines). Sections:
- Summary (1-3 bullets)
- Related Issues (`Closes #N`)
- Changes table
- Diagrams (optional Mermaid)
- Test Plan (checklist)
- Checklist (commit format, docs updated, independent reviewer confirmed the head SHA)

**Purpose**: Saves tokens — Claude Code fills in the skeleton instead of generating structure from scratch.

### 2. Issue Templates (YAML Forms)

**Directory**: `solution/.github/ISSUE_TEMPLATE/`

Generate YAML issue forms + chooser config. Include at minimum:

**`bug.yml`** — Bug report:
- Description (required)
- Steps to Reproduce (required)
- Expected/Actual Behavior (required)
- Component dropdown (detect from project structure)
- Error Output (code block)
- Environment

**`feature.yml`** — Feature request:
- Summary (required)
- Motivation (required)
- Acceptance Criteria (required, checklist)
- Technical Notes (optional)

**`config-addition.yml`** (optional, for plugin/config repos):
- Component type dropdown (e.g., agent, command, skill, hook, rule)
- Name, description, acceptance criteria

**`config.yml`** — Template chooser:
```yaml
blank_issues_enabled: true
contact_links: []
```

### 3. Semantic Versioning (Direct Release)

Automates git tags and GitHub releases directly on push to main — no intermediate release PR.

**How it works**:
1. On push to main, the workflow classifies the commit that landed. A squash subject's title is the pull request title plus ` (#N)`. A leading gitmoji is ignored. An older merge commit (`Merge pull request #N`) is classified from the pull request title, with the merge message's second paragraph as the fallback. The practice is to squash and delete the head branch when the human asks. GitHub still allows merge commits and rebase, and it does not delete the head branch on its own.
2. Bumps `.version`, prepends entry to `CHANGELOG.md`
3. Commits the version bump, creates a git tag, and creates a GitHub Release
4. All in one job — no intermediate PR needed

**Version bump rules (standard SemVer)**:
- `feat` → minor (1.2.3 → 1.3.0)
- `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `security`, `deps` → patch (1.2.3 → 1.2.4)
- Any `type!` subject, or a `BREAKING CHANGE:` footer at the start of a line → major (1.2.3 → 2.0.0)
- A subject that is not in that list → no bump. The shared list is `scripts/commit-types.json`.

**Files to create**:

`solution/.version`:
```
0.1.0
```

`solution/.github/workflows/release.yml`:

The release workflow should:
1. Skip `chore(release):` commits and `github-actions[bot]` actor (loop prevention)
2. Parse the hybrid subject. On a squash commit, strip the trailing ` (#N)`. On a merge commit, read the pull request title instead of `Merge pull request #N`
3. Check commit body for `BREAKING CHANGE:` footer (line must start with it, not just contain it)
4. Bump `.version`, prepend to `CHANGELOG.md` via temp file (not sed)
5. Commit, create idempotent tag (check existence first), push
6. Create GitHub release via `--notes-file` (safe for special characters)
7. Use `concurrency` group to prevent race conditions

**Reference implementation:** See `.github/workflows/release.yml` in this repo for the canonical workflow (~150 lines). Copy and adapt for the generated project's directory structure.

### 4. Auto-Labeler

Applies labels to PRs based on changed file paths.

**`solution/.github/labeler.yml`** — map project directories to labels:
```yaml
# Detect from project structure:
# src/api/** → backend
# src/components/** → frontend
# tests/** → testing
# docs/** → docs
# .github/** → internal
```

**`solution/.github/workflows/labeler.yml`**:
```yaml
name: Labeler

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
          sync-labels: false
```

## Generation Process

1. **Detect project structure** — scan for `src/`, `backend/`, `frontend/`, `tests/`, `docs/`
2. **Detect labels** — check if labels exist via `gh label list`, create missing ones
3. **Generate PR template** — concise skeleton matching project conventions
4. **Generate issue templates** — bug + feature forms with project-specific component dropdowns
5. **Bootstrap version** — create `.version` at `0.1.0` (or detect from existing tags)
6. **Generate release workflow** — direct tag-and-release on push to main
7. **Generate labeler config** — map detected directories to labels
8. **Create all files** under `solution/.github/`

## Integration with Pipeline

The orchestrator should invoke this skill in **Stage 5** alongside CI/CD:

```
Stage 5.3: CI/CD Pipeline + GitHub Config
  - Create solution/.github/workflows/ci.yml
  - Include pip-audit for Python, cargo-deny for Rust, and CodeQL only on public repos
  - CodeQL keeps python. A Rust repository adds rust with build-mode none
  - When CodeQL is skipped it is not reported as `codeql (python)` or `codeql (<language>)`. A private repository does not require those checks
  - Pin these actions by full commit SHA, with a version comment, in the cheap-check jobs:
    - actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
    - astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
    - uv version 0.13.7 (the setup-uv `version` input, not a floating tag)
    - EmbarkStudios/cargo-deny-action@3c6349835b2b7b196a839186cb8b78e02f7b5f25 # v2.1.1
    - github/codeql-action/init and analyze @1fc58d04a4d4374f921bdac573c3811c240f9c26 # v4.39.2
  - Snippets: skills/foundation/devops/references/ci-cd-github-actions.md
  - Generate GitHub config (this skill)
```

## Example Output Structure

```
solution/
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.yml
│   │   ├── feature.yml
│   │   ├── config-addition.yml  # optional, for config repos
│   │   └── config.yml
│   ├── labeler.yml
│   └── workflows/
│       ├── ci.yml
│       ├── release.yml
│       └── labeler.yml
├── .version
└── CHANGELOG.md
```

---
description: "Create a conventional commit with semantic tagging and optional issue linking"
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# Commit

Create a well-structured conventional commit following the project's git workflow skill.

## Input
$ARGUMENTS — Optional: commit message or description of changes. If empty, auto-generates from diff.

## Process

1. **Load git-workflow skill** from `skills/foundation/git-workflow/SKILL.md`
2. **Analyze changes**:
   - Run `git status` to see all changed files
   - Run `git diff --staged` (or `git diff` if nothing staged) to understand changes
   - Run `git log --oneline -5` to match existing commit style
3. **Determine commit type** from changes:
   - New files/features → `feat`
   - Bug fixes → `fix`
   - Documentation → `docs`
   - Refactoring → `refactor`
   - Tests → `test`
   - CI/CD → `ci`
   - Dependencies → `chore(deps)`
   - Docker/infra → `build`
4. **Determine scope** from changed file paths:
   - `backend/` → `backend`
   - `frontend/` → `frontend`
   - `docs/` or `*.md` → `docs`
   - `.github/` → `ci`
   - `Dockerfile` / `docker-compose` → `devops`
   - `infrastructure/` → `infra`
   - Multiple areas → use most impactful scope or omit
5. **Compose commit message**:
   - Subject: `<type>(<scope>): <imperative description>` (max 72 chars)
   - Body: explain WHY, not WHAT (the diff shows WHAT)
   - Footer: `Refs #N` or `Closes #N` if issue number known
6. **Stage files** if not already staged (prefer specific files over `git add -A`)
7. **Check for secrets** — warn if `.env`, credentials, or API keys detected
8. **Create commit** using heredoc format for proper formatting
9. **Suggest semantic tag** if the commit warrants a version bump:
   - `feat` → suggest MINOR bump
   - `fix` → suggest PATCH bump
   - `BREAKING CHANGE` → suggest MAJOR bump
   - Other types → no tag needed

## Output
- Committed changes with conventional commit message
- Suggestion for semantic tag if applicable
- List of files committed

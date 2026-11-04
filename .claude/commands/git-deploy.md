---
description: Push the output directory to a GitHub repository
allowed-tools: Read, Glob, Bash, AskUserQuestion
argument-hint: [github-repo-url]
---

# Git Deployer

Push the generated `solution/` directory to GitHub.

## Usage

- `/git-deploy` - Push to existing remote (if configured) or prompt for URL
- `/git-deploy https://github.com/user/repo` - Push to specified URL

## Deployment Flow

### 1. Check Git Status

```bash
cd solution
git status
git remote -v
```

### 2. Determine Remote Configuration

**If remote already exists** (configured during `/orchestrate`):
- Verify remote URL: `git remote get-url origin`
- Proceed to push

**If no remote and URL provided as argument** ($ARGUMENTS):
- Add remote: `git remote add origin $ARGUMENTS`

**If no remote and no URL provided**:
- Use AskUserQuestion to prompt: "Enter your GitHub repository URL:"
- Add remote with provided URL

### 3. Ensure All Changes Committed

```bash
cd solution
git add .
git status
```

If there are uncommitted changes:
```bash
git commit -m "chore: final updates before deployment"
```

### 4. Push to Remote

```bash
cd solution
git branch -M main
git push -u origin main
```

### 5. Create Release Tag (Optional)

Ask user: "Would you like to create a release tag?"
- If yes:
```bash
git tag -a v1.0.0 -m "Initial release from coding challenge"
git push origin v1.0.0
```

## Validation Before Push

1. Verify no secrets in committed files:
   - Check for `.env` files (should be in .gitignore)
   - Check for credentials or API keys

2. Ensure README.md exists:
```bash
ls solution/README.md
```

3. Verify tests pass (optional):
```bash
cd solution/backend && uv run pytest tests/ -v
```

## Error Handling

### Remote Already Exists with Different URL
```bash
git remote remove origin
git remote add origin <NEW_URL>
```

### Branch Protection
If main is protected, create a PR:
```bash
git checkout -b initial-implementation
git push -u origin initial-implementation
gh pr create --title "Initial implementation" --body "Generated solution from SDLC pipeline"
```

### Authentication Issues
```bash
gh auth status
gh auth login  # If needed
```

## Output

On success, display:
```
✅ Deployed to GitHub

Repository: [URL]
Branch: main
Commit: [SHA]
Tag: v1.0.0 (if created)

View at: [URL]
```

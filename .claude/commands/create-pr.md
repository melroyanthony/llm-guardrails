---
description: "Create a GitHub PR with Mermaid diagrams, linked issues, and a hybrid subject"
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion, Agent
---

# Create Pull Request

Create a well-structured GitHub pull request with Mermaid diagrams, issue linking, and conventional commit title format.

## Input
$ARGUMENTS — Optional: target branch (defaults to main), or issue number to link.

## Process

1. **Load git-workflow skill** from `skills/foundation/git-workflow/SKILL.md`
2. **Analyze branch state**:
   - `git log main..HEAD --oneline` — all commits in this branch
   - `git diff main...HEAD --stat` — all changes vs base branch
   - `git diff main...HEAD` — full diff for understanding changes
   - Check if branch tracks a remote and is up to date
3. **Determine PR title** using the hybrid subject (`<emoji> <type>(<scope>): <lower-case imperative>`):
   - `✨ feat(scope): ...` for features
   - `🐛 fix(scope): ...` for bug fixes
   - Emoji character, not a `:shortcode:`
   - Keep under 72 characters
   - One logical change. If `gh pr create` refuses, report the refusal and stop. Do not merge from this command. A human merges with `gh pr merge <number> --squash --delete-branch`. The commit on main is this title plus ` (#N)`
4. **Generate PR body** with:

   ### Summary section
   - 1-3 bullet points describing the changes

   ### Related Issues section
   - Parse commit messages for `#N` references
   - If $ARGUMENTS contains an issue number, add `Closes #N`
   - If no issue exists, offer to create one first

   ### Architecture/Data Flow diagrams (Mermaid)
   Based on the nature of changes, include relevant diagrams:
   - **API changes** → Sequence diagram showing request flow
   - **Database changes** → ER diagram showing schema
   - **State changes** → State diagram showing transitions
   - **Architecture changes** → C4-style container diagram
   - **Logic changes** → Flowchart showing decision logic
   - Include "Before vs After" diagrams for refactoring PRs

   ### Changes section
   - Categorized list of what changed (added, modified, removed)

   ### Test Plan section
   - Checklist of testing performed

5. **Push branch** if not already pushed (`git push -u origin <branch>`)
6. **Create PR** using `gh pr create` with heredoc body
7. **Return PR URL**

## Output
- PR created with rich body including Mermaid diagrams
- PR URL for user to review

## Example Output

```
gh pr create --title "feat(api): add user registration with email verification" --body "$(cat <<'EOF'
## Summary
- Add POST /api/v1/auth/register endpoint with email/password validation
- Implement email verification flow with token expiry
- Add rate limiting on registration endpoint (5 req/min)

Closes #42

## Architecture

### Registration Flow
```mermaid
sequenceDiagram
    actor U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant E as Email Service

    U->>F: Fill registration form
    F->>B: POST /api/v1/auth/register
    B->>B: Validate input
    B->>DB: Check email uniqueness
    alt Email exists
        DB-->>B: Conflict
        B-->>F: 409 Email taken
    else New email
        B->>DB: INSERT user (unverified)
        B->>E: Send verification email
        B-->>F: 201 Created
        F-->>U: Check your email
    end
```

### Database Changes
```mermaid
erDiagram
    USERS {
        int id PK
        string email UK
        string password_hash
        boolean is_verified
        datetime created_at
    }
    VERIFICATION_TOKENS {
        int id PK
        int user_id FK
        string token UK
        datetime expires_at
    }
    USERS ||--o{ VERIFICATION_TOKENS : "has"
```

## Changes
- **Added**: `app/api/v1/auth.py` — registration endpoint
- **Added**: `app/models/user.py` — User and VerificationToken models
- **Added**: `app/services/email.py` — email verification service
- **Modified**: `app/main.py` — mount auth router
- **Added**: `tests/api/test_auth.py` — registration tests

## Test Plan
- [x] Unit tests for registration validation
- [x] Integration test for full registration flow
- [x] Rate limiting verified with 6 rapid requests
- [x] Email uniqueness constraint verified

EOF
)"
```

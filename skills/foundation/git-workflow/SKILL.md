---
name: git-workflow
description: |
  Git workflow for the hybrid commit subject (gitmoji plus a Conventional Commits header), PR bodies, and issue linking.
  Use when creating commits, PRs, issues, or managing git-based changeset workflows.
  Triggers on: "commit", "PR", "pull request", "issue", "branch", "changelog", "conventional commit", "gitmoji".
---


# Git Workflow

## Commit subject (hybrid)

Default for this catalog, taken from [melroyanthony/crabcake](https://github.com/melroyanthony/crabcake) `AGENTS.md`. It joins two styles the owner uses:

- **tiangolo** (FastAPI, SQLModel, Typer): the subject starts with a Unicode gitmoji, then an imperative verb phrase. Use the emoji character (`🐛`), not a shortcode (`:bug:`), so the title survives outside GitHub. Confirmed on current `main` (`🐛 Fix AliasChoices for named JSON body parameters`, `✨ Add support for SQLAlchemy 2.1`, `🔖 Release version 0.27.3`) and in FastAPI's management-tasks doc.
- **Conventional Commits**: `type(scope): subject`, which carries the semver type.

```
<emoji> <type>(<scope>): <imperative, lower-case subject>

<body>

<footer>
```

```
✨ feat(backend): add argon2 password hashing and jwt issuance
🐛 fix(frontend): refresh the access token before retrying a 401
♻️ refactor(backend): extract sqlx queries into the repo layer
👷 ci(template): build the generated project on every push
⬆️ deps(backend): bump axum to 0.8.9
📝 docs(skills): describe the hybrid commit subject
```

A pure tiangolo title (`✨ Add support for teleporting`) has no `type(scope)` token. Use that shape only when retitling a PR on one of those repos. In this catalog, keep both parts.

crabcake's Dependabot config sets `commit-message.prefix: "⬆️"` and one historical commit used the shortcode `:arrow_up:`. Human and agent commits use the emoji character and the full hybrid subject. There is no commitlint config in that repo; the rule lives in `AGENTS.md`.

## Conventional Commits reference

### Format
```
<emoji> <type>(<scope>): <subject>

<body>

<footer>
```

### Types (Semantic Versioning Impact)

| Type | SemVer | Emoji | Description | Example |
|------|--------|-------|-------------|----------|
| `feat` | MINOR | ✨ | New capability | `✨ feat(api): add user registration endpoint` |
| `fix` | PATCH | 🐛 | Bug fix | `🐛 fix(auth): resolve token expiry race condition` |
| `docs` | - | 📝 | Documentation only | `📝 docs(api): update the openapi spec` |
| `style` | - | 🎨 | Formatting only | `🎨 style(backend): apply ruff formatting` |
| `refactor` | - | ♻️ | Behaviour-preserving restructure | `♻️ refactor(models): extract a base model class` |
| `perf` | PATCH | ⚡️ | Performance | `⚡️ perf(queries): add an index for user lookup` |
| `test` | - | ✅ | Tests | `✅ test(api): add integration tests for auth` |
| `build` | - | 📦 | Docker, packaging, build pipeline | `📦 build(docker): slim the runtime stage` |
| `ci` | - | 👷 | GitHub Actions and other CI | `👷 ci(github): add a staging deploy workflow` |
| `chore` | - | 🔧 | Tooling that is none of the above | `🔧 chore(hooks): warn on a non-hybrid subject` |
| `deps` | PATCH | ⬆️ | Dependency bumps | `⬆️ deps(backend): bump fastapi to 0.115` |
| `security` | PATCH | 🔒️ | Security hardening | `🔒️ security(auth): stop logging refresh tokens` |
| `revert` | varies | ⏪️ | Revert | `⏪️ revert: feat(api): add user registration` |

Other emoji are fine when they describe the change more precisely, in front of the same type token: 🔥 removing code, 🚚 moving or renaming, 🚨 fixing warnings, 💚 fixing CI, 🎉 initial commit, 🔖 a release (`🔖 chore(release): release version 1.2.0`).

### Breaking Changes
Append `!` after type/scope or add `BREAKING CHANGE:` footer:
```
💥 feat(api)!: change authentication to oauth2

BREAKING CHANGE: JWT tokens are no longer accepted. Use OAuth2 bearer tokens.
Closes #42
```

### Scopes
| Scope | When |
|-------|------|
| `backend` | Backend code changes |
| `frontend` | Frontend code changes |
| `database` | Schema, migrations, queries |
| `api` | API contract changes |
| `auth` | Authentication/authorization |
| `devops` | Docker, CI/CD, infrastructure |
| `docs` | Documentation |
| `deps` | Dependency updates |
| `stage-N` | SDLC pipeline stage N |
| `infra` | Infrastructure-as-Code |

### Subject Rules
- Emoji character, then type, then optional scope, then a lower-case imperative subject
- "add", not "added", "adds", or "Add"
- No period at the end
- Whole subject line under 72 characters, emoji included
- No `Co-authored-by` or `Generated with` trailer

### Body Rules
- Explain WHY, not WHAT (the diff shows WHAT)
- Wrap at 72 characters
- Separate from subject with blank line
- Use bullet points for multiple items

### Footer Rules
- `Closes #N` or `Fixes #N` — link to GitHub issues
- `BREAKING CHANGE: description` — for breaking changes
- `Refs #N` — reference related issues without closing
- No `Co-authored-by`, `Generated with`, or other tool-attribution trailers

## Semantic Git Tags

### Version Format
```
v<major>.<minor>.<patch>[-<prerelease>]
```

### Tagging Rules

| Commit Type | Version Bump | Example |
|-------------|-------------|---------|
| `feat` | MINOR | v1.0.0 → v1.1.0 |
| `feat!` / `BREAKING CHANGE` | MAJOR | v1.1.0 → v2.0.0 |
| `fix` / `docs` / `refactor` / `perf` / `chore` / `ci` / `style` / `test` / `build` | PATCH | v1.1.0 → v1.1.1 |

### Tag Commands
```bash
# Create annotated tag
git tag -a v1.0.0 -m "Release v1.0.0: initial release with core CRUD"

# Create tag for specific commit
git tag -a v1.1.0 -m "Release v1.1.0: add authentication" abc1234

# Push tags
git push origin --tags

# List tags
git tag -l "v*" --sort=-v:refname
```

### SDLC Stage Tags
Tag after each major stage completion:
```bash
git tag -a stage-1-complete -m "Requirements analysis complete"
git tag -a stage-2-complete -m "Architecture design complete"
git tag -a stage-3-complete -m "Implementation complete"
git tag -a stage-4-complete -m "Testing and validation complete"
git tag -a v1.0.0 -m "Release v1.0.0: MVP complete"
```

## Pull Request Format

One logical change per PR, small enough to review.

### PR Title
Same hybrid subject as commits. Merge with a squash and delete the head branch. The commit on `main` is that title plus ` (#N)`. `.github/workflows/release.yml` classifies that subject and strips a leading emoji. An older `Merge pull request #N` subject is still classified from the pull request title. The emoji has to be the character itself:

```
<emoji> <type>(<scope>): <imperative lower-case subject>
```

### PR Body

State what changed and why, the linked issue, how you tested, risks and rollback, and any breaking change, migration, or config/env change. Attach screenshots or a recording for UI changes. Add a Mermaid diagram when architecture or data flow changes. When to draw one, which type to pick, and when to update it are the `diagrams` skill. PR examples are in [`references/pr-mermaid-and-templates.md`](references/pr-mermaid-and-templates.md).

```markdown
## What and why
<symptom or goal, and the outcome of this change>

Closes #N

## Evidence
- **Before:** <failing test, command output, or screenshot>
- **After:** <the same check passing>
- Not verified: <what you did not run>

## Merge danger
- **Door:** two-way (revert is enough) or one-way (migration, data, or public API)
- **Blast radius:** <who or what breaks if this is wrong>
- **Rollback:** <revert this PR, or the migration down step>

## Breaking changes, migrations, config
- None.
<!-- or describe the break, the migration, and any new env var -->
```

Evidence (before/after) and the one-way/two-way door are adapted from Matt Pocock's `pr` skill (MIT, https://github.com/mattpocock/skills), which credits Dex Horthy's show-me skill. Linking keywords and the issue-to-merge walkthrough: [`references/issue-and-pr-details.md`](references/issue-and-pr-details.md).

## Branch, CI, and review

- Keep the branch current with its base.
- When the human asks, merge with `gh pr merge <number> --squash --delete-branch`. GitHub still allows merge commits and rebase, and it does not delete the head branch on its own.
- Red CI blocks the PR. Read the failing log and fix the cause. Re-run a check after a real change. When the log shows an infrastructure flake, file an issue for the flake — leave the test enabled.
- Address every review comment with a change or a reasoned reply, then resolve the thread. `/resolve-review` runs the fix rounds. The loop is [`review-loop-to-squash-merge`](../review-loop-to-squash-merge/SKILL.md).
- **Ready to merge** means required CI is green and the independent reviewer has confirmed the current full head SHA, or the lead has waived a hold on that SHA. Confirmation is a message from that reviewer in the `Channel` under `## Review` that quotes the full head SHA and explicitly confirms it. A hold or a request-changes message does not confirm. A new push needs a new confirmation. A reviewer hold blocks the merge until it is fixed or the lead waives that SHA. Before squash-merge, append `Reviewed by <reviewer> at \`<full sha>\`` and the findings. `<reviewer>` is the Independent reviewer named under `## Review`. A waiver appends `Lead waived the hold at \`<full sha>\`` and the findings instead. Ask before merging.
- Commits carry the author's name only. Do not add `Co-authored-by` or `Generated with` trailers.
- Never force-push a shared branch, rewrite pushed history, or skip hooks unless the human explicitly signs off.
- If the forge tool refuses to open or merge the PR, that refusal is the result. Report it. Do not open or merge through a side path.

## References (progressive disclosure)

Load only when needed:

- [`references/gitmoji.md`](references/gitmoji.md)
- [`references/issue-templates.md`](references/issue-templates.md)
- [`references/pr-mermaid-and-templates.md`](references/pr-mermaid-and-templates.md)
- [`references/release-automation.md`](references/release-automation.md)
- [`references/issue-and-pr-details.md`](references/issue-and-pr-details.md)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "CI is red, I'll re-run it" | Read the log. A re-run hides a real failure. Fix the cause, or file a flake with evidence. |
| "I'll force-push to tidy the commits" | Pushed history is shared once someone else can see it. Ask for an explicit sign-off, or add a new commit. |
| "The PR body can just say 'fix bug'" | Reviewers need what, why, how tested, and how to undo it. The diff does not say why. |
| "I'll merge while checks are still running" | Ready to merge means required CI is green and the independent reviewer has confirmed this head SHA. A new push needs a new confirmation. Ask, then merge. |
| "I'll add Co-authored-by so the bot is credited" | This convention forbids attribution trailers. The author on the commit is the credit. |

## Red Flags

- PR mixes a bugfix with an unrelated refactor
- Required check red, skipped, or unread
- Review thread closed with no change and no reply
- Force-push or `--no-verify` without an explicit sign-off
- Merge attempted after the forge tool refused

## Verification

- [ ] Title is a hybrid subject (`<emoji> <type>(<scope>): <lower-case imperative>`) and the PR is one logical change
- [ ] Body has what/why, a link, how tested, risks/rollback, and breaking/migration/config called out
- [ ] Relevant tests, lint, and typecheck were run; unverified items are named
- [ ] Required CI is green and the independent reviewer has confirmed the current head SHA before anyone is asked to merge
- [ ] The squash-merge appends the review record for that full SHA, plus the findings, to the pull request body

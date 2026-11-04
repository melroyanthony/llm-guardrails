---
name: git-workflow
description: Commit subjects, pull request bodies, and the rule against pushing to main. Use when committing, opening a PR, or merging.
---

# Git workflow

Follow `AGENTS.md` § Commit messages and § Pull requests.

## Commit subject

`<emoji> <type>(<scope>): <lower-case imperative>`

- Under 72 characters, no trailing period.
- Body says why and wraps at 72.
- Footers: `Closes #N`, `Fixes #N`, `Refs #N`, `BREAKING CHANGE:`.
- No `Co-authored-by` and no "Generated with".

Types and emoji are `scripts/commit-types.json`. A `!` or a `BREAKING CHANGE:` footer is major.
Every other known type, including `docs` and `chore`, is a patch. `chore(release):` does not
open another release.

## Branch, CI, and review

- Branch from `main`: `feat/issue-N-short-name` or `fix/issue-N-short-name`.
- Never force-push a shared branch. Never push to `main`.
- A forge refusal is the result. Report it. Do not switch remotes or tokens to get around it.
- Red CI blocks the pull request. Read the log. Do not re-run a failure you have not read.
- Ready to merge means required checks are green and the approval rule is met. With no rule
  set, that is checks green plus at least one approval.
- Merge only when the human asks: `gh pr merge <number> --squash --delete-branch`.

## PR body

**What and why** plus `Closes #N`.

**Evidence.** Before, after, not verified.

**Merge danger.** Door (one-way or two-way), blast radius, rollback.

**Breaking changes, migrations, config.**

Add a Mermaid diagram when the architecture or the data flow changes.

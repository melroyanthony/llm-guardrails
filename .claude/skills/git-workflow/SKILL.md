---
name: git-workflow
description: Commit subjects, pull request shape, and direct releases from main. Use when committing, opening a PR, or changing release automation.
---

# Git workflow

## Commit subject

`<emoji> <type>(<scope>): <lower-case imperative>`. Under 72 characters. No trailing period. The body says why. Footers are `Closes #N`, `Fixes #N`, `Refs #N`, or `BREAKING CHANGE:`. No `Co-authored-by` and no "Generated with" trailer.

Types and emoji are the table in `AGENTS.md` and `scripts/commit-types.json`. Extra emoji that keep the same type: 🔥 🚚 🚨 💚 🎉 🔖.

## Pull request

Title is the subject. One label from `feature`, `bug`, `refactor`, `upgrade`, `docs`, `internal`, `breaking`, `security`.

Body:

- **What and why**, with `Closes #N`
- **Evidence**: Before, After, Not verified
- **Merge danger**: Door (one-way or two-way), Blast radius, Rollback
- **Breaking changes, migrations, config**

Add a Mermaid diagram when the architecture or the data flow changes.

Branch from `main` as `feat/issue-N-short-name` or `fix/issue-N-short-name`. Do not force-push a shared branch.

## Release

A releasable push to `main` publishes in one workflow run. `scripts/release_subject.py` takes the highest bump since the last tag and consumes `## Unreleased`. The job commits `🔖 chore(release): vX.Y.Z`, pushes `main` without force, and tags that commit. The release commit does not publish again. It does not publish a wheel.

## Merge

Only when the human asks: `gh pr merge <number> --squash --delete-branch`.

# Issue and pull request details

Load this when creating an issue or filling in a PR body. Diagrams: [`pr-mermaid-and-templates.md`](pr-mermaid-and-templates.md). Issue skeletons: [`issue-templates.md`](issue-templates.md). The required PR sections live in [`../SKILL.md`](../SKILL.md).

## Changeset workflow

1. Open or link a GitHub issue. The title uses the same hybrid subject as the PR: `<emoji> <type>(<scope>): <lower-case imperative>`.
2. Branch from the repo's default base: `feat/issue-N-short-name` or `fix/issue-N-short-name`.
3. Commits reference the issue (`Refs #N` while in progress). The PR uses `Closes #N` when the issue should close on merge.
4. Keep the PR to one logical change. Push and open it with the body from `SKILL.md`.
5. Tag only after merge, and only when the project is cutting a release.

## Linking conventions

| Keyword | Effect |
|---------|--------|
| `Closes #N` | Closes the issue when the PR merges |
| `Fixes #N` | Closes the issue when the PR merges |
| `Resolves #N` | Closes the issue when the PR merges |
| `Refs #N` | References without closing |
| `Part of #N` | Partial work toward an issue |

## Triage note (bugs)

When the issue is a bug, the body starts with:

- Expected behavior vs actual behavior
- Scope, severity, and who is affected
- Repro: steps, environment, versions, logs, and the smallest failing case
- Related issues and PRs (link a duplicate; do not file a second one)

Use the repo's existing labels for type and area (including AFK/HITL on pipeline slices). Put priority in the body unless the repo already has priority labels.

## PR body checklist

- [ ] What and why
- [ ] `Closes #N` or `Refs #N`
- [ ] Evidence: before and after, including what was not verified
- [ ] Merge danger: one-way or two-way door, blast radius, rollback
- [ ] Breaking changes, migrations, and config/env called out, or an explicit "none"
- [ ] Screenshots or a recording for UI changes
- [ ] Mermaid diagram when architecture or data flow changes

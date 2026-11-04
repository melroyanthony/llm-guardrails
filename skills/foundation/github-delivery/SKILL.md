---
name: github-delivery
description: |
  Opt-in GitHub delivery: labels, milestones, Projects v2 status, issue forms, and a Pages docs site.
  Use when filing issues, moving a project board, or publishing the docs site.
  Triggers on: "github project", "labels", "milestone", "docs site", "pages", "sub-issue".
---

# GitHub delivery

The executable is `scripts/github-delivery.py`. It creates missing labels and milestones from `github/labels.json` and `github/milestones.json`. `labels --apply` does not change the color or description of a label that already exists. Pass `--update` to edit those. It does not delete labels it does not own. It does not deploy an app and it does not publish a package.

This catalog's version tags come from `.github/workflows/release.yml`. Merge with a squash, then delete the head branch. The commit on `main` is the pull request title plus ` (#N)`, and the workflow strips a leading emoji. Do not add `changeset publish` here.

## Opt in

`.github/workflows/delivery.yml` runs only when `vars.SDLC_DELIVERY_ENABLED` is `true`.

| Name | Where | Role |
|------|--------|------|
| `SDLC_PROJECT_OWNER` | variable | User or org that owns the project |
| `SDLC_PROJECT_NUMBER` | variable | Project number |
| `SDLC_PROJECT_TOKEN` | secret | A PAT or a GitHub App token. `GITHUB_TOKEN` cannot access Projects v2 at all. A user-owned project needs a classic PAT with the `project` and `repo` scopes |

`python3 scripts/github-delivery.py setup` prints the one-time `gh project field-create` commands. The Status options are Backlog, Ready, In progress, In review, Done. Priority is P0–P3, Size is S/M/L, and Iteration is an iteration field.

## What moves the card

| Event | Status |
|-------|--------|
| Issue opened or reopened | Backlog |
| Pull request opened, reopened, or ready | In review |
| Issue closed, or pull request merged | Done |
| Pull request closed without merge | unchanged |

Ready and In progress are set by a person or by `gh project item-edit`. The workflow does not guess them.

Without the project token the script prints `project skipped` and exits 0. Labels still apply with `GITHUB_TOKEN`.

```bash
python3 scripts/github-delivery.py labels            # dry-run
python3 scripts/github-delivery.py labels --apply    # create missing labels only
python3 scripts/github-delivery.py labels --apply --update
python3 scripts/github-delivery.py milestones --apply
python3 scripts/github-delivery.py --self-test
```

## Issues

Forms already cover a bug and a feature. `task.yml` is a task or an epic. An epic lists sub-issue titles in the form. Open each one with `gh issue create`, then link it as a sub-issue. The form does not open them.

`to-tickets` still writes the tracer bullets. When `gh` is available, create the issues and then run the delivery script so the labels and the board match. `Closes #N` in the pull request body is what closes the issue on merge. The pull request template already has that line.

## Docs site

`mkdocs.yml` is the Zensical config (the same tool CruiseKube uses; trueforge's site is Mintlify, which this catalog does not run). `.github/workflows/docs.yml` builds on pull requests. It publishes GitHub Pages on `main` only when `vars.SDLC_DOCS_ENABLED` is `true`. The site is public even when the repository is private. Leave that variable unset so a repo without Pages does not go red, and so the docs stay unpublished.

A pipeline app copies `templates/docs-site/` and the docs workflow. A package repo that uses Changesets copies `templates/changesets/release.yml`. That file is `workflow_dispatch` only and stops before `changeset publish`. A pull request it opens with `GITHUB_TOKEN` does not trigger other workflows.

## Do not

- Run `changeset publish`, `npm publish`, or `railway up` from this flow
- Turn on `SDLC_DELIVERY_ENABLED` in a fork that should not write labels
- Delete labels that `labeler.yml` applies (`agent`, `command`, `skill`, `hook`, `rule`, `docs`, `internal`)

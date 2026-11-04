## Release Notes Automation (tiangolo-style)

### GitHub Action: Auto-generate Release Notes

Add to `solution/.github/workflows/latest-changes.yml`:

```yaml
name: Latest Changes

on:
  pull_request_target:
    branches: [main]
    types: [closed]

jobs:
  latest-changes:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: tiangolo/latest-changes@0.4.1
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          latest_changes_file: CHANGELOG.md
          latest_changes_header: '## Latest Changes'
          end_regex: '^## '
          label_header_prefix: '### '
          debug_logs: true
```

### Label → Release Notes Section Mapping

Configure labels in the repo settings or via `.github/labels.yml`:

```yaml
# .github/labels.yml (for use with github-labeler action)
- name: breaking
  color: "d73a4a"
  description: "Breaking changes"
- name: security
  color: "e4e669"
  description: "Security fixes"
- name: feature
  color: "0075ca"
  description: "New features"
- name: bug
  color: "d73a4a"
  description: "Bug fixes"
- name: refactor
  color: "cfd3d7"
  description: "Code refactoring"
- name: upgrade
  color: "0e8a16"
  description: "Dependency upgrades"
- name: docs
  color: "0075ca"
  description: "Documentation changes"
- name: internal
  color: "ededed"
  description: "Internal/CI/tooling changes"
```

### Auto-generated Release Notes Format

After PRs merge, `CHANGELOG.md` is automatically updated:

```markdown

## Latest Changes

### Features

* ✨ Add user registration with email verification. PR [#42](https://github.com/org/repo/pull/42) by [@author](https://github.com/author).

### Fixes

* 🐛 Fix token expiry race condition in auth. PR [#43](https://github.com/org/repo/pull/43) by [@author](https://github.com/author).

### Internal

* 👷 Add deploy workflow for staging. PR [#44](https://github.com/org/repo/pull/44) by [@author](https://github.com/author).
```

### Auto-labeler for PRs

Add `.github/labeler.yml` to auto-label based on file paths:

```yaml
# .github/labeler.yml
feature:
  - changed-files:
    - any-glob-to-any-file:
      - 'backend/app/**'
      - 'frontend/app/**'
      - 'frontend/components/**'

bug:
  - changed-files:
    - any-glob-to-any-file:
      - '**/*fix*'

docs:
  - changed-files:
    - any-glob-to-any-file:
      - 'docs/**'
      - '**/*.md'
      - 'solution/docs/**'

internal:
  - changed-files:
    - any-glob-to-any-file:
      - '.github/**'
      - 'scripts/**'
      - '.claude/**'

upgrade:
  - changed-files:
    - any-glob-to-any-file:
      - '**/pyproject.toml'
      - '**/package.json'
      - '**/package-lock.json'
      - '**/uv.lock'
```

And the labeler workflow:

```yaml
# .github/workflows/labeler.yml
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
```

## Release Workflow

### Creating a Release

```bash
# 1. Determine version bump from merged PRs since last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Last release: $LAST_TAG"

# 2. Check commits since last tag for bump type
# - Any feat → MINOR
# - Any fix/docs/refactor/perf/chore/ci/style/test/build → PATCH
# - Any BREAKING CHANGE or feat! → MAJOR
git log ${LAST_TAG}..HEAD --oneline

# 3. Create release commit and tag
# Conventional style:
git commit --allow-empty -m "chore(release): release v1.2.0"
git tag -a v1.2.0 -m "Release v1.2.0"

# Gitmoji style (tiangolo):
git commit --allow-empty -m "🔖 Release version 1.2.0"
git tag -a 1.2.0 -m "Release 1.2.0"  # Note: no 'v' prefix

# 4. Push
git push origin main --tags

# 5. Create GitHub release (auto-generates notes from PRs)
gh release create v1.2.0 --generate-notes --title "v1.2.0"

# Or with custom notes:
gh release create v1.2.0 --title "v1.2.0" --notes "$(cat <<'NOTES'

## Highlights
- ✨ User registration with email verification
- 🐛 Fixed auth token race condition
- ⚡ 3x faster query performance on user lookups

## Full Changelog
See CHANGELOG.md for details.
NOTES
)"
```


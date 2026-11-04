# Releasing

A push to `main` publishes in one GitHub Actions run. The workflow is
[`.github/workflows/release.yml`](.github/workflows/release.yml). It does not
open a pull request. The same run builds the wheels and publishes them to PyPI.
A workflow that started on the tag push would not run: the version commit is
pushed with `GITHUB_TOKEN`.

## When the job runs

The workflow triggers on a push to `main`. The job skips when the actor is
`github-actions[bot]`, or when the head commit message starts with
`chore(release):` or `🔖 chore(release):`. That commit is the release itself,
so it does not start another release.

The workflow file sets `permissions: {}`. The release job sets
`contents: write`. It pushes to `main` with the workflow `GITHUB_TOKEN` and
does not change branch protection.

## Decide

The job runs:

```bash
python3 scripts/release_subject.py \
  --decide \
  --since-tag \
  --version-file .version \
  --rev HEAD
```

`scripts/release_subject.py` reads commits after the highest `vX.Y.Z` tag.
`feat` bumps minor. Every other type in `scripts/commit-types.json` bumps
patch, including `docs`, `chore`, `test`, and `ci`. A `!` before the colon,
or a footer line that starts with `BREAKING CHANGE: ` or `BREAKING-CHANGE: `
followed by text, bumps minor while the version is below 1.0.0 and major from
1.0.0 up. The changelog section is still Breaking changes. A mention in prose
is not a footer. The highest bump in the range wins. A subject that is not
conventional is ignored. If nothing in the range is releasable, the action is
`skip` and the job exits without publishing.

If no `vX.Y.Z` tag exists and `.version` is not `0.0.0`, the script exits
instead of treating the whole history as unreleased.

## Publish

`scripts/release_publish.py publish` writes that decision into:

- `.version`
- `Cargo.toml` `[package].version`. `pyproject.toml` declares
  `dynamic = ["version"]`, and maturin reads the version from `Cargo.toml`
- the `llm-guardrails-core` package in `Cargo.lock`
- `CHANGELOG.md`

Notes under `## Unreleased` become the body of the new version and replace the
generated commit lines. An empty Unreleased section falls back to those
generated lines. The script leaves a fresh empty `## Unreleased` at the top.

The commit subject is `🔖 chore(release): vX.Y.Z`, authored as
`github-actions[bot]`. The job pushes it with
`git push origin HEAD:main` and does not force-push. A non-fast-forward
rejection is retried by rebuilding the commit on `origin/main`, up to four
times. It then creates the `vX.Y.Z` tag on that commit, pushes the tag, and
opens a GitHub Release whose notes point at `CHANGELOG.md`.

A re-run against a version that is already the tip of `main`, or already
tagged, does not create a second commit, tag, or GitHub Release. Wheel jobs
still build when the decision stays `publish`, and the PyPI upload skips
files that are already there.

## Wheels and PyPI

After the tag exists, this same workflow checks out that tag and builds one
abi3-py311 wheel for each of:

- Linux manylinux x86_64 (`ubuntu-latest`)
- Linux manylinux aarch64 (`ubuntu-24.04-arm`)
- macOS arm64 (`macos-latest`)
- macOS x86_64 (`macos-15-intel`)
- Windows x86_64 (`windows-latest`)

It also builds an sdist. The `pypi` job downloads those artifacts, writes an
SPDX SBOM, uploads the distributions with PyPI trusted publishing (OIDC,
`id-token: write`, provenance attestations), and attaches the SBOM to the
GitHub Release. There is no PyPI API token.

The publish job uses the GitHub environment `pypi`. Before the first release,
register a trusted publisher on PyPI:

| Setting | Value |
| --- | --- |
| PyPI project name | `ferroguard` |
| Owner | `melroyanthony` |
| Repository name | `llm-guardrails` |
| Workflow filename | `release.yml` |
| Environment name | `pypi` |

Create the GitHub environment `pypi` on this repository with no secret and no
required reviewer, unless a reviewer should approve each publish. Use a
pending publisher if the PyPI project does not exist yet.

## Local checks

These do not push:

```bash
python3 scripts/release_subject.py --self-test
python3 scripts/release_publish.py --self-test
```

# Releasing

A push to `main` opens a release pull request. Merging that pull request
publishes in the workflow run that the merge starts. The workflow is
[`.github/workflows/release.yml`](.github/workflows/release.yml). It does not
push `main`. PyPI trusted publishing runs in that merge run. A workflow that
started on the tag push would not run: the tag is pushed with `GITHUB_TOKEN`.

## When the jobs run

The workflow triggers on a push to `main`.

The `release` job runs when the actor is not `github-actions[bot]` and the
head commit message does not start with `chore(release):` or
`🔖 chore(release):`. It opens `release/vX.Y.Z`. It does not tag and it does
not publish.

The `ship` job runs when the actor is not `github-actions[bot]` and the head
commit message does start with one of those prefixes. That commit is the
squash-merge of the release pull request. The job tags it. A merge performed
by `github-actions[bot]` does not start the workflow, so a person merges the
release pull request.

The workflow file sets `permissions: {}`. The `release` job sets
`contents: write`, `pull-requests: write`, and `actions: write`. It pushes
`release/vX.Y.Z` and opens the pull request. It does not push `main`.
`actions: write` is only on that job. It dispatches CI and lists Release
runs for an unfinished tag. The `recover` job stays `actions: read`. The
`ship` job sets `contents: write` so it can push the tag and create the
GitHub Release. The `recover` job stays `contents: read`, so it cannot push.

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

`scripts/release_publish.py open-pr` writes that decision into:

- `.version`
- `Cargo.toml` `[package].version`. `pyproject.toml` declares
  `dynamic = ["version"]`, and maturin reads the version from `Cargo.toml`
- the `llm-guardrails-core` package in `Cargo.lock`
- `CHANGELOG.md`

Notes under `## Unreleased` become the body of the new version and replace the
generated commit lines. An empty Unreleased section falls back to those
generated lines. The script leaves a fresh empty `## Unreleased` at the top.

The commit subject is `🔖 chore(release): vX.Y.Z`, authored as
`github-actions[bot]`. The job pushes that commit to `release/vX.Y.Z` and
opens a pull request into `main`. It does not force-push. If that branch
exists and is not based on current `main`, the job deletes only
`release/vX.Y.Z` and pushes it again. It never deletes `main`.

That pull request is opened with `GITHUB_TOKEN`, so the `pull_request`
event does not start CI. After `_ensure_pr`, the release job runs
`gh workflow run ci.yml --ref release/vX.Y.Z`. `ci.yml` allows
`workflow_dispatch`. The checks on the release pull request come from that
dispatch. The PyPI job is unchanged: it stays in this workflow, uses the
`pypi` environment, and runs from the push to `main` that merging the
release pull request starts. There is no tag trigger.

When this opens a version, it closes any older open pull request whose head
is `release/vX.Y.Z` and deletes that branch. The same guard refuses every
other name, including `main`.

Squash-merge the pull request so the commit subject stays
`🔖 chore(release): vX.Y.Z`. That merge starts this workflow again. The
`ship` job runs `scripts/release_publish.py publish-tag`, which creates the
`vX.Y.Z` tag on that commit, pushes the tag, and opens a GitHub Release
whose notes point at `CHANGELOG.md`. It does not create another commit and
it does not push `main`.

A re-run against a version that is already the tip of `main`, or already
tagged, does not create a second commit, tag, or GitHub Release. Wheel jobs
build when `ship` tags the merge, or when recovery still needs wheels. The
PyPI upload skips files that are already there.

## Wheels and PyPI

After the tag exists, this same workflow checks out that tag and builds one
abi3-py311 wheel for each of:

- Linux x86_64 (`ubuntu-latest`) and aarch64 (`ubuntu-24.04-arm`), both with
  `manylinux: auto`. That builds in the manylinux2014 image. The wheel
  filename carries `manylinux_2_17_<arch>` and the `manylinux2014_<arch>` alias.
- macOS arm64 (`macos-latest`)
- macOS x86_64 (`macos-15-intel`)
- Windows x86_64 (`windows-latest`)

It also builds an sdist. The `pypi` job only downloads those artifacts and
uploads them with PyPI trusted publishing. Its permissions are `id-token: write`
and `actions: read` (so it can download this run's artifacts). PEP 740
attestations are signed with that OIDC token. The job does not have
`attestations: write` or `contents: write`. There is no PyPI API token.

A later job has `contents: write` and `actions: read`. It downloads the
files just published to PyPI, checks each SHA256 against the project index,
and catalogs the wheels with Syft's installed-package cataloger. The SBOM
names `ferroguard` at that version. `Requires-Dist` entries are declared
requirements, not resolved installations. The job refuses a directory-only
document before `gh release upload --repo`. The repository comes from
`github.repository`.

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
required reviewer, unless a reviewer should approve each publish. Limit that
environment's deployment branches to `main`, so a workflow on another branch
cannot use the trusted publisher. Use a pending publisher if the PyPI project
does not exist yet.

## Unfinished release

`v0.3.1` is that release. The tag is
`59888df627d42097d66c895f048d10bae1f5fc4d`. Run
[42093909645](https://github.com/melroyanthony/llm-guardrails/actions/runs/42093909645)
published the wheels. Run
[42102035174](https://github.com/melroyanthony/llm-guardrails/actions/runs/42102035174)
attached the SBOM from that scan:
[llm-guardrails-sbom.spdx.json](https://github.com/melroyanthony/llm-guardrails/releases/download/v0.3.1/llm-guardrails-sbom.spdx.json).
Syft scanned the wheel directory, so the document's only package is `dist`
with `filesAnalyzed: false`. It does not name `ferroguard` 0.3.1.

Do not re-run those workflows. Do not delete or move the tag. Do not
dispatch a run from this branch. Do not rebuild the wheels or publish them
again. After this change is on `main`, the next push calls
`release_recover.py --resolve`. The attached SPDX fails the content check
and PyPI already has 0.3.1, so the action is `sbom`. The release job exits
before `release_publish.py`. `selected` outputs `mode=sbom` and `tag=v0.3.1`.
The wheel, sdist, and PyPI jobs stay skipped. The SBOM job downloads the
published wheels and sdist, refuses them unless each SHA256 matches the
project index, catalogs each wheel, writes `ferroguard.spdx.json`, refuses
the directory-only shape, and runs:

```text
gh release upload v0.3.1 ferroguard.spdx.json --repo melroyanthony/llm-guardrails --clobber
```

It then deletes `llm-guardrails-sbom.spdx.json` because that asset still
fails the check. `v0.3.1` stays at
`59888df627d42097d66c895f048d10bae1f5fc4d`. A later push cuts the next
version only after the attached SPDX names `ferroguard` 0.3.1. A future
unfinished tag whose PyPI job did not succeed still returns `recover` and
rebuilds the wheels.

To retry without another commit, run this workflow with `workflow_dispatch`
from `main`, set `recover_tag` to `v0.3.1`, and leave `recover_mode` at
`sbom`. The dispatch job has `contents: read` only. It refuses any tag
except the latest unfinished `vX.Y.Z` tag on `main`, and it refuses
`recover_mode=wheels` while PyPI has already succeeded.

## Local checks

These do not push:

```bash
python3 scripts/release_subject.py --self-test
python3 scripts/release_publish.py --self-test
python3 scripts/release_recover.py --self-test
python3 scripts/release_sbom.py --self-test
```

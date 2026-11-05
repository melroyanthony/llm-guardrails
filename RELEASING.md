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

A later job has `contents: write` and `actions: read`. When this run built
the wheels, it writes an SPDX SBOM with `output-file` and `artifact-name`
both set to `ferroguard.spdx.json`, checks that the file exists, and uploads
it with `gh release upload --repo`. The repository comes from
`github.repository`, so the upload does not need `git` to infer it. When PyPI
already succeeded and that upload did not, the job downloads the saved
artifact instead of building again. The failed v0.3.1 run stored that file
as `llm-guardrails-sbom.spdx.json`.

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
built the wheels, and its Publish to PyPI job succeeded. Release SBOM failed
before any asset was attached: `gh release upload` had no checkout, so it
could not infer the repository, and it named `ferroguard.spdx.json` while
the action stored artifact `llm-guardrails-sbom.spdx.json` (artifact
`13447181343`). The GitHub Release still has no assets.

Do not re-run that workflow. It is pinned to the file from before this
change. Do not delete or move the tag. Do not dispatch a run from this
branch. After this change is on `main`, the next push calls
`release_recover.py --resolve`. That sees the tag, the empty asset list, and
the successful Publish to PyPI job, and it returns action `sbom`. The release
job then exits without `release_publish.py`, so it does not create a commit
or a tag. `selected` outputs `mode=sbom` and `tag=v0.3.1`. The wheel, sdist,
and PyPI jobs stay skipped. The SBOM job checks out the script only, finds
the newest completed Release run whose Publish to PyPI job succeeded and
whose Release SBOM job did not, downloads `llm-guardrails-sbom.spdx.json`,
checks that the file exists, and runs:

```text
gh release upload v0.3.1 sbom-in/llm-guardrails-sbom.spdx.json --repo melroyanthony/llm-guardrails --clobber
```

`v0.3.1` stays at `59888df627d42097d66c895f048d10bae1f5fc4d`. A later push cuts
the next version only after that SBOM asset exists. A future unfinished tag
whose PyPI job did not succeed still returns `recover` and rebuilds the
wheels. `v0.3.1` returns `sbom`, so its wheel jobs stay skipped.

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
```

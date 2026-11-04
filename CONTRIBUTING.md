# Contributing

Thanks for helping with `llm_guardrails`. By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md). Contributions are licensed under the
[MIT License](LICENSE).

Report a vulnerability in private. See [SECURITY.md](SECURITY.md). Do not open
a public issue for one.

## Setup

You need [Rust](https://rustup.rs/) and [uv](https://docs.astral.sh/uv/).
Opening the repo selects the stable channel in `rust-toolchain.toml`, including
rustfmt and clippy. Python 3.11 or newer works. Development uses 3.14
(`.python-version`).

With [just](https://just.systems/) installed:

```bash
just setup
```

That is the same as:

```bash
uv sync --locked --all-extras
uv run --with maturin maturin develop
```

`uv sync --locked --all-extras` installs the locked environment. `--all-extras`
is the `api` extra (FastAPI and uvicorn). pytest and ruff are the default
`dev` dependency group in `pyproject.toml`, not an extra, so they are
installed without `--extra dev`. `maturin develop` builds the PyO3 extension
into that environment and leaves it editable. pytest imports
`llm_guardrails._core`, so the extension
has to exist first. Python edits are picked up from the editable install.
Run `uv run --with maturin maturin develop` again after you change Rust.

`just build` is the same recipe as `just setup`.

## Tests

```bash
just test
```

`cargo test` runs the Rust tests in `src/`. `uv run pytest` runs `tests/`.

## Lint and format

Ruff line length stays 100 (`pyproject.toml`). This repo does not use Black
or isort.

```bash
just lint
just fmt
```

`just lint` runs:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `cargo fmt --check`
- `cargo clippy --all-targets -- -D warnings`

`just fmt` writes formatting with `uv run ruff format .` and `cargo fmt`.

`just ci` runs setup, lint, tests, `scripts/test_guardrails.py`, and the
release self-tests that GitHub Actions runs.

Optional, the same ruff and cargo checks on commit:

```bash
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

`.pre-commit-config.yaml` also runs basic hygiene hooks (whitespace, YAML,
TOML, private keys, merge conflicts).

## Commits

`<emoji> <type>(<scope>): <lower-case imperative>`. Under 72 characters. No
trailing period. The body says why. A scope is optional.

| Type | Emoji | Use for |
| --- | --- | --- |
| `feat` | ✨ | New capability |
| `fix` | 🐛 | Bug fix |
| `docs` | 📝 | Documentation |
| `test` | ✅ | Tests |
| `ci` | 👷 | GitHub Actions and other CI config |
| `chore` | 🔧 | Tooling and config that is none of the above |

The full table, and how a breaking change is marked, is in
[AGENTS.md](AGENTS.md). `Closes #N` goes in the footer when an issue exists.

## Pull requests

Branch from `main`. A name like `feat/issue-N-short-name` or
`fix/issue-N-short-name` is enough.

The title is the commit subject. Use the sections in
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md): what
and why (`Closes #N`), what you ran, how to revert, and any breaking change.
Run `just ci` before you ask for review.

A maintainer squash-merges. The squash commit on `main` is the pull request
title. Do not force-push `main`.

set shell := ["bash", "-uc"]

# List available recipes
default:
    @just --list

# Install the locked environment and build the PyO3 extension
setup:
    uv sync --locked --all-extras
    uv run --with maturin maturin develop

# Same as setup
build: setup

# Rust tests and pytest
test:
    cargo test
    uv run pytest

# Ruff, rustfmt, and clippy. Ruff line length stays 100
lint:
    uv run ruff check .
    uv run ruff format --check .
    cargo fmt --check
    cargo clippy --all-targets -- -D warnings

# Format Python and Rust
fmt:
    uv run ruff format .
    cargo fmt

# Setup, lint, tests, release self-tests, and scripts/test_guardrails.py
ci: setup lint test
    python3 scripts/release_subject.py --self-test
    python3 scripts/release_publish.py --self-test
    python3 scripts/test_guardrails.py

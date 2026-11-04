"""The PyPI distribution name and the release publish path."""

from importlib.metadata import version
from pathlib import Path

import llm_guardrails

ROOT = Path(__file__).resolve().parents[1]


def test_distribution_is_ferroguard_and_import_stays():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    cargo = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    assert '\nname = "ferroguard"\n' in pyproject
    assert 'module-name = "llm_guardrails._core"' in pyproject
    assert "abi3-py311" in cargo
    assert llm_guardrails.__name__ == "llm_guardrails"
    assert version("ferroguard")


def test_release_publishes_inside_release_yml():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    header, _, jobs = workflow.partition("jobs:")
    assert "tags:" not in header
    assert "environment: pypi" in jobs
    assert "id-token: write" in jobs
    assert "attestations: true" in jobs
    assert "maturin sdist" in jobs
    assert "ferroguard.spdx.json" in jobs
    assert "PYPI_TOKEN" not in workflow
    assert "password:" not in workflow
    for needle in (
        "ubuntu-latest",
        "ubuntu-24.04-arm",
        "macos-latest",
        "macos-15-intel",
        "windows-latest",
    ):
        assert needle in workflow
    scorecard = (ROOT / ".github/workflows/scorecard.yml").read_text(encoding="utf-8")
    assert "ossf/scorecard-action@" in scorecard
    assert "publish_results: true" in scorecard
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "maturin build" in ci
    assert "3.14" in ci

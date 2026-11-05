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
    _, _, after_pypi = jobs.partition("\n  pypi:")
    pypi, _, sbom = after_pypi.partition("\n  sbom:")
    assert "environment: pypi" in pypi
    assert "attestations: true" in pypi
    assert "attestations: write" not in pypi
    assert "contents: write" not in pypi
    perm_block = pypi.split("permissions:", 1)[1].split("steps:", 1)[0]
    perm_lines = [
        line.strip()
        for line in perm_block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert perm_lines == ["id-token: write", "actions: read"]
    assert pypi.index("- name: Collect distributions") < pypi.index("- name: Publish to PyPI")
    for tag in (
        "cp311-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl",
        "cp311-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl",
        "-cp311-abi3-win_amd64.whl",
        "_x86_64.whl",
        "_arm64.whl",
    ):
        assert (
            tag
            in pypi.split("- name: Collect distributions", 1)[1].split(
                "- name: Publish to PyPI", 1
            )[0]
        )
    assert "len(wheels) != 5" in pypi
    assert "exactly one sdist" in pypi
    assert "needs: pypi" in sbom
    assert "contents: write" in sbom
    assert "anchore/sbom-action@" in sbom
    assert "ferroguard.spdx.json" in sbom
    wheels_job = jobs.split("\n  wheels:", 1)[1].split("\n  sdist:", 1)[0]
    assert "enable-cache: false" in wheels_job
    assert "maturin sdist" in jobs
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
    assert "PyO3/maturin-action@" in ci
    assert "manylinux: auto" in ci
    assert "target: x86_64" in ci
    assert "--interpreter python3.11" in ci
    assert "manylinux_2_17_x86_64" in ci
    assert 'python" -P' in ci
    assert "3.14" in ci

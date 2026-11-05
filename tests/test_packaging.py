"""The PyPI distribution name and the release publish path."""

import re
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
    recover_job = jobs.split("\n  recover:", 1)[1].split("\n  selected:", 1)[0]
    assert "contents: read" in recover_job
    assert "contents: write" not in recover_job
    assert "id-token:" not in recover_job
    assert "workflow_dispatch:" in header
    assert "github.event_name == 'push'" in jobs.split("\n  recover:", 1)[0]
    source = (ROOT / "scripts" / "release_recover.py").read_text(encoding="utf-8")
    assert "git push" not in source
    assert "git tag" not in source
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


_TOKEN = re.compile(r"!cancelled\(\)|&&|\|\||==|\(|\)|'[^']*'|[A-Za-z_][\w.]*")
_JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_IF = re.compile(r"^    if:\s*(.+)$")
_NEEDS = re.compile(r"^    needs:\s*(.+)$")
_CHAIN = ("selected", "wheels", "sdist", "pypi", "sbom")


def _workflow_controls(workflow: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    current = None
    conditions: dict[str, str] = {}
    needs: dict[str, list[str]] = {}
    for line in workflow.splitlines():
        job = _JOB.match(line)
        if job:
            current = job.group(1)
            needs.setdefault(current, [])
            continue
        if current is None:
            continue
        condition = _IF.match(line)
        if condition and current not in conditions:
            conditions[current] = condition.group(1).strip()
        needed = _NEEDS.match(line)
        if needed:
            raw = needed.group(1).strip()
            if raw.startswith("["):
                needs[current] = [part.strip() for part in raw[1:-1].split(",")]
            else:
                needs[current] = [raw]
    return conditions, needs


class _Expr:
    def __init__(self, text: str) -> None:
        body = text.strip()
        if body.startswith("${{") and body.endswith("}}"):
            body = body[3:-2].strip()
        self.tokens = _TOKEN.findall(body)
        self.index = 0

    def parse(
        self,
        results: dict[str, str],
        outputs: dict[str, dict[str, str]],
        cancelled: bool,
    ) -> bool:
        value = self._or_expr(results, outputs, cancelled)
        if self.index != len(self.tokens):
            raise AssertionError(self.tokens[self.index :])
        return value

    def _or_expr(self, results, outputs, cancelled) -> bool:
        value = self._and_expr(results, outputs, cancelled)
        while self._peek() == "||":
            self.index += 1
            right = self._and_expr(results, outputs, cancelled)
            value = value or right
        return value

    def _and_expr(self, results, outputs, cancelled) -> bool:
        value = self._primary(results, outputs, cancelled)
        while self._peek() == "&&":
            self.index += 1
            right = self._primary(results, outputs, cancelled)
            value = value and right
        return value

    def _primary(self, results, outputs, cancelled) -> bool:
        item = self._pop()
        if item == "(":
            value = self._or_expr(results, outputs, cancelled)
            if self._pop() != ")":
                raise AssertionError("missing closing parenthesis")
            return value
        if item == "!cancelled()":
            return not cancelled
        if self._peek() != "==":
            raise AssertionError(item)
        self.index += 1
        expected = self._pop().strip("'")
        return _lookup(item, results, outputs) == expected

    def _peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def _pop(self) -> str:
        item = self._peek()
        if item is None:
            raise AssertionError("unexpected end of expression")
        self.index += 1
        return item


def _lookup(token: str, results: dict[str, str], outputs: dict[str, dict[str, str]]) -> str:
    parts = token.split(".")
    if len(parts) == 3 and parts[0] == "needs" and parts[2] == "result":
        return results.get(parts[1], "skipped")
    if len(parts) == 4 and parts[0] == "needs" and parts[2] == "outputs":
        return outputs.get(parts[1], {}).get(parts[3], "")
    raise AssertionError(token)


def _ancestor_skipped(job: str, results: dict[str, str], needs: dict[str, list[str]]) -> bool:
    for dependency in needs.get(job, []):
        if results.get(dependency) == "skipped":
            return True
        if _ancestor_skipped(dependency, results, needs):
            return True
    return False


def _simulate(
    conditions: dict[str, str],
    needs: dict[str, list[str]],
    roots: dict[str, str],
    *,
    cancelled: bool = False,
    published: str = "true",
    fail: set[str] | None = None,
) -> dict[str, str]:
    """Apply the workflow conditions, including skip propagation."""
    failed = fail or set()
    results = dict(roots)
    outputs: dict[str, dict[str, str]] = {
        "release": {"published": published if results.get("release") == "success" else ""},
        "recover": {"published": published if results.get("recover") == "success" else ""},
    }
    for job in _CHAIN:
        expression = conditions[job]
        opted_out = "!cancelled()" in expression or "always()" in expression
        if not opted_out and _ancestor_skipped(job, results, needs):
            results[job] = "skipped"
        elif _Expr(expression).parse(results, outputs, cancelled):
            results[job] = "failure" if job in failed else "success"
        else:
            results[job] = "skipped"
        if job == "selected" and results[job] == "success":
            release_ready = (
                results.get("release") == "success" and outputs["release"]["published"] == "true"
            )
            recover_ready = (
                results.get("recover") == "success" and outputs["recover"]["published"] == "true"
            )
            outputs[job] = {
                "published": "true" if release_ready or recover_ready else "false",
                "tag": "v0.3.1" if release_ready or recover_ready else "",
            }
        else:
            outputs[job] = {"published": "", "tag": ""}
    return results


def test_release_gates_cover_push_dispatch_failure_and_cancellation():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    conditions, needs = _workflow_controls(workflow)
    assert needs["wheels"] == ["selected"]
    assert needs["sdist"] == ["selected"]
    assert needs["pypi"] == ["selected", "wheels", "sdist"]
    assert needs["sbom"] == ["pypi"]
    for job in ("wheels", "sdist", "pypi", "sbom"):
        assert "!cancelled()" in conditions[job]
        for dependency in needs[job]:
            assert f"needs.{dependency}.result == 'success'" in conditions[job]

    def run(roots, **kwargs):
        return _simulate(conditions, needs, roots, **kwargs)

    push = {"release": "success", "recover": "skipped"}
    dispatch = {"release": "skipped", "recover": "success"}
    for roots in (push, dispatch):
        happy = run(roots)
        assert happy["wheels"] == "success"
        assert happy["sdist"] == "success"
        assert happy["pypi"] == "success"
        assert happy["sbom"] == "success"
        wheels_failed = run(roots, fail={"wheels"})
        assert wheels_failed["pypi"] == "skipped"
        assert wheels_failed["sbom"] == "skipped"
        sdist_failed = run(roots, fail={"sdist"})
        assert sdist_failed["pypi"] == "skipped"
        assert sdist_failed["sbom"] == "skipped"
        pypi_failed = run(roots, fail={"pypi"})
        assert pypi_failed["sbom"] == "skipped"
        cancelled = run(roots, cancelled=True)
        assert cancelled["wheels"] == "skipped"
        assert cancelled["sdist"] == "skipped"
        assert cancelled["pypi"] == "skipped"
        assert cancelled["sbom"] == "skipped"

    idle = run(push, published="false")
    assert idle["wheels"] == "skipped"
    assert idle["sdist"] == "skipped"
    assert idle["pypi"] == "skipped"
    assert idle["sbom"] == "skipped"
    release_failed = run({"release": "failure", "recover": "skipped"})
    assert release_failed["selected"] == "skipped"
    assert release_failed["pypi"] == "skipped"
    recover_failed = run({"release": "skipped", "recover": "failure"})
    assert recover_failed["selected"] == "skipped"
    assert recover_failed["pypi"] == "skipped"

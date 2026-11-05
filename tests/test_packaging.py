"""The PyPI distribution name and the release publish path."""

import json
import os
import re
import subprocess
import sys
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
    assert "needs: [selected, pypi]" in sbom
    assert "contents: write" in sbom
    assert "actions: read" in sbom
    assert "id-token:" not in sbom
    assert "anchore/sbom-action@" in sbom
    assert "artifact-name: ferroguard.spdx.json" in sbom
    assert "output-file: ferroguard.spdx.json" in sbom
    assert "upload-release-assets: false" in sbom
    assert "--repo" in sbom
    assert "--upload-saved-sbom" in sbom
    assert "needs.selected.outputs.mode == 'sbom'" in sbom
    assert "needs.selected.outputs.tag" in sbom
    assert "needs.pypi.outputs.tag" not in sbom
    assert "gh release upload" not in sbom
    assert "persist-credentials: false" in sbom
    assert "/" + "tmp/sbom-action-" not in workflow
    wheels_job = jobs.split("\n  wheels:", 1)[1].split("\n  sdist:", 1)[0]
    assert "enable-cache: false" in wheels_job
    assert "needs.selected.outputs.mode == 'wheels'" in wheels_job
    assert "needs.selected.outputs.mode == 'wheels'" in pypi
    release_job = jobs.split("\n  release:", 1)[1].split("\n  recover:", 1)[0]
    assert "actions: read" in release_job
    assert "id-token:" not in release_job
    recover_job = jobs.split("\n  recover:", 1)[1].split("\n  selected:", 1)[0]
    assert "contents: read" in recover_job
    assert "actions: read" in recover_job
    assert "contents: write" not in recover_job
    assert "id-token:" not in recover_job
    assert "workflow_dispatch:" in header
    assert "github.event_name == 'push'" in jobs.split("\n  recover:", 1)[0]
    source = (ROOT / "scripts" / "release_recover.py").read_text(encoding="utf-8")
    assert "git push" not in source
    assert "git tag" not in source
    assert '"--repo"' in source
    assert "llm-guardrails-sbom.spdx.json" in source
    assert "ferroguard.spdx.json" in source
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
    mode: str = "wheels",
    fail: set[str] | None = None,
) -> dict[str, str]:
    """Apply the workflow conditions, including skip propagation."""
    failed = fail or set()
    results = dict(roots)
    ready_mode = mode if published == "true" else ""
    outputs: dict[str, dict[str, str]] = {
        "release": {
            "published": published if results.get("release") == "success" else "",
            "mode": ready_mode if results.get("release") == "success" else "",
        },
        "recover": {
            "published": published if results.get("recover") == "success" else "",
            "mode": ready_mode if results.get("recover") == "success" else "",
        },
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
            chosen = ""
            if release_ready:
                chosen = outputs["release"].get("mode", "")
            elif recover_ready:
                chosen = outputs["recover"].get("mode", "")
            outputs[job] = {
                "published": "true" if release_ready or recover_ready else "false",
                "tag": "v0.3.1" if release_ready or recover_ready else "",
                "mode": chosen if chosen in {"wheels", "sbom"} else "skip",
            }
        else:
            outputs[job] = {"published": "", "tag": "", "mode": ""}
    return results


def test_release_gates_cover_push_dispatch_failure_and_cancellation():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    conditions, needs = _workflow_controls(workflow)
    assert needs["wheels"] == ["selected"]
    assert needs["sdist"] == ["selected"]
    assert needs["pypi"] == ["selected", "wheels", "sdist"]
    assert needs["sbom"] == ["selected", "pypi"]
    for job in ("wheels", "sdist", "pypi", "sbom"):
        assert "!cancelled()" in conditions[job]
        for dependency in needs[job]:
            assert f"needs.{dependency}.result == 'success'" in conditions[job]
    for job in ("wheels", "sdist", "pypi"):
        assert "needs.selected.outputs.mode == 'wheels'" in conditions[job]
    assert "needs.selected.outputs.mode == 'sbom'" in conditions["sbom"]

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
        saved = run(roots, mode="sbom")
        assert saved["wheels"] == "skipped"
        assert saved["sdist"] == "skipped"
        assert saved["pypi"] == "skipped"
        assert saved["sbom"] == "success"
        saved_cancelled = run(roots, mode="sbom", cancelled=True)
        assert saved_cancelled["sbom"] == "skipped"
        assert saved_cancelled["pypi"] == "skipped"

    idle = run(push, published="false")
    assert idle["wheels"] == "skipped"
    assert idle["sdist"] == "skipped"
    assert idle["pypi"] == "skipped"
    assert idle["sbom"] == "skipped"
    idle_sbom = run(push, published="false", mode="sbom")
    assert idle_sbom["pypi"] == "skipped"
    assert idle_sbom["sbom"] == "skipped"
    release_failed = run({"release": "failure", "recover": "skipped"})
    assert release_failed["selected"] == "skipped"
    assert release_failed["pypi"] == "skipped"
    recover_failed = run({"release": "skipped", "recover": "failure"})
    assert recover_failed["selected"] == "skipped"
    assert recover_failed["pypi"] == "skipped"


def _recover():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import release_recover

    return release_recover


def test_sbom_plan_skips_wheels_after_pypi_succeeded():
    recover = _recover()
    subject = "🔖 chore(release): v0.3.1"
    assert recover.plan("v0.3.1", subject, True, 0, pypi_succeeded=True) == {
        "action": "sbom",
        "tag": "v0.3.1",
    }
    assert recover.plan("v0.3.1", subject, True, 0)["action"] == "recover"
    assert recover.workflow_mode("sbom") == "sbom"
    assert recover.workflow_mode("recover") == "wheels"
    saved = recover.select_saved_sbom(
        [
            {
                "databaseId": 1,
                "status": "in_progress",
                "tag": "v0.3.1",
                "jobs": [],
                "artifact_names": ["ferroguard.spdx.json"],
            },
            {
                "databaseId": 42093909645,
                "status": "completed",
                "tag": "v0.3.1",
                "jobs": [
                    {"name": "Publish to PyPI", "conclusion": "success"},
                    {"name": "Release SBOM", "conclusion": "failure"},
                ],
                "artifact_names": ["llm-guardrails-sbom.spdx.json"],
            },
        ],
        "v0.3.1",
    )
    assert saved == {
        "run_id": "42093909645",
        "name": "llm-guardrails-sbom.spdx.json",
    }


def test_sbom_upload_uses_explicit_repo_without_a_checkout(tmp_path, monkeypatch):
    recover = _recover()
    work = tmp_path / "no-git"
    work.mkdir()
    sbom = work / "llm-guardrails-sbom.spdx.json"
    sbom.write_text('{"spdxVersion": "SPDX-2.3"}\n', encoding="utf-8")
    record = tmp_path / "args"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import pathlib\n"
        "import sys\n"
        "pathlib.Path(os.environ['SBOM_ARGS_FILE']).write_text('\\n'.join(sys.argv) + '\\n')\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SBOM_ARGS_FILE", str(record))
    monkeypatch.chdir(work)

    def run(argv):
        return subprocess.run(  # noqa: S603
            argv,
            cwd=work,
            check=False,
            capture_output=True,
            text=True,
        )

    expected = [
        "gh",
        "release",
        "upload",
        "v0.3.1",
        str(sbom),
        "--repo",
        "melroyanthony/llm-guardrails",
        "--clobber",
    ]
    argv = recover.upload_release_asset(
        "v0.3.1",
        sbom,
        "melroyanthony/llm-guardrails",
        run=run,
    )
    assert argv == expected
    recorded = record.read_text(encoding="utf-8").splitlines()
    assert Path(recorded[0]).name == "gh"
    assert recorded[1:] == expected[1:]
    assert not (work / ".git").exists()
    current = work / "ferroguard.spdx.json"
    current.write_text("{}\n", encoding="utf-8")
    current_argv = recover.upload_release_asset(
        "v0.3.1",
        current,
        "melroyanthony/llm-guardrails",
        run=run,
    )
    assert current_argv[4] == str(current)
    assert "--repo" in current_argv


def test_missing_sbom_is_not_uploaded(tmp_path):
    recover = _recover()
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv)
        raise AssertionError(argv)

    try:
        recover.upload_release_asset(
            "v0.3.1",
            tmp_path / "ferroguard.spdx.json",
            "melroyanthony/llm-guardrails",
            run=run,
        )
    except SystemExit as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("missing SBOM was uploaded")
    assert calls == []


def _completed(argv: list[str], payload) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")


_V031_TAGS = [{"name": "v0.3.1", "sha": "59888df", "parent": "a07f80a"}]


def _v031_ancestor(ancestor: str, head: str) -> bool:
    return ancestor == "59888df" and head == "27746ed"


def test_saved_sbom_upload_uses_the_action_artifact(tmp_path, monkeypatch):
    recover = _recover()
    work = tmp_path / "no-git"
    work.mkdir()
    monkeypatch.chdir(work)
    calls: list[list[str]] = []

    def run(argv):
        calls.append(list(argv))
        if argv[:3] == ["gh", "run", "list"]:
            return _completed(
                argv,
                [
                    {
                        "databaseId": 42093909645,
                        "status": "completed",
                        "conclusion": "failure",
                        "headSha": "27746ed",
                    }
                ],
            )
        if argv[:3] == ["gh", "run", "view"]:
            return _completed(
                argv,
                {
                    "jobs": [
                        {"name": "Publish to PyPI", "conclusion": "success"},
                        {"name": "Release SBOM", "conclusion": "failure"},
                    ]
                },
            )
        if argv[:2] == ["gh", "api"]:
            return _completed(
                argv,
                {
                    "artifacts": [
                        {"name": "llm-guardrails-sbom.spdx.json", "expired": False},
                        {"name": "sdist", "expired": False},
                    ]
                },
            )
        if argv[:3] == ["gh", "run", "download"]:
            dest = Path(argv[argv.index("--dir") + 1])
            name = argv[argv.index("--name") + 1]
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["gh", "release", "upload"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)

    dest = work / "sbom-in"
    argv = recover.upload_saved_sbom(
        "v0.3.1",
        "melroyanthony/llm-guardrails",
        dest,
        run=run,
        tags=_V031_TAGS,
        is_ancestor=_v031_ancestor,
    )
    path = dest / "llm-guardrails-sbom.spdx.json"
    assert argv == [
        "gh",
        "release",
        "upload",
        "v0.3.1",
        str(path),
        "--repo",
        "melroyanthony/llm-guardrails",
        "--clobber",
    ]
    assert calls[3] == [
        "gh",
        "run",
        "download",
        "42093909645",
        "--repo",
        "melroyanthony/llm-guardrails",
        "--name",
        "llm-guardrails-sbom.spdx.json",
        "--dir",
        str(dest),
    ]
    assert path.is_file()
    assert not (work / ".git").exists()


def test_saved_sbom_missing_after_download_is_not_uploaded(tmp_path):
    recover = _recover()
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv[:3])
        if argv[:3] == ["gh", "run", "list"]:
            return _completed(
                argv,
                [
                    {
                        "databaseId": 42093909645,
                        "status": "completed",
                        "headSha": "27746ed",
                    }
                ],
            )
        if argv[:3] == ["gh", "run", "view"]:
            return _completed(
                argv,
                {
                    "jobs": [
                        {"name": "Publish to PyPI", "conclusion": "success"},
                        {"name": "Release SBOM", "conclusion": "failure"},
                    ]
                },
            )
        if argv[:2] == ["gh", "api"]:
            return _completed(
                argv,
                {"artifacts": [{"name": "llm-guardrails-sbom.spdx.json", "expired": False}]},
            )
        if argv[:3] == ["gh", "run", "download"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)

    try:
        recover.upload_saved_sbom(
            "v0.3.1",
            "melroyanthony/llm-guardrails",
            tmp_path / "sbom-in",
            run=run,
            tags=_V031_TAGS,
            is_ancestor=_v031_ancestor,
        )
    except SystemExit as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("missing SBOM was uploaded")
    assert ["gh", "release", "upload"] not in calls


def test_retries_keep_same_tag_publication_and_sbom(tmp_path):
    """A later skipped PyPI job must not rebuild, and v0.3.0's SBOM stays put."""
    recover = _recover()
    tags = [
        {"name": "v0.3.2", "sha": "t32", "parent": "p32"},
        {"name": "v0.3.1", "sha": "t31", "parent": "p31"},
        {"name": "v0.3.0", "sha": "t30", "parent": "p30"},
    ]
    ancestors = {
        ("t30", "p31"),
        ("t31", "retry-2"),
        ("t30", "retry-2"),
        ("t31", "retry-1"),
        ("t30", "retry-1"),
        ("t31", "published"),
        ("t30", "published"),
        ("t31", "p32"),
        ("t30", "p32"),
        ("t32", "later"),
        ("t31", "later"),
        ("t30", "later"),
        ("t30", "old"),
    }

    def is_ancestor(ancestor: str, head: str) -> bool:
        return (ancestor, head) in ancestors

    assert recover.assign_tag("p31", tags, is_ancestor) == "v0.3.1"
    assert recover.assign_tag("published", tags, is_ancestor) == "v0.3.1"
    assert recover.assign_tag("retry-2", tags, is_ancestor) == "v0.3.1"
    assert recover.assign_tag("p32", tags, is_ancestor) == "v0.3.2"
    assert recover.assign_tag("later", tags, is_ancestor) == "v0.3.2"
    assert recover.assign_tag("old", tags, is_ancestor) == "v0.3.0"

    jobs = {
        "3": [
            {"name": "Publish to PyPI", "conclusion": "skipped"},
            {"name": "Release SBOM", "conclusion": "failure"},
        ],
        "2": [
            {"name": "Publish to PyPI", "conclusion": "skipped"},
            {"name": "Release SBOM", "conclusion": "failure"},
        ],
        "10": [
            {"name": "Publish to PyPI", "conclusion": "success"},
            {"name": "Release SBOM", "conclusion": "failure"},
        ],
        "42093909645": [
            {"name": "Publish to PyPI", "conclusion": "success"},
            {"name": "Release SBOM", "conclusion": "failure"},
        ],
    }
    artifacts = {
        "3": [],
        "2": [],
        "10": [{"name": "ferroguard.spdx.json", "expired": False}],
        "42093909645": [{"name": "llm-guardrails-sbom.spdx.json", "expired": False}],
    }
    listed = [
        {"databaseId": 3, "status": "completed", "headSha": "retry-2", "conclusion": "failure"},
        {"databaseId": 2, "status": "completed", "headSha": "retry-1", "conclusion": "failure"},
        {"databaseId": 10, "status": "completed", "headSha": "old", "conclusion": "failure"},
        {
            "databaseId": 42093909645,
            "status": "completed",
            "headSha": "published",
            "conclusion": "failure",
        },
    ]
    calls: list[list[str]] = []

    def run(argv):
        calls.append(list(argv))
        if argv[:3] == ["gh", "run", "list"]:
            assert "headSha" in argv[argv.index("--json") + 1]
            assert "100" in argv
            return _completed(argv, listed)
        if argv[:3] == ["gh", "run", "view"]:
            return _completed(argv, {"jobs": jobs[argv[3]]})
        if argv[:2] == ["gh", "api"]:
            run_id = argv[2].rstrip("/").split("/")[-2]
            return _completed(argv, {"artifacts": artifacts[run_id]})
        if argv[:3] == ["gh", "run", "download"]:
            dest = Path(argv[argv.index("--dir") + 1])
            name = argv[argv.index("--name") + 1]
            dest.mkdir(parents=True, exist_ok=True)
            (dest / name).write_text("{}\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:3] == ["gh", "release", "upload"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(argv)

    assert recover.publish_succeeded(
        "melroyanthony/llm-guardrails",
        "v0.3.1",
        run=run,
        tags=tags,
        is_ancestor=is_ancestor,
    )
    calls.clear()
    dest = tmp_path / "sbom-in"
    argv = recover.upload_saved_sbom(
        "v0.3.1",
        "melroyanthony/llm-guardrails",
        dest,
        run=run,
        tags=tags,
        is_ancestor=is_ancestor,
    )
    path = dest / "llm-guardrails-sbom.spdx.json"
    assert argv == [
        "gh",
        "release",
        "upload",
        "v0.3.1",
        str(path),
        "--repo",
        "melroyanthony/llm-guardrails",
        "--clobber",
    ]
    download = next(call for call in calls if call[:3] == ["gh", "run", "download"])
    assert download[3] == "42093909645"
    assert "ferroguard.spdx.json" not in download
    assert path.is_file()
    assert not (tmp_path / ".git").exists()

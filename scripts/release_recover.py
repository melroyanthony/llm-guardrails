#!/usr/bin/env python3
"""Reuse an unfinished tag without creating another one.

The release job creates the tag before the wheels are published. If those
jobs fail, the tag is already immutable. This script selects that tag again.
When the wheels are already on PyPI and the SBOM was not attached, it selects
SBOM-only recovery: no new tag, no wheel rebuild, and no second publish.

It does not create, move, or delete a tag, and it does not push.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from release_subject import RELEASE_SUBJECT, ROOT, strip_emoji

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SBOM_NAMES = ("ferroguard.spdx.json", "llm-guardrails-sbom.spdx.json")
DEFAULT_REPO = "melroyanthony/llm-guardrails"


def release_version(subject: str) -> str | None:
    """Return the version from a release commit subject, if it is one."""
    text = strip_emoji(subject).splitlines()[0].strip() if subject else ""
    match = RELEASE_SUBJECT.match(text)
    return match.group(1) if match else None


def plan(
    tag: str,
    subject: str,
    release_exists: bool,
    asset_count: int,
    *,
    pypi_succeeded: bool = False,
) -> dict:
    """Return sbom, recover, or continue for one tag.

    An unfinished release is an existing ``vX.Y.Z`` tag whose commit is the
    matching release commit, whose GitHub Release exists, and which has no
    assets yet. SBOM-only recovery applies when PyPI already succeeded.
    Otherwise the wheels are built again. Any asset means this tag is done.
    """
    match = TAG_RE.fullmatch(tag.strip())
    version = release_version(subject)
    if match and version == match.group(1) and release_exists and asset_count == 0:
        if pypi_succeeded:
            return {"action": "sbom", "tag": tag.strip()}
        return {"action": "recover", "tag": tag.strip()}
    return {"action": "continue", "tag": ""}


def workflow_mode(action: str) -> str:
    """Map a recover action to the workflow mode that gates the later jobs."""
    if action == "sbom":
        return "sbom"
    if action == "recover":
        return "wheels"
    raise SystemExit(f"refusing action {action}")


def choose_sbom_name(names: list[str]) -> str:
    """Prefer the current artifact name, then the name the failed run stored."""
    for candidate in SBOM_NAMES:
        if candidate in names:
            return candidate
    return ""


def job_conclusion(jobs: list[dict], name: str) -> str:
    for job in jobs:
        if job.get("name") == name:
            return str(job.get("conclusion") or "")
    return ""


def select_saved_sbom(runs: list[dict]) -> dict[str, str]:
    """Pick the newest completed run whose PyPI job succeeded and SBOM did not.

    ``runs`` is newest first. Each item has ``databaseId``, ``status``,
    ``jobs``, and ``artifact_names``.
    """
    for run in runs:
        if run.get("status") != "completed":
            continue
        jobs = list(run.get("jobs") or [])
        if job_conclusion(jobs, "Publish to PyPI") != "success":
            continue
        if job_conclusion(jobs, "Release SBOM") == "success":
            continue
        name = choose_sbom_name(list(run.get("artifact_names") or []))
        if not name:
            continue
        return {"run_id": str(run["databaseId"]), "name": name}
    raise SystemExit("no saved SBOM artifact")


def repo_name(explicit: str = "") -> str:
    repo = explicit or os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY") or ""
    repo = repo or DEFAULT_REPO
    if not REPO_RE.fullmatch(repo):
        raise SystemExit(f"refusing repository {repo}")
    return repo


def upload_argv(tag: str, path: Path, repo: str) -> list[str]:
    """The exact ``gh release upload`` invocation. It does not need a checkout."""
    if not TAG_RE.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    if not REPO_RE.fullmatch(repo):
        raise SystemExit(f"refusing repository {repo}")
    file_path = Path(path)
    if file_path.name not in SBOM_NAMES:
        raise SystemExit(f"refusing SBOM name {file_path.name}")
    if not file_path.is_file():
        raise SystemExit(f"SBOM file not found: {file_path}")
    return [
        "gh",
        "release",
        "upload",
        tag,
        str(file_path),
        "--repo",
        repo,
        "--clobber",
    ]


def upload_release_asset(tag: str, path: Path, repo: str, run=None) -> list[str]:
    argv = upload_argv(tag, path, repo)
    result = (run or _run)(argv)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "gh release upload failed").strip())
    return argv


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, check=False, capture_output=True, text=True)


def _json(run, argv: list[str]):
    result = run(argv)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "gh failed").strip()
        raise SystemExit(detail)
    return json.loads(result.stdout)


def locate_sbom(repo: str, run=None) -> dict[str, str]:
    """Find the saved SBOM artifact. Read-only; does not upload or publish."""
    repo = repo_name(repo)
    runner = run or _run
    listed = _json(
        runner,
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            "release.yml",
            "--limit",
            "15",
            "--json",
            "databaseId,status,conclusion",
        ],
    )
    discovered: list[dict] = []
    for item in listed:
        if item.get("status") != "completed":
            continue
        run_id = str(item["databaseId"])
        viewed = _json(
            runner,
            ["gh", "run", "view", run_id, "--repo", repo, "--json", "jobs"],
        )
        artifacts = _json(
            runner,
            ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/artifacts"],
        )
        names = [
            artifact["name"]
            for artifact in artifacts.get("artifacts") or []
            if not artifact.get("expired")
        ]
        discovered.append(
            {
                "databaseId": item["databaseId"],
                "status": item["status"],
                "jobs": viewed.get("jobs") or [],
                "artifact_names": names,
            }
        )
    return select_saved_sbom(discovered)


def download_sbom(repo: str, found: dict[str, str], dest: Path, run=None) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    argv = [
        "gh",
        "run",
        "download",
        found["run_id"],
        "--repo",
        repo,
        "--name",
        found["name"],
        "--dir",
        str(dest),
    ]
    result = (run or _run)(argv)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "gh run download failed").strip())
    path = dest / found["name"]
    if not path.is_file():
        raise SystemExit(f"SBOM file not found: {path}")
    return path


def upload_saved_sbom(tag: str, repo: str, dest: Path, run=None) -> list[str]:
    repo = repo_name(repo)
    found = locate_sbom(repo, run=run)
    path = download_sbom(repo, found, dest, run=run)
    return upload_release_asset(tag, path, repo, run=run)


def _fetch() -> None:
    result = _run(["git", "fetch", "origin", "main"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git fetch origin main failed")
    result = _run(["git", "fetch", "origin", "refs/tags/v*:refs/tags/v*"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git fetch tags failed")


def latest_tag() -> str:
    """Highest existing ``vX.Y.Z`` tag. Empty when there is none."""
    result = _run(["git", "tag", "-l", "v[0-9]*", "--sort=-v:refname"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "listing version tags failed")
    for line in result.stdout.splitlines():
        tag = line.strip()
        if TAG_RE.fullmatch(tag):
            return tag
    return ""


def _subject(tag: str) -> str:
    result = _run(["git", "log", "-1", "--format=%s", f"{tag}^{{}}"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"cannot read {tag}")
    return result.stdout.strip()


def _on_main(tag: str) -> bool:
    result = _run(["git", "merge-base", "--is-ancestor", f"{tag}^{{}}", "origin/main"])
    return result.returncode == 0


def _assets(tag: str) -> tuple[bool, int]:
    result = _run(["gh", "release", "view", tag, "--repo", repo_name(), "--json", "assets"])
    if result.returncode == 0:
        payload = json.loads(result.stdout)
        assets = payload.get("assets") or []
        return True, len(assets)
    detail = f"{result.stderr}\n{result.stdout}".lower()
    if "not found" in detail:
        return False, 0
    raise SystemExit(result.stderr.strip() or f"gh release view {tag} failed")


def publish_succeeded(repo: str, run=None) -> bool:
    """True when the newest completed Release run published to PyPI.

    A lookup failure aborts. It does not fall through to a new tag.
    """
    repo = repo_name(repo)
    runner = run or _run
    listed = _json(
        runner,
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            "release.yml",
            "--limit",
            "15",
            "--json",
            "databaseId,status,conclusion",
        ],
    )
    for item in listed:
        if item.get("status") != "completed":
            continue
        viewed = _json(
            runner,
            ["gh", "run", "view", str(item["databaseId"]), "--repo", repo, "--json", "jobs"],
        )
        return job_conclusion(viewed.get("jobs") or [], "Publish to PyPI") == "success"
    return False


def resolve(requested: str | None = None, expect: str | None = None) -> dict:
    """Select the latest unfinished tag, or continue with a new release.

    ``requested`` is the workflow-dispatch input. It must be that same tag.
    ``expect`` is ``sbom`` or ``wheels`` and must match the decision.
    """
    if expect not in {None, "", "sbom", "wheels"}:
        raise SystemExit(f"refusing mode {expect}")
    _fetch()
    tag = latest_tag()
    if requested:
        if not TAG_RE.fullmatch(requested):
            raise SystemExit(f"refusing {requested}; expected vX.Y.Z")
        if requested != tag:
            raise SystemExit(f"refusing {requested}; the latest tag is {tag or 'missing'}")
    if not tag or not _on_main(tag):
        if requested:
            raise SystemExit(f"refusing {requested}; it is not on origin/main")
        return {"action": "continue", "tag": ""}
    exists, count = _assets(tag)
    pypi_succeeded = publish_succeeded(repo_name()) if exists and count == 0 else False
    decision = plan(tag, _subject(tag), exists, count, pypi_succeeded=pypi_succeeded)
    if requested and decision["action"] not in {"recover", "sbom"}:
        raise SystemExit(f"refusing {requested}; it is not an unfinished release")
    if expect == "sbom" and decision["action"] != "sbom":
        raise SystemExit(
            f"refusing sbom-only recovery of {tag}; this tag needs {decision['action']}"
        )
    if expect == "wheels" and decision["action"] != "recover":
        raise SystemExit(
            f"refusing a wheel rebuild of {tag}; this tag needs {decision['action']}"
        )
    return decision


def self_test() -> None:
    """Check the decision table and the upload command. Does not fetch or upload."""
    subject = "🔖 chore(release): v0.3.1"
    recover = plan("v0.3.1", subject, True, 0)
    if recover != {"action": "recover", "tag": "v0.3.1"}:
        raise SystemExit(f"unfinished v0.3.1 was not reused: {recover}")
    sbom = plan("v0.3.1", subject, True, 0, pypi_succeeded=True)
    if sbom != {"action": "sbom", "tag": "v0.3.1"}:
        raise SystemExit(f"published v0.3.1 was not SBOM-only: {sbom}")
    if workflow_mode("sbom") != "sbom" or workflow_mode("recover") != "wheels":
        raise SystemExit("workflow mode mapping changed")
    if plan("v0.3.1", subject, True, 1, pypi_succeeded=True)["action"] != "continue":
        raise SystemExit("a release with assets was reused")
    if plan("v0.3.1", subject, False, 0, pypi_succeeded=True)["action"] != "continue":
        raise SystemExit("a missing GitHub Release was reused")
    if plan("v0.3.1", "🔖 chore(release): v0.3.2", True, 0)["action"] != "continue":
        raise SystemExit("a mismatched release commit was reused")
    if plan("not-a-tag", subject, True, 0)["action"] != "continue":
        raise SystemExit("a non-version tag was reused")
    saved = select_saved_sbom(
        [
            {
                "databaseId": 9,
                "status": "completed",
                "jobs": [
                    {"name": "Publish to PyPI", "conclusion": "success"},
                    {"name": "Release SBOM", "conclusion": "success"},
                ],
                "artifact_names": ["ferroguard.spdx.json"],
            },
            {
                "databaseId": 42093909645,
                "status": "completed",
                "jobs": [
                    {"name": "Publish to PyPI", "conclusion": "success"},
                    {"name": "Release SBOM", "conclusion": "failure"},
                ],
                "artifact_names": ["llm-guardrails-sbom.spdx.json", "sdist"],
            },
        ]
    )
    if saved != {"run_id": "42093909645", "name": "llm-guardrails-sbom.spdx.json"}:
        raise SystemExit(f"saved SBOM was not the failed run: {saved}")
    preferred = select_saved_sbom(
        [
            {
                "databaseId": 1,
                "status": "completed",
                "jobs": [
                    {"name": "Publish to PyPI", "conclusion": "success"},
                    {"name": "Release SBOM", "conclusion": "failure"},
                ],
                "artifact_names": [
                    "llm-guardrails-sbom.spdx.json",
                    "ferroguard.spdx.json",
                ],
            }
        ]
    )
    if preferred["name"] != "ferroguard.spdx.json":
        raise SystemExit(f"current SBOM name was not preferred: {preferred}")
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        path = directory / "llm-guardrails-sbom.spdx.json"
        path.write_text("{}\n", encoding="utf-8")
        seen: list[list[str]] = []

        def fake(argv: list[str]) -> subprocess.CompletedProcess[str]:
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        argv = upload_release_asset("v0.3.1", path, DEFAULT_REPO, run=fake)
        expected = [
            "gh",
            "release",
            "upload",
            "v0.3.1",
            str(path),
            "--repo",
            DEFAULT_REPO,
            "--clobber",
        ]
        if argv != expected or seen != [expected]:
            raise SystemExit(f"upload invocation changed: {argv}")
        try:
            upload_release_asset("v0.3.1", directory / "ferroguard.spdx.json", DEFAULT_REPO, run=fake)
        except SystemExit as exc:
            if "not found" not in str(exc):
                raise
        else:
            raise SystemExit("missing SBOM was uploaded")
        if seen != [expected]:
            raise SystemExit("missing SBOM called gh")
    source = Path(__file__).read_text(encoding="utf-8")
    if "git " + "push" in source or "git " + "tag" in source:
        raise SystemExit("recovery script contains a tag or push command")
    print("release_recover.py self-test ok")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--resolve", action="store_true")
    parser.add_argument("--tag", default="")
    parser.add_argument("--expect", default="")
    parser.add_argument("--mode-for", default="")
    parser.add_argument("--upload-sbom", action="store_true")
    parser.add_argument("--upload-saved-sbom", action="store_true")
    parser.add_argument("--file", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--dest", default="sbom-in")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.mode_for:
        sys.stdout.write(workflow_mode(args.mode_for) + "\n")
        return
    if args.upload_sbom:
        upload_release_asset(args.tag, Path(args.file), repo_name(args.repo))
        return
    if args.upload_saved_sbom:
        upload_saved_sbom(args.tag, repo_name(args.repo), Path(args.dest))
        return
    if args.resolve or args.tag:
        json.dump(resolve(args.tag or None, args.expect or None), sys.stdout)
        sys.stdout.write("\n")
        return
    parser.error("pass --self-test, --resolve, --upload-sbom, or --upload-saved-sbom")


if __name__ == "__main__":
    main()

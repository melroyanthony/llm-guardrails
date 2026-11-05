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

from release_sbom import assert_release_sbom, replacement_needed, version_of
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
    sbom_acceptable: bool = True,
) -> dict:
    """Return sbom, recover, or continue for one tag.

    An unfinished release is an existing ``vX.Y.Z`` tag whose commit is the
    matching release commit and whose GitHub Release exists. SBOM-only
    recovery applies when PyPI already succeeded and the release has no
    acceptable SBOM, including when the only asset is a directory-only scan.
    That path does not build wheels. A release with an acceptable SBOM is done.
    """
    match = TAG_RE.fullmatch(tag.strip())
    version = release_version(subject)
    if match and version == match.group(1) and release_exists:
        replace_sbom = asset_count == 0 or not sbom_acceptable
        if replace_sbom and pypi_succeeded:
            return {"action": "sbom", "tag": tag.strip()}
        if asset_count == 0:
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


def assign_tag(head_sha: str, tags: list[dict], is_ancestor) -> str:
    """Return the release tag a workflow run published.

    ``tags`` is newest version first. Each item has ``name``, ``sha``, and
    ``parent`` (the commit the tag points at, and that commit's parent).
    A run whose head is the parent of a tag created that tag. Otherwise the
    run belongs to the newest tag that is an ancestor of its head. A newer
    tag therefore keeps an older release's runs off this tag.
    """
    if not head_sha:
        return ""
    for tag in tags:
        if tag.get("parent") and tag["parent"] == head_sha:
            return str(tag["name"])
    for tag in tags:
        sha = str(tag.get("sha") or "")
        if sha and is_ancestor(sha, head_sha):
            return str(tag["name"])
    return ""


def pypi_succeeded_for_tag(runs: list[dict], tag: str) -> bool:
    """True when any completed run for ``tag`` published to PyPI.

    A later SBOM-only retry skips PyPI. That skip does not erase an earlier
    success for the same tag, and a success for another tag does not count.
    """
    if not TAG_RE.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    for run in runs:
        if run.get("status") != "completed" or run.get("tag") != tag:
            continue
        if job_conclusion(list(run.get("jobs") or []), "Publish to PyPI") == "success":
            return True
    return False


def select_saved_sbom(runs: list[dict], tag: str) -> dict[str, str]:
    """Pick the newest saved SBOM for ``tag``.

    ``runs`` is newest first. Each item has ``databaseId``, ``status``,
    ``tag``, ``jobs``, and ``artifact_names``. Runs for other tags are
    ignored, including when their artifact is newer than this tag's file.
    """
    if not TAG_RE.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    for run in runs:
        if run.get("status") != "completed" or run.get("tag") != tag:
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
    raise SystemExit(f"no saved SBOM artifact for {tag}")


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
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_release_sbom(document, version_of(tag))
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


def discover_release_runs(
    repo: str,
    runner,
    tags: list[dict],
    is_ancestor,
    *,
    with_artifacts: bool,
) -> list[dict]:
    """Load completed Release runs, newest first, each bound to one tag.

    A lookup failure aborts. It does not fall through to a new tag.
    """
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
            "100",
            "--json",
            "databaseId,status,conclusion,headSha",
        ],
    )
    discovered: list[dict] = []
    for item in listed:
        if item.get("status") != "completed":
            continue
        head = str(item.get("headSha") or "")
        run_id = str(item["databaseId"])
        viewed = _json(
            runner,
            ["gh", "run", "view", run_id, "--repo", repo, "--json", "jobs"],
        )
        names: list[str] = []
        if with_artifacts:
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
                "headSha": head,
                "tag": assign_tag(head, tags, is_ancestor),
                "jobs": viewed.get("jobs") or [],
                "artifact_names": names,
            }
        )
    return discovered


def locate_sbom(repo: str, tag: str, run=None, tags=None, is_ancestor=None) -> dict[str, str]:
    """Find the saved SBOM for ``tag``. Read-only; does not upload or publish."""
    if not TAG_RE.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    repo = repo_name(repo)
    runner = run or _run
    if tags is None:
        _fetch()
        tags = version_tags()
    ancestor = _is_ancestor if is_ancestor is None else is_ancestor
    discovered = discover_release_runs(
        repo,
        runner,
        tags,
        ancestor,
        with_artifacts=True,
    )
    return select_saved_sbom(discovered, tag)


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


def upload_saved_sbom(
    tag: str,
    repo: str,
    dest: Path,
    run=None,
    tags=None,
    is_ancestor=None,
) -> list[str]:
    repo = repo_name(repo)
    found = locate_sbom(repo, tag, run=run, tags=tags, is_ancestor=is_ancestor)
    path = download_sbom(repo, found, dest, run=run)
    return upload_release_asset(tag, path, repo, run=run)


def _fetch() -> None:
    result = _run(["git", "fetch", "origin", "main"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git fetch origin main failed")
    result = _run(["git", "fetch", "origin", "refs/tags/v*:refs/tags/v*"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "git fetch tags failed")


def _parent(commit: str) -> str:
    result = _run(["git", "rev-parse", f"{commit}^"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def version_tags() -> list[dict]:
    """Version tags newest first, each with its commit and that commit's parent."""
    result = _run(
        [
            "git",
            "for-each-ref",
            "--sort=-v:refname",
            "--format=%(refname:short) %(objectname) %(*objectname)",
            "refs/tags/v*",
        ]
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "listing version tags failed")
    tags: list[dict] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts or not TAG_RE.fullmatch(parts[0]):
            continue
        commit = parts[2] if len(parts) > 2 and parts[2] else parts[1]
        tags.append({"name": parts[0], "sha": commit, "parent": _parent(commit)})
    return tags


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    if not ancestor or not descendant:
        return False
    result = _run(["git", "merge-base", "--is-ancestor", ancestor, descendant])
    return result.returncode == 0


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


def load_release_documents(tag: str, repo: str, run=None) -> list[dict]:
    """Download attached SPDX assets. Read-only."""
    repo = repo_name(repo)
    runner = run or _run
    payload = _json(runner, ["gh", "release", "view", tag, "--repo", repo, "--json", "assets"])
    names = [
        asset.get("name") or ""
        for asset in payload.get("assets") or []
        if (asset.get("name") or "").endswith(".spdx.json")
    ]
    if not names:
        return []
    with tempfile.TemporaryDirectory() as raw:
        dest = Path(raw)
        result = runner(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repo,
                "--dir",
                str(dest),
                "--pattern",
                "*.spdx.json",
                "--clobber",
            ]
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "gh release download failed").strip()
            raise SystemExit(detail)
        documents = []
        for name in names:
            path = dest / name
            if not path.is_file():
                raise SystemExit(f"SBOM asset was not downloaded: {name}")
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        return documents


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


def publish_succeeded(repo: str, tag: str, run=None, tags=None, is_ancestor=None) -> bool:
    """True when a completed Release run for ``tag`` published to PyPI.

    The newest run is not enough: an SBOM-only retry skips PyPI. A lookup
    failure aborts. It does not fall through to a new tag.
    """
    if not TAG_RE.fullmatch(tag):
        raise SystemExit(f"refusing {tag}; expected vX.Y.Z")
    repo = repo_name(repo)
    runner = run or _run
    if tags is None:
        tags = version_tags()
    ancestor = _is_ancestor if is_ancestor is None else is_ancestor
    discovered = discover_release_runs(
        repo,
        runner,
        tags,
        ancestor,
        with_artifacts=False,
    )
    return pypi_succeeded_for_tag(discovered, tag)


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
    acceptable = True
    if exists and count and tag:
        version = version_of(tag)
        acceptable = not replacement_needed(load_release_documents(tag, repo_name()), version)
    pypi_succeeded = False
    if exists and (count == 0 or not acceptable):
        pypi_succeeded = publish_succeeded(repo_name(), tag)
    decision = plan(
        tag,
        _subject(tag),
        exists,
        count,
        pypi_succeeded=pypi_succeeded,
        sbom_acceptable=acceptable,
    )
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
        raise SystemExit("a release with a good SBOM was replaced")
    replaced = plan("v0.3.1", subject, True, 1, pypi_succeeded=True, sbom_acceptable=False)
    if replaced != {"action": "sbom", "tag": "v0.3.1"}:
        raise SystemExit(f"a directory-only SBOM was left in place: {replaced}")
    if plan("v0.3.1", subject, False, 0, pypi_succeeded=True)["action"] != "continue":
        raise SystemExit("a missing GitHub Release was reused")
    if plan("v0.3.1", "🔖 chore(release): v0.3.2", True, 0)["action"] != "continue":
        raise SystemExit("a mismatched release commit was reused")
    if plan("not-a-tag", subject, True, 0)["action"] != "continue":
        raise SystemExit("a non-version tag was reused")
    history = [
        {
            "databaseId": 51,
            "status": "completed",
            "tag": "v0.3.1",
            "jobs": [
                {"name": "Publish to PyPI", "conclusion": "skipped"},
                {"name": "Release SBOM", "conclusion": "failure"},
            ],
            "artifact_names": [],
        },
        {
            "databaseId": 50,
            "status": "completed",
            "tag": "v0.3.1",
            "jobs": [
                {"name": "Publish to PyPI", "conclusion": "skipped"},
                {"name": "Release SBOM", "conclusion": "failure"},
            ],
            "artifact_names": [],
        },
        {
            "databaseId": 10,
            "status": "completed",
            "tag": "v0.3.0",
            "jobs": [
                {"name": "Publish to PyPI", "conclusion": "success"},
                {"name": "Release SBOM", "conclusion": "failure"},
            ],
            "artifact_names": ["ferroguard.spdx.json"],
        },
        {
            "databaseId": 9,
            "status": "completed",
            "tag": "v0.3.1",
            "jobs": [
                {"name": "Publish to PyPI", "conclusion": "success"},
                {"name": "Release SBOM", "conclusion": "success"},
            ],
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
            "artifact_names": ["llm-guardrails-sbom.spdx.json", "sdist"],
        },
    ]
    if not pypi_succeeded_for_tag(history, "v0.3.1"):
        raise SystemExit("a skipped SBOM retry erased the PyPI success")
    skipped_only = [run for run in history if run["databaseId"] in {51, 50, 10}]
    if pypi_succeeded_for_tag(skipped_only, "v0.3.1"):
        raise SystemExit("skipped retries or another tag counted as publication")
    saved = select_saved_sbom(history, "v0.3.1")
    if saved != {"run_id": "42093909645", "name": "llm-guardrails-sbom.spdx.json"}:
        raise SystemExit(f"saved SBOM was not the failed run: {saved}")
    if select_saved_sbom(history, "v0.3.0")["run_id"] != "10":
        raise SystemExit("an older release SBOM was mixed with v0.3.1")
    tags = [
        {"name": "v0.3.2", "sha": "t32", "parent": "p32"},
        {"name": "v0.3.1", "sha": "t31", "parent": "p31"},
        {"name": "v0.3.0", "sha": "t30", "parent": "p30"},
    ]
    ancestors = {
        ("t30", "p31"),
        ("t31", "mid"),
        ("t30", "mid"),
        ("t31", "p32"),
        ("t30", "p32"),
        ("t32", "later"),
        ("t31", "later"),
        ("t30", "later"),
        ("t30", "old"),
    }

    def is_ancestor(ancestor: str, descendant: str) -> bool:
        return (ancestor, descendant) in ancestors

    if assign_tag("p31", tags, is_ancestor) != "v0.3.1":
        raise SystemExit("the run that created v0.3.1 was given another tag")
    if assign_tag("mid", tags, is_ancestor) != "v0.3.1":
        raise SystemExit("a v0.3.1 retry was given another tag")
    if assign_tag("p32", tags, is_ancestor) != "v0.3.2":
        raise SystemExit("the run that created v0.3.2 stayed on v0.3.1")
    if assign_tag("later", tags, is_ancestor) != "v0.3.2":
        raise SystemExit("a newer tag did not hide the older release")
    if assign_tag("old", tags, is_ancestor) != "v0.3.0":
        raise SystemExit("an older release was pulled onto v0.3.1")
    preferred = select_saved_sbom(
        [
            {
                "databaseId": 1,
                "status": "completed",
                "tag": "v0.3.1",
                "jobs": [
                    {"name": "Publish to PyPI", "conclusion": "success"},
                    {"name": "Release SBOM", "conclusion": "failure"},
                ],
                "artifact_names": [
                    "llm-guardrails-sbom.spdx.json",
                    "ferroguard.spdx.json",
                ],
            }
        ],
        "v0.3.1",
    )
    if preferred["name"] != "ferroguard.spdx.json":
        raise SystemExit(f"current SBOM name was not preferred: {preferred}")
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        from release_sbom import build_release_sbom

        path = directory / "ferroguard.spdx.json"
        document = build_release_sbom(
            "0.3.1",
            ["pydantic>=2.0,<3.0"],
            [{"filename": "ferroguard-0.3.1.tar.gz", "sha256": "a" * 64}],
            "2026-11-05T00:00:00Z",
        )
        path.write_text(json.dumps(document), encoding="utf-8")
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
            upload_release_asset(
                "v0.3.1",
                directory / "llm-guardrails-sbom.spdx.json",
                DEFAULT_REPO,
                run=fake,
            )
        except SystemExit as exc:
            if "not found" not in str(exc):
                raise
        else:
            raise SystemExit("missing SBOM was uploaded")
        empty = directory / "ferroguard.spdx.json"
        empty.write_text(
            json.dumps(
                {
                    "name": "dist",
                    "packages": [{"name": "dist", "versionInfo": None, "filesAnalyzed": False}],
                }
            ),
            encoding="utf-8",
        )
        try:
            upload_release_asset("v0.3.1", empty, DEFAULT_REPO, run=fake)
        except SystemExit as exc:
            if "directory-only" not in str(exc):
                raise
        else:
            raise SystemExit("directory-only SBOM was uploaded")
        if seen != [expected]:
            raise SystemExit("rejected SBOM called gh")
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

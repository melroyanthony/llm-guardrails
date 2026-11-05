#!/usr/bin/env python3
"""Republish an existing tag when its GitHub Release has no assets.

The release job creates the tag before the wheels are published. If those
jobs fail, the tag is already immutable. This script selects that tag again.
It does not create, move, or delete a tag, and it does not push.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from release_subject import RELEASE_SUBJECT, ROOT, strip_emoji

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def release_version(subject: str) -> str | None:
    """Return the version from a release commit subject, if it is one."""
    text = strip_emoji(subject).splitlines()[0].strip() if subject else ""
    match = RELEASE_SUBJECT.match(text)
    return match.group(1) if match else None


def plan(tag: str, subject: str, release_exists: bool, asset_count: int) -> dict:
    """Return recover for an unfinished release, otherwise continue.

    An unfinished release is an existing ``vX.Y.Z`` tag whose commit is the
    matching release commit, whose GitHub Release exists, and which has no
    assets yet. Any asset means the publish path already finished.
    """
    match = TAG_RE.fullmatch(tag.strip())
    version = release_version(subject)
    if match and version == match.group(1) and release_exists and asset_count == 0:
        return {"action": "recover", "tag": tag.strip()}
    return {"action": "continue", "tag": ""}


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, check=False, capture_output=True, text=True)


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
    result = _run(["gh", "release", "view", tag, "--json", "assets"])
    if result.returncode == 0:
        payload = json.loads(result.stdout)
        assets = payload.get("assets") or []
        return True, len(assets)
    detail = f"{result.stderr}\n{result.stdout}".lower()
    if "not found" in detail:
        return False, 0
    raise SystemExit(result.stderr.strip() or f"gh release view {tag} failed")


def resolve(requested: str | None = None) -> dict:
    """Select the latest unfinished tag, or continue with a new release.

    ``requested`` is the workflow-dispatch input. It must be that same tag.
    """
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
    decision = plan(tag, _subject(tag), *_assets(tag))
    if requested and decision["action"] != "recover":
        raise SystemExit(f"refusing {requested}; it is not an unfinished release")
    return decision


def self_test() -> None:
    """Check the decision table. Does not fetch, tag, or push."""
    subject = "🔖 chore(release): v0.3.1"
    recover = plan("v0.3.1", subject, True, 0)
    if recover != {"action": "recover", "tag": "v0.3.1"}:
        raise SystemExit(f"unfinished v0.3.1 was not reused: {recover}")
    if plan("v0.3.1", subject, True, 1)["action"] != "continue":
        raise SystemExit("a release with assets was reused")
    if plan("v0.3.1", subject, False, 0)["action"] != "continue":
        raise SystemExit("a missing GitHub Release was reused")
    if plan("v0.3.1", "🔖 chore(release): v0.3.2", True, 0)["action"] != "continue":
        raise SystemExit("a mismatched release commit was reused")
    if plan("not-a-tag", subject, True, 0)["action"] != "continue":
        raise SystemExit("a non-version tag was reused")
    source = Path(__file__).read_text(encoding="utf-8")
    if "git " + "push" in source or "git " + "tag" in source:
        raise SystemExit("recovery script contains a tag or push command")
    print("release_recover.py self-test ok")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--resolve", action="store_true")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.resolve or args.tag:
        json.dump(resolve(args.tag or None), sys.stdout)
        sys.stdout.write("\n")
        return
    parser.error("pass --self-test or --resolve")


if __name__ == "__main__":
    main()

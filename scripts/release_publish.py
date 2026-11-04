#!/usr/bin/env python3
"""Commit a release on main, push it, and publish the tag.

The workflow passes ``GH_TOKEN`` (``GITHUB_TOKEN``). The release commit is
authored as ``github-actions[bot]``. A non-fast-forward push is retried by
rebuilding the commit on ``origin/main``. This script never force-pushes.
This script does not upload to PyPI. The release workflow builds the
wheels from the tag this script pushes and publishes those.

Re-running against a version that is already the tip of ``main``, or already
tagged, does not create a second commit, tag, or GitHub Release.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from release_subject import (
    RELEASE_SUBJECT,
    ROOT,
    _subject_of,
    classify_tip,
    decide_unreleased,
    prepend_changes,
    push_commands,
)

VERSION_PATH = ROOT / ".version"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
BOT_NAME = "github-actions[bot]"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"


def _run(argv: list[str], dry_run: bool, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(argv), flush=True)
    if not dry_run:
        subprocess.run(argv, cwd=ROOT, check=True, env=env)


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = BOT_NAME
    env["GIT_AUTHOR_EMAIL"] = BOT_EMAIL
    env["GIT_COMMITTER_NAME"] = BOT_NAME
    env["GIT_COMMITTER_EMAIL"] = BOT_EMAIL
    return env


def _read_decision(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.loads(sys.stdin.read())


def _output(argv: list[str]) -> str:
    return subprocess.check_output(argv, cwd=ROOT, text=True).strip()


def _tip_subject(rev: str) -> str:
    message = subprocess.check_output(["git", "log", "-1", "--format=%B", rev], cwd=ROOT, text=True)
    return _subject_of(message, None)


def _is_this_release(rev: str, version: str) -> bool:
    match = RELEASE_SUBJECT.match(_tip_subject(rev))
    return bool(match and match.group(1) == version)


def _push_rejected(text: str) -> bool:
    """True when a push failed because the remote moved, not because of auth."""
    lowered = text.lower()
    return (
        "non-fast-forward" in lowered
        or "[rejected]" in lowered
        or "failed to push some refs" in lowered
        or "updates were rejected" in lowered
    )


def _tag_exists(tag: str) -> bool:
    local = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if local.returncode == 0:
        return True
    remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return remote.returncode == 0 and bool(remote.stdout.strip())


def _release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", tag],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _changes(decision: dict) -> list[dict[str, str]]:
    changes = decision.get("changes")
    if isinstance(changes, list) and changes:
        return changes
    return [{"section": decision["section"], "subject": decision["subject"]}]


def _set_cargo_package_version(text: str, version: str) -> str:
    """Replace the ``[package]`` version and leave dependency versions alone."""
    updated, count = re.subn(
        r'(?m)^version = "[^"]+"',
        f'version = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("Cargo.toml has no package version")
    return updated


def _set_lock_package_version(text: str, package: str, version: str) -> str:
    """Replace one lockfile package's version line, matched by name."""
    pattern = re.compile(rf'(name = "{re.escape(package)}"\nversion = ")[^"]+(")')
    updated, count = pattern.subn(rf"\g<1>{version}\2", text, count=1)
    if count != 1:
        raise SystemExit(f"{package} version was not found in the lockfile")
    return updated


def write_package_versions(root: Path, version: str) -> None:
    """Keep Cargo.toml and the root Cargo.lock entry aligned with ``version``.

    ``pyproject.toml`` declares ``dynamic = ["version"]``. Maturin reads the
    version from Cargo.toml, so that file is the only package version.
    """
    cargo = root / "Cargo.toml"
    cargo.write_text(
        _set_cargo_package_version(cargo.read_text(encoding="utf-8"), version),
        encoding="utf-8",
    )
    lock = root / "Cargo.lock"
    if lock.is_file():
        lock.write_text(
            _set_lock_package_version(
                lock.read_text(encoding="utf-8"),
                "llm-guardrails-core",
                version,
            ),
            encoding="utf-8",
        )


def _write_release_files(decision: dict) -> bool:
    version = decision["version"] + "\n"
    changelog = prepend_changes(
        CHANGELOG_PATH.read_text(encoding="utf-8"),
        decision["version"],
        _changes(decision),
        date.today().isoformat(),
    )
    changed = VERSION_PATH.read_text(encoding="utf-8") != version
    changed = changed or CHANGELOG_PATH.read_text(encoding="utf-8") != changelog
    cargo_before = (ROOT / "Cargo.toml").read_text(encoding="utf-8")
    lock_path = ROOT / "Cargo.lock"
    lock_before = lock_path.read_text(encoding="utf-8") if lock_path.is_file() else ""
    VERSION_PATH.write_text(version, encoding="utf-8")
    CHANGELOG_PATH.write_text(changelog, encoding="utf-8")
    write_package_versions(ROOT, decision["version"])
    changed = changed or (ROOT / "Cargo.toml").read_text(encoding="utf-8") != cargo_before
    if lock_path.is_file():
        changed = changed or lock_path.read_text(encoding="utf-8") != lock_before
    return changed


def _commit_release(decision: dict) -> bool:
    """Write the version files and commit them. False when there is nothing new."""
    if _is_this_release("HEAD", decision["version"]):
        return False
    if not _write_release_files(decision):
        return False
    _run(
        ["git", "add", ".version", "CHANGELOG.md", "Cargo.toml", "Cargo.lock"],
        dry_run=False,
    )
    _run(
        ["git", "commit", "-m", decision["commit_subject"]],
        dry_run=False,
        env=_git_env(),
    )
    return True


def _published_rev(decision: dict) -> str | None:
    """A rev that already is this release, so a re-run must not commit again."""
    version = decision["version"]
    tag = decision["tag"]
    subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT, check=True)
    subprocess.run(["git", "fetch", "origin", "tag", tag], cwd=ROOT, check=False)
    if _is_this_release("origin/main", version):
        return "origin/main"
    if _tag_exists(tag):
        return f"refs/tags/{tag}"
    return None


def _checkout(rev: str) -> None:
    _run(["git", "checkout", "--detach", rev], dry_run=False)


def _push_main(decision: dict) -> None:
    """Push HEAD to main. On a rejected update, rebuild the commit and try again."""
    version = decision["version"]
    for attempt in range(1, 5):
        result = subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode == 0:
            return
        if not _push_rejected(result.stderr + result.stdout):
            raise SystemExit(f"git push origin HEAD:main failed:\n{result.stderr}")
        print(f"# push rejected ({attempt}), rebuilding on origin/main", flush=True)
        subprocess.run(["git", "fetch", "origin", "main"], cwd=ROOT, check=True)
        if _is_this_release("origin/main", version):
            _checkout("origin/main")
            return
        _checkout("origin/main")
        if not _commit_release(decision):
            if _is_this_release("HEAD", version):
                return
            raise SystemExit("rebuilt release commit was empty")
    raise SystemExit("git push origin HEAD:main was rejected four times")


def publish_tag(decision: dict, dry_run: bool) -> None:
    """Push ``vX.Y.Z`` and create the GitHub Release. Does not move an existing tag."""
    if decision.get("action") != "publish":
        raise SystemExit(f"refusing to tag action {decision.get('action')}")
    tag = decision["tag"]
    if dry_run:
        for argv in push_commands(decision):
            if argv == ["git", "push", "origin", "HEAD:main"]:
                continue
            _run(argv, dry_run=True)
        return
    if not _tag_exists(tag):
        sha = _output(["git", "rev-parse", "HEAD"])
        _run(["git", "tag", tag, sha], dry_run=False)
        _run(["git", "push", "origin", tag], dry_run=False)
    if _release_exists(tag):
        print(f"release {tag} already exists")
        return
    notes = ROOT / ".git" / f"{tag}-notes.md"
    notes.write_text(f"Release {tag}.\n\nSee CHANGELOG.md.\n", encoding="utf-8")
    _run(
        ["gh", "release", "create", tag, "--title", tag, "--notes-file", str(notes)],
        dry_run=False,
    )


def _store_decision(path: str | None, decision: dict) -> None:
    if path:
        Path(path).write_text(json.dumps(decision) + "\n", encoding="utf-8")


def publish(decision: dict, dry_run: bool, decision_path: str | None = None) -> None:
    """Bump, commit, push main, then tag that commit."""
    if decision.get("action") != "publish":
        raise SystemExit(f"refusing to publish action {decision.get('action')}")
    if dry_run:
        print(f"# commit {decision['commit_subject']}")
        for argv in push_commands(decision):
            _run(argv, dry_run=True)
        return
    existing = _published_rev(decision)
    if existing:
        _checkout(existing)
    else:
        # The workflow checkout is the push that started the run. origin/main
        # may have moved. Classify that tip, then commit the release on it.
        head = _output(["git", "rev-parse", "HEAD"])
        origin = _output(["git", "rev-parse", "origin/main"])
        if head != origin:
            _checkout(origin)
        version = VERSION_PATH.read_text(encoding="utf-8")
        decision = classify_tip(version, "HEAD")
        _store_decision(decision_path, decision)
        if decision.get("action") != "publish":
            print(f"release skipped: {decision.get('reason')}")
            return
        if not _commit_release(decision) and not _is_this_release("HEAD", decision["version"]):
            raise SystemExit("release files were unchanged but HEAD is not the release commit")
    _push_main(decision)
    publish_tag(decision, dry_run=False)


def self_test() -> None:
    """Check the dry-run plan and the non-fast-forward detector. Does not push."""
    version_before = VERSION_PATH.read_text(encoding="utf-8")
    changelog_before = CHANGELOG_PATH.read_text(encoding="utf-8")
    decision = decide_unreleased(
        [
            "✨ feat(turns): stream a chat turn with an inline agent (#22)\n",
            "⚡️ perf(llm): reuse one http client for model streams (#24)\n",
        ],
        "0.2.1",
    )
    if decision["version"] != "0.3.0":
        raise SystemExit(f"expected v0.3.0, got {decision['version']}")
    publish(decision, dry_run=True)
    if VERSION_PATH.read_text(encoding="utf-8") != version_before:
        raise SystemExit("dry-run changed .version")
    if CHANGELOG_PATH.read_text(encoding="utf-8") != changelog_before:
        raise SystemExit("dry-run changed CHANGELOG.md")
    commands = push_commands(decision)
    if ["git", "push", "origin", "HEAD:main"] not in commands:
        raise SystemExit(f"missing main push: {commands}")
    for argv in commands:
        if "--force" in argv or "-f" in argv:
            raise SystemExit(f"dry-run force-pushes: {argv}")
    if not _push_rejected("! [rejected] main -> main (non-fast-forward)"):
        raise SystemExit("non-fast-forward was not treated as a retry")
    if _push_rejected("fatal: could not read Username"):
        raise SystemExit("auth failure was treated as a retry")
    try:
        publish({"action": "skip"}, dry_run=True)
    except SystemExit:
        pass
    else:
        raise SystemExit("publish accepted a skip decision")
    _check_versions_match_after_bump()
    print("release_publish.py self-test ok")


def _check_versions_match_after_bump() -> None:
    """Cargo.toml, Cargo.lock, and .version share one version after a bump."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Cargo.toml").write_text(
            "\n".join(
                [
                    "[package]",
                    'name = "llm-guardrails-core"',
                    'version = "0.2.0"',
                    "",
                    "[dependencies]",
                    'pyo3 = { version = "0.29", features = ["extension-module"] }',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (root / "Cargo.lock").write_text(
            "\n".join(
                [
                    "[[package]]",
                    'name = "pyo3"',
                    'version = "0.29.3"',
                    "",
                    "[[package]]",
                    'name = "llm-guardrails-core"',
                    'version = "0.2.0"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (root / ".version").write_text("0.2.0\n", encoding="utf-8")
        write_package_versions(root, "0.2.1")
        (root / ".version").write_text("0.2.1\n", encoding="utf-8")
        cargo = (root / "Cargo.toml").read_text(encoding="utf-8")
        lock = (root / "Cargo.lock").read_text(encoding="utf-8")
        recorded = (root / ".version").read_text(encoding="utf-8").strip()
        if 'version = "0.2.1"' not in cargo.split("[dependencies]", 1)[0]:
            raise SystemExit(f"Cargo.toml package version was not bumped:\n{cargo}")
        if 'pyo3 = { version = "0.29"' not in cargo:
            raise SystemExit("dependency version was rewritten")
        core = lock.split('name = "llm-guardrails-core"', 1)[1]
        if 'version = "0.2.1"' not in core:
            raise SystemExit(f"Cargo.lock root package was not bumped:\n{lock}")
        if 'name = "pyo3"\nversion = "0.29.3"' not in lock:
            raise SystemExit("Cargo.lock rewrote a dependency version")
        if recorded != "0.2.1":
            raise SystemExit(f".version is {recorded}, not 0.2.1")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("publish",))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--decision-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.action != "publish":
        raise SystemExit("pass publish or --self-test")
    os.chdir(ROOT)
    publish(_read_decision(args.decision_file), args.dry_run, args.decision_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

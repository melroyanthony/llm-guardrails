#!/usr/bin/env python3
"""Classify commits since the last tag and decide the next release.

feat bumps minor, and every other type in ``commit-types.json`` bumps patch,
including test, ci, docs, and chore. A breaking marker (``!`` or a
``BREAKING CHANGE:`` footer) bumps major once the current version is 1.0.0
or newer, and bumps minor while the major is still 0. The changelog section
stays Breaking changes either way. The highest bump among unreleased commits
wins, so a later patch does not hide an earlier minor. A subject of
``chore(release): vX.Y.Z`` is skipped, including when it is the tip, so the
release commit does not start another release.

``--self-test`` also checks that the workflow pushes that commit to ``main``
without a force-push.
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

ROOT = Path(__file__).resolve().parent.parent
TYPES_PATH = ROOT / "scripts" / "commit-types.json"
COMMITLINT_PATH = ROOT / ".commitlintrc.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "release.yml"
REPO_URL = "https://github.com/melroyanthony/llm-guardrails"
RELEASE_TITLE = "🔖 chore(release): v{version}"
RELEASE_SUBJECT = re.compile(r"^chore\(release\): v(\d+\.\d+\.\d+)$")
PR_SUFFIX = re.compile(r"\s+\(#(\d+)\)\s*$")
MERGE_PR = re.compile(r"^Merge pull request #(\d+)\b")
# Conventional Commits: a breaking footer is its own line, not a mention in prose.
_BREAKING_FOOTER = re.compile(r"^(?:BREAKING CHANGE|BREAKING-CHANGE): \S", re.MULTILINE)

Push = list[str]


def load_types() -> dict:
    """Return the commit-type table."""
    return json.loads(TYPES_PATH.read_text(encoding="utf-8"))


def type_names() -> list[str]:
    """Return conventional types in commitlint order."""
    return [item["name"] for item in load_types()["types"]]


def pr_number(message: str) -> str | None:
    """Pull N from ``(#N)`` or ``Merge pull request #N``."""
    first = _first_line(message)
    suffix = PR_SUFFIX.search(first)
    if suffix:
        return suffix.group(1)
    merge = MERGE_PR.match(first)
    if merge:
        return merge.group(1)
    return None


def choose_subject(message: str, pr_title: str | None) -> str:
    """Pick the squash subject, preferring a fetched pull request title."""
    if pr_title and pr_title.strip():
        return pr_title.strip()
    lines = [line.strip() for line in message.splitlines()]
    first = lines[0] if lines else ""
    if MERGE_PR.match(first):
        for line in lines[1:]:
            if line:
                return line
        return first
    return PR_SUFFIX.sub("", first).strip()


def strip_emoji(text: str) -> str:
    """Drop leading non-letters, including the gitmoji and the space after it."""
    for index, char in enumerate(text):
        if char.isalpha():
            return text[index:].lstrip()
    return text.strip()


def classify(subject: str, body: str, version: str | None = None) -> dict:
    """Return the bump kind for an already-stripped subject.

    A ``!`` before the colon, or a footer line that starts with
    ``BREAKING CHANGE: `` or ``BREAKING-CHANGE: `` and then text, is a major
    bump from 1.0.0 up. Below that it is a minor bump. The changelog section
    stays ``Breaking changes`` in both cases. A mention in prose or backticks
    is not a footer. The description must be non-empty and start with a
    cased letter or a digit. The type, and the scope when one is present,
    stay conventional.
    """
    names = "|".join(type_names())
    pattern = re.compile(rf"^({names})(\([a-z0-9][a-z0-9._-]*\))?(!)?: (.+)$")
    match = pattern.match(subject)
    if match is None or not _description_opens(match.group(4)):
        return {"bump": "none", "subject": subject}
    name = match.group(1)
    entry = next(item for item in load_types()["types"] if item["name"] == name)
    breaking = match.group(3) is not None or _BREAKING_FOOTER.search(body) is not None
    if breaking:
        kind = "minor" if _below_one(version) else "major"
        section = "Breaking changes"
    else:
        kind = entry["bump"]
        section = entry["section"]
    return {
        "bump": kind,
        "type": name,
        "section": section,
        "subject": subject,
    }


def _below_one(version: str | None) -> bool:
    """True when ``version`` is a 0.x release."""
    if not version or not version.strip():
        return False
    return int(version.strip().split(".", 1)[0]) == 0


def bump_version(current: str, kind: str) -> str:
    """Apply one semver bump. A major bump below 1.0 stays on 0.x."""
    major, minor, patch = (int(part) for part in current.strip().split("."))
    if kind == "major" and major == 0:
        kind = "minor"
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump {kind}")


_BUMP_RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}


def _subject_of(message: str, title: str | None) -> str:
    raw = title.strip() if title and title.strip() else choose_subject(message, None)
    return strip_emoji(PR_SUFFIX.sub("", raw).strip())


def decide_unreleased(messages: list[str], version: str, tip_title: str | None = None) -> dict:
    """Choose skip or publish from commits since the last tag, oldest first.

    The last message is the tip. A release subject on the tip skips the run
    even when earlier commits would have bumped. Otherwise every releasable
    commit is kept and the highest bump wins.
    """
    if not messages:
        return {"action": "skip", "reason": "no commits since the last tag"}
    tip_subject = _subject_of(messages[-1], tip_title)
    if RELEASE_SUBJECT.match(tip_subject):
        return {
            "action": "skip",
            "reason": "release commit does not start another release",
            "subject": tip_subject,
        }
    changes: list[dict[str, str]] = []
    best = "none"
    for index, message in enumerate(messages):
        title = tip_title if index == len(messages) - 1 else None
        subject = _subject_of(message, title)
        if RELEASE_SUBJECT.match(subject):
            continue
        classified = classify(subject, message, version)
        if classified["bump"] == "none":
            continue
        changes.append(
            {
                "section": classified["section"],
                "subject": classified["subject"],
                "bump": classified["bump"],
            }
        )
        if _BUMP_RANK[classified["bump"]] > _BUMP_RANK[best]:
            best = classified["bump"]
    if best == "none" or not changes:
        return {
            "action": "skip",
            "reason": "subject is not releasable",
            "subject": tip_subject,
        }
    new_version = bump_version(version, best)
    return {
        "action": "publish",
        "version": new_version,
        "tag": f"v{new_version}",
        "commit_subject": RELEASE_TITLE.format(version=new_version),
        "bump": best,
        "section": changes[-1]["section"],
        "subject": changes[-1]["subject"],
        "changes": changes,
    }


def decide(message: str, version: str, pr_title: str | None) -> dict:
    """Choose skip or publish for one squash subject."""
    return decide_unreleased([message], version, tip_title=pr_title)


_UNRELEASED = "## Unreleased"


def _is_h2(line: str) -> bool:
    """A changelog section heading. `###` does not match `## `."""
    return line.startswith("## ")


def _find_h2(lines: list[str], predicate) -> tuple[int, int] | None:
    """Return the heading index and the index of the next h2, or the end."""
    for index, line in enumerate(lines):
        if predicate(line):
            end = index + 1
            while end < len(lines) and not _is_h2(lines[end]):
                end += 1
            return index, end
    return None


def _strip_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _is_note(line: str) -> bool:
    """A hand-written Unreleased line. Blank lines and `###` headings are not."""
    text = line.strip()
    return bool(text) and not text.startswith("###")


def _has_entries(lines: list[str]) -> bool:
    return any(_is_note(line) for line in lines)


def _drop_span(lines: list[str], start: int, end: int) -> list[str]:
    return lines[:start] + lines[end:]


def _generated_body(changes: list[dict[str, str]]) -> list[str]:
    """Commit subjects grouped by section. Order is first-seen, then encounter."""
    grouped: dict[str, list[str]] = {}
    for change in changes:
        grouped.setdefault(change["section"], []).append(change["subject"])
    blocks: list[str] = []
    for section, subjects in grouped.items():
        lines = [f"### {section}", ""]
        lines.extend(f"* {subject}" for subject in subjects)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks).splitlines()


def _join_changelog(lines: list[str]) -> str:
    text = "\n".join(lines).strip() + "\n"
    return text


def _unreleased_at_top(lines: list[str], notes: list[str]) -> list[str]:
    """Put `## Unreleased` under the title, with `notes` when the next release owns them."""
    span = _find_h2(lines, lambda line: line.strip() == _UNRELEASED)
    if span is not None:
        lines = _drop_span(lines, span[0], span[1])
    if not lines or not lines[0].startswith("# "):
        lines = ["# Changelog", *lines]
    rest = lines[1:]
    while rest and not rest[0].strip():
        rest = rest[1:]
    block = [_UNRELEASED, ""]
    if notes:
        block.extend(notes)
        block.append("")
    return [lines[0], "", *block, *rest]


def _empty_unreleased_at_top(lines: list[str]) -> list[str]:
    """Leave one empty `## Unreleased` immediately under the title."""
    return _unreleased_at_top(lines, [])


def prepend_changes(existing: str, version: str, changes: list[dict[str, str]], date: str) -> str:
    """Insert one version section and consume `## Unreleased` into it.

    Hand-written notes under Unreleased, bullets or prose, become the new
    version body, with their `###` subsections kept in order. Those notes
    replace the generated commit lines. An empty Unreleased section falls
    back to the generated lines. The heading stays at the top. When the
    version section is already present, its body stays as released and any
    new notes stay under Unreleased for the next release.
    """
    lines = existing.splitlines()
    span = _find_h2(lines, lambda line: line.strip() == _UNRELEASED)
    notes: list[str] = []
    if span is not None:
        notes = _strip_edges(lines[span[0] + 1 : span[1]])
        lines = _drop_span(lines, span[0], span[1])
    use_notes = _has_entries(notes)
    marker = f"## [{version}]"
    version_span = _find_h2(lines, lambda line: line.startswith(marker))
    if version_span is not None:
        kept = notes if use_notes else []
        return _join_changelog(_unreleased_at_top(lines, kept))
    body = notes if use_notes else _generated_body(changes)
    heading = f"## [{version}]({REPO_URL}/releases/tag/v{version}) ({date})"
    if not lines or not lines[0].startswith("# "):
        lines = ["# Changelog", *lines]
    rest = lines[1:]
    while rest and not rest[0].strip():
        rest = rest[1:]
    lines = [lines[0], "", heading, "", *body, "", *rest]
    return _join_changelog(_empty_unreleased_at_top(lines))


def prepend_changelog(existing: str, version: str, section: str, subject: str, date: str) -> str:
    """Insert a keep-a-changelog style section under the title."""
    return prepend_changes(existing, version, [{"section": section, "subject": subject}], date)


def push_commands(decision: dict) -> list[Push]:
    """Git and gh commands for a publish decision. The branch push is not a force-push."""
    if decision["action"] != "publish":
        return []
    tag = decision["tag"]
    return [
        ["git", "push", "origin", "HEAD:main"],
        ["git", "push", "origin", tag],
        ["gh", "release", "create", tag, "--title", tag],
    ]


def _first_line(message: str) -> str:
    lines = message.splitlines()
    return lines[0].strip() if lines else ""


def _description_opens(description: str) -> bool:
    """True when the description starts with a cased letter or a digit.

    A cased letter has upper and lower case forms, so ``OIDC`` and ``É``
    pass and a caseless script such as CJK does not. ``2xx`` passes. A
    symbol, or an empty description, does not. Conventional subjects are
    expected to be ASCII.
    """
    if not description:
        return False
    first = description[0]
    return first.islower() or first.isupper() or first.isdigit()


def _fail(message: str) -> None:
    raise SystemExit(message)


def _check_types_match_commitlint() -> None:
    commitlint = json.loads(COMMITLINT_PATH.read_text(encoding="utf-8"))
    enum = commitlint["rules"]["type-enum"][2]
    if type_names() != enum:
        _fail(f"commit-types.json and .commitlintrc.json disagree: {type_names()} != {enum}")


def _check_forbidden_pushes(text: str, label: str) -> None:
    forbidden = (
        "git push --force",
        "git push -f",
        "--force-with-lease",
        "main --tags",
        "git push origin --tags",
    )
    for snippet in forbidden:
        if snippet in text:
            _fail(f"{label} contains forbidden snippet: {snippet}")
    for line in text.splitlines():
        if "git push" in line and "--force" in line:
            _fail(f"{label} force-pushes: {line.strip()}")


def _check_workflow_file() -> None:
    if not WORKFLOW_PATH.is_file():
        _fail(f"missing {WORKFLOW_PATH}")
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    _check_forbidden_pushes(text, "release workflow")
    publish = (ROOT / "scripts" / "release_publish.py").read_text(encoding="utf-8")
    _check_forbidden_pushes(publish, "release_publish.py")
    if "permissions: {}" not in text.split("jobs:", 1)[0]:
        _fail("release workflow must set permissions: {} before jobs")
    if "contents: write" not in text:
        _fail("release job must set contents: write")
    if "pull-requests:" in text:
        _fail("release workflow must not request pull-requests permission")
    if "release-pr" in text or "_ensure_pr" in publish or "def publish_pr" in publish:
        _fail("release pull request path is still present")
    if '["git", "push", "origin", "HEAD:main"]' not in publish:
        _fail("release_publish.py must push HEAD:main")


def _check_pushes_are_safe() -> None:
    decision = decide("✨ feat(api): stream a turn (#2)\n", "0.0.0", None)
    commands = push_commands(decision)
    saw_main = False
    for argv in commands:
        if "--force" in argv or "-f" in argv or "--tags" in argv or "--force-with-lease" in argv:
            _fail(f"unsafe push: {argv}")
        if argv == ["git", "push", "origin", "HEAD:main"]:
            saw_main = True
    if not saw_main:
        _fail(f"publish does not push main: {commands}")
    skipped = decide("🔖 chore(release): v0.1.0 (#3)\n", "0.1.0", None)
    if push_commands(skipped):
        _fail("a release subject must not push")


def _expect(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        _fail(f"{label}: {actual!r} != {expected!r}")


def _check_decisions() -> None:
    feat = decide("✨ feat(api): stream a turn (#2)\n", "0.0.0", None)
    _expect(feat["action"], "publish", "feat action")
    _expect(feat["version"], "0.1.0", "feat version")
    _expect(feat["commit_subject"], "🔖 chore(release): v0.1.0", "feat title")
    _expect(feat["bump"], "minor", "feat bump")

    fix = decide("🐛 fix(api): close the stream\n", "0.1.0", None)
    _expect(fix["bump"], "patch", "fix bump")
    _expect(fix["version"], "0.1.1", "fix version")

    below = decide("💥 feat(api)!: replace ids\n", "0.1.0", None)
    _expect(below["bump"], "minor", "bang bump below 1.0")
    _expect(below["version"], "0.2.0", "bang version below 1.0")
    _expect(below["changes"][0]["section"], "Breaking changes", "bang section below 1.0")

    footer = "✨ feat(api): change the envelope\n\nBREAKING CHANGE: error shape\n"
    released = decide(footer, "1.0.0", None)
    _expect(released["bump"], "major", "footer bump")
    _expect(released["version"], "2.0.0", "footer version")
    _expect(released["changes"][0]["section"], "Breaking changes", "footer section")
    hyphen = "🐛 fix(api): change the envelope\n\nBREAKING-CHANGE: error shape\n"
    _expect(decide(hyphen, "1.0.0", None)["bump"], "major", "hyphen footer bump")
    prose = "👷 ci(release): note the marker\n\nThe body mentions `BREAKING CHANGE:` in prose.\n"
    _expect(decide(prose, "0.6.1", None)["bump"], "patch", "prose is not a footer")

    chore = decide("🎉 chore(repo): bootstrap the workspace\n", "0.0.0", None)
    _expect(chore["bump"], "patch", "chore bump")
    _expect(chore["version"], "0.0.1", "chore version")

    skipped = decide("update readme\n", "0.0.0", None)
    _expect(skipped["action"], "skip", "skip action")

    release_commit = decide("🔖 chore(release): v0.1.0 (#9)\n", "0.1.0", None)
    _expect(release_commit["action"], "skip", "release commit action")
    _expect(release_commit["subject"], "chore(release): v0.1.0", "release commit subject")

    merge = "Merge pull request #4 from melroyanthony/feat/x\n\n✨ feat(api): stream a turn\n"
    _expect(decide(merge, "0.0.0", None)["version"], "0.1.0", "merge version")
    titled = decide(merge, "0.0.0", "🐛 fix(api): close the stream")
    _expect(titled["bump"], "patch", "pr title wins")
    _expect(pr_number(merge), "4", "merge pr number")
    _expect(pr_number("✨ feat(api): stream a turn (#2)"), "2", "suffix pr number")

    # The old release PR looked only at #24's perf subject and opened v0.2.2.
    # Since v0.2.1 the unreleased commits are that feat and that perf. Minor wins.
    perf_only = decide(
        "⚡️ perf(llm): reuse one http client for model streams (#24)\n",
        "0.2.1",
        None,
    )
    _expect(perf_only["version"], "0.2.2", "perf alone is a patch")
    unreleased = decide_unreleased(
        [
            "✨ feat(turns): stream a chat turn with an inline agent (#22)\n",
            "⚡️ perf(llm): reuse one http client for model streams (#24)\n",
        ],
        "0.2.1",
    )
    _expect(unreleased["action"], "publish", "unreleased action")
    _expect(unreleased["bump"], "minor", "feat outranks perf")
    _expect(unreleased["version"], "0.3.0", "first direct release")
    _expect(unreleased["commit_subject"], "🔖 chore(release): v0.3.0", "v0.3.0 subject")
    _expect(
        [item["subject"] for item in unreleased["changes"]],
        [
            "feat(turns): stream a chat turn with an inline agent",
            "perf(llm): reuse one http client for model streams",
        ],
        "both unreleased subjects",
    )
    again = decide_unreleased(
        [
            "✨ feat(turns): stream a chat turn with an inline agent (#22)\n",
            "⚡️ perf(llm): reuse one http client for model streams (#24)\n",
            "🔖 chore(release): v0.3.0\n",
        ],
        "0.2.1",
    )
    _expect(again["action"], "skip", "release tip does not bump again")
    # This pull request's own merge is a ci commit on top of those two.
    # Patch does not lower the minor, so the first publish is still v0.3.0.
    with_ci = decide_unreleased(
        [
            "✨ feat(turns): stream a chat turn with an inline agent (#22)\n",
            "⚡️ perf(llm): reuse one http client for model streams (#24)\n",
            "👷 ci(release): publish releases directly from main (#26)\n",
        ],
        "0.2.1",
    )
    _expect(with_ci["version"], "0.3.0", "ci commit keeps v0.3.0")
    _expect(with_ci["bump"], "minor", "ci does not lower the bump")
    _expect(len(with_ci["changes"]), 3, "ci commit is in the changelog")
    _check_two_unreleased_commits_render_both_entries()
    _check_highest_bump_skips_a_middle_release_commit()
    _check_uppercase_or_digit_description()
    _check_v0_43_0_range_publishes_v0_44_0()


def _git(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "release-test"
    env["GIT_AUTHOR_EMAIL"] = "release-test@example.com"
    env["GIT_COMMITTER_NAME"] = "release-test"
    env["GIT_COMMITTER_EMAIL"] = "release-test@example.com"
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _check_a_commit_landed_before_tagging_is_listed() -> None:
    """HEAD stays on the triggering push. The later main tip is what gets tagged."""
    with tempfile.TemporaryDirectory() as raw:
        cwd = Path(raw)
        _git(cwd, "init", "-b", "main")
        _git(cwd, "commit", "--allow-empty", "-m", "🎉 chore(repo): bootstrap the workspace")
        _git(cwd, "tag", "v0.1.0")
        _git(cwd, "commit", "--allow-empty", "-m", "⬆️ build(deps): bump the uv group with 2 updates (#149)")
        _git(cwd, "commit", "--allow-empty", "-m", "⬆️ build(deps): bump the npm group with 4 updates (#150)")
        _git(cwd, "checkout", "--detach", "HEAD~1")
        stale = [item["subject"] for item in classify_tip("0.1.0", "HEAD", cwd)["changes"]]
        fresh = classify_tip("0.1.0", "main", cwd)
        _expect(stale, ["build(deps): bump the uv group with 2 updates"], "checkout range misses npm")
        _expect(
            [item["subject"] for item in fresh["changes"]],
            [
                "build(deps): bump the uv group with 2 updates",
                "build(deps): bump the npm group with 4 updates",
            ],
            "origin tip lists the commit merged before tagging",
        )
        rendered = prepend_changes("# Changelog\n\n", fresh["version"], fresh["changes"], "2026-10-30")
        if "* build(deps): bump the npm group with 4 updates" not in rendered:
            _fail(f"npm bump missing from the release that would tag main:\n{rendered}")


ISSUE_159_SUBJECT = (
    "✨ feat(auth): OIDC login, session cookies, CSRF and web sign-in (#59) (#159)"
)
THIS_FIX_SUBJECT = "🐛 fix(release): accept uppercase or digit subject starts (#168)"


def _check_uppercase_or_digit_description() -> None:
    """A description may start with a cased letter or a digit.

    The type, an optional scope, and a non-empty description are still required.
    """
    decision = decide(ISSUE_159_SUBJECT + "\n", "0.43.0", None)
    _expect(decision["action"], "publish", "issue 159 action")
    _expect(decision["bump"], "minor", "issue 159 bump")
    _expect(decision["version"], "0.44.0", "issue 159 version")
    _expect(decision["changes"][0]["section"], "Features", "issue 159 section")
    classified = classify(
        "feat(auth): OIDC login, session cookies, CSRF and web sign-in (#59)",
        "",
        "0.43.0",
    )
    _expect(classified["type"], "feat", "issue 159 type")
    _expect(classified["bump"], "minor", "issue 159 classified bump")
    _expect(classify("fix(api): 2xx body kept", "", "0.43.0")["bump"], "patch", "digit description")
    _expect(classify("OIDC login stuff", "", "0.43.0")["bump"], "none", "subject without a type")
    _expect(classify("feat(Auth): lower", "", "0.43.0")["bump"], "none", "uppercase scope")
    _expect(classify("nope(auth): lower", "", "0.43.0")["bump"], "none", "unknown type")
    _expect(classify("feat(auth):", "", "0.43.0")["bump"], "none", "empty description")


def _check_v0_43_0_range_publishes_v0_44_0() -> None:
    """Commits after v0.43.0 include #159 and this fix. Minor wins over patch."""
    before = _workspace_tags()
    with tempfile.TemporaryDirectory() as raw:
        cwd = Path(raw)
        _git(cwd, "init", "-b", "main")
        _git(cwd, "commit", "--allow-empty", "-m", "🔖 chore(release): v0.43.0")
        _git(cwd, "tag", "v0.43.0")
        _git(cwd, "commit", "--allow-empty", "-m", ISSUE_159_SUBJECT)
        _git(cwd, "commit", "--allow-empty", "-m", THIS_FIX_SUBJECT)
        decision = classify_tip("0.43.0", "HEAD", cwd)
    if _workspace_tags() != before:
        _fail("workspace tags were created, moved, or deleted")
    _expect(decision["action"], "publish", "v0.43.0 range action")
    _expect(decision["bump"], "minor", "feat outranks this fix")
    _expect(decision["version"], "0.44.0", "next release after v0.43.0")
    if decision["version"] == "0.43.1":
        _fail("the fix was classified alone and hid #159")
    _expect(
        [item["subject"] for item in decision["changes"]],
        [
            "feat(auth): OIDC login, session cookies, CSRF and web sign-in",
            "fix(release): accept uppercase or digit subject starts",
        ],
        "both commits since v0.43.0",
    )
    rendered = prepend_changes("# Changelog\n\n", decision["version"], decision["changes"], "2026-11-01")
    for subject in (
        "feat(auth): OIDC login, session cookies, CSRF and web sign-in",
        "fix(release): accept uppercase or digit subject starts",
    ):
        if f"* {subject}" not in rendered:
            _fail(f"changelog missed {subject}:\n{rendered}")
    if "v0.43.1" in rendered:
        _fail(f"changelog used a patch version:\n{rendered}")


def _workspace_tags() -> str:
    result = subprocess.run(
        ["git", "tag", "--list"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _check_two_unreleased_commits_render_both_entries() -> None:
    """Two commits after the last tag both land in the changelog."""
    decision = decide_unreleased(
        [
            "📝 docs(deploy): note the bind\n",
            "🐛 fix(api): keep the owner check\n",
        ],
        "0.42.3",
    )
    _expect(decision["action"], "publish", "two commits publish")
    _expect(decision["bump"], "patch", "docs and fix stay patch")
    _expect(decision["version"], "0.42.4", "one patch for both commits")
    rendered = prepend_changes("# Changelog\n\n", decision["version"], decision["changes"], "2026-10-30")
    if "* docs(deploy): note the bind" not in rendered or "* fix(api): keep the owner check" not in rendered:
        _fail(f"both changelog entries were not rendered:\n{rendered}")


def _check_highest_bump_skips_a_middle_release_commit() -> None:
    """A release commit in the range is omitted. The highest remaining bump wins."""
    decision = decide_unreleased(
        [
            "🔖 chore(release): v0.41.0\n",
            "🔧 chore(deps): ignore odd majors\n",
            "✨ feat(auth): add a service key\n",
            "🐛 fix(auth): compare digests\n",
        ],
        "0.41.0",
    )
    _expect(decision["bump"], "minor", "feat outranks chore and fix")
    _expect(decision["version"], "0.42.0", "minor from 0.41.0")
    _expect(
        [item["subject"] for item in decision["changes"]],
        [
            "chore(deps): ignore odd majors",
            "feat(auth): add a service key",
            "fix(auth): compare digests",
        ],
        "release commit is not a changelog entry",
    )


def _check_changelog() -> None:
    rendered = prepend_changelog("# Changelog\n\nIntro.\n", "0.1.0", "Features", "feat(api): stream a turn", "2026-10-21")
    if "## [0.1.0]" not in rendered or "* feat(api): stream a turn" not in rendered:
        _fail(f"changelog render missed the entry:\n{rendered}")
    if not rendered.startswith("# Changelog\n"):
        _fail("changelog title was not preserved")
    again = prepend_changelog(rendered, "0.1.0", "Features", "feat(api): stream a turn", "2026-10-21")
    if again.count("## [0.1.0]") != 1:
        _fail("changelog prepend was not idempotent")
    combined = prepend_changes(
        "# Changelog\n\n",
        "0.3.0",
        [
            {"section": "Features", "subject": "feat(turns): stream a chat turn with an inline agent"},
            {"section": "Performance", "subject": "perf(llm): reuse one http client for model streams"},
        ],
        "2026-10-21",
    )
    if "### Features\n\n* feat(turns):" not in combined or "### Performance\n\n* perf(llm):" not in combined:
        _fail(f"combined changelog missed a section:\n{combined}")
    split = prepend_changes(
        "# Changelog\n\n",
        "0.4.0",
        [
            {"section": "Features", "subject": "feat(api): first"},
            {"section": "Bug Fixes", "subject": "fix(api): middle"},
            {"section": "Features", "subject": "feat(api): second"},
        ],
        "2026-10-21",
    )
    if split.count("### Features") != 1 or split.count("### Bug Fixes") != 1:
        _fail(f"non-adjacent sections were not grouped:\n{split}")
    features, fixes = split.split("### Bug Fixes", 1)
    if features.find("feat(api): first") > features.find("feat(api): second"):
        _fail(f"subjects inside a section lost encounter order:\n{split}")
    if "fix(api): middle" not in fixes or split.find("### Features") > split.find("### Bug Fixes"):
        _fail(f"section order did not follow first appearance:\n{split}")
    _check_unreleased_is_consumed()
    _check_empty_unreleased_is_idempotent()
    _check_prose_unreleased_is_consumed()
    _check_rerun_keeps_released_body_and_new_notes()
    _check_changelog_keeps_empty_unreleased()


def _check_unreleased_is_consumed() -> None:
    """Notes in more than one subsection move into the new version."""
    source = """# Changelog

## Unreleased

### Features

* hand written feature

### Security

* hand written security note

## [0.1.0](https://github.com/melroyanthony/hangar/releases/tag/v0.1.0) (2026-01-01)

### Bug Fixes

* fix(api): older
"""
    rendered = prepend_changes(
        source,
        "0.2.0",
        [{"section": "Features", "subject": "feat(api): generic"}],
        "2026-11-03",
    )
    if not rendered.startswith("# Changelog\n\n## Unreleased\n\n## [0.2.0]"):
        _fail(f"empty Unreleased was not left above the new version:\n{rendered}")
    if "* hand written feature" not in rendered or "* hand written security note" not in rendered:
        _fail(f"unreleased subsections were not kept:\n{rendered}")
    if "feat(api): generic" in rendered:
        _fail(f"generated line was added beside hand-written notes:\n{rendered}")
    if rendered.index("### Features") > rendered.index("### Security"):
        _fail(f"subsection order changed:\n{rendered}")
    if rendered.index("## [0.2.0]") > rendered.index("## [0.1.0]"):
        _fail(f"older version was not left below the new one:\n{rendered}")
    again = prepend_changes(
        rendered,
        "0.2.0",
        [{"section": "Features", "subject": "feat(api): generic"}],
        "2026-11-03",
    )
    if again != rendered:
        _fail(f"consuming Unreleased was not idempotent:\n{again}")


def _check_empty_unreleased_is_idempotent() -> None:
    """No hand-written notes means the generated lines are used once."""
    source = """# Changelog

## Unreleased

## [0.1.0](https://github.com/melroyanthony/hangar/releases/tag/v0.1.0) (2026-01-01)

### Bug Fixes

* fix(api): older
"""
    rendered = prepend_changes(
        source,
        "0.2.0",
        [{"section": "Bug Fixes", "subject": "fix(api): generic"}],
        "2026-11-03",
    )
    if "* fix(api): generic" not in rendered or "* fix(api): older" not in rendered:
        _fail(f"empty Unreleased did not fall back to generated lines:\n{rendered}")
    if not rendered.startswith("# Changelog\n\n## Unreleased\n\n## [0.2.0]"):
        _fail(f"empty Unreleased was not kept at the top:\n{rendered}")
    again = prepend_changes(
        rendered,
        "0.2.0",
        [{"section": "Bug Fixes", "subject": "fix(api): generic"}],
        "2026-11-03",
    )
    if again != rendered:
        _fail(f"empty Unreleased release was not idempotent:\n{again}")


def _check_changelog_keeps_empty_unreleased() -> None:
    """This library's changelog keeps an empty Unreleased section above 0.2.0."""
    on_disk = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not on_disk.startswith("# Changelog\n\n## Unreleased\n\n## [0.2.0]"):
        _fail("CHANGELOG.md does not keep an empty Unreleased above 0.2.0")


def _check_prose_unreleased_is_consumed() -> None:
    """A note with no bullet is kept, not replaced by the generated line."""
    source = "# Changelog\n\n## Unreleased\n\nA prose note with no bullet.\n"
    rendered = prepend_changes(
        source,
        "0.2.0",
        [{"section": "Features", "subject": "feat(api): generic"}],
        "2026-11-03",
    )
    if "feat(api): generic" in rendered:
        _fail(f"generated line replaced a prose note:\n{rendered}")
    version = rendered.split("## [0.2.0]", 1)[-1]
    if "A prose note with no bullet." not in version:
        _fail(f"prose note was not consumed into the new version:\n{rendered}")
    if "A prose note with no bullet." in rendered.split("## [0.2.0]", 1)[0]:
        _fail(f"prose note stayed under Unreleased:\n{rendered}")


def _check_rerun_keeps_released_body_and_new_notes() -> None:
    """A second call for a published version does not rewrite that section."""
    source = """# Changelog

## [0.2.0](https://github.com/melroyanthony/hangar/releases/tag/v0.2.0) (2026-11-03)

### Features

* released note

## Unreleased

* a new note
"""
    rendered = prepend_changes(
        source,
        "0.2.0",
        [{"section": "Features", "subject": "feat(api): generic"}],
        "2026-11-03",
    )
    if "feat(api): generic" in rendered:
        _fail(f"re-run wrote a generated line into a released version:\n{rendered}")
    before, after = rendered.split("## [0.2.0]", 1)
    if "* a new note" not in before:
        _fail(f"new note was not kept under Unreleased:\n{rendered}")
    if "* released note" not in after:
        _fail(f"released body was rewritten:\n{rendered}")
    if "* a new note" in after.split("## [", 1)[0]:
        _fail(f"new note was copied into the released section:\n{rendered}")


def _check_since_tag_fails_closed_without_a_tag() -> None:
    """No tag plus a shipped .version must not scan the whole history."""
    with tempfile.TemporaryDirectory() as raw:
        cwd = Path(raw)
        _git(cwd, "init", "-b", "main")
        _git(cwd, "commit", "--allow-empty", "-m", "✨ feat(core): scaffold the library")
        try:
            classify_tip("0.2.0", "HEAD", cwd)
        except SystemExit as exc:
            text = str(exc)
            if "0.2.0" not in text or "0.0.0" not in text or "tag" not in text.lower():
                _fail(f"fail-closed message was unclear: {text}")
        else:
            _fail("--since-tag classified history when no v* tag exists")
        allowed = classify_tip("0.0.0", "HEAD", cwd)
        _expect(allowed["action"], "publish", "0.0.0 with no tag still classifies")
        _expect(allowed["version"], "0.1.0", "0.0.0 with no tag bumps from zero")


def self_test() -> None:
    """Run the classifier contract and the workflow safety checks."""
    _check_types_match_commitlint()
    _check_workflow_file()
    _check_pushes_are_safe()
    _check_decisions()
    _check_changelog()
    _check_a_commit_landed_before_tagging_is_listed()
    _check_since_tag_fails_closed_without_a_tag()
    print("release_subject.py self-test ok")


def latest_version_tag(cwd: Path | None = None) -> str | None:
    """Return the highest ``vX.Y.Z`` tag, or None when the repo has no release tag."""
    result = subprocess.run(
        ["git", "tag", "--list", "v*", "--sort=-v:refname"],
        cwd=cwd or ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if re.fullmatch(r"v\d+\.\d+\.\d+", line.strip()):
            return line.strip()
    return None


def commit_messages_since(tag: str | None, rev: str = "HEAD", cwd: Path | None = None) -> list[str]:
    """Return full commit messages after ``tag`` up to ``rev``, oldest first.

    ``tag is None`` is every commit reachable from ``rev``. The release job
    passes ``origin/main``: that is the parent of the commit about to be tagged.
    ``HEAD`` stays on the push that started the workflow.
    """
    revision = rev if tag is None else f"{tag}..{rev}"
    result = subprocess.run(
        ["git", "log", "--reverse", "--format=%x1e%B", revision],
        cwd=cwd or ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [part.strip("\n") for part in result.stdout.split("\x1e") if part.strip()]


def classify_tip(version: str, rev: str = "HEAD", cwd: Path | None = None) -> dict:
    """Decide the release for ``last tag..rev`` and record that tip.

    With no ``vX.Y.Z`` tag, every reachable commit would look unreleased.
    That is allowed only when ``.version`` is still ``0.0.0``. Any other
    version fails closed so a first publish cannot recount history that
    already shipped.
    """
    root = cwd or ROOT
    current = version.strip()
    tag = latest_version_tag(root)
    if tag is None and current != "0.0.0":
        _fail(
            "no vX.Y.Z tag exists and .version is "
            f"{current}, not 0.0.0; refusing to treat every commit as unreleased"
        )
    decision = decide_unreleased(commit_messages_since(tag, rev, root), current)
    tip = subprocess.check_output(["git", "rev-parse", rev], cwd=root, text=True).strip()
    decision["tip"] = tip
    return decision


def _read_message(args: argparse.Namespace) -> str:
    if args.message is not None:
        return args.message
    if args.message_file is not None:
        return Path(args.message_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--pr-number", action="store_true")
    parser.add_argument("--decide", action="store_true")
    parser.add_argument("--version")
    parser.add_argument("--version-file")
    parser.add_argument("--message")
    parser.add_argument("--message-file")
    parser.add_argument("--pr-title", default="")
    parser.add_argument(
        "--since-tag",
        action="store_true",
        help="Decide from commits after the highest vX.Y.Z tag",
    )
    parser.add_argument(
        "--rev",
        default="HEAD",
        help="Tip of the range. The release job uses origin/main, the commit it tags.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.decide and args.since_tag:
        version = args.version
        if args.version_file:
            version = Path(args.version_file).read_text(encoding="utf-8")
        if not version:
            _fail("--decide needs --version or --version-file")
        decision = classify_tip(version, args.rev)
        print(json.dumps(decision))
        return 0
    message = _read_message(args)
    if args.pr_number:
        number = pr_number(message)
        if number:
            print(number)
        return 0
    if args.decide:
        version = args.version
        if args.version_file:
            version = Path(args.version_file).read_text(encoding="utf-8")
        if not version:
            _fail("--decide needs --version or --version-file")
        decision = decide(message, version, args.pr_title or None)
        print(json.dumps(decision))
        return 0
    _fail("pass --self-test, --pr-number, or --decide")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

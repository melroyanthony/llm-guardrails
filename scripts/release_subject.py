#!/usr/bin/env python3
"""Classify a squash-merge subject and consume ``## Unreleased``.

Stdlib only. The changelog keeps an empty ``## Unreleased`` section at the
top. A release moves that section's body under the new version heading.
Handwritten notes win. An empty section gets one bullet from the subject.

``chore(release):`` subjects do not bump. ``.claude-plugin/plugin.json`` is
rewritten only when that file exists.

    python3 scripts/release_subject.py --self-test
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES_PATH = ROOT / "scripts" / "commit-types.json"
COMMITLINT_PATH = ROOT / ".commitlintrc.json"
DEFAULT_REPO = "https://github.com/melroyanthony/llm-guardrails"

SUBJECT_RE_TEMPLATE = (
    r"^(?P<type>{types})(?:\((?P<scope>[a-z0-9][a-z0-9._-]*)\))?(?P<breaking>!)?: "
    r"(?P<desc>[a-z].*)$"
)
PR_TRAILER_RE = re.compile(r"\s+\(#(?P<number>\d+)\)\s*$")
MERGE_RE = re.compile(r"^Merge pull request #(?P<number>\d+)\b")
UNRELEASED_RE = re.compile(r"^## Unreleased[ \t]*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)
BREAKING_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)

SECTION_FOR_TYPE = {
    "feat": "Added",
    "fix": "Fixed",
    "security": "Security",
    "revert": "Removed",
}


class ReleaseError(Exception):
    """The commit message or changelog cannot be released as given."""


def load_types(path: Path = TYPES_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    types = list(data["types"])
    minor = set(data["minor"])
    patch = set(data["patch"])
    if set(types) != minor | patch:
        raise ReleaseError("commit-types.json minor+patch must equal types")
    if minor & patch:
        raise ReleaseError("commit-types.json minor and patch overlap")
    return data


def assert_commitlint_matches(types: list[str], path: Path = COMMITLINT_PATH) -> None:
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    enum = data["rules"]["type-enum"][2]
    if list(enum) != list(types):
        raise ReleaseError("commit-types.json types and .commitlintrc.json type-enum differ")


def strip_emoji(subject: str) -> str:
    """Drop leading non-letters so a gitmoji prefix is not part of the type."""
    match = re.search(r"[A-Za-z]", subject)
    if match is None:
        return subject.strip()
    return subject[match.start() :].strip()


def pr_number(message: str) -> str:
    lines = message.splitlines()
    if not lines:
        return ""
    first = lines[0].strip()
    merge = MERGE_RE.match(first)
    if merge:
        return merge.group("number")
    trailer = PR_TRAILER_RE.search(first)
    if trailer:
        return trailer.group("number")
    return ""


def _second_nonempty_line(message: str) -> str:
    nonempty = [line.strip() for line in message.splitlines() if line.strip()]
    if len(nonempty) >= 2:
        return nonempty[1]
    return nonempty[0] if nonempty else ""


def choose_subject(message: str, pr_title: str | None) -> str:
    """Pick the subject a squash or merge commit should be classified on."""
    lines = message.splitlines()
    first = lines[0].strip() if lines else ""
    if MERGE_RE.match(first):
        raw = pr_title.strip() if pr_title and pr_title.strip() else _second_nonempty_line(message)
    elif pr_title and pr_title.strip():
        raw = pr_title.strip()
    else:
        raw = PR_TRAILER_RE.sub("", first).strip()
    return strip_emoji(raw)


def parse_subject(subject: str, types: list[str]) -> re.Match[str] | None:
    pattern = SUBJECT_RE_TEMPLATE.format(types="|".join(re.escape(t) for t in types))
    return re.match(pattern, subject)


def classify(message: str, pr_title: str | None, types_doc: dict) -> dict:
    subject = choose_subject(message, pr_title)
    types = list(types_doc["types"])
    match = parse_subject(subject, types)
    if match is None:
        return {"bump": "none", "subject": subject, "type": "", "scope": "", "desc": ""}
    kind = match.group("type")
    scope = match.group("scope") or ""
    breaking = bool(match.group("breaking")) or bool(BREAKING_RE.search(message))
    if kind == "chore" and scope == "release":
        bump = "none"
    elif breaking:
        bump = "major"
    elif kind in types_doc["minor"]:
        bump = "minor"
    elif kind in types_doc["patch"]:
        bump = "patch"
    else:
        bump = "none"
    return {
        "bump": bump,
        "subject": subject,
        "type": kind,
        "scope": scope,
        "desc": match.group("desc"),
    }


def bump_version(current: str, kind: str) -> str:
    parts = current.strip().split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ReleaseError(f"version must be MAJOR.MINOR.PATCH, got {current!r}")
    major, minor, patch = (int(part) for part in parts)
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ReleaseError(f"unknown bump {kind}")


def _split_changelog(text: str) -> tuple[str, str, str]:
    match = UNRELEASED_RE.search(text)
    if match is None:
        raise ReleaseError("CHANGELOG.md is missing a '## Unreleased' section")
    preamble = text[: match.start()]
    after = text[match.end() :]
    if after.startswith("\n"):
        after = after[1:]
    next_heading = NEXT_H2_RE.search(after)
    if next_heading is None:
        body = after
        rest = ""
    else:
        body = after[: next_heading.start()]
        rest = after[next_heading.start() :]
    return preamble, body, rest


def _synthesized_body(result: dict) -> str:
    section = SECTION_FOR_TYPE.get(result["type"], "Changed")
    return f"### {section}\n\n* {result['subject']}\n"


def render_changelog(
    text: str,
    version: str,
    result: dict,
    repo: str,
    date: str,
) -> str:
    preamble, body, rest = _split_changelog(text)
    notes = body.strip()
    version_body = notes + "\n" if notes else _synthesized_body(result)
    heading = f"## [{version}]({repo}/releases/tag/v{version}) ({date})"
    out = preamble.rstrip() + "\n\n## Unreleased\n\n" + heading + "\n\n" + version_body
    if rest.strip():
        if not out.endswith("\n"):
            out += "\n"
        out += "\n" + rest.lstrip("\n")
        if not out.endswith("\n"):
            out += "\n"
    elif not out.endswith("\n"):
        out += "\n"
    return out


def notes_for_version(text: str, version: str) -> str:
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*$", re.MULTILINE)
    match = heading.search(text)
    if match is None:
        raise ReleaseError(f"changelog has no section for {version}")
    after = text[match.end() :]
    if after.startswith("\n"):
        after = after[1:]
    next_heading = NEXT_H2_RE.search(after)
    body = after if next_heading is None else after[: next_heading.start()]
    return body.strip() + "\n"


def _replace_first_version(text: str, version: str) -> str:
    updated, count = re.subn(
        r'(?m)^(version = ")[^"]+(")\s*$',
        rf"\g<1>{version}\2",
        text,
        count=1,
    )
    if count != 1:
        raise ReleaseError("could not find a version field to bump")
    return updated


def bump_package_versions(root: Path, version: str) -> None:
    """Keep the Python and Rust package versions aligned with ``.version``."""
    for relative in ("pyproject.toml", "Cargo.toml"):
        path = root / relative
        if not path.is_file():
            continue
        path.write_text(
            _replace_first_version(path.read_text(encoding="utf-8"), version),
            encoding="utf-8",
        )


def maybe_update_plugin(root: Path, version: str) -> None:
    path = root / ".claude-plugin" / "plugin.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def apply_release(
    root: Path,
    message: str,
    pr_title: str | None,
    repo: str,
    date: str,
) -> dict:
    types_doc = load_types(root / "scripts" / "commit-types.json")
    assert_commitlint_matches(types_doc["types"], root / ".commitlintrc.json")
    result = classify(message, pr_title, types_doc)
    if result["bump"] == "none":
        return result
    version_path = root / ".version"
    current = version_path.read_text(encoding="utf-8").strip()
    nxt = bump_version(current, result["bump"])
    changelog_path = root / "CHANGELOG.md"
    rendered = render_changelog(
        changelog_path.read_text(encoding="utf-8"),
        nxt,
        result,
        repo,
        date,
    )
    version_path.write_text(nxt + "\n", encoding="utf-8")
    changelog_path.write_text(rendered, encoding="utf-8")
    bump_package_versions(root, nxt)
    maybe_update_plugin(root, nxt)
    result["next"] = nxt
    return result


def _write_fixture(root: Path, changelog: str, version: str = "0.2.0") -> None:
    (root / "scripts").mkdir()
    (root / "scripts" / "commit-types.json").write_text(
        TYPES_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / ".commitlintrc.json").write_text(
        COMMITLINT_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / ".version").write_text(version + "\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (root / "Cargo.toml").write_text(
        '[package]\nname = "x"\nversion = "0.2.0"\n',
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.2.0"\n',
        encoding="utf-8",
    )


def self_test() -> None:
    types_doc = load_types()
    assert_commitlint_matches(types_doc["types"])

    def expect(message: str, bump: str, subject: str, pr_title: str | None = None) -> None:
        got = classify(message, pr_title, types_doc)
        if got["bump"] != bump or got["subject"] != subject:
            raise ReleaseError(f"{message!r} -> {got}, want bump={bump} subject={subject}")

    expect(
        "✨ feat(core): add reversible pii placeholders",
        "minor",
        "feat(core): add reversible pii placeholders",
    )
    expect(
        "🐛 fix(api): reject an empty prompt\n\nwhy\n", "patch", "fix(api): reject an empty prompt"
    )
    expect("feat(api): add a route (#12)", "minor", "feat(api): add a route")
    expect(
        "Merge pull request #4 from melroyanthony/cursor/example\n\n✨ feat(core): stream tokens\n",
        "minor",
        "feat(core): stream tokens",
    )
    expect(
        "✨ feat(core): keep the old title\n",
        "minor",
        "feat(core): prefer the pull request title",
        pr_title="✨ feat(core): prefer the pull request title",
    )
    expect("💥 feat(api)!: drop the v0 response", "major", "feat(api)!: drop the v0 response")
    expect(
        "🐛 fix(core): rename a field\n\nBREAKING CHANGE: clients must send text\n",
        "major",
        "fix(core): rename a field",
    )
    expect("🔧 chore(release): v0.3.0", "none", "chore(release): v0.3.0")
    expect("🔖 chore(release): v0.3.0", "none", "chore(release): v0.3.0")
    expect("hello there", "none", "hello there")
    expect("⬆️ deps: bump pydantic", "patch", "deps: bump pydantic")

    if pr_number("✨ feat(core): add it (#9)\n") != "9":
        raise ReleaseError("pr number missed squash trailer")
    if pr_number("Merge pull request #15 from melroyanthony/x\n") != "15":
        raise ReleaseError("pr number missed merge commit")
    if bump_version("0.2.0", "minor") != "0.3.0":
        raise ReleaseError("minor bump")
    if bump_version("0.2.9", "patch") != "0.2.10":
        raise ReleaseError("patch bump")
    if bump_version("1.4.2", "major") != "2.0.0":
        raise ReleaseError("major bump")

    base = (
        "# Changelog\n\nNotes stay above.\n\n"
        "## Unreleased\n\n### Fixed\n\n"
        "* fix(api): keep the handwritten note\n\n"
        "## [0.2.0](https://example/releases/tag/v0.2.0) (2026-02-17)\n\n"
        "### Added\n\n* prior\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fixture(root, base)
        result = apply_release(
            root,
            "🐛 fix(api): this subject must not replace the note\n",
            None,
            "https://github.com/melroyanthony/llm-guardrails",
            "2026-11-04",
        )
        if result["next"] != "0.2.1":
            raise ReleaseError(f"expected 0.2.1, got {result}")
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        if not text.startswith("# Changelog\n"):
            raise ReleaseError("preamble dropped")
        if "## Unreleased\n" not in text.split("## [0.2.1]")[0]:
            raise ReleaseError("empty Unreleased section missing at top")
        unreleased_body = text.split("## Unreleased\n", 1)[1].split("## [0.2.1]", 1)[0]
        if unreleased_body.strip():
            raise ReleaseError(f"Unreleased was not emptied: {unreleased_body!r}")
        if "keep the handwritten note" not in text.split("## [0.2.0]")[0]:
            raise ReleaseError("handwritten Unreleased notes were not consumed")
        if "must not replace the note" in text:
            raise ReleaseError("subject bullet duplicated handwritten notes")
        if (root / ".version").read_text(encoding="utf-8").strip() != "0.2.1":
            raise ReleaseError(".version not updated")
        if 'version = "0.2.1"' not in (root / "Cargo.toml").read_text(encoding="utf-8"):
            raise ReleaseError("Cargo.toml version was not bumped")
        if 'version = "0.2.1"' not in (root / "pyproject.toml").read_text(encoding="utf-8"):
            raise ReleaseError("pyproject.toml version was not bumped")
        notes = notes_for_version(text, "0.2.1")
        if "handwritten note" not in notes:
            raise ReleaseError("notes extractor missed the new section")

        plugin_dir = root / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            '{"name": "x", "version": "0.0.0"}\n', encoding="utf-8"
        )
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## Unreleased\n\n"
            "## [0.2.1](https://example/releases/tag/v0.2.1) (2026-11-04)\n\n"
            "* old\n",
            encoding="utf-8",
        )
        (root / ".version").write_text("0.2.1\n", encoding="utf-8")
        empty = apply_release(
            root,
            "✨ feat(core): synthesise a bullet when unreleased is empty\n",
            None,
            DEFAULT_REPO,
            "2026-11-04",
        )
        if empty["next"] != "0.3.0":
            raise ReleaseError("empty unreleased should still bump feat to minor")
        rendered = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        if "* feat(core): synthesise a bullet when unreleased is empty" not in rendered:
            raise ReleaseError("empty Unreleased did not synthesise a bullet")
        plugin = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
        if plugin["version"] != "0.3.0":
            raise ReleaseError("plugin.json version was not rewritten")

        try:
            render_changelog(
                "# Changelog\n\nNo unreleased heading.\n",
                "0.0.1",
                empty,
                DEFAULT_REPO,
                "2026-11-04",
            )
        except ReleaseError:
            pass
        else:
            raise ReleaseError("missing Unreleased heading should fail")

    print("release_subject.py self-test ok")


def _read_message(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--pr-number", action="store_true")
    parser.add_argument("--message-file")
    parser.add_argument("--version", help="current MAJOR.MINOR.PATCH, from .version")
    parser.add_argument("--pr-title", default=None)
    parser.add_argument("--pr-title-file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--notes-for", help="print the changelog body for VERSION")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--github-output", help="append bump and next to this file")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return 0

    if args.notes_for:
        text = (args.root / "CHANGELOG.md").read_text(encoding="utf-8")
        sys.stdout.write(notes_for_version(text, args.notes_for))
        return 0

    message = _read_message(args.message_file)
    pr_title = args.pr_title
    if args.pr_title_file:
        loaded = Path(args.pr_title_file).read_text(encoding="utf-8").strip()
        pr_title = loaded or None
    if args.pr_number:
        print(pr_number(message))
        return 0

    if not args.version and not args.apply:
        parser.error("--version is required unless --self-test, --pr-number, or --notes-for")

    types_doc = load_types(args.root / "scripts" / "commit-types.json")
    assert_commitlint_matches(types_doc["types"], args.root / ".commitlintrc.json")
    if args.apply:
        result = apply_release(args.root, message, pr_title, args.repo, args.date)
        current = (args.root / ".version").read_text(encoding="utf-8").strip()
        nxt = result.get("next", "")
    else:
        result = classify(message, pr_title, types_doc)
        current = args.version.strip()
        nxt = "" if result["bump"] == "none" else bump_version(current, result["bump"])
        result["next"] = nxt

    print(f"bump={result['bump']}")
    print(f"next={result.get('next', nxt)}")
    print(f"subject={result['subject']}")
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as handle:
            handle.write(f"bump={result['bump']}\n")
            handle.write(f"next={result.get('next', nxt)}\n")
            handle.write(f"subject={result['subject']}\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

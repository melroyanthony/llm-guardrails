#!/usr/bin/env python3
"""Check a Claude Code Bash payload for a hybrid git commit subject.

Warns with hook JSON (additionalContext) so the model sees it. --strict
denies and exits 2. Types come from scripts/commit-types.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_segments import argv_of, git_command, split_segments
from hook_output import emit

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = "✨ feat(api): add user registration endpoint"
REVERT = re.compile(r'^Revert ".+"$')


def load_types() -> list[str]:
    data = json.loads(
        (ROOT / "scripts" / "commit-types.json").read_text(encoding="utf-8")
    )
    types = data["types"]
    if types and isinstance(types[0], dict):
        return [item["name"] for item in types]
    return list(types)


def subject_pattern() -> re.Pattern[str]:
    types = "|".join(re.escape(item) for item in load_types())
    return re.compile(
        r"^(?P<emoji>\S+)\s+(?:"
        + types
        + r")(\([a-z0-9][a-z0-9._-]*\))?(!)?: [a-z][^\n]*$"
    )


def command_from(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(data, dict):
        return raw
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or "")
    return raw


def _first_subject_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _heredoc_body(text: str) -> str:
    lines = text.splitlines()
    if not lines or "<<" not in lines[0]:
        return text
    marker = lines[0].split("<<", 1)[1].strip().strip("'\"")
    marker = marker.lstrip("-")
    body: list[str] = []
    for line in lines[1:]:
        if line.strip().startswith(marker):
            break
        body.append(line)
    return "\n".join(body)


def _regex_subject(cmd: str) -> str:
    quoted = re.findall(r"(?:-m|--message)(?:\s+|=)(['\"])(.*?)\1", cmd, re.DOTALL)
    if quoted:
        message = quoted[0][1]
        if message.splitlines() and "<<" in message.splitlines()[0]:
            message = _heredoc_body(message)
        return _first_subject_line(message)
    heredoc = re.search(
        r"git\s+commit\b.*<<[-]?['\"]?(\w+)['\"]?\n(.*)", cmd, re.DOTALL
    )
    if not heredoc:
        return ""
    body = heredoc.group(2)
    end = re.search(r"^" + re.escape(heredoc.group(1)) + r"\s*$", body, re.MULTILINE)
    chunk = body[: end.start()] if end else body
    return _first_subject_line(chunk)


def _commit_message(args: list[str]) -> str:
    messages: list[str] = []
    index = 1
    while index < len(args):
        word = args[index]
        if word in {"-m", "--message"} and index + 1 < len(args):
            messages.append(args[index + 1])
            index += 2
            continue
        if word.startswith("--message="):
            messages.append(word.split("=", 1)[1])
            index += 1
            continue
        if (
            word.startswith("-")
            and not word.startswith("--")
            and "m" in word[1:]
            and index + 1 < len(args)
        ):
            messages.append(args[index + 1])
            index += 2
            continue
        index += 1
    return messages[0] if messages else ""


def _looks_expanded(message: str) -> bool:
    return "<<" in message or message.lstrip().startswith("$(")


def subject_from(cmd: str) -> str:
    saw_commit = False
    for segment in split_segments(cmd):
        git_args = git_command(argv_of(segment))
        if not git_args or git_args[0] != "commit":
            continue
        saw_commit = True
        message = _commit_message(git_args)
        if message:
            if _looks_expanded(message):
                fallback = _regex_subject(cmd)
                if fallback:
                    return fallback
            return _first_subject_line(message)
        if "--amend" in git_args and not re.search(r"(?:^|\s)-[A-Za-z]*m\b", segment):
            return ""
    if saw_commit or re.search(r"(^|[;&|]\s*)(?:\S+\s+)*git\s+commit\b", cmd):
        return _regex_subject(cmd)
    return ""


def _trailers(cmd: str, found: list[str]) -> None:
    lowered = cmd.lower()
    if (
        "co-authored-by:" in lowered
        or "generated with" in lowered
        or "generated-with" in lowered
    ):
        found.append("do not add Co-authored-by or Generated-with trailers")


def problems(cmd: str, subject: str) -> list[str]:
    found: list[str] = []
    if not subject:
        return found
    if subject.startswith("Merge ") or REVERT.match(subject):
        _trailers(cmd, found)
        return found
    match = subject_pattern().match(subject)
    if not match:
        found.append(
            "subject is not `<emoji> <type>(<scope>): <lower-case imperative>`"
        )
    elif match.group("emoji").isascii():
        found.append("first token must be a Unicode gitmoji, not a shortcode or a word")
    if subject.endswith("."):
        found.append("no trailing period")
    if len(subject) > 72:
        found.append(f"subject is over 72 characters ({len(subject)})")
    _trailers(cmd, found)
    return found


def self_test() -> int:
    def text(cmd: str) -> str:
        return "; ".join(problems(cmd, subject_from(cmd)))

    wip = text('git commit -am "WIP"')
    assert "subject is not" in wip, wip
    nested = text('git -C sub commit -m "bad"')
    assert "subject is not" in nested, nested
    amend = text('git commit --amend -am "WIP"')
    assert "subject is not" in amend, amend
    assert text("git commit --amend") == ""
    assert text('git commit -m ""') == ""
    good = 'git commit -m "✨ feat(api): add registration"'
    assert text(good) == ""
    trailer = text(
        'git commit -m "✨ feat(api): add registration" -m "Co-Authored-By: Claude"'
    )
    assert "Co-authored-by" in trailer, trailer
    generated = text(
        'git commit -m "✨ feat(api): add registration\n\nGenerated with Claude"'
    )
    assert "Generated-with" in generated, generated
    revert = "git commit -m 'Revert \"✨ feat(api): add registration\"'"
    assert text(revert) == "", text(revert)
    assert text("git status") == ""
    assert text("git push --no-verify") == ""
    for commit_type in load_types():
        subject = f"✨ {commit_type}(api): add a check"
        assert text(f'git commit -m "{subject}"') == "", commit_type
    heredoc = """git commit -m "$(cat <<'EOF'
✨ feat(api): add registration

body
EOF
)"
"""
    assert text(heredoc) == "", text(heredoc)
    print("commit-style self-test ok")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    cmd = command_from(sys.stdin.read())
    found = problems(cmd, subject_from(cmd))
    if not found:
        return 0
    reason = "[commit-style] " + "; ".join(found) + ". Example: " + EXAMPLE
    if "--strict" in argv:
        sys.stderr.write(reason + "\n")
        emit("PreToolUse", reason, decision="deny")
        return 2
    emit("PreToolUse", reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

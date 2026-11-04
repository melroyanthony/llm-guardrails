#!/usr/bin/env python3
"""Classify destructive git commands. Ordinary git push is allowed.

Each shell segment is checked on its own. --no-verify counts only as an
argument of commit, push, merge, or rebase, not inside a message or a later
command. A refspec that starts with + is a force-push.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_segments import argv_of, git_command, split_segments
from hook_output import emit

NO_VERIFY_COMMANDS = {"commit", "push", "merge", "rebase"}


def _flags(args: list[str]) -> list[str]:
    found: list[str] = []
    index = 0
    while index < len(args):
        word = args[index]
        if word in {"-C", "-c", "--git-dir", "--work-tree"} and index + 1 < len(args):
            index += 2
            continue
        if word.startswith("-"):
            found.append(word)
        index += 1
    return found


def classify_git(args: list[str]) -> str | None:
    if not args:
        return None
    command, rest = args[0], args[1:]
    flags = _flags(rest)
    if command == "push":
        if any(flag.startswith("--force") for flag in flags):
            return "force-push"
        for flag in flags:
            if flag.startswith("-") and not flag.startswith("--") and "f" in flag[1:]:
                return "force-push"
        if any(word.startswith("+") and word != "+" for word in rest):
            return "force-push"
    if command in NO_VERIFY_COMMANDS and "--no-verify" in flags:
        return "skip-hooks"
    if command == "reset" and "--hard" in flags:
        return "reset-hard"
    if command == "clean":
        for flag in flags:
            if flag.startswith("-") and not flag.startswith("--") and "f" in flag[1:]:
                return "clean-force"
    if command == "branch" and "-D" in flags:
        return "branch-delete-force"
    if command in {"checkout", "restore"} and "." in rest:
        return "discard-worktree"
    return None


def classify(command: str) -> str | None:
    for segment in split_segments(command):
        git_args = git_command(argv_of(segment))
        if not git_args:
            continue
        found = classify_git(git_args)
        if found:
            return found
    return None


def command_from(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(data, dict):
        tool_input = data.get("tool_input") or {}
        if isinstance(tool_input, dict):
            return str(tool_input.get("command") or "")
    return raw


def self_test() -> int:
    assert classify("git push -u origin branch") is None
    assert classify("git push origin feat/x && rm -f /tmp/x.log") is None
    assert classify("git clean -n && ls -lf") is None
    assert classify('git commit -m "docs: note --no-verify"') is None
    assert classify("npm test -- --no-verify") is None
    assert classify("git push --force origin main") == "force-push"
    assert classify("git push -f") == "force-push"
    assert classify("git push -uf origin main") == "force-push"
    assert classify("git push --force-with-lease") == "force-push"
    assert classify("git push origin +main") == "force-push"
    assert classify("git checkout -- .") == "discard-worktree"
    assert classify("git -C repo reset --hard") == "reset-hard"
    assert (
        classify("git commit --no-verify -m '✨ feat(api): add registration'")
        == "skip-hooks"
    )
    assert classify("git push --no-verify") == "skip-hooks"
    assert classify("git clean -fd") == "clean-force"
    assert classify("git branch -D old") == "branch-delete-force"
    print("git_guardrails self-test ok")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    found = classify(command_from(sys.stdin.read()))
    if not found:
        return 0
    reason = (
        f"[git-guardrails] {found}. Ask the human before force-push, --no-verify, "
        "or a destructive git command."
    )
    emit("PreToolUse", reason, decision="ask")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

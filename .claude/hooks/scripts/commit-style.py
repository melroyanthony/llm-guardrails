#!/usr/bin/env python3
"""Warn or deny a git commit whose subject misses the hybrid convention."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TYPES_PATH = ROOT / "scripts" / "commit-types.json"
MESSAGE = re.compile(r"""(?:-m|--message)(?:=|\s+)(?:"([^"]+)"|'([^']+)'|(\S+))""")


def subject_pattern() -> re.Pattern[str]:
    """Subject regex built from scripts/commit-types.json."""
    names = [item["name"] for item in json.loads(TYPES_PATH.read_text(encoding="utf-8"))["types"]]
    joined = "|".join(names)
    return re.compile(rf"^\S+\s+(?:{joined})(\([a-z0-9][a-z0-9._-]*\))?(!)?: [a-z].*")


def commit_subject(command: str) -> str | None:
    """Return the -m subject when this command is a git commit."""
    if not re.search(r"\bgit\s+commit\b", command):
        return None
    match = MESSAGE.search(command)
    if match is None:
        return None
    return next(group for group in match.groups() if group)


def decision(command: str, profile: str | None = None) -> tuple[int, str | None]:
    """Return (exit code, warning). Exit 2 denies. Standard only warns."""
    subject = commit_subject(command)
    if subject is None or subject_pattern().match(subject):
        return 0, None
    message = f"commit subject does not match <emoji> <type>(<scope>): <imperative>: {subject}"
    mode = profile if profile is not None else os.environ.get("SDLC_HOOK_PROFILE", "standard")
    if mode == "strict":
        return 2, message
    if mode == "minimal":
        return 0, None
    return 0, message


def main() -> int:
    """Read the hook payload and apply the profile."""
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    code, warning = decision(command)
    if warning:
        print(warning, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

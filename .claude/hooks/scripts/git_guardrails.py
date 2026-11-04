#!/usr/bin/env python3
"""Ask before destructive git commands. A plain git push is allowed."""

from __future__ import annotations

import json
import re
import sys

FORCE_PUSH = re.compile(r"\bgit\s+push\b[^\n]*--force\b|\bgit\s+push\b[^\n]*--force-with-lease\b")
FORCE_FLAG = re.compile(r"\bgit\s+push\b[^\n]*(?:^|\s)-f(?:\s|$)")
PLUS_REF = re.compile(r"\bgit\s+push\b[^\n]*\s\+\S+")
RESET_HARD = re.compile(r"\bgit\s+reset\b[^\n]*--hard\b")
CLEAN_FORCE = re.compile(r"\bgit\s+clean\b[^\n]*\s-[a-zA-Z]*f")
BRANCH_DELETE = re.compile(r"\bgit\s+branch\b[^\n]*(?:^|\s)-D(?:\s|$)")


def needs_ask(command: str) -> str | None:
    """Return a reason to ask, or None when the command may run."""
    if "git" not in command:
        return None
    if "--no-verify" in command:
        return "git command skips hooks (--no-verify)"
    if FORCE_PUSH.search(command) or FORCE_FLAG.search(command) or PLUS_REF.search(command):
        return "force-push"
    if RESET_HARD.search(command):
        return "git reset --hard"
    if CLEAN_FORCE.search(command):
        return "git clean -f"
    if BRANCH_DELETE.search(command):
        return "git branch -D"
    return None


def hook_response(command: str) -> dict | None:
    """Claude Code PreToolUse payload, or None to allow."""
    reason = needs_ask(command)
    if reason is None:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"git guardrail: {reason}",
        }
    }


def main() -> int:
    """Read the hook payload on stdin and print a decision when needed."""
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    response = hook_response(command)
    if response is not None:
        print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

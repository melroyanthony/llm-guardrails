#!/usr/bin/env python3
"""Block publish and deploy commands when stack guardrails are opted in.

Opt in with `.claude/stack-guardrails.enabled` at the git root, or
`SDLC_STACK_GUARDRAILS=1`. The block exits 2 in every profile, including
standard. Dry-run publishes are allowed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

PUBLISH = re.compile(r"\b(?:npm|pnpm|yarn|uv)\s+publish\b|\bchangeset\s+publish\b")
RAILWAY = re.compile(
    r"\brailway\s+(?:up|deploy|redeploy|down)\b"
    r"|\brailway\s+variables\s+--set\b"
    r"|\brailway\s+config\s+apply\b"
    r"|\brailway\s+config\s+migrate\b[^\n]*--apply\b"
)
LOCKFILE = re.compile(r"(?:^|/)(?:uv\.lock|pnpm-lock\.yaml)$")


def enabled(start: Path | None = None) -> bool:
    """True when the repo opted in or the environment variable is set."""
    if os.environ.get("SDLC_STACK_GUARDRAILS") == "1":
        return True
    here = start or Path.cwd()
    for parent in [here, *here.parents]:
        marker = parent / ".claude" / "stack-guardrails.enabled"
        if marker.is_file():
            return True
        if (parent / ".git").exists():
            return marker.is_file()
    return False


def blocked_reason(command: str) -> str | None:
    """Return why a shell command is blocked, ignoring publish dry-runs."""
    if not enabled():
        return None
    if PUBLISH.search(command) and "--dry-run" not in command:
        return "package publish is blocked by stack guardrails"
    if RAILWAY.search(command):
        return "railway deploy is blocked by stack guardrails"
    return None


def lockfile_warning(path: str) -> str | None:
    """Warn on a hand edit of a lockfile this harness does not regenerate."""
    if not enabled():
        return None
    if LOCKFILE.search(path):
        return f"hand edit of {path}; prefer the package manager that owns it"
    return None


def main() -> int:
    """Apply the pre-bash block or the post-edit lockfile warning."""
    payload = json.load(sys.stdin)
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input", {})
    if tool == "Bash":
        reason = blocked_reason(str(tool_input.get("command", "")))
        if reason:
            print(reason, file=sys.stderr)
            return 2
        return 0
    path = str(tool_input.get("file_path", ""))
    warning = lockfile_warning(path)
    if warning:
        print(warning, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

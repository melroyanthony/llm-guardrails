#!/usr/bin/env python3
"""Print the file path from a Claude Code hook payload on stdin."""

from __future__ import annotations

import json
import sys


def file_path(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if path:
        return str(path)
    edits = tool_input.get("edits") or []
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and edit.get("file_path"):
                return str(edit["file_path"])
    return ""


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    sys.stdout.write(file_path(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

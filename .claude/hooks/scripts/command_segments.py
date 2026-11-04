#!/usr/bin/env python3
"""Split a shell command into segments and argv, without executing it.

Separators are &&, ||, ;, and |. Quotes are respected, so a flag inside a
commit message is not a flag. Used by the git and stack guardrail hooks.
"""

from __future__ import annotations

import os
import re
import shlex


def split_segments(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            buf.append(char)
            if char == quote and command[index - 1] != "\\":
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            index += 1
            continue
        if char == ";":
            parts.append("".join(buf))
            buf = []
            index += 1
            continue
        if command.startswith("&&", index) or command.startswith("||", index):
            parts.append("".join(buf))
            buf = []
            index += 2
            continue
        if char == "|":
            parts.append("".join(buf))
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    if buf:
        parts.append("".join(buf))
    return [part.strip() for part in parts if part.strip()]


def argv_of(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def git_command(argv: list[str]) -> list[str] | None:
    """Return [subcommand, ...args] after git's global options, or None."""
    index = 0
    while index < len(argv) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[index]):
        index += 1
    if index >= len(argv) or os.path.basename(argv[index]) != "git":
        return None
    index += 1
    valued = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
    while index < len(argv):
        word = argv[index]
        if word in valued and index + 1 < len(argv):
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        return argv[index:]
    return None

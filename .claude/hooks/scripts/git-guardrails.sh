#!/usr/bin/env bash
# PreToolUse wrapper. stdin is the Claude Code hook payload.
exec python3 "$(dirname "$0")/git_guardrails.py"

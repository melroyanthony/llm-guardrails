#!/usr/bin/env bash
# PreToolUse and PostToolUse wrapper. stdin is the Claude Code hook payload.
exec python3 "$(dirname "$0")/stack_guardrails.py"

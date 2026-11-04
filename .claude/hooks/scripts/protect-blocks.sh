#!/usr/bin/env bash
# .claude/hooks/scripts/protect-blocks.sh
#
# PreToolUse hook: warn when editing files that contain agent-protect annotations.
# Does NOT modify file content — just alerts the agent that protected regions exist.
# Exits 0 in standard mode (non-blocking warning to stderr).
# Exits 2 in strict mode (blocks the edit).
# Controlled by SDLC_HOOK_PROFILE: minimal | standard (default) | strict.
#
# Protected blocks are annotated with:
#   # agent-protect-start: <reason>
#   ... protected code ...
#   # agent-protect-end
#
# Works with any comment syntax: #, //, /*, --, <!--

set -euo pipefail

# Hook profile
SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[protect-blocks] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
    SDLC_HOOK_PROFILE="standard"
    ;;
esac
if [ "$SDLC_HOOK_PROFILE" = "minimal" ]; then
  exit 0
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${1:-}" ]; then
  FILE="$1"
elif [ -n "${CLAUDE_FILE_PATH:-}" ]; then
  FILE="$CLAUDE_FILE_PATH"
elif [ -t 0 ]; then
  FILE=""
else
  FILE="$(python3 "$DIR/hook_file.py" || true)"
fi

if [ -z "$FILE" ]; then
  exit 0
fi

# Resolve to absolute path
if [ "${FILE#/}" = "$FILE" ]; then
  FILE="$(pwd)/$FILE"
fi

# Only check files that exist
if [ ! -f "$FILE" ]; then
  exit 0
fi

# Check for agent-protect-start annotations
PROTECTED_COUNT=$(grep -c 'agent-protect-start' "$FILE" 2>/dev/null || true)

if [ "$PROTECTED_COUNT" -gt 0 ]; then
  # Extract the reasons for protection
  REASONS=$(grep 'agent-protect-start' "$FILE" 2>/dev/null | sed 's/.*agent-protect-start[[:space:]]*:[[:space:]]*/  - /' | sed 's/[[:space:]]*\*\///' | sed 's/[[:space:]]*-->//' || true)

  echo "[protect-blocks] This file contains ${PROTECTED_COUNT} protected region(s):" >&2
  echo "$REASONS" >&2
  echo "[protect-blocks] Do NOT modify code between agent-protect-start and agent-protect-end markers." >&2

  if [ "$SDLC_HOOK_PROFILE" = "strict" ]; then
    echo "[protect-blocks] BLOCKED — file contains protected regions. Review annotations before editing." >&2
    exit 2
  else
    echo "[protect-blocks] WARNING — proceed with caution. Protected regions must not be modified." >&2
  fi
fi

exit 0

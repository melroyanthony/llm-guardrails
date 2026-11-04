#!/usr/bin/env bash
# Opt-in PreToolUse / PostToolUse hook. See stack_guardrails.py.
# Phase is the first argument: pre | post. Never deploys or pushes.
#
# Opt-in and the minimal profile are decided here, before Python starts.
# Python 3.9 and 3.10 have no tomllib, and a missing python3 used to exit 127
# on every Bash/Edit/Write even when the guardrails were off.

# bash 3.2. Do not use pipefail: the exit code must be Python's, including 0
# when guardrails are off. Stdin is read first so the hook runner is not
# SIGPIPE'd.

set -eu

PHASE="${1:-pre}"
DIR="$(cd "$(dirname "$0")" && pwd)"
SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"

if [ -t 0 ]; then
  INPUT=""
else
  INPUT=$(cat || true)
fi

if [ -z "$INPUT" ] && [ -z "${CLAUDE_FILE_PATH:-}" ]; then
  exit 0
fi

if [ "$SDLC_HOOK_PROFILE" = "minimal" ]; then
  exit 0
fi

enabled=0
case "${SDLC_STACK_GUARDRAILS:-}" in
  1|true|TRUE|on|ON|yes|YES) enabled=1 ;;
  0|false|FALSE|off|OFF|no|NO) enabled=0 ;;
  *)
    root="${CLAUDE_PROJECT_DIR:-}"
    if [ -z "$root" ]; then
      root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    fi
    if [ -f "$root/.claude/stack-guardrails.enabled" ]; then
      enabled=1
    fi
    ;;
esac

if [ "$enabled" -eq 0 ]; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  if printf '%s' "$INPUT" | grep -Eq 'railway[[:space:]]+(up|deploy|redeploy|down)|[[:space:]]publish([[:space:]]|$)'; then
    echo "[stack-guardrails] BLOCKED: python3 is not on PATH, so this deploy or publish was refused." >&2
    exit 2
  fi
  exit 0
fi

set +e
printf '%s' "$INPUT" | python3 "$DIR/stack_guardrails.py" "$PHASE"
status=$?
exit "$status"

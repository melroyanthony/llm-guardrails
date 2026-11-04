#!/usr/bin/env bash
# PreToolUse hook: check `git commit` subjects against the hybrid style.
#
# <emoji> <type>(<scope>): <lower-case imperative subject>
#
# The rule is the one in melroyanthony/crabcake AGENTS.md (tiangolo gitmoji
# plus Conventional Commits). Standard mode prints hook JSON so the model
# sees the warning. Strict mode denies (exit 2). Does not rewrite the
# message and does not push.
#
# SDLC_HOOK_PROFILE: minimal | standard (default) | strict.

set -euo pipefail

SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[commit-style] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
    SDLC_HOOK_PROFILE="standard"
    ;;
esac

if [ "$SDLC_HOOK_PROFILE" = "minimal" ]; then
  exit 0
fi

if [ -t 0 ]; then
  exit 0
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$SDLC_HOOK_PROFILE" = "strict" ]; then
  exec python3 "$DIR/commit-style.py" --strict
fi
exec python3 "$DIR/commit-style.py"

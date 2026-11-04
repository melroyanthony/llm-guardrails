#!/usr/bin/env bash
# PreToolUse hook: ask before destructive git operations.
#
# Idea adapted from mattpocock/skills git-guardrails-claude-code (MIT,
# https://github.com/mattpocock/skills). Ordinary `git push` stays allowed.
# Flagged: force-push (including a +refspec or a short -f cluster), --no-verify
# on commit/push/merge/rebase, reset --hard, clean -f, branch -D, and
# discarding the work tree. Each shell segment is judged on its own.
#
# Prints Claude Code hook JSON with permissionDecision "ask" and exits 0.
# Exit 2 would hide that JSON. minimal exits 0 before Python.
# SDLC_HOOK_PROFILE: minimal | standard (default) | strict.

set -euo pipefail

SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[git-guardrails] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
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
exec python3 "$DIR/git_guardrails.py"

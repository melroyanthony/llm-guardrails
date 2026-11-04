#!/usr/bin/env bash
# .claude/hooks/scripts/commit-reminder.sh
#
# Stop hook: check for uncommitted changes and remind the user to commit
# before the session ends.
#
# Also performs a lightweight scan of staged/unstaged files for leftover
# debug statements (console.log, debugger, print()).
#
# Exits 0 in standard mode (non-blocking warnings to stderr).
# Exits 2 in strict mode (blocks the operation on findings).
# Controlled by SDLC_HOOK_PROFILE: minimal | standard (default) | strict.

set -euo pipefail

# Hook profile: minimal (skip), standard (warn), strict (block on findings)
SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[commit-reminder] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
    SDLC_HOOK_PROFILE="standard"
    ;;
esac
if [[ "$SDLC_HOOK_PROFILE" == "minimal" ]]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

if [[ -z "$REPO_ROOT" ]]; then
  # Not inside a git repository — nothing to do
  exit 0
fi

# ── 1. Uncommitted changes reminder ─────────────────────────────────────────

PORCELAIN="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)"

if [[ -n "$PORCELAIN" ]]; then
  CHANGED_COUNT="$(echo "$PORCELAIN" | grep -c '.' || true)"
  echo "" >&2
  echo "[commit-reminder] You have $CHANGED_COUNT file(s) with uncommitted changes:" >&2
  echo "$PORCELAIN" | awk 'NR<=20{print "  "$0}' >&2
  if [[ "$CHANGED_COUNT" -gt 20 ]]; then
    echo "  ... and $((CHANGED_COUNT - 20)) more" >&2
  fi
  echo "" >&2
  echo "  Consider committing your work:" >&2
  echo "    git add <files>" >&2
  echo "    git commit -m \"<message>\"" >&2
  echo "" >&2

  # Strict mode: block if there are uncommitted changes
  if [[ "$SDLC_HOOK_PROFILE" == "strict" ]]; then
    echo "[commit-reminder] STRICT MODE: blocking due to uncommitted changes." >&2
    exit 2
  fi
fi

# ── 2. Debug artifact scan on modified files ────────────────────────────────

# Gather all modified files (staged + unstaged, tracked by git)
MODIFIED_FILES=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  F="$REPO_ROOT/$line"
  [[ -f "$F" ]] && MODIFIED_FILES+=("$F")
done < <(
  git -C "$REPO_ROOT" diff --name-only 2>/dev/null
  git -C "$REPO_ROOT" diff --name-only --cached 2>/dev/null
)

# If no modified files, skip debug scan
if [[ ${#MODIFIED_FILES[@]} -eq 0 ]]; then
  exit 0
fi

# Deduplicate using sort -u
UNIQUE=()
while IFS= read -r F; do
  [[ -n "$F" ]] && UNIQUE+=("$F")
done < <(printf '%s\n' "${MODIFIED_FILES[@]}" | sort -u)

if [[ ${#UNIQUE[@]} -eq 0 ]]; then
  exit 0
fi

DEBUG_WARNINGS=()

for FILE in "${UNIQUE[@]}"; do
  EXT="${FILE##*.}"
  BASENAME="$(basename "$FILE")"

  case "$EXT" in
    ts|tsx|js|jsx|mjs|cjs)
      if grep -qn "console\.log\|debugger" "$FILE" 2>/dev/null; then
        DEBUG_WARNINGS+=("$FILE: contains console.log or debugger statement(s)")
      fi
      ;;
    py)
      if [[ "$BASENAME" != test_* ]] && [[ "$BASENAME" != *_test.py ]]; then
        if grep -qn "^[[:space:]]*print(" "$FILE" 2>/dev/null; then
          DEBUG_WARNINGS+=("$FILE: contains print() statement(s) in production code")
        fi
      fi
      ;;
  esac
done

if [[ ${#DEBUG_WARNINGS[@]} -gt 0 ]]; then
  echo "[commit-reminder] Leftover debug statements detected in modified files:" >&2
  for W in "${DEBUG_WARNINGS[@]}"; do
    echo "  - $W" >&2
  done
  echo "  Clean these up before committing to keep production code tidy." >&2
  echo "" >&2

  # Strict mode: block the operation on any finding
  if [[ "$SDLC_HOOK_PROFILE" == "strict" ]]; then
    echo "[commit-reminder] STRICT MODE: blocking due to debug artifacts in modified files." >&2
    exit 2
  fi
fi

exit 0

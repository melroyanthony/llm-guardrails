#!/usr/bin/env bash
# .claude/hooks/scripts/debug-check.sh
#
# PostToolUse hook (Edit): scan recently modified files for debug artifacts
# that should not land in production code.
#
# Scans for:
#   - console.log / debugger in .ts/.tsx/.js/.jsx files
#   - print( in .py files (excluding test files)
#   - TODO / FIXME markers in any modified file
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
    echo "[debug-check] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
    SDLC_HOOK_PROFILE="standard"
    ;;
esac
if [[ "$SDLC_HOOK_PROFILE" == "minimal" ]]; then
  exit 0
fi

# Collect files to inspect: hook JSON file_path, then CLAUDE_FILE_PATH,
# then git diff.
FILES=()
DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_FILE="${1:-${CLAUDE_FILE_PATH:-}}"
if [ -z "$HOOK_FILE" ] && [ ! -t 0 ]; then
  HOOK_FILE="$(python3 "$DIR/hook_file.py" || true)"
fi

if [ -n "$HOOK_FILE" ] && [ -f "$HOOK_FILE" ]; then
  FILES+=("$HOOK_FILE")
else
  # Read git-tracked changed files (unstaged + staged)
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    F="$REPO_ROOT/$line"
    [[ -f "$F" ]] && FILES+=("$F")
  done < <(git -C "${REPO_ROOT}" diff --name-only 2>/dev/null; git -C "${REPO_ROOT}" diff --name-only --cached 2>/dev/null)
fi

# Deduplicate (bash 3.2-compatible: no associative arrays required)
UNIQUE=()
for F in "${FILES[@]:-}"; do
  [[ -z "$F" ]] && continue
  ALREADY_SEEN=0
  if [[ ${#UNIQUE[@]} -gt 0 ]]; then
    for U in "${UNIQUE[@]}"; do
      if [[ "$U" == "$F" ]]; then
        ALREADY_SEEN=1
        break
      fi
    done
  fi
  if [[ "$ALREADY_SEEN" -eq 0 ]]; then
    UNIQUE+=("$F")
  fi
done
if [[ ${#UNIQUE[@]} -gt 0 ]]; then
  FILES=("${UNIQUE[@]}")
else
  FILES=()
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  exit 0
fi

WARNINGS=()

for FILE in "${FILES[@]}"; do
  EXT="${FILE##*.}"
  BASENAME="$(basename "$FILE")"

  case "$EXT" in
    ts|tsx|js|jsx|mjs|cjs)
      # console.log — noisy in production; should use structured logger
      if grep -qn "console\.log" "$FILE" 2>/dev/null; then
        LINES="$(grep -n "console\.log" "$FILE" | awk 'NR<=5{print "    "$0}')"
        WARNINGS+=("console.log found in $FILE:\n$LINES")
      fi
      # debugger statement — must never ship
      if grep -qwn "debugger" "$FILE" 2>/dev/null; then
        LINES="$(grep -wn "debugger" "$FILE" | awk 'NR<=5{print "    "$0}')"
        WARNINGS+=("debugger statement found in $FILE:\n$LINES")
      fi
      ;;

    py)
      # Skip test files (test_*.py and *_test.py)
      if [[ "$BASENAME" != test_* ]] && [[ "$BASENAME" != *_test.py ]]; then
        if grep -qn "^[[:space:]]*print(" "$FILE" 2>/dev/null; then
          LINES="$(grep -n "^[[:space:]]*print(" "$FILE" | awk 'NR<=5{print "    "$0}')"
          WARNINGS+=("print() statement found in production Python file $FILE:\n$LINES")
        fi
      fi
      ;;
  esac

  # TODO / FIXME markers — flag in all supported source files
  case "$EXT" in
    py|ts|tsx|js|jsx|mjs|cjs|go|sh|yaml|yml|json)
      if grep -qwiEn "TODO|FIXME" "$FILE" 2>/dev/null; then
        LINES="$(grep -wiEn "TODO|FIXME" "$FILE" | awk 'NR<=5{print "    "$0}')"
        WARNINGS+=("TODO/FIXME marker found in $FILE:\n$LINES")
      fi
      ;;
  esac
done

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  echo "" >&2
  echo "[debug-check] Debug artifact warnings (review before shipping):" >&2
  for W in "${WARNINGS[@]}"; do
    echo -e "  - $W" >&2
  done
  echo "" >&2

  # Strict mode: block the operation on any finding
  if [[ "$SDLC_HOOK_PROFILE" == "strict" ]]; then
    echo "[debug-check] STRICT MODE: blocking operation due to debug artifacts." >&2
    exit 2
  fi
fi

exit 0

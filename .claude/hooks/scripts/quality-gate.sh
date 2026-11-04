#!/usr/bin/env bash
# .claude/hooks/scripts/quality-gate.sh
#
# PreToolUse hook: detect file language and run appropriate formatter/linter.
# Exits 0 in standard mode (non-blocking warnings to stderr).
# Exits 2 in strict mode (blocks the operation on findings).
# Controlled by SDLC_HOOK_PROFILE: minimal | standard (default) | strict.
#
# Usage: called automatically by Claude Code before Edit or Write tool use.
# The path of the file being modified is passed as $CLAUDE_FILE_PATH by Claude Code,
# with a fallback to $1 for manual invocation.

set -euo pipefail

# Hook profile: minimal (skip), standard (warn), strict (block on findings)
SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[quality-gate] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
    SDLC_HOOK_PROFILE="standard"
    ;;
esac
if [[ "$SDLC_HOOK_PROFILE" == "minimal" ]]; then
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

if [[ -z "$FILE" ]]; then
  exit 0
fi

# Resolve to absolute path relative to repo root when the path is relative
if [[ "$FILE" != /* ]]; then
  FILE="$(pwd)/$FILE"
fi

# Only check files that actually exist on disk
if [[ ! -f "$FILE" ]]; then
  exit 0
fi

EXT="${FILE##*.}"
WARNINGS=()

case "$EXT" in
  py)
    # Python: ruff check (lint) + ruff format --check
    if command -v ruff &>/dev/null; then
      if ! ruff check --quiet "$FILE" >/dev/null 2>&1; then
        WARNINGS+=("ruff lint issues found in $FILE — run: ruff check --fix $FILE")
      fi
      if ! ruff format --check --quiet "$FILE" >/dev/null 2>&1; then
        WARNINGS+=("ruff format issues found in $FILE — run: ruff format $FILE")
      fi
    elif command -v uv &>/dev/null; then
      if ! uv run ruff check --quiet "$FILE" >/dev/null 2>&1; then
        WARNINGS+=("ruff lint issues found in $FILE — run: uv run ruff check --fix $FILE")
      fi
      if ! uv run ruff format --check --quiet "$FILE" >/dev/null 2>&1; then
        WARNINGS+=("ruff format issues found in $FILE — run: uv run ruff format $FILE")
      fi
    fi
    ;;

  ts|tsx|js|jsx|mjs|cjs)
    # TypeScript/JavaScript: prefer biome, fall back to prettier
    REPO_ROOT="$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null || dirname "$FILE")"
    if [[ -f "$REPO_ROOT/biome.json" ]] || [[ -f "$REPO_ROOT/biome.jsonc" ]]; then
      if command -v biome &>/dev/null; then
        if ! biome check --quiet "$FILE" 2>/dev/null; then
          WARNINGS+=("biome issues found in $FILE — run: biome check --apply $FILE")
        fi
      elif [[ -f "$REPO_ROOT/node_modules/.bin/biome" ]]; then
        if ! "$REPO_ROOT/node_modules/.bin/biome" check --quiet "$FILE" 2>/dev/null; then
          WARNINGS+=("biome issues found in $FILE — run: npx biome check --apply $FILE")
        fi
      fi
    else
      # Fall back to prettier
      if command -v prettier &>/dev/null; then
        if ! prettier --check --log-level silent "$FILE" 2>/dev/null; then
          WARNINGS+=("prettier format issues in $FILE — run: prettier --write $FILE")
        fi
      elif [[ -f "${REPO_ROOT:-$(pwd)}/node_modules/.bin/prettier" ]]; then
        if ! npx prettier --check --log-level silent "$FILE" 2>/dev/null; then
          WARNINGS+=("prettier format issues in $FILE — run: npx prettier --write $FILE")
        fi
      fi
    fi
    ;;

  go)
    # Go: gofmt -l prints files with issues; no output means clean
    if command -v gofmt &>/dev/null; then
      RESULT="$(gofmt -l "$FILE" 2>/dev/null)"
      if [[ -n "$RESULT" ]]; then
        WARNINGS+=("gofmt issues found in $FILE — run: gofmt -w $FILE")
      fi
    fi
    ;;

  *)
    # Unsupported extension — nothing to check
    exit 0
    ;;
esac

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  echo "" >&2
  echo "[quality-gate] Formatting/lint warnings:" >&2
  for W in "${WARNINGS[@]}"; do
    echo "  - $W" >&2
  done
  echo "" >&2

  # Strict mode: block the operation on any finding
  if [[ "$SDLC_HOOK_PROFILE" == "strict" ]]; then
    echo "[quality-gate] STRICT MODE: blocking operation due to lint/format issues." >&2
    exit 2
  fi
fi

exit 0

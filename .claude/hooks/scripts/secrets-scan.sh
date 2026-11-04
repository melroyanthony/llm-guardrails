#!/usr/bin/env bash
# .claude/hooks/scripts/secrets-scan.sh
#
# PostToolUse hook: scan written/edited files for hardcoded secrets.
# Exits 0 in standard mode (non-blocking warnings to stderr).
# Exits 2 in strict mode (blocks on secret findings, not .env warnings).
# Controlled by SDLC_HOOK_PROFILE: minimal | standard (default) | strict.
#
# Usage: called automatically by Claude Code after Edit or Write tool use.

set -euo pipefail

# Hook profile
SDLC_HOOK_PROFILE="${SDLC_HOOK_PROFILE:-standard}"
case "$SDLC_HOOK_PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[secrets-scan] WARNING: unknown SDLC_HOOK_PROFILE='$SDLC_HOOK_PROFILE', falling back to 'standard'." >&2
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

# Skip non-source files (binary, images, lockfiles)
BASENAME="$(basename "$FILE")"
case "$BASENAME" in
  *.lock|*.png|*.jpg|*.gif|*.ico|*.woff|*.woff2|*.ttf|*.eot|*.svg|*.pdf)
    exit 0
    ;;
  package-lock.json|pnpm-lock.yaml|go.sum)
    exit 0
    ;;
esac

# Skip .env.example and template files (they contain placeholders, not real secrets)
case "$BASENAME" in
  *.example|*.template|*.sample)
    exit 0
    ;;
esac

# Helper: return first matching line number only (never leak secret values)
# Usage: first_match_line "pattern" "file" [extra_grep_flags]
first_match_line() {
  local pattern="$1"
  local file="$2"
  local flags="${3:-}"
  if [[ -n "$flags" ]]; then
    grep -nE "$flags" "$pattern" "$file" 2>/dev/null | head -1 | cut -d: -f1 || true
  else
    grep -nE "$pattern" "$file" 2>/dev/null | head -1 | cut -d: -f1 || true
  fi
}

SECRET_FINDINGS=""
WARNINGS=""

# Pattern 1: API keys (generic, case-insensitive) — matches api_key, API_KEY, ApiKey, quoted and unquoted
API_KEY_PATTERN_Q="(api[_-]?key|apikey)[[:space:]]*[:=][[:space:]]*[\"'][A-Za-z0-9_-]{20,}[\"']"
API_KEY_PATTERN_UQ="(api[_-]?key|apikey)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_-]{20,}"
if grep -qinE "$API_KEY_PATTERN_Q" "$FILE" 2>/dev/null || grep -qinE "$API_KEY_PATTERN_UQ" "$FILE" 2>/dev/null; then
  LINE_NO=$(first_match_line "$API_KEY_PATTERN_Q" "$FILE" "-i")
  if [ -z "$LINE_NO" ]; then
    LINE_NO=$(first_match_line "$API_KEY_PATTERN_UQ" "$FILE" "-i")
  fi
  SECRET_FINDINGS="${SECRET_FINDINGS}  CRITICAL: Possible API key at line ${LINE_NO}\n"
fi

# Pattern 2: AWS access keys (AKIA...)
if grep -qnE 'AKIA[0-9A-Z]{16}' "$FILE" 2>/dev/null; then
  LINE_NO=$(first_match_line 'AKIA[0-9A-Z]{16}' "$FILE")
  SECRET_FINDINGS="${SECRET_FINDINGS}  CRITICAL: AWS access key at line ${LINE_NO}\n"
fi

# Pattern 3: Private keys
if grep -qn 'BEGIN.*PRIVATE KEY' "$FILE" 2>/dev/null; then
  LINE_NO=$(first_match_line 'BEGIN.*PRIVATE KEY' "$FILE")
  SECRET_FINDINGS="${SECRET_FINDINGS}  CRITICAL: Private key at line ${LINE_NO}\n"
fi

# Pattern 4: Password assignments — quoted values anywhere in source code
PWD_PATTERN_DQ='(password|passwd|pwd)[[:space:]]*[:=][[:space:]]*["][^"]{8,}["]'
# Exclude env lookups (os.getenv, process.env, ${...}) from quoted matches
PWD_MATCHES=$(grep -inE "$PWD_PATTERN_DQ" "$FILE" 2>/dev/null | grep -viE '(os\.getenv|process\.env|\$\{|getenv|environ)' || true)
if [ -n "$PWD_MATCHES" ]; then
  LINE_NO=$(echo "$PWD_MATCHES" | head -1 | cut -d: -f1)
  SECRET_FINDINGS="${SECRET_FINDINGS}  HIGH: Possible hardcoded password at line ${LINE_NO}\n"
fi
# Unquoted password pattern — only check .env-style files to reduce false positives
case "$BASENAME" in
  .env|.env.*|*.env)
    PWD_PATTERN_UQ='([a-z_]*password|[a-z_]*passwd|[a-z_]*pwd)[[:space:]]*=[[:space:]]*[^[:space:]"]{8,}'
    if [ -z "$LINE_NO" ] && grep -qinE "$PWD_PATTERN_UQ" "$FILE" 2>/dev/null; then
      LINE_NO=$(first_match_line "$PWD_PATTERN_UQ" "$FILE" "-i")
      SECRET_FINDINGS="${SECRET_FINDINGS}  HIGH: Possible hardcoded password at line ${LINE_NO}\n"
    fi
    ;;
esac

# Pattern 5: JWT tokens
if grep -qnE 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.' "$FILE" 2>/dev/null; then
  LINE_NO=$(first_match_line 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.' "$FILE")
  SECRET_FINDINGS="${SECRET_FINDINGS}  HIGH: JWT token at line ${LINE_NO}\n"
fi

# Pattern 6: Connection strings with credentials (per-line placeholder check)
CONN_PATTERN='(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@'
CONN_MATCHES=$(grep -nE "$CONN_PATTERN" "$FILE" 2>/dev/null | grep -vE '(user:pass|username:password|USER:PASS|\$\{|<user>|<pass>)' || true)
if [ -n "$CONN_MATCHES" ]; then
  LINE_NO=$(echo "$CONN_MATCHES" | head -1 | cut -d: -f1)
  SECRET_FINDINGS="${SECRET_FINDINGS}  HIGH: Connection string with credentials at line ${LINE_NO}\n"
fi

# Pattern 7: .env files (non-blocking warning, never blocks in strict mode)
case "$BASENAME" in
  .env|.env.local|.env.production|.env.staging)
    WARNINGS="${WARNINGS}  WARNING: Writing to ${BASENAME} — ensure this file is in .gitignore\n"
    ;;
esac

# Report warnings (never block)
if [ -n "$WARNINGS" ]; then
  printf "%b" "$WARNINGS" >&2
fi

# Report secret findings (block in strict mode)
if [ -n "$SECRET_FINDINGS" ]; then
  echo "[secrets-scan] Potential secrets detected in $(basename "$FILE"):" >&2
  printf "%b" "$SECRET_FINDINGS" >&2

  if [ "$SDLC_HOOK_PROFILE" = "strict" ]; then
    echo "[secrets-scan] BLOCKED — secrets detected. Use environment variables or a secret manager instead." >&2
    exit 2
  else
    echo "[secrets-scan] WARNING — review before committing. Use environment variables or a secret manager." >&2
  fi
fi

exit 0

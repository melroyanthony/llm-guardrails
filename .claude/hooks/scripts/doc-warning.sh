#!/usr/bin/env bash
# PreToolUse: tell the model when a Write, Edit, or MultiEdit touches docs.
# additionalContext is how the model sees it. stderr with exit 0 is not.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
FILE="${1:-${CLAUDE_FILE_PATH:-}}"
if [ -z "$FILE" ] && [ ! -t 0 ]; then
  FILE="$(python3 "$DIR/hook_file.py" || true)"
fi

case "$FILE" in
  *.md|*.rst|*.txt) ;;
  *) exit 0 ;;
esac

FILE="$FILE" DIR="$DIR" python3 - <<'PY'
import os
import sys

sys.path.insert(0, os.environ["DIR"])
from hook_output import emit

emit(
    "PreToolUse",
    "[doc-warning] Modifying documentation file: " + os.environ["FILE"],
)
PY

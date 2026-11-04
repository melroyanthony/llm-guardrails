#!/usr/bin/env bash
# Read-only verification harness for the stacks this repo knows how to detect.
# Does not push, publish, deploy, or rewrite lockfiles.
#
#   bash .claude/hooks/scripts/stack-verify.sh
#   bash .claude/hooks/scripts/stack-verify.sh --railway-plan
#
# --railway-plan runs `railway config plan` (preview only) when the CLI exists.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/stack_guardrails.py" --verify "$@"

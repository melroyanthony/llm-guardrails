#!/usr/bin/env bash
# Copy a local sdlc-claude-code-conf checkout into .claude/upstream for review.
#
# Usage: scripts/install-harness-from.sh /path/to/sdlc-claude-code-conf
#
# This does not clone, does not replace AGENTS.md, and does not touch
# .github/workflows/release.yml. Diff .claude/upstream/.claude against
# .claude/ before you copy anything over. The committed harness is the slim
# install. The conf catalog is not vendored into this repository.
set -euo pipefail

src="${1:-}"
if [[ -z "${src}" || ! -f "${src}/AGENTS.md" || ! -d "${src}/.claude" ]]; then
  echo "usage: scripts/install-harness-from.sh /path/to/sdlc-claude-code-conf" >&2
  exit 2
fi

dest=".claude/upstream"
rm -rf "${dest}"
mkdir -p "${dest}"
cp -a "${src}/AGENTS.md" "${dest}/AGENTS.md"
mkdir -p "${dest}/.claude"
cp -a "${src}/.claude/." "${dest}/.claude/"
echo "Copied into ${dest}. Diff ${dest}/.claude against .claude/ before replacing anything."

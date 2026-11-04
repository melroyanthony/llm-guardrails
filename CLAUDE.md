@AGENTS.md

# Claude Code

This file imports `AGENTS.md` with `@AGENTS.md`. The import is text, not a symlink.

## Hooks

`.claude/settings.json` holds project permissions and hooks. `SDLC_HOOK_PROFILE` is `minimal`, `standard` (default), or `strict`. Stack guardrails run only when `SDLC_STACK_GUARDRAILS=1` or `.claude/stack-guardrails.enabled` exists.

`.claude/hooks/hooks.json` is the plugin hook list from the conf. Its commands exit immediately when `${CLAUDE_PLUGIN_ROOT}` equals `${CLAUDE_PROJECT_DIR}`, so an in-repo plugin does not run the project hooks a second time. The project hooks in `settings.json` call `.claude/hooks/scripts/` directly.

`.claude/rules/` keeps path-scoped rules only (`coding-standards`, `security`). Behaviour, git, and the daily flow live in `AGENTS.md`. The generator does not emit an always-on Cursor or Copilot copy.

## Plugin

This repository vendors the harness. It is not the `sdlc-pipeline` plugin, so there is no `.claude-plugin/plugin.json` for a release to rewrite.

`agents` at the repo root is a symlink to `.claude/agents`. A Claude Code session follows that symlink. `claude plugin validate` does not.

## Models

Opus for architecture, review, and security. Sonnet for implementation. Haiku for mechanical tasks.

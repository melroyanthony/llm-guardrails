@AGENTS.md

## Models

Opus for architecture, review, and security. Sonnet for implementation. Haiku for mechanical tasks.

## Hooks

`SDLC_HOOK_PROFILE` is `minimal`, `standard` (default), or `strict`.
Git guardrails ask before a force-push, `--no-verify`, `reset --hard`, `clean -f`, or `branch -D`.
Commit subjects that miss the hybrid convention warn in `standard` and are denied in `strict`.
Stack guardrails are on because `.claude/stack-guardrails.enabled` is committed. They block package publish and Railway deploy, including in `standard`.

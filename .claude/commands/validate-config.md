---
description: "Validate skills/ and .claude/ configuration — frontmatter, invocation taxonomy, line budgets, shell compatibility, sync drift"
allowed-tools: Read, Glob, Grep, Bash
---

# Validate Config

Lint the canonical skill catalog and Claude adapter for correctness and consistency.

## Process

1. **Sync check** — run `bash scripts/sync-skills.sh --check`. Fail if `skills/` and `.claude/skills/` drift.

2. **Scan all agents** in `.claude/agents/*.md`:
   - Verify YAML frontmatter has required fields: `name`, `description`, `tools`
   - Verify `name` matches filename (e.g., `code-reviewer.md` has `name: code-reviewer`)
   - Verify `tools` field is a valid format (list or comma-separated)
   - Flag agents without `model` field as WARNING (recommended: opus/sonnet/haiku)
   - If `skills:` is present, each entry must match a skill directory `name` under `skills/` (not agent names)

3. **Scan all commands** in `.claude/commands/*.md`:
   - Verify YAML frontmatter has required fields: `description`
   - Verify `allowed-tools` is present and non-empty
   - Flag commands that reference agents not in `.claude/agents/`

4. **Scan skill definition files** in `skills/**/SKILL.md` (canonical; adapter is a mirror):
   - Verify YAML frontmatter has required fields: `name`, `description`
   - Verify `name` matches parent directory name
   - **Invocation**: if `disable-model-invocation: true`, description must NOT contain `Triggers on:` (user-invoked one-liner). If omitted, description SHOULD include trigger guidance.
   - **Line budget**: WARN if body >350 lines; CRITICAL if >500 lines
   - If `agents/openai.yaml` exists, verify `policy.allow_implicit_invocation` matches invocation mode
   - Skip supplemental docs (APPROACH.md, PATTERNS.md, MODELS.md, references/, templates) — no frontmatter required

5. **Scan all rules** in `.claude/rules/*.md`:
   - Verify YAML frontmatter has `description` and `paths`
   - Verify `paths` is a JSON array of glob patterns
   - `paths: ["**/*"]` means the rule always applies

6. **Scan all hook scripts** in `.claude/hooks/scripts/*.sh`:
   - Verify shebang line (`#!/usr/bin/env bash` or `#!/bin/bash`)
   - Check for bash 4+ features (`declare -A`, `mapfile`, `${var,,}`, `|&`)
   - Verify scripts are executable
   - Check for non-portable grep patterns: `\b`, `\s`, `\w`

7. **Check hooks config** in `.claude/settings.json`:
   - Verify `hooks` key exists
   - Verify each hook command references a script that exists

8. **AGENTS.md coverage** — skill names listed in the intent→skill table should exist under `skills/`

9. **Orphans**:
   - Skill directories under `skills/foundation|meta|engineering` without `SKILL.md`
   - Hook scripts not referenced in settings.json

## Output

```markdown
# Config Validation Report

## Summary
- Sync: OK / DRIFT
- Agents: N scanned, N issues
- Commands: N scanned, N issues
- Skills: N scanned, N issues (line-budget warnings/fails)
- Rules / Hooks: …

## Issues Found

### CRITICAL
- …

### WARNING
- …

## Result: PASS / FAIL
```

---
name: config-validation
description: |
  Validation rules for skills/ and .claude/ configuration: frontmatter schemas, invocation taxonomy, line budgets, shell compatibility, and naming.
  Use when checking configuration correctness or debugging frontmatter parsing issues.
  Triggers on: "validate config", "frontmatter", "config lint", "naming convention", "shell compatibility", "skill line budget".
---

# Config Validation Rules

## Canonical Skills Catalog

- Source of truth: `skills/**/SKILL.md`
- Claude adapter: `.claude/skills/` (must match via `bash scripts/sync-skills.sh --check`)
- Categories: `foundation/`, `meta/`, `engineering/`, `generated/`

## Agent Frontmatter Schema

Required fields:
```yaml
---
name: <string>          # Must match filename without .md
description: <string>   # What the agent does
tools: <list|string>    # Available tools (list or comma-separated)
---
```

Optional fields:
```yaml
model: <opus|sonnet|haiku>  # Model to use (defaults to project setting)
skills: <list|string>       # Skills this agent uses
```

### Validation Rules
- `name` must be kebab-case and match the filename
- `description` must be non-empty
- `tools` must contain only valid tool names: Read, Glob, Grep, Edit, Write, Bash, WebFetch, WebSearch, Agent, AskUserQuestion, Task, NotebookEdit (this list is non-exhaustive — check Claude Code docs for additions)
- If `model` is specified, must be one of: opus, sonnet, haiku

## Command Frontmatter Schema

Required fields:
```yaml
---
description: <string>       # What the command does
allowed-tools: <string>     # Comma-separated tool names
---
```

Optional fields:
```yaml
argument-hint: <string>     # Hint for $ARGUMENTS
```

### Validation Rules
- `description` must be non-empty
- `allowed-tools` must contain only valid tool names
- If command body references `$ARGUMENTS`, `argument-hint` should be present

## Skill Frontmatter Schema

Required fields:
```yaml
---
name: <string>          # Must match parent directory name
description: <string>   # Model-facing triggers OR human one-liner
---
```

Optional fields:
```yaml
disable-model-invocation: true   # User-invoked only (slash/human); strip trigger lists from description
allowed-tools: <string>          # Optional tool allow-list
```

### Invocation Taxonomy
- **Model-invoked** (default): omit `disable-model-invocation`. Description includes “Use when…” / “Triggers on:” branches. One trigger per branch; max 1024 characters.
- **User-invoked**: `disable-model-invocation: true`. Description is a single human-facing line — no trigger lists. May call model-invoked skills only.

### Line Budget (progressive disclosure)
| Severity | `SKILL.md` lines |
|----------|------------------|
| Target | ≤350 |
| Warning | 351–500 |
| Critical fail | >500 |

Bulk reference must live in sibling files or `references/` with one-level pointers from `SKILL.md`.

### Codex metadata (optional)
If `agents/openai.yaml` exists beside `SKILL.md`:
- User-invoked skills must set `policy.allow_implicit_invocation: false`
- Model-invoked skills must omit that false policy (or set `true`)

## Rule Frontmatter Schema

Required fields:
```yaml
---
description: <string>   # What this rule enforces
paths: <array>          # File patterns this rule applies to
---
```

### Validation Rules
- `paths` must be a JSON array of glob patterns
- `paths: ["**/*"]` means the rule always applies
- Glob patterns must be valid (e.g., `"**/*.py"`, `"**/*"`)

## Shell Script Compatibility (bash 3.2 — macOS default)

### Forbidden Features
| Feature | Bash Version | Portable Alternative |
|---------|-------------|---------------------|
| `declare -A` | 4.0+ | Use indexed arrays + loops |
| `mapfile` / `readarray` | 4.0+ | Use `while read` loop |
| `${var,,}` / `${var^^}` | 4.0+ | Use `tr '[:upper:]' '[:lower:]'` |
| `|&` (pipe stderr) | 4.0+ | Use `2>&1 |` |
| `[[ $var =~ regex ]]` with stored regex | 4.0+ | Inline the regex |
| `${!prefix@}` variable indirection | 4.0+ | Avoid or use eval |
| `coproc` | 4.0+ | Use named pipes |

### Forbidden grep Patterns
| Pattern | Issue | Portable Alternative |
|---------|-------|---------------------|
| `\b` | Not POSIX, backspace on macOS | `grep -w` or `[^[:alnum:]]` boundaries |
| `\s` | Not POSIX | `[[:space:]]` |
| `\w` | Not POSIX | `[[:alnum:]_]` |
| `\d` | Not POSIX | `[0-9]` |

### Required Script Properties
- Shebang: `#!/usr/bin/env bash` or `#!/bin/bash` (both accepted)
- Must exit 0 in standard mode (non-blocking warnings to stderr)
- May exit 2 in strict mode (`SDLC_HOOK_PROFILE=strict`) to block operations
- Warnings go to stderr (`>&2`)
- Must be executable (`chmod +x`)

## Naming Conventions

| Component | Convention | Example |
|-----------|-----------|---------|
| Agent files | kebab-case.md | `code-reviewer.md` |
| Command files | kebab-case.md | `create-pr.md` |
| Skill directories | kebab-case/ | `api-testing/` |
| Skill files | UPPER_CASE.md | `SKILL.md`, `PATTERNS.md` |
| Rule files | kebab-case.md | `coding-standards.md` |
| Hook scripts | kebab-case.sh | `quality-gate.sh` |

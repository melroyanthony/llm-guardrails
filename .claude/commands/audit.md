---
description: "Audit skills/ and .claude/ inventory against documentation — find count mismatches and undocumented components"
allowed-tools: Read, Glob, Grep, Bash
---

# Audit

Compare actual catalog and adapter contents against README.md, CLAUDE.md, and AGENTS.md.

## Process

1. **Sync check**: `bash scripts/sync-skills.sh --check`

2. **Count actual files**:
   - Agents: `ls .claude/agents/*.md | wc -l`
   - Commands: `ls .claude/commands/*.md | wc -l`
   - Skills (canonical): `find skills -name "SKILL.md" | wc -l`
   - Skills (adapter): `find -L .claude/skills -name "SKILL.md" | wc -l` — must match canonical. `-L` follows the flat symlinks
   - Rules: `ls .claude/rules/*.md | wc -l`
   - Hook scripts: `find .claude/hooks -name "*.sh" | wc -l`

3. **Extract documented counts** from README.md and CLAUDE.md; compare.

4. **AGENTS.md**: every skill path in the intent→skill table must exist under `skills/`.

5. **Find undocumented / missing** agents and commands vs docs.

6. **Plugin version**: `.claude-plugin/plugin.json` `version` must match `.version`.

## Output

```markdown
# Audit Report

## Inventory
| Component | Actual | README | CLAUDE.md | Status |
|-----------|--------|--------|-----------|--------|
| Agents | N | N | N | OK / DRIFT |
| Commands | N | N | N | OK / DRIFT |
| Skills (canonical) | N | N | N | OK / DRIFT |
| Skills sync | OK / DRIFT | | | |
| Rules | N | N | - | |
| Hooks | N | N | - | |
| Plugin version | x.y.z | .version | | |

## Undocumented / Missing
- …

## Recommendation
[What to update]
```

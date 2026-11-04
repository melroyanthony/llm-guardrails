---
description: "Save current session state for later resumption"
allowed-tools: Read, Glob, Grep, Write, Bash
---

# Save Session

Capture the current session state to enable seamless resumption.

## Process

1. **Load session-persistence skill** from `skills/meta/session-persistence/SKILL.md`
2. **Gather state**:
   - Current SDLC stage (from latest checkpoint file)
   - Files created/modified (from `git status` and `git diff --name-only`)
   - Recent decisions (from checkpoint files and ADRs)
   - Any known blockers
3. **Prompt for additional context**:
   - Ask the user: "Any additional context or notes to save?"
4. **Write session file** to `solution/checkpoints/session-{date}-{time}.md`
5. **Confirm save** with file path and summary

## Output
Session state file with all sections from the session-persistence skill.

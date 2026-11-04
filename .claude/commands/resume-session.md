---
description: "Resume from a previously saved session"
allowed-tools: Read, Glob, Grep, Bash, Agent, AskUserQuestion
---

# Resume Session

Resume work from a previously saved session.

## Process

1. **Find session files**: Glob for `solution/checkpoints/session-*.md`
2. **If multiple sessions exist**: Show the list and ask the user which to resume
3. **If one session exists**: Load it automatically
4. **Present briefing**:
   - What we were building
   - Current stage and status
   - Key decisions made
   - What worked and what didn't
   - Current blockers
   - The exact next step
5. **Verify file state**: Check that key files mentioned in the session still exist and haven't changed unexpectedly
6. **Confirm with user**: "Ready to continue from [next step]. Proceed?"
7. **Resume execution** from the identified next step

## Output
Structured briefing followed by continuation of the pipeline.

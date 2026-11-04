---
description: "Scaffold a new slash command from template"
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion
---

# Generate Command

Create a new slash command definition file with proper frontmatter and structure.

## Input
$ARGUMENTS — Command name and brief purpose. E.g., "lint — run linters on the codebase"

## Process

1. **Parse input**: Extract command name (kebab-case) and purpose from $ARGUMENTS
2. **If no input**, ask user:
   - "What should this command be named? (kebab-case, will become /name)"
   - "What should this command do? (one sentence)"
   - "Does it need to modify files, or is it read-only?"
3. **Check for conflicts**: Verify `.claude/commands/<name>.md` doesn't already exist
4. **Determine tools**: Based on purpose:
   - Modifies code → `Read, Write, Edit, Glob, Grep, Bash`
   - Analysis/review → `Read, Glob, Grep, Bash`
   - GitHub operations → `Read, Glob, Grep, Bash, AskUserQuestion`
   - Spawns agents → `Read, Glob, Grep, Bash, Agent`
5. **Generate file** at `.claude/commands/<name>.md`:

```markdown
---
description: "<purpose>"
allowed-tools: <tool-list>
---

# <Name>

<Purpose description>.

## Input
$ARGUMENTS — [What the user provides]. If empty, [default behavior].

## Process

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output
[What the command produces]
```

6. **Confirm creation**: "Command created at `.claude/commands/<name>.md`. You can now use `/<name>` in Claude Code."

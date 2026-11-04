---
description: "Scaffold a new agent definition from template"
allowed-tools: Read, Write, Glob, Grep, AskUserQuestion
---

# Generate Agent

Create a new agent definition file with proper frontmatter and structure.

## Input
$ARGUMENTS — Agent name and brief purpose. E.g., "api-monitor — monitors API health and uptime"

## Process

1. **Parse input**: Extract agent name (kebab-case) and purpose from $ARGUMENTS
2. **If no input**, ask user:
   - "What should this agent be named? (kebab-case, e.g., api-monitor)"
   - "What should this agent do? (one sentence)"
3. **Check for conflicts**: Verify `.claude/agents/<name>.md` doesn't already exist
4. **Determine model**: Based on purpose:
   - Architecture, review, security, complex reasoning → `opus`
   - Implementation, testing, standard workflows → `sonnet`
   - Mechanical, boilerplate, simple tasks → `haiku`
5. **Determine tools**: Based on purpose:
   - Needs to modify code → `Read, Glob, Grep, Edit, Write, Bash`
   - Read-only analysis → `Read, Glob, Grep, Bash`
   - Research-oriented → `Read, Glob, Grep, WebFetch, WebSearch`
6. **Generate file** at `.claude/agents/<name>.md`:

```markdown
---
name: <name>
description: "<purpose>"
tools: <tool-list>
model: <model>
---

# <Name> Agent

You are a [role description based on purpose].

## Input
- [What this agent receives]

## Process
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Format

    # <Name> Report
    ## Summary
    [Brief summary]
    ## Findings / Results
    [Details]
    ## Recommendations
    [Next steps]

## Rules
- [Key constraint 1]
- [Key constraint 2]
```

7. **Confirm creation** and suggest creating a matching command:
   - "Agent created at `.claude/agents/<name>.md`. Want me to create a matching `/name` command too?"

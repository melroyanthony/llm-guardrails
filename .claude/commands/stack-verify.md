---
description: "Run the opt-in stack verification harness (read-only; never deploys)"
argument-hint: "[--railway-plan]"
allowed-tools: Read, Glob, Grep, Bash
---

# Stack verify

Load `skills/foundation/stack-guardrails/SKILL.md` and run:

```bash
bash .claude/hooks/scripts/stack-verify.sh $ARGUMENTS
```

Report each stack's command, exit code, and the failure guidance the script printed. Do not follow a failure by publishing, deploying, force-pushing, or rewriting a lockfile yourself unless the user asks for that specific command.

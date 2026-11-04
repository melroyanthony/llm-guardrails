---
description: "Adversarial interview: relentlessly question a plan until shared understanding is reached"
argument-hint: "[path to plan or description]"
allowed-tools: Read, Glob, Grep, Bash, WebFetch, AskUserQuestion
model: opus
---

# Grill

Load and follow the model-invoked skill `skills/engineering/grilling/SKILL.md`.

## Input

$ARGUMENTS — path to a plan file, or a description of what to interrogate. If empty, ask the user what they want to be grilled on.

## After grilling

Recommend `/to-spec` if the user wants a durable artifact — do not run `to-spec` yourself (user-invoked).

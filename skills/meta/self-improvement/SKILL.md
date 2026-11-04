---
name: self-improvement
description: |
  Analyze external repos, identify capability gaps, and evolve the SDLC config.
  Use when enhancing the config based on external inspiration or session learnings.
  Triggers on: "improve config", "capability gap", "external repo", "enhance skills", "self-improve".
---

# Self-Improvement Workflow

## Overview
A structured process for evolving the SDLC config based on external inspiration, session learnings, or user feedback.

## Process

### Phase 1: Research
- Fetch and analyze the external repo or reference
- Identify patterns, conventions, and capabilities
- Focus on: agents, commands, skills, hooks, rules, workflows

### Phase 2: Gap Analysis
Compare against current config:

| Feature | Current | External | Gap | Impact |
|---------|---------|----------|-----|--------|
| [feature] | [status] | [status] | [what's missing] | [H/M/L] |

Prioritize by impact:
- **High**: Missing capability that blocks workflows
- **Medium**: Enhancement that improves quality or speed
- **Low**: Nice-to-have polish

### Phase 3: Plan
For each high/medium gap:
1. What files need to be created or modified?
2. Which existing components are affected?
3. Can changes be parallelized?
4. What's the testing strategy?

### Phase 4: Implement
1. Create GitHub issue describing the enhancement
2. Create feature branch from latest main
3. Implement changes (use parallel agents where possible)
4. Run `/validate-config` to verify correctness
5. Run `/audit` to verify documentation is in sync
6. Commit, push, create PR

### Phase 5: Validate
1. Address review comments via `/resolve-review`
2. Merge PR
3. Tag release if warranted

## When to Use
- User says "enhance", "improve", "add capabilities", "update based on X"
- After completing a project and identifying missing workflows
- When a new Claude Code feature becomes available
- When learning from other config repos

## Anti-Patterns
- Adding features nobody asked for
- Duplicating existing capabilities under new names
- Over-engineering simple workflows
- Adding skills without corresponding commands (orphaned knowledge)

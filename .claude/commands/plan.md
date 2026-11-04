---
description: "Create a structured implementation plan for a complex task"
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, Agent
---

# Plan

Decompose a complex task into a structured implementation plan.

## Input
$ARGUMENTS — Description of the task or feature to plan.

## Process

1. **Spawn planner agent** to analyze the task
2. The planner will:
   - Analyze requirements and constraints
   - Identify dependencies between work units
   - Create a dependency graph
   - Estimate effort per unit (S/M/L/XL)
   - Identify risks and mitigations
   - Find parallelization opportunities
3. **Output structured plan** with:
   - Phases and milestones
   - Work units with dependencies
   - Effort estimates
   - Risk assessment
   - Success criteria

## Output
Structured implementation plan ready for execution.

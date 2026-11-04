---
name: {{domain}}-product-analysis
description: |
  Analyzes {{domain}} requirements and creates prioritized backlog.
  Use when parsing requirements, prioritizing features, or defining MVP scope.
allowed-tools: Read, Grep, Glob, Write
---

# {{Domain}} Product Analysis

## Domain Context

{{domain_context}}

## Time Constraint

{{time_hours}} hours available. Allocate:
- 10% understanding & planning
- 70% implementation
- 10% testing
- 10% documentation & polish

## Prioritization Framework

### RICE Scoring

| Feature | Reach | Impact | Confidence | Effort | Score | Priority |
|---------|-------|--------|------------|--------|-------|----------|
{{#features}}
| {{name}} | {{reach}} | {{impact}} | {{confidence}} | {{effort}} | {{score}} | {{priority}} |
{{/features}}

### MoSCoW

**Must Have:**
{{#must_have}}
- {{feature}}
{{/must_have}}

**Should Have:**
{{#should_have}}
- {{feature}}
{{/should_have}}

**Could Have:**
{{#could_have}}
- {{feature}}
{{/could_have}}

**Won't Have:**
{{#wont_have}}
- {{feature}} — Reason: {{reason}}
{{/wont_have}}

## MVP Definition

{{mvp_definition}}

## Success Criteria

{{#success_criteria}}
- [ ] {{criterion}}
{{/success_criteria}}

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
{{#risks}}
| {{risk}} | {{probability}} | {{impact}} | {{mitigation}} |
{{/risks}}

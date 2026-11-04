---
name: skill-generator
description: |
  Analyzes problem statements and generates domain-specific SKILL.md files.
  Use when starting a new interview challenge or when problem requirements change.
  Triggers on: "generate skills", "analyze problem", "parse requirements".
allowed-tools: Read, Glob, Grep, Write, Edit
---

# Skill Generator

Generates contextual Claude skills from problem statements. This is the entry point for interview challenges.

## Workflow

1. **Parse** problem statement from `PROBLEM.md` in repo root (or prompt user)
2. **Extract** domain entities, operations, constraints, and evaluation criteria
3. **Generate** domain-specific skills in `skills/generated/`
4. **Output** analysis artifacts to `solution/requirements/`

## Input

Problem statement sources (checked in order):
- `PROBLEM.md` or `problem.md` in repo root
- User-provided file path
- User-pasted content

## Output Structure

```
skills/generated/
├── {domain}-models/SKILL.md      # Domain entity patterns
├── {domain}-operations/SKILL.md  # Core business operations
├── {domain}-validation/SKILL.md  # Business rules & constraints
└── {domain}-reporting/SKILL.md   # Reporting & analytics

solution/requirements/
├── requirements.md               # Extracted requirements
├── entities.md                   # Domain model analysis
├── rice-scores.md                # RICE prioritization
├── moscow.md                     # MoSCoW categorization
└── mvp-scope.md                  # Final MVP definition
```

## Skill Generation Process

### Step 1: Requirement Extraction

Extract and categorize requirements:

```markdown
## Functional Requirements
- FR-001: [Description] — Priority: [Must/Should/Could/Won't]

## Non-Functional Requirements
- NFR-001: [Description] — Category: [Performance/Security/UX/etc.]

## Constraints
- CON-001: [Description] — Impact: [High/Medium/Low]

## Evaluation Criteria
- EVAL-001: [What evaluators will look for]
```

### Step 2: Domain Entity Analysis

Identify entities and relationships:

```markdown
## Entities
| Entity | Attributes | Relationships |
|--------|------------|---------------|
| User   | id, name   | has_many: Orders |

## Aggregate Roots
- [Entity]: Controls lifecycle of [related entities]

## Value Objects
- [Object]: Immutable, defined by attributes
```

### Step 3: RICE Scoring

Score each feature for prioritization:

| Feature | Reach | Impact | Confidence | Effort | Score |
|---------|-------|--------|------------|--------|-------|
| [Name]  | 1-10  | 1-3    | 0-100%     | person-hours | R×I×C/E |

**Scoring Guide:**
- **Reach**: How many users/transactions affected (1-10 scale)
- **Impact**: Business value (3=massive, 2=high, 1=medium, 0.5=low)
- **Confidence**: How sure are we? (100%=high, 80%=medium, 50%=low)
- **Effort**: Engineering hours estimate

### Step 4: MoSCoW Categorization

Based on RICE scores and time constraints:

```markdown
## Must Have (MVP-critical, do first)
- [ ] Feature with highest RICE scores
- [ ] Features blocking other work

## Should Have (Important, time permitting)
- [ ] High-value features after Must-haves

## Could Have (Nice to have)
- [ ] Lower priority features

## Won't Have (Explicitly out of scope)
- [ ] Features we're consciously skipping
- [ ] Document WHY for code review discussion
```

### Step 5: Generate Domain Skills

For each identified domain area, generate a SKILL.md:

```yaml
---
name: {domain}-{capability}
description: |
  {Specific description of what this skill does}.
  Use when {trigger conditions}.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {Domain} {Capability}

## Domain Context
{Problem-specific context from analysis}

## Extends
- foundation/{relevant-foundation-skill}

## Patterns
{Domain-specific code patterns}

## Validation Criteria
{How to validate this is implemented correctly}
```

## Templates

See `templates/` directory for skill templates:
- `product-manager.template.md`
- `architect.template.md`
- `backend.template.md`
- `frontend.template.md`
- `database.template.md`
- `testing.template.md`
- `devops.template.md`

## Example: Inventory Management Challenge

Given a restaurant/warehouse inventory problem, would generate:

```
skills/generated/
├── inventory-models/SKILL.md       # Location, Item, Category, Staff
├── inventory-operations/SKILL.md   # Delivery, Usage, StockTake
├── inventory-validation/SKILL.md   # Stock level checks, location scoping
├── inventory-reporting/SKILL.md    # Movement audit, financial summary
└── inventory-import/SKILL.md       # Data import utilities
```

## Handoff

After generation, trigger validation:
```
→ Judge validates skill coverage and quality
→ Checkpoint: solution/checkpoints/00-skill-generation.md
→ User reviews and approves
→ Orchestrator proceeds to Stage 1
```

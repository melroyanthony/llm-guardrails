# Critique Prompts

Qualitative analysis prompts for each validation stage.

## General Critique Framework

For each stage, analyze:

1. **Alignment**: Does output match input requirements?
2. **Completeness**: Is anything missing?
3. **Quality**: Is the work well-executed?
4. **Pragmatism**: Are choices appropriate for constraints?
5. **Explainability**: Can this be defended in code review?

---

## Stage 0: Skill Generation

### Strengths Analysis
> What aspects of the skill generation demonstrate strong problem understanding?
> - Domain entity identification
> - Constraint recognition
> - Appropriate skill granularity

### Improvement Areas
> What could make the generated skills more effective?
> - Missing domain patterns
> - Overly generic skills
> - Trigger description clarity

### Critical Review
> Are there fundamental misunderstandings of the problem?
> - Misidentified entities
> - Wrong relationships
> - Missing constraints

---

## Stage 1: Product Analysis

### Strengths Analysis
> What aspects of prioritization show strong product thinking?
> - Business value recognition
> - User impact consideration
> - Realistic scoping

### Improvement Areas
> What could improve the prioritization?
> - Overlooked dependencies
> - Underestimated effort
> - Missing trade-off analysis

### Critical Review
> Are there prioritization decisions that could fail the interview?
> - Wrong features in MVP
> - Unrealistic scope
> - Missing evaluator criteria

---

## Stage 2: Architecture

### Strengths Analysis
> What architectural decisions demonstrate expertise?
> - Appropriate patterns for scale
> - Clean API design
> - Thoughtful data modeling

### Improvement Areas
> What architectural choices could be improved?
> - Overcomplicated design
> - Missing error handling strategy
> - Inconsistent naming

### Critical Review
> Are there architectural decisions that will cause problems?
> - Fundamental data model issues
> - API inconsistencies
> - Missing critical endpoints

### Interview Prep
> What decisions should be highlighted in code review?
> - Trade-offs made
> - Alternatives considered
> - Why this approach

---

## Stage 3: Implementation

### Strengths Analysis
> What aspects of implementation show engineering quality?
> - Clean code structure
> - Idiomatic patterns
> - Appropriate abstractions

### Improvement Areas
> What implementation details could be improved?
> - Code duplication
> - Missing edge cases
> - Type safety gaps

### Critical Review
> Are there implementation issues that must be fixed?
> - Bugs in critical paths
> - Security issues
> - Performance problems

### Interview Prep
> What code should be highlighted in review?
> - Clever solutions
> - Pragmatic shortcuts
> - Known limitations

---

## Stage 4: Testing

### Strengths Analysis
> What aspects of testing show quality thinking?
> - Critical path coverage
> - Meaningful assertions
> - Clear test organization

### Improvement Areas
> What testing gaps exist?
> - Untested scenarios
> - Weak assertions
> - Missing edge cases

### Critical Review
> Are there testing issues that undermine confidence?
> - Failing tests
> - Tests that don't test anything
> - Missing critical coverage

---

## Stage 5: DevOps

### Strengths Analysis
> What deployment choices show production awareness?
> - Clean containerization
> - Clear documentation
> - Reproducible setup

### Improvement Areas
> What deployment aspects could be improved?
> - Missing health checks
> - Unclear instructions
> - Missing environment config

### Critical Review
> Are there deployment issues that prevent running the app?
> - Build failures
> - Missing dependencies
> - Broken compose file

### Interview Prep
> Is the candidate ready for code review?
> - Can explain all decisions
> - Knows limitations
> - Has talking points ready

---

## Synthesis Questions

After analyzing each area:

1. **Overall Assessment**: Is this work interview-ready?
2. **Biggest Risk**: What's the most likely point of failure?
3. **Biggest Strength**: What should be highlighted?
4. **Time Check**: Is progress on track for time budget?
5. **Next Stage**: What guidance is needed for the next stage?

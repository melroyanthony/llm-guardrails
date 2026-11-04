# Validation Rubrics

Structured scoring criteria for each stage.

## Stage 0: Skill Generation

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| Requirement Coverage | 25% | All requirements extracted and categorized | Most requirements captured | Major requirements missing |
| Entity Identification | 25% | Complete domain model with relationships | Core entities identified | Key entities missing |
| Skill Relevance | 25% | Skills precisely match problem domain | Skills generally applicable | Generic/irrelevant skills |
| Skill Structure | 25% | Valid YAML, clear triggers, proper extends | Minor formatting issues | Invalid or incomplete skills |

## Stage 1: Product Analysis

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| RICE Consistency | 20% | Scores well-justified with evidence | Reasonable estimates | Arbitrary or inconsistent |
| Prioritization Logic | 25% | Clear rationale, trade-offs documented | Logical ordering | No clear reasoning |
| MVP Realism | 25% | Achievable in time budget with buffer | Tight but possible | Overscoped or underscoped |
| Scope Documentation | 15% | What's in/out clearly stated with why | Basic scope defined | Ambiguous scope |
| Risk Identification | 15% | Key risks identified with mitigations | Some risks noted | No risk consideration |

## Stage 2: Architecture

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| C4 Accuracy | 20% | Diagrams match implementation plan | Diagrams mostly accurate | Misleading diagrams |
| API Completeness | 25% | All MVP endpoints with full schemas | Core endpoints defined | Missing critical endpoints |
| Data Model | 25% | Normalized, relationships clear, indexes considered | Workable schema | Fundamental modeling issues |
| ADR Quality | 15% | Meaningful decisions, clear rationale | Basic decisions documented | Boilerplate or missing |
| Consistency | 15% | API, DB, and diagrams align | Minor inconsistencies | Major contradictions |

## Stage 3: Implementation

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| Functionality | 30% | All MVP features work correctly | Core features work | Critical features broken |
| Code Quality | 25% | Idiomatic, readable, well-structured | Reasonable quality | Messy or confusing |
| Type Safety | 15% | No type errors, proper typing | Minor type issues | Type errors prevent build |
| Error Handling | 15% | Appropriate error handling | Basic error handling | Crashes on errors |
| Pattern Adherence | 15% | Follows skill patterns consistently | Generally follows patterns | Ignores guidance |

## Stage 4: Testing

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| Critical Path Coverage | 40% | All Must-Have features tested | Core paths tested | Critical paths untested |
| Test Quality | 25% | Meaningful assertions, clear arrange/act/assert | Basic tests | Trivial or broken tests |
| Test Passing | 25% | All tests pass | Most tests pass | Tests fail |
| Documentation | 10% | Test purpose clear | Tests exist | No documentation |

## Stage 5: DevOps

| Criterion | Weight | 5 (Exceptional) | 3 (Adequate) | 1 (Critical Gap) |
|-----------|--------|-----------------|--------------|------------------|
| Deployment Works | 30% | docker-compose up works from clean state | Works with minor issues | Doesn't start |
| README Quality | 25% | Clear setup, what/why documented | Basic instructions | Missing or unclear |
| Interview Prep | 25% | Decisions summarized, talking points ready | Key points noted | Unprepared for review |
| Commit History | 20% | Conventional commits, coherent story | Reasonable history | Messy or unclear |

## Scoring Calculation

```
Stage Score = Σ(Criterion Score × Weight)
```

### Thresholds

- **Pass**: Score ≥ 3.5 AND no criterion < 2
- **Conditional Pass**: Score ≥ 3.0 AND no criterion = 1
- **Fail**: Score < 3.0 OR any criterion = 1

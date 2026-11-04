---
name: optimization-algorithms
description: |
  Decision framework for selecting optimization algorithms: greedy, DP, ILP, and heuristic approaches.
  Use when choosing an algorithm strategy or deciding between baseline-first vs advanced optimization.
  Triggers on: "optimization", "greedy", "dynamic programming", "ILP", "heuristic", "complexity".
---

# Optimization Algorithm Selection

## Decision Flowchart

```
Is the problem solvable in polynomial time?
├── Yes (P) → Use exact algorithm (DP, shortest path, flow)
└── No (NP-hard / NP-complete)
    ├── Is N small enough for exact? (N ≤ 20)
    │   └── Yes → Exact: brute force / DP with bitmask
    ├── Is N moderate? (20 < N ≤ 1000)
    │   ├── Good structure (subproblems) → DP / branch-and-bound
    │   └── No structure → Greedy + local search
    └── Is N large? (N > 1000)
        ├── Approximation guarantee needed → Approximation algorithm
        └── Good enough solution → Greedy / heuristic / metaheuristic
```

## Algorithm Classes

| Class | Time Complexity | Solution Quality | When to Use |
|-------|----------------|-----------------|-------------|
| **Exact (DP)** | O(2^N * N) or O(N^3) | Optimal | N ≤ 20, or polynomial substructure |
| **Greedy** | O(N log N) or O(N^2) | Good (often near-optimal) | Time-constrained, simple structure |
| **Local search** | O(N^2 * iterations) | Good to optimal | Improvement over greedy baseline |
| **Branch-and-bound** | Exponential worst, fast average | Optimal | Moderate N with good pruning |
| **ILP/SAT** | Exponential worst | Optimal | Complex constraints, solver available |
| **Metaheuristic** | Varies | Approximate | Large N, no structure, time budget |

## Baseline-First Pattern

**Always implement a trivially correct baseline before optimizing.**

```
Phase 1 (hours 0-4): Baseline
  - Simplest valid solution (e.g., one item per group, no optimization)
  - Proves the constraint model works
  - Provides regression test baseline
  - Guarantees a submittable answer

Phase 2 (hours 4-12): Greedy optimization
  - One pass improvement (e.g., merge adjacent items)
  - Cost-based decisions (merge only if total cost decreases)
  - Validate against baseline (must strictly improve)

Phase 3 (hours 12+): Advanced optimization
  - Local search (swap, split, recombine)
  - Parameter tuning (search over configurations)
  - Domain-specific tricks (closed-form formulas, pruning)
```

**Why baseline-first works:**
- Eliminates cascading failures (latency model bugs surface early)
- Provides safety fallback if optimization code has bugs
- Enables incremental validation (each stage must beat previous)
- Gives confidence to try aggressive optimizations

## Complexity Analysis for ADRs

When documenting algorithm choices in ADRs, include:

```markdown
## Complexity Analysis

### Search Space
- Total configurations: [formula, e.g., Bell(N) ~ 10^75]
- Feasible configurations: [estimate]

### Chosen Algorithm
- Time: O(N^2) per iteration, K iterations
- Space: O(N) auxiliary
- Expected runtime: <1s for N ≤ 100

### Alternatives Considered
| Algorithm | Time | Quality | Rejected Because |
|-----------|------|---------|-----------------|
| Exact DP | O(2^N * N) | Optimal | N=103 makes 2^103 infeasible |
| ILP | Exponential | Optimal | Solver dependency, setup time |
| Beam search | O(N * B * log B) | Near-optimal | Marginal gain over greedy |

### Evidence
- Greedy achieves X% of theoretical optimal on benchmarks
- Runtime: Y ms on largest test case (N=103)
- ROI: 4 hours to implement vs. 2 days for DP
```

## Cost-Based Decision Making

When merging, splitting, or transforming in optimization:

```python
# WRONG — feasibility-based (can we?)
if merged_fits_in_memory:
    merge(a, b)

# RIGHT — cost-based (should we?)
merged_cost = evaluate(merge(a, b))
split_cost = evaluate(a) + evaluate(b)
EPSILON = 1.0  # Tolerance for floating-point noise
if merged_cost < split_cost - EPSILON:
    merge(a, b)
```

**Rules:**
- Always compare costs, not just feasibility
- Use epsilon tolerance for floating-point comparisons (see `numerical-computing` skill)
- Log the decision and costs for debugging
- Test with cases where merge is harmful (ensures cost check works)

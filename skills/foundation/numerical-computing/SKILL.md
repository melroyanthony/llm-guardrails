---
name: numerical-computing
description: |
  Floating-point precision guidelines, tolerance strategies, and epsilon-based decision making for algorithms.
  Use when implementing mathematical computations, optimization, or scientific code.
  Triggers on: "floating point", "precision", "epsilon", "tolerance", "rounding", "numeric".
---

# Numerical Computing Guidelines

## Floating-Point Comparison

### Never Use Exact Equality
```python
# WRONG
assert result == 42.0

# RIGHT — absolute tolerance
assert abs(result - 42.0) < 0.01

# RIGHT — relative tolerance (guard against zero)
assert abs(result - expected) / max(abs(expected), 1e-15) < 0.001
```

### When to Use Absolute vs Relative Tolerance

| Situation | Strategy | Example |
|-----------|----------|---------|
| Values near zero | Absolute | `abs(x) < 1e-10` |
| Large values | Relative | `abs(x - y) / abs(y) < 1e-6` |
| Mixed magnitudes | Combined | `abs(x - y) < max(atol, rtol * abs(y))` |
| Test assertions | Absolute with documented delta | `assert abs(actual - expected) < 1.0` |

### Standard Tolerances by Domain

| Domain | Absolute | Relative | Notes |
|--------|----------|----------|-------|
| Financial | 0.01 | - | Penny-level precision |
| Scientific | 1e-10 | 1e-6 | Double precision limits |
| ML/AI | 1e-4 | 1e-3 | Model weights are approximate |
| Scheduling/optimization | 0.5-1.0 | 1e-3 | Hardware tile rounding |
| Graphics | 1e-5 | 1e-4 | Pixel-level precision |

## Epsilon in Decision-Making

When making algorithmic decisions (merge, branch, optimize), use epsilon tolerance to avoid floating-point noise:

```python
# WRONG — floating-point noise causes unstable decisions
if fused_latency < split_latency:
    merge()

# RIGHT — epsilon prevents borderline decisions
EPSILON = 1.0  # Document: accounts for rounding in tile calculation
if fused_latency < split_latency - EPSILON:
    merge()
```

### Rules for Epsilon
- Always document the epsilon value and its justification
- Epsilon should be proportional to the magnitude of values compared
- Use a named constant, never a magic number
- Test with values near the epsilon boundary

## Type Selection for Numeric Code

| Use Case | Python | Rust | TypeScript |
|----------|--------|------|-----------|
| Integer dimensions | `int` | `i64` | `number` (careful) |
| Floating-point results | `float` (f64) | `f64` | `number` |
| Fixed-point currency | `Decimal` | `rust_decimal` | Libraries only |
| Large integers | `int` (arbitrary) | `i128` or `num` crate | `BigInt` |

### TypeScript Warning
JavaScript's `number` is always IEEE 754 double. For integers >2^53, use `BigInt`. For financial calculations, use a decimal library.

## Common Pitfalls

1. **Accumulation error**: Summing many small floats → use Kahan summation or sort ascending
2. **Catastrophic cancellation**: `a - b` where `a ≈ b` → rearrange formula
3. **Integer overflow**: `a * b` where both are large → check before multiply or use wider type
4. **Division by zero**: Always guard divisions, especially in formulas with `1/x`
5. **NaN propagation**: One NaN poisons all downstream calculations → validate inputs early

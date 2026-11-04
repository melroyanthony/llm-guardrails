---
name: polyglot-coordination
description: |
  Patterns for coordinating multi-language projects: specification contracts and cross-language testing.
  Use when a project uses multiple programming languages that must interoperate.
  Triggers on: "polyglot", "multi-language", "cross-language", "specification contract", "interop".
---

# Polyglot Project Coordination

## When to Use Multiple Languages
- Performance-critical component + rapid prototyping (Rust + Python)
- Frontend + backend (TypeScript + Python)
- Contest with multiple tracks (each optimized for its track)
- Migration from one language to another (old + new coexist)

See `language-selection` skill for the decision framework on which language to choose per component.

## Specification Contract

The key to multi-language coordination is a **neutral specification** that both implementations follow independently.

### Contract Types

| Type | Format | Best For |
|------|--------|----------|
| JSON Schema | `.json` / `.yaml` | API contracts, data interchange |
| OpenAPI | `.yaml` | Web APIs with typed endpoints |
| Protocol Buffers | `.proto` | RPC, high-performance serialization |
| Header file | `.h` | Systems interop (C/Rust FFI) |
| Worked examples | `.md` + `.json` | Algorithm correctness (input→output pairs) |

### Example: Algorithm Project (MLSys Pattern)
```
Specification:
  - problem.h (C++ structs defining types)
  - PROBLEM.md (worked examples with expected outputs)
  - examples/*.json (input→output test cases)

Implementation A (Rust):
  - models.rs mirrors C++ types
  - 18 unit tests match worked examples

Implementation B (Python):
  - dataclasses mirror C++ types
  - Same 18 test cases, same expected outputs

Validation:
  - Both implementations run on same inputs
  - JSON outputs compared structurally
  - Floating-point tolerance applied
```

## Cross-Language Testing

### Strategy
1. **Unit tests per language**: Each implementation tests against worked examples independently
2. **Integration test**: Run both implementations on same input, compare outputs
3. **E2E test**: Full pipeline through both paths, validate end-to-end

### CI Configuration
```yaml
# Minimal example — add caching, matrix builds, and permissions per your project
jobs:
  lang-a:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo test

  lang-b:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv run pytest

  cross-validation:
    needs: [lang-a, lang-b]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: astral-sh/setup-uv@v5
      - run: |
          cargo run -- input.json > output_a.json
          uv run python main.py input.json > output_b.json
          python compare.py output_a.json output_b.json --tolerance 1.0
```

## Directory Structure

```
project/
├── problem/                    # Shared specification
│   ├── PROBLEM.md              # Worked examples
│   ├── spec.h or schema.json   # Type definitions
│   └── benchmarks/             # Test inputs
├── solution/
│   ├── backend/rust/           # Implementation A
│   │   ├── Cargo.toml
│   │   └── src/
│   ├── backend/python/         # Implementation B (or agent/)
│   │   ├── pyproject.toml
│   │   └── src/
│   ├── scripts/
│   │   ├── test-e2e.sh         # Cross-language validation
│   │   └── compare.py          # Output comparison with tolerance
│   └── docs/
│       └── decisions/
│           └── ADR-001-language-selection.md
```

## Mutual Validation Pattern

When two implementations exist, use them to validate each other:

1. **Same input → same output**: Both must produce equivalent results
2. **Divergence = bug**: If outputs differ, one (or both) has a bug
3. **Tolerance-aware comparison**: Use domain-appropriate tolerance for floating-point
4. **Deterministic**: Both implementations must be deterministic (same input → same output every time)

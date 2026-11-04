---
name: language-selection
description: |
  Decision framework for choosing Rust, Python, Go, or TypeScript based on project requirements.
  Use when selecting a programming language for a new project or component.
  Triggers on: "which language", "Rust vs", "Python vs", "Go vs", "TypeScript vs", "language choice".
---

# Language Selection Guide

## Decision Framework

```
What are you building?
├── Systems tool (CLI, compiler, optimizer, scheduler)
│   ├── Performance-critical? → Rust
│   └── Rapid prototyping? → Python (then port to Rust)
├── Web service (API, backend, microservice)
│   ├── ML/AI integration? → Python (FastAPI)
│   ├── Serverless API (AWS)? → TypeScript (Lambda + API Gateway)
│   ├── JavaScript ecosystem? → TypeScript (Express/NestJS)
│   ├── High concurrency (Go ecosystem)? → Go (net/http, Fiber)
│   └── High concurrency (Rust ecosystem)? → Rust (Actix, Axum)
├── Frontend (web UI)
│   ├── SSR/SEO needed? → Next.js (TypeScript)
│   └── SPA? → React+Vite (TypeScript)
├── Data pipeline (ETL, batch, streaming)
│   ├── Simple transforms? → Python
│   └── High throughput? → Go or Rust
└── AI agent (LLM integration)
    └── Python (SDK support, prompt engineering)
```

## Per-Language Standards

### Rust
- Use `Result<T, E>` for all fallible operations (no panics in library code)
- Use `i64` for dimensions/capacity, `f64` for latency/scores (match C/C++ interop)
- Prefer `serde` for serialization, avoid heavy frameworks
- Use `cargo clippy` and `cargo fmt` for linting
- Testing: `#[test]` with `assert!`, `assert_eq!`, tolerance-based for f64
- Dependencies: Minimize — prefer std library, audit each crate

### Python
See `.claude/rules/coding-standards.md` for full standards. Additional notes:
- `async def` for I/O-bound, regular `def` for CPU-bound
- `dataclasses` for data structures, `Pydantic` only at API boundaries
- Testing: `pytest` with fixtures, `assert` with tolerance for floats

### TypeScript
See `.claude/rules/coding-standards.md` for full standards. Additional notes:
- `type` for unions/intersections (use `interface` for object shapes)
- Testing: `vitest` with `expect().toBe()`, `.toBeCloseTo()` for floats

### Go
- Follow `Effective Go` conventions
- Use `error` return values (not panic)
- `go fmt` and `go vet` required
- Testing: `testing` package, `t.Helper()` for test helpers

## When to Use Multiple Languages

| Scenario | Primary | Secondary | Coordination |
|----------|---------|-----------|-------------|
| Contest (performance + agent) | Rust (submission) | Python (AI agent) | JSON spec + E2E tests |
| Full-stack web | Python (backend) | TypeScript (frontend) | OpenAPI contract |
| CLI + API | Rust (CLI) | Python (API wrapper) | Shared JSON schema |
| Data + serving | Python (pipeline) | Go (serving) | Message queue / API |
| Serverless + Angular | TypeScript (Lambda) | TypeScript (Angular) | Nx monorepo + npm workspaces |

See `polyglot-coordination` skill for multi-language project patterns.

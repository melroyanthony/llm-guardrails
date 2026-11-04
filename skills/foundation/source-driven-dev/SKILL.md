---
name: source-driven-dev
description: |
  Mandate that framework-specific code decisions are backed by fetching and citing official
  documentation. Prevents hallucinated APIs and deprecated patterns from training data.
  Use when writing framework-specific code where training data may be outdated.
  Triggers on: new framework, "check the docs", unfamiliar API, version-specific code.
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch, Bash
---

# Source-Driven Development

## Principle

Every framework-specific implementation decision must be grounded in official documentation — not training data recall, not Stack Overflow, not blog posts. Fetch the docs, verify the API, cite the source.

## Workflow

### 1. Detect Stack and Versions

Before writing framework-specific code, identify exact versions from lockfiles:

```bash
# Python
grep 'version' pyproject.toml          # Project version
grep 'fastapi' uv.lock                 # FastAPI version
grep 'sqlmodel' uv.lock                # SQLModel version

# Node.js
jq '.dependencies' package.json        # Direct dependencies
jq '.devDependencies' package.json     # Dev dependencies

# Go
grep 'require' go.mod                  # Module dependencies
```

### 2. Fetch Official Documentation

Use `WebFetch` to retrieve the specific documentation page for the API you're about to use:

| Framework | Documentation URL Pattern |
|---|---|
| FastAPI | `https://fastapi.tiangolo.com/` |
| Next.js | `https://nextjs.org/docs/` |
| SQLModel | `https://sqlmodel.tiangolo.com/` |
| Pydantic | `https://docs.pydantic.dev/latest/` |
| React | `https://react.dev/reference/` |
| AWS SDK | `https://docs.aws.amazon.com/` |
| Terraform | `https://registry.terraform.io/providers/` |

Fetch the **specific page** for the API you need, not the homepage.

### 3. Implement Following Documented Patterns

Write code that matches the documented API signatures, not what training data suggests. Common divergences:

| Area | Training Data Risk | Verification |
|---|---|---|
| FastAPI 0.115+ | Old `on_event` lifecycle | Verify `lifespan` context manager pattern |
| Next.js App Router | Pages Router patterns (`getServerSideProps`) | Verify `app/` directory conventions |
| Pydantic v2 | v1 `Config` class, `.dict()` method | Verify `model_config`, `.model_dump()` |
| SQLModel 0.0.22+ | Sync-only patterns | Verify async session support |
| AWS S3 Vectors | Pre-GA API (Dec 2025) | Verify current boto3 client methods |
| Angular 21 | Older module-based patterns | Verify signal-based patterns |

### 4. Cite Sources

For non-obvious API usage, add a brief citation comment:

```python
# Per FastAPI docs: use lifespan context manager, not on_event
# https://fastapi.tiangolo.com/advanced/events/
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
```

Only cite when the pattern is **non-obvious** or **differs from common training data**. Don't cite obvious stdlib usage.

### 5. Flag Unverified Patterns

If you cannot fetch or verify the documentation:

```python
# UNVERIFIED: S3 Vectors pagination API — docs unavailable, using training data pattern
# TODO: Verify against https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html
response = client.list_vectors(IndexArn=index_arn, MaxResults=100)
```

## Source Priority

| Priority | Source | Trust Level |
|---|---|---|
| 1 | Official framework documentation | Trusted |
| 2 | Framework source code (GitHub) | Trusted |
| 3 | Framework changelog/release notes | Trusted |
| 4 | Official framework examples | High |
| 5 | Well-maintained community packages | Verify |
| 6 | Stack Overflow / blog posts | Untrusted — verify against #1 |
| 7 | Training data recall | Untrusted — always verify |

## Anti-Patterns

| Anti-Pattern | Reality |
|---|---|
| "I know this API from training data" | Training data may be 6-18 months old. APIs change. Verify. |
| "Stack Overflow says to do it this way" | SO answers may target older versions. Check the version tag. |
| "The blog post showed this pattern" | Blog posts are opinions, not documentation. Cross-reference with official docs. |
| "Fetching docs wastes tokens" | Hallucinating an API wastes more — plus debugging time when it fails at runtime. |

## When to Apply

- **Always**: When using a framework API for the first time in a session
- **Always**: When the framework version is newer than your training cutoff
- **Always**: When you're unsure about the exact method signature or parameters
- **Skip**: When using well-known stdlib functions (e.g., `os.path.join`, `Array.map`)
- **Skip**: When repeating a pattern you already verified earlier in the same session

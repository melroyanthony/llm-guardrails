---
description: "Generate Postman collection with environments from OpenAPI spec"
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Generate Postman Collection

Generate a Postman v2.1 collection with environment files from the project's OpenAPI specification.

## Input
$ARGUMENTS — Optional path to OpenAPI spec. Defaults to `solution/docs/architecture/openapi.yaml`.

## Process

1. **Load API testing skill** from `skills/foundation/api-testing/SKILL.md`
2. **Read the OpenAPI spec** from the specified path or default location
3. **Parse all paths and methods** from the spec
4. **Generate collection** (`solution/docs/api-testing/collection.json`):
   - Group requests by tag or resource
   - Include request bodies with example values from schemas
   - Add test assertions for expected status codes
   - Add variable extraction (e.g., save created resource IDs)
   - Order as runnable flow: Auth → Create → Read → Update → Delete
   - Add collection-level bearer auth using `{{access_token}}`
   - Add pre-request scripts for token refresh
5. **Generate environment files**:
   - `env.dev.json` — localhost with test credentials
   - `env.staging.json` — staging URL, empty secrets
   - `env.prod.json` — production URL, empty secrets (gitignored)
6. **Add .gitignore entry** for production env file if not already present
7. **Show Newman run command** for local testing

## Output
- `solution/docs/api-testing/collection.json` — Importable Postman collection
- `solution/docs/api-testing/env.dev.json` — Development environment
- `solution/docs/api-testing/env.staging.json` — Staging environment
- `solution/docs/api-testing/env.prod.json` — Production environment (gitignored)
- Newman CLI command for CI integration

## Working Directory
Use `solution/` as the base directory for all file operations.

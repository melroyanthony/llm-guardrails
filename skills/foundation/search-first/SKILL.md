---
name: search-first
description: |
  Research-before-coding workflow. Before writing custom code, systematically search for existing
  solutions in packages, MCP servers, and open source.
  Use when tempted to write custom code that might already exist as a package or tool.
  Triggers on: "find package", "search for library", "is there a library", "don't reinvent", "reuse".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Search-First Development

## Principle
Before writing ANY custom code, systematically search for existing solutions. The best code is code you don't write.

## Search Order
1. **Standard Library** — Does the language already provide this?
2. **Existing Codebase** — Is this already implemented in the project?
3. **Package Registry** — Is there a well-maintained package for this?
4. **MCP Servers** — Is there a Model Context Protocol server that provides this capability?
5. **Open Source** — Is there an open-source implementation to reference or adapt?
6. **Build It** — Only after exhausting the above, write custom code.

## Decision Matrix

| Criteria | Adopt (use as-is) | Extend (fork/wrap) | Build (write custom) |
|----------|--------------------|--------------------|---------------------|
| Exact fit for needs | ✅ | | |
| 80% fit, missing minor features | | ✅ | |
| Core differentiator / competitive advantage | | | ✅ |
| Well-maintained (>1K stars, recent commits) | ✅ | ✅ | |
| Abandoned / unmaintained | | Cautiously | ✅ |
| Security-critical path | Audit first | Audit first | ✅ |
| Performance-critical path | Benchmark first | ✅ | ✅ |

## Package Evaluation Checklist
Before adopting a package, verify:
- [ ] **Maintenance**: Last commit within 6 months
- [ ] **Popularity**: Reasonable download count / stars for the ecosystem
- [ ] **License**: Compatible with your project (MIT, Apache 2.0, BSD preferred)
- [ ] **Size**: Not bloated (check bundle size for frontend packages)
- [ ] **Security**: No known critical CVEs (`npm audit` / `safety check`)
- [ ] **Dependencies**: Minimal transitive dependencies
- [ ] **TypeScript**: Has type definitions (for TS projects)
- [ ] **API stability**: Follows semver, no frequent breaking changes

## Search Commands

```bash
# Python packages — search on https://pypi.org
# pip search is deprecated; use pypi.org or uv search when available
uv tree  # check what's already installed and dependency tree
uv run pip index versions <package>  # check available versions

# Node.js packages
npm search <term>
npx npm-check-updates  # check for updates

# GitHub
gh search repos "<query>" --sort=stars --limit=10
gh search code "<query>" --language=python --limit=10

# Existing codebase
grep -r "<pattern>" --include="*.py" .
```

## When to Skip Search-First
- The task is clearly custom business logic
- You've already verified no solution exists in a previous session
- Time constraint makes the search overhead not worthwhile (< 10 lines of code)
- The code is a simple glue/adapter between existing components

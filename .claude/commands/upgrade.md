---
description: "Upgrade dependencies to resolve CVEs or update to latest versions"
allowed-tools: Read, Glob, Grep, Bash, WebFetch, WebSearch, Edit, Write, AskUserQuestion
argument-hint: [package-name, CVE-ID, or "all"]
---

# Upgrade

Safely upgrade dependencies to resolve CVEs or update to latest versions.

## Python 3.14 pin

Same rule as `AGENTS.md` and `skills/foundation/stack-guardrails/SKILL.md`.

A dependency sweep takes libraries and language runtimes to the latest stable release. Python is the exception: it is pinned to 3.14 (Melroy's decision, 2026-10-24, agreed by EL and SWE) because wheels for 3.15 are still catching up. The decision treated 3.15 as only at 3.15.0 and set the revisit at 3.15.1 or 3.15.2. python.org published 3.15.1 on 2026-10-21. The pin stays until that revisit is recorded. Until then, a dependency sweep must not bump `requires-python`, `.python-version`, `python-version` for `astral-sh/setup-uv` or `actions/setup-python`, or Ruff `target-version` past 3.14.

## Input
$ARGUMENTS — Dependency name, CVE ID, or "all" for full audit. Examples:
- `fastapi` (upgrade specific package)
- `CVE-2024-12345` (upgrade to fix specific CVE)
- `all` (audit and upgrade all vulnerable dependencies)

## Process

### Step 1: Audit Current State
Detect project stack and run audit:
```bash
# Python
uv run pip-audit 2>/dev/null || echo "pip-audit not available"
uv tree --outdated 2>/dev/null

# Node.js
npm audit
npm outdated
```

### Step 2: Identify Upgrade Path
For each dependency to upgrade:
- Current version → latest safe version
- Check for breaking changes (read changelog/release notes)
- Check if the dependency is a direct or transitive dependency
- Determine if a major, minor, or patch upgrade

### Step 3: Assess Risk
| Upgrade | Breaking Changes? | Test Coverage | Risk |
|---------|-------------------|---------------|------|
| patch (x.y.Z) | Unlikely | Any | Low |
| minor (x.Y.z) | Possible | Good | Medium |
| major (X.y.z) | Likely | Full | High |

### Step 4: Ask User to Confirm
Present the upgrade plan:
- Dependencies to upgrade with version ranges
- Risk assessment for each
- Breaking change warnings

Ask: "Proceed with these upgrades?"

### Step 5: Apply Upgrades
```bash
# Python
uv add <package>@<version>

# Node.js
npm install <package>@<version>
```

### Step 6: Verify
- Run full test suite
- Run type checker
- Run linter
- Verify build succeeds
- Run security audit again to confirm CVE is resolved

### Step 7: Commit and PR
If all checks pass:
- Commit: `fix(deps): upgrade <package> to <version> (CVE-XXXX)`
- Create PR with upgrade details and test results

## Output
- Audit report of current vulnerabilities
- Upgrades applied and tested
- PR created with upgrade details

---
description: "Investigate bugs, errors, or CVEs with root-cause analysis and fix recommendations"
allowed-tools: Read, Glob, Grep, Bash, WebFetch, WebSearch, Agent, AskUserQuestion, Edit, Write
argument-hint: [bug description, error message, CVE-ID, or #issue-number]
---

# Investigate

Run a structured debugging pipeline: root-cause analysis → solution design → user confirmation → implement fix → test → PR.

## Input
$ARGUMENTS — Bug description, error message, CVE ID, or GitHub issue number. Examples:
- `TypeError: Cannot read property 'id' of undefined in UserService`
- `CVE-2024-12345`
- `#42` (GitHub issue number)
- `Login fails intermittently after deploying v1.3`

## Process

### Step 1: Gather Context
- If $ARGUMENTS is a GitHub issue number (`#N`): fetch issue details with `gh issue view N`
- If $ARGUMENTS is a CVE ID: search for advisory details
- If $ARGUMENTS is an error message: start with the stack trace
- Read relevant code, configs, and recent git history

### Step 2: Root-Cause Analysis
Write the problem statement first (expected vs actual, scope, severity, who is affected) and search open issues and recent PRs for a duplicate.

Spawn **debugger** agent to:
- Reproduce the issue (or confirm CVE applicability)
- Trace through the code to isolate the root cause
- Apply 5 Whys methodology
- Produce a structured RCA report with fix recommendations

If the debugger's confidence is low, stop here. Comment the findings on the source issue and do not implement a speculative fix.

### Step 3: Solution Design (Architect Handoff)
Spawn **architect** agent to evaluate the fix options from the RCA report:
- Assess blast radius of each fix option
- Evaluate trade-offs (quick fix vs proper fix vs redesign)
- Consider impact on other components, API contracts, database schema
- Recommend the approach with the best risk/effort/quality balance

Present the architect's evaluation to the user with fix options:
- Option A: Quick fix (patch the symptom)
- Option B: Proper fix (address the root cause)
- Option C: Architectural fix (if applicable)

Ask user: "Which fix approach do you prefer? (A/B/C or suggest alternative)"

### Step 4: Create Issue (if not from existing issue)
If the investigation didn't start from a GitHub issue:
```bash
gh label create "bug" --color "d73a4a" 2>/dev/null || true
gh issue create --title "fix: <description>" --label "bug" --body "<RCA summary + chosen fix>"
```

### Step 5: Implement Fix
Based on the chosen approach:
- Create a fix branch: `fix/issue-N-description`
- Apply the code changes
- Add regression test that would have caught this
- Run existing tests to verify no regressions

### Step 6: Verify
- Run the verification loop: build → type check → lint → test
- If the original bug had reproduction steps, verify the fix resolves it
- Run security scan if CVE-related

### Step 7: Create PR
Push and create PR with:
- RCA summary in the PR body
- `Closes #N` linking to the bug issue
- Before/after code comparison
- Test results

## Output
- RCA report with root cause identified
- Fix implemented and tested
- PR created closing the bug issue

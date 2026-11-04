---
description: "Run security-focused code review targeting OWASP Top 10 and common vulnerabilities"
allowed-tools: Read, Glob, Grep, Bash, Agent
---

# Security Review

Perform a security-focused code review.

## Input
$ARGUMENTS — Target for review. Can be a file, directory, or git range. Defaults to `solution/`.

## Process

1. **Spawn security-reviewer agent** to perform the review
2. The agent will scan for:
   - OWASP Top 10 vulnerabilities
   - Hardcoded secrets and credentials
   - Authentication and authorization flaws
   - Input validation gaps
   - Dependency vulnerabilities
3. Run automated security tools:
   - Python: `bandit`, `safety check`
   - Node.js: `npm audit`
4. Review findings and provide remediation steps

## Output
Security assessment report with:
- Findings by severity (critical/high/medium/low/info)
- CWE references where applicable
- Specific remediation steps for each finding
- Overall security posture assessment

---
description: "Create a GitHub issue with Mermaid diagrams using gh CLI"
allowed-tools: Read, Glob, Grep, Bash, AskUserQuestion
---

# Create Issue

Create a well-structured GitHub issue using `gh` CLI with Mermaid diagrams and proper labeling.

## Input
$ARGUMENTS — Description of the issue to create. Can include type prefix (feat:, fix:, docs:).

## Process

1. **Load git-workflow skill** from `skills/foundation/git-workflow/SKILL.md`
2. **Determine issue type** from $ARGUMENTS or ask user:
   - `feat:` → Enhancement issue with `enhancement` label
   - `fix:` → Bug report with `bug` label
   - `docs:` → Documentation issue with `documentation` label
   - `refactor:` → Technical debt with `refactor` label
   - `infra:` → Infrastructure issue with `infrastructure` label
3. **Generate issue body** based on type:

   **For features:**
   - Summary, motivation, acceptance criteria
   - Mermaid diagram showing the feature's flow or architecture impact
   - Technical notes and dependencies

   **For bugs:**
   - Description, steps to reproduce, expected vs actual
   - Environment details
   - Error output if available

   **For architecture/design:**
   - Context, options considered with Mermaid diagrams
   - Recommendation with trade-off analysis

4. **Create issue** using `gh issue create`
5. **Return issue URL and number** for linking in commits/PRs

## Output
- Issue created with rich body including Mermaid diagrams
- Issue URL and number for reference

## Examples
```
/create-issue feat: add user registration with email verification
/create-issue fix: token expiry causes 500 error on refresh
/create-issue refactor: extract authentication into middleware
```

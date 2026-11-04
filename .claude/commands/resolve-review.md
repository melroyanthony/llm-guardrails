---
description: "Resolve independent-reviewer comments from GitHub or the review channel, then apply the merge gate"
argument-hint: "<PR number>"
allowed-tools: Read, Glob, Grep, Edit, Write, Bash, AskUserQuestion, Agent
---

# Resolve Review

Automated workflow for addressing PR review comments with root-cause analysis, sibling scanning, pre-push verification, and inline replies.

## Input
$ARGUMENTS — PR number. If empty, uses the current branch's PR.

## Process

### Phase 1: Read the review of this head

```bash
# Use $ARGUMENTS if provided, otherwise detect from current branch
if [ -n "$ARGUMENTS" ]; then
  PR_NUMBER=$ARGUMENTS
else
  PR_NUMBER=$(gh pr view --json number -q .number)
fi
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
```

Read the head SHA. Confirmation is a message from the Independent reviewer named under `## Review`, posted in the `Channel`, that quotes the full head SHA and explicitly confirms it. The author's review request, a lead note, a hold, and a request-changes message do not confirm, even when they quote the SHA. A blank GitHub login does not block that channel confirmation. Silence means the request is still open. Stop. Silence is not a clean review.

```bash
HEAD_SHA=$(gh pr view "${PR_NUMBER}" --json headRefOid --jq '.headRefOid')
AUTHOR=$(gh pr view "${PR_NUMBER}" --json author --jq '.author.login')
# GitHub reviews of this head. This is not the only confirmation.
gh api "repos/${REPO}/pulls/${PR_NUMBER}/reviews" \
  --jq "[.[] | select(.commit_id == \"${HEAD_SHA}\" and .user.login != \"${AUTHOR}\")] | last | .commit_id // \"\""
```

Also read the channel named under `## Review`. A message there from the named independent reviewer is a pass on this head. It confirms only when it quotes `${HEAD_SHA}` and explicitly confirms. A hold or a request-changes message in that channel is not confirmation. When `GitHub login` is set, a GitHub review from that login confirms only on the same terms: it quotes the SHA and explicitly confirms. Findings may be in the channel or in the GitHub review comments. Read both before fixing. The loop that decides depth, rounds, holds, and escalation is `skills/foundation/review-loop-to-squash-merge/SKILL.md`.

### Phase 2: Fetch and Understand ALL Comments

Read the GitHub review comments and the review-channel messages for this head SHA. A channel confirmation with no findings is a clean pass for that part.

```bash
gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
  --jq '.[] | {id: .id, path: .path, body: .body, line: .line, original_line: .original_line}'
```

**Read ALL comments before fixing ANY.** Do not start applying fixes after reading the first comment.

### Phase 3: Group by Root Cause

Multiple comments may share a single root cause. Group them before acting:

| Pattern | Example | Root Cause |
|---|---|---|
| Same bug in different files | "PCRE grep here" + "PCRE grep there" | Non-portable shell commands |
| Inconsistency between sections | "Docstring says X" + "Key Rules say Y" | One change wasn't propagated |
| Stack-specific term in shared section | "asyncpg in Node.js context" | Copy-paste from wrong stack section |
| Missing edge case | "Doesn't handle empty input" | No guard clause on boundary |

For each root-cause group:
1. **What's wrong?** — the specific issue
2. **Why is it wrong?** — the underlying cause (not just the symptom)
3. **What else might be affected?** — scan for siblings

### Phase 4: Scan for Siblings

Before fixing the flagged instance, search for ALL instances of the same pattern:

```bash
# If reviewer flagged a non-portable grep flag:
grep -Ern "grep -P|grep -oP" .claude/

# If reviewer flagged a stack-specific term in a shared section:
grep -Ern "asyncpg|Pydantic" .claude/agents/  # Check if it's in stack-agnostic context

# If reviewer flagged a docstring/behavior mismatch:
# Read the surrounding context — do other bullets/comments match the code?
```

Fix ALL siblings, not just the one the reviewer flagged. Don't make the reviewer find the other instances in the next round.

### Phase 5: Categorize Each Comment

For each comment, determine the action:

| Category | Criteria | Action |
|----------|----------|--------|
| **Fix** | Legitimate issue — bugs, incorrect values, portability, inconsistencies. Verify the comment against the code before applying it; a suggestion is not an order (adapted from Jesse Vincent, `receiving-code-review`, MIT) | Apply fix across all siblings |
| **Acknowledge** | Valid observation but intentional design choice | Reply with rationale |
| **Dismiss** | False positive, already addressed, or reviewer misread the code | Reply with explanation |

### Phase 6: Apply Fixes with Internal Consistency Check

For each "Fix" root-cause group:

1. **Read the full file context** (not just the flagged line) — understand what surrounds the change
2. **Apply the fix** — may touch multiple files if the root cause is shared
3. **Re-read the surrounding context after the fix** — check for new inconsistencies:
   - Does the fix contradict other guidance in the same section?
   - Does a docstring/comment still match the code?
   - Does a "Key Rules" or "Anti-Patterns" section still align with examples?
   - Are cross-references to other skills/agents still accurate?
4. **For code examples in markdown** — mentally execute: would this run on macOS (bash 3.2, BSD grep) and Linux?

### Phase 7: Pre-Push Verification

**Do NOT push until verification passes.** This is the critical step that prevents cascading review rounds.

#### For source code changes:
```bash
# Run the relevant test suite
uv run pytest tests/ -v    # Python
npm test                    # Node.js
```

#### For config/markdown changes (skills, agents, commands):
- **Shell commands in code blocks**: Verify portability (no PCRE, no GNU-only flags, bash 3.2 compatible)
- **Cross-references**: If skill A references skill B, verify skill B exists and the reference is accurate
- **Internal consistency**: Every code example must match its surrounding description
- **Frontmatter**: Verify required fields by file type (commands: `description`, `allowed-tools`; skills/agents: `name`, `description`)

#### For hook scripts:
```bash
# Verify bash 3.2 compatibility
bash --version  # Check available version
bash -n .claude/hooks/scripts/*.sh  # Portable syntax check (shellcheck not in allowed permissions)
```

If verification fails, fix the regression BEFORE proceeding to commit.

### Phase 8: Commit and Push

```bash
# One commit per root-cause group (not per comment, not monolithic)
git add <specific-files-changed>
git commit -m "🐛 fix(review): address findings on pr #${PR_NUMBER}

- [root-cause group 1]: [what was fixed across N files]
- [root-cause group 2]: [what was fixed]

Refs #[issue]"
git push origin <branch>
```

**Important**: Use specific file paths in `git add`, not `git add -A`.

### Phase 9: Reply Inline to Each Comment

Reply directly to each review comment using the GitHub API:

```bash
gh api "repos/${REPO}/pulls/${PR_NUMBER}/comments" \
  -f body="<response>" \
  -F in_reply_to=<comment_id>
```

**Reply format by category**:

- **Fix**: `"Fixed in <sha> — <what was changed>. Also fixed N sibling instances."`
- **Acknowledge**: `"Intentional — <rationale for the design choice>."`
- **Dismiss**: `"False positive — <explanation of why this isn't an issue>."`

Keep replies concise (1-2 sentences). Reference the commit SHA for fixes.

### Phase 10: Post Summary Comment on PR

```bash
gh pr comment ${PR_NUMBER} --body "## Review Resolution (round N — M comments)

| Category | Count | Details |
|----------|-------|---------|
| Fixed | X | Committed in <sha> |
| Acknowledged | Y | Intentional design choices |
| Dismissed | Z | False positives |

### Root-Cause Groups Fixed
| # | Root Cause | Comments Addressed | Files Changed | Siblings Found |
|---|------------|-------------------|---------------|----------------|
| 1 | <root cause> | <comment IDs> | <N files> | <M siblings> |

### Fixed
| # | Finding | File | Fix |
|---|---------|------|-----|
| 1 | <finding summary> | <path> | <what was done> |

### Acknowledged
| # | Finding | File | Response |
|---|---------|------|----------|
| 1 | <finding summary> | <path> | <rationale> |

### Dismissed
| # | Finding | File | Reason |
|---|---------|------|--------|
| 1 | <finding summary> | <path> | <why dismissed> |"
```

### Phase 11: Next review round

A round is the independent reviewer's pass on one head SHA. The first head they review is round 1. A further review of that same SHA stays in the round. The next round starts after a push, when they review the new head. Self-review is not a round.

After pushing, the next round starts. Merge only after Phase 12 is done for that head.

1. Re-read the head SHA. A GitHub review of an older SHA leaves this step open. A channel message from the named independent reviewer is a pass on this head. It confirms only when it quotes this full head SHA and explicitly confirms. A hold or a request-changes message does not confirm. Stop until that reviewer has passed on this head in the channel or on GitHub.
2. If the author and the reviewer disagree about the diff, the depth, or whether the head can merge, stop. Escalate to the lead with the PR link, the full head SHA, the round count, and both positions.
3. If this pass is not a confirmation and the round count is 3, stop. Escalate to the lead with the PR link, the full head SHA, the round count, and the open comments. A hold on round 3 escalates too.
4. If the reviewer holds and the round count is under 3, the merge stays blocked. A fix push starts the next round. The lead may waive this SHA.
5. If this pass has comments and the round count is under 3, go back to Phase 2. Push the fixes once.
6. If the named independent reviewer explicitly confirms this full head SHA, and the message is not a hold or a request for changes, run Phase 12.

### Phase 12: Merge gate

Follow `skills/foundation/review-loop-to-squash-merge/SKILL.md`.

- Required CI is green for this head.
- The named independent reviewer has explicitly confirmed this full head SHA in the review channel, or the lead has waived a hold by naming the hold and quoting this full head SHA. A hold or a request-changes message does not confirm. When `GitHub login` is set, a GitHub review from that login confirms only when it quotes the SHA and explicitly confirms.
- A hold blocks the merge until a later commit fixes it or that waiver exists. Silence leaves the merge blocked.
- A new head voids the confirmation and any waiver. Return to Phase 1.
- When the human has asked to merge, re-read the head SHA. If it moved, stop. Otherwise append the record to the pull request body, keeping the existing body. On confirmation:

`<reviewer>` is the Independent reviewer named under `## Review`.

```text
Reviewed by <reviewer> at `<full sha>`

Findings:
- <finding, or none>
```

On a lead waiver, append `Lead waived the hold at \`<full sha>\`` and the findings instead. Then run `gh pr merge <number> --squash --delete-branch`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's just one comment, I'll fix it and push quickly" | One fix without context checking creates one inconsistency caught in the next round. Read all comments first. |
| "The fix is obvious, no need to scan for siblings" | If the reviewer found one instance, there are probably more. Grep before fixing. |
| "It's just markdown, no verification needed" | Code examples in markdown run on real machines. A non-portable grep wastes the reviewer's time. |
| "I'll merge now and fix the remaining comments in a follow-up" | Follow-up PRs for review comments are tech debt that never gets paid. Fix them now. |
| "The reviewer approved, so the head SHA is confirmed" | Confirmation is an explicit confirm from the named independent reviewer that quotes the full head SHA. An approval that omits the SHA, a hold, and a request-changes message leave the gate closed. |
| "Three rounds is close enough to keep patching" | Round 3 without confirmation goes to the lead. A disagreement goes to the lead at once. |

## Red Flags

- Pushing without reading all comments first (fixing one at a time)
- Fixing only the flagged instance without scanning for siblings
- Not re-reading surrounding context after applying a fix
- Merging before the independent reviewer has reviewed this head
- Merging while required CI is red, or while this head lacks a confirmation or a lead waiver
- Merging over a hold the lead has not waived for this head SHA
- Reusing a confirmation or a waiver after the head moved
- Opening a fourth fix round, or patching through a disagreement

## Output
- Fixes committed and pushed (grouped by root cause)
- Each comment has an inline reply in its thread
- Summary comment posted on PR with root-cause analysis table
- The independent reviewer's confirmation, or the lead's waiver, quotes this full head SHA
- The pull request body records that SHA and the findings before squash-merge

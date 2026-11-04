---
description: Triage review comments on a pull request and fix them in groups.
---

# Resolve review

Argument: the pull request number or URL.

1. Wait until the latest review `commit_id` equals the pull request head SHA. If it does not,
   say so and stop.
2. Read every comment. Group them by root cause.
3. Fix each group once. Re-run the verification phases the fix can affect.
4. Push the feature branch. Do not force-push.
5. Reply inline on the thread (`in_reply_to` where the forge supports it) and post a short
   summary table: comment, cause, what changed.
6. Repeat until the comments you can act on are answered. Do not merge.

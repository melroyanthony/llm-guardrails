---
description: Review the current diff on two axes, standards and spec fidelity.
---

# Review

Read the diff against `main`. Report two separate lists.

**Standards.** `AGENTS.md` conventions: uv, ruff, clippy `-D warnings`, thin Python wrappers,
no invented configuration, no Python newer than `.python-version`, no package rename, no push to `main`.

**Spec fidelity.** What the requested change asked for, and what the diff actually does.

Findings first, by severity. Do not rewrite the diff in the same breath as the review unless
the human asked for fixes.

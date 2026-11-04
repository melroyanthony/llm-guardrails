---
description: Implement one issue with tests, then stop.
---

Read the issue. Read `AGENTS.md`.

Agree the seams, then make one failing test pass at a time. Rust tests live in `src/`. Python tests live in `tests/`. Mock only at process boundaries.

Verify with the commands in `AGENTS.md` that the diff can affect. Read the output.

Commit a meaningful unit when it is green. Open or update the pull request. Do not merge. Do not start the next issue.

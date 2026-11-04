---
name: implement
description: Implement one ticket on this library. Use when a spec or issue is ready to build.
---

# Implement

Do one ticket, then stop and name the next unblocked ticket. Do not start it.

1. Read the ticket, `AGENTS.md`, and the modules it names. State assumptions that are still open.
2. Load `tdd`. Agree the seams before writing production code.
3. Red, then green, then refactor, one test at a time.
4. Run the commands in `AGENTS.md` § Commands that the diff can affect. Read the output.
5. Load `verification-loop` before claiming done.
6. Load `git-workflow` for the commit and the pull request. Do not merge.

A success claim needs command output from this session. If a tool is missing, say so.

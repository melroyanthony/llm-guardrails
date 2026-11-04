---
description: Create one commit that follows the hybrid gitmoji subject.
---

# Commit

Load `.claude/skills/git-workflow/SKILL.md`.

1. Read `git status` and `git diff`. Stage one logical change.
2. Subject: `<emoji> <type>(<scope>): <lower-case imperative>`, under 72 characters.
3. Body says why. No attribution trailer.
4. Run the verification phases the diff can affect before committing, unless the human
   explicitly asked to commit a known failure.
5. Do not push unless asked. Never push to `main`.

---
description: Open a pull request. Do not merge it.
---

# Create a pull request

Load `.claude/skills/git-workflow/SKILL.md` and `.claude/skills/diagrams/SKILL.md`.

1. The title is the hybrid subject.
2. The body has What and why, Evidence, Merge danger, and Breaking changes.
3. Link `Closes #N` when an issue exists.
4. Push the feature branch with `git push -u origin <branch>`. Never force-push. Never push `main`.
5. `gh pr create`. Do not merge.

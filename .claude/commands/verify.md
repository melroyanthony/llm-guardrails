---
description: Run the verification loop and report pass, fail, or not run for each phase.
---

# Verify

Load `.claude/skills/verification-loop/SKILL.md` and run it. Report one line per phase:

`build`, `types`, `lint`, `test`, `security`, `diff`.

Do not say the change is done while any phase you could run is failing. Do not install a
typechecker or a new linter in order to tick a box.

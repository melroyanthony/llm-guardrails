#!/usr/bin/env python3
"""Claude Code hook JSON. Exit 0 so the decision is read.

permissionDecision "ask" prompts the human. "deny" stops the tool and the
reason is shown to the model. additionalContext is how a warning reaches the
model: stderr with exit 0 is not.
"""

from __future__ import annotations

import json
import sys


def emit(
    event: str, reason: str, decision: str | None = None, context: str | None = None
) -> None:
    payload: dict[str, object] = {
        "hookEventName": event,
        "additionalContext": context or reason,
    }
    if decision:
        payload["permissionDecision"] = decision
        payload["permissionDecisionReason"] = reason
    sys.stdout.write(json.dumps({"hookSpecificOutput": payload}))

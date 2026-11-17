"""Property-test budget. CI repeats the same Hypothesis seed."""

from __future__ import annotations

import os
from datetime import timedelta

# GitHub Actions sets CI. The seed is fixed there and left unset locally.
if os.environ.get("CI"):
    os.environ["HYPOTHESIS_SEED"] = "20261113"

from hypothesis import settings  # noqa: E402

settings.register_profile(
    "bounded",
    max_examples=20,
    deadline=timedelta(milliseconds=500),
)
settings.load_profile("bounded")

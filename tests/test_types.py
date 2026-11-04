"""The installed package is typed, including the native module."""

import subprocess
import sys
from pathlib import Path

import llm_guardrails
import llm_guardrails._core as core

PACKAGE = Path(llm_guardrails.__file__).resolve().parent
NATIVE_FUNCTIONS = (
    "pii_redact",
    "pii_restore",
    "injection_score",
    "injection_analyse",
    "injection_list_rules",
    "bias_score",
    "output_validate",
)


def test_package_ships_py_typed_and_core_stub():
    assert (PACKAGE / "py.typed").is_file()
    stub = (PACKAGE / "_core.pyi").read_text(encoding="utf-8")
    for name in NATIVE_FUNCTIONS:
        assert f"def {name}(" in stub
        assert callable(getattr(core, name))


def test_mypy_accepts_the_public_package():
    root = PACKAGE.parent
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "llm_guardrails"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

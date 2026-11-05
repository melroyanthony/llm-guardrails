"""The homepage example is the script CI runs."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
QUICKSTART = ROOT / "docs" / "examples" / "quickstart.py"
RESTORE = ROOT / "docs" / "examples" / "restore.py"


def _run(path: Path) -> str:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_homepage_includes_and_runs_the_quickstart():
    assert '--8<-- "examples/quickstart.py"' in INDEX
    assert "pip install ferroguard" in INDEX
    assert "llm_guardrails" in INDEX
    stdout = _run(QUICKSTART)
    assert stdout == "Mail <<EMAIL_1>> about the notes.\nblocked False\n"
    assert "Mail <<EMAIL_1>> about the notes." in INDEX
    assert "blocked False" in INDEX


def test_homepage_is_install_then_code():
    assert "fg-features" not in INDEX
    assert "fg-kicker" not in INDEX
    assert "fg-hero" not in INDEX
    install_at = INDEX.index("pip install ferroguard")
    example_at = INDEX.index('--8<-- "examples/quickstart.py"')
    assert install_at < example_at


def test_restore_example_runs():
    install = (ROOT / "docs" / "install.md").read_text(encoding="utf-8")
    assert '--8<-- "examples/quickstart.py"' in install
    assert '--8<-- "examples/restore.py"' in install
    assert _run(RESTORE) == "Noted.\nTrue\n0.0\n"

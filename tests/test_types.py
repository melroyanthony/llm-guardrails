"""The installed package is typed, including the native module."""

from pathlib import Path

import mypy.api

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


def _mypy(path: Path) -> tuple[str, int]:
    stdout, stderr, code = mypy.api.run(
        [
            "--config-file",
            str(PACKAGE.parent / "pyproject.toml"),
            str(path),
        ]
    )
    return stdout + stderr, code


def test_mypy_accepts_the_public_package():
    output, code = _mypy(PACKAGE)
    assert code == 0, output


def test_installed_mypy_is_2():
    from importlib.metadata import version

    major, minor, patch = (int(part) for part in version("mypy").split(".")[:3])
    assert (major, minor, patch) >= (2, 4, 1)
    assert major < 3


def test_mypy_rejects_a_bare_str_for_vec_string_params(tmp_path: Path):
    bare = tmp_path / "bare_str.py"
    bare.write_text(
        "from llm_guardrails._core import output_validate, pii_redact\n"
        "pii_redact('x', 'EMAIL')\n"
        "pii_redact('x', deny_entities='EMAIL')\n"
        "output_validate('x', required_keywords='please')\n"
        "output_validate('x', blocked_keywords='nope')\n",
        encoding="utf-8",
    )
    errors, code = _mypy(bare)
    assert code != 0, errors
    assert errors.count("error:") >= 4

    accepted = tmp_path / "string_lists.py"
    accepted.write_text(
        "from llm_guardrails._core import output_validate, pii_redact\n"
        "pii_redact('x', ['EMAIL'], ('PHONE',))\n"
        "output_validate('x', required_keywords=['please'], blocked_keywords=('nope',))\n",
        encoding="utf-8",
    )
    output, code = _mypy(accepted)
    assert code == 0, output

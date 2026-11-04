# Changelog

## Unreleased

### Breaking changes

* The PyPI distribution name is `ferroguard`. Install with `pip install ferroguard` and keep `import llm_guardrails`. `importlib.metadata.version("llm_guardrails")` no longer finds the package; use `ferroguard`. `GET /health` reports that distribution version.

### Features

* A release builds one abi3-py311 wheel each for Linux manylinux (x86_64 and aarch64), macOS (x86_64 and arm64), and Windows x86_64, plus an sdist, and publishes them from `release.yml` with PyPI trusted publishing. The GitHub Release gets an SPDX SBOM of those artifacts. CI builds a wheel and imports it on Python 3.11 and 3.14.

## [0.3.0](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.3.0) (2026-11-04)

### Breaking changes

* `PIIRedactor.allow_entities` and `deny_entities` are read-only. Assigning either one after construction raises `AttributeError`. Each value is a tuple, or `None`, and cannot be changed in place. Pass the labels to the constructor.

### Features

* The package ships `py.typed` and `llm_guardrails/_core.pyi`, so type checkers see the native module. CI runs mypy on `llm_guardrails/`.

## [0.2.8](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.8) (2026-11-04)

### Breaking changes

* `/guard/input` no longer returns the PII mapping. It returns an opaque `pii_mapping_id`, and the server keeps a non-empty map in process memory for 15 minutes. The id is single-use: `/guard/output` pops it, and a second call is 404, the same as an unknown or expired id. Ids work only for one worker or replica and are lost on restart. `/guard/full` does not store a map. `/guard/output` rejects a client-supplied mapping. An unknown field on `/guard/input` or `/guard/full` is 422. Request `text` is limited to 8000 characters (422). Request bodies over 32768 bytes are rejected with 413.

### Bug Fixes

* `GET /health` reports the installed `llm_guardrails` version from package metadata instead of a hard-coded 0.1.0. The demo builds `GuardrailsPipeline` on first use, not at import. `python-dotenv` is no longer a core dependency.

## [0.2.7](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.7) (2026-11-04)

### Bug Fixes

* Injection rules run on normalised text (NFKC, invisible characters removed, common homoglyphs folded, spaced-out letters collapsed). A standalone spaced run still needs four letters. Once that run has started, two or more spaces are a word break emitted as one space, and a later spaced word of three letters collapses too, so "i g n o r e  a l l  p r e v i o u s  i n s t r u c t i o n s" and "ignore a l l previous instructions" score like the plain phrase. "I a m fine" still scores 0.
* The DAN rule is case-sensitive. A name such as "Dan" is no longer flagged. Only the uppercase token DAN, or the phrase "do anything now" in any case, matches. There is no switch that restores the old case-insensitive DAN match.

## [0.2.6](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.6) (2026-11-04)

### Bug Fixes

* NAME and DATE_OF_BIRTH are redacted only next to a context word such as "name", "born", "DOB", "Dr.", or "Ms.". The default redacts less: "Jane Doe called" is no longer redacted. There is no option that restores the old behaviour of matching every title-case pair or every date.

## [0.2.5](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.5) (2026-11-04)

### Documentation

* docs: community files, pre-commit and justfile

## [0.2.4](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.4) (2026-11-04)

### Build

* build(deps): bump the cargo group with 4 updates

## [0.2.3](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.3) (2026-11-04)

### Bug Fixes

* fix(release): allow notes under Unreleased in changelog check

## [0.2.2](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.2) (2026-11-04)

### Bug Fixes

* fix(release): accept any version below empty Unreleased

## [0.2.1](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.1) (2026-11-04)

### Chores

* chore(conf): roll out sdlc conf

## [0.2.0](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.0) (2026-02-17)

### Added

* Python library for PII redaction, prompt-injection scoring, bias scoring, and output validation, with a FastAPI demo
* Rust core for those guards, exposed to Python through PyO3

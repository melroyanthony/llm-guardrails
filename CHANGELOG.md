# Changelog

## Unreleased

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

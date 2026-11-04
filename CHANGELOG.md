# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Release notes are written under `Unreleased`. `scripts/release_subject.py` moves
that section into the next version.

## Unreleased

## [0.2.0](https://github.com/melroyanthony/llm-guardrails/releases/tag/v0.2.0) (2026-02-17)

### Added

* Python library for PII redaction, prompt-injection scoring, bias scoring, and output validation, with a FastAPI demo
* Rust core for those guards, exposed to Python through PyO3

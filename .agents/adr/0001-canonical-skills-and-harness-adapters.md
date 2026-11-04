# ADR-0001: Canonical Skills Catalog and Harness Adapters

## Status

Superseded by the flat layout in `AGENTS.md` (2026-10-21).

`.claude/skills/<name>/` is the committed discovery root. `.agents/skills/` is gitignored and created with `bash scripts/install-harness.sh codex`. The sections below record the earlier nested layout.

## Context

This repository began as a Claude Code plugin (`.claude/skills`, agents, commands, hooks). Reference systems (mattpocock/skills, addyosmani/agent-skills, affaan-m/ECC) show that portable Agent Skills catalogs outlive any single harness. We need one source of truth for skill content while keeping the Stages 0–5 SDLC pipeline and Claude plugin packaging.

## Decision

1. **Canonical catalog** lives at repo-root `skills/` (Agent Skills standard layout: `skills/<category>/<name>/SKILL.md`).
2. **Claude adapter** is `.claude/skills/<category>/<name>/`, a symlink written by `scripts/sync-skills.sh`. Flat `.agents/skills/<name>/` points at the same directory. Edit `skills/` only; sync before commit/release. Do not copy skills into `.cursor/skills/` or `.github/skills/`.
3. **Hybrid product posture**:
   - Greenfield: Stages 0–5 via `/orchestrate` (pipeline owns the process).
   - Daily change work: composable skills (`grilling` → `to-spec` → `to-tickets` → `implement`).
4. **Invocation taxonomy** (Pocock):
   - Model-invoked: default; rich trigger description; agent may auto-load.
   - User-invoked: `disable-model-invocation: true`; one-line human description; human (or slash command) must invoke.
   - User-invoked skills may call model-invoked skills; never chain user-invoked → user-invoked.
5. **Progressive disclosure**: `SKILL.md` target ≤350 lines, hard fail >500; bulk in `references/` or sibling docs with one-level pointers.
6. **Harness-agnostic surface**: root `AGENTS.md` + `docs/harness/*`. Optional per-skill `agents/openai.yaml` for Codex. No full ECC multi-folder install matrix in v1.

## Consequences

- Skill install via `npx skills add` can target top-level `skills/`.
- Claude plugin continues to ship `.claude/skills/` (synced copy).
- CI must run `scripts/sync-skills.sh --check` to prevent adapter drift.
- Path references in agents/commands may use `.claude/skills/...` (adapter) or `skills/...` (canonical); both resolve after sync.

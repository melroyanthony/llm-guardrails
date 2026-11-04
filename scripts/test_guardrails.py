#!/usr/bin/env python3
"""Behaviour checks for the committed git and stack guardrail hooks."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks" / "scripts"


def load(name: str, directory: Path = HOOKS):
    """Load a module by file so the test does not need a package."""
    path = directory / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """Exit non-zero when a guardrail regresses."""
    os.chdir(ROOT)
    git = load("git_guardrails")
    commits = load("commit-style")
    stack = load("stack_guardrails")

    expect(git.needs_ask("git push origin feat/issue-1-bootstrap") is None, "plain push")
    expect(git.needs_ask("git push --force origin main") == "force-push", "force")
    expect(git.needs_ask("git push --force-with-lease") == "force-push", "lease")
    expect(git.needs_ask("git reset --hard HEAD") == "git reset --hard", "reset")
    expect(git.needs_ask("git clean -fd") == "git clean -f", "clean")
    expect(git.needs_ask("git branch -D old") == "git branch -D", "branch")
    expect(git.needs_ask("git commit --no-verify -m 'x'") is not None, "no-verify")

    good = 'git commit -m "🎉 chore(repo): bootstrap the workspace"'
    code, warning = commits.decision(good, profile="standard")
    expect(code == 0 and warning is None, "good subject")
    code, warning = commits.decision('git commit -m "fix the bug"', profile="strict")
    expect(code == 2 and warning is not None, "strict deny")
    code, warning = commits.decision('git commit -m "fix the bug"', profile="standard")
    expect(code == 0 and warning is not None, "standard warn")

    expect(stack.blocked_reason("npm publish") is not None, "npm publish")
    expect(stack.blocked_reason("npm publish --dry-run") is None, "dry run")
    expect(stack.blocked_reason("uv publish") is not None, "uv publish")
    expect(stack.blocked_reason("railway up") is not None, "railway")
    expect(stack.blocked_reason("cargo test") is None, "cargo test")
    expect(stack.lockfile_warning("uv.lock") is not None, "uv.lock")
    expect(stack.lockfile_warning("Cargo.lock") is None, "cargo lock")
    check_harness_copy()
    check_release_bumps()
    print("guardrail tests ok")
    return 0


def check_harness_copy() -> None:
    """The helper must keep the upstream `.claude` directory name."""
    script = ROOT / "scripts" / "install-harness-from.sh"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src = root / "conf"
        (src / ".claude" / "skills").mkdir(parents=True)
        (src / "AGENTS.md").write_text("agents\n", encoding="utf-8")
        (src / ".claude" / "skills" / "demo.md").write_text("skill\n", encoding="utf-8")
        work = root / "work"
        work.mkdir()
        subprocess.run(
            ["bash", str(script), str(src)],
            cwd=work,
            check=True,
            capture_output=True,
            text=True,
        )
        copied = work / ".claude" / "upstream" / ".claude" / "skills" / "demo.md"
        expect(copied.is_file(), "upstream .claude path")
        expect((work / ".claude" / "upstream" / "AGENTS.md").is_file(), "upstream agents")
        expect(not (work / ".claude" / "upstream" / "claude").exists(), "no dropped dot")


def check_release_bumps() -> None:
    """0.x breaking changes stay minor. 1.x breaking changes are major."""
    release = load("release_subject", ROOT / "scripts")
    breaking = "💥 feat(api)!: replace ids\n"
    zero = release.decide(breaking, "0.4.0", None)
    expect(zero["version"] == "0.5.0", "0.4.0 breaking version")
    expect(zero["bump"] == "minor", "0.4.0 breaking bump")
    expect(zero["changes"][0]["section"] == "Breaking changes", "0.4.0 breaking section")
    footer = "🐛 fix(api): change the envelope\n\nBREAKING CHANGE: error shape\n"
    expect(release.decide(footer, "0.4.0", None)["version"] == "0.5.0", "0.4.0 footer")
    one = release.decide(breaking, "1.2.3", None)
    expect(one["version"] == "2.0.0", "1.2.3 breaking version")
    expect(one["bump"] == "major", "1.2.3 breaking bump")
    expect(one["changes"][0]["section"] == "Breaking changes", "1.2.3 breaking section")
    expect(release.bump_version("0.4.0", "major") == "0.5.0", "bump_version below 1.0")
    expect(release.bump_version("1.2.3", "major") == "2.0.0", "bump_version from 1.0")
    feat = release.decide("✨ feat(api): stream a turn\n", "0.4.0", None)
    expect(feat["bump"] == "minor" and feat["version"] == "0.5.0", "feat is minor")
    for subject, label in (
        ("🐛 fix(api): close the stream\n", "fix"),
        ("✅ test(api): cover the stream\n", "test"),
        ("📝 docs(api): describe the stream\n", "docs"),
    ):
        decision = release.decide(subject, "0.4.0", None)
        expect(decision["action"] == "publish", f"{label} still releases")
        expect(decision["bump"] == "patch" and decision["version"] == "0.4.1", f"{label} is patch")
    prose = (
        "👷 ci(release): bump minor on breaking changes while below 1.0\n\n"
        "The only change is a breaking marker (`!` or `BREAKING CHANGE:`) while the major is 0.\n"
    )
    prose_decision = release.decide(prose, "0.6.1", None)
    expect(
        prose_decision["bump"] == "patch" and prose_decision["version"] == "0.6.2",
        "prose mention is patch",
    )
    backticks = "🐛 fix(api): close the stream\n\n`BREAKING CHANGE: error shape`\n"
    tick_decision = release.decide(backticks, "0.6.1", None)
    expect(
        tick_decision["bump"] == "patch" and tick_decision["version"] == "0.6.2",
        "backtick mention is patch",
    )
    inline = "📝 docs(api): describe the marker\n\nSee BREAKING CHANGE: error shape in the notes.\n"
    inline_decision = release.decide(inline, "0.6.1", None)
    expect(
        inline_decision["bump"] == "patch" and inline_decision["version"] == "0.6.2",
        "inline mention is patch",
    )
    ignored = "update the readme\n\nBREAKING CHANGE: error shape\n"
    expect(release.decide(ignored, "0.6.1", None)["action"] == "skip", "non-type stays none")
    real_footer = "🐛 fix(api): change the envelope\n\nBREAKING CHANGE: error shape\n"
    real = release.decide(real_footer, "0.6.1", None)
    expect(
        real["bump"] == "minor" and real["version"] == "0.7.0", "footer line is breaking below 1.0"
    )
    expect(real["changes"][0]["section"] == "Breaking changes", "footer section")
    hyphen_footer = "🐛 fix(api): change the envelope\n\nBREAKING-CHANGE: error shape\n"
    hyphen = release.decide(hyphen_footer, "1.2.3", None)
    expect(
        hyphen["bump"] == "major" and hyphen["version"] == "2.0.0",
        "hyphen footer is breaking from 1.0",
    )
    expect(zero["bump"] == "minor", "subject bang is breaking")


def expect(condition: bool, label: str) -> None:
    """Stop at the first failed check."""
    if not condition:
        raise SystemExit(f"failed: {label}")


if __name__ == "__main__":
    sys.exit(main())

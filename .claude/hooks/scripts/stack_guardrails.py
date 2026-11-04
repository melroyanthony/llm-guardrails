#!/usr/bin/env python3
"""Opt-in stack guardrails for Claude Code hooks and the verify harness.

The hook never pushes, force-pushes, or deploys. Deploy-shaped commands are
blocked when guardrails are enabled. Lint and version mismatches warn in
standard mode and block only in strict mode.

Enable with SDLC_STACK_GUARDRAILS=1 or a file .claude/stack-guardrails.enabled
at the repo root. SDLC_STACK_GUARDRAILS=0 forces them off. SDLC_HOOK_PROFILE=minimal
skips the hook entirely.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None  # type: ignore[assignment]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_segments import argv_of, split_segments
from hook_output import emit

_SKIP_DIR_NAMES = {"node_modules", ".git", "dist", "build", ".venv", "venv"}
_TOOL_TABLE = re.compile(r"(?m)^\[tool\.(uv|ruff|pyright|mypy)(\]|\.)")
_SHELLS = {"bash", "sh", "zsh", "dash"}
_REFUSAL = ". Refusing. This hook does not deploy or publish."

LOCKFILES = {
    "uv.lock": "uv lock",
    "pnpm-lock.yaml": "pnpm install",
    "package-lock.json": "npm install",
    "yarn.lock": "yarn",
}

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"
)


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return current


def enabled(root: Path) -> bool:
    flag = os.environ.get("SDLC_STACK_GUARDRAILS", "").strip().lower()
    if flag in {"0", "false", "off", "no"}:
        return False
    if flag in {"1", "true", "on", "yes"}:
        return True
    if (root / ".claude" / "stack-guardrails.enabled").is_file():
        return True
    project = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    return (
        bool(project)
        and (Path(project) / ".claude" / "stack-guardrails.enabled").is_file()
    )


def profile() -> str:
    value = os.environ.get("SDLC_HOOK_PROFILE", "standard")
    return value if value in {"minimal", "standard", "strict"} else "standard"


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _pyproject_fallback(text: str) -> dict:
    """Detect tool tables without tomllib. Not a TOML parser."""
    tool = {}
    for match in _TOOL_TABLE.finditer(text):
        tool[match.group(1)] = {}
    return {"tool": tool} if tool else {}


def pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}
    text = read_text(path)
    if tomllib is None:
        return _pyproject_fallback(text)
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return _pyproject_fallback(text)


def package_json(root: Path) -> dict:
    path = root / "package.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def typescript_major(pkg: dict) -> int | None:
    deps = {}
    deps.update(pkg.get("dependencies") or {})
    deps.update(pkg.get("devDependencies") or {})
    raw = str(deps.get("typescript") or "")
    match = re.search(r"(\d+)", raw)
    return int(match.group(1)) if match else None


def candidate_dirs(root: Path) -> list[Path]:
    """Git root plus the layouts this catalog actually generates.

    Pipeline apps keep manifests under solution/, not the git root. One extra
    directory level under packages/apps/services is enough for a monorepo and
    stays a handful of stat calls.
    """
    ordered: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if not path.is_dir():
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        ordered.append(path)

    add(root)
    for rel in (
        "solution",
        "solution/backend",
        "solution/frontend",
        "backend",
        "frontend",
        "server",
        "client",
    ):
        add(root / rel)
    for rel in ("packages", "apps", "services", "solution/packages", "solution/apps"):
        parent = root / rel
        if not parent.is_dir():
            continue
        for child in sorted(parent.iterdir()):
            if (
                child.is_dir()
                and child.name not in _SKIP_DIR_NAMES
                and not child.name.startswith(".")
            ):
                add(child)
    return ordered


def display_dir(directory: Path, repo: Path) -> str:
    try:
        rel = directory.resolve().relative_to(repo.resolve())
    except ValueError:
        return str(directory)
    return "." if rel == Path(".") else rel.as_posix()


def detect(root: Path) -> dict[str, str]:
    """Return stack name -> why it applies. Cheap filesystem checks only."""
    found: dict[str, str] = {}
    project = pyproject(root)
    pkg = package_json(root)
    if (root / ".changeset" / "config.json").is_file():
        found["changesets"] = ".changeset/config.json"
    if (root / "uv.lock").is_file() or "uv" in (project.get("tool") or {}):
        found["uv"] = "uv.lock or [tool.uv]"
    tool = project.get("tool") or {}
    if (
        (root / "ruff.toml").is_file()
        or (root / ".ruff.toml").is_file()
        or "ruff" in tool
    ):
        found["ruff"] = "ruff.toml, .ruff.toml, or [tool.ruff]"
    if (root / "pyrightconfig.json").is_file() or "pyright" in tool:
        found["pyright"] = "pyrightconfig.json or [tool.pyright]"
    if "mypy" in tool:
        found["mypy"] = "[tool.mypy]"
    major = typescript_major(pkg)
    if major is not None and major >= 7:
        found["typescript"] = f"typescript {major} (stable CLI is tsc, not tsgo)"
    elif "@typescript/native-preview" in {
        **(pkg.get("dependencies") or {}),
        **(pkg.get("devDependencies") or {}),
    }:
        found["typescript"] = (
            "@typescript/native-preview (tsgo before the 7.0 stable CLI)"
        )
    elif (root / "tsconfig.json").is_file():
        found["typescript"] = "tsconfig.json"
    if (root / ".nvmrc").is_file() or (root / ".node-version").is_file():
        found["nvm"] = ".nvmrc or .node-version"
    manager = str(pkg.get("packageManager") or "")
    if (root / "pnpm-lock.yaml").is_file() or manager.startswith("pnpm@"):
        found["pnpm"] = "pnpm-lock.yaml or packageManager pnpm@"
    if (root / "biome.json").is_file() or (root / "biome.jsonc").is_file():
        found["biome"] = "biome.json"
    if (root / "railway.toml").is_file() or (root / "railway.json").is_file():
        found["railway"] = "railway.toml or railway.json (deprecated config-as-code)"
    if (root / ".railway").is_dir():
        found["railway-iac"] = ".railway/ authoring file"
    if (root / ".pre-commit-config.yaml").is_file():
        found["pre-commit"] = ".pre-commit-config.yaml"
    return found


def iter_stacks(repo: Path):
    for directory in candidate_dirs(repo):
        for name, why in detect(directory).items():
            yield directory, name, why


def ignored_path(path: Path) -> bool:
    return any(part in _SKIP_DIR_NAMES for part in path.parts)


def ruff_applies(path: Path, repo: Path) -> bool:
    if ignored_path(path):
        return False
    current = path if path.is_dir() else path.parent
    try:
        current = current.resolve()
        stop = repo.resolve()
    except OSError:
        return False
    while True:
        try:
            current.relative_to(stop)
        except ValueError:
            return False
        if (current / "ruff.toml").is_file() or (current / ".ruff.toml").is_file():
            return True
        if (current / "pyproject.toml").is_file() and "ruff" in (
            pyproject(current).get("tool") or {}
        ):
            return True
        if current == stop or current.parent == current:
            return False
        current = current.parent


def which(name: str) -> str | None:
    return shutil.which(name)


def node_mismatch(root: Path) -> str | None:
    pin_path = (
        root / ".nvmrc" if (root / ".nvmrc").is_file() else root / ".node-version"
    )
    if not pin_path.is_file():
        return None
    pin = ""
    for line in read_text(pin_path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pin = line.lstrip("v")
            break
    if not pin:
        return None
    node = which("node")
    if not node:
        return f"Node is not on PATH. .nvmrc asks for {pin}. Run `nvm use` in a shell that has nvm. This hook does not install Node."
    try:
        current = (
            subprocess.run(
                [node, "-v"], check=False, capture_output=True, text=True, timeout=5
            )
            .stdout.strip()
            .lstrip("v")
        )
    except (OSError, subprocess.TimeoutExpired):
        return "Could not read `node -v`."
    pin_major = pin.split(".", 1)[0]
    if not pin_major.isdigit():
        return (
            f"{pin_path.name} asks for '{pin}', which is not a numeric major. "
            "Run `nvm use` yourself. This hook does not run nvm install."
        )
    current_major = current.split(".", 1)[0]
    if pin_major and pin_major != current_major:
        return (
            f"Node {current} on PATH does not match {pin_path.name} ({pin}). "
            "This is the hook process's node, not an nvm shell. "
            "Run `nvm use` yourself. This harness does not run nvm install and does not block commits."
        )
    return None


def railway_static(root: Path) -> list[tuple[str, bool]]:
    """Notes plus whether the note is a harness failure. The flag is not the sentence."""
    notes: list[tuple[str, bool]] = []
    for name in ("railway.toml", "railway.json"):
        path = root / name
        if not path.is_file():
            continue
        text = read_text(path)
        notes.append(
            (
                (
                    f"{name} is deprecated Railway config-as-code (hard cutoff 2026-12-01). "
                    "Prefer `.railway/railway.ts` and preview with `railway config plan`. "
                    "Do not run `railway up` or `railway config apply` from an agent."
                ),
                False,
            )
        )
        if SECRET_RE.search(text):
            notes.append(
                (
                    f"{name} looks like it contains a secret. Move it to the Railway service variables.",
                    True,
                )
            )
    iac = root / ".railway"
    if iac.is_dir() and not any(
        (iac / name).is_file() for name in ("railway.ts", "railway.py", "railway.go")
    ):
        notes.append(
            (
                ".railway/ has no railway.ts, railway.py, or railway.go authoring file.",
                False,
            )
        )
    return notes


def _block(reason: str) -> tuple[str, str]:
    return ("block", reason + _REFUSAL)


def _dry_run(args: list[str]) -> bool:
    return any(arg == "--dry-run" or arg.startswith("--dry-run=") for arg in args)


def _railway(args: list[str]) -> tuple[str, str] | None:
    if not args:
        return None
    verb, rest = args[0], args[1:]
    if verb in {"up", "deploy", "redeploy", "down"}:
        return _block("railway " + verb + " changes the live service")
    if verb == "config" and rest:
        if rest[0] == "apply":
            return _block("railway config apply changes the linked environment")
        if rest[0] == "migrate" and "--apply" in rest:
            return _block("railway config migrate --apply writes live config")
        return None
    if verb in {"variable", "variables"}:
        writes = any(
            arg in {"--set", "--delete"} or arg.startswith(("--set=", "--set-from"))
            for arg in rest
        ) or (rest and rest[0] in {"set", "delete"})
        if writes:
            return _block("railway variables --set changes live configuration")
    return None


def _is_railway(token: str) -> bool:
    if os.path.basename(token) == "railway":
        return True
    return token == "@railway/cli" or token.endswith("/@railway/cli")


def classify_argv(argv: list[str]) -> tuple[str, str] | None:
    index = 0
    while index < len(argv) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[index]):
        index += 1
    argv = argv[index:]
    if not argv:
        return None
    token = argv[0]
    name = os.path.basename(token)
    if name in _SHELLS:
        rest = argv[1:]
        cursor = 0
        while cursor < len(rest):
            word = rest[cursor]
            if word == "-c" or (
                word.startswith("-") and not word.startswith("--") and "c" in word[1:]
            ):
                if cursor + 1 < len(rest):
                    return classify_command(rest[cursor + 1])
                return None
            cursor += 1
        return None
    if name == "pnpm" and len(argv) > 2 and argv[1] in {"dlx", "exec"}:
        return classify_argv(argv[2:])
    if name == "yarn" and len(argv) > 2 and argv[1] == "exec":
        return classify_argv(argv[2:])
    if name in {"npx", "bunx"}:
        rest = argv[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        return classify_argv(rest)
    if _is_railway(token):
        return _railway(argv[1:])
    if name in {"npm", "pnpm", "yarn", "uv"} and len(argv) > 1 and argv[1] == "publish":
        if _dry_run(argv):
            return None
        return _block(name + " publish releases to the registry")
    if name == "changeset" and len(argv) > 1 and argv[1] == "publish":
        return _block("changeset publish releases to the registry")
    return None


def classify_command(command: str) -> tuple[str, str] | None:
    for segment in split_segments(command):
        found = classify_argv(argv_of(segment))
        if found:
            return found
    return None


def classify_path(path: Path) -> str | None:
    if path.name in LOCKFILES:
        tool = LOCKFILES[path.name]
        return (
            f"Hand-editing {path.name} drifts from the generator. "
            f"Change the manifest and run `{tool}`, then commit the result. "
            "This hook does not rewrite the lockfile."
        )
    return None


def _tool_missing(output: str) -> bool:
    lowered = output.lower()
    return any(
        needle in lowered
        for needle in (
            "failed to spawn",
            "no such file",
            "not found",
            "no virtual environment",
            "does not exist",
        )
    )


def _python_tool(
    prefix: str, directory: Path, name: str, argv: list[str], timeout: int
) -> list[tuple[str, int, str]]:
    if which(name):
        code, output = run_checked(argv, directory, timeout=timeout)
        return [(prefix + name, code, output or name + " clean")]
    if not which("uv") or not (directory / ".venv").is_dir():
        return [
            (
                prefix + name,
                1,
                name + " is not on PATH and there is no .venv to run it from. "
                "Nothing was installed and no virtualenv was created.",
            )
        ]
    code, output = run_checked(
        ["uv", "run", "--frozen", "--no-sync", *argv], directory, timeout=timeout
    )
    if _tool_missing(output):
        return [
            (
                prefix + name,
                1,
                name + " is not installed in the project environment. "
                "This harness used `uv run --frozen --no-sync` and did not sync or write a lockfile.",
            )
        ]
    return [(prefix + name, code, output or name + " clean")]


def run_checked(argv: list[str], cwd: Path, timeout: int = 60) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (1, str(exc))
    output = (completed.stdout or "") + (completed.stderr or "")
    return (completed.returncode, output.strip()[-2000:])


def _check_one(
    name: str, directory: Path, repo: Path, railway_plan: bool
) -> list[tuple[str, int, str]]:
    label_at = display_dir(directory, repo)
    prefix = "" if label_at == "." else label_at + ": "
    results: list[tuple[str, int, str]] = []
    if name == "uv":
        if which("uv"):
            code, output = run_checked(
                ["uv", "lock", "--check"], directory, timeout=120
            )
            guidance = (
                "Fix the manifest or regenerate with `uv lock` (not by editing uv.lock). Then re-run. "
                + output
            )
            results.append(
                (
                    prefix + "uv lock --check",
                    code,
                    guidance if code else "lockfile matches pyproject.toml",
                )
            )
        else:
            results.append(
                (
                    prefix + "uv",
                    1,
                    "uv is not on PATH. Install it from https://docs.astral.sh/uv/ and re-run. Nothing was installed.",
                )
            )
    elif name == "ruff":
        binary = which("ruff")
        if binary:
            pairs = [
                (
                    "ruff check",
                    [binary, "check", "."],
                    "Fix the rules ruff printed. Do not pass --fix from this hook.\n",
                ),
                (
                    "ruff format --check",
                    [binary, "format", "--check", "."],
                    "Run `ruff format` yourself if you want the rewrite.\n",
                ),
            ]
        elif which("uv") and (directory / ".venv").is_dir():
            frozen = ["uv", "run", "--frozen", "--no-sync", "ruff"]
            pairs = [
                (
                    "ruff check",
                    frozen + ["check", "."],
                    "Fix the rules ruff printed. Do not pass --fix from this hook.\n",
                ),
                (
                    "ruff format --check",
                    frozen + ["format", "--check", "."],
                    "Run `ruff format` yourself if you want the rewrite.\n",
                ),
            ]
        else:
            pairs = []
            results.append(
                (
                    prefix + "ruff",
                    1,
                    (
                        "ruff is not on PATH and there is no .venv to run it from. "
                        "Nothing was installed and no virtualenv was created."
                    ),
                )
            )
        for label, argv, hint in pairs:
            code, output = run_checked(argv, directory)
            if not binary and _tool_missing(output):
                results.append(
                    (
                        prefix + "ruff",
                        1,
                        (
                            "ruff is not installed in the project environment. "
                            "This harness used `uv run --frozen --no-sync` and did not sync or write a lockfile."
                        ),
                    )
                )
                break
            results.append(
                (prefix + label, code, (hint + output) if code else label + " clean")
            )
    elif name == "typescript":
        pkg = package_json(directory)
        major = typescript_major(pkg)
        preview = "@typescript/native-preview" in {
            **(pkg.get("devDependencies") or {}),
            **(pkg.get("dependencies") or {}),
        }
        if major is not None and major >= 7:
            argv = ["npx", "--no-install", "tsc", "--noEmit", "--pretty", "false"]
            label = "npx tsc --noEmit (TypeScript 7 stable CLI is tsc)"
        elif preview:
            argv = ["npx", "--no-install", "tsgo", "--noEmit", "--pretty", "false"]
            label = "npx tsgo --noEmit (native preview, pre-stable)"
        else:
            argv = ["npx", "--no-install", "tsc", "--noEmit", "--pretty", "false"]
            label = "npx tsc --noEmit"
        code, output = run_checked(argv, directory, timeout=180)
        hint = (
            "TypeScript 7.0 (8 July 2026) ships as the `typescript` package and its CLI is `tsc`. "
            "`tsgo` is the binary from `@typescript/native-preview` for pre-stable builds. "
            "Install the compiler yourself; this harness passes --no-install.\n"
        )
        results.append(
            (prefix + label, code, (hint + output) if code else "typecheck clean")
        )
    elif name == "nvm":
        mismatch = node_mismatch(directory)
        results.append(
            (
                prefix + "node vs .nvmrc",
                1 if mismatch else 0,
                mismatch or "Node major matches the pin",
            )
        )
    elif name == "changesets":
        code, output = run_checked(
            ["npx", "--no-install", "changeset", "status"], directory, timeout=60
        )
        results.append(
            (
                prefix + "changeset status",
                code,
                "Add a changeset with `npx changeset` if this change should release. Do not run `changeset publish`.\n"
                + output
                if code
                else "changeset status ok",
            )
        )
    elif name == "pnpm":
        if which("pnpm"):
            code, output = run_checked(
                [
                    "pnpm",
                    "install",
                    "--frozen-lockfile",
                    "--ignore-scripts",
                    "--offline",
                    "--lockfile-only",
                ],
                directory,
                timeout=120,
            )
            results.append(
                (
                    prefix + "pnpm frozen lockfile",
                    code,
                    "If the lock is stale, run `pnpm install` and commit pnpm-lock.yaml. "
                    "This used --offline --lockfile-only, so it did not fetch and did not write node_modules.\n"
                    + output
                    if code
                    else "pnpm lockfile matches the manifest",
                )
            )
        else:
            results.append(
                (
                    prefix + "pnpm",
                    1,
                    "pnpm is not on PATH. Install it or enable corepack. This harness did not install it.",
                )
            )
    elif name == "biome":
        if which("biome"):
            code, output = run_checked(["biome", "ci", "."], directory, timeout=120)
            results.append(
                (
                    prefix + "biome ci",
                    code,
                    "biome ci is read-only. Fix findings; do not rely on --write inside the hook.\n"
                    + output
                    if code
                    else "biome ci clean",
                )
            )
        else:
            results.append(
                (
                    prefix + "biome",
                    1,
                    "biome is not on PATH. Install it yourself. This harness did not install it.",
                )
            )
    elif name == "pyright":
        results.extend(_python_tool(prefix, directory, "pyright", ["pyright"], 180))
    elif name == "mypy":
        results.extend(_python_tool(prefix, directory, "mypy", ["mypy", "."], 180))
    elif name in {"railway", "railway-iac"}:
        if name == "railway-iac" and (
            (directory / "railway.toml").is_file()
            or (directory / "railway.json").is_file()
        ):
            return results
        for note, failed in railway_static(directory):
            results.append((prefix + "railway static", 1 if failed else 0, note))
        if railway_plan and which("railway"):
            code, output = run_checked(
                ["railway", "config", "plan"], directory, timeout=60
            )
            results.append(
                (
                    prefix + "railway config plan",
                    code,
                    "plan does not apply. Never follow it with apply unless a human asked.\n"
                    + output,
                )
            )
        else:
            results.append(
                (
                    prefix + "railway",
                    0,
                    "Safe check is `railway config plan`. This harness did not run it (needs auth). Deploy commands stay blocked.",
                )
            )
    elif name == "pre-commit":
        results.append(
            (
                prefix + "pre-commit",
                0,
                "A .pre-commit-config.yaml is present. Run `pre-commit run` on staged files yourself. This harness does not execute it (it can be slow and can mutate).",
            )
        )
    return results


def verify(root: Path, railway_plan: bool = False) -> list[tuple[str, int, str]]:
    """Read-only checks. Never publishes, deploys, or rewrites locks."""
    results: list[tuple[str, int, str]] = []
    for directory, name, _why in iter_stacks(root):
        results.extend(_check_one(name, directory, root, railway_plan))
    if not results:
        results.append(("detect", 0, "No supported stack markers at " + str(root)))
    return results


def payload_from_stdin() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"tool_input": {"command": raw}}
    return data if isinstance(data, dict) else {}


def hook_main(phase: str) -> int:
    # Consume stdin before any early return. A disabled hook that exits without
    # reading leaves printf with SIGPIPE, and the shell would then fail the tool call.
    data = payload_from_stdin()
    if profile() == "minimal":
        return 0
    root = repo_root()
    if not enabled(root):
        return 0
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    command = str(tool_input.get("command") or "")
    file_path = str(
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("filePath")
        or os.environ.get("CLAUDE_FILE_PATH")
        or ""
    )
    messages: list[tuple[str, str]] = []
    if phase == "pre" and command:
        found = classify_command(command)
        if found:
            messages.append(found)
    if file_path:
        path = Path(file_path)
        if not path.is_absolute():
            path = root / path
        if not ignored_path(path):
            if phase == "pre":
                note = classify_path(path)
                if note:
                    messages.append(("warn", note))
            if (
                phase == "post"
                and path.suffix == ".py"
                and path.is_file()
                and ruff_applies(path, root)
            ):
                binary = which("ruff")
                if binary:
                    code, output = run_checked(
                        [binary, "check", str(path)], path.parent, timeout=20
                    )
                    if code:
                        messages.append(
                            (
                                "warn",
                                "ruff check failed for "
                                + path.name
                                + ". Fix the rules; this hook does not pass --fix.\n"
                                + output,
                            )
                        )
    if not messages:
        return 0
    event = "PreToolUse" if phase == "pre" else "PostToolUse"
    blocking = [
        text
        for level, text in messages
        if level == "block" or (level == "warn" and profile() == "strict")
    ]
    warning = [
        text for level, text in messages if level == "warn" and profile() != "strict"
    ]
    if blocking:
        reason = "[stack-guardrails] BLOCKED: " + " ".join(blocking)
        sys.stderr.write(reason + "\n")
        emit(event, reason, decision="deny")
        return 2
    if warning:
        emit(event, "[stack-guardrails] WARNING: " + " ".join(warning))
    return 0


def verify_main(railway_plan: bool) -> int:
    root = repo_root()
    print("repo: " + str(root))
    print(
        "enabled: "
        + (
            "yes"
            if enabled(root)
            else "no (harness runs anyway; hooks no-op until opted in)"
        )
    )
    stacks = list(iter_stacks(root))
    print(
        "detected: "
        + (
            ", ".join(
                f"{display_dir(directory, root)}:{name} ({why})"
                for directory, name, why in stacks
            )
            or "none"
        )
    )
    failed = 0
    for label, code, output in verify(root, railway_plan=railway_plan):
        state = "ok" if code == 0 else "fail"
        print(f"\n## {label}: {state}")
        if output:
            print(output)
        if code != 0:
            failed += 1
    print("\nThis harness did not push, publish, or deploy.")
    return 1 if failed else 0


def self_test() -> int:
    import tempfile

    assert classify_command("railway up -y")[0] == "block"
    assert classify_command("cd app && railway up")[0] == "block"
    assert classify_command('bash -lc "railway up"')[0] == "block"
    assert classify_command("npx --yes @railway/cli deploy --service api")[0] == "block"
    assert classify_command("railway config plan") is None
    assert classify_command("railway config migrate") is None
    assert classify_command("railway config apply")[0] == "block"
    assert (
        classify_command("railway config migrate --service web --apply")[0] == "block"
    )
    assert classify_command("npx changeset publish")[0] == "block"
    assert classify_command("pnpm exec changeset publish")[0] == "block"
    assert classify_command("git push -u origin branch") is None
    assert classify_command("git push --force") is None
    assert classify_command("railway down")[0] == "block"
    assert classify_command("railway variables --set TOKEN=secret")[0] == "block"
    assert classify_command("railway variables") is None
    assert classify_command("pnpm dlx @railway/cli up")[0] == "block"
    assert classify_command("bunx @railway/cli up")[0] == "block"
    assert classify_command("npm publish --dry-run") is None
    assert classify_command("pnpm publish --dry-run") is None
    assert classify_command("uv publish --dry-run") is None
    assert classify_command('git commit -m "npm publish"') is None
    assert classify_command('gh pr create --body "ship it with railway up"') is None
    assert classify_command('rg "uv publish" docs/') is None
    assert classify_command("grep -rn 'changeset publish' .") is None
    assert classify_command('echo "uv publish"') is None
    assert classify_command('git log --grep="railway deploy"') is None
    assert "uv" in _pyproject_fallback("[tool.uv]\n")["tool"]
    assert "ruff" in _pyproject_fallback("[tool.ruff.lint]\n")["tool"]
    assert _pyproject_fallback("[project]\nname='x'\n") == {}
    assert "uv lock" in (classify_path(Path("uv.lock")) or "")
    sample = {"devDependencies": {"typescript": "^7.0.0"}}
    assert typescript_major(sample) == 7
    preview = {"devDependencies": {"@typescript/native-preview": "7.0.0-beta"}}
    assert typescript_major(preview) is None
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        sol = repo / "solution"
        sol.mkdir()
        (sol / "uv.lock").write_text("", encoding="utf-8")
        (sol / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        (sol / ".nvmrc").write_text("20\n", encoding="utf-8")
        hits = {(name, path.resolve()) for path, name, _why in iter_stacks(repo)}
        assert ("uv", sol.resolve()) in hits
        assert ("ruff", sol.resolve()) in hits
        assert ("nvm", sol.resolve()) in hits
        assert ruff_applies(sol / "pkg" / "app.py", repo)
        assert not ruff_applies(repo / "README.md", repo)
        hidden = repo / "hidden-ruff"
        hidden.mkdir()
        (hidden / ".ruff.toml").write_text("line-length = 88\n", encoding="utf-8")
        assert "ruff" in detect(hidden)
        plain = repo / "railway-plain"
        plain.mkdir()
        (plain / "railway.toml").write_text(
            '[build]\nbuilder = "nixpacks"\n', encoding="utf-8"
        )
        plain_notes = railway_static(plain)
        assert plain_notes and all(flag is False for _note, flag in plain_notes)
        secret = repo / "railway-secret"
        secret.mkdir()
        (secret / "railway.toml").write_text(
            'token = "abcdefghijklmnopqrstuvwxyz"\n', encoding="utf-8"
        )
        secret_notes = railway_static(secret)
        assert any(flag is True for _note, flag in secret_notes)
        assert any(flag is False for _note, flag in secret_notes)
        secret_checks = _check_one("railway", secret, secret, False)
        assert any(code == 1 for _name, code, _note in secret_checks)
        plain_checks = _check_one("railway", plain, plain, False)
        assert plain_checks and all(code == 0 for _name, code, _note in plain_checks)
    import inspect

    assert "node_mismatch" not in inspect.getsource(hook_main)
    if which("uv"):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text(
                "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
            )
            _check_one("ruff", repo, repo, False)
            assert not (repo / ".venv").exists()
            assert not (repo / "uv.lock").exists()
    print("stack_guardrails self-test ok")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) >= 2 and argv[1] == "--verify":
        return verify_main("--railway-plan" in argv)
    phase = argv[1] if len(argv) > 1 else "pre"
    return hook_main(phase)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

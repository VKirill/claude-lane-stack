"""Shared safety boundary for generated verification commands."""

from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath
from typing import Any, Iterable

# L1 verification timeout is control-plane policy, not a PM/writer concern.
# Authors omit timeout_sec; runtime fills DEFAULT. Explicit values still honored.
DEFAULT_VERIFY_TIMEOUT_SEC = 900
HARD_VERIFY_TIMEOUT_SEC = 7200


def default_verification_timeout(command: str = "") -> int:
    """Deterministic L1 timeout. LLM plans should not invent this field."""
    del command  # reserved for future command-class heuristics
    return DEFAULT_VERIFY_TIMEOUT_SEC


def resolve_verification_timeout(raw: Any, *, command: str = "") -> int:
    """Return a bounded timeout_sec; missing/invalid → default."""
    if raw is None or raw is False or raw == "":
        return default_verification_timeout(command)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default_verification_timeout(command)
    if value < 1:
        return default_verification_timeout(command)
    if value > HARD_VERIFY_TIMEOUT_SEC:
        return HARD_VERIFY_TIMEOUT_SEC
    return value


DEFAULT_EXECUTABLES = frozenset(
    {
        "npm",
        "pnpm",
        "yarn",
        "node",
        "python",
        "python3",
        "pytest",
        "cargo",
        "go",
        "make",
        "just",
        "bundle",
        "composer",
        "php",
        "bin/rails",
        "bin/rake",
    }
)
FORBIDDEN_EXECUTABLES = frozenset(
    {
        "bunx",
        "corepack",
        "curl",
        "git",
        "gh",
        "npx",
        "pip",
        "pip3",
        "pnpx",
        "scp",
        "ssh",
        "sudo",
        "uv",
        "uvx",
        "wget",
    }
)
FORBIDDEN_PACKAGE_SUBCOMMANDS = {
    "npm": {"add", "ci", "exec", "i", "install", "pack", "publish", "uninstall", "update"},
    "pnpm": {"add", "deploy", "dlx", "exec", "fetch", "import", "install", "publish", "remove", "update"},
    "yarn": {"add", "dlx", "exec", "install", "npm", "pack", "publish", "remove", "upgrade"},
    "bundle": {"add", "install", "lock", "remove", "update"},
    "composer": {"install", "remove", "require", "update"},
    "cargo": {"add", "install", "login", "owner", "package", "publish", "remove", "update"},
    "go": {"env", "generate", "get", "install", "work"},
}
SAFE_PYTHON_MODULES = frozenset({"compileall", "mypy", "pytest", "ruff", "unittest"})
SHELL_COMPOSITION = re.compile(r"(?:&&|\|\||[;&|<>`$*?{}\[\]]|\r|\n)")


def verification_error(
    command: str, extra_executables: Iterable[str] = ()
) -> str | None:
    if not isinstance(command, str) or not command.strip():
        return "verification command is empty"
    if SHELL_COMPOSITION.search(command):
        return "verification command contains shell composition, redirection, or substitution"
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        return f"verification command cannot be parsed: {exc}"
    if not tokens:
        return "verification command is empty"
    executable = tokens[0]
    if executable in FORBIDDEN_EXECUTABLES:
        return f"verification executable is forbidden: {executable}"
    allowed = DEFAULT_EXECUTABLES | frozenset(extra_executables)
    if executable not in allowed:
        return f"verification executable is not allowlisted: {executable}"
    for token in tokens[1:]:
        candidates = [token]
        if "=" in token:
            candidates.append(token.split("=", 1)[1])
        for candidate in candidates:
            normalized = candidate.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or normalized.startswith("~") or ".." in path.parts:
                return "verification arguments may not escape the task worktree"
    forbidden = FORBIDDEN_PACKAGE_SUBCOMMANDS.get(executable, set())
    if forbidden.intersection(tokens[1:]):
        return f"generated verification may not mutate or fetch packages with {executable}"
    inline_flags = {
        "python": {"-c"},
        "python3": {"-c"},
        "node": {"-e", "--eval", "-p", "--print"},
        "php": {"-r"},
    }
    forbidden_inline = inline_flags.get(executable, set()).intersection(tokens[1:])
    if forbidden_inline:
        flag = sorted(forbidden_inline)[0]
        return f"inline code is forbidden for generated verification: {executable} {flag}"
    if executable in {"python", "python3"} and "-m" in tokens[1:]:
        module_index = tokens.index("-m") + 1
        if module_index >= len(tokens) or tokens[module_index] not in SAFE_PYTHON_MODULES:
            module = tokens[module_index] if module_index < len(tokens) else "<missing>"
            return f"python module is not allowlisted for verification: {module}"
    return None


def verification_argv(command: str, extra_executables: Iterable[str] = ()) -> list[str]:
    error = verification_error(command, extra_executables)
    if error is not None:
        raise ValueError(error)
    return shlex.split(command, posix=True)


# Path-like args that look like scripts files to open (not package names / flags).
_SCRIPT_SUFFIXES = (
    ".py",
    ".sh",
    ".bash",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".rb",
    ".php",
)


def verification_script_args(command: str) -> list[str]:
    """Return relative script path arguments from a verification command.

    Used by run-validate to ensure pre-authored checkers exist under
    verification cwd before dispatch (common worktree footgun: path points at
    main-repo .agents while cwd is the worktree).
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []
    if len(tokens) < 2:
        return []
    scripts: list[str] = []
    skip_next = False
    for index, token in enumerate(tokens):
        if index == 0:
            continue
        if skip_next:
            skip_next = False
            continue
        # Flag + value pairs that are not script paths (npm workspaces, -m modules, …)
        if token in {
            "-m",
            "-W",
            "-X",
            "-C",
            "--require",
            "-r",
            "-w",
            "--workspace",
            "--prefix",
            "--filter",
        }:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        # npm/pnpm/yarn script names and package names are not files on disk
        if tokens[0] in {"npm", "pnpm", "yarn"} and token in {
            "run",
            "test",
            "exec",
            "typecheck",
            "lint",
            "build",
        }:
            continue
        normalized = token.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or normalized.startswith("~") or ".." in path.parts:
            continue  # already rejected by verification_error when invalid
        looks_like_script = (
            normalized.endswith(_SCRIPT_SUFFIXES)
            or normalized.startswith("./")
            or normalized.startswith("../")
            or normalized.startswith(".agents/")
            or "/artifacts/" in normalized
            or normalized.endswith("/check.py")
        )
        # Paths like apps/api after npm -w are workspaces, not checkers
        if looks_like_script:
            scripts.append(token)
    return scripts

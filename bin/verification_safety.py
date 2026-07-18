"""Shared safety boundary for generated verification commands."""

from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath
from typing import Iterable


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

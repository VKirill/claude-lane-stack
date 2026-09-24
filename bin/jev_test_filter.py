"""Wrap L1 test runners with mizchi/jev-test-filter. Fail-open otherwise.

Typecheck/lint/build cannot be subset like tests (tsc is whole-program).
They are skipped when the git diff under cwd has no files that can affect
that check. Lint may be narrowed to those files when the argv is eslint.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SKIP_TOKENS = frozenset({"typecheck", "lint", "build", "tsc"})
ROOT_FLAGS = frozenset({"--root", "-C", "--config", "-c", "--reporter", "--project"})
TYPE_SUFFIX = (
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
)
LINT_SUFFIX = TYPE_SUFFIX + (".css", ".scss", ".md")
BUILD_SUFFIX = TYPE_SUFFIX + (".css", ".scss", ".sass", ".less", ".html", ".json")
CONFIG_NAMES = frozenset(
    {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "tsconfig.json",
        "jsconfig.json",
        "nuxt.config.ts",
        "nuxt.config.js",
        "nuxt.config.mjs",
        "vite.config.ts",
        "vite.config.js",
        "vite.config.mjs",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.ts",
        "dockerfile",
    }
)


def filter_enabled() -> bool:
    raw = (os.environ.get("LANE_JEV_TEST_FILTER") or "").strip().lower()
    if raw in {"0", "off", "false", "no"}:
        return False
    if "unittest" in sys.modules and raw not in {"1", "on", "true", "yes"}:
        return False
    return True


def scope_enabled() -> bool:
    raw = (os.environ.get("LANE_L1_SCOPE") or "").strip().lower()
    if raw in {"0", "off", "false", "no"}:
        return False
    if "unittest" in sys.modules and raw not in {"1", "on", "true", "yes"}:
        return False
    return True


def filter_bin() -> Path | None:
    explicit = (os.environ.get("JEV_TEST_FILTER_BIN") or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    found = shutil.which("jev-test-filter")
    if found:
        return Path(found)
    home = (
        Path.home()
        / ".agents"
        / "lib"
        / "jev-test-filter"
        / "node_modules"
        / ".bin"
        / "jev-test-filter"
    )
    return home if home.is_file() else None


def test_runner_format(argv: list[str]) -> str | None:
    """Return a jev-test-filter --format, or None when this is not a test run."""
    if not argv:
        return None
    lower = [token.lower() for token in argv]
    if any(token in SKIP_TOKENS for token in lower):
        return None
    blob = " ".join(argv)
    if "vitest" in blob:
        return "vitest"
    if "playwright" in blob:
        return "playwright"
    if any(
        token == "jest" or token.endswith("/jest") or token.endswith("jest.js")
        for token in argv
    ):
        return "jest"
    if argv[0] == "bun" and "test" in lower:
        return "bun"
    if argv[0] == "node" and "--test" in argv:
        return "node"
    if argv[:2] == ["cargo", "test"]:
        return "rust"
    if argv[:2] == ["go", "test"]:
        return "go"
    if argv[0] in {"npm", "pnpm", "yarn"}:
        scripts = [token for token in lower[1:] if not token.startswith("-")]
        if scripts and scripts[0] == "test":
            return "auto"
        if "run" in lower and any(token.startswith("test") for token in lower):
            return "auto"
    return None


def command_kind(argv: list[str]) -> str | None:
    """typecheck / lint / build, or None."""
    if not argv:
        return None
    lower = [token.lower() for token in argv]
    blob = " ".join(lower)
    if "typecheck" in blob or "vue-tsc" in blob or "tsc" in lower:
        return "typecheck"
    if any(token in {"lint", "eslint", "eslint-compat"} for token in lower) or "eslint" in blob:
        return "lint"
    if any(token == "build" or token.startswith("build:") for token in lower):
        return "build"
    return None


def discovery_paths(argv: list[str]) -> list[str]:
    """Path args already on the runner, used to narrow Jev discovery."""
    out: list[str] = []
    skip_next = False
    for index, token in enumerate(argv):
        if index == 0:
            continue
        if skip_next:
            skip_next = False
            continue
        if token in ROOT_FLAGS:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        if "node_modules" in token:
            continue
        if "/" in token or token.endswith(
            (".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".go", ".rs")
        ):
            out.append(token)
    return out


def git_changed_under(cwd: Path) -> list[str] | None:
    """Paths under cwd that differ from HEAD, plus untracked. None = git failed."""
    try:
        root = subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    root_path = Path(root)
    names: set[str] = set()
    try:
        diff = subprocess.check_output(
            ["git", "-C", root, "diff", "--name-only", "HEAD"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        extra = subprocess.check_output(
            ["git", "-C", root, "ls-files", "--others", "--exclude-standard"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    for block in (diff, extra):
        names.update(line.strip() for line in block.splitlines() if line.strip())
    cwd_res = cwd.resolve()
    out: list[str] = []
    for name in sorted(names):
        abs_path = (root_path / name).resolve()
        try:
            rel = abs_path.relative_to(cwd_res)
        except ValueError:
            continue
        out.append(str(rel))
    return out


def affects(kind: str, rel: str) -> bool:
    name = Path(rel).name.lower()
    if name in CONFIG_NAMES or name.startswith("tsconfig"):
        return True
    suffix = Path(rel).suffix.lower()
    if kind == "typecheck":
        return suffix in TYPE_SUFFIX
    if kind == "lint":
        return suffix in LINT_SUFFIX
    return suffix in BUILD_SUFFIX


def lint_argv(argv: list[str], files: list[str]) -> list[str] | None:
    """Replace a trailing `.` on a direct eslint argv. npm run lint stays full."""
    if not files or not argv:
        return None
    if argv[0] in {"npm", "pnpm", "yarn"}:
        return None
    if "eslint" not in " ".join(argv).lower():
        return None
    if argv[-1] != ".":
        return None
    return [*argv[:-1], *files]


def scope_heavy(
    argv: list[str], *, cwd: Path | None, kind: str
) -> tuple[list[str], dict[str, Any]]:
    if cwd is None or not scope_enabled():
        return argv, {"kind": kind, "full": True, "reason": "scope-off"}
    files = git_changed_under(cwd)
    if files is None:
        return argv, {"kind": kind, "full": True, "reason": "git-unavailable"}
    relevant = [path for path in files if affects(kind, path)]
    if not relevant:
        return argv, {
            "skip_run": True,
            "kind": kind,
            "reason": "no-relevant-diff",
            "changed": files,
        }
    if kind == "lint":
        narrowed = lint_argv(argv, relevant)
        if narrowed is not None:
            return narrowed, {
                "kind": "lint",
                "files": relevant,
                "narrowed": True,
            }
    return argv, {"kind": kind, "full": True, "files": relevant}


def wrap_verification(
    argv: list[str], *, cwd: Path | None = None
) -> tuple[list[str], dict[str, Any]]:
    """Skip/narrow heavy checks, or prefix tests with jev-test-filter --exec."""
    kind = command_kind(argv)
    if kind in {"typecheck", "lint", "build"}:
        return scope_heavy(argv, cwd=cwd, kind=kind)
    fmt = test_runner_format(argv)
    if fmt is None:
        return argv, {"skipped": "not-a-test-runner"}
    if not filter_enabled():
        return argv, {"skipped": "disabled"}
    binary = filter_bin()
    if binary is None:
        return argv, {"skipped": "missing-bin"}
    try:
        from jev_decisions import typesafe_key
    except ImportError:
        typesafe_key = lambda: ""  # noqa: E731
    if not typesafe_key():
        return argv, {"skipped": "no-key"}
    wrapped = [str(binary), "--format", fmt, *discovery_paths(argv), "--exec", "--", *argv]
    return wrapped, {"format": fmt, "bin": str(binary), "wrapped": True}


def verification_env() -> dict[str, str]:
    """Pass TypeSafe key into the Node CLI even when it lives in ~/secrets."""
    env = os.environ.copy()
    if env.get("TYPESAFE_API_KEY"):
        return env
    try:
        from jev_decisions import typesafe_key
    except ImportError:
        return env
    key = typesafe_key()
    if key:
        env["TYPESAFE_API_KEY"] = key
    return env

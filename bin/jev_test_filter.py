"""Wrap L1 test runners with mizchi/jev-test-filter. Fail-open otherwise."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

SKIP_TOKENS = frozenset({"typecheck", "lint", "build", "tsc"})
ROOT_FLAGS = frozenset({"--root", "-C", "--config", "-c", "--reporter", "--project"})


def filter_enabled() -> bool:
    raw = (os.environ.get("LANE_JEV_TEST_FILTER") or "").strip().lower()
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


def wrap_verification(
    argv: list[str], *, cwd: Path | None = None
) -> tuple[list[str], dict[str, Any]]:
    """Prefix a test argv with jev-test-filter --exec, or leave it alone."""
    del cwd
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

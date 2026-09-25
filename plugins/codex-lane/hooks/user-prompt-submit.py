#!/usr/bin/env python3
"""Delegate main-session skill hints to the installed lane-stack fallback."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if os.environ.get("LANE_CODEX_WORKER") == "1":
        return 0
    hook = Path.home() / ".agents" / "hooks" / "skill_hint.py"
    if not hook.is_file():
        return 0
    try:
        environment = os.environ.copy()
        environment.pop("CLAUDE_PLUGIN_ROOT", None)
        environment.pop("PLUGIN_ROOT", None)
        result = subprocess.run(
            [sys.executable, str(hook)],
            input=sys.stdin.read(),
            text=True,
            capture_output=True,
            env=environment,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if any(
        blocked in result.stdout
        for blocked in ("orchestrator-lanes", "orchestrator-workflow", "codex-lane-worker")
    ):
        return 0
    sys.stdout.write(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

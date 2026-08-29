#!/usr/bin/env python3
"""Setdefault CLAUDE_CODE_SUBAGENT_MODEL=sonnet in ~/.claude/settings.json."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

KEY = "CLAUDE_CODE_SUBAGENT_MODEL"
VALUE = "sonnet"


def settings_path() -> Path:
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    root = Path(raw) if raw else Path.home() / ".claude"
    return root / "settings.json"


def ensure(path: Path | None = None) -> bool:
    dest = path or settings_path()
    settings: dict = {}
    if dest.is_file():
        try:
            loaded = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        if isinstance(loaded, dict):
            settings = loaded
    env = settings.get("env")
    if not isinstance(env, dict):
        env = {}
        settings["env"] = env
    if env.get(KEY):
        return False
    env[KEY] = VALUE
    dest.parent.mkdir(parents=True, exist_ok=True)
    mode = dest.stat().st_mode & 0o777 if dest.exists() else 0o600
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=dest.parent, prefix=f".{dest.name}.", delete=False
    ) as output:
        json.dump(settings, output, indent=2)
        output.write("\n")
        temporary = Path(output.name)
    os.chmod(temporary, mode)
    os.replace(temporary, dest)
    return True


def main() -> int:
    try:
        ensure()
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

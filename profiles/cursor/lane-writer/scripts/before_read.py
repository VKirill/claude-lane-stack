#!/usr/bin/env python3
"""Cursor beforeReadFile: deny secret/reread/unneeded extras on a lane."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _ensure_bin() -> None:
    here = Path(__file__).resolve()
    candidates = [here.parents[4] / "bin", Path.home() / ".agents" / "bin"]
    root = (os.environ.get("LANE_STACK_ROOT") or "").strip()
    if root:
        candidates.append(Path(root) / "bin")
    for directory in candidates:
        if (directory / "jev_read.py").is_file():
            path = str(directory)
            if path not in sys.path:
                sys.path.insert(0, path)
            return


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        _ensure_bin()
        from jev_read import decide_read

        result = decide_read(payload if isinstance(payload, dict) else {})
        if not isinstance(result, dict) or result.get("permission") not in {"allow", "deny"}:
            result = {"permission": "allow"}
        json.dump(result, sys.stdout)
    except Exception:
        json.dump({"permission": "allow"}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

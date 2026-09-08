#!/usr/bin/env python3
"""PreToolUse Read: block fat full-file reads when pm_read.enabled."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BIN = _ROOT / "bin"
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))

from pm_read import hook_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(hook_main())

#!/usr/bin/env python3
"""Small Codex Lane session introduction; workers use a separate marker."""

from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("LANE_CODEX_WORKER") == "1":
        sys.stdout.write(
            "Codex Lane worker mode: follow the assigned task contract and finish with the canonical LANE_REPORT.\n"
        )
        return 0
    # The owner's own Codex sessions get no lane banner (2026-10-13); the codex-lane skill is still listed for them.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

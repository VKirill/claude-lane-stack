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
    sys.stdout.write(
        "Codex Lane active: use the codex-lane skill for typed run status, resume, review, verification, and acceptance.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

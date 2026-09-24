#!/usr/bin/env python3
"""Lane writer stays one agent. Deny Task/subagents when LANE_TASK_FILE is set."""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    json.load(sys.stdin)
    if not (os.environ.get("LANE_TASK_FILE") or "").strip():
        json.dump({"permission": "allow"}, sys.stdout)
        return 0
    json.dump(
        {
            "permission": "deny",
            "agent_message": (
                "Lane writer: no nested Agent/Task. Finish this YAML yourself."
            ),
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

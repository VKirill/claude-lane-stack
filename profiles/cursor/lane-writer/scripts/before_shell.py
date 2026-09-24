#!/usr/bin/env python3
"""Deny L0 test/typecheck/git-write shells when the Cursor lane is active."""
from __future__ import annotations

import json
import os
import re
import sys

_DENY = re.compile(
    r"(?:^|\s)(?:"
    r"npm(?:\s+run)?\s+test\b"
    r"|pnpm(?:\s+run)?\s+test\b"
    r"|yarn(?:\s+run)?\s+test\b"
    r"|npx\s+"
    r"|vitest\b|jest\b|pytest\b|playwright\b"
    r"|typecheck\b|(?:vue-)?tsc\b"
    r"|git\s+(?:commit|push|merge|checkout|restore|reset|switch)\b"
    r")",
    re.IGNORECASE,
)


def main() -> int:
    payload = json.load(sys.stdin)
    if not (os.environ.get("LANE_TASK_FILE") or "").strip():
        json.dump({"permission": "allow"}, sys.stdout)
        return 0
    command = payload.get("command") if isinstance(payload, dict) else ""
    if isinstance(command, str) and _DENY.search(command):
        json.dump(
            {
                "permission": "deny",
                "agent_message": (
                    "L0: do not run tests, typecheck, npx, or git write. "
                    "Controller L1 runs verification[]. Emit LANE_REPORT."
                ),
            },
            sys.stdout,
        )
        return 0
    json.dump({"permission": "allow"}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

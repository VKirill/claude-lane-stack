#!/usr/bin/env python3
"""PreToolUse: block destructive shell across CLIs."""
from __future__ import annotations
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_payload import (  # type: ignore
    read_payload, detect_client, tool_name, shell_command,
    is_shell_tool, emit_allow, emit_deny,
)

def main() -> None:
    p = read_payload()
    client = detect_client(p)
    name = tool_name(p)
    if name and not is_shell_tool(name):
        emit_allow(client)
    cmd = shell_command(p)
    if not cmd.strip():
        emit_allow(client)

    low = cmd.lower()

    # git hook skip
    if re.search(r"\bgit\s+(commit|push|merge)\b", low) and (
        "--no-verify" in low or "husky=0" in low or "husky=false" in low
    ):
        emit_deny(client, "[agent-guard] git --no-verify / HUSKY=0 blocked. Fix the failing hook instead of bypassing it.")

    # force push
    if re.search(r"\bgit\s+push\b", low) and (
        re.search(r"(^|[\s])--force($|[\s=])", low) or re.search(r"(^|[\s])-f($|[\s])", low)
    ) and "--force-with-lease" not in low:
        emit_deny(client, "[agent-guard] git push --force blocked. Use --force-with-lease after git fetch.")

    # SQL destroyers (simple)
    if re.search(r"\b(drop\s+(table|database|schema)|truncate\s+table)\b", low):
        emit_deny(client, "[agent-guard] DROP/TRUNCATE blocked. Use migrations / explicit review.")

    if re.search(r"\bdelete\s+from\s+\w+\s*;?\s*$", low) and "where" not in low:
        emit_deny(client, "[agent-guard] DELETE without WHERE blocked.")

    # rm -rf outside known build dirs
    if re.search(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*|--force).*-[a-zA-Z]*r|rm\s+-rf\b|rm\s+-fr\b", low):
        safe = any(x in low for x in (
            "node_modules", "/tmp/", ".next", "dist", "build", ".cache", "coverage", ".turbo",
        ))
        if not safe:
            emit_deny(client, "[agent-guard] rm -rf blocked (use gio trash or whitelist build/tmp paths).")

    emit_allow(client)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # fail-open
        sys.exit(0)

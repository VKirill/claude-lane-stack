#!/usr/bin/env python3
"""PostToolUse: catch gross code smells after write/edit."""
from __future__ import annotations
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_payload import ( # type: ignore
    read_payload, detect_client, tool_name, file_path, is_edit_tool, emit_post_block,
)

def main() -> None:
    p = read_payload()
    client = detect_client(p)
    name = tool_name(p)
    if name and not is_edit_tool(name) and client != "":
        #  post may not send tool name the same way — still try path
        pass
    path = file_path(p)
    if not path or not Path(path).is_file():
        sys.exit(0)
    # skip agent contract paths
    if "/.agents/" in path or "/node_modules/" in path:
        sys.exit(0)

    text = Path(path).read_text(errors="replace")
    lines = text.splitlines()
    warnings: list[str] = []
    ext = Path(path).suffix.lower()

    def add(msg: str, hits: list[str]) -> None:
        if hits:
            warnings.append(msg + "\n" + "\n".join(hits[:12]))

    if ext in {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}:
        any_hits = []
        for i, ln in enumerate(lines, 1):
            if "guardian: allow" in ln:
                continue
            if re.search(r":\s*any(\s|;|,|\)|>|\[|=|$)|as\s+any\b|<any>", ln):
                any_hits.append(f"{i}:{ln.strip()[:120]}")
        add(f"'any' type in {path}", any_hits)

        prisma = []
        for i, ln in enumerate(lines, 1):
            if "guardian: allow" in ln:
                continue
            if re.search(r"\$queryRawUnsafe|\$executeRawUnsafe", ln):
                prisma.append(f"{i}:{ln.strip()[:120]}")
        add(f"Prisma unsafe raw SQL in {path}", prisma)

        ts_ignore = []
        for i, ln in enumerate(lines, 1):
            if re.search(r"@ts-ignore|@ts-nocheck", ln) and "guardian: allow" not in ln:
                ts_ignore.append(f"{i}:{ln.strip()[:120]}")
        add(f"@ts-ignore/@ts-nocheck in {path}", ts_ignore)

        evals = []
        for i, ln in enumerate(lines, 1):
            if re.search(r"\beval\s*\(|new\s+Function\s*\(", ln) and "guardian: allow" not in ln:
                evals.append(f"{i}:{ln.strip()[:120]}")
        add(f"eval/new Function in {path}", evals)

    secrets = []
    for i, ln in enumerate(lines, 1):
        if "guardian: allow" in ln or "process.env" in ln or "os.environ" in ln:
            continue
        if re.search(r"(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", ln, re.I):
            secrets.append(f"{i}:{ln.strip()[:100]}")
    add(f"Possible hardcoded secret in {path}", secrets)

    if not warnings:
        if client == "":
            print("{}")
        sys.exit(0)

    report = "=== agent-guard code quality ===\n\n" + "\n\n---\n\n".join(warnings)
    report += "\n\nFix before done. Bypass line: // guardian: allow <reason>"
    emit_post_block(client, report)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)

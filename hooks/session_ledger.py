#!/usr/bin/env python3
"""
Session / handoff ledger for multi-CLI agents.

Modes:
  record — PostToolUse: accumulate edits & shell into session state
  flush — Stop / SessionEnd: write .agents/session-log entry + INDEX
  note — optional: append to .agents/agent-notes/OPEN.md

Community names we align with:
  - agent handoff log (X: BuildIdeaDaily)
  - session ledger / coding journal
  - decision log / ADR for big choices (manual or later)
  - agent notes for debt / simplify later

Does NOT invent prose changelog. Writes evidence from tools + git.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(os.environ.get("AGENT_LEDGER_STATE", f"/tmp/agent-session-ledger-{os.getuid()}"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib_payload import (  # type: ignore
        read_payload,
        detect_client,
        tool_name,
        tool_input,
        shell_command,
        file_path,
        is_shell_tool,
        is_edit_tool,
    )
except Exception:
    def read_payload():
        try:
            return json.loads(sys.stdin.read() or "{}")
        except Exception:
            return {}
    def detect_client(p): return os.environ.get("AGENT_HOOK_CLIENT", "claude")
    def tool_name(p): return p.get("tool_name") or p.get("toolName") or ""
    def tool_input(p): return p.get("tool_input") or p.get("toolInput") or {}
    def shell_command(p):
        ti = tool_input(p) if isinstance(tool_input(p), dict) else {}
        return ti.get("command") or ti.get("CommandLine") or ""
    def file_path(p):
        ti = tool_input(p) if isinstance(tool_input(p), dict) else {}
        return ti.get("file_path") or ti.get("path") or ti.get("target_file") or ""
    def is_shell_tool(n): return n.lower() in {"bash", "run_terminal_command", "run_command", "shell"}
    def is_edit_tool(n): return n.lower() in {"edit", "write", "multiedit", "search_replace", "apply_patch", "write_to_file", "replace_file_content", "multi_replace_file_content"}

def session_key(p: dict) -> str:
    for k in ("session_id", "sessionId", "SESSION_ID"):
        v = p.get(k) or os.environ.get(k)
        if v:
            return re.sub(r"[^a-zA-Z0-9._-]", "_", str(v))[:80]
    # fallback: cwd + client + day
    cwd = p.get("cwd") or p.get("workspaceRoot") or os.getcwd()
    client = detect_client(p)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{client}-{day}-{abs(hash(cwd)) % 10**8}"

def project_root(cwd: str) -> Path:
    c = Path(cwd).resolve()
    try:
        r = subprocess.run(
            ["git", "-C", str(c), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except Exception:
        pass
    # walk up for markers
    for p in [c, *c.parents]:
        if (p / ".git").exists() or (p / "package.json").exists() or (p / "pyproject.toml").exists():
            return p
        if p == p.parent:
            break
    return c

def load_state(key: str) -> dict:
    f = STATE_DIR / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {
        "key": key,
        "started": datetime.now(timezone.utc).isoformat(),
        "files": [],
        "shell": [],
        "client": None,
        "agent": None,
        "cwd": None,
    }

def save_state(st: dict) -> None:
    f = STATE_DIR / f"{st['key']}.json"
    f.write_text(json.dumps(st, ensure_ascii=False, indent=2))

def mode() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.environ.get("AGENT_LEDGER_MODE", "record")

def do_record(p: dict) -> None:
    key = session_key(p)
    st = load_state(key)
    st["client"] = detect_client(p)
    st["agent"] = p.get("agent_type") or p.get("agent") or st.get("agent")
    st["cwd"] = p.get("cwd") or p.get("workspaceRoot") or st.get("cwd") or os.getcwd()
    name = tool_name(p)
    path = file_path(p)
    if path and (is_edit_tool(name) or name.lower() in {"write", "edit"} or path):
        # record edits; also record if path present on write tools
        if is_edit_tool(name) or name.lower() in {"write", "edit", "multiedit", "apply_patch"}:
            if path not in st["files"]:
                st["files"].append(path)
    if is_shell_tool(name):
        cmd = shell_command(p).strip()
        if cmd:
            short = cmd if len(cmd) <= 200 else cmd[:200] + "…"
            if short not in st["shell"]:
                st["shell"].append(short)
            # keep last 40
            st["shell"] = st["shell"][-40:]
    st["updated"] = datetime.now(timezone.utc).isoformat()
    save_state(st)

def git_snapshot(root: Path) -> str:
    parts = []
    try:
        for args in (
            ["git", "-C", str(root), "status", "-sb"],
            ["git", "-C", str(root), "diff", "--stat", "HEAD"],
            ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
        ):
            r = subprocess.run(args, capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                parts.append(r.stdout.strip())
    except Exception as e:
        parts.append(f"(git unavailable: {e})")
    return "\n\n".join(parts) if parts else "(clean or not a git repo)"

def extract_debt_from_files(files: list[str]) -> list[str]:
    debt = []
    for f in files[-30:]:
        p = Path(f)
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", ln) and "guardian: allow" not in ln:
                debt.append(f"{f}:{i}: {ln.strip()[:120]}")
                if len(debt) >= 15:
                    return debt
    return debt

def do_flush(p: dict) -> None:
    key = session_key(p)
    st = load_state(key)
    cwd = p.get("cwd") or p.get("workspaceRoot") or st.get("cwd") or os.getcwd()
    root = project_root(str(cwd))
    files = st.get("files") or []
    shell = st.get("shell") or []
    # also merge git changed names
    git_txt = git_snapshot(root)
    client = st.get("client") or detect_client(p) or "agent"
    agent = st.get("agent") or "unknown"
    now = datetime.now().astimezone()
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%H%M%S")
    log_dir = root / ".agents" / "session-log" / day
    log_dir.mkdir(parents=True, exist_ok=True)
    short = key[-8:] if len(key) > 8 else key
    out = log_dir / f"{stamp}-{client}-{short}.md"

    # skip empty sessions (no edits, no shell)
    if not files and not shell and "nothing to commit" in git_txt and not re.search(r"^\s*M |\?\?", git_txt, re.M):
        # still write micro marker only if env forces
        if os.environ.get("AGENT_LEDGER_ALWAYS") != "1":
            return

    debt = extract_debt_from_files(files)
    file_list = "\n".join(f"- `{f}`" for f in files) or "- (none recorded via edit tools)"
    shell_list = "\n".join(f"- `{s}`" for s in shell[-20:]) or "- (none recorded)"
    debt_list = "\n".join(f"- {d}" for d in debt) if debt else "- (none detected in touched files)"

    body = f"""# Session ledger — {now.strftime('%Y-%m-%d %H:%M %Z')}

> Auto-generated agent **handoff / session ledger** (not a human CHANGELOG).
> Names in the wild: *session ledger*, *agent handoff log*, *coding journal*, *decision log* (ADR for big choices).

| | |
|--|--|
| client | `{client}` |
| agent | `{agent}` |
| project | `{root}` |
| session | `{key}` |

## What was touched (tool evidence)

{file_list}

## Shell (sampled)

{shell_list}

## Git snapshot

```
{git_txt[:4000]}
```

## Why / intent

_Not available from hooks alone (no model summary)._ 
Fill later or from run report: ` .agents/runs/*/artifacts/*/report.md `.

## Follow-ups / simplify / fix later

{debt_list}

## Night-audit hooks

- Scan this file for incomplete verification / TODO debt
- Cross-check `git_txt` paths vs tests
- Promote durable rules into `AGENTS.md` / `docs/decisions.md` if architectural

---
_generated by `~/.agents/hooks/session_ledger.py`_
"""
    out.write_text(body)

    # INDEX (newest first)
    index = root / ".agents" / "session-log" / "INDEX.md"
    line = f"- [{day} {stamp}]({day}/{out.name}) — {client}/{agent} — files:{len(files)} shell:{len(shell)}\n"
    header = "# Session log (agent handoff index)\n\n"
    if index.exists():
        prev = index.read_text()
        body_lines = prev.splitlines()
        # skip title + leading blanks
        i = 0
        if body_lines and body_lines[0].startswith("#"):
            i = 1
        while i < len(body_lines) and body_lines[i].strip() == "":
            i += 1
        body = "\n".join(body_lines[i:])
        if body and not body.endswith("\n"):
            body += "\n"
        index.write_text(header + line + body)
    else:
        index.write_text(header + line)

    # Agent notes OPEN backlog
    if debt:
        notes_dir = root / ".agents" / "agent-notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        open_f = notes_dir / "OPEN.md"
        header = "# Agent notes — open improvements\n\n> Debt / simplify / fix-later surfaced by agents. Night audit closes or promotes items.\n\n"
        block = f"## {day} {stamp} ({client})\n\n" + "\n".join(f"- [ ] {d}" for d in debt) + "\n\n"
        if open_f.exists():
            open_f.write_text(open_f.read_text() + block)
        else:
            open_f.write_text(header + block)

    # Touch PROGRESS.md auto section (create from template if missing)
    try:
        progress = root / "PROGRESS.md"
        tpl = Path.home() / ".agents" / "templates" / "PROGRESS.md"
        if not progress.exists() and tpl.exists():
            progress.write_text(tpl.read_text())
        if progress.exists():
            pt = progress.read_text()
            auto_start = "<!-- auto:session-ledger -->"
            auto_end = "<!-- /auto:session-ledger -->"
            auto_body = (
                f"{auto_start}\n"
                f"## Auto (session ledger)\n"
                f"- last flush: {now.strftime('%Y-%m-%d %H:%M %Z')}\n"
                f"- client/agent: `{client}` / `{agent}`\n"
                f"- entry: `.agents/session-log/{day}/{out.name}`\n"
                f"- files this session: {len(files)} · shell samples: {len(shell)}\n"
                f"- open INDEX: `.agents/session-log/INDEX.md`\n"
                f"{auto_end}\n"
            )
            # Prefer LAST start marker (template prose must not contain the marker)
            if auto_start in pt and auto_end in pt:
                s = pt.rfind(auto_start)
                e = pt.find(auto_end, s)
                if s >= 0 and e > s:
                    e2 = e + len(auto_end)
                    progress.write_text(pt[:s] + auto_body + pt[e2:].lstrip("\n"))
                else:
                    progress.write_text(pt.rstrip() + "\n\n" + auto_body)
            else:
                progress.write_text(pt.rstrip() + "\n\n" + auto_body)
    except Exception:
        pass

    # clear state after flush
    try:
        (STATE_DIR / f"{key}.json").unlink(missing_ok=True)
    except Exception:
        pass

def main() -> None:
    m = mode()
    p = read_payload()
    if m == "record":
        do_record(p)
    elif m in ("flush", "stop", "session_end"):
        do_flush(p)
    else:
        do_record(p)
    # always silent success for non-blocking hooks
    if detect_client(p) == "" and m == "record":
        print("{}")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)

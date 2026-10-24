#!/usr/bin/env python3
"""The SMA session hooks of Lane Stack (SMA map: Claude Code session hooks), one dispatcher per event: `sma_hooks.py <Event>`.

SessionStart       window registration and name, session model sighting, sessions/collisions, memory before the first act, what changed
                   since last time, the guard of disabled protections, the weekly digest rebuild, the MEMORY.md budget line, the capsule
                   restored after compaction — one context block.
UserPromptSubmit   heal a stale index, search memory by the prompt words, never repeat what was given, pointers beside the prompt,
                   the note citation ledger.
PreToolUse         streams in order over one shared context, a soft budget of 1.5 s, timings to perf.jsonl, merged into one answer:
                   claim collision, enforcing foreign claims, checkable hard rules, git airbag, dependency store, window work fingerprint,
                   reflexes from lessons, spend and rule loops, knowledge at the act. Only a foreign claim or a hard rule denies; every
                   other stream advises (the advice is handed to the model by the next PostToolUse).
PreToolUse Task    the spend cap on subagents and the context pack sewn into the subagent's prompt (spawn records).
PostToolUse        the advice of the streams; the attempt trail.
Stop               turn diff: did the edits leave the claim; the attempt trail of the window.
SubagentStop       claimed writes from the transcript checked against the real tree; the receipt into the shared journal.
PreCompact         the flight capsule (the goal, the last asks, the files at work, the claims) and the worker's progress summary.
SessionEnd         release own claims, drop the window lease, a farewell lesson draft.

A hook never wedges a session: every stream has a time limit and an error in a stream is written to perf.jsonl and skipped.
Lane sessions always; the owner's plain sessions only when ~/.agents/config/coord.json says {"plain_sessions": true}.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_coord as coord  # noqa: E402

SOFT_BUDGET_SEC = 1.5
HOME = Path.home()
STATE = HOME / ".agents" / "state" / "sma"
SUBAGENT_CAP = int(os.environ.get("LANE_SUBAGENT_CAP", "8") or 8)
DEPENDENCY_FILES = re.compile(r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?|Cargo\.lock|poetry\.lock|uv\.lock|go\.sum|Gemfile\.lock)$|(^|/)node_modules/")
DESTRUCTIVE_GIT = re.compile(r"\bgit\s+(checkout\s+--|restore\b|reset\b|clean\b|stash\s+(drop|clear)|rebase\b|branch\s+-D)")
EDIT_TOOLS = {"edit", "multiedit", "write", "notebookedit"}


def session_id(p: dict) -> str:
    return str(p.get("session_id") or os.environ.get("CLAUDE_SESSION_ID") or "unknown")


def state_of(session: str) -> dict[str, Any]:
    try:
        return json.loads((STATE / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:80]}.json").read_text())
    except (OSError, ValueError):
        return {}


def save_state(session: str, data: dict[str, Any]) -> None:
    coord.atomic_write(STATE / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:80]}.json", json.dumps(data, ensure_ascii=False))


def perf(stream: str, started: float, error: str | None = None) -> None:
    try:
        coord.append_jsonl("perf.jsonl", {"stream": stream, "ms": round((time.time() - started) * 1000), **({"error": error[:200]} if error else {})})
    except OSError:
        pass


def run(cmd: list[str], timeout: float, cwd: str | None = None) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def lane_memory() -> str | None:
    for candidate in (HOME / ".agents" / "bin" / "lane-memory", Path(__file__).resolve().parent.parent / "bin" / "lane-memory"):
        if candidate.exists():
            return str(candidate)
    return None


# ------------------------------------------------------------------ SessionStart

def protections_off() -> list[str]:
    """Guard of disabled protections: switches that turn a protection off in this session, and a guard hook missing from the settings."""
    off = [name for name in ("LANE_STALL_CHECK", "LANE_PM_STOP_SENTINEL", "LANE_TEAMMATE_IDLE_SENTINEL", "LANE_COORD", "LANE_OWNER_PRESENCE") if os.environ.get(name) == "0"]
    try:
        settings = json.loads((HOME / ".claude" / "settings.json").read_text())
        commands = json.dumps(settings.get("hooks", {}))
        if "guard_shell.py" not in commands:
            off.append("guard_shell.py is not registered in ~/.claude/settings.json")
    except (OSError, ValueError):
        pass
    return off


def memory_budget_line(cwd: str) -> str | None:
    """MEMORY.md budget line: Claude Code loads the first 200 lines of the project's MEMORY.md; say how close it is."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd))
    path = HOME / ".claude" / "projects" / slug / "memory" / "MEMORY.md"
    if not path.exists():
        return None
    lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    return f"MEMORY.md: {lines}/200 lines" + (" — near the limit: merge or trim entries" if lines > 170 else "")


def session_start(p: dict) -> dict | None:
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    st = state_of(sid)
    parts: list[str] = []
    model = str(p.get("model") or os.environ.get("ANTHROPIC_MODEL") or "")
    last_model = st.get("model")
    record = coord.register(sid, description=str(p.get("source") or ""), model=model, cwd=cwd)
    coord.journal(sid, "session_start", {"source": p.get("source"), "model": model}, cwd)
    if last_model and model and last_model != model:
        parts.append(f"Model change: this session ran on {last_model}, now on {model}; earlier receipts of this window were made by the other model.")
    others = coord.digest(sid, cwd, since=float(st.get("last_seen", 0)) or None)
    if others:
        parts.append("Other windows in this repository:\n" + others)
    # Whose subscription is this session: the account Claude Code is signed in with (or the config folder that names one).
    account = os.environ.get("CLAUDE_CONFIG_DIR", "")
    try:
        account = account or json.loads((HOME / ".claude.json").read_text()).get("oauthAccount", {}).get("emailAddress", "")
    except (OSError, ValueError):
        pass
    if account:
        parts.append(f"Subscription of this session: {account}")
    off = protections_off()
    if off:
        parts.append("Protections switched off: " + "; ".join(off))
    budget = memory_budget_line(cwd)
    if budget:
        parts.append(budget)
    lm = lane_memory()
    if lm:
        stamp = HOME / ".agents" / "state" / "sma" / "weekly-digest.stamp"
        if not stamp.exists() or time.time() - stamp.stat().st_mtime > 7 * 86400:
            subprocess.Popen([lm, "index"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            coord.atomic_write(stamp, str(time.time()))
            parts.append("Weekly digest rebuild started (lane-memory index, in the background).")
    if p.get("source") == "compact":
        capsule = coord.read_capsule(sid, cwd)
        if capsule:
            parts.append("Capsule restored after compaction:\n" + json.dumps({k: capsule[k] for k in capsule if k != "at"}, ensure_ascii=False)[:3000])
    st.update({"model": model or last_model, "last_seen": time.time(), "given": st.get("given", []), "name": record.get("name")})
    save_state(sid, st)
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(parts)}} if parts else None


# ------------------------------------------------------------------ UserPromptSubmit

def prompt_recall(p: dict) -> dict | None:
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    prompt = str(p.get("prompt") or "")
    lm = lane_memory()
    if not lm or len(prompt) < 12:
        return None
    started = time.time()
    st = state_of(sid)
    index_stamp = HOME / ".agents" / "state" / "sma" / "index.stamp"
    if not index_stamp.exists() or time.time() - index_stamp.stat().st_mtime > 86400:   # heal a stale index, once a day
        subprocess.Popen([lm, "index"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        coord.atomic_write(index_stamp, str(time.time()))
    words = " ".join(re.findall(r"[\wа-яё]{4,}", prompt.lower())[:12])
    out = run([lm, "search", words, "--limit", "4", "--json"], timeout=1.2, cwd=cwd)
    perf("prompt_recall", started)
    try:
        hits = json.loads(out) if out.strip() else []
    except ValueError:
        return None
    hits = hits.get("results", hits) if isinstance(hits, dict) else hits
    given = set(st.get("given", []))
    fresh = [hit for hit in hits if isinstance(hit, dict) and str(hit.get("id")) not in given][:3]   # never repeat what was given
    if not fresh:
        return None
    st["given"] = sorted(given | {str(hit.get("id")) for hit in fresh})[-300:]
    save_state(sid, st)
    for hit in fresh:
        coord.append_jsonl("citations.jsonl", {"session": sid, "id": hit.get("id"), "words": words[:120]}, cwd)   # note citation ledger
    pointers = "\n".join(f"- [{hit.get('id')}] {str(hit.get('content') or hit.get('text') or '')[:220]}" for hit in fresh)
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": f"Memory for these words (pointers, not orders):\n{pointers}"}}


# ------------------------------------------------------------------ PreToolUse streams

def stream_claims(ctx: dict) -> tuple[str | None, str | None]:
    """Claim collision and enforcing foreign claims: an edit claims its file for this window; a file a live other window claimed is refused."""
    if ctx["tool"] not in EDIT_TOOLS or not ctx["path"]:
        return None, None
    holder = coord.foreign_holder(ctx["path"], ctx["sid"], ctx["cwd"])
    if holder:
        return f"[lane-coord] {ctx['path']} is claimed by another live window ({holder.get('session', '')[:8]}: {holder.get('why') or holder.get('pattern')}). Work elsewhere, or ask that window; `lane-coord force-clear '{holder.get('pattern')}' --reason <why>` clears a claim of a window that is gone.", None
    rel = os.path.relpath(os.path.realpath(ctx["path"]), coord.repo_root(ctx["cwd"])) if os.path.isabs(ctx["path"]) else ctx["path"]
    coord.claim(ctx["sid"], [rel], ctx["cwd"], why="edited")
    return None, None


def stream_hard_rules(ctx: dict) -> tuple[str | None, str | None]:
    """Checkable hard rules: the project's .agents/hard-rules.json [{tool, pattern, message}] — a match is refused with its message."""
    path = Path(coord.repo_root(ctx["cwd"])) / ".agents" / "hard-rules.json"
    try:
        rules = json.loads(path.read_text())
    except (OSError, ValueError):
        return None, None
    subject = ctx["command"] or ctx["path"]
    for rule in rules if isinstance(rules, list) else []:
        if (not rule.get("tool") or rule["tool"].lower() == ctx["tool"]) and rule.get("pattern") and re.search(rule["pattern"], subject):
            return f"[hard-rule] {rule.get('message', rule['pattern'])}", None
    return None, None


def stream_git_airbag(ctx: dict) -> tuple[str | None, str | None]:
    """Git airbag: before a git command that drops uncommitted work, the work is saved under refs/lane-airbag/ (git stash create)."""
    if not ctx["command"] or not DESTRUCTIVE_GIT.search(ctx["command"]):
        return None, None
    sha = run(["git", "stash", "create"], timeout=1.0, cwd=ctx["cwd"]).strip()
    if sha:
        ref = f"refs/lane-airbag/{int(time.time())}"
        run(["git", "update-ref", ref, sha], timeout=0.5, cwd=ctx["cwd"])
        return None, f"[git-airbag] uncommitted work saved as {ref} ({sha[:10]}): `git stash apply {sha[:10]}` brings it back."
    return None, None


def stream_dependency_store(ctx: dict) -> tuple[str | None, str | None]:
    """Dependency store guard and watch: lockfiles and node_modules are written by the package manager, never by hand."""
    if ctx["tool"] in EDIT_TOOLS and ctx["path"] and DEPENDENCY_FILES.search(ctx["path"]):
        coord.append_jsonl("dependency-watch.jsonl", {"session": ctx["sid"], "path": ctx["path"]}, ctx["cwd"])
        return None, f"[dependency-store] {ctx['path']} belongs to the package manager: change the manifest and run the install, do not edit the lockfile or node_modules by hand."
    return None, None


def stream_fingerprint(ctx: dict) -> tuple[str | None, str | None]:
    """Window work fingerprint: the window's uncommitted state, kept on its lease (other windows see it moved)."""
    if ctx["tool"] in EDIT_TOOLS:
        coord.pulse(ctx["sid"], ctx["cwd"], coord.work_fingerprint(ctx["cwd"]))
    return None, None


def stream_reflexes(ctx: dict) -> tuple[str | None, str | None]:
    """Reflexes from lessons: lines of the project's .agents/LESSONS.md written as «WHEN <pattern> → <advice>» fire at the act."""
    path = Path(coord.repo_root(ctx["cwd"])) / ".agents" / "LESSONS.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, None
    subject = f"{ctx['tool']} {ctx['command']} {ctx['path']}"
    for line in lines:
        match = re.match(r"^\s*[-*]?\s*WHEN\s+(.+?)\s*(?:→|->)\s*(.+)$", line)
        if match and fnmatch.fnmatch(subject, f"*{match.group(1)}*"):
            return None, f"[reflex] {match.group(2)}"
    return None, None


def stream_rule_loops(ctx: dict) -> tuple[str | None, str | None]:
    """Spend and rule loops: a rule that refused this session three times means the approach, not the rule, has to change."""
    denials = ctx["state"].get("denials", {})
    worst = max(denials.items(), key=lambda kv: kv[1], default=(None, 0))
    if worst[1] >= 3:
        return None, f"[rule-loop] «{worst[0]}» refused you {worst[1]} times this session: stop retrying variants, change the approach or ask."
    return None, None


def stream_knowledge(ctx: dict) -> tuple[str | None, str | None]:
    """Knowledge at the act: the file card — memory notes that name the file about to change."""
    lm = lane_memory()
    if ctx["tool"] not in EDIT_TOOLS or not ctx["path"] or not lm:
        return None, None
    # The file card catalog (lane-memory card): notes that name this file, masked, and cited in the usage ledger.
    out = run([lm, "card", ctx["path"], "--json", ctx["cwd"]], timeout=0.6, cwd=ctx["cwd"])
    try:
        notes = json.loads(out) if out.strip() else []
    except ValueError:
        return None, None
    notes = [note for note in notes if isinstance(note, dict) and note.get("claim")][:2]
    return (None, "[file-card] " + " | ".join(str(note["claim"])[:200] for note in notes)) if notes else (None, None)


STREAMS: list[tuple[str, Callable[[dict], tuple[str | None, str | None]]]] = [
    ("claims", stream_claims), ("hard_rules", stream_hard_rules), ("git_airbag", stream_git_airbag), ("dependency_store", stream_dependency_store),
    ("fingerprint", stream_fingerprint), ("reflexes", stream_reflexes), ("rule_loops", stream_rule_loops), ("knowledge", stream_knowledge),
]


def pre_tool(p: dict) -> dict | None:
    tool = str(p.get("tool_name") or "").lower()
    tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    if tool in {"task", "agent"}:
        return pretask_pack(p, tin, sid, cwd)
    st = state_of(sid)
    ctx = {"tool": tool, "sid": sid, "cwd": cwd, "state": st, "command": str(tin.get("command") or ""), "path": str(tin.get("file_path") or tin.get("notebook_path") or "")}
    begun = time.time()
    deny, advice = None, []
    for name, stream in STREAMS:
        if time.time() - begun > SOFT_BUDGET_SEC:   # soft budget: the remaining streams skip this call
            perf(name, time.time(), "skipped: soft budget spent")
            continue
        started = time.time()
        try:
            refused, said = stream(ctx)
        except Exception as exc:  # a stream never wedges the call
            perf(name, started, f"{type(exc).__name__}: {exc}")
            continue
        perf(name, started)
        if refused and not deny:
            deny = refused
            st.setdefault("denials", {})[name] = int(st.get("denials", {}).get(name, 0)) + 1
        if said:
            advice.append(said)
    if advice:
        st["advice"] = (st.get("advice", []) + advice)[-6:]
    save_state(sid, st)
    if deny:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": deny}}
    return None


def pretask_pack(p: dict, tin: dict, sid: str, cwd: str) -> dict | None:
    """Spend cap on subagents, then the context pack sewn into the prompt; each spawn is recorded."""
    st = state_of(sid)
    spawned = int(st.get("subagents", 0))
    if spawned >= SUBAGENT_CAP:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": f"[subagent-cap] {spawned} subagents already in this session (cap {SUBAGENT_CAP}, LANE_SUBAGENT_CAP): finish with what you have or do it yourself."}}
    st["subagents"] = spawned + 1
    save_state(sid, st)
    claims = [row["pattern"] for row in coord._read(coord.store(cwd) / "claims.json", []) if row.get("session") == sid][:20]
    pack = f"\n\n[context pack] Repository {coord.repo_root(cwd)}. Files this window claims: {', '.join(claims) or 'none'}. Report the files you changed by path at the end."
    coord.append_jsonl("subagents.jsonl", {"session": sid, "type": tin.get("subagent_type"), "description": str(tin.get("description") or "")[:200]}, cwd)
    prompt = str(tin.get("prompt") or "")
    if prompt and "[context pack]" not in prompt:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {**tin, "prompt": prompt + pack}}}
    return None


def post_tool(p: dict) -> dict | None:
    sid = session_id(p)
    st = state_of(sid)
    advice = st.pop("advice", [])
    save_state(sid, st)
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(advice)}} if advice else None


# ------------------------------------------------------------------ Stop, SubagentStop, PreCompact, SessionEnd

def changed_files(cwd: str) -> list[str]:
    return [line[3:] for line in run(["git", "status", "--porcelain"], timeout=2, cwd=cwd).splitlines() if len(line) > 3]


def stop(p: dict) -> dict | None:
    """Turn diff: what the turn left changed, kept on the attempt trail; edits outside this window's claims are named."""
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    files = changed_files(cwd)
    st = state_of(sid)
    coord.append_jsonl("attempts.jsonl", {"session": sid, "name": st.get("name"), "files": files[:40]}, cwd)
    claims = [row["pattern"] for row in coord._read(coord.store(cwd) / "claims.json", []) if row.get("session") == sid]
    outside = [f for f in files if claims and not any(coord._overlap(f, c) for c in claims)]
    coord.journal(sid, "turn", {"files": files[:40], "outside_claims": outside[:20]}, cwd)
    return None


def subagent_verify(p: dict) -> dict | None:
    """Claimed writes from the transcript, checked against the real tree; the receipt goes into the shared journal."""
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    transcript = p.get("agent_transcript_path") or p.get("transcript_path")
    claimed: set[str] = set()
    try:
        for line in Path(str(transcript)).read_text(encoding="utf-8").splitlines()[-2000:]:
            entry = json.loads(line)
            for block in (entry.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and str(block.get("name", "")).lower() in EDIT_TOOLS:
                    path = (block.get("input") or {}).get("file_path")
                    if path:
                        claimed.add(str(path))
    except (OSError, ValueError, TypeError):
        return None
    root = coord.repo_root(cwd)
    real = set(changed_files(cwd))
    missing = sorted(path for path in claimed if os.path.relpath(path, root) not in real and not os.path.exists(path))
    coord.journal(sid, "subagent_receipt", {"claimed": sorted(claimed)[:40], "missing": missing[:20]}, cwd)
    if missing:
        return {"hookSpecificOutput": {"hookEventName": "SubagentStop", "additionalContext": f"[subagent-verify] the subagent says it wrote {', '.join(missing[:6])}, but the tree does not have them: check before you rely on it."}}
    return None


def precompact(p: dict) -> dict | None:
    """The flight capsule: what the window was doing, written before compaction and restored after it (SessionStart source=compact)."""
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    asks: list[str] = []
    try:
        for line in Path(str(p.get("transcript_path"))).read_text(encoding="utf-8").splitlines()[-400:]:
            entry = json.loads(line)
            if entry.get("type") == "user" and isinstance((entry.get("message") or {}).get("content"), str):
                asks.append(entry["message"]["content"][:300])
    except (OSError, ValueError, TypeError):
        pass
    claims = [row["pattern"] for row in coord._read(coord.store(cwd) / "claims.json", []) if row.get("session") == sid]
    coord.write_capsule(sid, {"asks": asks[-5:], "files": changed_files(cwd)[:30], "claims": claims[:30], "trigger": p.get("trigger")}, cwd)
    coord.append_jsonl("progress.jsonl", {"session": sid, "files": len(changed_files(cwd)), "asks": len(asks)}, cwd)   # the worker's progress summary
    return None


def session_end(p: dict) -> dict | None:
    """Release own claims, drop the window lease, and leave a farewell lesson draft when the turns changed files."""
    sid, cwd = session_id(p), str(p.get("cwd") or os.getcwd())
    trail = [row for row in coord.tail_jsonl("attempts.jsonl", cwd, limit=200) if row.get("session") == sid]
    coord.drop(sid, cwd)
    coord.journal(sid, "session_end", {"turns": len(trail)}, cwd)
    if trail:
        files = sorted({f for row in trail for f in row.get("files", [])})[:20]
        draft = STATE / "drafts" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', sid)[:80]}.md"
        coord.atomic_write(draft, f"# Farewell lesson draft ({time.strftime('%Y-%m-%d %H:%M')})\n\nThis session changed: {', '.join(files)}.\nWhat should the next window know? (a draft: it waits for a person or the memory maintainer)\n")
    return None


HANDLERS = {"SessionStart": session_start, "UserPromptSubmit": prompt_recall, "PreToolUse": pre_tool, "PostToolUse": post_tool,
            "Stop": stop, "SubagentStop": subagent_verify, "PreCompact": precompact, "SessionEnd": session_end}


def main(argv: list[str]) -> int:
    event = argv[0] if argv else ""
    handler = HANDLERS.get(event)
    if not handler or not coord.coord_enabled():
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    started = time.time()
    try:
        out = handler(payload)
    except Exception as exc:  # a hook never wedges a session
        perf(event, started, f"{type(exc).__name__}: {exc}")
        return 0
    perf(event, started)
    if out:
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

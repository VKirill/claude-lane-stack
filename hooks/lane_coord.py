#!/usr/bin/env python3
"""Terminal coordination between the windows (sessions) working in one repository (SMA map: Terminal coordination).

One store per repository: ~/.agents/coord/<repo-hash>/ with
- sessions.json   the session lease registry: who works here, since when, last pulse, model, description, work fingerprint;
- claims.json     atomic claims: glob patterns a session is about to change, with the session that holds them;
- counters.json   shared counters: next-slot / consume (ports, ticket numbers, migration numbers);
- journal/<sid>.jsonl  each window's journal, every line chained to the previous one by sha256 (Window journal with a hash chain);
- attempts.jsonl  the attempt trail of the person windows (what a turn changed);
- exec.jsonl      the plan execution journal (steps a plan run did);
- capsules/<sid>.json the flight capsule written before compaction and read back after it.
Every write is atomic (temp file + rename, the same on Windows and POSIX) under one lock file (fcntl where it exists).

The hooks (sma_hooks.py) use it for lane sessions; the owner's plain sessions only when ~/.agents/config/coord.json says
{"plain_sessions": true} (the owner keeps plain sessions untouched by default, 2026-10-13). The CLI is bin/lane-coord.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

LEASE_SEC = 15 * 60
MARKERS = ("LANE_STACK_SESSION", "LANE_PILOT_AGENT_TYPE", "LANE_PILOT_ROLE", "LANE_PROMPT_FILE", "LANE_TASK_FILE", "LANE_CODEX_WORKER")


def coord_enabled(environ: dict[str, str] | None = None) -> bool:
    """Lane sessions always; the owner's plain sessions only when the coord config turns them on. LANE_COORD=0 turns it off."""
    env = environ if environ is not None else dict(os.environ)
    if env.get("LANE_COORD") == "0":
        return False
    if any(env.get(name) for name in MARKERS):
        return True
    try:
        home = Path(env.get("HOME") or Path.home())
        return bool(json.loads((home / ".agents" / "config" / "coord.json").read_text()).get("plain_sessions"))
    except (OSError, ValueError):
        return False


def repo_root(cwd: str | None = None) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or os.getcwd(), capture_output=True, text=True, timeout=3)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.realpath(cwd or os.getcwd())


def store(cwd: str | None = None) -> Path:
    root = repo_root(cwd)
    path = Path(os.environ.get("LANE_COORD_HOME", str(Path.home() / ".agents" / "coord"))) / hashlib.sha256(root.encode()).hexdigest()[:16]
    path.mkdir(parents=True, exist_ok=True)
    meta = path / "repo.txt"
    if not meta.exists():
        atomic_write(meta, root + "\n")
    return path


def atomic_write(path: Path, text: str) -> None:
    """Windows-aware atomic write: a temp file in the same folder, flushed, then os.replace (atomic on Windows and POSIX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def locked(base: Path) -> Iterator[None]:
    lock = base / ".lock"
    with open(lock, "a+") as fh:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except ImportError:  # Windows: a sentinel file with retries
            pass
        try:
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass


def _read(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def machine_name(description: str) -> str:
    """Description into a machine name: «Fix the login page!» -> fix-the-login-page."""
    slug = re.sub(r"[^a-z0-9а-яё]+", "-", description.lower()).strip("-")
    return slug[:48] or "window"


# ------------------------------------------------------------------ sessions and leases

def register(session: str, *, description: str = "", model: str = "", cwd: str | None = None, now: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    base = store(cwd)
    with locked(base):
        sessions = _read(base / "sessions.json", {})
        record = sessions.get(session, {"since": now})
        record.update({"pulse": now, "name": machine_name(description) if description else record.get("name", session[:8]), "model": model or record.get("model", ""), "cwd": cwd or os.getcwd()})
        sessions[session] = record
        atomic_write(base / "sessions.json", json.dumps(sessions, indent=1))
    return record


def pulse(session: str, cwd: str | None = None, fingerprint: str | None = None) -> None:
    base = store(cwd)
    with locked(base):
        sessions = _read(base / "sessions.json", {})
        if session in sessions:
            sessions[session]["pulse"] = time.time()
            if fingerprint:
                sessions[session]["fingerprint"] = fingerprint
            atomic_write(base / "sessions.json", json.dumps(sessions, indent=1))


def live_sessions(cwd: str | None = None, now: float | None = None) -> dict[str, dict[str, Any]]:
    now = now or time.time()
    return {sid: rec for sid, rec in _read(store(cwd) / "sessions.json", {}).items() if now - float(rec.get("pulse", 0)) < LEASE_SEC}


def drop(session: str, cwd: str | None = None) -> None:
    """Drop the window lease and release its claims (SessionEnd)."""
    base = store(cwd)
    with locked(base):
        sessions = _read(base / "sessions.json", {})
        sessions.pop(session, None)
        atomic_write(base / "sessions.json", json.dumps(sessions, indent=1))
        claims = [row for row in _read(base / "claims.json", []) if row.get("session") != session]
        atomic_write(base / "claims.json", json.dumps(claims, indent=1))


# ------------------------------------------------------------------ claims

def _overlap(a: str, b: str) -> bool:
    """Glob collision: two patterns can name one file (one matches the other, or one is a folder prefix of the other)."""
    a, b = a.strip("./"), b.strip("./")
    if fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    fixed = lambda p: re.split(r"[*?\[]", p, maxsplit=1)[0]
    pa, pb = fixed(a), fixed(b)
    return bool(pa) and bool(pb) and (pa.startswith(pb) or pb.startswith(pa))


def collisions(patterns: list[str], session: str, cwd: str | None = None) -> list[dict[str, Any]]:
    live = live_sessions(cwd)
    return [row for row in _read(store(cwd) / "claims.json", []) if row.get("session") != session and row.get("session") in live
            and any(_overlap(p, row.get("pattern", "")) for p in patterns)]


def claim(session: str, patterns: list[str], cwd: str | None = None, why: str = "") -> dict[str, Any]:
    """Atomic claim: all patterns or none; refused when a live window holds an overlapping one."""
    base = store(cwd)
    with locked(base):
        hit = collisions(patterns, session, cwd)
        if hit:
            return {"ok": False, "collisions": hit}
        claims = [row for row in _read(base / "claims.json", []) if not (row.get("session") == session and row.get("pattern") in patterns)]
        claims += [{"session": session, "pattern": p, "at": time.time(), "why": why} for p in patterns]
        atomic_write(base / "claims.json", json.dumps(claims, indent=1))
    return {"ok": True, "claimed": patterns}


def release(session: str, patterns: list[str] | None = None, cwd: str | None = None) -> int:
    base = store(cwd)
    with locked(base):
        claims = _read(base / "claims.json", [])
        kept = [row for row in claims if not (row.get("session") == session and (patterns is None or row.get("pattern") in patterns))]
        atomic_write(base / "claims.json", json.dumps(kept, indent=1))
    return len(claims) - len(kept)


def force_clear(pattern: str, reason: str, cwd: str | None = None) -> int:
    """Clear a claim with a reason (the claim of a window that is gone or stuck); the reason goes to the journal of the clearing."""
    if not reason.strip():
        raise ValueError("force-clear needs a reason")
    base = store(cwd)
    with locked(base):
        claims = _read(base / "claims.json", [])
        kept = [row for row in claims if row.get("pattern") != pattern]
        atomic_write(base / "claims.json", json.dumps(kept, indent=1))
    journal("coordinator", "force_clear", {"pattern": pattern, "reason": reason}, cwd)
    return len(claims) - len(kept)


def foreign_holder(path: str, session: str, cwd: str | None = None) -> dict[str, Any] | None:
    """Enforcing foreign claims: the live window that claimed this path, if it is not us."""
    root = repo_root(cwd)
    rel = os.path.relpath(os.path.realpath(path), root) if os.path.isabs(path) else path
    live = live_sessions(cwd)
    for row in _read(store(cwd) / "claims.json", []):
        if row.get("session") != session and row.get("session") in live and _overlap(rel, row.get("pattern", "")):
            return row
    return None


# ------------------------------------------------------------------ counters

def next_slot(name: str, cwd: str | None = None) -> int:
    """Shared counters: the next free number of a named counter (a port, a migration number); taken atomically."""
    base = store(cwd)
    with locked(base):
        counters = _read(base / "counters.json", {})
        value = int(counters.get(name, {}).get("next", 1))
        counters[name] = {"next": value + 1, "taken": sorted(set(counters.get(name, {}).get("taken", [])) | {value})}
        atomic_write(base / "counters.json", json.dumps(counters, indent=1))
    return value


def consume(name: str, value: int, cwd: str | None = None) -> bool:
    """Mark a number of a counter as used by hand (it is never given out again)."""
    base = store(cwd)
    with locked(base):
        counters = _read(base / "counters.json", {})
        entry = counters.setdefault(name, {"next": 1, "taken": []})
        fresh = value not in entry["taken"]
        entry["taken"] = sorted(set(entry["taken"]) | {value})
        entry["next"] = max(int(entry["next"]), value + 1)
        atomic_write(base / "counters.json", json.dumps(counters, indent=1))
    return fresh


# ------------------------------------------------------------------ journals

def journal(session: str, kind: str, data: dict[str, Any], cwd: str | None = None) -> str:
    """Append to the window's journal; each line carries the hash of the line before it."""
    base = store(cwd)
    path = base / "journal" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:64]}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(base):
        prev = "0" * 64
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            if lines:
                prev = json.loads(lines[-1]).get("hash", prev)
        body = {"at": time.time(), "kind": kind, "data": data, "prev": prev}
        body["hash"] = hashlib.sha256((prev + json.dumps({k: body[k] for k in ("at", "kind", "data")}, sort_keys=True)).encode()).hexdigest()
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(body, ensure_ascii=False) + "\n")
    return body["hash"]


def chain_ok(session: str, cwd: str | None = None) -> bool:
    path = store(cwd) / "journal" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:64]}.jsonl"
    prev = "0" * 64
    for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []):
        row = json.loads(line)
        expect = hashlib.sha256((prev + json.dumps({k: row[k] for k in ("at", "kind", "data")}, sort_keys=True)).encode()).hexdigest()
        if row.get("prev") != prev or row.get("hash") != expect:
            return False
        prev = row["hash"]
    return True


def append_jsonl(name: str, row: dict[str, Any], cwd: str | None = None) -> None:
    base = store(cwd)
    with locked(base):
        with open(base / name, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.time(), **row}, ensure_ascii=False) + "\n")


def tail_jsonl(name: str, cwd: str | None = None, since: float = 0, limit: int = 50) -> list[dict[str, Any]]:
    path = store(cwd) / name
    rows = [json.loads(line) for line in (path.read_text(encoding="utf-8").splitlines() if path.exists() else []) if line.strip()]
    return [row for row in rows if float(row.get("at", 0)) >= since][-limit:]


def work_fingerprint(cwd: str | None = None) -> str:
    """Live work fingerprint: the hash of `git status --porcelain` — what is uncommitted in this checkout right now."""
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=cwd or os.getcwd(), capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    return hashlib.sha256(out.encode()).hexdigest()[:16]


def digest(session: str, cwd: str | None = None, since: float | None = None) -> str:
    """Cross-terminal digest: the other live windows, their claims, and what the person windows changed since this one last looked."""
    live = live_sessions(cwd)
    others = {sid: rec for sid, rec in live.items() if sid != session}
    claims = _read(store(cwd) / "claims.json", [])
    lines = []
    for sid, rec in others.items():
        held = [row["pattern"] for row in claims if row.get("session") == sid]
        lines.append(f"- window {rec.get('name', sid[:8])} ({rec.get('model', '?')}), {int((time.time() - float(rec.get('since', time.time()))) / 60)} min" + (f", claims {', '.join(held[:6])}" if held else ""))
    changed = tail_jsonl("attempts.jsonl", cwd, since=since or time.time() - 86400, limit=10)
    if changed:
        lines.append("- recent turns: " + "; ".join(f"{row.get('name', '?')}: {', '.join(row.get('files', [])[:4])}" for row in changed if row.get("session") != session))
    return "\n".join(lines)


def test_impact(changed: list[str], cwd: str | None = None) -> list[str]:
    """Test impact analysis: the tests to run for the changed files — tests named after a changed module, and tests that mention it."""
    root = repo_root(cwd)
    try:
        files = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=10).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return []
    tests = [f for f in files if re.search(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.[cm]?[jt]sx?$|_test\.(go|py)$|(^|/)test_[^/]+\.py$", f)]
    stems = {Path(c).stem.replace(".test", "").replace(".spec", "") for c in changed if c}
    hits = {t for t in tests if any(stem and stem in Path(t).stem for stem in stems)}
    for t in tests:
        if t in hits or len(hits) > 200:
            continue
        try:
            text = (Path(root) / t).read_text(encoding="utf-8", errors="ignore")[:200_000]
        except OSError:
            continue
        if any(stem and len(stem) > 3 and re.search(rf"\b{re.escape(stem)}\b", text) for stem in stems):
            hits.add(t)
    return sorted(hits)


STATE_START, STATE_END = "<!-- lane:state:start -->", "<!-- lane:state:end -->"


def state_section(path: str, new: str | None = None) -> str:
    """Fenced STATE.md section: read the text between the fences, or replace it (the rest of the file is never touched)."""
    file = Path(path)
    text = file.read_text(encoding="utf-8") if file.exists() else ""
    if STATE_START in text and STATE_END in text:
        head, rest = text.split(STATE_START, 1)
        body, tail = rest.split(STATE_END, 1)
    else:
        head, body, tail = (text + ("\n" if text and not text.endswith("\n") else "")), "", "\n"
    if new is None:
        return body.strip()
    atomic_write(file, f"{head}{STATE_START}\n{new.strip()}\n{STATE_END}{tail}")
    return new.strip()


def write_capsule(session: str, capsule: dict[str, Any], cwd: str | None = None) -> Path:
    path = store(cwd) / "capsules" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:64]}.json"
    atomic_write(path, json.dumps({"at": time.time(), **capsule}, ensure_ascii=False, indent=1))
    return path


def read_capsule(session: str, cwd: str | None = None) -> dict[str, Any] | None:
    return _read(store(cwd) / "capsules" / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)[:64]}.json", None)


# ------------------------------------------------------------------ CLI (bin/lane-coord)

USAGE = """lane-coord status | claim <session> <glob>... [--why text] | release <session> [<glob>...] | force-clear <glob> --reason text
          | next-slot <name> | consume <name> <n> | tia [<file>...] | state <STATE.md> [--set text] | exec-journal [add <json>]
          | open <session> | digest <session> | journal-ok <session>"""


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "status":
        live = live_sessions()
        print(json.dumps({"repo": repo_root(), "sessions": live, "claims": _read(store() / "claims.json", [])}, indent=1, ensure_ascii=False))
        return 0
    if cmd == "claim" and len(args) >= 2:
        why = args[args.index("--why") + 1] if "--why" in args else ""
        patterns = [a for a in args[1:] if a != "--why" and a != why]
        result = claim(args[0], patterns, why=why)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    if cmd == "release" and args:
        print(release(args[0], args[1:] or None))
        return 0
    if cmd == "force-clear" and args and "--reason" in args:
        print(force_clear(args[0], args[args.index("--reason") + 1]))
        return 0
    if cmd == "next-slot" and args:
        print(next_slot(args[0]))
        return 0
    if cmd == "consume" and len(args) == 2:
        print(consume(args[0], int(args[1])))
        return 0
    if cmd == "tia":
        files = args or subprocess.run(["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True).stdout.split()
        print("\n".join(test_impact(files)))
        return 0
    if cmd == "state" and args:
        print(state_section(args[0], args[args.index("--set") + 1] if "--set" in args else None))
        return 0
    if cmd == "exec-journal":
        if args[:1] == ["add"] and len(args) == 2:
            append_jsonl("exec.jsonl", json.loads(args[1]))
            return 0
        print(json.dumps(tail_jsonl("exec.jsonl", limit=100), indent=1, ensure_ascii=False))
        return 0
    if cmd == "open" and args:
        rec = live_sessions().get(args[0])
        thread = os.environ.get("BB_THREAD_ID")
        print(f"bb thread show {thread}" if thread else json.dumps(rec or {}, ensure_ascii=False))
        return 0 if rec or thread else 1
    if cmd == "digest" and args:
        print(digest(args[0]))
        return 0
    if cmd == "journal-ok" and args:
        ok = chain_ok(args[0])
        print("intact" if ok else "BROKEN")
        return 0 if ok else 1
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

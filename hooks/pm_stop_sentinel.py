#!/usr/bin/env python3
"""Keep the PM from parking while a run needs it.

Stop (sync):
  exit 2 — continue the turn; stderr is the reason.
  exit 0 — allow idle (also on Ctrl+C / session exit, and while rs-* is live).

PostToolUse Agent|Task (asyncRewake):
  if this spawn is run-supervisor / lane-supervisor, poll controller.json
  until stage is accepted|blocked|failed (or watch timeout), then exit 2
  so Claude Code wakes an idle session.

Disable: LANE_PM_STOP_SENTINEL=0
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
from pathlib import Path

PM_AGENTS = frozenset(
    {
        "dev-orchestrator",
        "frontend-orchestrator",
        "marketing-orchestrator",
        "site-architect",
    }
)
SUPERVISOR_TYPES = frozenset({"run-supervisor", "lane-supervisor"})
SUPERVISOR_RE = re.compile(
    r"(?:run-supervisor|lane-supervisor|\brs-[a-z0-9][a-z0-9-]*)",
    re.IGNORECASE,
)
RUN_DIR_RE = re.compile(r"\.agents/runs/([A-Za-z0-9._-]+)")
TERMINAL = frozenset({"accepted", "blocked", "failed"})
TAIL_CHARS = 8000
DEFAULT_POLL = 5.0
DEFAULT_WATCH_SEC = 7200.0
RUNNING_AGE_SEC = 24 * 3600
TERMINAL_AGE_SEC = 30 * 60


def _disabled() -> bool:
    return os.environ.get("LANE_PM_STOP_SENTINEL", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def _event(payload: dict) -> str:
    return str(payload.get("hook_event_name") or payload.get("hookEventName") or "")


def _cwd(payload: dict) -> Path:
    raw = payload.get("cwd") or payload.get("CWD") or os.getcwd()
    return Path(str(raw)).expanduser()


def _session_id(payload: dict) -> str:
    for key in ("session_id", "sessionId"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _mark_agent(session_id: str) -> str:
    if not session_id:
        return ""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in session_id)[:120]
    path = Path.home() / ".agents" / "statusline" / "sessions" / f"{safe}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    agent = data.get("agent_type")
    return agent.strip() if isinstance(agent, str) else ""


def is_pm_session(payload: dict) -> bool:
    agent = str(payload.get("agent_type") or payload.get("agentType") or "").strip()
    if agent in PM_AGENTS:
        return True
    marked = _mark_agent(_session_id(payload))
    return marked in PM_AGENTS


def last_assistant_text(payload: dict) -> str:
    for key in ("last_assistant_message", "lastAssistantMessage"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw
    return ""


def _blob(obj: object) -> str:
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj or "")


def is_supervisor_spawn(payload: dict) -> bool:
    tool = str(payload.get("tool_name") or payload.get("toolName") or "")
    if tool and tool not in {"Agent", "Task"}:
        return False
    tin = payload.get("tool_input") or payload.get("toolInput") or {}
    sub = ""
    if isinstance(tin, dict):
        sub = str(
            tin.get("subagent_type")
            or tin.get("agent_type")
            or tin.get("subagentType")
            or tin.get("name")
            or ""
        )
    if sub in SUPERVISOR_TYPES:
        return True
    return bool(SUPERVISOR_RE.search(f"{sub} {_blob(tin)}"))


# Host keeps finished rs-* chips in background_tasks. Only live watches
# may block Stop. Unknown/missing status stays in-flight (safer).
PARKED_STATUSES = frozenset(
    {
        "idle",
        "completed",
        "complete",
        "done",
        "finished",
        "failed",
        "stopped",
        "cancelled",
        "canceled",
        "error",
        "success",
    }
)
IN_FLIGHT_STATUSES = frozenset(
    {
        "running",
        "in_progress",
        "in-progress",
        "working",
        "active",
        "started",
        "busy",
        "pending",
    }
)


def _task_status(item: dict) -> str:
    for key in ("status", "state", "task_status", "taskStatus"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower()
    return ""


def supervisor_in_flight(item: dict) -> bool:
    """True when this roster chip is still watching, not a leftover rs-* idle."""
    if item.get("is_idle") is True or item.get("idle") is True:
        return False
    status = _task_status(item)
    if status in PARKED_STATUSES:
        return False
    if status in IN_FLIGHT_STATUSES:
        return True
    return not status


def supervisor_tasks(payload: dict, *, inflight_only: bool = False) -> list[dict]:
    raw = payload.get("background_tasks") or payload.get("backgroundTasks") or []
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        typ = str(item.get("type") or "").lower()
        if typ not in {"subagent", "agent", "teammate"}:
            continue
        agent = str(item.get("agent_type") or item.get("agentType") or "")
        desc = " ".join(
            str(item.get(k) or "")
            for k in ("agent_type", "agentType", "description", "name")
        )
        if not (agent in SUPERVISOR_TYPES or SUPERVISOR_RE.search(desc)):
            continue
        if inflight_only and not supervisor_in_flight(item):
            continue
        out.append(item)
    return out


def run_slug_from_payload(payload: dict) -> str:
    tin = payload.get("tool_input") or payload.get("toolInput") or {}
    match = RUN_DIR_RE.search(_blob(tin))
    return match.group(1) if match else ""


def controller_path(cwd: Path, slug: str) -> Path:
    return cwd / ".agents" / "runs" / slug / "controller.json"


def read_stage(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("stage") or "")


def pick_controller(cwd: Path, *, now: float | None = None, slug: str = "") -> Path | None:
    if slug:
        path = controller_path(cwd, slug)
        if path.is_file():
            return path
    root = cwd / ".agents" / "runs"
    if not root.is_dir():
        return None
    now = time.time() if now is None else now
    best: tuple[float, Path] | None = None
    for path in root.glob("*/controller.json"):
        try:
            mtime = path.stat().st_mtime
            stage = read_stage(path)
        except OSError:
            continue
        age = now - mtime
        if stage == "running" and age <= RUNNING_AGE_SEC:
            pass
        elif stage in TERMINAL and age <= TERMINAL_AGE_SEC:
            pass
        else:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, path)
    return best[1] if best else None


def already_acked(text: str, slug: str, stage: str) -> bool:
    if not text or not slug or not stage:
        return False
    tail = text[-TAIL_CHARS:] if len(text) > TAIL_CHARS else text
    if slug not in tail:
        return False
    return re.search(
        rf"DONE\s+{re.escape(stage)}|{re.escape(stage)}\s+\S*controller\.json",
        tail,
        re.IGNORECASE,
    ) is not None


USER_LEAVE_REASONS = frozenset(
    {
        "clear",
        "resume",
        "logout",
        "prompt_input_exit",
        "interrupt",
        "interrupted",
        "user_interrupt",
        "cancelled",
        "canceled",
    }
)


def user_is_leaving(payload: dict) -> bool:
    """True when the human is exiting / interrupting — do not fight Ctrl+C."""
    if _event(payload) in {"SessionEnd", "session_end"}:
        return True
    for key in ("reason", "source", "stop_reason", "end_reason"):
        val = str(payload.get(key) or "").strip().lower()
        if val in USER_LEAVE_REASONS:
            return True
    return False


def decide_stop(payload: dict) -> tuple[int, str]:
    if _disabled() or not isinstance(payload, dict):
        return 0, ""
    event = _event(payload)
    if event and event not in {"Stop", "stop"}:
        return 0, ""
    # Live rs-* is durable (run-controller). Blocking Stop here paints a red
    # "Stop hook error" and fights Ctrl+C / session exit. Wake is PostToolUse.
    if user_is_leaving(payload):
        return 0, ""

    tasks = supervisor_tasks(payload, inflight_only=True)

    if not is_pm_session(payload):
        return 0, ""

    cwd = _cwd(payload)
    path = pick_controller(cwd)
    if path is None:
        return 0, ""
    stage = read_stage(path)
    slug = path.parent.name
    text = last_assistant_text(payload)
    if already_acked(text, slug, stage):
        return 0, ""
    if stage == "running" and tasks:
        return 0, ""
    if stage == "running":
        return (
            2,
            f"lane pm_stop_sentinel: {slug} stage=running but no supervisor task. "
            f"Re-dispatch run-supervisor. Read {path}.",
        )
    if stage in TERMINAL:
        return (
            2,
            f"lane pm_stop_sentinel: {slug} stage={stage}. Silence protocol: "
            f"read {path} and act now (recover or merge). Do not idle.",
        )
    return 0, ""


def _poll_sec() -> float:
    raw = os.environ.get("LANE_PM_STOP_POLL", "").strip()
    try:
        return max(0.05, float(raw)) if raw else DEFAULT_POLL
    except ValueError:
        return DEFAULT_POLL


def _watch_sec() -> float:
    raw = os.environ.get("LANE_PM_STOP_WATCH_SEC", "").strip()
    try:
        return max(1.0, float(raw)) if raw else DEFAULT_WATCH_SEC
    except ValueError:
        return DEFAULT_WATCH_SEC


def decide_watch(payload: dict) -> tuple[Path, str] | None:
    """Return (cwd, slug) to watch, slug may be empty (newest interesting)."""
    if _disabled() or not isinstance(payload, dict):
        return None
    event = _event(payload)
    if event and event not in {"PostToolUse", "post_tool_use"}:
        return None
    if not is_supervisor_spawn(payload):
        return None
    return _cwd(payload), run_slug_from_payload(payload)


def watch_run(cwd: Path, slug: str, *, timeout_s: float, poll_s: float) -> tuple[int, str]:
    deadline = time.time() + timeout_s
    last = ""
    path = controller_path(cwd, slug) if slug else None
    while time.time() < deadline:
        if path is None or not path.is_file():
            found = pick_controller(cwd, slug=slug)
            if found is not None:
                path = found
        if path is not None and path.is_file():
            last = read_stage(path) or last
            if last in TERMINAL:
                return (
                    2,
                    f"lane pm_stop_sentinel: {path.parent.name} stage={last}. "
                    f"Silence protocol: read {path} and act now.",
                )
        time.sleep(poll_s)
    label = slug or (path.parent.name if path is not None else "run")
    where = str(path) if path is not None else str(cwd / ".agents" / "runs")
    return (
        2,
        f"lane pm_stop_sentinel: watch timeout on {label} (last stage={last or 'missing'}). "
        f"Read {where}.",
    )


def main() -> int:
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    event = _event(payload)
    if event in {"PostToolUse", "post_tool_use"}:
        spec = decide_watch(payload)
        if spec is None:
            return 0
        cwd, slug = spec
        code, err = watch_run(cwd, slug, timeout_s=_watch_sec(), poll_s=_poll_sec())
        if err:
            print(err, file=sys.stderr)
        return code
    code, err = decide_stop(payload)
    if err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

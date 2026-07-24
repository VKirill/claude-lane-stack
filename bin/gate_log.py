"""Best-effort append-only gate-event log for periodic review.

Every gate evaluation (owns-paths, validate, accept, verification) appends one
compact JSON line to a durable log so a weekly `gate-report` can surface
recurring blocks / false positives without walking every per-run receipt.

Writing NEVER fails the calling gate: any error is swallowed. The location
defaults to ``~/.agents/logs/gate-events.jsonl``; override with the
``CLAUDE_LANE_GATE_LOG`` env var (set it to ``off`` to disable entirely).
"""
from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_LOG_RELATIVE = Path(".agents") / "logs" / "gate-events.jsonl"
_MAX_LIST_ITEMS = 40
_MAX_DETAIL_CHARS = 300


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_log_path(explicit: str | os.PathLike | None = None) -> Path | None:
    """Return the gate-event log path, or None when logging is disabled."""
    if explicit is not None:
        return Path(str(explicit)).expanduser()
    override = os.environ.get("CLAUDE_LANE_GATE_LOG")
    if override is not None:
        if override.strip().lower() in {"", "off", "0", "false", "no"}:
            return None
        return Path(override).expanduser()
    return Path.home() / DEFAULT_LOG_RELATIVE


def _bounded_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out = [str(item) for item in value if str(item).strip()]
    return out[:_MAX_LIST_ITEMS]


def _bounded_detail(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:_MAX_DETAIL_CHARS]


def record_gate_event(
    gate: str,
    status: str,
    *,
    project: str | os.PathLike | None = None,
    run_slug: str | None = None,
    task_id: str | None = None,
    scope: str | None = None,
    violations: object = None,
    never_touch_hits: object = None,
    exit_code: int | None = None,
    detail: object = None,
    provider: str | None = None,
    model: str | None = None,
    log_path: str | os.PathLike | None = None,
) -> None:
    """Append one gate evaluation to the durable log. Never raises."""
    try:
        path = resolve_log_path(log_path)
        if path is None:
            return
        event: dict = {
            "v": SCHEMA_VERSION,
            "ts": _utc_now(),
            "gate": str(gate),
            "status": str(status),
        }
        if project is not None:
            event["project"] = str(project)
        if run_slug:
            event["run_slug"] = str(run_slug)
        if task_id:
            event["task_id"] = str(task_id)
        if scope:
            event["scope"] = str(scope)
        bounded_violations = _bounded_list(violations)
        if bounded_violations:
            event["violations"] = bounded_violations
        bounded_never = _bounded_list(never_touch_hits)
        if bounded_never:
            event["never_touch_hits"] = bounded_never
        if isinstance(exit_code, int) and not isinstance(exit_code, bool):
            event["exit_code"] = exit_code
        bounded_detail = _bounded_detail(detail)
        if bounded_detail is not None:
            event["detail"] = bounded_detail
        if provider:
            event["provider"] = str(provider)
        if model:
            event["model"] = str(model)

        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except Exception:
        # Observability must never break a gate.
        pass


def run_slug_from_run_dir(run_dir: str | os.PathLike | None) -> str | None:
    if not run_dir:
        return None
    name = Path(str(run_dir)).name
    return name or None

"""Keep the full text of every rewritten tool result so it can be recalled."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from winnow.config import Config


def key_for(session_id: str, tool_use_id: str, text: str) -> str:
    digest = hashlib.sha256()
    for part in (session_id, "\0", tool_use_id, "\0", text):
        digest.update(part.encode("utf-8", errors="replace"))
    return digest.hexdigest()[:12]


def store(cfg: Config, key: str, payload: dict[str, Any]) -> Path:
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.cache_dir / f"{key}.json"
    payload = {"key": key, "created": time.time(), **payload}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load(cfg: Config, key: str) -> dict[str, Any] | None:
    if not key.isalnum():
        return None
    path = cfg.cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def clean(cfg: Config, *, older_than_days: float = 30, max_mb: float = 200, dry_run: bool = False) -> dict[str, Any]:
    """Delete cache entries older than ``older_than_days``, then the oldest until under ``max_mb``."""
    entries: list[tuple[float, int, Path]] = []
    if cfg.cache_dir.is_dir():
        for path in cfg.cache_dir.glob("*.json"):
            try:
                stat = path.stat()
            except OSError:
                continue
            entries.append((stat.st_mtime, stat.st_size, path))
    entries.sort()  # oldest first
    now = time.time()
    cutoff = now - older_than_days * 86400
    doomed: list[Path] = [p for mtime, _, p in entries if mtime < cutoff]
    keep = [(m, s, p) for m, s, p in entries if m >= cutoff]
    total = sum(s for _, s, _ in keep)
    limit = max_mb * 1024 * 1024
    while keep and total > limit:
        _, size, path = keep.pop(0)
        doomed.append(path)
        total -= size
    freed = 0
    for path in doomed:
        try:
            freed += path.stat().st_size
            if not dry_run:
                path.unlink()
        except OSError:
            pass
    markers = cfg.home / "notified"
    stale_markers = 0
    if markers.is_dir():
        for marker in markers.iterdir():
            try:
                if marker.stat().st_mtime < now - 2 * 86400:
                    stale_markers += 1
                    if not dry_run:
                        marker.unlink()
            except OSError:
                pass
    return {
        "entries_before": len(entries),
        "deleted": len(doomed),
        "bytes_freed": freed,
        "entries_after": len(entries) - len(doomed),
        "bytes_after": total,
        "stale_session_markers_removed": stale_markers,
        "dry_run": dry_run,
    }


def slice_lines(text: str, start: int | None, end: int | None, line_offset: int = 1) -> str:
    """Return lines ``start``..``end`` (inclusive, in the numbering the stub used)."""
    lines = text.split("\n")
    first = 0 if start is None else max(0, start - line_offset)
    last = len(lines) if end is None else max(first, end - line_offset + 1)
    return "\n".join(lines[first:last])

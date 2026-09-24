#!/usr/bin/env python3
"""Classify Cursor beforeReadFile: packet/reread in code, Jev Choice for extras."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jev_decisions import JevCritiqueError, call_jev, choice, clip, jev_enabled

ALLOW = {"permission": "allow"}
SKIP_CONF = 0.55
_SECRET_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
}
_SECRET_SUFFIXES = (".pem", ".p12", ".key")
_SKIP_DIRS = {".git", ".gitnexus", ".agents", "node_modules"}
_JEV_QUESTIONS = {
    "need": {
        "type": "choice",
        "instructions": (
            "Must the writer Read `path` to implement this YAML task? "
            "Packet files are already allowed by code; this path is outside "
            "the packet. Prefer skip unless the file is a direct import, type, "
            "or callee of an owned/read_first file."
        ),
        "criteria": {
            "needed": (
                "Direct import, type, or callee of an owned or read_first file; "
                "the edit is wrong without it"
            ),
            "skip": (
                "Unrelated, already covered by the packet, tests, docs, "
                "or speculative browse"
            ),
        },
    }
}


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _norm(path: object) -> str:
    raw = str(path or "").replace("\\", "/").strip()
    while raw.startswith("./"):
        raw = raw[2:]
    return raw


def _rel(cwd: Path, file_path: str) -> str:
    resolved = Path(file_path).expanduser().resolve(strict=False)
    try:
        return resolved.relative_to(cwd.resolve(strict=False)).as_posix()
    except ValueError:
        return resolved.as_posix()


def _flag_off(name: str) -> bool:
    return (os.environ.get(name) or "1").strip().lower() in {"0", "off", "false", "no"}


def packet_paths(task: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for item in _as_list(task.get("read_first")):
        if isinstance(item, str):
            paths.add(_norm(item))
        elif isinstance(item, dict) and item.get("path"):
            paths.add(_norm(item.get("path")))
    for item in _as_list(task.get("owns_paths") or task.get("files")):
        if isinstance(item, str):
            if "*" in item or item.endswith("/"):
                continue
            paths.add(_norm(item))
        elif isinstance(item, dict) and item.get("path"):
            paths.add(_norm(item.get("path")))
    for item in _as_list(task.get("context_selectors")):
        if isinstance(item, dict) and item.get("path"):
            paths.add(_norm(item.get("path")))
    return {p for p in paths if p}


def in_packet(rel: str, paths: set[str]) -> bool:
    if rel in paths:
        return True
    return any(rel.endswith("/" + item) for item in paths if item)


def _never_touch(rel: str, task: dict[str, Any]) -> bool:
    import fnmatch

    for pattern in _as_list(task.get("never_touch")):
        if not isinstance(pattern, str) or not pattern:
            continue
        if fnmatch.fnmatchcase(rel, pattern) or fnmatch.fnmatchcase(Path(rel).name, pattern):
            return True
    return False


def _blocked_tree(rel: str, file_path: str, task_file: str) -> bool:
    resolved = Path(file_path).expanduser().resolve(strict=False)
    if task_file:
        try:
            if resolved == Path(task_file).expanduser().resolve(strict=False):
                return False
        except OSError:
            pass
    name = resolved.name
    if name in _SECRET_NAMES or name.endswith(_SECRET_SUFFIXES):
        return True
    parts = Path(rel).parts
    return any(part in _SKIP_DIRS for part in parts)


def _load_task(path: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _seen_store() -> Path | None:
    raw = (os.environ.get("LANE_PROMPT_FILE") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve(strict=False).parent / ".lane-read-seen.json"


def _load_seen() -> dict[str, str]:
    store = _seen_store()
    if store is None or not store.is_file():
        return {}
    try:
        data = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _save_seen(seen: dict[str, str]) -> None:
    store = _seen_store()
    if store is None:
        return
    try:
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(seen, sort_keys=True), encoding="utf-8")
    except OSError:
        return


def _deny(message: str) -> dict[str, str]:
    return {"permission": "deny", "user_message": message}


def _head(content: object) -> str:
    if not isinstance(content, str) or "\0" in content[:1024]:
        return ""
    lines = content.splitlines()[:40]
    return clip("\n".join(lines), 1500)


def _ask_need(rel: str, task: dict[str, Any], head: str) -> str:
    try:
        raw = call_jev(
            {
                "path": rel,
                "title": task.get("title"),
                "objective": clip(str(task.get("objective") or ""), 800),
                "interfaces": clip(str(task.get("interfaces") or ""), 1200),
                "read_first": [_norm(p) for p in _as_list(task.get("read_first")) if _norm(p)],
                "owns_paths": [
                    _norm(p) for p in _as_list(task.get("owns_paths") or task.get("files")) if _norm(p)
                ],
                "head": head,
            },
            _JEV_QUESTIONS,
            timeout=8,
            title="lane-stack read-jev",
        )
    except JevCritiqueError:
        return "needed"
    pick, conf = choice(raw.get("answers") or {}, "need", {"needed", "skip"}, "needed")
    if pick == "skip" and conf >= SKIP_CONF:
        return "skip"
    return "needed"


def decide_read(payload: dict[str, Any] | None, cwd: Path | None = None) -> dict[str, str]:
    """Return a beforeReadFile permission object. Fail-open on errors."""
    task_file = (os.environ.get("LANE_TASK_FILE") or "").strip()
    if not task_file:
        return dict(ALLOW)
    if not isinstance(payload, dict):
        return dict(ALLOW)
    file_path = payload.get("file_path")
    if not isinstance(file_path, str) or not file_path.strip():
        return dict(ALLOW)
    root = (cwd or Path.cwd()).expanduser().resolve(strict=False)
    rel = _rel(root, file_path)
    key = Path(file_path).expanduser().resolve(strict=False).as_posix()
    task = _load_task(task_file)
    if _never_touch(rel, task) or _blocked_tree(rel, file_path, task_file):
        return _deny(f"Skip read: {rel} is never_touch, secret, or outside lane trees")
    seen = _load_seen()
    if key in seen:
        return _deny(f"Already read this session: {rel}")
    packet = packet_paths(task)
    extra = not (in_packet(rel, packet) or key == Path(task_file).expanduser().resolve(strict=False).as_posix())
    if extra and not _flag_off("LANE_JEV_READ") and jev_enabled():
        verdict = _ask_need(rel, task, _head(payload.get("content")))
        if verdict == "skip":
            seen[key] = "skip"
            _save_seen(seen)
            return _deny(f"Skip extra read: {rel} is outside the execution packet")
    seen[key] = "allow"
    _save_seen(seen)
    return dict(ALLOW)

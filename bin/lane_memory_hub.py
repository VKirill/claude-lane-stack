"""Project memory on the BB hub, from any machine.

Lane Pilot keeps one project memory in its database on the hub. A PM chat on the Mac mini and a terminal
session on OVH both write and read it here, through `bb plugin rpc call lane-pilot session_memory_*`, instead of
each machine growing its own `.agents/memory` files. Without a connection a write waits in
`.cls/memory-outbox/` and goes out with the next successful call.

`LANE_MEMORY_HUB=off` keeps the old local corpus (tests, a machine without BB).
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

PLUGIN = "lane-pilot"
TIMEOUT = 25


def disabled() -> bool:
    return os.environ.get("LANE_MEMORY_HUB", "").strip().lower() in {"off", "0", "false", "no"}


def bb_cli() -> str | None:
    pinned = os.environ.get("BB_CLI", "").strip()
    if pinned and os.access(pinned, os.X_OK):
        return pinned
    for candidate in sorted(glob.glob(str(Path.home() / ".bb-machines/*/npm/lib/node_modules/bb-app/host-daemon/dist/bb"))):
        if os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("bb")


def _machine_file(name: str) -> str:
    for path in sorted(glob.glob(str(Path.home() / f".bb-machines/*/{name}"))):
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return ""


def _env() -> dict[str, str]:
    env = dict(os.environ)
    if not env.get("BB_SERVER_URL"):
        try:
            url = json.loads(_machine_file("config.json") or "{}").get("serverUrl")
        except json.JSONDecodeError:
            url = None
        if url:
            env["BB_SERVER_URL"] = url
    return env


def host_id() -> str:
    return os.environ.get("BB_HOST_ID", "").strip() or _machine_file("host-id")


def call(method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """One RPC to Lane Pilot on the hub; None when bb or the hub is out of reach."""
    if disabled():
        return None
    cli = bb_cli()
    if not cli:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(payload, handle)
        input_path = handle.name
    try:
        done = subprocess.run([cli, "plugin", "rpc", "call", PLUGIN, method, "--input-file", input_path, "--json"],
                              capture_output=True, text=True, timeout=TIMEOUT, env=_env(), check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        os.unlink(input_path)
    if done.returncode != 0:
        return None
    try:
        out = json.loads(done.stdout)
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) and out.get("ok") is not False else None


def _cls(repo: Path) -> Path:
    folder = Path(repo) / ".cls"
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / ".gitignore"
    if not marker.is_file():
        marker.write_text("*\n", encoding="utf-8")
    return folder


def project(repo: Path) -> str | None:
    """The hub project of this folder: a cached answer, the hub's lookup by folder and machine, and only then the
    BB session's own project — a session of one project may work in another project's folder."""
    env_project = os.environ.get("BB_PROJECT_ID", "").strip() or None
    root = str(Path(repo).resolve())
    cache = _cls(repo) / "hub-project.json"
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("path") == root and cached.get("projectId"):
            return str(cached["projectId"])
    except (OSError, json.JSONDecodeError):
        pass
    host = host_id()
    found = call("session_memory_project", {"hostId": host, "path": root}) if host else None
    project_id = (found or {}).get("projectId")
    if project_id:
        cache.write_text(json.dumps({"path": root, "projectId": project_id}), encoding="utf-8")
        return str(project_id)
    return env_project


def available(repo: Path) -> bool:
    return not disabled() and bb_cli() is not None and project(repo) is not None


def _outbox(repo: Path) -> Path:
    folder = _cls(repo) / "memory-outbox"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _queue(repo: Path, method: str, payload: dict[str, Any]) -> Path:
    path = _outbox(repo) / f"{time.time_ns()}-{method}.json"
    path.write_text(json.dumps({"method": method, "payload": payload}, ensure_ascii=False), encoding="utf-8")
    return path


def flush(repo: Path) -> int:
    """Sends queued writes and lessons; stops at the first failure so the order holds."""
    project_id = project(repo)
    if not project_id:
        return 0
    sent = 0
    for path in sorted(_outbox(repo).glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            continue
        payload = {**item["payload"], "projectId": project_id}
        if call(item["method"], payload) is None:
            break
        path.unlink(missing_ok=True)
        sent += 1
    return sent


def _send(repo: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    project_id = project(repo)
    if project_id:
        flush(repo)
        result = call(method, {**payload, "projectId": project_id})
        if result is not None:
            return result
    queued = _queue(repo, method, payload)
    return {"queued": str(queued)}


def write(repo: Path, *, kind: str, content: str, concepts: list[str], source: str = "") -> dict[str, Any]:
    return _send(repo, "session_memory_write", {"kind": kind, "content": content, "concepts": concepts[:24], "source": source[:300]})


def lesson(repo: Path, *, rule: str, evidence: str = "", scope: list[str] | None = None, audience: str = "both", always: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {"rule": rule, "audience": audience, "always": always}
    if evidence:
        payload["evidence"] = evidence[:1000]
    if scope:
        payload["scope"] = scope[:8]
    return _send(repo, "session_lesson", payload)


def search(repo: Path, query: str, limit: int = 8) -> list[dict[str, Any]] | None:
    project_id = project(repo)
    found = call("session_memory_search", {"projectId": project_id, "query": query, "limit": limit}) if project_id else None
    return None if found is None else list(found.get("records") or [])


def core(repo: Path) -> list[dict[str, Any]] | None:
    project_id = project(repo)
    found = call("session_memory_core", {"projectId": project_id}) if project_id else None
    return None if found is None else list(found.get("records") or [])

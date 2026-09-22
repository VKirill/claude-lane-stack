"""``winnow serve``: a resident sidecar so a hook costs a local round trip, not a Python start.

The function-hook module (``hooks/winnow.ts``) POSTs each event as JSON and reads
the answer from the response body: an empty 2xx means pass-through, a JSON 2xx
carries the rewrite (or the context to inject), an ``X-Winnow`` header summarises
a rewrite for the module's toast, and a connection failure means the module
passes the result through untouched. This server binds to loopback only, keeps
the SDK imported and the judge's HTTP client warm, and exits after a long idle
period.

``winnow serve --ensure`` is what the SessionStart hook runs: it checks the
health endpoint and spawns a detached server if nothing answers. It prints
nothing on stdout, because SessionStart stdout is injected into Claude's
context.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from winnow import __version__, log
from winnow.config import Config, default_home, env_file_path, load_env_file

DEFAULT_PORT = 47311
DEFAULT_IDLE_MINUTES = 45
EVENTS = {"/hook/post-tool-use": "post-tool-use", "/hook/user-prompt-submit": "user-prompt-submit"}


class State:
    """Per-server state: the cached runtime and the env-file watch."""

    def __init__(self, runtime: Any = None) -> None:
        self.started = time.time()
        self.last_request = time.time()
        self.requests = 0
        self.lock = threading.Lock()
        self.runtime = runtime
        self.pinned = runtime is not None  # tests inject a runtime and never rebuild it
        self.env_mtime: float | None = None
        self.loaded_keys: list[str] = []
        self.next_build_attempt = 0.0

    def _env_mtime(self) -> float | None:
        path = env_file_path()
        try:
            return path.stat().st_mtime if path.is_file() else None
        except OSError:
            return None

    def config(self) -> Config:
        """Re-read the env file when it changes, so a key or threshold edit takes effect without a restart."""
        mtime = self._env_mtime()
        if mtime != self.env_mtime:
            for key in self.loaded_keys:
                os.environ.pop(key, None)
            self.loaded_keys = load_env_file()
            self.env_mtime = mtime
            if not self.pinned:
                self.runtime = None
        return Config.from_env()

    def get_runtime(self, cfg: Config) -> tuple[Any, Exception | None]:
        if self.runtime is not None:
            return self.runtime, None
        if time.time() < self.next_build_attempt:
            return None, RuntimeError("judge unavailable (retry pending)")
        from winnow.hooks import Runtime

        try:
            self.runtime = Runtime.from_config(cfg)
            return self.runtime, None
        except Exception as exc:  # noqa: BLE001 - usually a missing key; retry later
            self.next_build_attempt = time.time() + 30
            log.log_error(cfg, "serve:runtime", exc)
            return None, exc


def handle(event: str, payload: dict[str, Any], state: State) -> dict[str, Any] | None:
    """The same logic as ``winnow hook``, with the runtime kept between calls."""
    return handle_with_meta(event, payload, state)[0]


def handle_with_meta(event: str, payload: dict[str, Any], state: State) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """``handle`` plus a summary of what was hidden, for the module's toast (the X-Winnow header)."""
    from winnow.cli import _notify_once
    from winnow.hooks import post_tool_use, user_prompt_submit, worth_judging

    with state.lock:
        state.last_request = time.time()
        state.requests += 1
        cfg = state.config()
    if event == "post-tool-use" and not worth_judging(payload, cfg):
        return None, {}
    runtime, error = state.get_runtime(cfg)
    if runtime is None:
        notice = _notify_once(
            cfg,
            str(payload.get("session_id") or ""),
            f"winnow is running but its judge could not start ({type(error).__name__}: {str(error)[:140]}). "
            "Tool results are passing through untouched. Run `winnow doctor` to fix it.",
        )
        return notice, {}
    meta: dict[str, Any] = {}
    try:
        if event == "post-tool-use":
            return post_tool_use(payload, runtime, meta), meta
        if event == "user-prompt-submit":
            return user_prompt_submit(payload, runtime), {}
    except Exception as exc:  # noqa: BLE001 - never break the tool call
        log.log_error(cfg, f"serve:{event}", exc)
    return None, {}


class Handler(BaseHTTPRequestHandler):
    server_version = f"winnow/{__version__}"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return  # quiet; the decision log is the record

    @property
    def state(self) -> State:
        return self.server.state  # type: ignore[attr-defined]

    def _send(
        self, status: int, body: bytes = b"", content_type: str = "application/json", headers: dict[str, str] | None = None
    ) -> None:
        self.send_response(status)
        if body:
            self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, status: int, obj: Any, headers: dict[str, str] | None = None) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), headers=headers)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path == "/health":
            st = self.state
            self._json(
                200,
                {
                    "ok": True,
                    "pid": os.getpid(),
                    "version": __version__,
                    "uptime_s": round(time.time() - st.started),
                    "requests": st.requests,
                    "judge_ready": st.runtime is not None and getattr(st.runtime, "judge", None) is not None,
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/shutdown":
            self._send(200)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        event = EVENTS.get(self.path)
        if event is None:
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            payload = json.loads(body.decode("utf-8")) if body else {}
            if not isinstance(payload, dict):
                raise ValueError("payload must be an object")
        except (ValueError, UnicodeDecodeError) as exc:
            self._json(400, {"error": f"bad request: {exc}"})
            return
        output, meta = handle_with_meta(event, payload, self.state)
        headers = {"X-Winnow": json.dumps(meta, separators=(",", ":"))} if meta else None
        if output is None:
            self._send(200, headers=headers)  # empty 2xx: pass-through
        else:
            self._json(200, output, headers=headers)


def make_server(port: int, runtime: Any = None) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.state = State(runtime)  # type: ignore[attr-defined]
    return server


def run_server(port: int = DEFAULT_PORT, idle_minutes: float = DEFAULT_IDLE_MINUTES) -> int:
    server = make_server(port)
    state: State = server.state  # type: ignore[attr-defined]
    cfg = state.config()
    log.log_event(cfg, {"event": "serve_start", "pid": os.getpid(), "port": port})

    def reaper() -> None:
        while True:
            time.sleep(30)
            if time.time() - state.last_request > idle_minutes * 60:
                log.log_event(cfg, {"event": "serve_idle_exit", "pid": os.getpid(), "requests": state.requests})
                server.shutdown()
                return

    threading.Thread(target=reaper, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


def health(port: int = DEFAULT_PORT, timeout: float = 0.5) -> dict[str, Any] | None:
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, ValueError):
        return None


def stop(port: int = DEFAULT_PORT) -> bool:
    try:
        with urlopen(Request(f"http://127.0.0.1:{port}/shutdown", data=b"", method="POST"), timeout=2):
            return True
    except (URLError, OSError):
        return False


def ensure(port: int = DEFAULT_PORT, wait_s: float = 8.0) -> bool:
    """Start a detached server if none answers. Silent on stdout by design.

    A server from an older plugin version is stopped and replaced, so a plugin
    update takes effect at the next session start.
    """
    info = health(port)
    if info is not None:
        if info.get("version") == __version__:
            return True
        stop(port)
        time.sleep(0.5)
    home = default_home()
    home.mkdir(parents=True, exist_ok=True)
    log_file = open(home / "serve.log", "ab")  # noqa: SIM115 - handed to the child
    cmd = [sys.executable, "-m", "winnow", "serve", "--port", str(port)]
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log_file, "stderr": log_file, "close_fds": True}
    if os.name == "nt":
        # CREATE_NO_WINDOW, not DETACHED_PROCESS: a venv's python.exe is a launcher that starts the
        # real interpreter as a child. With no console at all, Windows opens a new visible one for
        # that child (an empty terminal that kills the sidecar if closed). A hidden console is inherited.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kwargs)
    except OSError:
        return False
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if health(port) is not None:
            return True
        time.sleep(0.2)
    return False

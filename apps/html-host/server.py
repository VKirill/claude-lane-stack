#!/usr/bin/env python3
"""24h HTML preview host. One file or a small folder. Stdlib only."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote

ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
FILE_RE = re.compile(r"^(?!.*\.\.)[A-Za-z0-9_][A-Za-z0-9._/-]{0,120}$")
OK_EXT = {".html", ".css", ".js", ".svg", ".txt", ".json", ".ico"}
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
}
MAX_HTML = 1_000_000
MAX_FILES = 24
TTL = int(os.environ.get("HTML_HOST_TTL", "86400"))
DATA = Path(os.environ.get("HTML_HOST_DATA", os.path.expanduser("~/html-host-data")))
BASE = os.environ.get("HTML_HOST_BASE", "https://html.vechkasov.pro").rstrip("/")
BIND = os.environ.get("HTML_HOST_BIND", "127.0.0.1:8787")
TOKEN = os.environ.get("HTML_HOST_TOKEN", "")
UI_FILE = Path(__file__).with_name("ui.html")


def _now() -> int:
    return int(time.time())


def _expired(exp: object) -> bool:
    try:
        return int(exp) <= _now()
    except (TypeError, ValueError):
        return True


def gc() -> None:
    if not DATA.is_dir():
        return
    for meta in DATA.glob("*.json"):
        try:
            exp = json.loads(meta.read_text(encoding="utf-8")).get("exp", 0)
        except (OSError, json.JSONDecodeError):
            exp = 0
        if not _expired(exp):
            continue
        meta.with_suffix(".html").unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
    for meta in DATA.glob("*/meta.json"):
        try:
            exp = json.loads(meta.read_text(encoding="utf-8")).get("exp", 0)
        except (OSError, json.JSONDecodeError):
            exp = 0
        if _expired(exp):
            shutil.rmtree(meta.parent, ignore_errors=True)


def _new_id() -> str:
    import secrets

    DATA.mkdir(parents=True, exist_ok=True)
    for _ in range(8):
        nid = secrets.token_urlsafe(6)
        if not (DATA / f"{nid}.html").exists() and not (DATA / nid).exists():
            return nid
    raise RuntimeError("id collision")


def _norm_files(raw: dict) -> dict[str, str] | str:
    if not isinstance(raw, dict) or not raw:
        return "files object required"
    if len(raw) > MAX_FILES:
        return f"max {MAX_FILES} files"
    out: dict[str, str] = {}
    total = 0
    for name, body in raw.items():
        if not isinstance(name, str) or not isinstance(body, str):
            return "file names and bodies must be strings"
        name = name.lstrip("/")
        if not FILE_RE.match(name) or Path(name).suffix.lower() not in OK_EXT:
            return f"bad name: {name}"
        data = body.encode("utf-8")
        total += len(data)
        if total > MAX_HTML:
            return "html 20B–1MB"
        out[name] = body
    if "index.html" not in out:
        return "index.html required"
    if len(out["index.html"].strip()) < 20:
        return "html 20B–1MB"
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send(
        self,
        code: int,
        body: bytes,
        ctype: str,
        robots: str = "noindex",
        cache: str = "no-store",
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Robots-Tag", robots)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _auth_ok(self) -> bool:
        return (not TOKEN) or self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def _serve_page(self, nid: str, rel: str) -> None:
        folder = DATA / nid
        legacy = DATA / f"{nid}.html"
        legacy_meta = DATA / f"{nid}.json"
        if folder.is_dir() and (folder / "meta.json").is_file():
            try:
                exp = json.loads((folder / "meta.json").read_text(encoding="utf-8")).get("exp", 0)
            except json.JSONDecodeError:
                exp = 0
            if _expired(exp):
                gc()
                self._json(404, {"error": "not found or expired"})
                return
            if rel == "":
                self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
                return
            if not FILE_RE.match(rel):
                self._json(404, {"error": "not found"})
                return
            path = (folder / rel).resolve()
            if folder.resolve() not in path.parents and path != folder.resolve():
                self._json(404, {"error": "not found"})
                return
            if not path.is_file():
                self._json(404, {"error": "not found"})
                return
            self._send(200, path.read_bytes(), MIME.get(path.suffix.lower(), "application/octet-stream"))
            return
        if rel not in ("", "index.html"):
            self._json(404, {"error": "not found"})
            return
        if not legacy.is_file() or not legacy_meta.is_file():
            self._json(404, {"error": "not found or expired"})
            return
        try:
            exp = json.loads(legacy_meta.read_text(encoding="utf-8")).get("exp", 0)
        except json.JSONDecodeError:
            exp = 0
        if _expired(exp):
            gc()
            self._json(404, {"error": "not found or expired"})
            return
        if rel == "":
            self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
            return
        self._send(200, legacy.read_bytes(), "text/html; charset=utf-8")

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        gc()
        path = unquote(self.path.split("?", 1)[0])
        if path == "/health":
            self._json(200, {"ok": True, "ttl": TTL})
            return
        if path == "/":
            self._send(
                200,
                UI_FILE.read_bytes(),
                "text/html; charset=utf-8",
                robots="index, follow",
                cache="public, max-age=120",
            )
            return
        if path == "/robots.txt":
            body = (
                "User-agent: *\nAllow: /\nDisallow: /p/\nDisallow: /api/\n"
                f"Sitemap: {BASE}/sitemap.xml\n"
            ).encode()
            self._send(200, body, "text/plain; charset=utf-8", robots="index, follow")
            return
        if path == "/sitemap.xml":
            body = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{BASE}/</loc></url></urlset>\n"
            ).encode()
            self._send(200, body, "application/xml; charset=utf-8", robots="index, follow")
            return
        if path.startswith("/p/"):
            rest = path[3:].strip("/")
            if "/" not in rest:
                nid, rel = rest, ""
            else:
                nid, rel = rest.split("/", 1)
            if not ID_RE.match(nid):
                self._json(404, {"error": "not found"})
                return
            self._serve_page(nid, rel)
            return
        self._json(404, {"error": "not found"})

    def _live_dir(self, nid: str) -> Path | None:
        folder = DATA / nid
        meta = folder / "meta.json"
        if not meta.is_file():
            return None
        try:
            exp = json.loads(meta.read_text(encoding="utf-8")).get("exp", 0)
        except (OSError, json.JSONDecodeError):
            return None
        if _expired(exp):
            return None
        return folder

    def _write_bundle(self, files: dict[str, str], nid: str | None = None) -> tuple[str, int] | None:
        if nid is not None:
            folder = self._live_dir(nid)
            if folder is None:
                return None
            shutil.rmtree(folder)
        else:
            nid = _new_id()
        exp = _now() + TTL
        folder = DATA / nid
        folder.mkdir(parents=True)
        for name, body in files.items():
            dest = folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
        (folder / "meta.json").write_text(
            json.dumps({"exp": exp, "files": sorted(files), "kind": "bundle"}),
            encoding="utf-8",
        )
        return nid, exp

    def do_POST(self) -> None:
        gc()
        if self.path.split("?", 1)[0] != "/api/pages":
            self._json(404, {"error": "not found"})
            return
        if not self._auth_ok():
            self._json(401, {"error": "bad token"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_HTML + 8192:
            self._json(413, {"error": "too large"})
            return
        raw = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")
        files: dict[str, str] | None = None
        html = ""
        want_id: str | None = None
        if "application/json" in ctype:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(400, {"error": "bad json"})
                return
            raw_id = payload.get("id")
            if raw_id:
                if not isinstance(raw_id, str) or not ID_RE.match(raw_id):
                    self._json(400, {"error": "bad id"})
                    return
                want_id = raw_id
            if isinstance(payload.get("files"), dict):
                got = _norm_files(payload["files"])
                if isinstance(got, str):
                    self._json(400, {"error": got})
                    return
                files = got
            else:
                html = payload.get("html") or ""
        elif "application/x-www-form-urlencoded" in ctype:
            html = (parse_qs(raw.decode("utf-8")).get("html") or [""])[0]
        else:
            html = raw.decode("utf-8", errors="replace")
        if files is None:
            html = html.strip()
            if len(html) < 20 or len(html.encode("utf-8")) > MAX_HTML:
                self._json(400, {"error": "html 20B–1MB"})
                return
            files = {"index.html": html}
        wrote = self._write_bundle(files, want_id)
        if wrote is None:
            self._json(404, {"error": "not found or expired"})
            return
        nid, exp = wrote
        url = f"{BASE}/p/{nid}/"
        if "application/x-www-form-urlencoded" in ctype:
            self.send_response(303)
            self.send_header("Location", f"/p/{nid}/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._json(200 if want_id else 201, {
            "id": nid,
            "url": url,
            "expires_in": TTL,
            "exp": exp,
            "files": sorted(files),
            "updated": bool(want_id),
        })


def main() -> None:
    host, port_s = BIND.rsplit(":", 1)
    DATA.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer((host, int(port_s)), Handler).serve_forever()


if __name__ == "__main__":
    main()

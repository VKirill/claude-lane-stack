#!/usr/bin/env python3
"""Self-check: one-file + bundle + expire."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import server as host


def _req(method: str, url: str, data: bytes | None = None, ctype: str = "") -> tuple[int, bytes]:
    r = urllib.request.Request(url, data=data, method=method)
    if ctype:
        r.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(r, timeout=3) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="html-host-"))
    host.DATA = tmp
    host.TTL = 1
    host.BASE = "http://127.0.0.1:18787"
    host.TOKEN = ""
    httpd = host.ThreadingHTTPServer(("127.0.0.1", 18787), host.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.05)
    code, landing = _req("GET", "http://127.0.0.1:18787/")
    assert code == 200 and b"codemirror" in landing and b"Alt+S" in landing, (code, landing[:80])
    html = "<!DOCTYPE html><html><body><h1>hi</h1></body></html>"
    code, body = _req(
        "POST", "http://127.0.0.1:18787/api/pages",
        json.dumps({"html": html}).encode(), "application/json",
    )
    assert code == 201, (code, body)
    nid = json.loads(body)["id"]
    code, page = _req("GET", f"http://127.0.0.1:18787/p/{nid}/")
    assert code == 200 and b"codemirror" in page, (code, page[:80])
    code, page = _req("GET", f"http://127.0.0.1:18787/p/{nid}/index.html")
    assert code == 200 and b"<h1>hi</h1>" in page, (code, page)

    bundle = {
        "index.html": '<!DOCTYPE html><link rel="stylesheet" href="style.css"><h1 class="x">b</h1><script src="script.js"></script>',
        "style.css": ".x{color:#111}",
        "script.js": "window.__p=1",
        "_kit/proto.css": "body{margin:0}",
    }
    code, body = _req(
        "POST", "http://127.0.0.1:18787/api/pages",
        json.dumps({"files": bundle}).encode(), "application/json",
    )
    assert code == 201, (code, body)
    bid = json.loads(body)["id"]
    code, css = _req("GET", f"http://127.0.0.1:18787/p/{bid}/style.css")
    assert code == 200 and b".x{" in css, (code, css)
    code, kit = _req("GET", f"http://127.0.0.1:18787/p/{bid}/_kit/proto.css")
    assert code == 200 and b"margin" in kit, (code, kit)
    upd = "<!DOCTYPE html><html><body><h1>upd</h1></body></html>"
    code, body = _req(
        "POST", "http://127.0.0.1:18787/api/pages",
        json.dumps({"id": nid, "html": upd}).encode(), "application/json",
    )
    assert code == 200 and json.loads(body)["id"] == nid, (code, body)
    code, page = _req("GET", f"http://127.0.0.1:18787/p/{nid}/index.html")
    assert code == 200 and b"<h1>upd</h1>" in page, (code, page)
    code, miss = _req(
        "POST", "http://127.0.0.1:18787/api/pages",
        json.dumps({"id": "noSuchId1", "html": upd}).encode(), "application/json",
    )
    assert code == 404, (code, miss)
    time.sleep(1.1)
    host.gc()
    code, _ = _req("GET", f"http://127.0.0.1:18787/p/{nid}/")
    assert code == 404, code
    httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()

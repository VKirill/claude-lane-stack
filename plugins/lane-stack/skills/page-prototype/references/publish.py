#!/usr/bin/env python3
"""Publish a prototype to htmlshare.pro.

  --one     one HTML (kit inlined)
  --bundle  index.html + style.css + script.js + _kit/* as separate files
  default   bundle if the page folder has style.css/script.js or extra .css/.js;
            otherwise --one
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,16}$")
HOST_META = ".host.json"

KIT_HREFS = (
    "../../_kit/proto.css",
    "../../../_kit/proto.css",
    "../../_kit/proto.js",
    "../../../_kit/proto.js",
)


def kit_root(page: Path) -> Path:
    for up in (page.parent.parent.parent, page.parent.parent.parent.parent):
        if (up / "_kit").is_dir():
            return up / "_kit"
    return page.parent.parent.parent / "_kit"


def extra_assets(page: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(page.parent.iterdir()):
        if p == page or not p.is_file():
            continue
        if p.suffix.lower() in {".css", ".js"} and p.name != "INDEX.md":
            out.append(p)
    return out


def inline(html: str, kit: Path) -> str:
    if not kit.is_dir():
        return html
    css = (kit / "proto.css").read_text(encoding="utf-8") if (kit / "proto.css").is_file() else ""
    js = (kit / "proto.js").read_text(encoding="utf-8") if (kit / "proto.js").is_file() else ""
    for rel in KIT_HREFS:
        if rel.endswith(".css"):
            html = html.replace(
                f'<link rel="stylesheet" href="{rel}">',
                f"<style>\n{css}\n</style>",
            )
        else:
            html = html.replace(
                f'<script src="{rel}"></script>',
                f"<script>\n{js}\n</script>",
            )
    return html


def rewrite_kit_hrefs(html: str) -> str:
    for rel in KIT_HREFS:
        dest = "_kit/proto.css" if rel.endswith(".css") else "_kit/proto.js"
        html = html.replace(f'href="{rel}"', f'href="{dest}"')
        html = html.replace(f'src="{rel}"', f'src="{dest}"')
    return html


def collect_bundle(page: Path) -> dict[str, str]:
    kit = kit_root(page)
    html = rewrite_kit_hrefs(page.read_text(encoding="utf-8"))
    files = {"index.html": html}
    if (page.parent / "style.css").is_file() or "style.css" in html:
        sc = page.parent / "style.css"
        if sc.is_file():
            files["style.css"] = sc.read_text(encoding="utf-8")
    if (page.parent / "script.js").is_file() or "script.js" in html:
        sj = page.parent / "script.js"
        if sj.is_file():
            files["script.js"] = sj.read_text(encoding="utf-8")
    for extra in extra_assets(page):
        files[extra.name] = extra.read_text(encoding="utf-8")
    if kit.is_dir() and ("_kit/proto.css" in html or "_kit/proto.js" in html):
        if (kit / "proto.css").is_file():
            files["_kit/proto.css"] = (kit / "proto.css").read_text(encoding="utf-8")
        if (kit / "proto.js").is_file():
            files["_kit/proto.js"] = (kit / "proto.js").read_text(encoding="utf-8")
    return files


def read_id(page: Path) -> str | None:
    meta = page.parent / HOST_META
    if not meta.is_file():
        return None
    try:
        nid = json.loads(meta.read_text(encoding="utf-8")).get("id")
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(nid, str) and ID_RE.match(nid):
        return nid
    return None


def write_host(page: Path, data: dict) -> None:
    (page.parent / HOST_META).write_text(
        json.dumps({"id": data["id"], "url": data["url"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def post(payload: dict) -> tuple[int, dict]:
    base = os.environ.get("HTML_HOST_BASE", "https://htmlshare.pro").rstrip("/")
    req = urllib.request.Request(
        f"{base}/api/pages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    token = os.environ.get("HTML_HOST_TOKEN", "")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 404 and payload.get("id"):
            return 404, {}
        sys.stderr.write(body + "\n")
        raise SystemExit(e.code)


def publish(page: Path, payload: dict, force_new: bool) -> None:
    nid = None if force_new else read_id(page)
    if nid:
        payload = dict(payload, id=nid)
    code, data = post(payload)
    if nid and code == 404:
        payload.pop("id", None)
        code, data = post(payload)
    if "url" not in data:
        sys.stderr.write("bad host response\n")
        raise SystemExit(1)
    write_host(page, data)
    sys.stdout.write(json.dumps(data, ensure_ascii=False) + "\n")


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    mode = "auto"
    force_new = False
    while args and args[0] in {"--one", "--bundle", "--auto", "--new"}:
        flag = args.pop(0).lstrip("-")
        if flag == "new":
            force_new = True
        else:
            mode = flag
    if len(args) != 1:
        sys.exit("usage: publish.py [--one|--bundle|--new] path/to/index.html")
    page = Path(args[0]).resolve()
    if mode == "auto":
        mode = "bundle" if extra_assets(page) else "one"
    if mode == "one":
        publish(page, {"html": inline(page.read_text(encoding="utf-8"), kit_root(page))}, force_new)
        return
    publish(page, {"files": collect_bundle(page)}, force_new)


if __name__ == "__main__":
    main()

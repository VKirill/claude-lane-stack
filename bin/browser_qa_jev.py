#!/usr/bin/env python3
"""Jev browser-QA driver (jev-ultrafast pattern, our CDP, no harness).

Snapshot visible controls → one Jev request (operation + target) → click/type.
TYPE_TEXT uses a small OpenRouter chat model. DONE is checked against Expected.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from jev_decisions import JevCritiqueError, call_jev, openrouter_key

MAX_STEPS = 16
TEXT_MODEL = os.environ.get("JEV_TEXT_MODEL") or "inception/mercury-2.5"
DEVTOOLS_PORTS = (9333, 9222)

# MIT: trimmed from browser-use/jev-ultrafast snapshot.js (visible controls only).
SNAPSHOT_JS = r"""
(() => {
  if (!document.body) return null;
  const cache = window.__laneJev ||= {ids: new WeakMap(), nodes: new Map(), next: 1};
  const identity = (e) => {
    if (!cache.ids.has(e)) cache.ids.set(e, cache.next++);
    const id = cache.ids.get(e);
    cache.nodes.set(id, e);
    return id;
  };
  for (const [id, e] of cache.nodes) if (!e.isConnected) cache.nodes.delete(id);
  const safe = (e) => !['password', 'file', 'hidden'].includes(e.type);
  const visible = (e) => !e.closest('[aria-hidden="true"],[inert]') &&
    e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  const name = (e, seen = new Set()) => {
    if (!e || seen.has(e)) return '';
    seen.add(e);
    const referenced = (e.getAttribute('aria-labelledby') || '').split(/\s+/)
      .map((id) => name(document.getElementById(id), seen)).filter(Boolean).join(' ');
    return referenced || e.getAttribute('aria-label') ||
      [...(e.labels || [])].map((l) => name(l, seen)).filter(Boolean).join(' ') ||
      (['button', 'submit', 'reset'].includes(e.type) ? e.value : '') ||
      e.getAttribute('alt') ||
      (e.tagName === 'INPUT' ? '' : [...e.childNodes].map((n) =>
        n.nodeType === 3 ? n.textContent :
        n.nodeType === 1 && n.getAttribute('aria-hidden') !== 'true' ? name(n, seen) : ''
      ).join(' ').trim()) ||
      e.getAttribute('title') || e.getAttribute('placeholder') || '';
  };
  const roles = ['button', 'link', 'checkbox', 'radio', 'switch', 'tab',
    'menuitem', 'option', 'combobox', 'textbox', 'searchbox'];
  const selector = 'a[href],button,input,textarea,select,summary,[contenteditable="true"],' +
    roles.map((r) => '[role="' + r + '"]').join(',');
  const role = (e) => {
    const explicit = e.getAttribute('role');
    if (roles.includes(explicit)) return explicit;
    if (e.tagName === 'BUTTON' || e.tagName === 'SUMMARY') return 'button';
    if (e.tagName === 'A') return 'link';
    if (e.tagName === 'SELECT') return 'combobox';
    if (e.tagName === 'TEXTAREA' || e.isContentEditable) return 'textbox';
    if (e.tagName === 'INPUT') {
      if (['checkbox', 'radio'].includes(e.type)) return e.type;
      if (['button', 'submit', 'reset', 'image'].includes(e.type)) return 'button';
      if (e.type === 'search') return 'searchbox';
      if (['text', 'email', 'url', 'tel', 'number'].includes(e.type)) return 'textbox';
    }
    return null;
  };
  const actions = [];
  for (const e of document.querySelectorAll(selector)) {
    if (!safe(e) || !visible(e) || e.matches(':disabled')) continue;
    const r = e.getBoundingClientRect();
    const x = r.x + r.width / 2, y = r.y + r.height / 2, rname = role(e);
    if (!rname || r.width <= 0 || r.height <= 0 || x < 0 || y < 0 ||
        x >= innerWidth || y >= innerHeight) continue;
    const base = {node: identity(e), role: rname, label: name(e) || rname,
      rect: {x: r.x, y: r.y, w: r.width, h: r.height}};
    if (e.tagName === 'SELECT') {
      for (const o of e.options) {
        if (!o.selected && !o.disabled)
          actions.push({...base, kind: 'select', value: o.value,
            label: base.label + ' → ' + o.label});
      }
    } else {
      const editable = !e.readOnly && e.getAttribute('aria-readonly') !== 'true' &&
        (['textbox', 'searchbox'].includes(rname) ||
         (rname === 'combobox' && ['INPUT', 'TEXTAREA'].includes(e.tagName)));
      const value = 'value' in e ? String(e.value) : '';
      actions.push({...base, kind: editable ? 'fill' : 'click', value});
    }
  }
  const words = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const value = node.textContent.trim(), parent = node.parentElement;
    if (!value || !parent || parent.closest('script,style,noscript,template') || !visible(parent))
      continue;
    words.push(value);
  }
  actions.forEach((a, i) => a.id = 'e' + (i + 1));
  if (scrollY + innerHeight < document.documentElement.scrollHeight - 2)
    actions.push({id: 'scroll_down', kind: 'scroll', label: 'Scroll down', delta: 560});
  if (scrollY > 0)
    actions.push({id: 'scroll_up', kind: 'scroll', label: 'Scroll up', delta: -560});
  actions.push({id: 'wait', kind: 'wait', label: 'Wait for the page to update'});
  return {url: location.href, title: document.title, text: words.join('\n'),
    w: innerWidth, h: innerHeight, actions};
})()
"""


class CdpError(RuntimeError):
    """Chrome DevTools protocol failure."""


def _ws_connect(url: str, timeout: float = 10) -> socket.socket:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.sendall(req.encode())
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise CdpError("CDP websocket handshake closed")
        header += chunk
    if b"101" not in header.split(b"\r\n", 1)[0]:
        sock.close()
        raise CdpError(f"CDP handshake failed: {header[:120]!r}")
    return sock


def _ws_send(sock: socket.socket, payload: bytes) -> None:
    mask = os.urandom(4)
    header = bytearray([0x81])
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    header.extend(mask)
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _ws_recv(sock: socket.socket) -> bytes:
    def read(n: int) -> bytes:
        out = b""
        while len(out) < n:
            chunk = sock.recv(n - len(out))
            if not chunk:
                raise CdpError("CDP socket closed")
            out += chunk
        return out

    b1, b2 = read(2)
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack("!H", read(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read(8))[0]
    if b2 & 0x80:
        mask = read(4)
        data = read(length)
        return bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return read(length)


class Cdp:
    def __init__(self, ws_url: str) -> None:
        self.sock = _ws_connect(ws_url)
        self._n = 0

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        self._n += 1
        msg_id = self._n
        _ws_send(self.sock, json.dumps({"id": msg_id, "method": method, "params": params}).encode())
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            raw = _ws_recv(self.sock)
            try:
                msg = json.loads(raw.decode())
            except json.JSONDecodeError:
                continue
            if msg.get("id") != msg_id:
                continue
            if msg.get("error"):
                raise CdpError(f"{method}: {msg['error']}")
            result = msg.get("result")
            return result if isinstance(result, dict) else {}
        raise CdpError(f"{method}: timeout")

    def evaluate(self, expression: str) -> Any:
        result = self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        inner = result.get("result") if isinstance(result.get("result"), dict) else {}
        if result.get("exceptionDetails"):
            raise CdpError(str(result["exceptionDetails"])[:240])
        return inner.get("value")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def http_json(url: str, method: str = "GET") -> Any:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read().decode())


def discover_devtools(port: int | None = None) -> str | None:
    ports = (port,) if port else DEVTOOLS_PORTS
    for candidate in ports:
        try:
            http_json(f"http://127.0.0.1:{candidate}/json/version")
            return f"http://127.0.0.1:{candidate}"
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            continue
    return None


def open_tab(devtools: str, url: str) -> tuple[Cdp, str]:
    new_url = f"{devtools}/json/new?{urllib.parse.quote(url, safe=':/')}"
    try:
        created = http_json(new_url, method="PUT")
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        created = http_json(new_url)
    ws = created.get("webSocketDebuggerUrl") if isinstance(created, dict) else ""
    target = created.get("id") if isinstance(created, dict) else ""
    if not ws:
        raise CdpError("Chrome /json/new returned no websocket")
    cdp = Cdp(str(ws))
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    time.sleep(0.4)
    return cdp, str(target or "")


def close_tab(devtools: str, target_id: str) -> None:
    if not target_id:
        return
    try:
        urllib.request.urlopen(f"{devtools}/json/close/{target_id}", timeout=3).read()
    except (OSError, urllib.error.URLError, TimeoutError):
        return


def set_viewport(cdp: Cdp, width: int) -> None:
    height = 812 if width <= 430 else 900
    cdp.call(
        "Emulation.setDeviceMetricsOverride",
        width=width,
        height=height,
        deviceScaleFactor=1,
        mobile=width <= 430,
    )


def snapshot(cdp: Cdp) -> dict[str, Any]:
    raw = cdp.evaluate(SNAPSHOT_JS)
    if not isinstance(raw, dict):
        return {"url": "", "title": "", "text": "", "actions": []}
    actions = raw.get("actions") if isinstance(raw.get("actions"), list) else []
    raw["actions"] = [a for a in actions if isinstance(a, dict)]
    return raw


def screenshot_png(cdp: Cdp) -> bytes:
    result = cdp.call("Page.captureScreenshot", format="png")
    return base64.b64decode(str(result.get("data") or ""))


def expected_hit(page_text: str, expected: str) -> bool:
    needle = (expected or "").strip().lower()
    if not needle or needle in {"as written", "as written."}:
        return True
    hay = (page_text or "").lower()
    return needle in hay or all(word in hay for word in needle.split() if len(word) > 2)


def format_elements(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in actions:
        if item.get("kind") in {"scroll", "wait"}:
            continue
        rows.append(
            {
                "id": item.get("id"),
                "kind": item.get("kind"),
                "role": item.get("role"),
                "label": str(item.get("label") or ""),
                "value": str(item.get("value") or ""),
            }
        )
    return rows


def decide(
    page: dict[str, Any], goal: str, history: list[str], *, expected: str = ""
) -> dict[str, Any]:
    actions = page.get("actions") if isinstance(page.get("actions"), list) else []
    clicks = {str(a["id"]): str(a.get("label") or a["id"]) for a in actions if a.get("kind") == "click"}
    fills = {str(a["id"]): str(a.get("label") or a["id"]) for a in actions if a.get("kind") == "fill"}
    ops = {
        "CLICK": "Click a visible control that advances the case",
        "TYPE_TEXT": "Type into a visible field (a small model supplies the text)",
        "SCROLL_DOWN": "More of the page is below the fold",
        "WAIT": "The page is still loading",
        "DONE": "Visible page already matches the expected outcome",
        "BLOCKED": "Cannot proceed (missing control, overlay, auth, error)",
    }
    if not fills:
        del ops["TYPE_TEXT"]
    if not any(a.get("id") == "scroll_down" for a in actions):
        del ops["SCROLL_DOWN"]
    questions: dict[str, Any] = {
        "operation": {
            "type": "choice",
            "instructions": (
                "QA case. Pick the next browser operation. "
                "DONE only if the expected outcome is already visible."
            ),
            "criteria": ops,
        }
    }
    if clicks:
        questions["click_target"] = {
            "type": "choice",
            "instructions": "Which control to click if operation is CLICK.",
            "criteria": clicks,
        }
    if fills:
        questions["type_target"] = {
            "type": "choice",
            "instructions": "Which field to type into if operation is TYPE_TEXT.",
            "criteria": fills,
        }
    raw = call_jev(
        {
            "goal": goal,
            "expected": expected,
            "page": {
                "url": page.get("url"),
                "title": page.get("title"),
                "text": str(page.get("text") or ""),
            },
            "elements": format_elements(actions),
            "recent": history,
        },
        questions,
        title="lane-stack browser-qa-jev",
    )
    answers = raw.get("answers") if isinstance(raw.get("answers"), dict) else {}
    op = str((answers.get("operation") or {}).get("choice") or "WAIT")
    try:
        conf = float((answers.get("operation") or {}).get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    target = ""
    if op == "CLICK":
        target = str((answers.get("click_target") or {}).get("choice") or "")
    elif op == "TYPE_TEXT":
        target = str((answers.get("type_target") or {}).get("choice") or "")
    elif op == "SCROLL_DOWN":
        target = "scroll_down"
    elif op == "WAIT":
        target = "wait"
    return {"operation": op, "target": target, "confidence": conf, "raw": raw}


def field_text(goal: str, label: str, current: str) -> str:
    key = openrouter_key()
    if not key:
        raise JevCritiqueError("OPENROUTER_API_KEY missing for TYPE_TEXT")
    body = json.dumps(
        {
            "model": TEXT_MODEL,
            "max_tokens": 128,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": 'Return {"text":"..."} only. No passwords. Short field value.',
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"goal": goal, "field": label, "current": current},
                        ensure_ascii=False,
                    ),
                },
            ],
        }
    ).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "{}"
    parsed = json.loads(content)
    text = str(parsed.get("text") or "").strip()
    if not text or len(text) > 200:
        raise JevCritiqueError("text helper returned empty")
    return text


def act(cdp: Cdp, action: dict[str, Any], text: str | None = None) -> None:
    kind = str(action.get("kind") or "")
    if kind == "wait":
        time.sleep(0.25)
        return
    if kind == "scroll":
        delta = int(action.get("delta") or 560)
        cdp.evaluate(f"window.scrollBy(0, {delta})")
        time.sleep(0.15)
        return
    node = int(action.get("node") or 0)
    if kind == "fill" and text is not None:
        payload = json.dumps(text)
        cdp.evaluate(
            f"""(() => {{
              const e = window.__laneJev && window.__laneJev.nodes.get({node});
              if (!e) return false;
              e.focus();
              if ('value' in e) e.value = {payload};
              else e.innerText = {payload};
              e.dispatchEvent(new Event('input', {{bubbles: true}}));
              e.dispatchEvent(new Event('change', {{bubbles: true}}));
              return true;
            }})()"""
        )
        time.sleep(0.12)
        return
    cdp.evaluate(
        f"""(() => {{
          const e = window.__laneJev && window.__laneJev.nodes.get({node});
          if (!e) return false;
          e.click();
          return true;
        }})()"""
    )
    time.sleep(0.2)


def run_case(
    cdp: Cdp,
    *,
    goal: str,
    expected: str,
    max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    history: list[str] = []
    steps: list[dict[str, Any]] = []
    last_page: dict[str, Any] = {}
    for _ in range(max_steps):
        last_page = snapshot(cdp)
        try:
            decision = decide(last_page, goal, history, expected=expected)
        except JevCritiqueError as exc:
            return {
                "status": "blocked",
                "evidence": f"Jev unavailable: {exc}",
                "steps": steps,
                "page": last_page,
            }
        op = decision["operation"]
        target = decision["target"]
        steps.append({"operation": op, "target": target, "confidence": decision["confidence"]})
        if op == "DONE":
            ok = expected_hit(str(last_page.get("text") or ""), expected)
            return {
                "status": "passed" if ok else "failed",
                "evidence": (
                    "DONE and expected text visible"
                    if ok
                    else f"DONE but expected not visible: {expected[:120]}"
                ),
                "steps": steps,
                "page": last_page,
            }
        if op == "BLOCKED" or decision["confidence"] < 0.35:
            return {
                "status": "blocked",
                "evidence": f"{op} conf={decision['confidence']:.2f}",
                "steps": steps,
                "page": last_page,
            }
        action = next((a for a in last_page.get("actions") or [] if a.get("id") == target), None)
        if action is None and op == "CLICK":
            return {
                "status": "failed",
                "evidence": f"click target missing: {target}",
                "steps": steps,
                "page": last_page,
            }
        typed = None
        if op == "TYPE_TEXT" and action:
            try:
                typed = field_text(goal, str(action.get("label") or ""), str(action.get("value") or ""))
            except (JevCritiqueError, OSError, json.JSONDecodeError, urllib.error.URLError) as exc:
                return {
                    "status": "blocked",
                    "evidence": f"TYPE_TEXT helper: {exc}",
                    "steps": steps,
                    "page": last_page,
                }
        if action:
            act(cdp, action, typed)
        elif op == "SCROLL_DOWN":
            act(cdp, {"kind": "scroll", "delta": 560})
        elif op == "WAIT":
            act(cdp, {"kind": "wait"})
        history.append(f"{op} {action.get('label') if action else target} {typed or ''}".strip())
    return {
        "status": "blocked",
        "evidence": f"step budget {max_steps}",
        "steps": steps,
        "page": last_page,
    }

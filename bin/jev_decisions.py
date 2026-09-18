#!/usr/bin/env python3
"""Shared OpenRouter Decisions client for Jev (typesafe/jev-1.13)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

JEV_MODEL = "typesafe/jev-1.13"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


class JevCritiqueError(RuntimeError):
    """OpenRouter / Jev invoke or parse failure."""


def clip(text: str, limit: int) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    return raw[: limit - 16] + "\n…[truncated]"


def jev_enabled() -> bool:
    flag = (os.environ.get("LANE_JEV") or "1").strip().lower()
    if flag in {"0", "off", "false", "no"}:
        return False
    return bool(openrouter_key())


def openrouter_key() -> str:
    env = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if env:
        return env
    try:
        from usage_ledger import openrouter_api_key

        return (openrouter_api_key() or "").strip()
    except Exception:
        return ""


def noul(answers: dict[str, Any], key: str) -> float:
    raw = answers.get(key)
    if not isinstance(raw, dict):
        return 0.0
    try:
        return float(raw.get("noul") or 0)
    except (TypeError, ValueError):
        return 0.0


def choice(
    answers: dict[str, Any], key: str, allowed: set[str], default: str
) -> tuple[str, float]:
    raw = answers.get(key)
    if not isinstance(raw, dict):
        return default, 0.0
    picked = str(raw.get("choice") or default).strip().lower()
    if picked not in allowed:
        picked = default
    try:
        conf = float(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    return picked, conf


def call_jev(
    state: object,
    questions: dict[str, Any],
    *,
    timeout: int = 20,
    title: str = "lane-stack jev",
) -> dict[str, Any]:
    if not jev_enabled():
        raise JevCritiqueError("Jev disabled or OPENROUTER_API_KEY missing")
    key = openrouter_key()
    if not key:
        raise JevCritiqueError("OPENROUTER_API_KEY missing")
    body = json.dumps(
        {"model": JEV_MODEL, "state": state, "questions": questions}
    ).encode()
    req = urllib.request.Request(
        DECISIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/local/claude-lane-stack",
            "X-Title": title,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise JevCritiqueError(f"HTTP {exc.code}: {detail}") from exc
    except (OSError, json.JSONDecodeError, TimeoutError) as exc:
        raise JevCritiqueError(str(exc)) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
        raise JevCritiqueError("Jev response missing answers")
    return payload

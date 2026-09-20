#!/usr/bin/env python3
"""Shared Jev client: TypeSafe native API, else OpenRouter Decisions."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

JEV_MODEL = "typesafe/jev-1.13"
TYPESAFE_MODEL = os.environ.get("JEV_NATIVE_MODEL") or "jev-latest"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"


class JevCritiqueError(RuntimeError):
    """OpenRouter / TypeSafe / Jev invoke or parse failure."""


def clip(text: str, limit: int) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    return raw[: limit - 16] + "\n…[truncated]"


def jev_enabled() -> bool:
    flag = (os.environ.get("LANE_JEV") or "1").strip().lower()
    if flag in {"0", "off", "false", "no"}:
        return False
    return bool(typesafe_key() or openrouter_key())


def _key_from_env_file(path: Path, names: tuple[str, ...]) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        if key.strip() in names:
            return value.strip().strip('"').strip("'")
    return ""


def typesafe_key() -> str:
    env = (os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY") or "").strip()
    if env:
        return env
    raw = os.environ.get("TYPESAFE_API_KEY_FILE")
    if raw:
        path = Path(raw).expanduser()
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8").strip()
            except OSError:
                return ""
    secrets = Path.home() / "secrets"
    for name in ("typesafe.env", "jev.env"):
        found = _key_from_env_file(secrets / name, ("TYPESAFE_API_KEY", "JEV_API_KEY"))
        if found:
            return found
    return ""


def openrouter_key() -> str:
    env = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if env:
        return env
    found = _key_from_env_file(
        Path.home() / "secrets" / "openrouter.env", ("OPENROUTER_API_KEY",)
    )
    if found:
        return found
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


def score_value(
    answers: dict[str, Any], key: str, default: float = 0.0
) -> tuple[float, float]:
    raw = answers.get(key)
    if not isinstance(raw, dict):
        return default, 0.0
    try:
        value = float(raw.get("score") if raw.get("score") is not None else default)
    except (TypeError, ValueError):
        value = default
    try:
        conf = float(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    return value, conf


def call_jev(
    state: object,
    questions: dict[str, Any],
    *,
    timeout: int = 20,
    title: str = "lane-stack jev",
) -> dict[str, Any]:
    if not jev_enabled():
        raise JevCritiqueError("Jev disabled or API key missing")
    native = typesafe_key()
    if native:
        url = TYPESAFE_URL
        model = TYPESAFE_MODEL
        key = native
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    else:
        key = openrouter_key()
        if not key:
            raise JevCritiqueError("TYPESAFE_API_KEY or OPENROUTER_API_KEY missing")
        url = DECISIONS_URL
        model = JEV_MODEL
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/VKirill/claude-lane-stack",
            "X-Title": title,
        }
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
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

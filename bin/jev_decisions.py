#!/usr/bin/env python3
"""Shared Jev client: TypeSafe native API, else OpenRouter Decisions."""
from __future__ import annotations

import json
import os
import re
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


# Jev reads about 32k tokens of state plus the longest question and answers
# 400 max_tokens_exceeded past it. Mirrors fast-jev's estimateTokens: a word
# costs one token per six letters, a digit half, any other symbol nine tenths.
MAX_STATE_TOKENS = 28_000
_TOKEN_PIECES = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]")


def estimate_tokens(text: str) -> int:
    tokens = 0.0
    for piece in _TOKEN_PIECES.findall(text):
        if piece[0].isdigit():
            tokens += len(piece) / 2
        elif piece[0].isascii() and piece[0].isalpha():
            tokens += 1 + (len(piece) - 1) // 6
        else:
            tokens += 0.9
    return int(tokens + 0.999)


def bound_state(state: object, max_tokens: int = MAX_STATE_TOKENS) -> object:
    """Abridges the longest texts, head and tail kept, until the state fits Jev's window."""
    copy = json.loads(json.dumps(state))
    for _ in range(24):
        tokens = estimate_tokens(json.dumps(copy))
        if tokens <= max_tokens:
            break
        ratio = max(0.1, max_tokens / tokens * 0.95)
        if isinstance(copy, str):
            copy = _abridge(copy, ratio)
            continue
        longest: list[Any] = [None, None, -1]

        def visit(value: Any, holder: Any, key: Any) -> None:
            if isinstance(value, str):
                if holder is not None and len(value) > longest[2]:
                    longest[:] = [holder, key, len(value)]
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    visit(item, value, index)
            elif isinstance(value, dict):
                for name, item in value.items():
                    visit(item, value, name)

        visit(copy, None, None)
        if longest[0] is None:
            break
        longest[0][longest[1]] = _abridge(longest[0][longest[1]], ratio)
    return copy


def _abridge(text: str, ratio: float) -> str:
    keep = max(400, int(len(text) * ratio))
    if keep >= len(text):
        return text
    head = int(keep * 0.7)
    return f"{text[:head]}\n[… {len(text) - keep} chars omitted …]\n{text[len(text) - (keep - head):]}"


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
    body = json.dumps({"model": model, "state": bound_state(state), "questions": questions}).encode()
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

#!/usr/bin/env python3
"""Daily token/cost totals per CLI. SQLite under ~/.agents/usage/."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TICKS_PER_USD = 10_000_000_000
CACHE_KEYS = (
    "cache_read_input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
)
OUTPUT_KEYS = (
    "output_tokens",
    "reasoning_tokens",
    "reasoning_output_tokens",
    "thinking_tokens",
)
INPUT_ALIASES = ("input_tokens", "inputTokens", "input", "prompt_tokens", "promptTokens")
OUTPUT_ALIASES = (
    "output_tokens",
    "outputTokens",
    "output",
    "completion_tokens",
    "completionTokens",
)
REASONING_ALIASES = (
    "reasoning_tokens",
    "reasoningTokens",
    "reasoning",
    "reasoning_output_tokens",
    "reasoningOutputTokens",
    "thinking_tokens",
    "thinkingTokens",
)
CACHE_READ_ALIASES = (
    "cache_read_input_tokens",
    "cacheReadInputTokens",
    "cached_input_tokens",
    "cachedInputTokens",
    "cacheReadTokens",
    "cache_read_tokens",
)
CACHE_WRITE_ALIASES = (
    "cache_creation_input_tokens",
    "cacheCreationInputTokens",
    "cache_write_input_tokens",
    "cacheWriteInputTokens",
    "cacheWriteTokens",
    "cache_write_tokens",
)
TOTAL_ALIASES = ("total_tokens", "totalTokens", "total")
COST_ALIASES = ("total_cost_usd", "costUSD", "cost")
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_TTL_SEC = 24 * 3600
_SLUG_STRIP = re.compile(r"-(?:fast|preview|thinking|xhigh|high|medium|low)$")
_DATE_SUFFIX = re.compile(r"-\d{8}$")


def db_path() -> Path:
    raw = os.environ.get("AGENTS_USAGE_DB")
    if raw:
        return Path(raw)
    return Path.home() / ".agents" / "usage" / "usage.sqlite"


def prices_path() -> Path:
    raw = os.environ.get("AGENTS_USAGE_PRICES")
    if raw:
        return Path(raw)
    return db_path().with_name("openrouter-models.json")


def prices_table_path(dest: Path | None = None) -> Path:
    raw = os.environ.get("AGENTS_USAGE_PRICES_TABLE")
    if raw:
        return Path(raw)
    return (dest or prices_path()).with_name("openrouter-prices.tsv")


def openrouter_key_path() -> Path:
    raw = os.environ.get("OPENROUTER_API_KEY_FILE")
    if raw:
        return Path(raw)
    return db_path().with_name("openrouter.key")


def openrouter_api_key() -> str:
    env = os.environ.get("OPENROUTER_API_KEY") or ""
    if env.strip():
        return env.strip()
    path = openrouter_key_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def model_slug(name: str) -> str:
    slug = str(name or "").strip().lower().split("/")[-1]
    slug = slug.split(":")[0].lstrip("~")
    slug = re.sub(r"^cursor-", "", slug)
    slug = _DATE_SUFFIX.sub("", slug)
    while True:
        nxt = _SLUG_STRIP.sub("", slug)
        if nxt == slug:
            break
        slug = nxt
    return slug.replace("-4-5", "-4.5").replace("-3-5", "-3.5")


def _parse_rate(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def match_openrouter_model(model: str, catalog: list[dict]) -> dict | None:
    slug = model_slug(model)
    if not slug:
        return None
    exact: list[dict] = []
    fuzzy: list[dict] = []
    for item in catalog:
        ident = str(item.get("id") or "")
        if not ident or ident.startswith("~") or ":" in ident:
            continue
        last = model_slug(ident)
        if last == slug:
            exact.append(item)
        elif slug in last or last in slug:
            fuzzy.append(item)
    if exact:
        exact.sort(key=lambda item: len(str(item.get("id") or "")))
        return exact[0]
    if len(fuzzy) == 1:
        return fuzzy[0]
    return None


def estimate_api_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_tokens: int,
    catalog: list[dict] | None = None,
) -> tuple[float | None, str]:
    item = match_openrouter_model(model, catalog or [])
    if not item:
        return None, ""
    pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
    prompt = _parse_rate(pricing.get("prompt"))
    completion = _parse_rate(pricing.get("completion"))
    cache_read = _parse_rate(pricing.get("input_cache_read")) or prompt
    usd = (
        input_tokens * prompt
        + output_tokens * completion
        + cache_tokens * cache_read
    )
    return usd, str(item.get("id") or "")


def refresh_openrouter_prices(*, dest: Path | None = None, key: str | None = None) -> list[dict]:
    token = key if key is not None else openrouter_api_key()
    headers = {"User-Agent": "lane-usage-ledger"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(OPENROUTER_MODELS_URL, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("openrouter models response missing data")
    path = dest or prices_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fetched_at": time.time(), "models": models}, separators=(",", ":")),
        encoding="utf-8",
    )
    write_openrouter_prices_table(models, dest=prices_table_path(path))
    return models


def write_openrouter_prices_table(models: list[dict], dest: Path | None = None) -> Path:
    path = dest or prices_table_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "id\tname\tprompt\tcompletion\tcache_read\tcache_write\t"
        "prompt_1m\tcompletion_1m\tcache_read_1m\tcache_write_1m"
    ]
    for item in models:
        ident = str(item.get("id") or "")
        if not ident:
            continue
        pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
        prompt = pricing.get("prompt")
        completion = pricing.get("completion")
        cache_read = pricing.get("input_cache_read")
        cache_write = pricing.get("input_cache_write")
        name = str(item.get("name") or "").replace("\t", " ").replace("\n", " ")
        lines.append(
            f"{ident}\t{name}\t{prompt or ''}\t{completion or ''}\t"
            f"{cache_read or ''}\t{cache_write or ''}\t"
            f"{_parse_rate(prompt) * 1_000_000:.6f}\t"
            f"{_parse_rate(completion) * 1_000_000:.6f}\t"
            f"{_parse_rate(cache_read) * 1_000_000:.6f}\t"
            f"{_parse_rate(cache_write) * 1_000_000:.6f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_openrouter_prices(
    *, dest: Path | None = None, refresh: bool = False, cached_only: bool = False
) -> list[dict]:
    path = dest or prices_path()
    if path.is_file() and not refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = {}
        models = cached.get("models") if isinstance(cached, dict) else None
        fetched = float(cached.get("fetched_at") or 0) if isinstance(cached, dict) else 0
        if isinstance(models, list) and (
            cached_only or time.time() - fetched < OPENROUTER_TTL_SEC
        ):
            return models
    if cached_only:
        return []
    try:
        return refresh_openrouter_prices(dest=path)
    except (OSError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError):
        if path.is_file():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                models = cached.get("models") if isinstance(cached, dict) else None
                if isinstance(models, list):
                    return models
            except json.JSONDecodeError:
                pass
        return []


def catalog_for_db(path: Path | None = None) -> list[dict]:
    dest = Path(os.environ["AGENTS_USAGE_PRICES"]) if os.environ.get("AGENTS_USAGE_PRICES") else None
    if dest is None and path is not None:
        dest = Path(path).with_name("openrouter-models.json")
    return load_openrouter_prices(dest=dest, cached_only=True)


def _as_int(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _first_int(data: dict, keys: tuple[str, ...]) -> int:
    for key in keys:
        value = _as_int(data.get(key))
        if value:
            return value
    return 0


def _as_cost(value: object) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def normalize_usage(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    tokens = raw["tokens"] if isinstance(raw.get("tokens"), dict) else raw
    cache = tokens["cache"] if isinstance(tokens.get("cache"), dict) else {}
    mapped = {
        "input_tokens": _first_int(tokens, INPUT_ALIASES),
        "output_tokens": _first_int(tokens, OUTPUT_ALIASES),
        "reasoning_tokens": _first_int(tokens, REASONING_ALIASES),
        "cache_read_input_tokens": _first_int(tokens, CACHE_READ_ALIASES) or _as_int(cache.get("read")),
        "cache_creation_input_tokens": _first_int(tokens, CACHE_WRITE_ALIASES)
        or _as_int(cache.get("write")),
        "total_tokens": _first_int(tokens, TOTAL_ALIASES),
    }
    mapped = {key: value for key, value in mapped.items() if value}
    return mapped or None


_CACHE_PEAK_KEYS = frozenset(
    {
        "cache_read_input_tokens",
        "cached_input_tokens",
        "cache_read_tokens",
    }
)


def merge_usage(left: dict | None, right: dict | None) -> dict | None:
    if not left:
        return dict(right) if right else None
    if not right:
        return dict(left)
    merged = dict(left)
    for key, value in right.items():
        current = _as_int(merged.get(key))
        incoming = _as_int(value)
        # ponytail: cache_read is the same prefix re-sent every turn; peak, do not sum
        merged[key] = max(current, incoming) if key in _CACHE_PEAK_KEYS else current + incoming
    return merged


def is_subagent_transcript(transcript: Path) -> bool:
    return "subagents" in Path(transcript).parts


def transcript_cursor_key(transcript: Path, session_id: str = "") -> str:
    dest = Path(transcript)
    if is_subagent_transcript(dest):
        return f"sub:{dest.stem}"
    return session_id or str(dest)


def _line_usage(payload: dict, *, allow_sidechain: bool = False) -> dict | None:
    if payload.get("isSidechain") and not allow_sidechain:
        return None
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    return normalize_usage(message.get("usage")) or normalize_usage(payload.get("usage"))


def _working_set(usage: dict) -> int:
    return _as_int(usage.get("cache_read_input_tokens")) + _as_int(
        usage.get("cache_creation_input_tokens")
    )


def usage_from_event(payload: object) -> tuple[dict | None, float]:
    if not isinstance(payload, dict):
        return None, 0.0
    blobs: list[object] = []
    if isinstance(payload.get("usage"), dict):
        blobs.append(payload["usage"])
    part = payload["part"] if isinstance(payload.get("part"), dict) else {}
    if isinstance(part.get("usage"), dict):
        blobs.append(part["usage"])
    if isinstance(part.get("tokens"), dict):
        blobs.append({"tokens": part["tokens"]})
    if isinstance(payload.get("tokens"), dict) and payload.get("type") in {
        "step_finish",
        "step-finish",
        "finish",
    }:
        blobs.append({"tokens": payload["tokens"]})
    merged = None
    for blob in blobs:
        merged = merge_usage(merged, normalize_usage(blob))
    cost = 0.0
    for source in (payload, part, payload.get("usage") if isinstance(payload.get("usage"), dict) else {}):
        if not isinstance(source, dict):
            continue
        for key in COST_ALIASES:
            cost += _as_cost(source.get(key))
    return merged, cost


def usage_from_stdout(text: str) -> tuple[dict | None, float]:
    """Walk JSON / NDJSON / JSON arrays for usage + cost (agy/qwen/kimi/opencode/codex)."""
    merged = None
    cost = 0.0
    raw = (text or "").strip()
    if not raw:
        return None, 0.0
    blobs: list[object] = []
    if raw[0] in "{[":
        try:
            blobs.append(json.loads(raw))
        except json.JSONDecodeError:
            blobs = []
    if not blobs:
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                blobs.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def walk(obj: object) -> None:
        nonlocal merged, cost
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        if not isinstance(obj, dict):
            return
        chunk, part_cost = usage_from_event(obj)
        merged = merge_usage(merged, chunk)
        cost += part_cost
        result = obj.get("result")
        if isinstance(result, dict):
            walk(result)
        elif isinstance(result, list):
            walk(result)

    for blob in blobs:
        walk(blob)
    return merged, cost


def usage_from_opencode_export(session_id: str, *, timeout: int = 20) -> tuple[dict | None, float]:
    if not session_id:
        return None, 0.0
    try:
        result = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, 0.0
    if result.returncode != 0 or not result.stdout.strip():
        return None, 0.0
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, 0.0
    merged = None
    cost = 0.0
    messages = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(messages, list):
        return None, 0.0
    for message in messages:
        if not isinstance(message, dict):
            continue
        for part in message.get("parts") or []:
            if not isinstance(part, dict):
                continue
            chunk, part_cost = usage_from_event({"part": part})
            merged = merge_usage(merged, chunk)
            cost += part_cost
    return merged, cost


def tokens_from_usage(usage: object) -> tuple[int, int, int, int]:
    data = normalize_usage(usage) or (usage if isinstance(usage, dict) else {})
    input_tokens = _as_int(data.get("input_tokens"))
    output_tokens = sum(_as_int(data.get(key)) for key in OUTPUT_KEYS)
    cache_tokens = sum(_as_int(data.get(key)) for key in CACHE_KEYS)
    total = _as_int(data.get("total_tokens"))
    if total <= 0:
        total = input_tokens + output_tokens + cache_tokens
    return input_tokens, output_tokens, cache_tokens, total


def cost_from_receipt(receipt: dict) -> float:
    cost = receipt.get("total_cost_usd")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool):
        return float(cost)
    ticks = receipt.get("total_cost_usd_ticks")
    if isinstance(ticks, (int, float)) and not isinstance(ticks, bool):
        return float(ticks) / TICKS_PER_USD
    return 0.0


def day_from_receipt(receipt: dict) -> str:
    for key in ("finished_at", "started_at"):
        value = receipt.get(key)
        if isinstance(value, str) and len(value) >= 10 and value[4] == "-":
            return value[:10]
    return datetime.now(timezone.utc).date().isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    dest = path or db_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(dest, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_daily (
            day TEXT NOT NULL,
            cli TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            api_usd REAL NOT NULL DEFAULT 0,
            calls INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (day, cli, model)
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(usage_daily)")}
    if "api_usd" not in cols:
        conn.execute(
            "ALTER TABLE usage_daily ADD COLUMN api_usd REAL NOT NULL DEFAULT 0"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingest_cursor (
            source TEXT PRIMARY KEY,
            last_line INTEGER NOT NULL DEFAULT 0,
            cache_peak INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cursor_cols = {row[1] for row in conn.execute("PRAGMA table_info(ingest_cursor)")}
    if "cache_peak" not in cursor_cols:
        conn.execute(
            "ALTER TABLE ingest_cursor ADD COLUMN cache_peak INTEGER NOT NULL DEFAULT 0"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS critique_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            day TEXT NOT NULL,
            project TEXT NOT NULL DEFAULT '',
            run TEXT NOT NULL DEFAULT '',
            event TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '',
            llm_verdict TEXT NOT NULL DEFAULT '',
            errors INTEGER NOT NULL DEFAULT 0,
            warns INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return conn


_ADVICE = frozenset({"revise", "revise_required"})


def run_identity(run_dir: Path) -> tuple[str, str]:
    dest = run_dir.expanduser().resolve()
    run = dest.name
    if dest.parent.name == "runs" and dest.parent.parent.name == ".agents":
        return dest.parent.parent.parent.name, run
    return dest.parent.name, run


def record_critique_event(
    *,
    event: str,
    project: str = "",
    run: str = "",
    mode: str = "",
    provider: str = "",
    model: str = "",
    decision: str = "",
    llm_verdict: str = "",
    errors: int = 0,
    warns: int = 0,
    path: Path | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO critique_events (
                ts, day, project, run, event, mode, provider, model,
                decision, llm_verdict, errors, warns
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now.isoformat(),
                now.date().isoformat(),
                project,
                run,
                event,
                mode,
                provider,
                model,
                decision,
                llm_verdict or "",
                errors,
                warns,
            ),
        )


def record_critique_result(
    run_dir: Path,
    result: dict,
    *,
    mode: str = "",
    path: Path | None = None,
) -> None:
    project, run = run_identity(run_dir)
    llm = result.get("llm_pass") if isinstance(result.get("llm_pass"), dict) else {}
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    record_critique_event(
        event="critique",
        project=project,
        run=run,
        mode=mode,
        provider=str(llm.get("provider") or ""),
        model=str(llm.get("model") or ""),
        decision=str(result.get("decision") or ""),
        llm_verdict=str(llm.get("verdict") or ""),
        errors=int(summary.get("errors") or 0),
        warns=int(summary.get("warnings") or 0),
        path=path,
    )


def record_critique_dispatch(run_dir: Path, *, path: Path | None = None) -> None:
    project, run = run_identity(run_dir)
    decision = ""
    llm_verdict = ""
    mode = ""
    artifact = run_dir / "artifacts" / "critique.json"
    if artifact.is_file():
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            decision = str(data.get("decision") or "")
            llm = data.get("llm_pass") if isinstance(data.get("llm_pass"), dict) else {}
            llm_verdict = str(llm.get("verdict") or "")
    record_critique_event(
        event="dispatch",
        project=project,
        run=run,
        mode=mode,
        decision=decision,
        llm_verdict=llm_verdict,
        path=path,
    )


def critique_follow_stats(path: Path | None = None) -> dict[str, int]:
    with connect(path) as conn:
        rows = list(
            conn.execute(
                "SELECT project, run, event, decision, llm_verdict "
                "FROM critique_events ORDER BY id"
            )
        )
    advised = followed = ignored = 0
    last_advice: dict[tuple[str, str], bool] = {}
    for project, run, event, decision, llm_verdict in rows:
        key = (str(project), str(run))
        advice = decision in _ADVICE or llm_verdict in _ADVICE
        if event == "critique":
            if advice:
                advised += 1
                last_advice[key] = True
            elif decision == "ship" and last_advice.get(key):
                followed += 1
                last_advice[key] = False
        elif event == "dispatch" and last_advice.get(key):
            ignored += 1
            last_advice[key] = False
    return {
        "advised": advised,
        "followed": followed,
        "ignored": ignored,
        "open": sum(1 for flag in last_advice.values() if flag),
    }


def record_usage(
    *,
    day: str,
    cli: str,
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_tokens: int = 0,
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    api_usd: float | None = None,
    path: Path | None = None,
) -> None:
    total = total_tokens or (input_tokens + output_tokens + cache_tokens)
    if api_usd is None:
        estimate, _matched = estimate_api_usd(
            model, input_tokens, output_tokens, cache_tokens, catalog_for_db(path)
        )
        api_usd = estimate or 0.0
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO usage_daily (
                day, cli, model, input_tokens, output_tokens, cache_tokens,
                total_tokens, cost_usd, api_usd, calls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(day, cli, model) DO UPDATE SET
                input_tokens = input_tokens + excluded.input_tokens,
                output_tokens = output_tokens + excluded.output_tokens,
                cache_tokens = cache_tokens + excluded.cache_tokens,
                total_tokens = total_tokens + excluded.total_tokens,
                cost_usd = cost_usd + excluded.cost_usd,
                api_usd = api_usd + excluded.api_usd,
                calls = calls + 1
            """,
            (
                day,
                cli,
                model,
                input_tokens,
                output_tokens,
                cache_tokens,
                total,
                cost_usd,
                api_usd,
            ),
        )


def event_day(payload: dict) -> str:
    ts = payload.get("timestamp")
    if isinstance(ts, str) and len(ts) >= 10 and ts[4] == "-":
        return ts[:10]
    return ""


def default_transcript_root() -> Path:
    return Path.home() / ".claude" / "projects"


def default_receipt_roots() -> list[Path]:
    home = Path.home()
    return [home / "apps", home / "sites", home / "tools"]


def iter_claude_transcripts(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [path for path in root.rglob("*.jsonl") if path.name != "history.jsonl"]


def iter_parent_transcripts(root: Path) -> list[Path]:
    return iter_claude_transcripts(root)


def iter_runtime_receipts(roots: list[Path]) -> list[dict]:
    receipts: list[dict] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            paths = list(root.rglob("runtime.json"))
        except OSError:
            continue
        for dest in paths:
            if ".agents" not in dest.parts:
                continue
            try:
                data = json.loads(dest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and data.get("usage"):
                receipts.append(data)
    return receipts


def _rebuild_transcript_day(transcript: Path, day: str, *, path: Path | None = None) -> bool:
    by_model: dict[str, dict[str, int]] = {}
    all_peak = 0
    lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    allow_sidechain = is_subagent_transcript(transcript)
    source = transcript_cursor_key(transcript, transcript.stem)
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        usage = _line_usage(payload, allow_sidechain=allow_sidechain)
        if not usage:
            continue
        working = _working_set(usage)
        all_peak = max(all_peak, working)
        if not allow_sidechain:
            sid = payload.get("sessionId") or payload.get("session_id")
            if isinstance(sid, str) and sid:
                source = sid
        if event_day(payload) != day:
            continue
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        model = message.get("model") if isinstance(message.get("model"), str) else ""
        added_in, added_out, _cache, _total = tokens_from_usage(usage)
        rec = by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "cache_peak": 0})
        rec["input_tokens"] += added_in
        rec["output_tokens"] += added_out
        rec["cache_peak"] = max(rec["cache_peak"], working)
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO ingest_cursor (source, last_line, cache_peak) VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_line = excluded.last_line,
                cache_peak = excluded.cache_peak
            """,
            (source, len(lines), all_peak),
        )
    if not by_model:
        return False
    for model, rec in by_model.items():
        record_usage(
            day=day,
            cli="claude",
            model=model,
            input_tokens=rec["input_tokens"],
            output_tokens=rec["output_tokens"],
            cache_tokens=rec["cache_peak"],
            total_tokens=rec["input_tokens"] + rec["output_tokens"] + rec["cache_peak"],
            path=path,
        )
    return True


def rebuild_day(
    day: str,
    *,
    path: Path | None = None,
    transcript_root: Path | None = None,
    receipt_roots: list[Path] | None = None,
) -> dict[str, int]:
    keep: list[tuple] = []
    with connect(path) as conn:
        keep = [
            tuple(row)
            for row in conn.execute(
                "SELECT day, cli, model, input_tokens, output_tokens, cache_tokens, "
                "total_tokens, cost_usd, api_usd, calls FROM usage_daily "
                "WHERE day = ? AND cli NOT IN ('claude', 'opencode')",
                (day,),
            )
        ]
        conn.execute("DELETE FROM usage_daily WHERE day = ?", (day,))
    receipts = [
        rec
        for rec in iter_runtime_receipts(receipt_roots or default_receipt_roots())
        if day_from_receipt(rec) == day and rec.get("provider") != "claude"
    ]
    for receipt in receipts:
        record_receipt(receipt, path=path)
    sessions = 0
    for transcript in iter_claude_transcripts(transcript_root or default_transcript_root()):
        if _rebuild_transcript_day(transcript, day, path=path):
            sessions += 1
    with connect(path) as conn:
        for row in keep:
            conn.execute(
                "INSERT INTO usage_daily ("
                "day, cli, model, input_tokens, output_tokens, cache_tokens, "
                "total_tokens, cost_usd, api_usd, calls"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )
    return {"sessions": sessions, "receipts": len(receipts), "kept": len(keep)}


def record_receipt(receipt: dict, *, path: Path | None = None) -> bool:
    usage = receipt.get("usage")
    input_tokens, output_tokens, cache_tokens, total_tokens = tokens_from_usage(usage)
    cost_usd = cost_from_receipt(receipt)
    if input_tokens <= 0 and output_tokens <= 0 and cache_tokens <= 0 and total_tokens <= 0 and cost_usd <= 0:
        return False
    cli = receipt.get("provider") if isinstance(receipt.get("provider"), str) else ""
    model = receipt.get("model") if isinstance(receipt.get("model"), str) else ""
    record_usage(
        day=day_from_receipt(receipt),
        cli=cli or "unknown",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_tokens=cache_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        path=path,
    )
    return True


def record_transcript(
    transcript: Path,
    *,
    cli: str,
    session_id: str = "",
    path: Path | None = None,
) -> bool:
    if not transcript.is_file():
        return False
    source = transcript_cursor_key(transcript, session_id)
    allow_sidechain = is_subagent_transcript(transcript)
    with connect(path) as conn:
        row = conn.execute(
            "SELECT last_line, cache_peak FROM ingest_cursor WHERE source = ?",
            (source,),
        ).fetchone()
        start = int(row[0]) if row else 0
        cache_peak = int(row[1]) if row else 0
    lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    if start >= len(lines):
        return False
    input_tokens = 0
    output_tokens = 0
    model = ""
    chunk_peak = cache_peak
    for line in lines[start:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
        if isinstance(message.get("model"), str) and message["model"]:
            model = message["model"]
        usage = _line_usage(payload, allow_sidechain=allow_sidechain)
        if not usage:
            continue
        added_in, added_out, _cache, _total = tokens_from_usage(usage)
        input_tokens += added_in
        output_tokens += added_out
        chunk_peak = max(chunk_peak, _working_set(usage))
    cache_delta = max(0, chunk_peak - cache_peak)
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO ingest_cursor (source, last_line, cache_peak) VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_line = excluded.last_line,
                cache_peak = excluded.cache_peak
            """,
            (source, len(lines), chunk_peak),
        )
    if input_tokens <= 0 and output_tokens <= 0 and cache_delta <= 0:
        return False
    record_usage(
        day=datetime.now(timezone.utc).date().isoformat(),
        cli=cli or "claude",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_tokens=cache_delta,
        total_tokens=input_tokens + output_tokens + cache_delta,
        path=path,
    )
    return True


def record_hook_payload(payload: dict, *, path: Path | None = None) -> bool:
    transcript = (
        payload.get("agent_transcript_path")
        or payload.get("agentTranscriptPath")
        or payload.get("transcript_path")
        or payload.get("transcriptPath")
    )
    session_id = payload.get("session_id") or payload.get("sessionId") or ""
    cli = payload.get("client") or os.environ.get("AGENT_HOOK_CLIENT") or "claude"
    recorded = False
    if isinstance(transcript, str) and transcript:
        dest = Path(transcript)
        recorded = record_transcript(
            dest,
            cli=str(cli),
            session_id=str(session_id),
            path=path,
        )
        if not is_subagent_transcript(dest):
            folder = dest.with_suffix("") / "subagents"
            if folder.is_dir():
                for child in sorted(folder.glob("*.jsonl")):
                    recorded = (
                        record_transcript(child, cli=str(cli), path=path) or recorded
                    )
        return recorded
    usage = normalize_usage(payload.get("usage") or payload)
    cost = cost_from_receipt(payload)
    if not usage and cost <= 0:
        return False
    input_tokens, output_tokens, cache_tokens, total_tokens = tokens_from_usage(usage)
    record_usage(
        day=day_from_receipt(payload),
        cli=str(cli),
        model=payload.get("model") if isinstance(payload.get("model"), str) else "",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_tokens=cache_tokens,
        total_tokens=total_tokens,
        cost_usd=cost,
        path=path,
    )
    return True


def rows(path: Path | None = None, *, day: str | None = None) -> list[sqlite3.Row]:
    with connect(path) as conn:
        conn.row_factory = sqlite3.Row
        if day:
            return list(
                conn.execute(
                    "SELECT * FROM usage_daily WHERE day = ? ORDER BY cli, model",
                    (day,),
                )
            )
        return list(conn.execute("SELECT * FROM usage_daily ORDER BY day, cli, model"))


def row_payload(row: sqlite3.Row) -> dict:
    keys = set(row.keys())
    return {
        "day": row["day"],
        "cli": row["cli"],
        "model": row["model"],
        "input_tokens": int(row["input_tokens"] or 0),
        "output_tokens": int(row["output_tokens"] or 0),
        "cache_tokens": int(row["cache_tokens"] or 0),
        "total_tokens": int(row["total_tokens"] or 0),
        "cost_usd": float(row["cost_usd"] or 0),
        "api_usd": float(row["api_usd"] or 0) if "api_usd" in keys else 0.0,
        "calls": int(row["calls"] or 0),
    }


def backfill_api_usd(path: Path | None = None, catalog: list[dict] | None = None) -> int:
    prices = catalog if catalog is not None else catalog_for_db(path)
    updated = 0
    with connect(path) as conn:
        for row in conn.execute(
            "SELECT day, cli, model, input_tokens, output_tokens, cache_tokens "
            "FROM usage_daily"
        ):
            estimate, _matched = estimate_api_usd(
                row[2], int(row[3] or 0), int(row[4] or 0), int(row[5] or 0), prices
            )
            if estimate is None:
                continue
            conn.execute(
                "UPDATE usage_daily SET api_usd = ? WHERE day = ? AND cli = ? AND model = ?",
                (estimate, row[0], row[1], row[2]),
            )
            updated += 1
    return updated


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return f"{'-':>10}"
    return f"{value:>10.4f}"


def _print_rows(records: list[sqlite3.Row], catalog: list[dict] | None = None) -> None:
    if not records:
        print("no usage rows")
        return
    prices = catalog if catalog is not None else load_openrouter_prices()
    print(
        f"{'day':<12} {'cli':<12} {'model':<28} {'in':>10} {'out':>10} "
        f"{'cache':>10} {'total':>10} {'usd':>10} {'api$':>10} {'calls':>6}"
    )
    for row in records:
        payload = row_payload(row)
        estimate = payload["api_usd"] or None
        if estimate is None or estimate <= 0:
            estimate, _matched = estimate_api_usd(
                payload["model"],
                payload["input_tokens"],
                payload["output_tokens"],
                payload["cache_tokens"],
                prices,
            )
        print(
            f"{payload['day']:<12} {payload['cli']:<12} {payload['model']:<28} "
            f"{payload['input_tokens']:>10} {payload['output_tokens']:>10} "
            f"{payload['cache_tokens']:>10} {payload['total_tokens']:>10} "
            f"{payload['cost_usd']:>10.4f} {_fmt_usd(estimate)} {payload['calls']:>6}"
        )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "show"
    if command in {"-h", "--help", "help"}:
        print(
            "usage: usage_ledger.py [show [YYYY-MM-DD]|today|json [YYYY-MM-DD]|"
            "critique|refresh-prices|prices|backfill-api|rebuild YYYY-MM-DD]"
        )
        print(f"db: {db_path()}")
        print(f"prices: {prices_path()}")
        print(f"table: {prices_table_path()}")
        return 0
    if command == "refresh-prices":
        models = refresh_openrouter_prices()
        print(f"openrouter models: {len(models)}")
        print(prices_path())
        print(prices_table_path())
        return 0
    if command == "prices":
        models = load_openrouter_prices()
        path = write_openrouter_prices_table(models)
        print(f"openrouter models: {len(models)}")
        print(path)
        return 0
    if command == "backfill-api":
        updated = backfill_api_usd()
        print(f"backfilled api_usd rows: {updated}")
        return 0
    if command == "rebuild":
        if len(args) < 2:
            print("usage: usage_ledger.py rebuild YYYY-MM-DD", file=sys.stderr)
            return 2
        stats = rebuild_day(args[1])
        print(
            f"rebuilt {args[1]} sessions={stats['sessions']} "
            f"receipts={stats['receipts']} kept={stats['kept']}"
        )
        _print_rows(rows(day=args[1]))
        return 0
    if command == "json":
        day = args[1] if len(args) > 1 else None
        print(json.dumps([row_payload(row) for row in rows(day=day)], ensure_ascii=True))
        return 0
    if command == "critique":
        stats = critique_follow_stats()
        print(
            f"advised={stats['advised']} followed={stats['followed']} "
            f"ignored={stats['ignored']} open={stats['open']}"
        )
        return 0
    if command == "today":
        _print_rows(rows(day=datetime.now(timezone.utc).date().isoformat()))
        return 0
    if command == "show":
        day = args[1] if len(args) > 1 else None
        _print_rows(rows(day=day))
        return 0
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

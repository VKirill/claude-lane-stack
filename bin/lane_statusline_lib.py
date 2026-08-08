"""Native Claude Code statusLine bars + HANDOFF chip for Claude Lane Stack.

No claude-pulse dependency. Reads rate limits / context / cost from Claude Code
statusLine stdin JSON (Claude Code ≥2.1.80 exposes rate_limits). Optional
last-known cache under ~/.agents/statusline/ so a missing tick still shows bars.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HANDOFF_NAME = "HANDOFF.json"
MAX_CHIP = 56
BAR_WIDTH = 4
FILL = "\u2501"  # ━
EMPTY = "\u2500"  # ─

# Single-column markers only. Emoji (⚡ ⚠ ▶) are double-width in most terminals
# and make Claude Code statusLine layout collide (icon over text).
ICON_RUN = ">"  # was ▶
ICON_WARN = "!"  # was ⚠
ICON_OK = "+"  # was ✓
ICON_DOT = "."  # was ·
ICON_PEAK = "*"  # was ⚡

# Sessions that get the lane HUD (native bars + HANDOFF). Everyone else → claude-pulse.
DEFAULT_LANE_AGENTS = (
    "dev-orchestrator",
    "frontend-orchestrator",
    "run-supervisor",
    "lane-supervisor",
)

# ANSI
RESET = "\033[0m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
WHITE = "\033[37m"

ACTION_SHORT = {
    "fix_control_plane": "fix_cp",
    "fix_contract": "fix_ctr",
    "operator_intervention": "ops",
    "resume_run": "resume",
    "dispatch": "dispatch",
}


def cache_path() -> Path:
    root = Path(
        os.environ.get(
            "LANE_STATUSLINE_CACHE",
            str(Path.home() / ".agents" / "statusline"),
        )
    )
    return root / "last_usage.json"


def _root(data: dict) -> dict:
    if isinstance(data.get("data"), dict):
        return data["data"]
    return data


def _payload_roots(data: dict[str, Any]) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = [data]
    nested = data.get("data")
    if isinstance(nested, dict):
        roots.append(nested)
    return roots


def _as_payload(raw_or_data: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw_or_data is None:
        return {}
    if isinstance(raw_or_data, dict):
        return raw_or_data
    if not isinstance(raw_or_data, str) or not raw_or_data.strip():
        return {}
    try:
        data = json.loads(raw_or_data)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def extract_agent_type(raw_or_data: str | dict[str, Any] | None) -> str:
    """Best-effort agent_type from statusLine / hook JSON."""
    data = _as_payload(raw_or_data)
    if not data:
        return ""

    for root in _payload_roots(data):
        for key in ("agent_type", "agent", "subagent_type"):
            val = root.get(key)
            if isinstance(val, str) and val.strip() and key != "agent":
                return val.strip()
            # bare string agent
            if key == "agent" and isinstance(val, str) and val.strip() and "/" not in val:
                # avoid mistaking paths; agent names are tokens
                if val.strip() in lane_agent_set() or "-" in val or val.isidentifier():
                    return val.strip()
        agent = root.get("agent")
        if isinstance(agent, dict):
            for key in ("type", "name", "agent_type"):
                val = agent.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return ""


def extract_session_id(raw_or_data: str | dict[str, Any] | None) -> str:
    data = _as_payload(raw_or_data)
    if not data:
        return ""
    for root in _payload_roots(data):
        for key in ("session_id", "sessionId"):
            val = root.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        for key in ("transcript_path", "transcriptPath"):
            val = root.get(key)
            if isinstance(val, str) and val.strip():
                return Path(val).stem
    return ""


def statusline_cache_root() -> Path:
    return Path(
        os.environ.get(
            "LANE_STATUSLINE_CACHE",
            str(Path.home() / ".agents" / "statusline"),
        )
    )


def session_mark_path(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in session_id)[:120]
    return statusline_cache_root() / "sessions" / f"{safe}.json"


def write_session_agent(session_id: str, agent_type: str) -> Path | None:
    if not session_id or not agent_type:
        return None
    path = session_mark_path(session_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "agent_type": agent_type,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        return path
    except OSError:
        return None


def read_session_agent(session_id: str) -> str:
    if not session_id:
        return ""
    path = session_mark_path(session_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    agent = data.get("agent_type")
    return agent.strip() if isinstance(agent, str) else ""


def lane_agent_set() -> set[str]:
    raw = os.environ.get("LANE_STATUSLINE_AGENTS")
    if raw is None or not str(raw).strip():
        return set(DEFAULT_LANE_AGENTS)
    return {part.strip() for part in str(raw).split(",") if part.strip()}


def use_lane_hud(raw_or_data: str | dict[str, Any] | None) -> bool:
    """True → native lane bars+chip; False → standard claude-pulse.

    Override:
      LANE_STATUSLINE_ENGINE=lane|pulse|auto  (default auto)
    """
    engine = (os.environ.get("LANE_STATUSLINE_ENGINE") or "auto").strip().lower()
    if engine in {"lane", "native", "hud"}:
        return True
    if engine in {"pulse", "external", "claude-pulse"}:
        return False

    agent = extract_agent_type(raw_or_data)
    if not agent:
        agent = (
            os.environ.get("CLAUDE_AGENT_TYPE") or os.environ.get("AGENT_TYPE") or ""
        ).strip()
    if not agent:
        # SessionStart mark (statusLine may omit agent_type)
        sid = extract_session_id(raw_or_data)
        agent = read_session_agent(sid)
    if not agent:
        return False
    return agent in lane_agent_set()


def parse_stdin(raw: str) -> dict[str, Any]:
    """Parse Claude Code statusLine JSON → flat usage/context dict."""
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}

    root = _root(data)
    out: dict[str, Any] = {}
    agent = extract_agent_type(data)
    if agent:
        out["agent_type"] = agent

    # cwd for handoff discovery
    for key in ("cwd", "cwd_path"):
        val = root.get(key)
        if isinstance(val, str) and val:
            out["cwd"] = val
            break
    if "cwd" not in out:
        ws = root.get("workspace")
        if isinstance(ws, dict):
            for key in ("current_dir", "cwd", "path"):
                val = ws.get(key)
                if isinstance(val, str) and val:
                    out["cwd"] = val
                    break

    # model
    model = root.get("model")
    if isinstance(model, dict):
        name = model.get("display_name") or model.get("id") or ""
        if isinstance(name, str) and name:
            out["model_name"] = name.replace("Claude ", "").strip()

    # context
    ctx = root.get("context_window")
    if isinstance(ctx, dict):
        pct = ctx.get("used_percentage")
        if pct is not None:
            try:
                out["context_pct"] = float(pct)
            except (TypeError, ValueError):
                pass
        size = ctx.get("context_window_size")
        used_in = ctx.get("total_input_tokens")
        used_out = ctx.get("total_output_tokens")
        if size is not None and used_in is not None:
            try:
                out["context_limit"] = int(size)
                out["context_used"] = int(used_in) + int(used_out or 0)
            except (TypeError, ValueError):
                pass

    # cost
    cost = root.get("cost")
    if isinstance(cost, dict):
        total = cost.get("total_cost_usd")
        if total is not None:
            try:
                out["cost_usd"] = float(total)
            except (TypeError, ValueError):
                pass

    # rate limits (preferred source — no OAuth)
    rl = root.get("rate_limits")
    if isinstance(rl, dict):
        usage: dict[str, Any] = {}
        for window in ("five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet"):
            w = rl.get(window)
            if not isinstance(w, dict):
                continue
            pct = w.get("used_percentage")
            if pct is None:
                pct = w.get("utilization")
            if pct is None:
                continue
            try:
                util = float(pct)
            except (TypeError, ValueError):
                continue
            resets_iso = _normalize_resets(w.get("resets_at"))
            usage[window] = {"utilization": util, "resets_at": resets_iso}
        if usage:
            out["usage"] = usage

    return out


def _normalize_resets(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str) and value.strip():
        # already ISO or numeric string
        s = value.strip()
        try:
            if re.fullmatch(r"\d+(\.\d+)?", s):
                return datetime.fromtimestamp(float(s), tz=timezone.utc).isoformat()
            # validate ISO
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            return s.replace("Z", "+00:00") if s.endswith("Z") else s
        except (ValueError, OSError, OverflowError):
            return s
    return None


def load_usage_cache() -> dict[str, Any]:
    path = cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_usage_cache(ctx: dict[str, Any]) -> None:
    usage = ctx.get("usage")
    if not isinstance(usage, dict) or not usage:
        return
    path = cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "usage": usage,
        }
        # preserve last context/cost for display if next tick is sparse
        for key in ("context_pct", "cost_usd", "model_name"):
            if key in ctx:
                payload[key] = ctx[key]
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def merge_with_cache(ctx: dict[str, Any]) -> dict[str, Any]:
    """Fill missing usage from last-known cache."""
    if isinstance(ctx.get("usage"), dict) and ctx["usage"]:
        save_usage_cache(ctx)
        return ctx
    cached = load_usage_cache()
    if isinstance(cached.get("usage"), dict) and cached["usage"]:
        merged = dict(ctx)
        merged["usage"] = cached["usage"]
        merged["_usage_cached"] = True
        return merged
    return ctx


def bar_color(pct: float) -> str:
    if pct < 50:
        return GREEN
    if pct < 80:
        return YELLOW
    return RED


def make_bar(pct: float, width: int = BAR_WIDTH) -> str:
    pct = max(0.0, min(100.0, float(pct or 0)))
    filled = int(round(pct / 100 * width))
    filled = max(0, min(width, filled))
    colour = bar_color(pct)
    return f"{colour}{FILL * filled}{DIM}{EMPTY * (width - filled)}{RESET}"


def format_reset_countdown(resets_at: str | None) -> str:
    if not resets_at:
        return ""
    try:
        resets = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        if resets.tzinfo is None:
            resets = resets.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        total = int((resets - now).total_seconds())
        if total <= 0:
            return ""  # window already rolled — omit noise ("now")
        hours = total // 3600
        minutes = (total % 3600) // 60
        if hours > 48:
            days = hours // 24
            return f"{days}d"
        if hours > 0:
            return f"{hours}h{minutes:02d}m" if hours < 10 else f"{hours}h"
        return f"{minutes}m"
    except (ValueError, TypeError, OSError):
        return ""


def format_cost(cost_usd: float | None) -> str:
    if cost_usd is None:
        return ""
    try:
        v = float(cost_usd)
    except (TypeError, ValueError):
        return ""
    if v < 0:
        return ""
    if v < 10:
        return f"${v:.2f}"
    if v < 100:
        return f"${v:.1f}"
    return f"${v:.0f}"


# Anthropic peak hours (limits burn faster). Defaults match published policy +
# claude-pulse: weekdays 13:00–19:00 local time; weekends always off-peak.
DEFAULT_PEAK_START = "13:00"
DEFAULT_PEAK_END = "19:00"
PEAK_APPROACH_MINUTES = 120


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def display_width(text: str) -> int:
    """Terminal columns for *text* (no ANSI). Wide / emoji chars count as 2."""
    width = 0
    for ch in text:
        if ch in "\r\n\t":
            continue
        # Combining marks don't advance the cursor
        if unicodedata.combining(ch):
            continue
        eaw = unicodedata.east_asian_width(ch)
        if eaw in {"F", "W"}:
            width += 2
        elif eaw == "A":
            # Ambiguous — treat as wide for statusline safety (icons)
            # except common Latin-ish punctuation already covered by Na/N
            o = ord(ch)
            if o > 0xFF:
                width += 2
            else:
                width += 1
        else:
            # Many emoji are "N" but still render 2 columns
            if ord(ch) >= 0x1F300:
                width += 2
            else:
                width += 1
    return width


def clip_display(text: str, max_cols: int) -> str:
    """Clip to max terminal columns, append ASCII '...' if truncated."""
    ell = "..."
    ell_w = 3
    if max_cols <= 0:
        return ""
    if display_width(text) <= max_cols:
        return text
    if max_cols <= ell_w:
        return ell[:max_cols]
    out: list[str] = []
    used = 0
    budget = max_cols - ell_w
    for ch in text:
        w = display_width(ch)
        if used + w > budget:
            break
        out.append(ch)
        used += w
    return "".join(out) + ell


def peak_hours_status(
    *,
    now: datetime | None = None,
    start: str | None = None,
    end: str | None = None,
    weekdays_only: bool = True,
    enabled: bool | None = None,
) -> tuple[bool, str, str]:
    """Return (is_peak, plain_label, ansi_colored_label).

    Compact labels (statusline budget) — ASCII/single-width only:
      peak:        *Peak 2h     (RED)
      approaching: *in 45m      (YELLOW) — within 2h of start
      off-peak:    Off          (GREEN)
    """
    if enabled is None:
        env = (os.environ.get("LANE_STATUSLINE_PEAK") or "1").strip().lower()
        enabled = env not in {"0", "false", "no", "off"}
    if not enabled:
        return False, "", ""

    start = start or os.environ.get("LANE_STATUSLINE_PEAK_START") or DEFAULT_PEAK_START
    end = end or os.environ.get("LANE_STATUSLINE_PEAK_END") or DEFAULT_PEAK_END
    try:
        sh, sm = _parse_hhmm(start)
        eh, em = _parse_hhmm(end)
    except (ValueError, IndexError):
        return False, "", ""

    now = now or datetime.now().astimezone()
    # weekends off-peak under Anthropic weekday-only peak
    if weekdays_only and now.weekday() >= 5:
        label = "Off"
        return False, label, f"{GREEN}{label}{RESET}"

    now_mins = now.hour * 60 + now.minute
    start_mins = sh * 60 + sm
    end_mins = eh * 60 + em

    if start_mins <= now_mins < end_mins:
        left = end_mins - now_mins
        left_str = f"{left // 60}h" if left >= 60 else f"{left}m"
        if left >= 60 and left % 60:
            left_str = f"{left // 60}h{left % 60:02d}m"
        label = f"{ICON_PEAK}Peak {left_str}"
        return True, label, f"{RED}{label}{RESET}"

    if now_mins < start_mins:
        until = start_mins - now_mins
        if until <= PEAK_APPROACH_MINUTES:
            until_str = f"{until // 60}h" if until >= 60 else f"{until}m"
            if until >= 60 and until % 60:
                until_str = f"{until // 60}h{until % 60:02d}m"
            label = f"{ICON_PEAK}in {until_str}"
            return False, label, f"{YELLOW}{label}{RESET}"

    label = "Off"
    return False, label, f"{GREEN}{label}{RESET}"


def render_bars(ctx: dict[str, Any], *, width: int = BAR_WIDTH) -> str:
    """Compact native bars: S | W | C | $ | peak (Off / ⚡Peak)."""
    parts: list[str] = []
    usage = ctx.get("usage") if isinstance(ctx.get("usage"), dict) else {}

    five = usage.get("five_hour") if isinstance(usage.get("five_hour"), dict) else None
    if five and five.get("utilization") is not None:
        pct = float(five["utilization"])
        bar = make_bar(pct, width=width)
        reset = format_reset_countdown(five.get("resets_at"))
        bit = f"{WHITE}S {bar}{WHITE} {pct:.0f}%{RESET}"
        if reset:
            bit += f"{DIM} {reset}{RESET}"
        parts.append(bit)

    seven = usage.get("seven_day") if isinstance(usage.get("seven_day"), dict) else None
    if seven and seven.get("utilization") is not None:
        pct = float(seven["utilization"])
        bar = make_bar(pct, width=width)
        parts.append(f"{WHITE}W {bar}{WHITE} {pct:.0f}%{RESET}")

    ctx_pct = ctx.get("context_pct")
    if ctx_pct is not None:
        try:
            pct = float(ctx_pct)
            bar = make_bar(pct, width=width)
            parts.append(f"{WHITE}C {bar}{WHITE} {pct:.0f}%{RESET}")
        except (TypeError, ValueError):
            pass

    cost = format_cost(ctx.get("cost_usd"))
    if cost:
        parts.append(f"{WHITE}{cost}{RESET}")

    # Peak / off-peak burn mode (always when we have any bar data, or alone)
    _is_peak, _plain, peak_ansi = peak_hours_status()
    if peak_ansi:
        parts.append(peak_ansi)

    if not parts:
        return ""
    sep = f" {DIM}|{RESET} "
    return sep.join(parts)


def find_handoff(start: Path | None) -> Path | None:
    candidates: list[Path] = []
    if start is not None:
        try:
            candidates.append(start.expanduser().resolve())
        except OSError:
            candidates.append(start.expanduser())
    try:
        candidates.append(Path.cwd().resolve())
    except OSError:
        pass
    seen: set[Path] = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        parts = list(base.parts)
        if ".worktrees" in parts:
            idx = parts.index(".worktrees")
            base = Path(*parts[:idx])
        for cur in (base, *base.parents):
            handoff = cur / ".agents" / HANDOFF_NAME
            if handoff.is_file():
                return handoff
            if cur.parent == cur:
                break
    return None


def render_chip(handoff_path: Path) -> str:
    try:
        data = json.loads(handoff_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""

    prof = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    mw = prof.get("main_write") or "?"
    ws = prof.get("workspace_mode") or "?"
    if ws == "in_place":
        ws = "main"
    elif ws == "worktree":
        ws = "wt"

    blocked = data.get("blocked") if isinstance(data.get("blocked"), list) else []
    active = data.get("active_runs") if isinstance(data.get("active_runs"), list) else []
    nxt = data.get("next") if isinstance(data.get("next"), list) else []

    run_bit = ""
    for a in active:
        if not isinstance(a, dict):
            continue
        stage = str(a.get("stage") or "")
        if stage in {"running", "degraded", "dispatching"} or stage not in {
            "accepted",
            "blocked",
            "failed",
            "planning",
        }:
            slug = str(a.get("slug") or "")[:14]
            counts = a.get("counts") if isinstance(a.get("counts"), dict) else {}
            acc, tot = counts.get("accepted"), counts.get("total")
            if isinstance(acc, int) and isinstance(tot, int) and tot:
                run_bit = f"{ICON_RUN}{slug} {acc}/{tot}"
            else:
                run_bit = f"{ICON_RUN}{slug}"
            break
    if not run_bit and active:
        a0 = active[0] if isinstance(active[0], dict) else {}
        slug = str(a0.get("slug") or "")[:14]
        if slug:
            run_bit = f"{ICON_DOT}{slug}"

    blk_bit = f"{ICON_WARN}{len(blocked)}" if blocked else ICON_OK

    next_bit = ""
    if nxt and isinstance(nxt[0], dict):
        act = str(nxt[0].get("action") or "")
        if act and act != "idle":
            next_bit = f"->{ACTION_SHORT.get(act, act)}"
        elif act == "idle":
            next_bit = "idle"

    parts = [f"{mw}/{ws}"]
    if run_bit:
        parts.append(run_bit)
    parts.append(blk_bit)
    if next_bit:
        parts.append(next_bit)
    chip = " ".join(parts)
    chip = clip_display(chip, MAX_CHIP)
    # Leading space before separator so bar% never collides with chip
    return f" {DIM}|{RESET} {CYAN}{chip}{RESET}"


def build_status_line(raw_stdin: str, *, mode: str = "compact") -> str:
    """Build full status line.

    mode:
      compact — native bars + chip (default)
      bars    — native bars only
      chip    — handoff chip only
      full    — same as compact (reserved; native is always compact-style)
    """
    mode = (mode or "compact").strip().lower()
    if mode not in {"compact", "bars", "chip", "full"}:
        mode = "compact"

    ctx = merge_with_cache(parse_stdin(raw_stdin))
    bars = render_bars(ctx) if mode in {"compact", "bars", "full"} else ""
    chip = ""
    if mode in {"compact", "chip", "full"}:
        cwd = Path(ctx["cwd"]) if ctx.get("cwd") else None
        handoff = find_handoff(cwd)
        if handoff:
            chip = render_chip(handoff)

    def _strip_chip_prefix(body: str) -> str:
        body = body.lstrip()
        for sep in (f"{DIM}|{RESET} ", f"{DIM}│{RESET} "):
            if body.startswith(sep):
                return body[len(sep) :]
        return body

    if mode == "chip":
        return _strip_chip_prefix(chip) or "lane"

    if mode == "bars":
        return bars or "lane"

    if bars and chip:
        # Explicit space between bars and chip separator (chip already starts with " | ")
        return f"{bars}{chip}"
    if bars:
        return bars
    if chip:
        return _strip_chip_prefix(chip)
    return "lane"

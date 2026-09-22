"""Append-only decision log, and the stats derived from it.

Every judged output writes one line. Every recall writes one line. The ratio of
recalled keys to pruned keys is the regret rate: how often winnow hid something
the agent turned out to need. That number, plotted against the ``drop``
threshold, is the calibration story.
"""

from __future__ import annotations

import json
import time
import traceback
from typing import Any, Iterator

from winnow.config import Config

JEV_USD_PER_MILLION_INPUT = 0.042


def log_event(cfg: Config, event: dict[str, Any]) -> None:
    try:
        cfg.home.mkdir(parents=True, exist_ok=True)
        with cfg.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), **event}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_error(cfg: Config, where: str, exc: BaseException) -> None:
    try:
        cfg.home.mkdir(parents=True, exist_ok=True)
        with cfg.error_log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {where}: {exc!r}\n")
            fh.write("".join(traceback.format_exception(exc)))
    except OSError:
        pass


def read_events(cfg: Config) -> Iterator[dict[str, Any]]:
    if not cfg.log_path.exists():
        return
    with cfg.log_path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event


def stats(cfg: Config) -> dict[str, Any]:
    judged = rewritten = passthrough = 0
    chars_before = chars_after = 0
    judge_ms: list[int] = []
    summary_ms: list[int] = []
    judge_tokens = 0
    pruned_keys: set[str] = set()
    recalled_keys: set[str] = set()
    context_injections = 0
    reasons: dict[str, int] = {}
    sources: dict[str, int] = {}
    shadow_judged = shadow_would_rewrite = shadow_saved = 0

    for event in read_events(cfg):
        if event.get("demo"):
            continue
        kind = event.get("event")
        if kind == "post_tool_use":
            source = str(event.get("source") or "http")
            sources[source] = sources.get(source, 0) + 1
            if event.get("judge_ms") is not None:
                judge_ms.append(int(event["judge_ms"]))
            judge_tokens += int(event.get("judge_input_tokens") or 0)
            if event.get("mode") == "shadow":
                shadow_judged += 1
                if event.get("would_rewrite"):
                    shadow_would_rewrite += 1
                    shadow_saved += max(0, int(event.get("chars_before") or 0) - int(event.get("chars_after") or 0))
                continue
            judged += 1
            reason = str(event.get("reason", "?"))
            reasons[reason] = reasons.get(reason, 0) + 1
            if event.get("summary_ms") is not None:
                summary_ms.append(int(event["summary_ms"]))
            if event.get("rewritten"):
                rewritten += 1
                chars_before += int(event.get("chars_before") or 0)
                chars_after += int(event.get("chars_after") or 0)
                if event.get("key"):
                    pruned_keys.add(str(event["key"]))
            else:
                passthrough += 1
        elif kind == "recall":
            if event.get("key"):
                recalled_keys.add(str(event["key"]))
        elif kind == "user_prompt_submit" and event.get("injected"):
            context_injections += 1

    saved = max(0, chars_before - chars_after)
    regret = len(recalled_keys & pruned_keys) / len(pruned_keys) if pruned_keys else 0.0
    from winnow.review import review_stats

    return {
        **review_stats(cfg),
        "outputs_judged": judged,
        "outputs_rewritten": rewritten,
        "outputs_passed_through": passthrough,
        "reasons": reasons,
        "sources": sources,
        "chars_saved": saved,
        "est_tokens_saved": saved // 4,
        "pruned_keys": len(pruned_keys),
        "recalled_keys": len(recalled_keys & pruned_keys),
        "regret_rate": round(regret, 4),
        "judge_ms_avg": round(sum(judge_ms) / len(judge_ms)) if judge_ms else None,
        "summary_ms_avg": round(sum(summary_ms) / len(summary_ms)) if summary_ms else None,
        "judge_input_tokens": judge_tokens,
        "est_judge_cost_usd": round(judge_tokens / 1_000_000 * JEV_USD_PER_MILLION_INPUT, 6),
        "context_injections": context_injections,
        "shadow_outputs_judged": shadow_judged,
        "shadow_would_rewrite": shadow_would_rewrite,
        "shadow_chars_would_save": shadow_saved,
        "shadow_est_tokens_would_save": shadow_saved // 4,
    }

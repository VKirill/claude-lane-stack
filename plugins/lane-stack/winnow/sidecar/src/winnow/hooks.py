"""The two hook handlers. Each takes the hook payload Claude Code sends on stdin
and returns the JSON to print on stdout, or ``None`` to pass through.

Both are written so that any failure (no API key, judge down, odd tool shape)
degrades to pass-through. winnow must never be the reason a tool result went
missing.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from winnow import cache, log
from winnow.chunk import Block, chunk, group_contiguous
from winnow.config import Config
from winnow.extract import extract, trimmed_input
from winnow.judge import Judge, build_judge
from winnow.memory import load_candidates
from winnow.policy import decide
from winnow.stub import assemble, digest, render_stub
from winnow.summarize import Summarizer, build_summarizer
from winnow.transcript import Task, read_task, task_from_payload, transcript_for


@dataclass
class Runtime:
    cfg: Config
    judge: Judge | None
    summarizer: Summarizer | None
    extra_event: dict[str, Any] = field(default_factory=dict)  # merged into every log line

    @classmethod
    def from_config(cls, cfg: Config) -> "Runtime":
        return cls(cfg, build_judge(cfg), build_summarizer(cfg))


# --------------------------------------------------------------------------- #
# PostToolUse: judge each block of a large tool result                        #
# --------------------------------------------------------------------------- #

def excluded(tool_name: str, tool_input: Any, cfg: Config) -> bool:
    """winnow never judges its own files or its own commands.

    Otherwise ``winnow recall`` output, replay samples, and label files would be
    pruned while you are trying to read them.
    """
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Read":
        raw = str(tool_input.get("file_path") or "")
        if raw:
            try:
                path = Path(raw).resolve()
            except (OSError, ValueError):
                return False
            for base in cfg.exclude_paths:
                try:
                    path.relative_to(base.resolve())
                    return True
                except ValueError:
                    continue
    if tool_name == "Bash" and cfg.exclude_commands:
        return re.search(cfg.exclude_commands, str(tool_input.get("command") or "")) is not None
    return False


def worth_judging(payload: dict[str, Any], cfg: Config) -> bool:
    """Cheap pre-check that needs no SDK import: right tool, not excluded, big enough output."""
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in cfg.tools or excluded(tool_name, payload.get("tool_input"), cfg):
        return False
    extracted = extract(tool_name, payload.get("tool_input"), payload.get("tool_response", payload.get("tool_output")))
    return extracted is not None and len(extracted.text) >= cfg.min_chars


def _block_questions(blocks: list[Block], name: str = "default") -> dict[str, Any]:
    from winnow.questions import build_questions  # imports the SDK lazily

    return build_questions(name, blocks)


def _judge_window(blocks: list[Block], max_chars: int) -> list[Block]:
    """Return every block so the judge can see the complete tool result."""
    return list(blocks)


def post_tool_use(payload: dict[str, Any], runtime: Runtime, meta: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Judge one tool result. ``meta``, if given, receives a summary of a rewrite for the caller's UI."""
    cfg = runtime.cfg
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in cfg.tools or runtime.judge is None or excluded(tool_name, payload.get("tool_input"), cfg):
        return None

    tool_response = payload.get("tool_response", payload.get("tool_output"))
    extracted = extract(tool_name, payload.get("tool_input"), tool_response)
    if extracted is None or len(extracted.text) < cfg.min_chars:
        return None

    blocks = chunk(extracted.text, block_lines=cfg.block_lines, max_blocks=cfg.max_blocks)
    if len(blocks) < 2:
        return None

    task = task_from_payload(payload) or read_task(transcript_for(payload))
    judged = _judge_window(blocks, cfg.max_state_chars)
    state = {
        "task": task.as_state(),
        "tool": {"name": tool_name, "input": trimmed_input(tool_name, payload.get("tool_input"))},
        "blocks": {block.id: block.text for block in judged},
    }

    session_id = str(payload.get("session_id") or "")
    tool_use_id = str(payload.get("tool_use_id") or "")
    event: dict[str, Any] = {
        **runtime.extra_event,
        "event": "post_tool_use",
        "source": str(payload.get("source") or "http"),
        "mode": cfg.mode,
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "agent_id": payload.get("agent_id"),
        "agent_type": payload.get("agent_type"),
        "tool": tool_name,
        "describe": extracted.describe,
        "n_blocks": len(blocks),
        "n_judged": len(judged),
        "chars_before": len(extracted.text),
        "task_known": not task.is_empty,
        "judge": runtime.judge.name,
    }

    event["questions"] = cfg.questions
    try:
        result = runtime.judge.nouls(state, _block_questions(judged, cfg.questions))
    except Exception as exc:  # noqa: BLE001 - any judge failure means pass through
        log.log_error(cfg, "judge", exc)
        log.log_event(cfg, {**event, "rewritten": False, "reason": "judge_error", "error": repr(exc)})
        return None

    event.update(
        judge_model=result.model,
        judge_ms=result.latency_ms,
        judge_input_tokens=result.input_tokens,
        probabilities=result.probabilities,
    )
    verdict = decide(blocks, result.probabilities, result.probabilities.get("error_present"), cfg)
    if not verdict.pruned:
        log.log_event(cfg, {**event, "rewritten": False, "reason": verdict.reason})
        return None

    key = cache.key_for(session_id, tool_use_id, extracted.text)
    cache.store(
        cfg,
        key,
        {
            "tool": tool_name,
            "describe": extracted.describe,
            "session_id": session_id,
            "tool_use_id": tool_use_id,
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "line_offset": extracted.line_offset,
            "task": task.as_state(),
            "questions": cfg.questions,
            "text": extracted.text,
            "blocks": [
                {"id": b.id, "start": b.start, "end": b.end, "p": result.probabilities.get(b.id), "hidden": b in verdict.pruned}
                for b in blocks
            ],
        },
    )

    if cfg.shadow:
        # Everything up to here ran for real; only the rewrite is withheld.
        preview_stubs = {
            group[0].index: render_stub(
                group,
                key,
                None,
                max((result.probabilities.get(b.id, 0.0) for b in group), default=0.0),
                extracted.line_offset,
                digest_text=digest(tool_name, "\n".join(b.text for b in group)),
            )
            for group in group_contiguous(verdict.pruned)
        }
        preview = assemble(blocks, verdict, preview_stubs)
        log.log_event(
            cfg,
            {
                **event,
                "rewritten": False,
                "would_rewrite": True,
                "reason": verdict.reason,
                "key": key,
                "n_hidden": len(verdict.pruned),
                "n_uncertain": len(verdict.uncertain),
                "chars_after": len(preview),
            },
        )
        return None

    stubs: dict[int, str] = {}
    summary_ms = 0
    for n, group in enumerate(group_contiguous(verdict.pruned)):
        text = "\n".join(b.text for b in group)
        summary = None
        if runtime.summarizer is not None and n < cfg.summary_max_groups:
            started = time.perf_counter()
            try:
                summary = runtime.summarizer.summarize(text, task, extracted.describe)
            except Exception as exc:  # noqa: BLE001 - a missing summary is not fatal
                log.log_error(cfg, "summarizer", exc)
            summary_ms += int((time.perf_counter() - started) * 1000)
        max_p = max((result.probabilities.get(b.id, 0.0) for b in group), default=0.0)
        stubs[group[0].index] = render_stub(group, key, summary, max_p, extracted.line_offset, digest_text=digest(tool_name, text))

    new_text = assemble(blocks, verdict, stubs)
    if meta is not None:
        meta.update(hidden=len(verdict.pruned), blocks=len(blocks), before=len(extracted.text), after=len(new_text), key=key)
    log.log_event(
        cfg,
        {
            **event,
            "rewritten": True,
            "reason": verdict.reason,
            "key": key,
            "n_hidden": len(verdict.pruned),
            "n_uncertain": len(verdict.uncertain),
            "chars_after": len(new_text),
            "summary_ms": summary_ms if runtime.summarizer else None,
        },
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": extracted.rebuild(new_text),
        }
    }


# --------------------------------------------------------------------------- #
# UserPromptSubmit: inject the context files this prompt actually needs       #
# --------------------------------------------------------------------------- #


def user_prompt_submit(payload: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
    cfg = runtime.cfg
    prompt = str(payload.get("prompt") or payload.get("prompt_text") or "").strip()
    if len(prompt) < 12 or runtime.judge is None:
        return None

    candidates = load_candidates(cfg, str(payload.get("cwd") or ""))
    if not candidates:
        return None
    from typesafe_sdk import Noul

    state = {
        "prompt": prompt,
        "candidates": {
            c.id: {"title": c.title, "description": c.description, "excerpt": c.text}
            for c in candidates
        },
    }
    questions = {
        c.id: Noul(
            instructions=f"Would the assistant need to read `candidates.{c.id}` to handle `prompt` well?",
            criteria={
                "true": "The file records facts, preferences, decisions, or project state that `prompt` depends on or touches.",
                "false": "The file is about something else; the prompt can be handled without it.",
            },
        )
        for c in candidates
    }

    event: dict[str, Any] = {
        **runtime.extra_event,
        "event": "user_prompt_submit",
        "source": str(payload.get("source") or "http"),
        "mode": cfg.mode,
        "session_id": str(payload.get("session_id") or ""),
        "n_candidates": len(candidates),
        "judge": runtime.judge.name,
    }
    try:
        result = runtime.judge.nouls(state, questions)
    except Exception as exc:  # noqa: BLE001
        log.log_error(cfg, "judge", exc)
        log.log_event(cfg, {**event, "injected": False, "reason": "judge_error", "error": repr(exc)})
        return None

    ranked = sorted(candidates, key=lambda c: result.probabilities.get(c.id, 0.0), reverse=True)
    chosen = [c for c in ranked if result.probabilities.get(c.id, 0.0) >= cfg.context_gate][: cfg.context_top_k]
    event.update(judge_ms=result.latency_ms, judge_input_tokens=result.input_tokens, probabilities=result.probabilities)
    if not chosen:
        log.log_event(cfg, {**event, "injected": False, "reason": "below_gate"})
        return None
    if cfg.shadow:
        log.log_event(cfg, {**event, "injected": False, "would_inject": True, "reason": "shadow", "chosen": [c.id for c in chosen]})
        return None

    parts = ["winnow selected these files as relevant to this prompt (read them here instead of opening them):"]
    for c in chosen:
        header = f"\n\n### {c.title} ({c.path})\n"
        parts.append(header + c.text)

    log.log_event(cfg, {**event, "injected": True, "reason": "injected", "chosen": [c.id for c in chosen]})
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "".join(parts),
        }
    }

#!/usr/bin/env python3
"""Jev plan-critique pass (OpenRouter Decisions API).

Structural still extracts. Jev only answers typed questions: verdict,
whether soft warns are actionable, SPEC↔PLAN conflict. No generated prose.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

JEV_MODEL = "typesafe/jev-1.13"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
HARD_CODES = frozenset(
    {
        "plan_missing",
        "no_tasks",
        "task_parse",
        "owns_empty",
        "verify_missing",
        "owns_overlap",
        "bad_dag",
    }
)
SOFT_CODES = frozenset(
    {"owns_gap", "plan_path_unowned", "verify_heavy", "verify_l2"}
)
ACTIONABLE_CUT = 0.35
UNCERTAIN_CUT = 0.5
_PLAN_CHARS = 4000
_SPEC_CHARS = 2000
_OBJECTIVE_CHARS = 400


class JevCritiqueError(RuntimeError):
    """OpenRouter / Jev invoke or parse failure."""


def _clip(text: str, limit: int) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    return raw[: limit - 16] + "\n…[truncated]"


def _read(path: Path, limit: int) -> str:
    if not path.is_file():
        return ""
    return _clip(path.read_text(encoding="utf-8", errors="replace"), limit)


def pack_jev_state(run_dir: Path, structural: dict[str, Any]) -> dict[str, Any]:
    """Narrow state: named fields only. Do not dump the whole repo."""
    run_dir = run_dir.expanduser().resolve()
    tasks: list[dict[str, Any]] = []
    tasks_dir = run_dir / "tasks"
    if tasks_dir.is_dir():
        for path in sorted(tasks_dir.glob("*.yaml")):
            body = path.read_text(encoding="utf-8", errors="replace")
            tasks.append({"file": path.name, "body": _clip(body, 1800)})
    findings = []
    for item in structural.get("findings") or []:
        if not isinstance(item, dict):
            continue
        if item.get("source") == "llm":
            continue
        if str(item.get("severity") or "") not in {"error", "warn"}:
            continue
        findings.append(
            {
                "id": item.get("id"),
                "severity": item.get("severity"),
                "code": item.get("code"),
                "title": item.get("title"),
                "path": item.get("path"),
                "task_id": item.get("task_id"),
            }
        )
    return {
        "plan": _read(run_dir / "PLAN.md", _PLAN_CHARS),
        "spec": _read(run_dir / "SPEC.md", _SPEC_CHARS),
        "tasks": tasks,
        "structural_findings": findings[:12],
    }


def jev_questions() -> dict[str, Any]:
    return {
        "verdict": {
            "type": "choice",
            "instructions": (
                "PM dispatch gate. A path in read_first that is not in "
                "owns_paths is fine if the writer only imports it. "
                "docs/wiki mentions are noise. Hard fail if two tasks own "
                "the same path or SPEC contradicts PLAN on which task "
                "edits a file."
            ),
            "criteria": {
                "ship": "Writers can start. Soft warns are false positives.",
                "revise": "PM should ack or lightly edit; writers would not hard-fail.",
                "revise_required": (
                    "Overlapping owns, empty owns/verify, or SPEC tells a "
                    "writer to edit a file PLAN moved to another task."
                ),
            },
        },
        "warns_actionable": {
            "type": "noul",
            "instructions": (
                "Do warn-level items in `structural_findings` require a "
                "PLAN/SPEC/task edit before dispatch?"
            ),
            "criteria": {
                "true": "A writer will miss a file they must edit or run L2 as L1",
                "false": "Read-only import, docs noise, or already out of scope",
            },
        },
        "spec_contradicts_plan": {
            "type": "noul",
            "instructions": (
                "Does `spec` or a task objective contradict `plan` "
                "(stale file, work moved to another task)?"
            ),
        },
        "risk": {
            "type": "choice",
            "instructions": "Product risk of this change.",
            "criteria": {
                "low": "Copy, spacing, dead code, isolated UI chrome",
                "medium": "Feature wiring, i18n, admin console, scoped API",
                "high": "Payments, auth, wallet, gates that can lock users out",
            },
        },
    }


def _openrouter_key() -> str:
    env = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if env:
        return env
    try:
        from usage_ledger import openrouter_api_key

        return (openrouter_api_key() or "").strip()
    except Exception:
        return ""


def call_jev(state: object, questions: dict[str, Any], *, timeout: int = 20) -> dict[str, Any]:
    key = _openrouter_key()
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
            "X-Title": "lane-stack plan-critique",
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


def _noul(answers: dict[str, Any], key: str) -> float:
    raw = answers.get(key)
    if not isinstance(raw, dict):
        return 0.0
    try:
        return float(raw.get("noul") or 0)
    except (TypeError, ValueError):
        return 0.0


def _choice(answers: dict[str, Any], key: str, allowed: set[str], default: str) -> tuple[str, float]:
    raw = answers.get(key)
    if not isinstance(raw, dict):
        return default, 0.0
    choice = str(raw.get("choice") or default).strip().lower()
    if choice not in allowed:
        choice = default
    try:
        conf = float(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    return choice, conf


def answers_to_payload(raw: dict[str, Any]) -> dict[str, Any]:
    answers = raw.get("answers") if isinstance(raw.get("answers"), dict) else {}
    verdict, confidence = _choice(
        answers, "verdict", {"ship", "revise", "revise_required"}, "revise"
    )
    warns_actionable = _noul(answers, "warns_actionable")
    spec_contradicts = _noul(answers, "spec_contradicts_plan")
    risk, _risk_conf = _choice(
        answers, "risk", {"low", "medium", "high"}, "medium"
    )
    uncertain = confidence < UNCERTAIN_CUT and verdict == "ship"
    if uncertain:
        verdict = "revise"
    findings: list[dict[str, Any]] = []
    if spec_contradicts >= 0.7:
        findings.append(
            {
                "severity": "warn",
                "code": "missing_invariant",
                "title": "SPEC/PLAN disagree on task ownership",
                "detail": (
                    "Jev noul spec_contradicts_plan="
                    f"{spec_contradicts:.2f}. Align SPEC and the task "
                    "objective with PLAN before dispatch."
                ),
                "path": "SPEC.md",
                "action": "fix_spec",
            }
        )
    summaries = {
        "ship": "Jev: dispatch. Soft structural warns look like noise.",
        "revise": (
            "Jev uncertain; PM review."
            if uncertain
            else "Jev: revise or ack before dispatch."
        ),
        "revise_required": "Jev: hard plan issues before writers.",
    }
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    return {
        "verdict": verdict,
        "summary": summaries[verdict],
        "findings": findings,
        "confidence": confidence,
        "warns_actionable": warns_actionable,
        "spec_contradicts": spec_contradicts,
        "risk": risk,
        "uncertain": uncertain,
        "model": str(raw.get("model") or JEV_MODEL),
        "usage": usage,
    }


def overlay_jev(result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Demote soft structural warns when Jev is confident they are noise."""
    from pipeline_stages import attach_decision  # local — same bin/

    if payload.get("uncertain"):
        return attach_decision(result)
    if str(payload.get("verdict") or "") != "ship":
        return attach_decision(result)
    if float(payload.get("warns_actionable") or 1) >= ACTIONABLE_CUT:
        return attach_decision(result)
    findings = result.get("findings") if isinstance(result.get("findings"), list) else []
    for item in findings:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "")
        if code in HARD_CODES:
            continue
        if code not in SOFT_CODES:
            continue
        if str(item.get("severity") or "") != "warn":
            continue
        item["severity"] = "info"
    result["findings"] = findings
    return attach_decision(result)


def _record_usage(raw: dict[str, Any], payload: dict[str, Any]) -> None:
    try:
        from usage_ledger import record_receipt

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        record_receipt(
            {
                "provider": "jev",
                "model": payload.get("model") or JEV_MODEL,
                "usage": {
                    "input_tokens": usage.get("input_tokens") or 0,
                    "output_tokens": usage.get("output_tokens") or 0,
                },
                "total_cost_usd": usage.get("cost") or 0,
            }
        )
    except Exception:
        return


def invoke_jev_critique(
    run_dir: Path,
    structural: dict[str, Any],
    *,
    timeout: int = 20,
) -> dict[str, Any]:
    state = pack_jev_state(run_dir, structural)
    raw = call_jev(state, jev_questions(), timeout=timeout)
    payload = answers_to_payload(raw)
    _record_usage(raw, payload)
    return payload

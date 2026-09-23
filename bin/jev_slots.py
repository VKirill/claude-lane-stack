#!/usr/bin/env python3
"""Jev judges for night findings, verify tail, brief risk, intent, QA report."""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from jev_decisions import JevCritiqueError, call_jev, choice, noul

DISMISS_CUT = 0.35
SCORE_FOR_RISK = {"low": 2, "medium": 5, "high": 8}


def triage_night_findings(findings: dict[str, dict[str, Any]]) -> list[str]:
    """Dismiss gold-plate / out-of-scope night findings. Returns fingerprints."""
    open_items = [
        (fp, item)
        for fp, item in findings.items()
        if isinstance(item, dict)
        and item.get("actionable")
        and item.get("status") in {"open", "needs_human", "in_progress"}
    ]
    if not open_items:
        return []
    rows = []
    questions: dict[str, Any] = {}
    for index, (fp, item) in enumerate(open_items):
        rows.append(
            {
                "i": index,
                "title": item.get("title"),
                "summary": str(item.get("summary") or ""),
                "severity": item.get("severity"),
                "paths": (item.get("scope") or {}).get("owns_paths") or [],
            }
        )
        questions[f"f{index}_real"] = {
            "type": "noul",
            "instructions": (
                f"Is `findings[{index}]` a real code defect the night fixer "
                "must patch? No if it is gold-plate, style-only, or out of "
                "the stated scope."
            ),
        }
    try:
        raw = call_jev({"findings": rows}, questions, title="lane-stack night-jev")
    except JevCritiqueError:
        return []
    answers = raw.get("answers") or {}
    dismissed: list[str] = []
    for index, (fp, item) in enumerate(open_items):
        if noul(answers, f"f{index}_real") >= DISMISS_CUT:
            continue
        item["actionable"] = False
        item["status"] = "dismissed"
        dismissed.append(fp)
    return dismissed


def classify_verify_tail(detail: str) -> str | None:
    """Refine leftover verification_failed. None = keep regex result."""
    text = detail or ""
    if not text.strip():
        return None
    try:
        raw = call_jev(
            {"verify_output": text},
            {
                "kind": {
                    "type": "choice",
                    "instructions": "What kind of verification failure is `verify_output`?",
                    "criteria": {
                        "real_fail": "Assertion or test failed because the code is wrong",
                        "flake": "Timing, order, or network flake; same test often passes",
                        "env": "Missing tool, auth, docker, or host setup — not the patch",
                    },
                }
            },
            title="lane-stack verify-jev",
        )
    except JevCritiqueError:
        return None
    kind, conf = choice(
        raw.get("answers") or {},
        "kind",
        {"real_fail", "flake", "env"},
        "real_fail",
    )
    if conf < 0.5:
        return None
    if kind == "flake":
        return "verification_flake"
    if kind == "env":
        return "verification_env"
    return None


def score_brief(brief: str) -> dict[str, Any]:
    raw = call_jev(
        {"brief": brief},
        {
            "risk": {
                "type": "choice",
                "instructions": "Product risk of implementing `brief`.",
                "criteria": {
                    "low": "Copy, spacing, dead code, isolated UI chrome",
                    "medium": "Feature wiring, i18n, admin console, scoped API",
                    "high": "Payments, auth, wallet, gates that can lock users out",
                },
            }
        },
        title="lane-stack risk-jev",
    )
    risk, conf = choice(
        raw.get("answers") or {}, "risk", {"low", "medium", "high"}, "medium"
    )
    return {"risk": risk, "score": SCORE_FOR_RISK[risk], "confidence": conf}


def classify_intent(query: str) -> dict[str, Any]:
    raw = call_jev(
        {"query": query},
        {
            "intent": {
                "type": "choice",
                "instructions": "Search intent of `query`.",
                "criteria": {
                    "informational": "Wants to learn or understand",
                    "commercial": "Comparing options before buying",
                    "transactional": "Ready to buy, book, or sign up",
                    "navigational": "Looking for a specific brand or site",
                },
            }
        },
        title="lane-stack intent-jev",
    )
    intent, conf = choice(
        raw.get("answers") or {},
        "intent",
        {"informational", "commercial", "transactional", "navigational"},
        "informational",
    )
    return {"intent": intent, "confidence": conf}


def judge_qa_report(report: str, verdict: str) -> dict[str, Any]:
    raw = call_jev(
        {"report": report, "codex_verdict": verdict},
        {
            "kind": {
                "type": "choice",
                "instructions": "Given `report`, what is the QA outcome really?",
                "criteria": {
                    "real_bug": "Visible product defect a user would hit",
                    "flake": "Timeout, race, or environment flake",
                    "out_of_scope": "Not in the stated QA scenario",
                },
            }
        },
        title="lane-stack qa-jev",
    )
    kind, conf = choice(
        raw.get("answers") or {},
        "kind",
        {"real_bug", "flake", "out_of_scope"},
        "real_bug",
    )
    return {"kind": kind, "confidence": conf}


WRITE_SKILLS = {
    "none": "No extra skill; the writer contract is enough",
    "writer-practices": "General code change: smallest correct diff",
    "impeccable-ui": "UI, layout, CSS, or React visual polish",
    "ru-text": "Russian user-facing copy",
    "karpathy-guidelines": "Model, training, or data-pipeline code quality",
}


def suggest_write_skills(task: dict[str, Any]) -> list[str]:
    """Declared task.skills win. Else one Jev Choice. Fail-open."""
    declared = task.get("skills") if isinstance(task, dict) else None
    if isinstance(declared, list) and declared:
        names = [str(item).strip() for item in declared if str(item).strip()]
        return [name for name in names if name != "none"][:3]
    if "unittest" in __import__("sys").modules:
        return []
    from jev_decisions import jev_enabled

    if not jev_enabled():
        return []
    try:
        raw = call_jev(
            {
                "title": task.get("title"),
                "objective": str(task.get("objective") or ""),
                "owns": task.get("owns_paths") or [],
            },
            {
                "skill": {
                    "type": "choice",
                    "instructions": "Which write skill should the implementer follow for this task?",
                    "criteria": WRITE_SKILLS,
                }
            },
            title="lane-stack skill-jev",
        )
    except JevCritiqueError:
        return []
    pick, conf = choice(
        raw.get("answers") or {}, "skill", set(WRITE_SKILLS), "none"
    )
    if pick == "none" or conf < 0.55:
        return []
    return [pick]


def skill_prompt_block(names: list[str]) -> str:
    # writer-practices is already the writer/agent contract; do not re-hint it.
    names = [name for name in names[:3] if name and name != "writer-practices"]
    if not names:
        return ""
    lines = ["\n---\nWRITE SKILLS (read SKILL.md and follow):\n"]
    for name in names:
        lines.append(f"- {name}: ~/.agents/skills/{name}/SKILL.md\n")
    return "".join(lines)


def persist_run_risk(run_dir: Path, risk: str) -> None:
    if risk not in {"low", "medium", "high"}:
        return
    path = run_dir / "run.yaml"
    if not path.is_file():
        return
    try:
        import yaml
    except ImportError:
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(data, dict):
        return
    data["risk"] = risk
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


GROK_EFFORTS = ("low", "medium", "high")
RISK_TO_GROK_EFFORT = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "high",
}

EMERGENCY_EFFORTS = {"medium", "high", "xhigh"}
RAW_TASK_MARKER = "--- RAW TASK YAML (verbatim) ---"


def _emergency_task_text(task_prompt: str) -> str:
    if RAW_TASK_MARKER in task_prompt:
        raw = task_prompt.split(RAW_TASK_MARKER, 1)[1]
        if raw.startswith("\r\n"):
            return raw[2:]
        if raw.startswith("\n"):
            return raw[1:]
        return raw
    return task_prompt


def classify_emergency_effort(
    task_prompt: str, configured_effort: str
) -> dict[str, Any]:
    """Pick one Codex effort for the emergency writer; fail open to config."""
    configured = str(configured_effort)

    def fallback(reason: str) -> dict[str, Any]:
        return {
            "chosen_effort": configured,
            "configured_effort": configured,
            "source": "configured",
            "fallback_reason": reason,
            "confidence": 0.0,
        }

    try:
        fulltask = _emergency_task_text(task_prompt)
        raw = call_jev(
            {"task_prompt": fulltask},
            {
                "effort": {
                    "type": "choice",
                    "instructions": "Which reasoning effort matches this task's complexity?",
                    "criteria": {
                        "medium": "A focused, local change with a clear implementation path",
                        "high": "A multi-file change or task requiring meaningful debugging and verification",
                        "xhigh": "A complex, risky, or deeply ambiguous task requiring extensive reasoning",
                    },
                }
            },
            timeout=3,
            title="lane-stack emergency-effort-jev",
        )
    except JevCritiqueError as exc:
        marker = str(exc).lower()
        if "api key missing" in marker or (
            marker.startswith("typesafe_api_key or openrouter_api_key")
            and marker.endswith("missing")
        ):
            return fallback("missing_api_key")
        return fallback("request_failed")
    except Exception:
        return fallback("request_failed")

    if not isinstance(raw, dict) or not isinstance(raw.get("answers"), dict):
        return fallback("invalid_response")
    answer = raw["answers"].get("effort")
    if not isinstance(answer, dict) or answer.get("type") != "choice":
        return fallback("invalid_response")
    answer_choice = answer.get("choice")
    if (
        not isinstance(answer_choice, str)
        or answer_choice.strip().lower() not in EMERGENCY_EFFORTS
    ):
        return fallback("invalid_response")
    raw_confidence = answer.get("confidence")
    if (
        isinstance(raw_confidence, bool)
        or not isinstance(raw_confidence, (int, float))
    ):
        return fallback("invalid_response")
    picked, confidence = choice(
        raw["answers"], "effort", EMERGENCY_EFFORTS, configured
    )
    if (
        picked not in EMERGENCY_EFFORTS
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        return fallback("invalid_response")
    return {
        "chosen_effort": picked,
        "configured_effort": configured,
        "source": "jev",
        "fallback_reason": None,
        "confidence": confidence,
    }


def _jev_effort_enabled() -> bool:
    return os.environ.get("LANE_JEV_EFFORT", "1") not in {"0", "off", "false"}


def read_run_risk(run_dir: Path) -> str | None:
    path = run_dir / "run.yaml"
    if not path.is_file():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    risk = data.get("risk")
    if isinstance(risk, str) and risk in RISK_TO_GROK_EFFORT:
        return risk
    return None


def grok_effort_from_run(run_dir: Path, current: str) -> str:
    """Map plan_critique risk on run.yaml to Grok --reasoning-effort."""
    fallback = current if current in GROK_EFFORTS else "medium"
    if not _jev_effort_enabled():
        return fallback
    risk = read_run_risk(run_dir)
    if risk is None:
        return fallback
    return RISK_TO_GROK_EFFORT[risk]


def bump_grok_effort(current: str) -> str:
    """Retry +1 notch, cap high. Fail-open medium if current is unknown."""
    if current not in GROK_EFFORTS:
        return "medium"
    if not _jev_effort_enabled():
        return current
    return GROK_EFFORTS[min(GROK_EFFORTS.index(current) + 1, len(GROK_EFFORTS) - 1)]

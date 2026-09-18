#!/usr/bin/env python3
"""Jev judges for night findings, verify tail, brief risk, intent, QA report."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from jev_decisions import JevCritiqueError, call_jev, choice, clip, noul

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
    for index, (fp, item) in enumerate(open_items[:12]):
        rows.append(
            {
                "i": index,
                "title": item.get("title"),
                "summary": clip(str(item.get("summary") or ""), 400),
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
    for index, (fp, item) in enumerate(open_items[:12]):
        if noul(answers, f"f{index}_real") >= DISMISS_CUT:
            continue
        item["actionable"] = False
        item["status"] = "dismissed"
        dismissed.append(fp)
    return dismissed


def classify_verify_tail(detail: str) -> str | None:
    """Refine leftover verification_failed. None = keep regex result."""
    text = clip(detail or "", 1500)
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
        {"brief": clip(brief, 2000)},
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
        {"query": clip(query, 500)},
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
        {"report": clip(report, 4000), "codex_verdict": verdict},
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

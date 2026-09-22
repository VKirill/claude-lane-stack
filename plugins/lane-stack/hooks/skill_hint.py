#!/usr/bin/env python3
"""UserPromptSubmit fallback when `sr` is missing. Same catalog as OpenCode skill-hint."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent
CATALOG = HOOK / "write-skills.json"


def _bin_paths() -> list[Path]:
    home = Path.home()
    plugin = Path(__file__).resolve().parents[1]
    stack = Path(__file__).resolve().parents[3]
    return [
        home / ".agents" / "bin",
        stack / "bin",
        plugin / ".." / ".." / "bin",
    ]


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "").strip()
    if not prompt:
        return 0
    try:
        skills = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(skills, dict) or not skills:
        return 0
    for folder in _bin_paths():
        if (folder / "jev_decisions.py").is_file():
            sys.path.insert(0, str(folder))
            break
    else:
        return 0
    try:
        from jev_decisions import call_jev, choice
    except Exception:
        return 0
    try:
        answers = call_jev(
            {"task": prompt[:1500]},
            {
                "skill": {
                    "type": "choice",
                    "instructions": "Which write skill should the implementer follow for this task?",
                    "criteria": skills,
                }
            },
            timeout=2,
            title="lane-stack skill-hint",
        )["answers"]
    except Exception:
        return 0
    picked, conf = choice(answers, "skill", set(skills), "none")
    if picked == "none" or conf < 0.55:
        return 0
    note = (
        f"[lane-stack skill] {picked} (conf {conf:.2f}). "
        f"Load ~/.agents/skills/{picked}/SKILL.md if it fits."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": note,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

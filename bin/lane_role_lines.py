#!/usr/bin/env python3
"""Installer helpers: keep the role lines a person appended, and the transitional /gsd-* command aliases.

  lane_role_lines.py save <agents dir> <stash>      the tails below «<!-- lane-stack:user -->» of every role file
  lane_role_lines.py restore <agents dir> <stash>   appended back after the reinstall wrote the new role files
  lane_role_lines.py gsd <commands dir> <0|1>       /gsd-* aliases on (1) or the ones we made removed (0)
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "<!-- lane-stack:user -->"
GSD_MARK = "<!-- lane-stack:gsd-alias -->"
GSD = {
    "gsd-plan-phase": "Plan the phase with lane-plan (CONTEXT, SPEC, PLAN from templates) and hand it to the Lane Pilot phase driver (lane_pilot_phase).",
    "gsd-execute-phase": "Execute the phase: the Lane Pilot phase driver issues the plan wave by wave (lane_pilot_phase).",
    "gsd-verify-work": "Verify the work: Lane Pilot run-goal and the phase verification stage; write VERIFICATION.md with lane-plan template fill.",
    "gsd-progress": "Show progress: lane-plan roadmap analyze and the Lane Pilot task board.",
    "gsd-debug": "Open a debug session: lane-plan debug new \"<symptom>\", one hypothesis at a time.",
    "gsd-discuss-phase": "Discuss the phase: lane-plan template fill CONTEXT --phase <n>, log each exchange with lane-plan discuss.",
    "gsd-new-project": "Start a project: lane-plan template fill ROADMAP, STATE and REQUIREMENTS, then /lane-stack:project-onboard.",
}


def save(agents: Path, stash: Path) -> None:
    for path in agents.rglob("*.md") if agents.is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        if MARK in text:
            tail = text.split(MARK, 1)[1]
            if tail.strip():
                dest = stash / path.relative_to(agents)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(tail, encoding="utf-8")


def restore(agents: Path, stash: Path) -> None:
    for kept in stash.rglob("*.md") if stash.is_dir() else []:
        path = agents / kept.relative_to(stash)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        head = text.split(MARK, 1)[0].rstrip("\n")
        path.write_text(f"{head}\n\n{MARK}{kept.read_text(encoding='utf-8')}", encoding="utf-8")


def gsd(commands: Path, on: bool) -> None:
    commands.mkdir(parents=True, exist_ok=True)
    for name, body in GSD.items():
        path = commands / f"{name}.md"
        ours = path.is_file() and GSD_MARK in path.read_text(encoding="utf-8", errors="replace")
        if on and (ours or not path.exists()):
            path.write_text(f"---\ndescription: SMA alias — {body.split(':')[0]}\n---\n{GSD_MARK}\n{body}\n\n$ARGUMENTS\n", encoding="utf-8")
        elif not on and ours:
            path.unlink()


if __name__ == "__main__":
    op = sys.argv[1]
    if op == "save":
        save(Path(sys.argv[2]), Path(sys.argv[3]))
    elif op == "restore":
        restore(Path(sys.argv[2]), Path(sys.argv[3]))
    elif op == "gsd":
        gsd(Path(sys.argv[2]), sys.argv[3] == "1")
    else:
        raise SystemExit(f"unknown op {op}")

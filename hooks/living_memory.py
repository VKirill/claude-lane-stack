"""Canonical paths for living project memory (PROGRESS / LESSONS).

Prefer `.agents/<name>` so root cleanups and accidental `rm *.md` do not
wipe session state. Legacy repo-root files are still read; writers migrate
them into `.agents/` on first touch.
"""
from __future__ import annotations

import shutil
from pathlib import Path

PROGRESS = "PROGRESS.md"
LESSONS = "LESSONS.md"
MEMORY_NAMES = (PROGRESS, LESSONS)


def preferred(repo: Path, name: str) -> Path:
    return Path(repo) / ".agents" / name


def legacy(repo: Path, name: str) -> Path:
    return Path(repo) / name


def resolve(repo: Path, name: str) -> Path:
    """Path to read/write: preferred if present, else legacy, else preferred."""
    pref = preferred(repo, name)
    if pref.is_file():
        return pref
    leg = legacy(repo, name)
    if leg.is_file():
        return leg
    return pref


def progress_path(repo: Path) -> Path:
    return resolve(repo, PROGRESS)


def lessons_path(repo: Path) -> Path:
    return resolve(repo, LESSONS)


def migrate_legacy(repo: Path, name: str) -> Path:
    """Ensure living memory lives under `.agents/`. Move legacy root file if needed."""
    pref = preferred(repo, name)
    leg = legacy(repo, name)
    if pref.is_file():
        return pref
    pref.parent.mkdir(parents=True, exist_ok=True)
    if leg.is_file():
        shutil.move(str(leg), str(pref))
        return pref
    return pref


def migrate_all(repo: Path) -> None:
    for name in MEMORY_NAMES:
        migrate_legacy(repo, name)

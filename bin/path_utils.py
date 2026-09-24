#!/usr/bin/env python3
"""Shared path-canonicalization helpers.

On macOS the system temp dir (and other paths) can live under a symlink,
e.g. ``/var/folders/...`` -> ``/private/var/folders/...``. Comparing a path
captured before resolving symlinks (a caller-supplied string, a value read
back from a receipt) against one captured after (``Path.resolve()``,
``os.path.realpath``, ``git rev-parse --show-toplevel``, ``pwd -P``) fails
spuriously unless both sides are canonicalized first.

Use these helpers instead of ad hoc ``==`` on raw path strings whenever the
two sides may have travelled through different resolution paths. This does
not change what gets persisted in receipts/state — only how paths are
compared.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_SKILLS = frozenset({"selfystudio"})
_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def canonical_path(value: str | Path) -> Path:
    """Resolve symlinks the same way ``pwd -P``/``realpath`` would.

    Works even when ``value`` does not (yet) exist: missing trailing
    components are normalized but not required to be real.
    """
    return Path(os.path.realpath(str(value)))


def same_path(a: str | Path, b: str | Path) -> bool:
    """True if two path strings/Paths refer to the same filesystem location."""
    return canonical_path(a) == canonical_path(b)


def find_project_skill(cwd: str | Path, name: str) -> Path | None:
    """Return SKILL.md for a project-local skill, walking up to the git root."""
    if name not in PROJECT_SKILLS or not _SKILL_NAME_RE.fullmatch(name):
        return None
    cur = Path(cwd).expanduser()
    try:
        cur = cur.resolve()
    except OSError:
        return None
    for _ in range(8):
        for rel in (
            Path(".agents") / "skills" / name / "SKILL.md",
            Path(".claude") / "skills" / name / "SKILL.md",
        ):
            hit = cur / rel
            try:
                if hit.is_file():
                    return hit.resolve()
            except OSError:
                continue
        if (cur / ".git").exists():
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None

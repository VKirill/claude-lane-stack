"""Candidate context files for the prompt-time selector.

Claude Code loads MEMORY.md (the index) into every session, but the individual
memory files behind it are only read when Claude decides to read them. winnow
ranks those files against the submitted prompt and injects the relevant ones
up front. Extra directories can be added with WINNOW_CONTEXT_DIRS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from winnow.config import Config

INDEX_NAMES = {"memory.md"}


@dataclass(frozen=True)
class Candidate:
    id: str
    path: Path
    title: str
    description: str
    text: str


def project_slug(cwd: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def project_memory_dir(cwd: str) -> Path | None:
    path = Path.home() / ".claude" / "projects" / project_slug(cwd) / "memory"
    return path if path.is_dir() else None


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    meta: dict[str, str] = {}
    for number, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return meta, "\n".join(lines[number + 1 :])
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return {}, text


def _safe_id(stem: str, taken: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]", "_", stem) or "file"
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    taken.add(candidate)
    return candidate


def load_candidates(cfg: Config, cwd: str) -> list[Candidate]:
    dirs: list[Path] = []
    memory_dir = project_memory_dir(cwd)
    if memory_dir:
        dirs.append(memory_dir)
    dirs.extend(d for d in cfg.context_dirs if d.is_dir())

    taken: set[str] = set()
    candidates: list[Candidate] = []
    for directory in dirs:
        for path in sorted(directory.glob("*.md")):
            if path.name.lower() in INDEX_NAMES:
                continue
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            meta, body = _frontmatter(raw)
            title = meta.get("name") or path.stem
            description = meta.get("description") or body.strip().split("\n", 1)[0]
            candidates.append(Candidate(_safe_id(path.stem, taken), path, title, description, body.strip()))
    return candidates

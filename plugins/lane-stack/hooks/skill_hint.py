#!/usr/bin/env python3
"""UserPromptSubmit fallback when `sr` is missing."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except Exception:  # PyYAML is an existing optional repo dependency.
    yaml = None

HOOK = Path(__file__).resolve().parent
NONE = "No extra skill applies"
MAX_TASK_BYTES = 8_000
MAX_CATALOG_BYTES = 16_000
MAX_FILES_PER_ROOT = 1_000
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    block = "\n".join(lines[1:end])
    if yaml is None:
        return {}
    try:
        data = yaml.safe_load(block)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    values: dict[str, str] = {}
    for key in ("name", "description", "disable-model-invocation"):
        value = data.get(key)
        if isinstance(value, str):
            values[key] = value
        elif isinstance(value, bool):
            values[key] = str(value)
    return values


def _project_root() -> Path | None:
    try:
        current = Path.cwd().resolve()
    except OSError:
        return None
    for path in (current, *current.parents):
        if (path / ".git").exists():
            return path
    return current


def _skill_roots() -> list[Path]:
    roots: list[Path] = []
    project = _project_root()
    if project:
        roots.extend((project / ".claude" / "skills", project / ".agents" / "skills"))
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if plugin:
        roots.append(Path(plugin) / "skills")
    roots.append(HOOK.parent / "skills")
    roots.extend((Path.home() / ".claude" / "skills", Path.home() / ".agents" / "skills"))
    return roots


def _skill_paths(root: Path):
    seen: set[Path] = set()
    count = 0
    for current, directories, files in os.walk(root, followlinks=True):
        try:
            resolved = Path(current).resolve()
        except OSError:
            directories[:] = []
            continue
        if resolved in seen:
            directories[:] = []
            continue
        seen.add(resolved)
        directories.sort()
        for filename in sorted(files):
            if filename != "SKILL.md":
                continue
            yield Path(current) / filename
            count += 1
            if count >= MAX_FILES_PER_ROOT:
                return


def discover_skills(roots: list[Path] | None = None) -> dict[str, dict[str, str]]:
    """Return all eligible skills keyed by frontmatter name."""
    found: dict[str, dict[str, str]] = {}
    blocked: set[str] = set()
    for root in roots or _skill_roots():
        for path in _skill_paths(root):
            meta = _frontmatter(path)
            name = meta.get("name", "").strip()
            description = meta.get("description", "").strip()
            if not name or name == "none" or name in found or name in blocked:
                continue
            disabled = meta.get("disable-model-invocation", "").strip().lower() == "true"
            if disabled:
                blocked.add(name)
                continue
            if not description:
                continue
            blocked.add(name)
            found[name] = {"description": description, "path": str(path)}
    return found


def select_catalog(
    discovered: dict[str, dict[str, str]], task: str = ""
) -> tuple[dict[str, str], dict[str, str]]:
    """Keep a deterministic, byte-bounded Jev catalog ranked by task terms."""
    task_terms = set(TOKEN_RE.findall(task.casefold()))
    names = sorted(discovered)
    if task_terms:
        # ponytail: token overlap is bounded and predictable; add semantic ranking if misses recur.
        def rank(name: str) -> tuple[int, str]:
            name_terms = set(TOKEN_RE.findall(name.casefold()))
            description_terms = set(TOKEN_RE.findall(discovered[name]["description"].casefold()))
            return (-(3 * len(task_terms & name_terms) + len(task_terms & description_terms)), name)

        names.sort(key=rank)
    skills = {"none": NONE}
    paths: dict[str, str] = {}
    for name in names:
        candidate = dict(skills)
        candidate[name] = discovered[name]["description"]
        if len(json.dumps(candidate, ensure_ascii=True).encode("utf-8")) > MAX_CATALOG_BYTES:
            continue
        skills[name] = candidate[name]
        paths[name] = discovered[name]["path"]
    return skills, paths


def _task_view(prompt: str) -> str:
    raw = prompt.encode("utf-8")
    if len(raw) <= MAX_TASK_BYTES:
        return prompt
    return raw[:MAX_TASK_BYTES].decode("utf-8", errors="ignore")


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
    if payload.get("agent_id") or payload.get("agentId"):
        return 0
    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "").strip()
    if not prompt:
        return 0
    task = _task_view(prompt)
    discovered = discover_skills()
    if not discovered:
        return 0
    skills, paths = select_catalog(discovered, task)
    if len(skills) == 1:
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
            {"task": task},
            {
                "skill": {
                    "type": "choice",
                    "instructions": "Which skill best fits the current task? Return none when no skill applies.",
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
    path = paths.get(picked)
    if not path:
        return 0
    note = f"[lane-stack skill] {picked} (conf {conf:.2f}). Load {path} if it fits."
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

#!/usr/bin/env python3
"""Build project HANDOFF.json — short operational truth for day resume.

Day policy: ship fast without LLM review; night-shift owns review/fix.
Handoff is a *projection* of runs + profile + PROGRESS, not a second SoT.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
for _cand in (_HERE.parent / "hooks", Path.home() / ".agents" / "hooks"):
    if (_cand / "living_memory.py").is_file():
        if str(_cand) not in sys.path:
            sys.path.insert(0, str(_cand))
        break
from living_memory import progress_path  # noqa: E402

HANDOFF_SCHEMA = 1
CONTRACT_NO_RETRY_CLASSES = frozenset(
    {
        "verification_script_missing",
        "lane_profile_mismatch",
        "contract_invalid",
    }
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_repo_root(start: Path) -> Path:
    """Resolve main project root (not a linked worktree checkout)."""
    start = start.expanduser().resolve()
    parts = list(start.parts)
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        return Path(*parts[:idx])
    cur = start if start.is_dir() else start.parent
    for candidate in (cur, *cur.parents):
        if (candidate / ".agents").is_dir():
            return candidate
        if candidate.parent == candidate:
            break
    return cur


def classify_verify_failure(detail: str) -> str:
    """Map verify stderr/stdout to a failure_class for retry policy."""
    low = (detail or "").lower()
    if (
        "can't open file" in low
        or "no such file or directory" in low
        or "script not found under cwd" in low
    ):
        return "verification_script_missing"
    if "lane " in low and "main_write" in low:
        return "lane_profile_mismatch"
    if "verification[" in low and "must" in low:
        return "contract_invalid"
    return "verification_failed"


def next_act_for_failure(failure_class: str | None) -> str:
    if failure_class in CONTRACT_NO_RETRY_CLASSES:
        return "fix_contract"
    if failure_class in {"provider_incomplete", "runtime_identity_mismatch"}:
        return "fix_control_plane"
    if failure_class == "verification_failed":
        return "inspect_verify"
    if failure_class in {"provider_failed", "provider_exit_nonzero"}:
        return "retry_or_fallback"
    return "operator_intervention"


def _parse_profile(repo: Path) -> dict[str, Any]:
    path = repo / ".agents" / "routing.profile.yaml"
    out: dict[str, Any] = {
        "main_write": None,
        "model": None,
        "effort": None,
        "workspace_mode": "auto",
    }
    if not path.is_file():
        return out
    try:
        section = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line in {"lanes:", "writer:", "workspace:", "ui:"}:
                section = line[:-1]
                continue
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip().split("#")[0].strip().strip("\"'")
            if section == "lanes" and key == "main_write":
                out["main_write"] = val
            elif section == "writer" and key == "model":
                out["model"] = val
            elif section == "writer" and key in {"reasoning_effort", "effort"}:
                out["effort"] = val
            elif section == "workspace" and key == "mode":
                out["workspace_mode"] = val
            elif key == "main_write" and section is None:
                out["main_write"] = val
    except OSError:
        pass
    return out


def _progress_now(repo: Path) -> str:
    path = progress_path(repo)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # ## Now section, first non-empty bullet/line
    m = re.search(r"(?m)^##\s+Now\s*$", text)
    if not m:
        return ""
    rest = text[m.end() :]
    for line in rest.splitlines():
        if line.startswith("## "):
            break
        s = line.strip().lstrip("-* ").strip()
        if s and not s.startswith("<!--"):
            return s[:200]
    return ""


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _scan_runs(repo: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (active, blocked_items, next_actions)."""
    runs_root = repo / ".agents" / "runs"
    active: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    next_actions: list[dict[str, Any]] = []
    if not runs_root.is_dir():
        return active, blocked, next_actions

    for run_dir in sorted(runs_root.iterdir(), key=lambda p: p.name):
        if not run_dir.is_dir() or run_dir.name.startswith("."):
            continue
        slug = run_dir.name
        if slug in {"BOARD.md"}:
            continue
        controller = _load_json(run_dir / "controller.json")
        run_yaml_repo = None
        run_path = run_dir / "run.yaml"
        if run_path.is_file():
            try:
                for line in run_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("repo:"):
                        run_yaml_repo = line.split(":", 1)[1].strip().strip("\"'")
                        break
            except OSError:
                pass

        if controller is None:
            # planning-only run
            if (run_dir / "tasks").is_dir() and not (run_dir / "merge.json").is_file():
                active.append(
                    {
                        "slug": slug,
                        "stage": "planning",
                        "run_dir": str(run_dir),
                    }
                )
            continue

        stage = str(controller.get("stage") or "unknown")
        project_cwd = controller.get("project_cwd")
        entry: dict[str, Any] = {
            "slug": slug,
            "stage": stage,
            "run_dir": str(run_dir),
            "project_cwd": project_cwd,
            "counts": controller.get("counts"),
            "next_action": controller.get("next_action"),
        }
        if run_yaml_repo:
            entry["repo"] = run_yaml_repo

        tasks = controller.get("tasks")
        if not isinstance(tasks, dict):
            tasks = {}

        terminal = stage in {"accepted", "blocked", "failed"}
        runningish = stage not in {"accepted", "blocked", "failed"} or any(
            isinstance(t, dict)
            and t.get("stage") not in {"accepted", "blocked", "pending", None}
            for t in tasks.values()
        )

        if stage == "accepted":
            # fully done — only surface if not finalized
            if not (run_dir / "finalize.json").is_file() and not (
                run_dir / "merge.json"
            ).is_file():
                next_actions.append(
                    {
                        "action": "merge",
                        "run": slug,
                        "reason": "all tasks accepted; ship to main",
                    }
                )
                active.append(entry)
            continue

        has_blocked_task = any(
            isinstance(t, dict) and t.get("stage") == "blocked" for t in tasks.values()
        )
        if stage in {"blocked", "failed"} or has_blocked_task:
            for tid, tstate in tasks.items():
                if not isinstance(tstate, dict) or tstate.get("stage") != "blocked":
                    continue
                fc = tstate.get("last_failure_class")
                if not isinstance(fc, str):
                    fc = None
                outcome = _load_json(run_dir / "artifacts" / str(tid) / "outcome.json")
                if outcome and isinstance(outcome.get("failure_class"), str):
                    fc = outcome["failure_class"] or fc
                # Prefer concrete class from verify output (missing check.py etc.)
                if fc in {None, "verification_failed"}:
                    for att in ("02", "01"):
                        vpath = (
                            run_dir
                            / "artifacts"
                            / str(tid)
                            / "attempts"
                            / att
                            / "verification.json"
                        )
                        vj = _load_json(vpath)
                        if not vj:
                            continue
                        cmds = vj.get("commands")
                        if isinstance(cmds, list) and cmds:
                            out = str(cmds[0].get("output") or "")
                            if out:
                                refined = classify_verify_failure(out)
                                if refined != "verification_failed":
                                    fc = refined
                                break
                blocked.append(
                    {
                        "run": slug,
                        "task": str(tid),
                        "stage": "blocked",
                        "failure_class": fc,
                        "next_act": next_act_for_failure(fc),
                        "provider": tstate.get("provider"),
                    }
                )
                next_actions.append(
                    {
                        "action": next_act_for_failure(fc),
                        "run": slug,
                        "task": str(tid),
                        "reason": fc or "blocked",
                    }
                )
            if stage in {"blocked", "failed"} and not any(
                b.get("run") == slug for b in blocked
            ):
                blocked.append(
                    {
                        "run": slug,
                        "task": None,
                        "stage": stage,
                        "failure_class": None,
                        "next_act": "operator_intervention",
                    }
                )
                next_actions.append(
                    {
                        "action": "operator_intervention",
                        "run": slug,
                        "reason": stage,
                    }
                )
            # Terminal blocked/failed runs stay out of "active" (listed under Blocked).
            continue

        if runningish or stage in {
            "running",
            "degraded",
            "dispatching",
            "pending",
        }:
            active.append(entry)
            next_actions.append(
                {
                    "action": "watch_run",
                    "run": slug,
                    "reason": f"stage={stage}",
                }
            )

    # de-dupe next by (action, run, task)
    seen: set[tuple[Any, ...]] = set()
    unique_next: list[dict[str, Any]] = []
    for item in next_actions:
        key = (item.get("action"), item.get("run"), item.get("task"))
        if key in seen:
            continue
        seen.add(key)
        unique_next.append(item)
    return active, blocked, unique_next[:8]


def build_handoff(repo: Path) -> dict[str, Any]:
    repo = find_repo_root(repo)
    profile = _parse_profile(repo)
    active, blocked, next_actions = _scan_runs(repo)
    now = _progress_now(repo)
    if not now:
        if active:
            a0 = active[0]
            now = f"run {a0['slug']} stage={a0.get('stage')}"
        elif blocked:
            now = f"blocked: {blocked[0]['run']}"
        else:
            now = "idle — no active runs"

    if not next_actions and not active and not blocked:
        next_actions = [
            {
                "action": "idle",
                "reason": "no active runs; day path free for new work",
            }
        ]

    return {
        "schema_version": HANDOFF_SCHEMA,
        "updated_at": utc_now(),
        "repo": str(repo),
        "day_policy": "fast write + L1 verify + accept; LLM review at night only",
        "profile": profile,
        "now": now,
        "blocked": blocked,
        "active_runs": active,
        "next": next_actions,
    }


def render_handoff_md(data: dict[str, Any]) -> str:
    lines = [
        "# HANDOFF",
        "",
        f"_Updated {data.get('updated_at', '')}_",
        "",
        f"**Now:** {data.get('now', '')}",
        "",
        f"**Day policy:** {data.get('day_policy', '')}",
        "",
    ]
    prof = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    lines.append(
        "**Profile:** "
        f"main_write={prof.get('main_write') or '—'} "
        f"model={prof.get('model') or '—'} "
        f"workspace={prof.get('workspace_mode') or '—'}"
    )
    lines.append("")
    lines.append("## Blocked")
    blocked = data.get("blocked") if isinstance(data.get("blocked"), list) else []
    if not blocked:
        lines.append("- (none)")
    else:
        for item in blocked:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('run')}` task {item.get('task')}: "
                f"{item.get('failure_class') or item.get('stage')} "
                f"→ **{item.get('next_act')}**"
            )
    lines.append("")
    lines.append("## Active runs")
    active = data.get("active_runs") if isinstance(data.get("active_runs"), list) else []
    if not active:
        lines.append("- (none)")
    else:
        for item in active:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('slug')}` stage={item.get('stage')} "
                f"next={item.get('next_action')}"
            )
    lines.append("")
    lines.append("## Next")
    nxt = data.get("next") if isinstance(data.get("next"), list) else []
    if not nxt:
        lines.append("- idle")
    else:
        for item in nxt:
            if not isinstance(item, dict):
                continue
            extra = ""
            if item.get("run"):
                extra += f" run={item['run']}"
            if item.get("task"):
                extra += f" task={item['task']}"
            lines.append(
                f"- **{item.get('action')}**{extra}"
                + (f" — {item.get('reason')}" if item.get("reason") else "")
            )
    lines.append("")
    lines.append(
        "_Regenerate: `handoff-write .` · Full dump: `resume-project .` · "
        "Compact: `resume-project . --compact`_"
    )
    lines.append("")
    return "\n".join(lines)


def write_handoff(repo: Path) -> Path:
    """Write `.agents/HANDOFF.json` + `.agents/HANDOFF.md`. Return json path."""
    repo = find_repo_root(repo)
    data = build_handoff(repo)
    agents = repo / ".agents"
    agents.mkdir(parents=True, exist_ok=True)
    json_path = agents / "HANDOFF.json"
    md_path = agents / "HANDOFF.md"
    json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_handoff_md(data), encoding="utf-8")
    return json_path

#!/usr/bin/env python3
"""Full-screen TUI for agents-doctor — coder / model / effort / night config.

Layout (single column, no fragile box-drawing):
  header · tabs · body · summary strip · footer

Keyboard-first, beginner-friendly. Requires prompt_toolkit.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable


APP_TITLE = "Lane Stack · Project Setup"

# Default catalogs (stack defaults + common options).
WRITER_MODELS: dict[str, list[str]] = {
    "qwen": [
        "qwen3.8-max-preview",
        "qwen3.7-max",
        "qwen3.7-plus",
        "qwen3.6-plus",
        "qwen3.6-flash",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "kimi-k2.7-code",
    ],
    "kimi": ["kimi-code/k3-256k"],
    "grok": ["grok-4.5"],
    "agy": ["gemini-3.6-flash-high"],
    "codex": ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"],
    "auto": ["(stack default)"],
}

WRITER_EFFORTS: dict[str, list[str]] = {
    "qwen": ["low", "medium", "high"],
    "kimi": ["low", "medium", "high"],
    "grok": ["low", "medium", "high"],
    "agy": ["low", "medium", "high"],
    "codex": ["low", "medium", "high", "xhigh", "max"],
    "auto": ["medium"],
}

WRITER_META: dict[str, dict[str, str]] = {
    "qwen": {
        "title": "Qwen",
        "badge": "FAST",
        "blurb": "Fast everyday coder for product work",
    },
    "kimi": {
        "title": "Kimi",
        "badge": "LONG CTX",
        "blurb": "Long-context Kimi K3 (256k)",
    },
    "grok": {
        "title": "Grok",
        "badge": "XAI",
        "blurb": "xAI Grok writer lane",
    },
    "agy": {
        "title": "AGY",
        "badge": "GEMINI",
        "blurb": "Gemini Flash high via AGY",
    },
    "codex": {
        "title": "Codex",
        "badge": "OPENAI",
        "blurb": "Bare Codex lane-writer (no host MCP/plugins)",
    },
    "auto": {
        "title": "Auto",
        "badge": "STACK",
        "blurb": "First available: Kimi → Qwen → Grok → AGY",
    },
}

DEFAULT_MODEL = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.6-flash-high",
    "codex": "gpt-5.6-luna",
    "auto": "(stack default)",
}

DEFAULT_EFFORT = {
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
    "codex": "max",
    "auto": "medium",
}

TAB_META = [
    ("coder", "Coder", "CLI + model + effort"),
    ("night", "Night", "Review & repair"),
    ("status", "Status", "Host CLIs"),
    ("apply", "Apply", "Save to project"),
]


class SetupState:
    def __init__(
        self,
        repo: Path,
        tools: dict[str, Any],
        writers: list[str],
        writer: str,
        model: str,
        effort: str,
        night_review: bool = False,
        night_provider: str = "qwen",
        max_fix_tasks: int = 5,
        auto_merge: bool = False,
        message: str = "",
        last_apply: str = "",
        cursor: int = 0,
        focus: str = "writer",  # writer | model | effort | night_writer
    ) -> None:
        self.repo = repo
        self.tools = tools
        self.writers = writers
        self.writer = writer
        self.model = model
        self.effort = effort
        self.night_review = night_review
        self.night_provider = night_provider
        self.max_fix_tasks = max_fix_tasks
        self.auto_merge = auto_merge
        self.message = message
        self.last_apply = last_apply
        self.cursor = cursor
        self.focus = focus


def _load_existing(repo: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    route = repo / ".agents" / "routing.profile.yaml"
    night = repo / ".agents" / "night-shift.yaml"
    if route.is_file():
        try:
            section = None
            for line in route.read_text(encoding="utf-8").splitlines():
                raw = line.rstrip()
                s = raw.strip()
                if s.startswith("main_write:"):
                    out["writer"] = s.split(":", 1)[1].strip().split()[0]
                if s == "writer:" or s.startswith("writer:"):
                    section = "writer"
                    continue
                if section == "writer":
                    if raw and not raw.startswith(" ") and not raw.startswith("\t"):
                        section = None
                    elif s.startswith("provider:"):
                        out["writer"] = s.split(":", 1)[1].strip().split()[0]
                    elif s.startswith("model:"):
                        out["model"] = s.split(":", 1)[1].strip().strip("\"'")
                    elif s.startswith("reasoning_effort:") or s.startswith("effort:"):
                        out["effort"] = s.split(":", 1)[1].strip().split()[0]
        except OSError:
            pass
    if night.is_file():
        try:
            for line in night.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("enabled:"):
                    out["night_review"] = "true" in s.lower()
                elif s.startswith("provider:"):
                    out["night_provider"] = s.split(":", 1)[1].strip().split()[0]
                elif s.startswith("max_fix_tasks:"):
                    try:
                        out["max_fix_tasks"] = int(s.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif s.startswith("auto_merge:"):
                    out["auto_merge"] = "true" in s.lower()
        except OSError:
            pass
    return out


def _switch(on: bool) -> str:
    return "[ ON ]" if on else "[ off ]"


def _radio(selected: bool) -> str:
    return "●" if selected else "○"


def _models_for(writer: str) -> list[str]:
    return list(WRITER_MODELS.get(writer, ["(default)"]))


def _efforts_for(writer: str) -> list[str]:
    return list(WRITER_EFFORTS.get(writer, ["medium"]))


def _ensure_model(writer: str, model: str) -> str:
    opts = _models_for(writer)
    if model in opts:
        return model
    return DEFAULT_MODEL.get(writer, opts[0])


def _ensure_effort(writer: str, effort: str) -> str:
    opts = _efforts_for(writer)
    if effort in opts:
        return effort
    return DEFAULT_EFFORT.get(writer, opts[0])


def run_tui(repo: Path, doctor: Any) -> int:
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
        from prompt_toolkit.styles import Style
    except ImportError:
        print(
            "TUI needs prompt_toolkit. Falling back to: agents-doctor setup",
            file=sys.stderr,
        )
        return doctor.run_setup(repo, interactive=True)

    tools = doctor.detect()
    if not tools.get("claude", {}).get("present"):
        print("ERROR: Claude Code is required as PM.", file=sys.stderr)
        return 1

    writers = list(doctor.available_writers(tools))
    if tools.get("codex", {}).get("present") and "codex" not in writers:
        writers.append("codex")
    if not writers:
        writers = ["auto"]

    suggested = doctor.default_setup_writer(tools)
    existing = _load_existing(repo)
    writer0 = existing.get("writer")
    if writer0 not in writers:
        writer0 = suggested if suggested in writers else writers[0]
    model0 = _ensure_model(writer0, existing.get("model") or DEFAULT_MODEL.get(writer0, ""))
    effort0 = _ensure_effort(
        writer0, existing.get("effort") or DEFAULT_EFFORT.get(writer0, "medium")
    )
    night_w0 = existing.get("night_provider")
    if night_w0 not in writers:
        night_w0 = writer0 if writer0 != "auto" else writers[0]

    state = SetupState(
        repo=repo,
        tools=tools,
        writers=writers,
        writer=writer0,
        model=model0,
        effort=effort0,
        night_review=bool(existing.get("night_review", False)),
        night_provider=night_w0,
        max_fix_tasks=int(existing.get("max_fix_tasks", 5)),
        auto_merge=bool(existing.get("auto_merge", False)),
        message="↑↓ coder · m model · e effort · Enter apply · ? help",
        cursor=max(0, writers.index(writer0) if writer0 in writers else 0),
        focus="writer",
    )

    tab_ids = [t[0] for t in TAB_META]
    tab_i = {"i": 0}

    # ── rendering (no fixed-width unicode boxes — they break on narrow terms) ─

    def header() -> list[tuple[str, str]]:
        short = str(state.repo)
        if len(short) > 56:
            short = "…" + short[-55:]
        return [
            ("class:hdr", "  "),
            ("class:brand", "◆ LANE"),
            ("class:hdr", "  "),
            ("class:hdr-title", APP_TITLE),
            ("class:hdr", "\n"),
            ("class:hdr-sub", f"  {short}"),
            ("class:hdr", "\n"),
        ]

    def tabs() -> list[tuple[str, str]]:
        parts: list[tuple[str, str]] = [("class:tabbar", " ")]
        for i, (_tid, label, _sub) in enumerate(TAB_META):
            on = i == tab_i["i"]
            st = "class:tab-on" if on else "class:tab-off"
            arrow = "▸" if on else " "
            parts.append((st, f" {arrow}{i + 1}.{label} "))
            parts.append(("class:tabbar", " "))
        parts.append(("class:tabbar", "\n"))
        _, label, sub = TAB_META[tab_i["i"]]
        parts.append(("class:tab-hint", f"  {label} — {sub}\n"))
        return parts

    def summary_strip() -> list[tuple[str, str]]:
        meta = WRITER_META.get(state.writer, {})
        night = "night:ON" if state.night_review else "night:off"
        return [
            ("class:sum", "  "),
            ("class:sum-label", "coder "),
            ("class:sum-hi", f"{meta.get('title', state.writer)}"),
            ("class:sum", "  "),
            ("class:sum-dim", state.model),
            ("class:sum", "  "),
            ("class:sum-dim", f"effort:{state.effort}"),
            ("class:sum", "  ·  "),
            ("class:sum-on" if state.night_review else "class:sum-dim", night),
            ("class:sum", "\n"),
        ]

    def body_coder() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", "  Daytime coder\n"),
            (
                "class:help",
                "  Who implements task YAML. Claude remains PM/orchestrator.\n\n",
            ),
            ("class:h2", "  Provider  (↑↓)\n"),
        ]
        for i, w in enumerate(state.writers):
            meta = WRITER_META.get(w, {"title": w, "badge": "?", "blurb": ""})
            selected = w == state.writer
            focused = state.focus == "writer" and i == state.cursor
            if selected and focused:
                st = "class:row-on-focus"
            elif selected:
                st = "class:row-on"
            elif focused:
                st = "class:row-focus"
            else:
                st = "class:row"
            mark = _radio(selected)
            active = "  ✓" if selected else ""
            # Single line — no box drawing
            title = f"{meta.get('title', w)}"
            badge = meta.get("badge", "")
            lines.append(
                (st, f"  {mark}  {title:<10}  {badge:<8}{active}\n")
            )
            if selected:
                lines.append(
                    ("class:row-detail", f"      {meta.get('blurb', '')}\n")
                )

        lines.append(("class:h2", "\n  Model for this coder  (m / M cycle · [ ])\n"))
        models = _models_for(state.writer)
        # show compact: current + neighbors
        try:
            mi = models.index(state.model)
        except ValueError:
            mi = 0
            state.model = models[0]
        focus_m = state.focus == "model"
        st_m = "class:row-on-focus" if focus_m else "class:row-on"
        lines.append((st_m, f"  ▸  {state.model}\n"))
        if len(models) > 1:
            lines.append(
                (
                    "class:help",
                    f"      {mi + 1}/{len(models)} available · "
                    f"prev {models[(mi - 1) % len(models)][:28]}\n",
                )
            )

        lines.append(("class:h2", "\n  Reasoning effort  (e / E cycle · { })\n"))
        efforts = _efforts_for(state.writer)
        try:
            ei = efforts.index(state.effort)
        except ValueError:
            ei = 0
            state.effort = efforts[0]
        focus_e = state.focus == "effort"
        st_e = "class:row-on-focus" if focus_e else "class:row-on"
        bar = "·".join(
            (f"[{x}]" if x == state.effort else x) for x in efforts
        )
        lines.append((st_e, f"  ▸  {state.effort}\n"))
        lines.append(("class:help", f"      {bar}\n"))

        lines.append(
            (
                "class:help",
                "\n  Focus: Tab field  ·  m model  ·  e effort  ·  "
                "Enter → Apply tab\n",
            )
        )
        return lines

    def body_night() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", "  Night shift\n"),
            (
                "class:help",
                "  Optional Codex Sol review + bounded fix tasks via cron.\n"
                "  Keep OFF for simple/static sites.\n\n",
            ),
            (
                "class:row-on" if state.night_review else "class:row",
                f"  {_switch(state.night_review)}  Night review + repair"
                f"     [Space]\n\n",
            ),
        ]
        if not state.night_review:
            lines.append(
                ("class:dim", "  Night disabled → enabled: false in night-shift.yaml\n")
            )
            return lines

        bar = "●" * state.max_fix_tasks + "○" * (10 - state.max_fix_tasks)
        lines.append(("class:h2", "  Fix budget  (+/-)\n"))
        lines.append(
            ("class:row", f"  max_fix_tasks = {state.max_fix_tasks} / 10\n")
        )
        lines.append(("class:dim", f"  {bar}\n\n"))

        lines.append(("class:h2", "  Auto-merge  (a)\n"))
        lines.append(
            (
                "class:row-on" if state.auto_merge else "class:row",
                f"  {_switch(state.auto_merge)}  Merge to main when green"
                f"  (usually OFF)\n\n",
            )
        )

        lines.append(("class:h2", "  Night fix writer  (n, ↑↓)\n"))
        opts = [w for w in state.writers if w != "auto"]
        for i, w in enumerate(opts):
            meta = WRITER_META.get(w, {"title": w})
            selected = w == state.night_provider
            focused = state.focus == "night_writer" and i == state.cursor
            if selected and focused:
                st = "class:row-on-focus"
            elif selected:
                st = "class:row-on"
            elif focused:
                st = "class:row-focus"
            else:
                st = "class:row"
            lines.append(
                (st, f"  {_radio(selected)}  {meta.get('title', w):<10}  {w}\n")
            )
        return lines

    def body_status() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", "  Host tooling\n"),
            ("class:help", "  Green = ready for writer lanes.\n\n"),
        ]
        order = ["claude", "qwen", "kimi", "grok", "agy", "codex", "bubblewrap"]
        seen: set[str] = set()
        for name in order + list(state.tools):
            if name in seen or name not in state.tools:
                continue
            seen.add(name)
            info = state.tools[name]
            ok = bool(info.get("present"))
            st = "class:ok" if ok else "class:bad"
            ver = (info.get("version") or "")[:36]
            req = " · required" if info.get("required") else ""
            lines.append((st, f"  {'✓' if ok else '✗'}  {name:<12} {ver}{req}\n"))
            reason = info.get("unavailable_reason")
            if reason and not ok:
                lines.append(("class:warn", f"       {reason}\n"))
        profile, lanes, notes = doctor.pick_profile(state.tools, state.writer)
        lines.append(("class:h2", f"\n  Profile preview · {profile}\n"))
        for k, v in (lanes or {}).items():
            lines.append(("class:dim", f"    {k:<16} {v}\n"))
        lines.append(("class:dim", f"    model            {state.model}\n"))
        lines.append(("class:dim", f"    reasoning_effort {state.effort}\n"))
        if notes:
            lines.append(("class:warn", "\n  Notes\n"))
            for n in notes:
                lines.append(("class:warn", f"    · {n}\n"))
        lines.append(("class:help", "\n  r  rescan CLIs\n"))
        return lines

    def body_apply() -> list[tuple[str, str]]:
        profile, lanes, _ = doctor.pick_profile(state.tools, state.writer)
        meta = WRITER_META.get(state.writer, {})
        lines: list[tuple[str, str]] = [
            ("class:h1", "  Save to this project\n"),
            (
                "class:help",
                "  Writes routing + night-shift. Safe to re-run anytime.\n\n",
            ),
            ("class:h2", "  Summary\n"),
            ("class:row-on", f"  project   {state.repo}\n"),
            (
                "class:row-on",
                f"  coder     {meta.get('title', state.writer)}  ({state.writer})\n",
            ),
            ("class:row-on", f"  model     {state.model}\n"),
            ("class:row-on", f"  effort    {state.effort}\n"),
            (
                "class:row-on",
                f"  night     {'ON' if state.night_review else 'off'}"
                + (
                    f"  fix={state.night_provider}  max={state.max_fix_tasks}"
                    if state.night_review
                    else ""
                )
                + "\n",
            ),
            ("class:row-on", f"  profile   {profile}\n\n"),
            ("class:h2", "  Files\n"),
            ("class:dim", "    .agents/routing.profile.yaml\n"),
            ("class:dim", "    .agents/capabilities.json\n"),
            ("class:dim", "    .agents/night-shift.yaml\n\n"),
            ("class:accent", "  ╔══════════════════════════════════╗\n"),
            ("class:accent", "  ║   ENTER  ·  Apply configuration  ║\n"),
            ("class:accent", "  ╚══════════════════════════════════╝\n"),
        ]
        if state.last_apply:
            lines.append(("class:ok", f"\n  ✓ {state.last_apply}\n"))
        lines.append(
            (
                "class:help",
                "\n  New runs pick up main_write + model/effort.\n"
                "  Already-running tasks keep their old lane until restarted.\n",
            )
        )
        return lines

    bodies: dict[str, Callable[[], list[tuple[str, str]]]] = {
        "coder": body_coder,
        "night": body_night,
        "status": body_status,
        "apply": body_apply,
    }

    def footer() -> list[tuple[str, str]]:
        keys = {
            "coder": "↑↓ provider · m/e model/effort · Tab panels · Enter apply",
            "night": "Space night · a merge · +/- budget · n writer · Enter apply",
            "status": "r rescan · 1-4 tabs · q quit",
            "apply": "ENTER save · q quit",
        }
        tid = tab_ids[tab_i["i"]]
        return [
            ("class:ftr", "  "),
            ("class:ftr-msg", (state.message or "")[:48]),
            ("class:ftr", "  ·  "),
            ("class:ftr-keys", keys.get(tid, "")),
        ]

    def main_view() -> list[tuple[str, str]]:
        return bodies[tab_ids[tab_i["i"]]]()

    # ── actions ───────────────────────────────────────────────────────────

    def set_writer(w: str) -> None:
        state.writer = w
        state.model = _ensure_model(w, DEFAULT_MODEL.get(w, state.model))
        state.effort = _ensure_effort(w, DEFAULT_EFFORT.get(w, state.effort))
        state.message = f"Coder → {WRITER_META.get(w, {}).get('title', w)}"

    def move_writer(delta: int) -> None:
        if not state.writers:
            return
        state.focus = "writer"
        state.cursor = (state.cursor + delta) % len(state.writers)
        set_writer(state.writers[state.cursor])

    def cycle_model(delta: int) -> None:
        opts = _models_for(state.writer)
        if not opts:
            return
        state.focus = "model"
        try:
            i = opts.index(state.model)
        except ValueError:
            i = 0
        state.model = opts[(i + delta) % len(opts)]
        state.message = f"Model → {state.model}"

    def cycle_effort(delta: int) -> None:
        opts = _efforts_for(state.writer)
        if not opts:
            return
        state.focus = "effort"
        try:
            i = opts.index(state.effort)
        except ValueError:
            i = 0
        state.effort = opts[(i + delta) % len(opts)]
        state.message = f"Effort → {state.effort}"

    def move_night_writer(delta: int) -> None:
        opts = [w for w in state.writers if w != "auto"]
        if not opts:
            return
        state.focus = "night_writer"
        try:
            i = opts.index(state.night_provider)
        except ValueError:
            i = 0
        i = (i + delta) % len(opts)
        state.cursor = i
        state.night_provider = opts[i]
        state.message = f"Night fix writer → {state.night_provider}"

    def do_apply() -> None:
        profile, lanes, notes = doctor.pick_profile(state.tools, state.writer)
        model = state.model if state.writer != "auto" else None
        effort = state.effort if state.writer != "auto" else None
        # Prefer write_outputs with model/effort if supported
        write = getattr(doctor, "write_outputs", None)
        if write is None:
            raise RuntimeError("doctor.write_outputs missing")
        try:
            write(
                state.repo,
                state.tools,
                profile,
                lanes,
                notes,
                writer_model=model,
                writer_effort=effort,
            )
        except TypeError:
            # older signature without model/effort
            write(state.repo, state.tools, profile, lanes, notes)
        doctor.write_night_shift(
            state.repo,
            enabled=state.night_review,
            provider=state.night_provider,
            max_fix_tasks=state.max_fix_tasks,
            auto_merge=state.auto_merge if state.night_review else False,
        )
        meta = WRITER_META.get(state.writer, {})
        state.last_apply = (
            f"{meta.get('title', state.writer)} · {state.model} · {state.effort} · "
            f"night={'on' if state.night_review else 'off'}"
        )
        state.message = "✓ Saved. New runs use this coder/model/effort."

    def rescan() -> None:
        state.tools = doctor.detect()
        writers = list(doctor.available_writers(state.tools))
        if state.tools.get("codex", {}).get("present") and "codex" not in writers:
            writers.append("codex")
        state.writers = writers or ["auto"]
        if state.writer not in state.writers:
            set_writer(state.writers[0])
            state.cursor = 0
        state.message = "Host tooling rescanned"

    # ── keys ──────────────────────────────────────────────────────────────

    kb = KeyBindings()

    @kb.add("q")
    @kb.add("c-c")
    def _(event) -> None:
        event.app.exit(result=0)

    @kb.add("tab")
    @kb.add("right")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "coder":
            # cycle focus: writer → model → effort → next tab
            order = ["writer", "model", "effort"]
            try:
                fi = order.index(state.focus)
            except ValueError:
                fi = 0
            if fi < len(order) - 1:
                state.focus = order[fi + 1]
                state.message = f"Focus → {state.focus}"
                return
        tab_i["i"] = (tab_i["i"] + 1) % len(tab_ids)
        state.message = f"Tab · {TAB_META[tab_i['i']][1]}"

    @kb.add("s-tab")
    @kb.add("left")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "coder":
            order = ["writer", "model", "effort"]
            try:
                fi = order.index(state.focus)
            except ValueError:
                fi = 0
            if fi > 0:
                state.focus = order[fi - 1]
                state.message = f"Focus → {state.focus}"
                return
        tab_i["i"] = (tab_i["i"] - 1) % len(tab_ids)
        state.message = f"Tab · {TAB_META[tab_i['i']][1]}"

    for n in range(1, 5):

        @kb.add(str(n))
        def _(event, n=n) -> None:
            tab_i["i"] = n - 1
            if tab_ids[tab_i["i"]] == "coder":
                state.focus = "writer"
            state.message = f"Tab · {TAB_META[tab_i['i']][1]}"

    @kb.add("up")
    @kb.add("k")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "coder":
            if state.focus == "model":
                cycle_model(-1)
            elif state.focus == "effort":
                cycle_effort(-1)
            else:
                move_writer(-1)
        elif tid == "night" and state.night_review:
            move_night_writer(-1)

    @kb.add("down")
    @kb.add("j")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "coder":
            if state.focus == "model":
                cycle_model(1)
            elif state.focus == "effort":
                cycle_effort(1)
            else:
                move_writer(1)
        elif tid == "night" and state.night_review:
            move_night_writer(1)

    @kb.add("m")
    @kb.add("]")
    def _(event) -> None:
        if tab_ids[tab_i["i"]] == "coder":
            cycle_model(1)

    @kb.add("M")
    @kb.add("[")
    def _(event) -> None:
        if tab_ids[tab_i["i"]] == "coder":
            cycle_model(-1)

    @kb.add("e")
    @kb.add("}")
    def _(event) -> None:
        if tab_ids[tab_i["i"]] == "coder":
            cycle_effort(1)

    @kb.add("E")
    @kb.add("{")
    def _(event) -> None:
        if tab_ids[tab_i["i"]] == "coder":
            cycle_effort(-1)

    @kb.add(" ")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "coder":
            if state.focus == "model":
                cycle_model(1)
            elif state.focus == "effort":
                cycle_effort(1)
            else:
                move_writer(0)  # re-affirm
                set_writer(state.writers[state.cursor] if state.writers else state.writer)
        elif tid == "night":
            state.night_review = not state.night_review
            state.message = f"Night → {'ON' if state.night_review else 'off'}"
        elif tid == "apply":
            do_apply()

    @kb.add("enter")
    def _(event) -> None:
        tid = tab_ids[tab_i["i"]]
        if tid == "apply":
            do_apply()
        elif tid == "coder":
            tab_i["i"] = tab_ids.index("apply")
            state.message = "Review & press Enter to save"
        elif tid == "night":
            state.night_review = not state.night_review
            state.message = f"Night → {'ON' if state.night_review else 'off'}"
        else:
            tab_i["i"] = tab_ids.index("apply")

    @kb.add("a")
    def _(event) -> None:
        if state.night_review:
            state.auto_merge = not state.auto_merge
            state.message = f"Auto-merge → {state.auto_merge}"

    @kb.add("n")
    def _(event) -> None:
        if tab_ids[tab_i["i"]] == "night" and state.night_review:
            state.focus = "night_writer"
            opts = [w for w in state.writers if w != "auto"]
            if opts and state.night_provider in opts:
                state.cursor = opts.index(state.night_provider)
            state.message = "Night writer list · ↑↓"

    @kb.add("+")
    @kb.add("=")
    def _(event) -> None:
        if state.night_review:
            state.max_fix_tasks = min(10, state.max_fix_tasks + 1)
            state.message = f"Max fix tasks → {state.max_fix_tasks}"

    @kb.add("-")
    def _(event) -> None:
        if state.night_review:
            state.max_fix_tasks = max(1, state.max_fix_tasks - 1)
            state.message = f"Max fix tasks → {state.max_fix_tasks}"

    @kb.add("r")
    def _(event) -> None:
        rescan()

    @kb.add("?")
    def _(event) -> None:
        state.message = (
            "1 Coder 2 Night 3 Status 4 Apply · m model · e effort · Enter save · q quit"
        )

    # ── layout (single column — no side panel collision) ──────────────────

    root = HSplit(
        [
            Window(content=FormattedTextControl(header), height=2, style="class:hdr"),
            Window(content=FormattedTextControl(tabs), height=2, style="class:tabbar"),
            Window(height=1, char="─", style="class:rule"),
            Window(content=FormattedTextControl(main_view), style="class:main"),
            Window(height=1, char="─", style="class:rule"),
            Window(
                content=FormattedTextControl(summary_strip),
                height=1,
                style="class:sum",
            ),
            Window(content=FormattedTextControl(footer), height=1, style="class:ftr"),
        ]
    )

    style = Style.from_dict(
        {
            "hdr": "bg:#0f111a #c0caf5",
            "brand": "bg:#0f111a #7aa2f7 bold",
            "hdr-title": "bg:#0f111a #c0caf5 bold",
            "hdr-sub": "bg:#0f111a #565f89",
            "tabbar": "bg:#16161e #565f89",
            "tab-on": "bg:#7aa2f7 #0f111a bold",
            "tab-off": "bg:#1a1b26 #a9b1d6",
            "tab-hint": "bg:#16161e #7dcfff",
            "main": "bg:#1a1b26 #c0caf5",
            "rule": "#3b4261",
            "h1": "bold #7dcfff",
            "h2": "bold #bb9af7",
            "help": "#565f89",
            "dim": "#565f89",
            "ok": "#9ece6a bold",
            "bad": "#f7768e",
            "warn": "#e0af68",
            "accent": "bold #bb9af7",
            "row": "#c0caf5",
            "row-on": "bold #9ece6a",
            "row-focus": "bold #7dcfff",
            "row-on-focus": "bold #73daca reverse",
            "row-detail": "#9aa5ce",
            "sum": "bg:#16161e #a9b1d6",
            "sum-label": "bg:#16161e #7aa2f7",
            "sum-hi": "bg:#16161e #9ece6a bold",
            "sum-dim": "bg:#16161e #565f89",
            "sum-on": "bg:#16161e #9ece6a bold",
            "ftr": "bg:#0f111a #a9b1d6",
            "ftr-msg": "bg:#0f111a #9ece6a",
            "ftr-keys": "bg:#0f111a #565f89",
        }
    )

    app = Application(
        layout=Layout(root),
        key_bindings=kb,
        style=style,
        full_screen=True,
        mouse_support=False,
    )
    try:
        return int(app.run() or 0)
    except Exception as exc:  # noqa: BLE001
        print(f"TUI error: {exc}\nFalling back to setup wizard.", file=sys.stderr)
        return doctor.run_setup(repo, interactive=True)


if __name__ == "__main__":
    from importlib.machinery import SourceFileLoader
    import importlib.util

    here = Path(__file__).resolve().parent
    loader = SourceFileLoader("agents_doctor", str(here / "agents-doctor"))
    spec = importlib.util.spec_from_loader("agents_doctor", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agents_doctor"] = mod
    spec.loader.exec_module(mod)
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
    raise SystemExit(run_tui(repo, mod))

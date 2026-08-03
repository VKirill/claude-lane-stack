#!/usr/bin/env python3
"""Full-screen TUI for agents-doctor — coder / workspace / night / UI language.

Layout (single column, no fragile box-drawing):
  header · tabs · body · summary strip · footer

Coder UX: form + drill-down lists (↑↓ fields, Enter open list).
UI language: en | ru (project ui.language + global ~/.agents/doctor.ui.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

# Sibling import when loaded via SourceFileLoader from agents-doctor.
_BIN = Path(__file__).resolve().parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))

from agents_doctor_tui_i18n import (  # type: ignore  # noqa: E402
    LANG_LABEL,
    LANGS,
    normalize_lang,
    tr,
    writer_blurb,
)

# Form field order on the Coder tab (stable indices for ↑↓).
CODER_FIELDS = ("writer", "model", "effort")

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
    "qwen": {"title": "Qwen", "badge": "FAST"},
    "kimi": {"title": "Kimi", "badge": "LONG CTX"},
    "grok": {"title": "Grok", "badge": "XAI"},
    "agy": {"title": "AGY", "badge": "GEMINI"},
    "codex": {"title": "Codex", "badge": "OPENAI"},
    "auto": {"title": "Auto", "badge": "STACK"},
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

# Tab ids (labels come from i18n).
TAB_IDS = ("coder", "work", "night", "ui", "status", "apply")

WORKSPACE_MODES = ("in_place", "worktree", "auto")


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
        workspace_mode: str = "auto",
        worktree_min_score: int = 4,
        worktree_on_multi_write: bool = True,
        lang: str = "en",
        message: str = "",
        last_apply: str = "",
        cursor: int = 0,
        focus: str = "writer",
        view: str = "form",
        pick_kind: str = "writer",
        pick_cursor: int = 0,
        field_i: int = 0,
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
        self.workspace_mode = workspace_mode
        self.worktree_min_score = worktree_min_score
        self.worktree_on_multi_write = worktree_on_multi_write
        self.lang = normalize_lang(lang)
        self.message = message
        self.last_apply = last_apply
        self.cursor = cursor
        self.focus = focus
        self.view = view
        self.pick_kind = pick_kind
        self.pick_cursor = pick_cursor
        self.field_i = field_i


def _t(state: SetupState, key: str, **kwargs: Any) -> str:
    return tr(state.lang, key, **kwargs)


def _global_ui_path() -> Path:
    return Path.home() / ".agents" / "doctor.ui.yaml"


def _load_global_lang() -> str | None:
    path = _global_ui_path()
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("language:"):
                return normalize_lang(s.split(":", 1)[1].strip().split()[0])
    except OSError:
        return None
    return None


def _save_global_lang(lang: str) -> None:
    path = _global_ui_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# agents-doctor TUI preferences (global)\nlanguage: {normalize_lang(lang)}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


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
                if s == "workspace:" or s.startswith("workspace:"):
                    section = "workspace"
                    continue
                if s == "ui:" or s.startswith("ui:"):
                    section = "ui"
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
                if section == "workspace":
                    if raw and not raw.startswith(" ") and not raw.startswith("\t"):
                        section = None
                    elif s.startswith("mode:"):
                        mode = s.split(":", 1)[1].strip().split()[0]
                        if mode in WORKSPACE_MODES:
                            out["workspace_mode"] = mode
                    elif s.startswith("worktree_min_score:"):
                        try:
                            out["worktree_min_score"] = int(
                                s.split(":", 1)[1].strip().split()[0]
                            )
                        except ValueError:
                            pass
                    elif s.startswith("worktree_on_multi_write:"):
                        out["worktree_on_multi_write"] = "true" in s.lower()
                if section == "ui":
                    if raw and not raw.startswith(" ") and not raw.startswith("\t"):
                        section = None
                    elif s.startswith("language:"):
                        out["lang"] = normalize_lang(
                            s.split(":", 1)[1].strip().split()[0]
                        )
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


def _field_label(state: SetupState, kind: str) -> str:
    return {
        "writer": _t(state, "field_provider"),
        "model": _t(state, "field_model"),
        "effort": _t(state, "field_effort"),
    }.get(kind, kind)


def _ws_title(state: SetupState, mode: str) -> str:
    return _t(state, f"ws_{mode}_title")


def _ws_blurb(state: SetupState, mode: str) -> str:
    return _t(state, f"ws_{mode}_blurb")


def _tab_label(state: SetupState, tid: str) -> str:
    return _t(state, f"tab_{tid}")


def _tab_sub(state: SetupState, tid: str) -> str:
    return _t(state, f"tab_{tid}_sub")


def run_tui(repo: Path, doctor: Any) -> int:
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
        from prompt_toolkit.styles import Style
    except ImportError:
        print(tr("en", "err_no_pt"), file=sys.stderr)
        return doctor.run_setup(repo, interactive=True)

    tools = doctor.detect()
    if not tools.get("claude", {}).get("present"):
        print(tr("en", "err_no_claude"), file=sys.stderr)
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
    ws0 = existing.get("workspace_mode") or "auto"
    if ws0 not in WORKSPACE_MODES:
        ws0 = "auto"
    ws_score0 = max(0, min(10, int(existing.get("worktree_min_score", 4))))
    lang0 = existing.get("lang") or _load_global_lang() or "en"
    lang0 = normalize_lang(lang0)

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
        workspace_mode=ws0,
        worktree_min_score=ws_score0,
        worktree_on_multi_write=bool(existing.get("worktree_on_multi_write", True)),
        lang=lang0,
        message=tr(lang0, "msg_boot"),
        cursor=max(0, writers.index(writer0) if writer0 in writers else 0),
        focus="writer",
        view="form",
        pick_kind="writer",
        pick_cursor=0,
        field_i=0,
    )

    tab_i = {"i": 0}

    def header() -> list[tuple[str, str]]:
        short = str(state.repo)
        if len(short) > 56:
            short = "…" + short[-55:]
        lang_badge = state.lang.upper()
        return [
            ("class:hdr", "  "),
            ("class:brand", "◆ LANE"),
            ("class:hdr", "  "),
            ("class:hdr-title", _t(state, "app_title")),
            ("class:hdr", "  "),
            ("class:hdr-sub", f"[{lang_badge}]"),
            ("class:hdr", "\n"),
            ("class:hdr-sub", f"  {short}"),
            ("class:hdr", "\n"),
        ]

    def tabs() -> list[tuple[str, str]]:
        parts: list[tuple[str, str]] = [("class:tabbar", " ")]
        for i, tid in enumerate(TAB_IDS):
            on = i == tab_i["i"]
            st = "class:tab-on" if on else "class:tab-off"
            arrow = "▸" if on else " "
            parts.append((st, f" {arrow}{i + 1}.{_tab_label(state, tid)} "))
            parts.append(("class:tabbar", " "))
        parts.append(("class:tabbar", "\n"))
        tid = TAB_IDS[tab_i["i"]]
        parts.append(
            ("class:tab-hint", f"  {_tab_label(state, tid)} — {_tab_sub(state, tid)}\n")
        )
        return parts

    def summary_strip() -> list[tuple[str, str]]:
        meta = WRITER_META.get(state.writer, {})
        night = _t(state, "sum_night_on" if state.night_review else "sum_night_off")
        ws_label = {
            "in_place": "main",
            "worktree": "worktree",
            "auto": "auto",
        }.get(state.workspace_mode, state.workspace_mode)
        return [
            ("class:sum", "  "),
            ("class:sum-label", _t(state, "sum_coder")),
            ("class:sum-hi", f"{meta.get('title', state.writer)}"),
            ("class:sum", "  "),
            ("class:sum-dim", state.model),
            ("class:sum", "  "),
            ("class:sum-dim", f"effort:{state.effort}"),
            ("class:sum", "  ·  "),
            ("class:sum-dim", f"ws:{ws_label}"),
            ("class:sum", "  ·  "),
            ("class:sum-dim", state.lang),
            ("class:sum", "  ·  "),
            ("class:sum-on" if state.night_review else "class:sum-dim", night),
            ("class:sum", "\n"),
        ]

    def _options_for(kind: str) -> list[str]:
        if kind == "writer":
            return list(state.writers)
        if kind == "model":
            return _models_for(state.writer)
        return _efforts_for(state.writer)

    def _current_value(kind: str) -> str:
        if kind == "writer":
            return state.writer
        if kind == "model":
            return state.model
        return state.effort

    def _display_value(kind: str, value: str) -> str:
        if kind == "writer":
            meta = WRITER_META.get(value, {})
            title = meta.get("title", value)
            badge = meta.get("badge", "")
            return f"{title:<10}  {badge}" if badge else title
        return value

    def body_coder_form() -> list[tuple[str, str]]:
        meta = WRITER_META.get(state.writer, {})
        models = _models_for(state.writer)
        efforts = _efforts_for(state.writer)
        try:
            mi = models.index(state.model)
        except ValueError:
            mi = 0
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "coder_h1")),
            ("class:help", _t(state, "coder_help")),
            ("class:h2", _t(state, "coder_settings")),
        ]
        rows = [
            (
                "writer",
                _t(state, "field_provider"),
                f"{meta.get('title', state.writer)}  ·  {meta.get('badge', '')}".rstrip(
                    " ·"
                ),
                writer_blurb(state.lang, state.writer),
            ),
            (
                "model",
                _t(state, "field_model"),
                state.model,
                _t(
                    state,
                    "coder_models_of",
                    n=mi + 1,
                    total=len(models),
                    writer=meta.get("title", state.writer),
                ),
            ),
            (
                "effort",
                _t(state, "field_effort"),
                state.effort,
                " · ".join(
                    (f"[{x}]" if x == state.effort else x) for x in efforts
                ),
            ),
        ]
        for i, (_kind, label, value, hint) in enumerate(rows):
            focused = state.field_i == i and state.view == "form"
            st = "class:row-on-focus" if focused else "class:row-on"
            caret = "▸" if focused else " "
            open_hint = _t(state, "coder_open_list") if focused else ""
            lines.append((st, f"  {caret} {label:<10}  {value}{open_hint}\n"))
            if focused and hint:
                lines.append(("class:row-detail", f"      {hint}\n"))
        lines.append(("class:help", _t(state, "coder_tip")))
        return lines

    def body_coder_pick() -> list[tuple[str, str]]:
        kind = state.pick_kind
        opts = _options_for(kind)
        label = _field_label(state, kind)
        parent = ""
        if kind != "writer":
            parent = f" · {WRITER_META.get(state.writer, {}).get('title', state.writer)}"
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "pick_h1", label=label, parent=parent)),
            ("class:help", _t(state, "pick_help")),
        ]
        if not opts:
            lines.append(("class:warn", _t(state, "pick_none")))
            return lines
        current = _current_value(kind)
        for i, opt in enumerate(opts):
            selected = opt == current
            focused = i == state.pick_cursor
            if selected and focused:
                st = "class:row-on-focus"
            elif focused:
                st = "class:row-focus"
            elif selected:
                st = "class:row-on"
            else:
                st = "class:row"
            caret = "▸" if focused else " "
            lines.append((st, f"  {caret} {_radio(selected)}  {_display_value(kind, opt)}\n"))
            if kind == "writer" and focused:
                blurb = writer_blurb(state.lang, opt)
                if blurb:
                    lines.append(("class:row-detail", f"        {blurb}\n"))
        lines.append(
            (
                "class:help",
                _t(
                    state,
                    "pick_footer",
                    n=state.pick_cursor + 1,
                    total=len(opts),
                    current=_current_value(kind),
                ),
            )
        )
        return lines

    def body_coder() -> list[tuple[str, str]]:
        if state.view == "pick":
            return body_coder_pick()
        return body_coder_form()

    def body_work() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "work_h1")),
            ("class:help", _t(state, "work_help")),
            ("class:h2", _t(state, "work_mode_h2")),
        ]
        for i, mode in enumerate(WORKSPACE_MODES):
            selected = mode == state.workspace_mode
            focused = state.focus == "work_mode" and i == state.cursor
            if selected and focused:
                st = "class:row-on-focus"
            elif selected:
                st = "class:row-on"
            elif focused:
                st = "class:row-focus"
            else:
                st = "class:row"
            lines.append((st, f"  {_radio(selected)}  {_ws_title(state, mode)}\n"))
            if selected or focused:
                lines.append(
                    ("class:row-detail", f"      {_ws_blurb(state, mode)}\n")
                )
        lines.append(("class:h2", _t(state, "work_auto_h2")))
        active = state.workspace_mode == "auto"
        st_thr = "class:row-on" if active else "class:dim"
        lines.append(
            (
                st_thr,
                _t(state, "work_score_line", n=state.worktree_min_score),
            )
        )
        lines.append(
            (
                st_thr,
                _t(
                    state,
                    "work_multi_line",
                    sw=_switch(state.worktree_on_multi_write),
                ),
            )
        )
        if not active:
            lines.append(("class:dim", _t(state, "work_thr_ignored")))
        lines.append(("class:help", _t(state, "work_footer")))
        return lines

    def body_night() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "night_h1")),
            ("class:help", _t(state, "night_help")),
            (
                "class:row-on" if state.night_review else "class:row",
                _t(state, "night_toggle", sw=_switch(state.night_review)),
            ),
        ]
        if not state.night_review:
            lines.append(("class:dim", _t(state, "night_off_note")))
            return lines
        bar = "●" * state.max_fix_tasks + "○" * (10 - state.max_fix_tasks)
        lines.append(("class:h2", _t(state, "night_budget_h2")))
        lines.append(
            ("class:row", _t(state, "night_budget_line", n=state.max_fix_tasks))
        )
        lines.append(("class:dim", f"  {bar}\n\n"))
        lines.append(("class:h2", _t(state, "night_merge_h2")))
        lines.append(
            (
                "class:row-on" if state.auto_merge else "class:row",
                _t(state, "night_merge_line", sw=_switch(state.auto_merge)),
            )
        )
        lines.append(("class:h2", _t(state, "night_writer_h2")))
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

    def body_ui() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "ui_h1")),
            ("class:help", _t(state, "ui_help")),
            ("class:h2", _t(state, "ui_lang_h2")),
        ]
        for i, code in enumerate(LANGS):
            selected = code == state.lang
            focused = state.focus == "ui_lang" and i == state.cursor
            if selected and focused:
                st = "class:row-on-focus"
            elif selected:
                st = "class:row-on"
            elif focused:
                st = "class:row-focus"
            else:
                st = "class:row"
            lines.append(
                (st, f"  {_radio(selected)}  {LANG_LABEL[code]}  ({code})\n")
            )
        lines.append(("class:help", _t(state, "ui_note")))
        return lines

    def body_status() -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "status_h1")),
            ("class:help", _t(state, "status_help")),
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
        lines.append(
            ("class:h2", _t(state, "status_profile", profile=profile))
        )
        for k, v in (lanes or {}).items():
            lines.append(("class:dim", f"    {k:<16} {v}\n"))
        lines.append(("class:dim", f"    model            {state.model}\n"))
        lines.append(("class:dim", f"    reasoning_effort {state.effort}\n"))
        lines.append(("class:dim", f"    workspace        {state.workspace_mode}\n"))
        lines.append(("class:dim", f"    language         {state.lang}\n"))
        if notes:
            for n in notes:
                lines.append(("class:warn", f"    · {n}\n"))
        lines.append(("class:help", _t(state, "status_rescan")))
        return lines

    def body_apply() -> list[tuple[str, str]]:
        profile, _lanes, _ = doctor.pick_profile(state.tools, state.writer)
        meta = WRITER_META.get(state.writer, {})
        night_txt = (
            f"{_t(state, 'on')}  fix={state.night_provider}  max={state.max_fix_tasks}"
            if state.night_review
            else _t(state, "off")
        )
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "apply_h1")),
            ("class:help", _t(state, "apply_help")),
            ("class:h2", _t(state, "apply_summary")),
            ("class:row-on", _t(state, "apply_project", repo=state.repo)),
            (
                "class:row-on",
                _t(
                    state,
                    "apply_coder",
                    title=meta.get("title", state.writer),
                    writer=state.writer,
                ),
            ),
            ("class:row-on", _t(state, "apply_model", model=state.model)),
            ("class:row-on", _t(state, "apply_effort", effort=state.effort)),
            (
                "class:row-on",
                _t(state, "apply_workspace", ws=_ws_title(state, state.workspace_mode)),
            ),
            (
                "class:row-on",
                _t(state, "apply_lang", lang=LANG_LABEL.get(state.lang, state.lang)),
            ),
            ("class:row-on", _t(state, "apply_night", night=night_txt)),
            ("class:row-on", _t(state, "apply_profile", profile=profile)),
            ("class:h2", _t(state, "apply_files")),
            ("class:dim", "    .agents/routing.profile.yaml\n"),
            ("class:dim", "    .agents/capabilities.json\n"),
            ("class:dim", "    .agents/night-shift.yaml\n\n"),
            ("class:accent", _t(state, "apply_box1")),
            ("class:accent", _t(state, "apply_box2")),
            ("class:accent", _t(state, "apply_box3")),
            ("class:help", _t(state, "apply_footer")),
        ]
        return lines

    bodies: dict[str, Callable[[], list[tuple[str, str]]]] = {
        "coder": body_coder,
        "work": body_work,
        "night": body_night,
        "ui": body_ui,
        "status": body_status,
        "apply": body_apply,
    }

    def footer() -> list[tuple[str, str]]:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder" and state.view == "pick":
            keys_txt = _t(state, "keys_coder_pick")
        else:
            keys_txt = _t(state, f"keys_{tid}")
        return [
            ("class:ftr", "  "),
            ("class:ftr-msg", (state.message or "")[:44]),
            ("class:ftr", "  ·  "),
            ("class:ftr-keys", keys_txt),
        ]

    def main_view() -> list[tuple[str, str]]:
        return bodies[TAB_IDS[tab_i["i"]]]()

    # ── actions ───────────────────────────────────────────────────────────

    def set_writer(w: str) -> None:
        state.writer = w
        state.model = _ensure_model(w, DEFAULT_MODEL.get(w, state.model))
        state.effort = _ensure_effort(w, DEFAULT_EFFORT.get(w, state.effort))
        state.message = _t(
            state, "msg_coder", name=WRITER_META.get(w, {}).get("title", w)
        )

    def open_pick(kind: str) -> None:
        opts = _options_for(kind)
        if not opts:
            state.message = _t(state, "msg_no_opts", name=_field_label(state, kind))
            return
        state.view = "pick"
        state.pick_kind = kind
        state.focus = kind
        current = _current_value(kind)
        try:
            state.pick_cursor = opts.index(current)
        except ValueError:
            state.pick_cursor = 0
        state.message = _t(state, "msg_pick", name=_field_label(state, kind))

    def close_pick(confirm: bool) -> None:
        if state.view != "pick":
            return
        kind = state.pick_kind
        opts = _options_for(kind)
        if confirm and opts:
            i = max(0, min(state.pick_cursor, len(opts) - 1))
            chosen = opts[i]
            if kind == "writer":
                set_writer(chosen)
                state.field_i = 1
            elif kind == "model":
                state.model = chosen
                state.message = _t(state, "msg_model", name=chosen)
                state.field_i = 2
            else:
                state.effort = chosen
                state.message = _t(state, "msg_effort", name=chosen)
                state.field_i = 2
        else:
            state.message = _t(state, "msg_cancelled")
        state.view = "form"
        state.focus = CODER_FIELDS[state.field_i]

    def move_form_field(delta: int) -> None:
        state.view = "form"
        state.field_i = (state.field_i + delta) % len(CODER_FIELDS)
        state.focus = CODER_FIELDS[state.field_i]
        state.message = _t(
            state, "msg_focus", name=_field_label(state, state.focus)
        )

    def move_pick(delta: int) -> None:
        opts = _options_for(state.pick_kind)
        if not opts:
            return
        state.pick_cursor = (state.pick_cursor + delta) % len(opts)

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
        state.message = _t(state, "msg_night_fix", name=state.night_provider)

    def move_work_mode(delta: int) -> None:
        state.focus = "work_mode"
        try:
            i = WORKSPACE_MODES.index(state.workspace_mode)
        except ValueError:
            i = 0
        i = (i + delta) % len(WORKSPACE_MODES)
        state.cursor = i
        state.workspace_mode = WORKSPACE_MODES[i]
        state.message = _t(
            state, "msg_workspace", name=_ws_title(state, state.workspace_mode)
        )

    def move_ui_lang(delta: int) -> None:
        state.focus = "ui_lang"
        try:
            i = LANGS.index(state.lang)
        except ValueError:
            i = 0
        i = (i + delta) % len(LANGS)
        state.cursor = i
        state.lang = LANGS[i]
        state.message = _t(
            state, "msg_lang", name=LANG_LABEL.get(state.lang, state.lang)
        )

    def cycle_lang() -> None:
        try:
            i = LANGS.index(state.lang)
        except ValueError:
            i = 0
        state.lang = LANGS[(i + 1) % len(LANGS)]
        if state.focus == "ui_lang":
            state.cursor = LANGS.index(state.lang)
        state.message = _t(
            state, "msg_lang", name=LANG_LABEL.get(state.lang, state.lang)
        )

    def do_apply(app: Any | None = None) -> None:
        import contextlib
        import io

        profile, lanes, notes = doctor.pick_profile(state.tools, state.writer)
        model = state.model if state.writer != "auto" else None
        effort = state.effort if state.writer != "auto" else None
        write = getattr(doctor, "write_outputs", None)
        if write is None:
            raise RuntimeError("doctor.write_outputs missing")
        sink = io.StringIO()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                try:
                    write(
                        state.repo,
                        state.tools,
                        profile,
                        lanes,
                        notes,
                        writer_model=model,
                        writer_effort=effort,
                        workspace_mode=state.workspace_mode,
                        worktree_min_score=state.worktree_min_score,
                        worktree_on_multi_write=state.worktree_on_multi_write,
                        ui_language=state.lang,
                        quiet=True,
                    )
                except TypeError:
                    try:
                        write(
                            state.repo,
                            state.tools,
                            profile,
                            lanes,
                            notes,
                            writer_model=model,
                            writer_effort=effort,
                            workspace_mode=state.workspace_mode,
                            worktree_min_score=state.worktree_min_score,
                            worktree_on_multi_write=state.worktree_on_multi_write,
                            quiet=True,
                        )
                    except TypeError:
                        try:
                            write(
                                state.repo,
                                state.tools,
                                profile,
                                lanes,
                                notes,
                                writer_model=model,
                                writer_effort=effort,
                                quiet=True,
                            )
                        except TypeError:
                            write(state.repo, state.tools, profile, lanes, notes)
                try:
                    doctor.write_night_shift(
                        state.repo,
                        enabled=state.night_review,
                        provider=state.night_provider,
                        max_fix_tasks=state.max_fix_tasks,
                        auto_merge=state.auto_merge if state.night_review else False,
                        quiet=True,
                    )
                except TypeError:
                    doctor.write_night_shift(
                        state.repo,
                        enabled=state.night_review,
                        provider=state.night_provider,
                        max_fix_tasks=state.max_fix_tasks,
                        auto_merge=state.auto_merge if state.night_review else False,
                    )
        except Exception as exc:  # noqa: BLE001
            state.message = _t(state, "msg_apply_fail", err=exc)
            return

        _save_global_lang(state.lang)
        state.message = _t(state, "msg_saved")
        result = {
            "ok": True,
            "repo": str(state.repo),
            "writer": state.writer,
            "model": state.model,
            "effort": state.effort,
            "workspace_mode": state.workspace_mode,
            "lang": state.lang,
            "night": state.night_review,
            "night_provider": state.night_provider if state.night_review else None,
            "max_fix_tasks": state.max_fix_tasks if state.night_review else None,
        }
        if app is not None:
            app.exit(result=result)
        else:
            from prompt_toolkit.application.current import get_app

            try:
                get_app().exit(result=result)
            except Exception:  # noqa: BLE001
                pass

    def rescan() -> None:
        state.tools = doctor.detect()
        writers = list(doctor.available_writers(state.tools))
        if state.tools.get("codex", {}).get("present") and "codex" not in writers:
            writers.append("codex")
        state.writers = writers or ["auto"]
        if state.writer not in state.writers:
            set_writer(state.writers[0])
            state.cursor = 0
        state.message = _t(state, "msg_rescan")

    # ── keys ──────────────────────────────────────────────────────────────

    kb = KeyBindings()

    def leave_pick_if_any() -> None:
        if state.view == "pick":
            state.view = "form"
            state.focus = CODER_FIELDS[state.field_i]

    def on_tab_enter() -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "work":
            state.focus = "work_mode"
            try:
                state.cursor = WORKSPACE_MODES.index(state.workspace_mode)
            except ValueError:
                state.cursor = 0
        elif tid == "ui":
            state.focus = "ui_lang"
            try:
                state.cursor = LANGS.index(state.lang)
            except ValueError:
                state.cursor = 0
        state.message = _t(state, "msg_tab", name=_tab_label(state, tid))

    @kb.add("q")
    @kb.add("c-c")
    def _(event) -> None:
        event.app.exit(result=0)

    @kb.add("escape")
    @kb.add("backspace")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "coder" and state.view == "pick":
            close_pick(confirm=False)

    @kb.add("tab")
    def _(event) -> None:
        leave_pick_if_any()
        tab_i["i"] = (tab_i["i"] + 1) % len(TAB_IDS)
        on_tab_enter()

    @kb.add("s-tab")
    def _(event) -> None:
        leave_pick_if_any()
        tab_i["i"] = (tab_i["i"] - 1) % len(TAB_IDS)
        on_tab_enter()

    @kb.add("right")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "form":
                open_pick(CODER_FIELDS[state.field_i])
            return
        tab_i["i"] = (tab_i["i"] + 1) % len(TAB_IDS)
        on_tab_enter()

    @kb.add("left")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                close_pick(confirm=False)
            return
        tab_i["i"] = (tab_i["i"] - 1) % len(TAB_IDS)
        on_tab_enter()

    for n in range(1, 7):

        @kb.add(str(n))
        def _(event, n=n) -> None:
            leave_pick_if_any()
            tab_i["i"] = n - 1
            if TAB_IDS[tab_i["i"]] == "coder":
                state.view = "form"
                state.field_i = 0
                state.focus = "writer"
            on_tab_enter()

    @kb.add("up")
    @kb.add("k")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                move_pick(-1)
            else:
                move_form_field(-1)
        elif tid == "work":
            move_work_mode(-1)
        elif tid == "ui":
            move_ui_lang(-1)
        elif tid == "night" and state.night_review:
            move_night_writer(-1)

    @kb.add("down")
    @kb.add("j")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                move_pick(1)
            else:
                move_form_field(1)
        elif tid == "work":
            move_work_mode(1)
        elif tid == "ui":
            move_ui_lang(1)
        elif tid == "night" and state.night_review:
            move_night_writer(1)

    @kb.add("L")
    @kb.add("l")
    def _(event) -> None:
        # Always available language cycle (does not steal 'l' only when capital L
        # preferred — both bound; coder list uses j/k for nav).
        if TAB_IDS[tab_i["i"]] == "coder" and state.view == "pick":
            return
        cycle_lang()

    @kb.add("m")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            state.field_i = 1
            open_pick("model")
        elif tid == "work":
            state.worktree_on_multi_write = not state.worktree_on_multi_write
            state.message = _t(
                state,
                "msg_multi",
                on=("on" if state.worktree_on_multi_write else "off"),
            )

    @kb.add("e")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "coder":
            state.field_i = 2
            open_pick("effort")

    @kb.add("p")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "coder":
            state.field_i = 0
            open_pick("writer")

    @kb.add(" ")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                close_pick(confirm=True)
            else:
                open_pick(CODER_FIELDS[state.field_i])
        elif tid == "work":
            i = max(0, min(state.cursor, len(WORKSPACE_MODES) - 1))
            state.workspace_mode = WORKSPACE_MODES[i]
            state.message = _t(
                state, "msg_workspace", name=_ws_title(state, state.workspace_mode)
            )
        elif tid == "ui":
            i = max(0, min(state.cursor, len(LANGS) - 1))
            state.lang = LANGS[i]
            state.message = _t(
                state, "msg_lang", name=LANG_LABEL.get(state.lang, state.lang)
            )
        elif tid == "night":
            state.night_review = not state.night_review
            state.message = _t(
                state,
                "msg_night",
                on=(_t(state, "on") if state.night_review else _t(state, "off")),
            )
        elif tid == "apply":
            do_apply(event.app)

    @kb.add("enter")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "apply":
            do_apply(event.app)
        elif tid == "coder":
            if state.view == "pick":
                close_pick(confirm=True)
            else:
                open_pick(CODER_FIELDS[state.field_i])
        elif tid == "work":
            i = max(0, min(state.cursor, len(WORKSPACE_MODES) - 1))
            state.workspace_mode = WORKSPACE_MODES[i]
            state.message = _t(
                state, "msg_workspace", name=_ws_title(state, state.workspace_mode)
            )
        elif tid == "ui":
            i = max(0, min(state.cursor, len(LANGS) - 1))
            state.lang = LANGS[i]
            state.message = _t(
                state, "msg_lang", name=LANG_LABEL.get(state.lang, state.lang)
            )
        elif tid == "night":
            state.night_review = not state.night_review
            state.message = _t(
                state,
                "msg_night",
                on=(_t(state, "on") if state.night_review else _t(state, "off")),
            )
        else:
            tab_i["i"] = TAB_IDS.index("apply")
            on_tab_enter()

    @kb.add("a")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "night" and state.night_review:
            state.auto_merge = not state.auto_merge
            state.message = _t(state, "msg_merge", on=str(state.auto_merge))

    @kb.add("n")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "night" and state.night_review:
            state.focus = "night_writer"
            opts = [w for w in state.writers if w != "auto"]
            if opts and state.night_provider in opts:
                state.cursor = opts.index(state.night_provider)
            state.message = _t(state, "msg_night_writer")

    @kb.add("+")
    @kb.add("=")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "work":
            state.worktree_min_score = min(10, state.worktree_min_score + 1)
            state.message = _t(
                state, "msg_ws_score", n=state.worktree_min_score
            )
        elif state.night_review:
            state.max_fix_tasks = min(10, state.max_fix_tasks + 1)
            state.message = _t(state, "msg_max_fix", n=state.max_fix_tasks)

    @kb.add("-")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "work":
            state.worktree_min_score = max(0, state.worktree_min_score - 1)
            state.message = _t(
                state, "msg_ws_score", n=state.worktree_min_score
            )
        elif state.night_review:
            state.max_fix_tasks = max(1, state.max_fix_tasks - 1)
            state.message = _t(state, "msg_max_fix", n=state.max_fix_tasks)

    @kb.add("r")
    def _(event) -> None:
        rescan()

    @kb.add("?")
    def _(event) -> None:
        if state.view == "pick":
            state.message = _t(state, "msg_help_pick")
        else:
            state.message = _t(state, "msg_help")

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
        result = app.run()
    except Exception as exc:  # noqa: BLE001
        print(tr("en", "err_tui", err=exc), file=sys.stderr)
        return doctor.run_setup(repo, interactive=True)

    if isinstance(result, dict) and result.get("ok"):
        agents = Path(result["repo"]) / ".agents"
        lang = normalize_lang(result.get("lang") or "en")
        print()
        print(tr(lang, "done_title"))
        print(tr(lang, "done_path", v=result["repo"]))
        print(tr(lang, "done_coder", v=result["writer"]))
        print(tr(lang, "done_model", v=result.get("model") or "—"))
        print(tr(lang, "done_effort", v=result.get("effort") or "—"))
        print(tr(lang, "done_ws", v=result.get("workspace_mode") or "auto"))
        print(tr(lang, "done_lang", v=lang))
        night_v = (
            f"on (fix={result.get('night_provider')}, max={result.get('max_fix_tasks')})"
            if result.get("night")
            else "off"
        )
        print(tr(lang, "done_night", v=night_v))
        print(tr(lang, "done_wrote", v=str(agents / "routing.profile.yaml")))
        print(f"           {agents / 'night-shift.yaml'}")
        print()
        print(tr(lang, "done_hint"))
        return 0
    return int(result or 0) if isinstance(result, int) else 0


if __name__ == "__main__":
    from importlib.machinery import SourceFileLoader
    import importlib.util

    here = Path(__file__).resolve().parent
    # Load sibling i18n if running as script
    i18n_path = here / "agents_doctor_tui_i18n.py"
    if i18n_path.is_file() and "agents_doctor_tui_i18n" not in sys.modules:
        loader = SourceFileLoader("agents_doctor_tui_i18n", str(i18n_path))
        spec = importlib.util.spec_from_loader("agents_doctor_tui_i18n", loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["agents_doctor_tui_i18n"] = mod
        spec.loader.exec_module(mod)

    loader = SourceFileLoader("agents_doctor", str(here / "agents-doctor"))
    spec = importlib.util.spec_from_loader("agents_doctor", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agents_doctor"] = mod
    spec.loader.exec_module(mod)
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
    raise SystemExit(run_tui(repo, mod))

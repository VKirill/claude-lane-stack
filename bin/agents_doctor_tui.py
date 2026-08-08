#!/usr/bin/env python3
"""Full-screen TUI for agents-doctor — conveyor stages / coder / work / night.

Layout (single column):
  header · tabs · body · pipeline strip · footer

Inspired by modern ops TUIs (k9s / lazygit style focus + badges):
  clear stages, radio cards, live conveyor strip, EN/RU.

Coder UX: form + drill-down lists (↑↓ fields, Enter open list).
Stages UX: customize plan_critique / write / night / specialist per agent.
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
from pipeline_stages import (  # type: ignore  # noqa: E402
    DEFAULT_MODELS,
    KNOWN_STAGE_PROVIDERS,
    default_stages,
    normalize_stages,
)

# Form field order on the Coder tab (stable indices for ↑↓).
CODER_FIELDS = ("writer", "model", "effort", "fast")  # fast only when writer=codex

# Stage cards on the Stages tab (pipeline roles, not Claude subagents).
STAGE_IDS = ("plan_critique", "write", "night_review", "specialist")
# Full agent catalog for stages (not limited to currently detected CLIs).
ALL_AGENTS = ("kimi", "qwen", "grok", "agy", "codex")
CRITIQUE_PROVIDERS = ("structural",) + ALL_AGENTS
STAGE_FIELD_CRITIQUE = ("enabled", "mode", "provider", "model", "effort")
STAGE_FIELD_WRITE = ("provider", "model", "effort")  # enabled always on
STAGE_FIELD_NIGHT = ("enabled", "provider", "model", "effort")
STAGE_FIELD_SPEC = ("enabled", "when", "provider", "model", "effort")

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
    "kimi": [
        "kimi-code/k3-256k",
        "kimi-k2.5",
        "kimi-latest",
        "moonshot-v1-128k",
        "moonshot-v1-32k",
        "moonshot-v1-8k",
    ],
    "grok": [
        "grok-4.5",
        "grok-4",
        "grok-3",
        "grok-3-mini",
    ],
    "agy": [
        "gemini-3.6-flash-high",
        "gemini-3.6-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ],
    "codex": [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.4",
        "o4-mini",
    ],
    "structural": [],
    "auto": ["(stack default)"],
}

WRITER_EFFORTS: dict[str, list[str]] = {
    "qwen": ["low", "medium", "high"],
    "kimi": ["low", "medium", "high"],
    "grok": ["low", "medium", "high"],
    "agy": ["low", "medium", "high"],
    "codex": ["low", "medium", "high", "xhigh", "max"],
    "structural": ["low", "medium", "high"],
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
TAB_IDS = ("coder", "stages", "work", "night", "ui", "status", "apply")

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
        fast_mode: bool = False,
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
        stages: dict[str, Any] | None = None,
        stage_i: int = 0,
        stage_field_i: int = 0,
    ) -> None:
        self.repo = repo
        self.tools = tools
        self.writers = writers
        self.writer = writer
        self.model = model
        self.effort = effort
        self.fast_mode = bool(fast_mode)
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
        self.stages = stages or default_stages(write_provider=writer or "kimi")
        self.stage_i = stage_i
        self.stage_field_i = stage_field_i


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
                    elif s.startswith("service_tier:"):
                        tier = s.split(":", 1)[1].strip().split()[0].lower()
                        out["fast_mode"] = tier == "fast"
                    elif s.startswith("fast_mode:"):
                        out["fast_mode"] = "true" in s.lower()
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
                if s == "stages:" or s.startswith("stages:"):
                    section = "stages"
                    stage_name = None
                    out.setdefault("stages_raw", {})
                    continue
                if section == "stages":
                    if raw and not raw.startswith(" ") and not raw.startswith("\t"):
                        section = None
                        stage_name = None
                    elif indent_is_two(raw) and s.endswith(":") and " " not in s[:-1]:
                        stage_name = s[:-1].strip()
                        out["stages_raw"].setdefault(stage_name, {})
                    elif stage_name and ":" in s and not s.endswith(":"):
                        k, _, v = s.partition(":")
                        out["stages_raw"][stage_name][k.strip()] = (
                            v.strip().split()[0].strip("\"'")
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


def indent_is_two(raw: str) -> bool:
    return len(raw) - len(raw.lstrip(" ")) == 2


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
        "fast": _t(state, "field_fast"),
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

    stages0 = normalize_stages(
        existing.get("stages_raw"),
        write_provider=writer0 if writer0 != "auto" else "kimi",
    )
    # Align stages write / night with loaded coder + night toggles
    stages0["write"]["provider"] = writer0 if writer0 != "auto" else stages0["write"]["provider"]
    stages0["write"]["model"] = model0
    stages0["write"]["reasoning_effort"] = effort0
    stages0["night_review"]["enabled"] = bool(existing.get("night_review", False))
    if night_w0 and night_w0 != "auto":
        stages0["night_review"]["provider"] = night_w0

    state = SetupState(
        repo=repo,
        tools=tools,
        writers=writers,
        writer=writer0,
        model=model0,
        effort=effort0,
        fast_mode=bool(existing.get("fast_mode", False)) and writer0 == "codex",
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
        stages=stages0,
        stage_i=0,
        stage_field_i=0,
    )

    tab_i = {"i": 0}

    def _sync_stages_from_coder_night() -> None:
        """Keep stages.write / night_review in lockstep with Coder + Night tabs."""
        st = state.stages
        st["write"]["provider"] = (
            state.writer if state.writer != "auto" else st["write"].get("provider", "kimi")
        )
        st["write"]["model"] = state.model
        st["write"]["reasoning_effort"] = state.effort
        st["night_review"]["enabled"] = bool(state.night_review)
        st["night_review"]["provider"] = state.night_provider
        state.stages = normalize_stages(st, write_provider=st["write"]["provider"])

    def _sync_coder_night_from_stages() -> None:
        """Push Stages-tab edits into Coder / Night fields."""
        st = state.stages
        w = st.get("write") or {}
        prov = str(w.get("provider") or state.writer)
        if prov in ALL_AGENTS or prov in WRITER_META:
            # Allow selecting agents even if not currently detected on host.
            if prov not in state.writers and prov != "auto":
                state.writers = list(dict.fromkeys([*state.writers, prov]))
            state.writer = prov
            state.model = _ensure_model(prov, str(w.get("model") or state.model))
            state.effort = _ensure_effort(
                prov, str(w.get("reasoning_effort") or state.effort)
            )
        nr = st.get("night_review") or {}
        state.night_review = bool(nr.get("enabled"))
        np = str(nr.get("provider") or state.night_provider)
        if np in ALL_AGENTS or np in WRITER_META:
            if np not in state.writers and np != "auto":
                state.writers = list(dict.fromkeys([*state.writers, np]))
            state.night_provider = np

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
            ("class:pipe-badge", " conveyor "),
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

    def _pipeline_parts() -> list[tuple[str, str]]:
        """Live conveyor: PM → critique → write → L1 → night/specialist."""
        st = state.stages
        pc = st.get("plan_critique") or {}
        wr = st.get("write") or {}
        nr = st.get("night_review") or {}
        sp = st.get("specialist") or {}
        # Short labels — localized for RU/EN
        crit_lbl = _t(state, "pipe_crit")
        write_lbl = _t(state, "pipe_write")
        night_lbl = _t(state, "pipe_night")
        spec_lbl = _t(state, "pipe_spec")
        off_lbl = _t(state, "off")
        parts: list[tuple[str, str]] = [("class:pipe", "  ")]
        parts.append(("class:pipe-node", "PM"))
        parts.append(("class:pipe-arrow", " › "))
        if pc.get("enabled"):
            mode_key = str(pc.get("mode") or "advisory")
            mode_short = _loc_mode(mode_key)
            prov = _loc_provider(str(pc.get("provider") or "structural"))
            parts.append(("class:pipe-on", f"{crit_lbl}:{prov}/{mode_short}"))
        else:
            parts.append(("class:pipe-off", f"{crit_lbl}:{off_lbl}"))
        parts.append(("class:pipe-arrow", " › "))
        parts.append(
            (
                "class:pipe-write",
                f"{write_lbl}:{wr.get('provider', state.writer)}",
            )
        )
        parts.append(("class:pipe-arrow", " › "))
        parts.append(("class:pipe-node", "L1"))
        parts.append(("class:pipe-arrow", " › "))
        if nr.get("enabled"):
            parts.append(
                (
                    "class:pipe-night",
                    f"{night_lbl}:{nr.get('provider', '?')}",
                )
            )
        else:
            parts.append(("class:pipe-off", f"{night_lbl}:{off_lbl}"))
        if sp.get("enabled"):
            parts.append(("class:pipe-arrow", " › "))
            when_s = _loc_when(str(sp.get("when") or "high_risk"))
            parts.append(
                (
                    "class:pipe-spec",
                    f"{spec_lbl}:{sp.get('provider')}/{when_s}",
                )
            )
        parts.append(("class:pipe", "\n"))
        return parts

    def summary_strip() -> list[tuple[str, str]]:
        meta = WRITER_META.get(state.writer, {})
        night = _t(state, "sum_night_on" if state.night_review else "sum_night_off")
        ws_label = {
            "in_place": "main",
            "worktree": "worktree",
            "auto": "auto",
        }.get(state.workspace_mode, state.workspace_mode)
        line1 = [
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
        return line1 + _pipeline_parts()

    def _coder_fields() -> tuple[str, ...]:
        if state.writer == "codex":
            return ("writer", "model", "effort", "fast")
        return ("writer", "model", "effort")

    def _options_for(kind: str) -> list[str]:
        if kind == "writer":
            return list(state.writers)
        if kind == "model":
            return _models_for(state.writer)
        if kind == "fast":
            return ["off", "on"]
        return _efforts_for(state.writer)

    def _current_value(kind: str) -> str:
        if kind == "writer":
            return state.writer
        if kind == "model":
            return state.model
        if kind == "fast":
            return "on" if state.fast_mode else "off"
        return state.effort

    def _display_value(kind: str, value: str) -> str:
        if kind == "writer":
            meta = WRITER_META.get(value, {})
            title = meta.get("title", value)
            badge = meta.get("badge", "")
            return f"{title:<10}  {badge}" if badge else title
        if kind == "fast":
            return _t(state, "on") if value == "on" else _t(state, "off")
        return value

    def body_coder_form() -> list[tuple[str, str]]:
        meta = WRITER_META.get(state.writer, {})
        models = _models_for(state.writer)
        efforts = _efforts_for(state.writer)
        fields = _coder_fields()
        if state.field_i >= len(fields):
            state.field_i = 0
        try:
            mi = models.index(state.model)
        except ValueError:
            mi = 0
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "coder_h1")),
            ("class:help", _t(state, "coder_help")),
            ("class:h2", _t(state, "coder_settings")),
        ]
        rows: list[tuple[str, str, str, str]] = [
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
        if "fast" in fields:
            rows.append(
                (
                    "fast",
                    _t(state, "field_fast"),
                    _t(state, "on") if state.fast_mode else _t(state, "off"),
                    _t(state, "coder_fast_hint"),
                )
            )
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

    def _stage_fields(stage_id: str) -> tuple[str, ...]:
        if stage_id == "plan_critique":
            return STAGE_FIELD_CRITIQUE
        if stage_id == "write":
            return STAGE_FIELD_WRITE
        if stage_id == "night_review":
            return STAGE_FIELD_NIGHT
        return STAGE_FIELD_SPEC

    def _loc_on(enabled: bool) -> str:
        return _t(state, "on") if enabled else _t(state, "off")

    def _loc_mode(mode: str) -> str:
        key = f"mode_{mode}"
        text = _t(state, key)
        return text if text != key else mode

    def _loc_when(when: str) -> str:
        key = f"when_{when}"
        text = _t(state, key)
        return text if text != key else when

    def _loc_provider(provider: str) -> str:
        key = f"prov_{provider}"
        text = _t(state, key)
        return text if text != key else provider

    def _providers_for_stage(stage_id: str) -> list[str]:
        """Full catalog — user can pick any agent per stage."""
        if stage_id == "plan_critique":
            return list(CRITIQUE_PROVIDERS)
        return list(ALL_AGENTS)

    def _models_for_provider(provider: str) -> list[str]:
        if provider == "structural":
            return []
        opts = _models_for(provider)
        return list(opts) if opts else [DEFAULT_MODEL.get(provider, provider)]

    def _efforts_for_provider(provider: str) -> list[str]:
        if provider == "structural":
            return ["low", "medium", "high"]
        return _efforts_for(provider)

    def _stage_field_value(stage_id: str, field: str) -> str:
        block = state.stages.get(stage_id) or {}
        if field == "enabled":
            return _loc_on(bool(block.get("enabled")))
        if field == "mode":
            return _loc_mode(str(block.get("mode") or "advisory"))
        if field == "when":
            return _loc_when(str(block.get("when") or "high_risk"))
        if field == "provider":
            return _loc_provider(str(block.get("provider") or "—"))
        if field == "effort":
            return str(block.get("reasoning_effort") or block.get("effort") or "—")
        if field == "model":
            prov = str(block.get("provider") or "")
            if prov == "structural":
                return _t(state, "model_na")
            return str(block.get("model") or "—") or "—"
        return str(block.get(field) or "—")

    def _select_stage(index: int) -> None:
        """Jump to a stage and land on its first editable field."""
        state.stage_i = max(0, min(index, len(STAGE_IDS) - 1))
        state.stage_field_i = 0
        # Always edit fields — list is only a preview of selection.
        state.focus = "stage_field"
        sid = STAGE_IDS[state.stage_i]
        fields = _stage_fields(sid)
        state.message = _t(
            state,
            "msg_stage_edit",
            stage=_t(state, f"stage_{sid}"),
            field=_t(state, f"sfield_{fields[0]}"),
        )

    def _move_stage(delta: int) -> None:
        _select_stage((state.stage_i + delta) % len(STAGE_IDS))

    def _move_stage_field(delta: int) -> None:
        """Move across fields; wrap into neighbouring stages."""
        state.focus = "stage_field"
        fields = _stage_fields(STAGE_IDS[state.stage_i])
        new_i = state.stage_field_i + delta
        if new_i < 0:
            _move_stage(-1)
            fields = _stage_fields(STAGE_IDS[state.stage_i])
            state.stage_field_i = len(fields) - 1
        elif new_i >= len(fields):
            _move_stage(1)
            state.stage_field_i = 0
        else:
            state.stage_field_i = new_i
        fields = _stage_fields(STAGE_IDS[state.stage_i])
        state.stage_field_i = max(0, min(state.stage_field_i, len(fields) - 1))
        state.message = _t(
            state,
            "msg_focus",
            name=_t(state, f"sfield_{fields[state.stage_field_i]}"),
        )

    def _set_provider(block: dict[str, Any], new_p: str) -> None:
        block["provider"] = new_p
        if new_p == "structural":
            block["model"] = ""
            block.setdefault("reasoning_effort", "low")
        else:
            models = _models_for_provider(new_p)
            cur = str(block.get("model") or "")
            if cur not in models:
                block["model"] = models[0] if models else DEFAULT_MODELS.get(new_p, "")
            efforts = _efforts_for_provider(new_p)
            cur_e = str(block.get("reasoning_effort") or block.get("effort") or "")
            if cur_e not in efforts:
                block["reasoning_effort"] = efforts[0] if efforts else "medium"

    def _cycle_stage_field(delta: int = 1) -> None:
        """← / → / Space / Enter: change the focused field's value."""
        state.focus = "stage_field"
        sid = STAGE_IDS[state.stage_i]
        fields = _stage_fields(sid)
        state.stage_field_i = max(0, min(state.stage_field_i, len(fields) - 1))
        field = fields[state.stage_field_i]
        block = state.stages.setdefault(sid, {})
        if field == "enabled":
            if sid == "write":
                state.message = _t(state, "msg_stage_write_fixed")
                return
            block["enabled"] = not bool(block.get("enabled"))
            state.message = _t(
                state,
                "msg_stage_enabled",
                stage=_t(state, f"stage_{sid}"),
                on=_loc_on(bool(block["enabled"])),
            )
        elif field == "mode":
            modes = ("advisory", "gate")
            cur = str(block.get("mode") or "advisory")
            try:
                i = modes.index(cur)
            except ValueError:
                i = 0
            block["mode"] = modes[(i + delta) % len(modes)]
            state.message = _t(
                state, "msg_stage_mode", mode=_loc_mode(block["mode"])
            )
        elif field == "when":
            opts = ("high_risk", "always")
            cur = str(block.get("when") or "high_risk")
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["when"] = opts[(i + delta) % len(opts)]
            state.message = _t(
                state, "msg_stage_when", when=_loc_when(block["when"])
            )
        elif field == "provider":
            opts = _providers_for_stage(sid)
            cur = str(block.get("provider") or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            new_p = opts[(i + delta) % len(opts)]
            _set_provider(block, new_p)
            state.message = _t(
                state, "msg_stage_provider", provider=_loc_provider(new_p)
            )
        elif field == "model":
            prov = str(block.get("provider") or "qwen")
            if prov == "structural":
                # Auto-step to first real agent so user can pick models.
                _set_provider(block, "qwen" if delta >= 0 else "codex")
                state.message = _t(
                    state,
                    "msg_stage_provider",
                    provider=_loc_provider(str(block["provider"])),
                )
            else:
                opts = _models_for_provider(prov)
                if not opts:
                    state.message = _t(state, "msg_stage_no_models")
                    return
                cur = str(block.get("model") or opts[0])
                try:
                    i = opts.index(cur)
                except ValueError:
                    i = 0
                block["model"] = opts[(i + delta) % len(opts)]
                state.message = _t(
                    state, "msg_stage_model", model=block["model"]
                )
        elif field == "effort":
            prov = str(block.get("provider") or "qwen")
            opts = _efforts_for_provider(prov)
            cur = str(block.get("reasoning_effort") or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["reasoning_effort"] = opts[(i + delta) % len(opts)]
            state.message = _t(
                state, "msg_stage_effort", effort=block["reasoning_effort"]
            )
        # Keep coder/night tabs in sync when write/night stages change.
        if sid in {"write", "night_review"}:
            _sync_coder_night_from_stages()
        state.stages = normalize_stages(
            state.stages,
            write_provider=str(
                (state.stages.get("write") or {}).get("provider") or "kimi"
            ),
        )

    def body_stages() -> list[tuple[str, str]]:
        # Field-first UX: pipeline is a selector preview; edits happen in
        # the settings list. ↑↓ fields (wrap stages) · ←→ cycle values.
        if state.focus not in {"stage_field", "stage_list"}:
            state.focus = "stage_field"
        lines: list[tuple[str, str]] = [
            ("class:h1", _t(state, "stages_h1")),
            ("class:help", _t(state, "stages_help")),
            ("class:h2", _t(state, "stages_pipe_h2")),
        ]
        for i, sid in enumerate(STAGE_IDS):
            block = state.stages.get(sid) or {}
            selected = state.stage_i == i
            enabled = True if sid == "write" else bool(block.get("enabled", True))
            if selected:
                st = "class:stage-focus"
                caret = "▸"
            elif enabled:
                st = "class:stage-on"
                caret = " "
            else:
                st = "class:stage-off"
                caret = " "
            title = _t(state, f"stage_{sid}")
            badge = _t(state, f"stage_{sid}_badge")
            prov = str(block.get("provider") or "—")
            model = str(block.get("model") or "—")
            effort = str(block.get("reasoning_effort") or "—")
            if sid == "write":
                detail = (
                    f"{_loc_provider(prov)} · {model} · {effort}"
                )
            elif sid == "plan_critique":
                detail = (
                    f"{_loc_on(enabled)} · {_loc_mode(str(block.get('mode') or 'advisory'))} · "
                    f"{_loc_provider(prov)}"
                )
                if prov != "structural" and model and model != "—":
                    detail += f" · {model} · {effort}"
            elif sid == "night_review":
                detail = (
                    f"{_loc_on(enabled)} · {_loc_provider(prov)} · {model} · {effort}"
                )
            else:
                detail = (
                    f"{_loc_on(enabled)} · "
                    f"{_loc_when(str(block.get('when') or 'high_risk'))} · "
                    f"{_loc_provider(prov)} · {model} · {effort}"
                )
            lines.append((st, f"  {caret} {i + 1}. {title:<18}  [{badge}]\n"))
            lines.append(("class:row-detail", f"       {detail}\n"))
        # Field editor for selected stage
        sid = STAGE_IDS[state.stage_i]
        fields = _stage_fields(sid)
        state.stage_field_i = max(0, min(state.stage_field_i, len(fields) - 1))
        lines.append(
            (
                "class:h2",
                _t(state, "stages_fields_h2", stage=_t(state, f"stage_{sid}")),
            )
        )
        for fi, field in enumerate(fields):
            focused = state.stage_field_i == fi
            st = "class:row-on-focus" if focused else "class:row"
            caret = "▸" if focused else " "
            val = _stage_field_value(sid, field)
            label = _t(state, f"sfield_{field}")
            # Hint how many options for model/provider
            hint = ""
            if focused and field == "provider":
                n = len(_providers_for_stage(sid))
                hint = f"  ←→ {n}"
            elif focused and field == "model":
                prov = str((state.stages.get(sid) or {}).get("provider") or "")
                n = len(_models_for_provider(prov))
                hint = f"  ←→ {n}" if n else f"  ({_t(state, 'model_na')})"
            elif focused and field in {"mode", "when", "effort", "enabled"}:
                hint = "  ←→"
            lines.append((st, f"  {caret} {label:<14}  {val}{hint}\n"))
        lines.append(("class:help", _t(state, "stages_tip")))
        return lines

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
        if state.writer == "codex":
            lines.append(
                (
                    "class:dim",
                    f"    service_tier     {'fast' if state.fast_mode else 'standard'}\n",
                )
            )
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
            *(
                [
                    (
                        "class:row-on",
                        _t(
                            state,
                            "apply_fast",
                            value=(
                                _t(state, "done_fast_on")
                                if state.fast_mode
                                else _t(state, "done_fast_off")
                            ),
                        ),
                    )
                ]
                if state.writer == "codex"
                else []
            ),
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
            (
                "class:row-on",
                _t(
                    state,
                    "apply_critique",
                    crit=_apply_critique_summary(),
                ),
            ),
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

    def _apply_critique_summary() -> str:
        pc = state.stages.get("plan_critique") or {}
        if not pc.get("enabled"):
            return _t(state, "off")
        return f"{pc.get('mode')}/{pc.get('provider')}"

    bodies: dict[str, Callable[[], list[tuple[str, str]]]] = {
        "coder": body_coder,
        "stages": body_stages,
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
        if w != "codex":
            state.fast_mode = False
        _sync_stages_from_coder_night()
        state.message = _t(
            state, "msg_coder", name=WRITER_META.get(w, {}).get("title", w)
        )

    def open_pick(kind: str) -> None:
        if kind == "fast":
            state.fast_mode = not state.fast_mode
            state.message = _t(
                state,
                "msg_fast",
                value=_t(state, "on") if state.fast_mode else _t(state, "off"),
            )
            return
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
        fields = _coder_fields()
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
            elif kind == "fast":
                state.fast_mode = chosen == "on"
                state.message = _t(
                    state,
                    "msg_fast",
                    value=_t(state, "on") if state.fast_mode else _t(state, "off"),
                )
            else:
                state.effort = chosen
                state.message = _t(state, "msg_effort", name=chosen)
                state.field_i = 2
        else:
            state.message = _t(state, "msg_cancelled")
        state.view = "form"
        state.field_i = max(0, min(state.field_i, len(fields) - 1))
        state.focus = fields[state.field_i]

    def move_form_field(delta: int) -> None:
        state.view = "form"
        fields = _coder_fields()
        state.field_i = (state.field_i + delta) % len(fields)
        state.focus = fields[state.field_i]
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

        _sync_stages_from_coder_night()
        profile, lanes, notes = doctor.pick_profile(state.tools, state.writer)
        model = state.model if state.writer != "auto" else None
        effort = state.effort if state.writer != "auto" else None
        write = getattr(doctor, "write_outputs", None)
        if write is None:
            raise RuntimeError("doctor.write_outputs missing")
        sink = io.StringIO()
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                # Night file first so write_outputs can read enabled flag if needed.
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
                service_tier = (
                    ("fast" if state.fast_mode else "standard")
                    if state.writer == "codex"
                    else None
                )
                try:
                    write(
                        state.repo,
                        state.tools,
                        profile,
                        lanes,
                        notes,
                        writer_model=model,
                        writer_effort=effort,
                        writer_service_tier=service_tier,
                        workspace_mode=state.workspace_mode,
                        worktree_min_score=state.worktree_min_score,
                        worktree_on_multi_write=state.worktree_on_multi_write,
                        ui_language=state.lang,
                        stages=state.stages,
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
                                quiet=True,
                            )
                        except TypeError:
                            write(state.repo, state.tools, profile, lanes, notes)
        except Exception as exc:  # noqa: BLE001
            state.message = _t(state, "msg_apply_fail", err=exc)
            return

        _save_global_lang(state.lang)
        state.message = _t(state, "msg_saved")
        pc = state.stages.get("plan_critique") or {}
        result = {
            "ok": True,
            "repo": str(state.repo),
            "writer": state.writer,
            "model": state.model,
            "effort": state.effort,
            "service_tier": (
                ("fast" if state.fast_mode else "standard")
                if state.writer == "codex"
                else None
            ),
            "fast_mode": bool(state.fast_mode) if state.writer == "codex" else False,
            "workspace_mode": state.workspace_mode,
            "lang": state.lang,
            "night": state.night_review,
            "night_provider": state.night_provider if state.night_review else None,
            "max_fix_tasks": state.max_fix_tasks if state.night_review else None,
            "critique": (
                f"{pc.get('mode')}/{pc.get('provider')}"
                if pc.get("enabled")
                else "off"
            ),
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
            fields = _coder_fields()
            state.field_i = max(0, min(state.field_i, len(fields) - 1))
            state.focus = fields[state.field_i]

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
        elif tid == "stages":
            # Pull latest coder/night into stages once when opening the tab.
            _sync_stages_from_coder_night()
            state.focus = "stage_field"
            state.stage_field_i = 0
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
                fields = _coder_fields()
                state.field_i = max(0, min(state.field_i, len(fields) - 1))
                open_pick(fields[state.field_i])
            return
        if tid == "stages":
            # Always cycle the focused field value forward.
            _cycle_stage_field(1)
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
        if tid == "stages":
            # Always cycle the focused field value backward.
            _cycle_stage_field(-1)
            return
        tab_i["i"] = (tab_i["i"] - 1) % len(TAB_IDS)
        on_tab_enter()

    for n in range(1, 8):

        @kb.add(str(n))
        def _(event, n=n) -> None:
            leave_pick_if_any()
            # On Stages tab, 1–4 pick a pipeline stage (not a top tab).
            if TAB_IDS[tab_i["i"]] == "stages" and 1 <= n <= len(STAGE_IDS):
                _select_stage(n - 1)
                return
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
        elif tid == "stages":
            _move_stage_field(-1)
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
        elif tid == "stages":
            _move_stage_field(1)
        elif tid == "work":
            move_work_mode(1)
        elif tid == "ui":
            move_ui_lang(1)
        elif tid == "night" and state.night_review:
            move_night_writer(1)

    # Stage prev/next — layout-safe (works on RU keyboards; [ ] often don't).
    @kb.add("p")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "stages":
            _move_stage(-1)
        elif tid == "coder":
            state.field_i = 0
            open_pick("writer")

    @kb.add("n")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "stages":
            _move_stage(1)
        elif tid == "night" and state.night_review:
            state.focus = "night_writer"
            opts = [w for w in state.writers if w != "auto"]
            if opts and state.night_provider in opts:
                state.cursor = opts.index(state.night_provider)
            state.message = _t(state, "msg_night_writer")

    @kb.add("[")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "stages":
            _move_stage(-1)

    @kb.add("]")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "stages":
            _move_stage(1)

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

    @kb.add(" ")
    def _(event) -> None:
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                close_pick(confirm=True)
            else:
                fields = _coder_fields()
                state.field_i = max(0, min(state.field_i, len(fields) - 1))
                open_pick(fields[state.field_i])
        elif tid == "stages":
            _cycle_stage_field(1)
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
            _sync_stages_from_coder_night()
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
                fields = _coder_fields()
                state.field_i = max(0, min(state.field_i, len(fields) - 1))
                open_pick(fields[state.field_i])
        elif tid == "stages":
            _cycle_stage_field(1)
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
            _sync_stages_from_coder_night()
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
                height=2,
                style="class:sum",
            ),
            Window(content=FormattedTextControl(footer), height=1, style="class:ftr"),
        ]
    )

    style = Style.from_dict(
        {
            "hdr": "bg:#0b0e14 #c0caf5",
            "brand": "bg:#0b0e14 #7aa2f7 bold",
            "hdr-title": "bg:#0b0e14 #c0caf5 bold",
            "hdr-sub": "bg:#0b0e14 #565f89",
            "pipe-badge": "bg:#bb9af7 #0b0e14 bold",
            "tabbar": "bg:#12131a #565f89",
            "tab-on": "bg:#7aa2f7 #0b0e14 bold",
            "tab-off": "bg:#1a1b26 #a9b1d6",
            "tab-hint": "bg:#12131a #7dcfff",
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
            "stage-focus": "bold #73daca reverse",
            "stage-on": "bold #9ece6a",
            "stage-off": "#565f89",
            "sum": "bg:#12131a #a9b1d6",
            "sum-label": "bg:#12131a #7aa2f7",
            "sum-hi": "bg:#12131a #9ece6a bold",
            "sum-dim": "bg:#12131a #565f89",
            "sum-on": "bg:#12131a #9ece6a bold",
            "pipe": "bg:#12131a #565f89",
            "pipe-node": "bg:#12131a #7aa2f7 bold",
            "pipe-arrow": "bg:#12131a #3b4261",
            "pipe-on": "bg:#12131a #e0af68 bold",
            "pipe-off": "bg:#12131a #414868",
            "pipe-write": "bg:#12131a #9ece6a bold",
            "pipe-night": "bg:#12131a #bb9af7 bold",
            "pipe-spec": "bg:#12131a #f7768e bold",
            "ftr": "bg:#0b0e14 #a9b1d6",
            "ftr-msg": "bg:#0b0e14 #9ece6a",
            "ftr-keys": "bg:#0b0e14 #565f89",
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
        _print_apply_receipt(result)
        return 0
    return int(result or 0) if isinstance(result, int) else 0


def _print_apply_receipt(result: dict[str, Any]) -> None:
    """Pretty post-Apply summary: includes Fast mode for Codex."""
    agents = Path(result["repo"]) / ".agents"
    lang = normalize_lang(result.get("lang") or "en")
    writer = str(result.get("writer") or "—")
    tier = str(result.get("service_tier") or "").strip().lower()
    is_codex = writer == "codex"

    if result.get("night"):
        night_v = tr(
            lang,
            "done_night_on",
            provider=result.get("night_provider") or "—",
            max=result.get("max_fix_tasks") or "—",
        )
    else:
        night_v = tr(lang, "done_night_off")

    rows: list[tuple[str, str]] = [
        (tr(lang, "done_lbl_path"), str(result.get("repo") or "—")),
        (tr(lang, "done_lbl_coder"), writer),
        (tr(lang, "done_lbl_model"), str(result.get("model") or "—")),
        (tr(lang, "done_lbl_effort"), str(result.get("effort") or "—")),
    ]
    if is_codex:
        fast_on = tier == "fast" or result.get("fast_mode") is True
        rows.append(
            (
                tr(lang, "done_lbl_fast"),
                tr(lang, "done_fast_on") if fast_on else tr(lang, "done_fast_off"),
            )
        )
    rows.extend(
        [
            (tr(lang, "done_lbl_ws"), str(result.get("workspace_mode") or "auto")),
            (tr(lang, "done_lbl_lang"), lang),
            (tr(lang, "done_lbl_night"), night_v),
            (tr(lang, "done_lbl_critique"), str(result.get("critique") or "—")),
        ]
    )

    files = [
        tr(lang, "done_file_routing"),
        tr(lang, "done_file_night"),
    ]
    file_paths = [
        str(agents / "routing.profile.yaml"),
        str(agents / "night-shift.yaml"),
    ]

    # Column widths for a clean table inside a box
    label_w = max(len(lbl) for lbl, _ in rows)
    label_w = max(label_w, len(tr(lang, "done_lbl_files")))
    value_w = max(len(val) for _, val in rows)
    value_w = max(value_w, max(len(p) for p in file_paths), 40)
    # Cap ultra-long paths for terminal readability
    value_w = min(value_w, 72)
    inner = label_w + 3 + value_w  # "lbl · val"
    title = tr(lang, "done_title")
    # Box width fits title or content
    width = max(inner + 4, len(title) + 4, 48)

    def _clip(text: str, n: int) -> str:
        if len(text) <= n:
            return text
        if n <= 1:
            return text[:n]
        return text[: n - 1] + "…"

    def _hline(left: str, mid: str, right: str) -> str:
        return f"{left}{'─' * (width - 2)}{right}"

    def _row(text: str) -> str:
        body = _clip(text, width - 4)
        return f"│ {body}{' ' * (width - 4 - len(body))} │"

    def _kv(label: str, value: str) -> str:
        lbl = f"{label:<{label_w}}"
        val = _clip(value, value_w)
        return _row(f"{lbl}  {val}")

    print()
    print(_hline("╭", "─", "╮"))
    # Title centered-ish
    pad = max(0, width - 4 - len(title))
    left_pad = pad // 2
    right_pad = pad - left_pad
    print(f"│ {' ' * left_pad}{title}{' ' * right_pad} │")
    print(_hline("├", "─", "┤"))
    for lbl, val in rows:
        print(_kv(lbl, val))
    print(_hline("├", "─", "┤"))
    print(_kv(tr(lang, "done_lbl_files"), ""))
    for path in file_paths:
        print(_row(f"  · {_clip(path, width - 8)}"))
    print(_hline("╰", "─", "╯"))
    print()
    print(f"  {tr(lang, 'done_hint')}")
    print()


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

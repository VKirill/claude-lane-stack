#!/usr/bin/env python3
"""Full-screen TUI for agents-doctor — conveyor stages / coder / work / night.

Layout:
  header
  sidebar (sections) | main (working content)
  pipeline strip · footer
  Keyboard + mouse.

Inspired by modern ops TUIs (k9s / lazygit style focus + badges):
  clear stages, radio cards, live conveyor strip, EN/RU.

Coder UX: form + drill-down lists (↑↓ fields, Enter open list).
Stages UX: customize plan_critique / write / night / specialist / onboard.
Memory and Docs are their own tabs.
UI language: en | ru (project ui.language + global ~/.agents/doctor.ui.yaml).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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
    DEFAULT_OPENCODE_WRITE_AGENT,
    KNOWN_STAGE_PROVIDERS,
    default_opencode_agent,
    default_stages,
    normalize_stages,
    resolve_opencode_agent,
)
from routing_profile import resolve_agy_effort  # type: ignore  # noqa: E402

# Form field order on the Coder tab (stable indices for ↑↓).
CODER_FIELDS = ("writer", "model", "effort", "fast")  # fast only when writer=codex

# Stage cards on the Stages tab (pipeline roles, not Claude subagents).
STAGE_IDS = (
    "plan_critique",
    "write",
    "night_review",
    "specialist",
    "onboard",
)
MODULE_TAB_IDS = ("memory", "docs")
# Full agent catalog for stages (not limited to currently detected CLIs).
ALL_AGENTS = ("kimi", "qwen", "grok", "agy", "codex", "cursor", "opencode")
CRITIQUE_PROVIDERS = ("structural",) + ALL_AGENTS
STAGE_FIELD_CRITIQUE = ("enabled", "mode", "provider", "model", "effort")
STAGE_FIELD_WRITE = ("provider", "model", "effort")  # enabled always on
STAGE_FIELD_NIGHT = ("enabled", "provider", "model", "effort")
STAGE_FIELD_SPEC = ("enabled", "when", "provider", "model", "effort")
STAGE_FIELD_ONBOARD = ("provider", "model", "effort", "fast")  # fast: codex/cursor
STAGE_FIELD_MEMORY = (
    "enabled",
    "maintain",
    "inject",
    "provider",
    "model",
    "effort",
    "audience",
    "personal_bot",
    "search_engine",
    "core_budget",
    "note_budget",
    "index_budget",
    "context_budget",
)
STAGE_FIELD_DOCS = (
    "enabled",
    "maintain",
    "provider",
    "model",
    "effort",
    "page_cap",
    "since",
    "hour",
)
DOCS_PAGE_CAPS = (0, 8, 16, 24, 48)
DOCS_SINCE_OPTS = ("yesterday", "24 hours ago", "7 days ago")
DOCS_HOURS = tuple(range(24))
MEMORY_BUDGET_STEPS = {
    "core_budget": (1536, 2048, 3072, 4096, 6144),
    "note_budget": (4000, 8000, 12000, 16000),
    "index_budget": (32768, 65536, 131072),
    "context_budget": (1500, 2500, 4000, 6000),
}
MEMORY_AUDIENCE_OPTS = ("subagent", "owner", "export")
MEMORY_ENGINE_OPTS = ("auto", "fts5", "bm25")
MEMORY_BOT_OPTS = ("", "claude", "codex", "grok", "qwen", "kimi", "agy", "cursor")

# Fallback Cursor catalog when `cursor-agent --list-models` is unavailable.
CURSOR_MODEL_FALLBACK = [
    "auto",
    "composer-2.5",
    "composer-2.5-fast",
    "cursor-grok-4.6-low",
    "cursor-grok-4.6-low-fast",
    "cursor-grok-4.6-medium",
    "cursor-grok-4.6-medium-fast",
    "cursor-grok-4.6-high",
    "cursor-grok-4.6-high-fast",
    "cursor-grok-4.6-xhigh",
    "cursor-grok-4.6-xhigh-fast",
    "cursor-grok-4.5-high",
    "cursor-grok-4.5-high-fast",
    "cursor-grok-4.5-medium",
    "cursor-grok-4.5-medium-fast",
    "claude-sonnet-5-thinking-high",
    "claude-opus-5-thinking-high",
    "gpt-5.6-sol-high",
    "gpt-5.5-high",
    "kimi-k3-high",
]

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
        "grok-4.6",
        "grok-4.5",
        "grok-4",
        "grok-3",
        "grok-3-mini",
    ],
    "agy": [
        "gemini-3.7-flash-high",
        "gemini-3.7-flash-medium",
        "gemini-3.7-flash-low",
        "gemini-3.6-flash-high",
        "gemini-3.6-flash-medium",
        "gemini-3.6-flash-low",
        "gemini-3.5-flash-high",
        "gemini-3.1-pro-high",
        "claude-sonnet-4-6",
        "claude-opus-4-6-thinking",
        "gpt-oss-120b-medium",
    ],
    "codex": [
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
        "gpt-5.4",
        "o4-mini",
    ],
    "cursor": list(CURSOR_MODEL_FALLBACK),
    "opencode": [
        "alibaba-token-plan/qwen3.8-max-preview",
        "google/gemini-3.6-flash",
        "opencode/gpt-5-nano",
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
    "cursor": ["low", "medium", "high"],
    "opencode": ["low", "medium", "high"],
    "structural": ["low", "medium", "high"],
    "auto": ["medium"],
}

WRITER_META: dict[str, dict[str, str]] = {
    "qwen": {"title": "Qwen", "badge": "FAST"},
    "kimi": {"title": "Kimi", "badge": "LONG CTX"},
    "grok": {"title": "Grok", "badge": "XAI"},
    "agy": {"title": "AGY", "badge": "GEMINI"},
    "codex": {"title": "Codex", "badge": "OPENAI"},
    "cursor": {"title": "Cursor", "badge": "AGENT"},
    "opencode": {"title": "OpenCode", "badge": "MULTI"},
    "auto": {"title": "Auto", "badge": "STACK"},
}

DEFAULT_MODEL = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.7-flash-high",
    "codex": "gpt-5.6-luna",
    "cursor": "composer-2.5",
    "opencode": "alibaba-token-plan/qwen3.8-max-preview",
    "auto": "(stack default)",
}

DEFAULT_EFFORT = {
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "high",
    "codex": "max",
    "cursor": "medium",
    "opencode": "medium",
    "auto": "medium",
}

# Tab ids (labels come from i18n).
TAB_IDS = (
    "coder",
    "stages",
    "memory",
    "docs",
    "work",
    "night",
    "ui",
    "status",
    "info",
    "apply",
)

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
        agent: str = DEFAULT_OPENCODE_WRITE_AGENT,
        fast_mode: bool = False,
        night_review: bool = False,
        night_provider: str = "qwen",
        max_fix_tasks: int = 5,
        auto_merge: bool = False,
        workspace_mode: str = "auto",
        worktree_min_score: int = 4,
        worktree_on_multi_write: bool = True,
        session_max_tasks: int = 10,
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
        self.agent = agent or DEFAULT_OPENCODE_WRITE_AGENT
        self.effort = effort
        self.fast_mode = bool(fast_mode)
        self.night_review = night_review
        self.night_provider = night_provider
        self.max_fix_tasks = max_fix_tasks
        self.auto_merge = auto_merge
        self.workspace_mode = workspace_mode
        self.worktree_min_score = worktree_min_score
        self.worktree_on_multi_write = worktree_on_multi_write
        self.session_max_tasks = session_max_tasks
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
                    elif s.startswith("agent:"):
                        out["agent"] = s.split(":", 1)[1].strip().split()[0].strip("\"'")
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
                    elif s.startswith("session_max_tasks:"):
                        try:
                            out["session_max_tasks"] = int(
                                s.split(":", 1)[1].strip().split()[0]
                            )
                        except ValueError:
                            pass
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


_CURSOR_MODELS_CACHE: list[str] | None = None
_AGY_MODELS_CACHE: list[str] | None = None
_OPENCODE_AGENT_FALLBACK = [
    "lane-writer",
    "lane-critic",
    "lane-reviewer",
    "build",
    "plan",
    "general",
    "explore",
    "scout",
]
_OPENCODE_NON_CODE = (
    "image",
    "veo-",
    "lyria",
    "embedding",
    "tts",
    "i2v",
    "t2v",
    "r2v",
    "computer-use",
)
# Live `opencode models --verbose` / `agent list` for this adoc visit only.
# Refreshed on launch, rescan, OpenCode writer pick, and opening the list.
# variants: model id → catalog variant names (empty list = no --variant).
_OPENCODE_LIVE: dict[str, Any] = {
    "models": None,
    "agents": None,
    "variants": None,
}


def _supports_fast(writer: str) -> bool:
    return writer in {"codex", "cursor"}


def _probe_cursor_models() -> list[str]:
    """Live catalog from cursor-agent --list-models (cached per process)."""
    global _CURSOR_MODELS_CACHE
    if _CURSOR_MODELS_CACHE is not None:
        return list(_CURSOR_MODELS_CACHE)
    binary = shutil.which("cursor-agent") or shutil.which("agent")
    models: list[str] = []
    if binary:
        try:
            out = subprocess.check_output(
                [binary, "--list-models"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=12,
            )
            for line in out.splitlines():
                token = line.strip().split()[0] if line.strip() else ""
                if not token or token.lower() in {"available", "models", "model"}:
                    continue
                # lines like: "composer-2.5 - Composer 2.5"
                if token.endswith("-") or token.startswith("-"):
                    continue
                if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", token):
                    models.append(token)
        except (OSError, subprocess.SubprocessError, ValueError):
            models = []
    if not models:
        models = list(CURSOR_MODEL_FALLBACK)
    # Prefer non-fast siblings first for picker clarity; keep -fast entries too.
    _CURSOR_MODELS_CACHE = list(dict.fromkeys(models))
    WRITER_MODELS["cursor"] = list(_CURSOR_MODELS_CACHE)
    return list(_CURSOR_MODELS_CACHE)


def _probe_agy_models() -> list[str]:
    """Live catalog from `agy models` (cached per process)."""
    global _AGY_MODELS_CACHE
    if _AGY_MODELS_CACHE is not None:
        return list(_AGY_MODELS_CACHE)
    binary = shutil.which("agy")
    models: list[str] = []
    if binary:
        try:
            out = subprocess.check_output(
                [binary, "models"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=12,
            )
            for line in out.splitlines():
                token = line.strip().split()[0] if line.strip() else ""
                if (
                    token
                    and ("-" in token or "/" in token)
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", token)
                ):
                    models.append(token)
        except (OSError, subprocess.SubprocessError, ValueError):
            models = []
    if not models:
        models = list(WRITER_MODELS["agy"])
    _AGY_MODELS_CACHE = list(dict.fromkeys(models))
    WRITER_MODELS["agy"] = list(_AGY_MODELS_CACHE)
    return list(_AGY_MODELS_CACHE)


def _models_for(writer: str) -> list[str]:
    if writer == "cursor":
        return _probe_cursor_models()
    if writer == "agy":
        return _probe_agy_models()
    if writer == "opencode":
        return _probe_opencode_models()
    return list(WRITER_MODELS.get(writer, ["(default)"]))


def _looks_opencode_code_model(model_id: str) -> bool:
    low = model_id.lower()
    return not any(token in low for token in _OPENCODE_NON_CODE)


def _variant_names(raw: Any) -> list[str]:
    if isinstance(raw, dict):
        return [str(key) for key in raw if str(key).strip()]
    if isinstance(raw, list):
        names: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
            elif isinstance(item, dict):
                ident = str(item.get("id") or "").strip()
                if ident:
                    names.append(ident)
        return names
    return []


def parse_opencode_models_verbose(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Parse `opencode models --verbose` into ids + per-model variants."""
    models: list[str] = []
    variants: dict[str, list[str]] = {}
    header: str | None = None
    buf: list[str] = []
    depth = 0
    ident_re = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
    for line in text.splitlines():
        stripped = line.strip()
        if depth == 0 and not buf:
            if not stripped.startswith("{"):
                token = stripped.split()[0] if stripped else ""
                if token and "/" in token and ident_re.fullmatch(token):
                    header = token
                continue
        if header is None:
            continue
        if "{" in line or "}" in line or buf:
            buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth == 0 and buf:
                try:
                    data = json.loads("\n".join(buf))
                except ValueError:
                    data = {}
                mid = header
                names: list[str] = []
                if isinstance(data, dict):
                    pid = str(data.get("providerID") or "").strip()
                    iid = str(data.get("id") or "").strip()
                    if pid and iid:
                        mid = f"{pid}/{iid}"
                    names = _variant_names(data.get("variants"))
                if _looks_opencode_code_model(mid):
                    models.append(mid)
                    variants[mid] = names
                header = None
                buf = []
                depth = 0
    return list(dict.fromkeys(models)), variants


def _fetch_opencode_models() -> tuple[list[str], dict[str, list[str]] | None]:
    binary = shutil.which("opencode")
    models: list[str] = []
    variants: dict[str, list[str]] | None = None
    if binary:
        try:
            out = subprocess.check_output(
                [binary, "models", "--verbose"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=12,
            )
            models, variants = parse_opencode_models_verbose(out)
            if not models:
                for line in out.splitlines():
                    token = line.strip().split()[0] if line.strip() else ""
                    if not token or "/" not in token:
                        continue
                    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", token):
                        continue
                    if _looks_opencode_code_model(token):
                        models.append(token)
                variants = None
        except (OSError, subprocess.SubprocessError, ValueError):
            models = []
            variants = None
    if not models:
        models = list(WRITER_MODELS["opencode"])
        variants = None
    return list(dict.fromkeys(models)), variants


def _fetch_opencode_agents() -> list[str]:
    names: list[str] = list(_OPENCODE_AGENT_FALLBACK)
    binary = shutil.which("opencode")
    if binary:
        try:
            out = subprocess.check_output(
                [binary, "agent", "list"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=12,
            )
            for line in out.splitlines():
                match = re.match(
                    r"^([A-Za-z0-9][A-Za-z0-9_.-]*) \((primary|subagent|all)",
                    line,
                )
                if match:
                    names.append(match.group(1))
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    config = Path.home() / ".config" / "opencode" / "opencode.json"
    try:
        data = __import__("json").loads(config.read_text(encoding="utf-8"))
        agents = data.get("agent") or data.get("agents") or {}
        if isinstance(agents, dict):
            names.extend(str(key) for key in agents if key)
    except (OSError, ValueError):
        pass
    agents_dir = Path.home() / ".config" / "opencode" / "agents"
    if agents_dir.is_dir():
        names.extend(path.stem for path in agents_dir.glob("*.md") if path.stem)
    return list(dict.fromkeys(names))


def refresh_opencode_catalog() -> None:
    """Pull live OpenCode models/agents/variants. No disk; this adoc visit only."""
    models, variants = _fetch_opencode_models()
    _OPENCODE_LIVE["models"] = models
    _OPENCODE_LIVE["variants"] = variants
    _OPENCODE_LIVE["agents"] = _fetch_opencode_agents()


def _probe_opencode_models() -> list[str]:
    if _OPENCODE_LIVE["models"] is None:
        refresh_opencode_catalog()
    return list(_OPENCODE_LIVE["models"] or WRITER_MODELS["opencode"])


def _probe_opencode_agents() -> list[str]:
    if _OPENCODE_LIVE["agents"] is None:
        refresh_opencode_catalog()
    return list(_OPENCODE_LIVE["agents"] or _OPENCODE_AGENT_FALLBACK)


def _ensure_agent(agent: str) -> str:
    opts = _probe_opencode_agents()
    if agent in opts:
        return agent
    return opts[0] if opts else DEFAULT_OPENCODE_WRITE_AGENT


def _preferred_effort(opts: list[str]) -> str:
    for name in ("medium", "low", "high"):
        if name in opts:
            return name
    return opts[0] if opts else ""


def _efforts_for(writer: str, model: str = "") -> list[str]:
    if writer == "opencode":
        if _OPENCODE_LIVE.get("models") is None:
            refresh_opencode_catalog()
        live = _OPENCODE_LIVE.get("variants")
        if isinstance(live, dict):
            return list(live.get(model, []))
    if writer == "agy":
        name = str(model or "").strip().lower()
        for token in ("xhigh", "high", "medium", "low"):
            if name.endswith("-" + token):
                return [resolve_agy_effort(model, "")]
    return list(WRITER_EFFORTS.get(writer, ["medium"]))


def _ensure_model(writer: str, model: str) -> str:
    opts = _models_for(writer)
    if model in opts:
        return model
    return DEFAULT_MODEL.get(writer, opts[0])


def _ensure_effort(writer: str, effort: str, model: str = "") -> str:
    if writer == "agy":
        return resolve_agy_effort(model, effort)
    opts = _efforts_for(writer, model)
    if not opts:
        return ""
    if effort in opts:
        return effort
    return _preferred_effort(opts)


def _field_label(state: SetupState, kind: str) -> str:
    return {
        "writer": _t(state, "field_provider"),
        "model": _t(state, "field_model"),
        "effort": _t(state, "field_effort"),
        "fast": _t(state, "field_fast"),
        "agent": _t(state, "field_agent"),
    }.get(kind, kind)


def _ws_title(state: SetupState, mode: str) -> str:
    return _t(state, f"ws_{mode}_title")


def _ws_blurb(state: SetupState, mode: str) -> str:
    return _t(state, f"ws_{mode}_blurb")


def _tab_label(state: SetupState, tid: str) -> str:
    return _t(state, f"tab_{tid}")


def _tab_sub(state: SetupState, tid: str) -> str:
    return _t(state, f"tab_{tid}_sub")


# Lines above the first sidebar tab (title + blank). Click y maps through this.
SIDEBAR_TAB_PAD = 2


def pick_window(count: int, cursor: int, visible: int) -> tuple[int, int]:
    """[start, end) so cursor stays on screen. FormattedTextControl does not scroll."""
    if count <= 0:
        return 0, 0
    vis = max(1, visible)
    cur = max(0, min(cursor, count - 1))
    if count <= vis:
        return 0, count
    start = max(0, cur - vis // 3)
    end = start + vis
    if end > count:
        end = count
        start = max(0, end - vis)
    if cur < start:
        start = cur
        end = min(count, start + vis)
    if cur >= end:
        end = cur + 1
        start = max(0, end - vis)
    return start, end


def pick_visible_rows() -> int:
    try:
        from prompt_toolkit.application.current import get_app

        rows = get_app().output.get_size().rows
    except Exception:
        rows = 24
    # hdr2 + tabbar2 + rule1 + sum2 + ftr1 + pick header/footer ~5 + ▲▼ reserve 2
    return max(8, rows - 15)


def sidebar_hit(y: int, ntabs: int = len(TAB_IDS), pad: int = SIDEBAR_TAB_PAD) -> int | None:
    """Map a click row in the sidebar to a tab index, or None."""
    i = y - pad
    if 0 <= i < ntabs:
        return i
    return None


def run_tui(repo: Path, doctor: Any) -> int:
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, VSplit, Window
        from prompt_toolkit.mouse_events import MouseEventType
        from prompt_toolkit.styles import Style
    except ImportError:
        print(tr("en", "err_no_pt"), file=sys.stderr)
        return doctor.run_setup(repo, interactive=True)

    # PT 3.0.x: mouse is a method, not a FormattedTextControl() kwarg.
    class ClickControl(FormattedTextControl):
        def __init__(self, text, on_mouse=None, **kwargs):
            super().__init__(text, **kwargs)
            self._on_mouse = on_mouse

        def mouse_handler(self, mouse_event):
            if self._on_mouse is None:
                return super().mouse_handler(mouse_event)
            self._on_mouse(mouse_event)
            return None

    tools = doctor.detect()
    if not tools.get("claude", {}).get("present"):
        print(tr("en", "err_no_claude"), file=sys.stderr)
        return 1

    writers = list(doctor.available_writers(tools))
    if tools.get("codex", {}).get("present") and "codex" not in writers:
        writers.append("codex")
    if tools.get("cursor", {}).get("present") and "cursor" not in writers:
        writers.append("cursor")
    if tools.get("opencode", {}).get("present") and "opencode" not in writers:
        writers.append("opencode")
    if not writers:
        writers = ["auto"]
    if shutil.which("opencode"):
        refresh_opencode_catalog()

    suggested = doctor.default_setup_writer(tools)
    existing = _load_existing(repo)
    writer0 = existing.get("writer")
    if writer0 not in writers:
        writer0 = suggested if suggested in writers else writers[0]
    model0 = _ensure_model(writer0, existing.get("model") or DEFAULT_MODEL.get(writer0, ""))
    effort0 = _ensure_effort(
        writer0,
        existing.get("effort") or DEFAULT_EFFORT.get(writer0, "medium"),
        model0,
    )
    agent0 = existing.get("agent") or (
        (existing.get("stages_raw") or {}).get("write") or {}
    ).get("agent") or DEFAULT_OPENCODE_WRITE_AGENT
    if writer0 == "opencode":
        agent0 = _ensure_agent(resolve_opencode_agent("write", str(agent0)))
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
        agent=agent0,
        fast_mode=bool(existing.get("fast_mode", False)) and _supports_fast(writer0),
        night_review=bool(existing.get("night_review", False)),
        night_provider=night_w0,
        max_fix_tasks=int(existing.get("max_fix_tasks", 5)),
        auto_merge=bool(existing.get("auto_merge", False)),
        workspace_mode=ws0,
        worktree_min_score=ws_score0,
        worktree_on_multi_write=bool(existing.get("worktree_on_multi_write", True)),
        session_max_tasks=max(
            1, min(10, int(existing.get("session_max_tasks", 10)))
        ),
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
    pick_view = {"start": 0, "header": 3}
    pane = {"col": "main"}  # "nav" | "main"

    def _sync_stages_from_coder_night() -> None:
        """Keep stages.write / night_review in lockstep with Coder + Night tabs."""
        st = state.stages
        st["write"]["provider"] = (
            state.writer if state.writer != "auto" else st["write"].get("provider", "kimi")
        )
        st["write"]["model"] = state.model
        st["write"]["reasoning_effort"] = state.effort
        if state.writer == "opencode":
            st["write"]["agent"] = state.agent or DEFAULT_OPENCODE_WRITE_AGENT
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
                prov, str(w.get("reasoning_effort") or state.effort), state.model
            )
            if prov == "opencode":
                state.agent = _ensure_agent(
                    resolve_opencode_agent(
                        "write",
                        str(w.get("agent") or state.agent or ""),
                    )
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

    def sidebar() -> list[tuple[str, str]]:
        nav_on = pane["col"] == "nav"
        parts: list[tuple[str, str]] = [
            ("class:side-title", f"  {_t(state, 'nav_title')}\n"),
            ("class:side", "\n"),
        ]
        for i, tid in enumerate(TAB_IDS):
            on = i == tab_i["i"]
            if on and nav_on:
                st = "class:side-on-focus"
            elif on:
                st = "class:side-on"
            else:
                st = "class:side-off"
            mark = "▸" if on else " "
            parts.append((st, f" {mark}{i + 1} {_tab_label(state, tid)}\n"))
        parts.append(("class:side", "\n"))
        parts.append(("class:side-hint", f"  {_t(state, 'nav_hint')}\n"))
        return parts

    def main_chrome() -> list[tuple[str, str]]:
        tid = TAB_IDS[tab_i["i"]]
        return [
            ("class:tab-on", f"  {_tab_label(state, tid)} "),
            ("class:tab-hint", f" {_tab_sub(state, tid)}\n"),
            ("class:tab-hint", "\n"),
        ]

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
        fields = ["writer", "model"]
        if state.writer == "opencode":
            fields.append("agent")
        if _efforts_for(state.writer, state.model):
            fields.append("effort")
        if _supports_fast(state.writer):
            fields.append("fast")
        return tuple(fields)

    def _options_for(kind: str) -> list[str]:
        if kind == "writer":
            return list(state.writers)
        if kind == "model":
            return _models_for(state.writer)
        if kind == "agent":
            return _probe_opencode_agents()
        if kind == "fast":
            return ["off", "on"]
        return _efforts_for(state.writer, state.model)

    def _current_value(kind: str) -> str:
        if kind == "writer":
            return state.writer
        if kind == "model":
            return state.model
        if kind == "agent":
            return state.agent
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
        efforts = _efforts_for(state.writer, state.model)
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
        ]
        if "agent" in fields:
            agents = _probe_opencode_agents()
            try:
                ai = agents.index(state.agent)
            except ValueError:
                ai = 0
            rows.append(
                (
                    "agent",
                    _t(state, "field_agent"),
                    state.agent,
                    f"{ai + 1}/{len(agents)}" if agents else "",
                )
            )
        if "effort" in fields:
            rows.append(
                (
                    "effort",
                    _t(state, "field_effort"),
                    state.effort,
                    " · ".join(
                        (f"[{x}]" if x == state.effort else x) for x in efforts
                    ),
                )
            )
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
        start, end = pick_window(len(opts), state.pick_cursor, pick_visible_rows())
        pick_view["start"] = start
        pick_view["header"] = 3 + (1 if start > 0 else 0)
        if start > 0:
            lines.append(("class:dim", f"  ▲  {start} ↑\n"))
        for i, opt in enumerate(opts[start:end], start=start):
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
        if end < len(opts):
            lines.append(("class:dim", f"  ▼  {len(opts) - end} ↓\n"))
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
            prov = str(
                (state.stages.get("plan_critique") or {}).get("provider") or ""
            )
            fields: tuple[str, ...] = STAGE_FIELD_CRITIQUE
            if _supports_fast(prov):
                fields = STAGE_FIELD_CRITIQUE + ("fast",)
        elif stage_id == "write":
            prov = str((state.stages.get("write") or {}).get("provider") or "")
            fields = STAGE_FIELD_WRITE
        elif stage_id == "night_review":
            prov = str((state.stages.get("night_review") or {}).get("provider") or "")
            fields = STAGE_FIELD_NIGHT
        elif stage_id == "onboard":
            prov = str((state.stages.get("onboard") or {}).get("provider") or "codex")
            fields = (
                STAGE_FIELD_ONBOARD
                if _supports_fast(prov)
                else ("provider", "model", "effort")
            )
        elif stage_id == "memory":
            prov = str((state.stages.get("memory") or {}).get("provider") or "codex")
            fields = STAGE_FIELD_MEMORY
            if _supports_fast(prov):
                lst = list(fields)
                lst.insert(lst.index("effort") + 1, "fast")
                fields = tuple(lst)
        elif stage_id == "docs":
            prov = str((state.stages.get("docs") or {}).get("provider") or "codex")
            fields = STAGE_FIELD_DOCS
            if _supports_fast(prov):
                lst = list(fields)
                lst.insert(lst.index("effort") + 1, "fast")
                fields = tuple(lst)
        else:
            prov = str((state.stages.get("specialist") or {}).get("provider") or "")
            fields = STAGE_FIELD_SPEC
        if prov == "opencode" and "agent" not in fields:
            out: list[str] = []
            for field in fields:
                out.append(field)
                if field == "model":
                    out.append("agent")
            fields = tuple(out)
        stage_model = str((state.stages.get(stage_id) or {}).get("model") or "")
        if prov == "opencode" and not _efforts_for(prov, stage_model):
            fields = tuple(field for field in fields if field != "effort")
        return fields

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

    def _efforts_for_provider(provider: str, model: str = "") -> list[str]:
        if provider == "structural":
            return ["low", "medium", "high"]
        return _efforts_for(provider, model)

    def _stage_field_value(stage_id: str, field: str) -> str:
        block = state.stages.get(stage_id) or {}
        if field == "enabled":
            return _loc_on(bool(block.get("enabled")))
        if field in {"maintain", "inject"}:
            return _loc_on(bool(block.get(field, True)))
        if field == "mode":
            return _loc_mode(str(block.get("mode") or "advisory"))
        if field == "when":
            return _loc_when(str(block.get("when") or "high_risk"))
        if field == "audience":
            key = f"audience_{block.get('audience') or 'subagent'}"
            text = _t(state, key)
            return text if text != key else str(block.get("audience") or "subagent")
        if field == "search_engine":
            key = f"engine_{block.get('search_engine') or 'auto'}"
            text = _t(state, key)
            return text if text != key else str(block.get("search_engine") or "auto")
        if field == "personal_bot":
            return str(block.get("personal_bot") or "—") or "—"
        if field == "provider":
            return _loc_provider(str(block.get("provider") or "—"))
        if field == "effort":
            return str(block.get("reasoning_effort") or block.get("effort") or "—")
        if field == "fast":
            tier = str(block.get("service_tier") or "standard").strip().lower()
            return _t(state, "on") if tier == "fast" else _t(state, "off")
        if field == "model":
            prov = str(block.get("provider") or "")
            if prov == "structural":
                return _t(state, "model_na")
            return str(block.get("model") or "—") or "—"
        if field == "hour":
            try:
                hour = int(block.get("hour") or 5)
            except (TypeError, ValueError):
                hour = 5
            return f"{hour:02d}:00"
        if field == "page_cap":
            try:
                cap = int(block.get("page_cap") or 0)
            except (TypeError, ValueError):
                cap = 0
            return _t(state, "page_cap_all") if cap <= 0 else str(cap)
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

    def _active_stage_id() -> str:
        tid = TAB_IDS[tab_i["i"]]
        if tid in MODULE_TAB_IDS:
            return tid
        return STAGE_IDS[state.stage_i]

    def _move_stage(delta: int) -> None:
        _select_stage((state.stage_i + delta) % len(STAGE_IDS))

    def _move_stage_field(delta: int) -> None:
        """Move across fields; wrap into neighbouring stages (stages tab only)."""
        state.focus = "stage_field"
        sid = _active_stage_id()
        fields = _stage_fields(sid)
        new_i = state.stage_field_i + delta
        if TAB_IDS[tab_i["i"]] in MODULE_TAB_IDS:
            state.stage_field_i = new_i % len(fields)
        elif new_i < 0:
            _move_stage(-1)
            fields = _stage_fields(STAGE_IDS[state.stage_i])
            state.stage_field_i = len(fields) - 1
        elif new_i >= len(fields):
            _move_stage(1)
            state.stage_field_i = 0
        else:
            state.stage_field_i = new_i
        sid = _active_stage_id()
        fields = _stage_fields(sid)
        state.stage_field_i = max(0, min(state.stage_field_i, len(fields) - 1))
        state.message = _t(
            state,
            "msg_focus",
            name=_t(state, f"sfield_{fields[state.stage_field_i]}"),
        )

    def _set_provider(block: dict[str, Any], new_p: str, *, stage_id: str) -> None:
        block["provider"] = new_p
        if new_p == "opencode":
            refresh_opencode_catalog()
            block["agent"] = _ensure_agent(default_opencode_agent(stage_id))
        else:
            block.pop("agent", None)
        if new_p == "structural":
            block["model"] = ""
            block.setdefault("reasoning_effort", "low")
        else:
            models = _models_for_provider(new_p)
            cur = str(block.get("model") or "")
            if cur not in models:
                block["model"] = models[0] if models else DEFAULT_MODELS.get(new_p, "")
            efforts = _efforts_for_provider(new_p, str(block.get("model") or ""))
            cur_e = str(block.get("reasoning_effort") or block.get("effort") or "")
            if not efforts:
                block["reasoning_effort"] = ""
            elif cur_e not in efforts:
                block["reasoning_effort"] = _preferred_effort(efforts)

    def _cycle_stage_field(delta: int = 1) -> None:
        """← / → / Space / Enter: change the focused field's value."""
        state.focus = "stage_field"
        sid = _active_stage_id()
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
            _set_provider(block, new_p, stage_id=sid)
            # Onboard defaults: terra+high (not daytime luna+max).
            if sid in {"onboard", "memory"} and new_p == "codex":
                if block.get("model") == DEFAULT_MODEL.get("codex"):
                    block["model"] = "gpt-5.6-terra"
                if block.get("reasoning_effort") == DEFAULT_EFFORT.get("codex"):
                    block["reasoning_effort"] = "high"
            if sid == "docs" and new_p == "codex":
                block["model"] = "gpt-5.6-luna"
                block["reasoning_effort"] = "max"
                block["service_tier"] = "fast"
            if sid in {"onboard", "plan_critique", "memory", "docs"} and not _supports_fast(new_p):
                block["service_tier"] = "standard"
            state.message = _t(
                state, "msg_stage_provider", provider=_loc_provider(new_p)
            )
        elif field == "model":
            prov = str(block.get("provider") or "qwen")
            if prov == "structural":
                # Auto-step to first real agent so user can pick models.
                _set_provider(
                    block,
                    "qwen" if delta >= 0 else "codex",
                    stage_id=sid,
                )
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
                if prov in {"opencode", "agy"}:
                    efforts = _efforts_for_provider(prov, str(block["model"]))
                    cur_e = str(block.get("reasoning_effort") or "")
                    if not efforts:
                        block["reasoning_effort"] = ""
                    elif cur_e not in efforts:
                        block["reasoning_effort"] = _preferred_effort(efforts)
                state.message = _t(
                    state, "msg_stage_model", model=block["model"]
                )
        elif field == "effort":
            prov = str(block.get("provider") or "qwen")
            opts = _efforts_for_provider(prov, str(block.get("model") or ""))
            if not opts:
                block["reasoning_effort"] = ""
                return
            cur = str(block.get("reasoning_effort") or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["reasoning_effort"] = opts[(i + delta) % len(opts)]
            state.message = _t(
                state, "msg_stage_effort", effort=block["reasoning_effort"]
            )
        elif field == "agent":
            opts = _probe_opencode_agents()
            if not opts:
                state.message = _t(state, "msg_no_opts", name=_t(state, "sfield_agent"))
                return
            cur = str(block.get("agent") or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["agent"] = opts[(i + delta) % len(opts)]
            state.message = _t(state, "msg_agent", name=block["agent"])
        elif field == "fast":
            prov = str(block.get("provider") or "")
            if not _supports_fast(prov):
                block["service_tier"] = "standard"
                state.message = _t(state, "msg_stage_fast_na")
            else:
                cur = str(block.get("service_tier") or "standard").strip().lower()
                block["service_tier"] = "standard" if cur == "fast" else "fast"
                state.message = _t(
                    state,
                    "msg_stage_fast",
                    value=_t(state, "on")
                    if block["service_tier"] == "fast"
                    else _t(state, "off"),
                )
        elif field in {"maintain", "inject"}:
            block[field] = not bool(block.get(field, True))
            state.message = _t(
                state,
                "msg_stage_flag",
                field=_t(state, f"sfield_{field}"),
                on=_loc_on(bool(block[field])),
            )
        elif field == "audience":
            cur = str(block.get("audience") or "subagent")
            try:
                i = MEMORY_AUDIENCE_OPTS.index(cur)
            except ValueError:
                i = 0
            block["audience"] = MEMORY_AUDIENCE_OPTS[(i + delta) % len(MEMORY_AUDIENCE_OPTS)]
            state.message = _t(state, "msg_stage_audience", audience=block["audience"])
        elif field == "search_engine":
            cur = str(block.get("search_engine") or "auto")
            try:
                i = MEMORY_ENGINE_OPTS.index(cur)
            except ValueError:
                i = 0
            block["search_engine"] = MEMORY_ENGINE_OPTS[(i + delta) % len(MEMORY_ENGINE_OPTS)]
            state.message = _t(state, "msg_stage_engine", engine=block["search_engine"])
        elif field == "personal_bot":
            cur = str(block.get("personal_bot") or "")
            try:
                i = MEMORY_BOT_OPTS.index(cur)
            except ValueError:
                i = 0
            block["personal_bot"] = MEMORY_BOT_OPTS[(i + delta) % len(MEMORY_BOT_OPTS)]
            state.message = _t(
                state, "msg_stage_bot", bot=block["personal_bot"] or "—"
            )
        elif field == "page_cap":
            opts = DOCS_PAGE_CAPS
            try:
                cur = int(block.get("page_cap") or 0)
            except (TypeError, ValueError):
                cur = 0
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["page_cap"] = opts[(i + delta) % len(opts)]
            shown = (
                _t(state, "page_cap_all")
                if int(block["page_cap"]) <= 0
                else str(block["page_cap"])
            )
            state.message = _t(state, "msg_stage_page_cap", n=shown)
        elif field == "since":
            opts = DOCS_SINCE_OPTS
            cur = str(block.get("since") or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = 0
            block["since"] = opts[(i + delta) % len(opts)]
            state.message = _t(state, "msg_stage_since", since=block["since"])
        elif field == "hour":
            try:
                cur = int(block.get("hour") or 5)
            except (TypeError, ValueError):
                cur = 5
            block["hour"] = (cur + delta) % 24
            state.message = _t(state, "msg_stage_hour", hour=f"{block['hour']:02d}:00")
        elif field in MEMORY_BUDGET_STEPS:
            opts = MEMORY_BUDGET_STEPS[field]
            cur = int(block.get(field) or opts[0])
            try:
                i = opts.index(cur)
            except ValueError:
                i = min(range(len(opts)), key=lambda j: abs(opts[j] - cur))
            block[field] = opts[(i + delta) % len(opts)]
            state.message = _t(
                state,
                "msg_stage_budget",
                field=_t(state, f"sfield_{field}"),
                n=block[field],
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
            if sid == "write":
                enabled = True
            elif sid == "onboard":
                enabled = True
            else:
                enabled = bool(block.get("enabled", True))
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
                if _supports_fast(prov) and str(block.get("service_tier") or "") == "fast":
                    detail += " · fast"
            elif sid == "night_review":
                detail = (
                    f"{_loc_on(enabled)} · {_loc_provider(prov)} · {model} · {effort}"
                )
            elif sid == "onboard":
                tier = str(block.get("service_tier") or "standard")
                fast_bit = (
                    f" · fast"
                    if _supports_fast(prov) and tier == "fast"
                    else ""
                )
                detail = f"{_loc_provider(prov)} · {model} · {effort}{fast_bit}"
            else:
                detail = (
                    f"{_loc_on(enabled)} · "
                    f"{_loc_when(str(block.get('when') or 'high_risk'))} · "
                    f"{_loc_provider(prov)} · {model} · {effort}"
                )
            lines.append((st, f"  {caret} {i + 1}. {title:<18}  [{badge}]\n"))
            lines.append(("class:row-detail", f"       {detail}\n"))
        sid = STAGE_IDS[state.stage_i]
        lines.append(
            (
                "class:h2",
                _t(state, "stages_fields_h2", stage=_t(state, f"stage_{sid}")),
            )
        )
        lines.extend(_stage_settings_rows(sid))
        lines.append(("class:help", _t(state, "stages_tip")))
        return lines

    def _stage_settings_rows(sid: str) -> list[tuple[str, str]]:
        fields = _stage_fields(sid)
        state.stage_field_i = max(0, min(state.stage_field_i, len(fields) - 1))
        rows: list[tuple[str, str]] = []
        for fi, field in enumerate(fields):
            focused = state.stage_field_i == fi
            st = "class:row-on-focus" if focused else "class:row"
            caret = "▸" if focused else " "
            val = _stage_field_value(sid, field)
            label = _t(state, f"sfield_{field}")
            hint = ""
            if focused and field == "provider":
                n = len(_providers_for_stage(sid))
                hint = f"  ←→ {n}"
            elif focused and field == "model":
                prov = str((state.stages.get(sid) or {}).get("provider") or "")
                n = len(_models_for_provider(prov))
                hint = f"  ←→ {n}" if n else f"  ({_t(state, 'model_na')})"
            elif focused and field in {
                "mode",
                "when",
                "effort",
                "enabled",
                "fast",
                "agent",
                "maintain",
                "inject",
                "audience",
                "personal_bot",
                "search_engine",
                "core_budget",
                "note_budget",
                "index_budget",
                "context_budget",
                "page_cap",
                "since",
                "hour",
            }:
                hint = "  ←→"
            rows.append((st, f"  {caret} {label:<14}  {val}{hint}\n"))
        return rows

    def body_memory() -> list[tuple[str, str]]:
        if state.focus not in {"stage_field", "stage_list"}:
            state.focus = "stage_field"
        return [
            ("class:h1", _t(state, "memory_h1")),
            ("class:help", _t(state, "memory_help")),
            ("class:h2", _t(state, "memory_fields_h2")),
            *_stage_settings_rows("memory"),
            ("class:h2", _t(state, "memory_info_h2")),
            ("class:help", _t(state, "memory_info")),
        ]

    def body_docs() -> list[tuple[str, str]]:
        if state.focus not in {"stage_field", "stage_list"}:
            state.focus = "stage_field"
        return [
            ("class:h1", _t(state, "docs_h1")),
            ("class:help", _t(state, "docs_help")),
            ("class:h2", _t(state, "docs_fields_h2")),
            *_stage_settings_rows("docs"),
            ("class:h2", _t(state, "docs_info_h2")),
            ("class:help", _t(state, "docs_info")),
        ]

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
        bar = "●" * state.session_max_tasks + "○" * (10 - state.session_max_tasks)
        lines.append(("class:h2", _t(state, "work_session_h2")))
        lines.append(
            (
                "class:row-on",
                _t(state, "work_session_line", n=state.session_max_tasks),
            )
        )
        lines.append(("class:dim", f"  {bar}\n"))
        lines.append(("class:help", _t(state, "work_session_hint")))
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
        order = [
            "claude",
            "qwen",
            "kimi",
            "grok",
            "agy",
            "codex",
            "cursor",
            "opencode",
            "bubblewrap",
        ]
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
        if _supports_fast(state.writer):
            lines.append(
                (
                    "class:dim",
                    f"    service_tier     {'fast' if state.fast_mode else 'standard'}\n",
                )
            )
        lines.append(("class:dim", f"    workspace        {state.workspace_mode}\n"))
        lines.append(
            ("class:dim", f"    session_max      {state.session_max_tasks}\n")
        )
        lines.append(("class:dim", f"    language         {state.lang}\n"))
        if notes:
            for n in notes:
                lines.append(("class:warn", f"    · {n}\n"))
        lines.append(("class:help", _t(state, "status_rescan")))
        return lines

    def body_info() -> list[tuple[str, str]]:
        return [
            ("class:h1", _t(state, "info_h1")),
            ("class:help", _t(state, "info_help")),
            ("class:h2", _t(state, "info_roles_h2")),
            ("class:row", _t(state, "info_roles")),
            ("class:h2", _t(state, "info_pipe_h2")),
            ("class:row", _t(state, "info_pipe")),
            ("class:h2", _t(state, "info_start_h2")),
            ("class:row", _t(state, "info_start")),
            ("class:h2", _t(state, "info_cmds_h2")),
            ("class:row-on", _t(state, "info_cmds")),
            ("class:help", _t(state, "info_onboard_note")),
        ]

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
                if _supports_fast(state.writer)
                else []
            ),
            (
                "class:row-on",
                _t(state, "apply_workspace", ws=_ws_title(state, state.workspace_mode)),
            ),
            (
                "class:row-on",
                _t(state, "apply_session", n=state.session_max_tasks),
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
        summary = f"{pc.get('mode')}/{pc.get('provider')}"
        if _supports_fast(str(pc.get("provider") or "")) and str(
            pc.get("service_tier") or ""
        ) == "fast":
            summary += "/fast"
        return summary

    bodies: dict[str, Callable[[], list[tuple[str, str]]]] = {
        "coder": body_coder,
        "stages": body_stages,
        "memory": body_memory,
        "docs": body_docs,
        "work": body_work,
        "night": body_night,
        "ui": body_ui,
        "status": body_status,
        "info": body_info,
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
            ("class:ftr-msg", (state.message or "")[:36]),
            ("class:ftr", "  ·  "),
            ("class:ftr-keys", f"{_t(state, 'keys_nav')} · {keys_txt}"),
        ]

    def main_view() -> list[tuple[str, str]]:
        return bodies[TAB_IDS[tab_i["i"]]]()

    # ── actions ───────────────────────────────────────────────────────────

    def set_writer(w: str) -> None:
        state.writer = w
        if w == "opencode":
            refresh_opencode_catalog()
            state.agent = _ensure_agent(default_opencode_agent("write"))
        state.model = _ensure_model(w, DEFAULT_MODEL.get(w, state.model))
        state.effort = _ensure_effort(
            w, DEFAULT_EFFORT.get(w, state.effort), state.model
        )
        if not _supports_fast(w):
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
        if kind in {"model", "agent"} and state.writer == "opencode":
            refresh_opencode_catalog()
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

    def _apply_coder_value(kind: str, chosen: str) -> None:
        if kind == "writer":
            set_writer(chosen)
        elif kind == "model":
            state.model = chosen
            state.effort = _ensure_effort(state.writer, state.effort, chosen)
            state.message = _t(state, "msg_model", name=chosen)
            _sync_stages_from_coder_night()
        elif kind == "agent":
            state.agent = chosen
            state.message = _t(state, "msg_agent", name=chosen)
            _sync_stages_from_coder_night()
        elif kind == "fast":
            state.fast_mode = chosen == "on"
            state.message = _t(
                state,
                "msg_fast",
                value=_t(state, "on") if state.fast_mode else _t(state, "off"),
            )
        else:
            state.effort = _ensure_effort(state.writer, chosen, state.model)
            state.message = _t(state, "msg_effort", name=state.effort)
            _sync_stages_from_coder_night()

    def _cycle_coder_field(delta: int) -> None:
        fields = _coder_fields()
        kind = fields[max(0, min(state.field_i, len(fields) - 1))]
        opts = _options_for(kind)
        if not opts:
            return
        cur = _current_value(kind)
        try:
            i = opts.index(cur)
        except ValueError:
            i = 0
        _apply_coder_value(kind, opts[(i + delta) % len(opts)])

    def close_pick(confirm: bool) -> None:
        if state.view != "pick":
            return
        kind = state.pick_kind
        opts = _options_for(kind)
        fields = _coder_fields()
        if confirm and opts:
            i = max(0, min(state.pick_cursor, len(opts) - 1))
            _apply_coder_value(kind, opts[i])
            if kind == "writer":
                state.field_i = 1
            elif kind != "fast":
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

    def _kick_docs_init(repo: Path, maintain: bool) -> None:
        web = Path.home() / ".agents" / "bin" / "docs-web"
        if not web.is_file():
            web = Path(__file__).resolve().parent / "docs-web"
        try:
            subprocess.run(
                [sys.executable, str(web), "rebuild", str(repo)],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return
        if not maintain:
            return
        runner = Path.home() / ".agents" / "bin" / "docs-maintain-project"
        if not runner.is_file():
            runner = Path(__file__).resolve().parent / "docs-maintain-project"
        try:
            listed = subprocess.run(
                ["pgrep", "-f", f"docs-maintain-project {repo}"],
                check=False,
                capture_output=True,
                text=True,
            )
            if listed.returncode == 0 and listed.stdout.strip():
                return
        except OSError:
            pass
        docs_root = repo / "docs"
        has_stub = False
        if docs_root.is_dir():
            for path in docs_root.rglob("*.md"):
                try:
                    head = path.read_text(encoding="utf-8")[:400]
                except OSError:
                    continue
                if "status: stub" in head:
                    has_stub = True
                    break
        if not has_stub:
            return
        log = Path.home() / ".agents" / "logs" / "docs-init.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.pop("DOCS_IF_HOUR", None)
        with log.open("a", encoding="utf-8") as fh:
            subprocess.Popen(
                [str(runner), str(repo)],
                stdout=fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
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
                    if _supports_fast(state.writer)
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
                        writer_agent=state.agent if state.writer == "opencode" else None,
                        writer_service_tier=service_tier,
                        workspace_mode=state.workspace_mode,
                        worktree_min_score=state.worktree_min_score,
                        worktree_on_multi_write=state.worktree_on_multi_write,
                        session_max_tasks=state.session_max_tasks,
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
        docs_block = state.stages.get("docs") or {}
        if docs_block.get("enabled"):
            cron = Path.home() / ".agents" / "bin" / "docs-cron-ensure"
            if not cron.is_file():
                cron = Path(__file__).resolve().parent / "docs-cron-ensure"
            try:
                subprocess.run(
                    [sys.executable, str(cron)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError:
                pass
            _kick_docs_init(Path(state.repo), bool(docs_block.get("maintain", True)))
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
                if _supports_fast(state.writer)
                else None
            ),
            "fast_mode": bool(state.fast_mode) if _supports_fast(state.writer) else False,
            "workspace_mode": state.workspace_mode,
            "session_max_tasks": state.session_max_tasks,
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
        if state.tools.get("cursor", {}).get("present") and "cursor" not in writers:
            writers.append("cursor")
        if state.tools.get("opencode", {}).get("present") and "opencode" not in writers:
            writers.append("opencode")
        if shutil.which("opencode"):
            refresh_opencode_catalog()
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

    def _goto_tab(i: int) -> None:
        tab_i["i"] = i % len(TAB_IDS)
        if TAB_IDS[tab_i["i"]] == "coder":
            state.view = "form"
            state.field_i = 0
            state.focus = "writer"
        on_tab_enter()

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
        elif tid in MODULE_TAB_IDS:
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
        if pane["col"] == "nav":
            pane["col"] = "main"
            state.message = _t(state, "msg_main")
            return
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "form":
                _cycle_coder_field(1)
            return
        if tid in {"stages", *MODULE_TAB_IDS}:
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
            else:
                _cycle_coder_field(-1)
            return
        if tid in {"stages", *MODULE_TAB_IDS}:
            _cycle_stage_field(-1)
            return
        tab_i["i"] = (tab_i["i"] - 1) % len(TAB_IDS)
        on_tab_enter()

    def _digit_goto(n: int) -> None:
        leave_pick_if_any()
        if (
            pane["col"] == "main"
            and TAB_IDS[tab_i["i"]] == "stages"
            and 1 <= n <= len(STAGE_IDS)
        ):
            _select_stage(n - 1)
            return
        if n == 0:
            _goto_tab(len(TAB_IDS) - 1)
            return
        _goto_tab(n - 1)

    for n in range(1, 10):

        @kb.add(str(n))
        def _(event, n=n) -> None:
            _digit_goto(n)

    @kb.add("0")
    def _(event) -> None:
        _digit_goto(0)

    @kb.add("c-left")
    def _(event) -> None:
        pane["col"] = "nav"
        state.message = _t(state, "msg_nav")

    @kb.add("c-right")
    def _(event) -> None:
        pane["col"] = "main"
        state.message = _t(state, "msg_main")

    @kb.add("up")
    @kb.add("k")
    def _(event) -> None:
        if pane["col"] == "nav":
            leave_pick_if_any()
            _goto_tab(tab_i["i"] - 1)
            return
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                move_pick(-1)
            else:
                move_form_field(-1)
        elif tid in {"stages", *MODULE_TAB_IDS}:
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
        if pane["col"] == "nav":
            leave_pick_if_any()
            _goto_tab(tab_i["i"] + 1)
            return
        tid = TAB_IDS[tab_i["i"]]
        if tid == "coder":
            if state.view == "pick":
                move_pick(1)
            else:
                move_form_field(1)
        elif tid in {"stages", *MODULE_TAB_IDS}:
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

    def _nudge_session(delta: int) -> None:
        if TAB_IDS[tab_i["i"]] != "work":
            return
        state.session_max_tasks = max(1, min(10, state.session_max_tasks + delta))
        state.message = _t(state, "msg_session_max", n=state.session_max_tasks)

    @kb.add("[")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "stages":
            _move_stage(-1)
        else:
            _nudge_session(-1)

    @kb.add("]")
    def _(event) -> None:
        if TAB_IDS[tab_i["i"]] == "stages":
            _move_stage(1)
        else:
            _nudge_session(1)

    @kb.add(",")
    def _(event) -> None:
        _nudge_session(-1)

    @kb.add(".")
    def _(event) -> None:
        _nudge_session(1)

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
        elif tid in {"stages", *MODULE_TAB_IDS}:
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
        if pane["col"] == "nav":
            pane["col"] = "main"
            state.message = _t(state, "msg_main")
            return
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
        elif tid in {"stages", *MODULE_TAB_IDS}:
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
        elif tid == "info":
            return
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
        leave_pick_if_any()
        _goto_tab(TAB_IDS.index("info"))

    def _sidebar_mouse(mouse_event) -> None:
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return
        hit = sidebar_hit(mouse_event.position.y)
        if hit is None:
            pane["col"] = "nav"
            return
        leave_pick_if_any()
        pane["col"] = "nav"
        _goto_tab(hit)

    def _main_mouse(mouse_event) -> None:
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return
        pane["col"] = "main"
        y = mouse_event.position.y
        tid = TAB_IDS[tab_i["i"]]
        if tid == "apply" and y >= 3:
            do_apply()
            return
        if tid == "coder" and state.view == "form" and y >= 3:
            fields = _coder_fields()
            i = y - 3
            if 0 <= i < len(fields):
                state.field_i = i
                state.focus = fields[i]
                open_pick(fields[i])
            return
        if tid == "coder" and state.view == "pick" and y >= pick_view["header"]:
            opts = _options_for(state.pick_kind)
            i = pick_view["start"] + (y - pick_view["header"])
            if 0 <= i < len(opts):
                state.pick_cursor = i
                close_pick(confirm=True)

    root = HSplit(
        [
            Window(content=FormattedTextControl(header), height=2, style="class:hdr"),
            VSplit(
                [
                    Window(
                        content=ClickControl(sidebar, on_mouse=_sidebar_mouse),
                        width=22,
                        style="class:side",
                    ),
                    Window(width=1, char="│", style="class:rule"),
                    HSplit(
                        [
                            Window(
                                content=FormattedTextControl(main_chrome),
                                height=2,
                                style="class:tabbar",
                            ),
                            Window(
                                content=ClickControl(main_view, on_mouse=_main_mouse),
                                style="class:main",
                            ),
                        ]
                    ),
                ]
            ),
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
            "side": "bg:#12131a #565f89",
            "side-title": "bg:#12131a #7aa2f7 bold",
            "side-on": "bg:#7aa2f7 #0b0e14 bold",
            "side-on-focus": "bg:#73daca #0b0e14 bold",
            "side-off": "bg:#12131a #a9b1d6",
            "side-hint": "bg:#12131a #565f89",
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
        mouse_support=True,
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
    """Pretty post-Apply summary: includes Fast mode for Codex/Cursor."""
    agents = Path(result["repo"]) / ".agents"
    lang = normalize_lang(result.get("lang") or "en")
    writer = str(result.get("writer") or "—")
    tier = str(result.get("service_tier") or "").strip().lower()
    show_fast = writer in {"codex", "cursor"}

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
    if show_fast:
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
            (
                tr(lang, "done_lbl_session"),
                str(result.get("session_max_tasks") or "10"),
            ),
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

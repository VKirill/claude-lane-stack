#!/usr/bin/env python3
"""PM bulk-read: cheap model maps a fat file; Fable never ingests the source.

Hook (PreToolUse Read|Bash) blocks full-file dumps over pm_read.min_lines.
Run:  pm_read --path FILE [--question '...']
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

_BIN = Path(__file__).resolve().parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))

from routing_profile import load_routing_profile  # noqa: E402

PM_READ_PROVIDERS = ("agy", "qwen", "kimi", "grok", "codex", "claude")
PICK_ORDER = ("agy", "qwen", "kimi", "grok", "codex", "claude")
HOST_BIN = {
    "agy": "agy",
    "qwen": "qwen",
    "kimi": "kimi",
    "grok": "grok",
    "codex": "codex",
    "claude": "claude",
}
DEFAULT_MIN_LINES = 350
DEFAULT_PROVIDER = "agy"
DEFAULT_MODEL = "gemini-3.8-flash-low"
DEFAULT_EFFORT = "low"
DEFAULT_MODELS = {
    "agy": "gemini-3.8-flash-low",
    "qwen": "qwen3.6-flash",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "codex": "gpt-5.6-terra",
    "claude": "sonnet",
}
DEFAULT_EFFORTS = {
    "agy": "low",
    "qwen": "low",
    "kimi": "low",
    "grok": "low",
    "codex": "low",
    "claude": "low",
}
DEFAULT_TIERS = {
    "agy": "standard",
    "qwen": "standard",
    "kimi": "standard",
    "grok": "standard",
    "codex": "fast",
    "claude": "standard",
}
PM_READ_EFFORTS = {
    "agy": ("low", "medium", "high"),
    "qwen": ("low", "medium", "high"),
    "kimi": ("low", "medium", "high"),
    "grok": ("low", "medium", "high"),
    "codex": ("low", "medium", "high", "xhigh", "max"),
    "claude": ("low", "medium", "high"),
}
MIN_LINE_CHOICES = (100, 200, 350, 500, 800, 1000, 2000)
MIN_LINES_LO = 50
MIN_LINES_HI = 5000
MAX_FILE_BYTES = 400_000
INVOKE_TIMEOUT = 180
HOOK_TIMEOUT = 200
BRIEF_MARK = "PM_READ_BRIEF v1"

BRIEF_RULES = """You map one source file for a senior planner who will NEVER see the file body.
Return ONLY this exact shape (no fences, no greeting, no source dumps):

PM_READ_BRIEF v1
path: <path>
lines: <n>

answer:
- (L<line>) <only if QUESTION is non-empty; else omit this section>

purpose: <one sentence>
exports:
- <Name> (L<line>): <role>
imports:
- <name> (L<line>): <used for>
flow:
- (L<start>-<end>) <what happens>
hotspots:
- L<start>-<end>: <where the planner would Read with offset if editing>
unknown:
- <fact you could not confirm>

Rules:
- Every bullet has a line number.
- Max 60 lines total.
- No code, no markdown fences, no preamble.
- If unsure, put it under unknown — do not invent.
"""


def pm_read_cli() -> str:
    home = Path.home() / ".agents" / "bin" / "pm_read"
    if home.is_file() and os.access(home, os.X_OK):
        return str(home)
    here = Path(__file__).resolve().parent / "pm_read.py"
    if here.is_file():
        return f"python3 {here}"
    return "pm_read"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_pm_read(raw: Any) -> dict[str, Any]:
    block = raw if isinstance(raw, dict) else {}
    provider = str(block.get("provider") or DEFAULT_PROVIDER).strip().lower()
    if provider not in PM_READ_PROVIDERS:
        provider = DEFAULT_PROVIDER
    try:
        min_lines = int(block.get("min_lines") or DEFAULT_MIN_LINES)
    except (TypeError, ValueError):
        min_lines = DEFAULT_MIN_LINES
    min_lines = max(MIN_LINES_LO, min(MIN_LINES_HI, min_lines))
    model = str(block.get("model") or DEFAULT_MODELS.get(provider) or DEFAULT_MODEL).strip()
    allowed = PM_READ_EFFORTS.get(provider, ("low", "medium", "high"))
    effort = str(
        block.get("reasoning_effort") or block.get("effort") or DEFAULT_EFFORTS.get(provider) or DEFAULT_EFFORT
    ).strip().lower()
    if effort not in allowed:
        effort = DEFAULT_EFFORTS.get(provider, DEFAULT_EFFORT)
    tier = str(block.get("service_tier") or DEFAULT_TIERS.get(provider) or "standard").strip().lower()
    if tier not in {"fast", "standard"}:
        tier = DEFAULT_TIERS.get(provider, "standard")
    return {
        "enabled": _truthy(block.get("enabled", False)),
        "min_lines": min_lines,
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
        "service_tier": tier,
    }


def host_has(provider: str, tools: dict[str, Any] | None = None) -> bool:
    if tools is not None:
        block = tools.get(provider)
        if isinstance(block, dict) and "present" in block:
            return bool(block.get("present"))
        return False
    import shutil

    return bool(shutil.which(HOST_BIN.get(provider, provider)))


def defaults_for(provider: str) -> dict[str, str]:
    return {
        "provider": provider,
        "model": DEFAULT_MODELS.get(provider, DEFAULT_MODEL),
        "reasoning_effort": DEFAULT_EFFORTS.get(provider, DEFAULT_EFFORT),
        "service_tier": DEFAULT_TIERS.get(provider, "standard"),
    }


def pick_pm_read(tools: dict[str, Any] | None = None) -> dict[str, str]:
    """Cheap mapper: AGY flash → other CLIs → Codex terra fast → Claude sonnet."""
    for provider in PICK_ORDER:
        if host_has(provider, tools):
            return defaults_for(provider)
    return defaults_for("claude")


def resolve_pm_read(
    raw: Any, tools: dict[str, Any] | None = None
) -> dict[str, Any]:
    cfg = normalize_pm_read(raw)
    if host_has(str(cfg["provider"]), tools):
        return cfg
    picked = pick_pm_read(tools)
    cfg.update(picked)
    return cfg


def load_pm_read(start: Path | None = None) -> dict[str, Any]:
    profile = load_routing_profile(start or Path.cwd())
    return resolve_pm_read(profile.get("pm_read"))


IMAGE_SUFFIXES = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".avif",
        ".heic",
        ".heif",
        ".bmp",
        ".ico",
        ".tif",
        ".tiff",
        ".svg",
    }
)


def looks_like_text(path: Path) -> bool:
    """Fable reads images himself. Only text sources go to the worker."""
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return False
    try:
        with path.open("rb") as fh:
            chunk = fh.read(4096)
    except OSError:
        return False
    return bool(chunk) and b"\x00" not in chunk


def count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as fh:
        for n, _ in enumerate(fh, 1):
            if n > MIN_LINES_HI + 1:
                return n
    return n


def should_block_read(
    path: Path,
    *,
    offset: Any = None,
    limit: Any = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[bool, int, str]:
    """Return (block, line_count, reason). reason empty when allow."""
    settings = cfg or load_pm_read(Path.cwd())
    if not settings.get("enabled"):
        return False, 0, ""
    if offset not in (None, "", 0, "0") or limit not in (None, "", 0, "0"):
        return False, 0, ""
    if not path.is_file():
        return False, 0, ""
    if not looks_like_text(path):
        return False, 0, ""
    lines = count_lines(path)
    min_lines = int(settings["min_lines"])
    if lines <= min_lines:
        return False, lines, ""
    reader = (
        f"{settings['provider']} {settings['model']} "
        f"effort={settings.get('reasoning_effort') or DEFAULT_EFFORT}"
    )
    cmd = (
        f"{pm_read_cli()} --path {path} --question "
        f"\"<what the planner needs from this file>\""
    )
    reason = (
        f"File is {lines} lines (pm_read.min_lines={min_lines}). "
        f"Use the /bulk-reader skill: {cmd}  "
        f"(worker: {reader}; stdout is {BRIEF_MARK}). "
        "Do not cat/head/tail/sed/Read the whole file. "
        "For an edit, Read with offset+limit on a hotspot."
    )
    return True, lines, reason


_DUMP_BIN = frozenset({
    "cat", "nl", "tac", "bat", "batcat", "less", "more", "pr", "head", "tail",
})
_ASSIGN_RE = re.compile(
    r"(?:^|[\n;&])\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=([^\n;&]+)"
)
_SED_SPAN = re.compile(r"(\d+)\s*,\s*(\d+)\s*p")
_PATHISH = re.compile(
    r"""['\"]([^'\"]+\.[A-Za-z0-9]{1,8})['\"]|((?:[\w./~-])+\.[A-Za-z0-9]{1,8})"""
)


def _assignment_map(cmd: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in _ASSIGN_RE.finditer(cmd)}


def _tokens_from_rhs(rhs: str) -> list[str]:
    return [m.group(1) or m.group(2) for m in _PATHISH.finditer(rhs)]


def _expand_operand(token: str, assigns: dict[str, str]) -> list[str]:
    raw = token
    if raw.startswith("${") and raw.endswith("}"):
        raw = "$" + raw[2:-1]
    if raw.startswith("$"):
        rhs = assigns.get(raw[1:], "")
        found = _tokens_from_rhs(rhs)
        if found:
            return found
        if rhs and not rhs.startswith("$("):
            return [rhs]
        return []
    return [token]


def dump_paths_from_bash(cmd: str, cwd: Path, min_lines: int) -> list[Path]:
    # ponytail: Spotify shunt — dump bins + sed print. python -c open() still dumps.
    del min_lines
    assigns = _assignment_map(cmd)
    out: list[Path] = []
    seen: set[str] = set()
    for part in re.split(r"(?:&&|\|\||\n|;)", cmd):
        part = part.strip()
        if not part:
            continue
        if re.search(r"\bcat\s*(>>?|<<)", part):
            continue
        if "|" in part:
            continue
        try:
            argv = shlex.split(part, posix=True)
        except ValueError:
            continue
        i = 0
        while i < len(argv) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i]):
            i += 1
        if i >= len(argv):
            continue
        bin_ = Path(argv[i]).name
        rest = argv[i + 1 :]
        if bin_ == "sed":
            if any(a == "-i" or a.startswith("-i") for a in rest):
                continue
            operands = [
                a for a in rest if not a.startswith("-") and not _SED_SPAN.fullmatch(a)
            ]
        elif bin_ in _DUMP_BIN:
            operands = [a for a in rest if not a.startswith("-")]
        else:
            continue
        for op in operands:
            for tok in _expand_operand(op, assigns):
                path = Path(tok).expanduser()
                if not path.is_absolute():
                    path = cwd / path
                try:
                    path = path.resolve()
                except OSError:
                    continue
                key = str(path)
                if key in seen or not path.is_file():
                    continue
                seen.add(key)
                out.append(path)
    return out


def should_block_bash(
    cmd: str,
    cwd: Path,
    cfg: dict[str, Any] | None = None,
) -> tuple[Path | None, int, str]:
    settings = cfg or load_pm_read(cwd)
    if not settings.get("enabled") or not (cmd or "").strip():
        return None, 0, ""
    min_lines = int(settings["min_lines"])
    for path in dump_paths_from_bash(cmd, cwd, min_lines):
        block, lines, reason = should_block_read(path, cfg=settings)
        if block:
            return path, lines, reason
    return None, 0, ""


def build_prompt(path: Path, question: str, body: str, lines: int) -> str:
    q = (question or "").strip()
    q_block = q if q else "(none — emit the map only, omit answer:)"
    return (
        f"{BRIEF_RULES}\n"
        f"QUESTION: {q_block}\n"
        f"FILE: {path}  LINES: {lines}\n"
        f"<file path=\"{path}\">\n{body}\n</file>\n"
    )


def _read_body(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    truncated = len(data) > MAX_FILE_BYTES
    if truncated:
        data = data[:MAX_FILE_BYTES]
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n…[truncated for worker payload]…\n"
    return text, truncated


def invoke_claude(prompt: str, *, model: str, timeout: int) -> str:
    import shutil
    import subprocess

    bin_path = shutil.which("claude")
    if not bin_path:
        raise SystemExit("pm_read: claude not on PATH")
    completed = subprocess.run(
        [
            bin_path,
            "-p",
            prompt,
            "--model",
            model or "sonnet",
            "--output-format",
            "text",
            "--dangerously-skip-permissions",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-800:]
        raise SystemExit(f"pm_read: claude exited {completed.returncode}: {tail}")
    return (completed.stdout or "").strip()


def invoke_brief(
    prompt: str,
    *,
    provider: str,
    model: str,
    effort: str = DEFAULT_EFFORT,
    service_tier: str = "standard",
) -> str:
    from plan_critique_llm import (  # noqa: WPS433
        LlmCritiqueError,
        invoke_agy,
        invoke_codex,
        invoke_grok,
        invoke_kimi,
        invoke_qwen,
    )

    try:
        if provider == "agy":
            return invoke_agy(
                prompt, model=model, effort=effort or "low", timeout=INVOKE_TIMEOUT
            )
        if provider == "codex":
            return invoke_codex(
                prompt,
                model=model,
                effort=effort or "low",
                timeout=INVOKE_TIMEOUT,
                service_tier=service_tier or "fast",
            )
        if provider == "claude":
            return invoke_claude(prompt, model=model, timeout=INVOKE_TIMEOUT)
        if provider == "qwen":
            return invoke_qwen(prompt, model=model, timeout=INVOKE_TIMEOUT)
        if provider == "kimi":
            return invoke_kimi(prompt, model=model, timeout=INVOKE_TIMEOUT)
        if provider == "grok":
            return invoke_grok(prompt, model=model, timeout=INVOKE_TIMEOUT)
    except LlmCritiqueError as exc:
        raise SystemExit(f"pm_read: worker failed: {exc}") from exc
    raise SystemExit(f"pm_read: unsupported provider {provider}")


def run_brief(path: Path, question: str, *, cfg: dict[str, Any] | None = None) -> str:
    settings = cfg or load_pm_read(Path.cwd())
    if not path.is_file():
        raise SystemExit(f"pm_read: not a file: {path}")
    if not looks_like_text(path):
        raise SystemExit(f"pm_read: not a text file: {path}")
    lines = count_lines(path)
    body, _ = _read_body(path)
    prompt = build_prompt(path, question, body, lines)
    raw = invoke_brief(
        prompt,
        provider=str(settings["provider"]),
        model=str(settings["model"]),
        effort=str(settings.get("reasoning_effort") or DEFAULT_EFFORT),
        service_tier=str(settings.get("service_tier") or "standard"),
    )
    text = (raw or "").strip()
    if BRIEF_MARK not in text:
        text = f"{BRIEF_MARK}\npath: {path}\nlines: {lines}\n\n{text}"
    return text.rstrip() + "\n"


def worker_brief_for_hook(path: Path, cfg: dict[str, Any]) -> str:
    """Run the adoc worker; on failure keep the deny hint so Fable still stops."""
    try:
        return run_brief(path, "", cfg=cfg)
    except (SystemExit, OSError, ValueError) as exc:
        hint = exc.args[0] if exc.args else "worker failed"
        return (
            f"{BRIEF_MARK}\npath: {path}\n"
            f"unknown:\n- worker failed: {hint}\n"
            f"Retry: pm_read --path {path}\n"
        )


def hook_main() -> int:
    try:
        return _hook_body()
    except SystemExit:
        raise
    except Exception:
        emit_allow_quiet()
        return 0


def emit_allow_quiet() -> None:
    try:
        from lib_payload import emit_allow  # noqa: WPS433

        emit_allow(os.environ.get("AGENT_HOOK_CLIENT", "") or "")
    except Exception:
        return


def _hook_body() -> int:
    hooks = Path(__file__).resolve().parent.parent / "hooks"
    if hooks.is_dir() and str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))
    from lib_payload import (  # noqa: WPS433
        detect_client,
        emit_allow,
        emit_deny,
        file_path,
        read_payload,
        shell_command,
        tool_input,
        tool_name,
    )

    payload = read_payload()
    if not isinstance(payload, dict):
        emit_allow("")
        return 0
    client = detect_client(payload)
    name = tool_name(payload).lower()
    cwd = Path(str(payload.get("cwd") or payload.get("workspaceRoot") or os.getcwd()))
    cfg = load_pm_read(cwd)
    inp = tool_input(payload)
    if name == "bash":
        path, _lines, reason = should_block_bash(
            shell_command(payload) or str(inp.get("command") or ""),
            cwd,
            cfg,
        )
        if path is not None:
            emit_deny(client, reason)
            return 2
        emit_allow(client)
        return 0
    if name != "read":
        emit_allow(client)
        return 0
    raw_path = file_path(payload)
    if not raw_path:
        emit_allow(client)
        return 0
    path = Path(raw_path)
    if not path.is_absolute():
        path = cwd / path
    block, _lines, reason = should_block_read(
        path,
        offset=inp.get("offset"),
        limit=inp.get("limit"),
        cfg=cfg,
    )
    if block:
        emit_deny(client, reason)
        return 2
    emit_allow(client)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Map a fat file via cheap model for Fable")
    ap.add_argument("--hook", action="store_true", help="PreToolUse stdin hook")
    ap.add_argument("--path", type=Path, default=None)
    ap.add_argument("--question", default="")
    args = ap.parse_args(argv)
    if args.hook:
        return hook_main()
    if args.path is None:
        ap.error("--path is required")
    sys.stdout.write(run_brief(args.path.expanduser(), args.question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

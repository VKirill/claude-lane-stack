#!/usr/bin/env python3
"""One-shot LLM plan critique invokers (read-only, structured JSON).

Used by ``plan-critique`` when stages.plan_critique.provider ≠ structural.
Providers: qwen, codex, kimi, grok, agy. No product edits — prompt embeds
PLAN/SPEC/tasks; tools are discouraged / sandboxed.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

# Soft caps so prompts stay within small-model windows.
_MAX_FILE_CHARS = 12_000
_MAX_TOTAL_CHARS = 48_000
AGY_SCHEMA_PATH = Path(__file__).with_name("plan_critique_agy.schema.json")
CRITIQUE_SCHEMA_PATH = AGY_SCHEMA_PATH


def _record_invoke_usage(cli: str, model: str, stdout: str) -> None:
    try:
        from usage_ledger import record_receipt, usage_from_stdout

        usage, cost = usage_from_stdout(stdout)
        record_receipt(
            {
                "provider": cli,
                "model": model,
                "usage": usage or {},
                "total_cost_usd": cost,
            }
        )
    except Exception:
        pass


class LlmCritiqueError(RuntimeError):
    """Provider invocation or parse failure."""


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 40] + "\n\n…[truncated]…\n"


def pack_run_corpus(run_dir: Path) -> str:
    """Embed plan artifacts into a single prompt body."""
    run_dir = run_dir.expanduser().resolve()
    chunks: list[str] = []
    total = 0
    for rel in ("PLAN.md", "SPEC.md", "run.yaml"):
        path = run_dir / rel
        if not path.is_file():
            chunks.append(f"### {rel}\n(missing)\n")
            continue
        body = _truncate(
            path.read_text(encoding="utf-8", errors="replace"), _MAX_FILE_CHARS
        )
        block = f"### {rel}\n```\n{body}\n```\n"
        if total + len(block) > _MAX_TOTAL_CHARS:
            chunks.append(f"### {rel}\n(omitted — budget)\n")
            break
        chunks.append(block)
        total += len(block)

    tasks_dir = run_dir / "tasks"
    if tasks_dir.is_dir():
        for path in sorted(tasks_dir.glob("*.yaml")):
            body = _truncate(
                path.read_text(encoding="utf-8", errors="replace"), _MAX_FILE_CHARS // 2
            )
            block = f"### tasks/{path.name}\n```yaml\n{body}\n```\n"
            if total + len(block) > _MAX_TOTAL_CHARS:
                chunks.append(f"### tasks/{path.name}\n(omitted — budget)\n")
                break
            chunks.append(block)
            total += len(block)
    else:
        chunks.append("### tasks/\n(missing)\n")
    return "\n".join(chunks)


def build_llm_prompt(
    run_dir: Path,
    structural: dict[str, Any],
    *,
    provider: str,
    model: str,
) -> str:
    """Independent plan review. AGY also gets --json-schema LanePlanCritique."""
    structural_md = json.dumps(
        {
            "status": structural.get("status"),
            "summary": structural.get("summary"),
            "findings": structural.get("findings") or [],
        },
        indent=2,
        ensure_ascii=False,
    )
    corpus = pack_run_corpus(run_dir)
    schema_hint = (
        "AGY: your output is enforced by LanePlanCritique JSON Schema. "
        "Return that object only.\n"
        if provider == "agy"
        else "Reply with a **single JSON object** and nothing else (no fences).\n"
    )
    return (
        "You are an independent plan critic. The PM wrote PLAN/SPEC/tasks. "
        "Review the plan itself, not product architecture.\n"
        "Structural findings below are hints. You MAY add new findings. "
        "Do not invent files that are not in the corpus. "
        "wiki/, TODO/, docs/** are noise unless a task must edit them.\n"
        "Max 7 findings. Prefer fewer.\n\n"
        f"Provider: {provider}"
        + (f" · model {model}" if model else "")
        + "\n\n"
        "## Structural hints\n\n"
        f"```json\n{structural_md}\n```\n\n"
        "## Run corpus\n\n"
        f"{corpus}\n\n"
        "## Output\n\n"
        f"{schema_hint}"
        "{\n"
        '  "verdict": "ship" | "revise" | "revise_required",\n'
        '  "summary": "one line the PM can act on",\n'
        '  "findings": [\n'
        "    {\n"
        '      "severity": "error" | "warn" | "info",\n'
        '      "code": "owns_gap" | "fat_task" | "verify_l2" | '
        '"missing_invariant" | "gold_plate" | "bad_dag" | "note",\n'
        '      "title": "short",\n'
        '      "detail": "what to change",\n'
        '      "path": "optional path",\n'
        '      "task_id": "optional",\n'
        '      "action": "add_owns" | "drop_scope" | "split_task" | '
        '"fix_spec" | "note"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def extract_json_payload(text: str) -> str:
    text = (text or "").strip()
    if not text:
        raise LlmCritiqueError("empty LLM response")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    raise LlmCritiqueError("no JSON object found in LLM response")


def parse_llm_payload(text: str) -> dict[str, Any]:
    raw = extract_json_payload(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LlmCritiqueError(f"invalid JSON from LLM: {exc}") from exc
    if not isinstance(data, dict):
        raise LlmCritiqueError("LLM JSON root must be an object")
    verdict = str(data.get("verdict") or "").strip().lower()
    if verdict not in {"ship", "revise", "revise_required"}:
        # Infer from findings if model skipped verdict.
        findings = data.get("findings") if isinstance(data.get("findings"), list) else []
        if any(
            isinstance(f, dict) and str(f.get("severity")) == "error" for f in findings
        ):
            verdict = "revise_required"
        elif findings:
            verdict = "revise"
        else:
            verdict = "ship"
        data["verdict"] = verdict
    if not isinstance(data.get("findings"), list):
        data["findings"] = []
    if not isinstance(data.get("summary"), str):
        data["summary"] = str(data.get("summary") or "")
    return data


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=env,
        input=stdin_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _parse_stream_or_json_array(stdout: str) -> str:
    """Extract final assistant text from qwen/kimi-style stream-json or JSON array."""
    text = (stdout or "").strip()
    if not text:
        return ""
    # Whole stdout as JSON array of events
    if text.startswith("["):
        try:
            events = json.loads(text)
        except json.JSONDecodeError:
            events = None
        if isinstance(events, list):
            for event in reversed(events):
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "result" and isinstance(event.get("result"), str):
                    return event["result"]
                if event.get("type") == "assistant":
                    message = event.get("message")
                    content = message.get("content") if isinstance(message, dict) else None
                    if isinstance(content, list):
                        parts = [
                            b.get("text", "")
                            for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        joined = "".join(parts)
                        if joined.strip():
                            return joined
    # NDJSON lines
    last_result = ""
    last_assistant = ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            last_result = event["result"]
        if event.get("type") == "assistant":
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                joined = "".join(parts)
                if joined.strip():
                    last_assistant = joined
    return last_result or last_assistant or text


def _agy_structured_blob(payload: object) -> str | None:
    if isinstance(payload, dict) and "verdict" in payload:
        return json.dumps(payload, ensure_ascii=False)
    if not isinstance(payload, dict):
        return None
    for key in ("result", "response", "data"):
        value = payload.get(key)
        if isinstance(value, dict):
            got = _agy_structured_blob(value)
            if got:
                return got
        if isinstance(value, str) and value.strip():
            try:
                inner = json.loads(value)
            except json.JSONDecodeError:
                if "verdict" in value:
                    return value
                continue
            got = _agy_structured_blob(inner)
            if got:
                return got
    return None


def parse_agy_stdout(stdout: str) -> str:
    """AGY --output-format json + --json-schema → LanePlanCritique object."""
    text = (stdout or "").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _parse_stream_or_json_array(text)
    extracted = _agy_structured_blob(payload)
    if extracted is not None:
        return extracted
    return _parse_stream_or_json_array(text)


def invoke_qwen(
    prompt: str, *, model: str, timeout: int, binary: str | None = None
) -> str:
    bin_path = binary or _which("qwen")
    if not bin_path:
        raise LlmCritiqueError("qwen binary not found on PATH")
    env = os.environ.copy()
    env["QWEN_CODE_SUPPRESS_YOLO_WARNING"] = "1"
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    with tempfile.TemporaryDirectory(prefix="plan-critique-qwen-") as raw:
        cwd = Path(raw)
        argv = [
            bin_path,
            "--safe-mode",
            "--yolo",
            "--model",
            model or "qwen3.8-max-preview",
            "-p",
            prompt,
            "-o",
            "json",
        ]
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-1500:]
        raise LlmCritiqueError(f"qwen exited {completed.returncode}: {tail}")
    _record_invoke_usage("qwen", model or "qwen3.8-max-preview", completed.stdout or "")
    return _parse_stream_or_json_array(completed.stdout)


def invoke_kimi(
    prompt: str, *, model: str, timeout: int, binary: str | None = None
) -> str:
    bin_path = binary or _which("kimi") or _which("kimi-code")
    if not bin_path:
        raise LlmCritiqueError("kimi binary not found on PATH")
    env = os.environ.copy()
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    with tempfile.TemporaryDirectory(prefix="plan-critique-kimi-") as raw:
        cwd = Path(raw)
        argv = [
            bin_path,
            "-p",
            prompt,
            "--model",
            model or "kimi-code/k3-256k",
            "--output-format",
            "json",
        ]
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
    if completed.returncode != 0:
        # fallback stream-json
        if "output-format" in (completed.stderr or ""):
            argv = [
                bin_path,
                "-p",
                prompt,
                "--model",
                model or "kimi-code/k3-256k",
                "--output-format",
                "stream-json",
            ]
            completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "")[-1500:]
            raise LlmCritiqueError(f"kimi exited {completed.returncode}: {tail}")
    _record_invoke_usage("kimi", model or "kimi-code/k3-256k", completed.stdout or "")
    return _parse_stream_or_json_array(completed.stdout)


def invoke_grok(
    prompt: str, *, model: str, timeout: int, binary: str | None = None
) -> str:
    bin_path = binary or _which("grok")
    if not bin_path:
        raise LlmCritiqueError("grok binary not found on PATH")
    env = os.environ.copy()
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    with tempfile.TemporaryDirectory(prefix="plan-critique-grok-") as raw:
        cwd = Path(raw)
        # Grok Build / CLI variants differ; try -p text first.
        argv = [bin_path, "--no-subagents", "-p", prompt]
        if model:
            argv.extend(["--model", model])
        if CRITIQUE_SCHEMA_PATH.is_file():
            argv.extend(
                [
                    "--json-schema",
                    CRITIQUE_SCHEMA_PATH.read_text(encoding="utf-8"),
                ]
            )
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-1500:]
        raise LlmCritiqueError(f"grok exited {completed.returncode}: {tail}")
    _record_invoke_usage("grok", model or "", completed.stdout or "")
    return completed.stdout or completed.stderr or ""


def invoke_agy(
    prompt: str, *, model: str, effort: str, timeout: int, binary: str | None = None
) -> str:
    bin_path = binary or _which("agy")
    if not bin_path:
        raise LlmCritiqueError("agy binary not found on PATH")
    env = os.environ.copy()
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    from routing_profile import resolve_agy_effort

    model_id = model or "gemini-3.7-flash-high"
    effort_id = resolve_agy_effort(model_id, effort)
    with tempfile.TemporaryDirectory(prefix="plan-critique-agy-") as raw:
        cwd = Path(raw)
        argv = [
            bin_path,
            "--print",
            prompt,
            "--model",
            model_id,
            "--effort",
            effort_id,
            "--dangerously-skip-permissions",
            "--sandbox=false",
            "--output-format",
            "json",
        ]
        if CRITIQUE_SCHEMA_PATH.is_file():
            argv.extend(["--json-schema", str(CRITIQUE_SCHEMA_PATH)])
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-1500:]
        raise LlmCritiqueError(f"agy exited {completed.returncode}: {tail}")
    _record_invoke_usage("agy", model_id, completed.stdout or "")
    return parse_agy_stdout(completed.stdout)


def invoke_codex(
    prompt: str,
    *,
    model: str,
    effort: str,
    timeout: int,
    binary: str | None = None,
    service_tier: str = "standard",
) -> str:
    bin_path = binary or _which("codex")
    if not bin_path:
        raise LlmCritiqueError("codex binary not found on PATH")
    env = os.environ.copy()
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    with tempfile.TemporaryDirectory(prefix="plan-critique-codex-") as raw:
        cwd = Path(raw)
        last_message = cwd / "last-message.txt"
        argv = [
            bin_path,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--model",
            model or "gpt-5.6-luna",
            "-c",
            f'model_reasoning_effort="{effort or "high"}"',
            "-c",
            'approval_policy="never"',
            "--sandbox",
            "read-only",
            "--cd",
            str(cwd),
            "--skip-git-repo-check",
            "--output-last-message",
            str(last_message),
            "-",
        ]
        extra: list[str] = []
        if CRITIQUE_SCHEMA_PATH.is_file():
            extra.extend(["--output-schema", str(CRITIQUE_SCHEMA_PATH), "--json"])
        if str(service_tier or "").strip().lower() == "fast":
            extra.extend(["-c", 'service_tier="fast"', "--enable", "fast_mode"])
        else:
            extra.extend(["--disable", "fast_mode"])
        argv[-1:-1] = extra
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout, stdin_text=prompt)
        result_text = (
            last_message.read_text(encoding="utf-8", errors="replace")
            if last_message.is_file()
            else ""
        )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-1500:]
        raise LlmCritiqueError(f"codex exited {completed.returncode}: {tail}")
    if not result_text.strip():
        result_text = completed.stdout or ""
    if not result_text.strip():
        raise LlmCritiqueError("codex produced no final message")
    _record_invoke_usage("codex", model or "gpt-5.6-luna", completed.stdout or "")
    return result_text


def _opencode_text_from_jsonl(stdout: str) -> str:
    parts: list[str] = []
    for line in (stdout or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        text = part.get("text") if isinstance(part, dict) else None
        if not isinstance(text, str):
            text = event.get("text")
        if isinstance(text, str) and text:
            parts.append(text)
    return "".join(parts)


def invoke_opencode(
    prompt: str,
    *,
    model: str,
    effort: str,
    timeout: int,
    binary: str | None = None,
    agent: str = "lane-critic",
) -> str:
    bin_path = binary or _which("opencode")
    if not bin_path:
        raise LlmCritiqueError("opencode binary not found on PATH")
    env = os.environ.copy()
    env["CLAUDE_LANE_AUTOMATION"] = "1"
    env["OPENCODE_DISABLE_CLAUDE_CODE"] = "1"
    env["OPENCODE_DISABLE_DEFAULT_PLUGINS"] = "1"
    env["OPENCODE_PERMISSION"] = '{"task":"deny"}'
    variant = (effort or "").strip().lower()
    with tempfile.TemporaryDirectory(prefix="plan-critique-opencode-") as raw:
        cwd = Path(raw)
        argv = [
            bin_path,
            "run",
            "--pure",
            "--format",
            "json",
            "--dir",
            str(cwd),
            "--agent",
            (agent or "lane-critic").strip() or "lane-critic",
            "--model",
            model or "alibaba-token-plan/qwen3.8-max-preview",
        ]
        if variant:
            argv.extend(["--variant", variant])
        argv.extend(
            [
                "--dangerously-skip-permissions",
                prompt,
            ]
        )
        completed = _run(argv, cwd=cwd, env=env, timeout=timeout)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-1500:]
        raise LlmCritiqueError(f"opencode exited {completed.returncode}: {tail}")
    _record_invoke_usage(
        "opencode",
        model or "alibaba-token-plan/qwen3.8-max-preview",
        completed.stdout or "",
    )
    result_text = _opencode_text_from_jsonl(completed.stdout or "")
    if not result_text.strip():
        result_text = completed.stdout or ""
    if not result_text.strip():
        raise LlmCritiqueError("opencode produced no final message")
    return result_text


_INVOKERS: dict[str, Callable[..., str]] = {
    "qwen": lambda prompt, model, effort, timeout: invoke_qwen(
        prompt, model=model, timeout=timeout
    ),
    "codex": lambda prompt, model, effort, timeout: invoke_codex(
        prompt, model=model, effort=effort, timeout=timeout
    ),
    "kimi": lambda prompt, model, effort, timeout: invoke_kimi(
        prompt, model=model, timeout=timeout
    ),
    "grok": lambda prompt, model, effort, timeout: invoke_grok(
        prompt, model=model, timeout=timeout
    ),
    "agy": lambda prompt, model, effort, timeout: invoke_agy(
        prompt, model=model, effort=effort, timeout=timeout
    ),
    "opencode": lambda prompt, model, effort, timeout: invoke_opencode(
        prompt, model=model, effort=effort, timeout=timeout
    ),
}


def invoke_llm_critique(
    run_dir: Path,
    structural: dict[str, Any],
    *,
    provider: str,
    model: str = "",
    effort: str = "",
    timeout: int = 180,
    service_tier: str = "standard",
    agent: str = "",
) -> dict[str, Any]:
    """Run one provider; return {verdict, summary, findings, raw_excerpt}."""
    provider = (provider or "").strip().lower()
    if provider not in _INVOKERS:
        raise LlmCritiqueError(f"unsupported critique provider: {provider!r}")
    prompt = build_llm_prompt(
        run_dir, structural, provider=provider, model=model or ""
    )
    invoker = _INVOKERS[provider]
    try:
        if provider == "codex":
            raw = invoke_codex(
                prompt,
                model=model or "",
                effort=effort or "low",
                timeout=timeout,
                service_tier=service_tier,
            )
        elif provider == "opencode":
            raw = invoke_opencode(
                prompt,
                model=model or "",
                effort=effort or "low",
                timeout=timeout,
                agent=agent or "lane-critic",
            )
        else:
            raw = invoker(prompt, model or "", effort or "low", timeout)
    except subprocess.TimeoutExpired as exc:
        raise LlmCritiqueError(f"{provider} timed out after {timeout}s") from exc
    payload = parse_llm_payload(raw)
    payload["raw_excerpt"] = (raw or "")[:2000]
    payload["provider"] = provider
    payload["model"] = model
    return payload

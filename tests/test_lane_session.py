from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE_SESSION = ROOT / "bin" / "lane-session"
LANE_EXEC = ROOT / "bin" / "lane-exec"

class LaneSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_dir = self.root / ".agents" / "runs" / "warm-run"
        self.run_dir.mkdir(parents=True)
        self.cwd = self.root / "worktree"
        self.cwd.mkdir()
        self.fake_home = self.root / "home"
        self.grok_home = self.fake_home / ".grok"
        self.grok_home.mkdir(parents=True)
        (self.grok_home / "provider-secret.txt").write_text(
            "grok-secret-file\n", encoding="utf-8"
        )
        (self.fake_home / ".codex").mkdir()
        (self.fake_home / ".gemini" / "antigravity-cli").mkdir(parents=True)
        agy_agent = self.fake_home / ".gemini" / "config" / "agents" / "agy-writer"
        agy_agent.mkdir(parents=True)
        shutil.copyfile(ROOT / "agents" / "agy" / "agent.md", agy_agent / "agent.md")
        (self.fake_home / ".codex" / "auth.json").write_text(
            "{}\n", encoding="utf-8"
        )
        self.args_log = self.cwd / "provider-args.jsonl"
        self.conversations = self.grok_home / "conversations"
        self.conversations.mkdir()
        self.fake_provider = self.cwd / "fake-provider"
        self.fake_provider.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import hashlib
                import os
                import subprocess
                import sys
                import time
                import uuid
                import re
                import socket
                from pathlib import Path

                args = sys.argv[1:]

                def credential_probe():
                    home = Path(os.environ["HOME"])
                    codex_home = os.environ.get("CODEX_HOME")
                    return {
                        "openai": os.environ.get("OPENAI_API_KEY"),
                        "grok": os.environ.get("GROK_API_KEY"),
                        "xai": os.environ.get("XAI_API_KEY"),
                        "codex_home": codex_home,
                        "host_codex_auth_readable": (home / ".codex" / "auth.json").is_file(),
                        "host_grok_auth_readable": (home / ".grok" / "provider-secret.txt").is_file(),
                        "active_codex_auth_readable": bool(
                            codex_home and (Path(codex_home) / "auth.json").is_file()
                        ),
                    }

                if "--version" in args:
                    if os.environ.get("FAKE_VERSION_PROBE_LOG"):
                        Path(os.environ["FAKE_VERSION_PROBE_LOG"]).write_text(
                            json.dumps(credential_probe()), encoding="utf-8"
                        )
                    if os.environ.get("FAKE_VERSION_WARNING"):
                        print(os.environ["FAKE_VERSION_WARNING"])
                    print(os.environ.get("FAKE_VERSION_TEXT", "grok 0.2.103-test (fake)"))
                    raise SystemExit(0)
                streaming = "--output-format" in args and args[
                    args.index("--output-format") + 1
                ] == "streaming-json"
                agy_streaming = "--output-format" in args and args[
                    args.index("--output-format") + 1
                ] == "stream-json"

                def emit(payload):
                    print(json.dumps(payload), flush=True)

                if os.environ.get("FAKE_PID_FILE"):
                    Path(os.environ["FAKE_PID_FILE"]).write_text(str(os.getpid()), encoding="utf-8")
                if os.environ.get("FAKE_ENV_LOG"):
                    Path(os.environ["FAKE_ENV_LOG"]).write_text(
                        ",".join(
                            (
                                os.environ.get("GROK_CLAUDE_HOOKS_ENABLED", "<unset>"),
                                os.environ.get("CLAUDE_LANE_AUTOMATION", "<unset>"),
                            )
                        ),
                        encoding="utf-8",
                    )
                if os.environ.get("FAKE_PROVIDER_SECRET_LOG"):
                    Path(os.environ["FAKE_PROVIDER_SECRET_LOG"]).write_text(
                        json.dumps(credential_probe()),
                        encoding="utf-8",
                    )
                if os.environ.get("FAKE_SOCKET_PROBE"):
                    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    try:
                        probe.connect(os.environ["FAKE_SOCKET_PROBE"])
                        socket_connect = "allowed"
                    except OSError:
                        socket_connect = "denied"
                    finally:
                        probe.close()
                    Path(os.environ["FAKE_ENV_SCRUB_LOG"]).write_text(
                        json.dumps(
                            {
                                "socket_connect": socket_connect,
                                "host_tmp_visible": Path(
                                    os.environ["FAKE_HOST_TMP_PROBE"]
                                ).exists(),
                                "docker_host": os.environ.get("DOCKER_HOST"),
                                "ssh_auth_sock": os.environ.get("SSH_AUTH_SOCK"),
                                "dbus": os.environ.get("DBUS_SESSION_BUS_ADDRESS"),
                            }
                        ),
                        encoding="utf-8",
                    )
                if os.environ.get("FAKE_CHILD_PID_FILE"):
                    child = subprocess.Popen(
                        [sys.executable, "-c", "import time; time.sleep(30)"]
                    )
                    Path(os.environ["FAKE_CHILD_PID_FILE"]).write_text(
                        str(child.pid), encoding="utf-8"
                    )
                log = Path(os.environ["FAKE_ARGS_LOG"])
                with log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(args) + "\\n")

                if args and args[0] == "exec":
                    if os.environ.get("FAKE_CODEX_HOME_LOG"):
                        codex_home = Path(os.environ["CODEX_HOME"])
                        # Record bare-home shape for assertions (auth + config, no mcp).
                        Path(os.environ["FAKE_CODEX_HOME_LOG"]).write_text(
                            json.dumps(
                                {
                                    "path": str(codex_home),
                                    "auth_exists": (codex_home / "auth.json").is_file(),
                                    "config_exists": (
                                        codex_home / "config.toml"
                                    ).is_file(),
                                    "skills_empty": not any(
                                        (codex_home / "skills").glob("*")
                                    )
                                    if (codex_home / "skills").is_dir()
                                    else False,
                                    "has_mcp_servers_block": "[mcp_servers"
                                    in (
                                        (codex_home / "config.toml").read_text(
                                            encoding="utf-8"
                                        )
                                        if (codex_home / "config.toml").is_file()
                                        else ""
                                    ),
                                }
                            ),
                            encoding="utf-8",
                        )
                    prompt = sys.stdin.read()
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    if os.environ.get("FAKE_CODEX_SESSION"):
                        thread_id = os.environ["FAKE_CODEX_SESSION"]
                    elif "resume" in args:
                        thread_id = args[args.index("resume") + 1]
                    else:
                        thread_id = "codex-thread-test"
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake codex report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit({"type": "thread.started", "thread_id": thread_id})
                    emit({"type": "turn.started"})
                    emit(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": report},
                        }
                    )
                    emit(
                        {
                            "type": "turn.completed",
                            "usage": {
                                "input_tokens": 11,
                                "cached_input_tokens": 2,
                                "output_tokens": 7,
                                "reasoning_output_tokens": 3,
                            },
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "agy":
                    prompt = args[args.index("--print") + 1]
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    conversation_id = (
                        args[args.index("--conversation") + 1]
                        if "--conversation" in args
                        else "agy-conversation-test"
                    )
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake AGY report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit(
                        {
                            "event": "init",
                            "conversation_id": conversation_id,
                            "init": {
                                "model": args[args.index("--model") + 1],
                                "agent": "agy-writer",
                                "tools": ["view_file", "run_command", "write_to_file"],
                                "permission_mode": "always-proceed",
                            },
                        }
                    )
                    emit(
                        {
                            "event": "step_update",
                            "step_update": {
                                "conversation_id": conversation_id,
                                "step_type": "agent_response",
                                "text_delta": report,
                            },
                        }
                    )
                    emit(
                        {
                            "event": "result",
                            "result": {
                                "conversation_id": conversation_id,
                                "status": "SUCCESS",
                                "response": report,
                                "num_turns": 1,
                                "usage": {
                                    "input_tokens": 10,
                                    "output_tokens": 5,
                                    "thinking_tokens": 2,
                                    "total_tokens": 17,
                                },
                            },
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "qwen":
                    prompt = args[args.index("-p") + 1]
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    session_id = (
                        args[args.index("--resume") + 1]
                        if "--resume" in args
                        else "qwen-session-test"
                    )
                    model = args[args.index("--model") + 1]
                    effective_model = os.environ.get("FAKE_EFFECTIVE_MODEL") or model
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake Qwen report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit(
                        {
                            "type": "system",
                            "subtype": "init",
                            "session_id": session_id,
                            "model": effective_model,
                            "permission_mode": "yolo",
                            "qwen_code_version": "0.20.1",
                        }
                    )
                    emit(
                        {
                            "type": "assistant",
                            "session_id": session_id,
                            "message": {
                                "role": "assistant",
                                "model": model,
                                "content": [{"type": "text", "text": report}],
                                "usage": {"input_tokens": 10, "output_tokens": 5},
                            },
                        }
                    )
                    emit(
                        {
                            "type": "result",
                            "subtype": "success",
                            "session_id": session_id,
                            "is_error": False,
                            "num_turns": 1,
                            "result": report,
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 5,
                                "total_tokens": 15,
                            },
                            "permission_denials": [],
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "cursor":
                    # Prompt is the last arg for cursor-agent -p … --model X "<prompt>"
                    prompt = args[-1]
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    session_id = (
                        args[args.index("--resume") + 1]
                        if "--resume" in args
                        else "cursor-session-test"
                    )
                    model = args[args.index("--model") + 1]
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake Cursor report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit(
                        {
                            "type": "system",
                            "subtype": "init",
                            "session_id": session_id,
                            "model": "Composer 2.5",
                            "permissionMode": "default",
                        }
                    )
                    emit(
                        {
                            "type": "assistant",
                            "session_id": session_id,
                            "message": {
                                "role": "assistant",
                                "content": [{"type": "text", "text": report}],
                            },
                        }
                    )
                    emit(
                        {
                            "type": "result",
                            "subtype": "success",
                            "session_id": session_id,
                            "is_error": False,
                            "result": report,
                            "usage": {
                                "inputTokens": 10,
                                "outputTokens": 5,
                            },
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "opencode":
                    prompt = args[-1]
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    session_id = (
                        args[args.index("--session") + 1]
                        if "--session" in args
                        else "opencode-session-test"
                    )
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake OpenCode report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit(
                        {
                            "type": "step_start",
                            "sessionID": session_id,
                        }
                    )
                    emit(
                        {
                            "type": "text",
                            "sessionID": session_id,
                            "part": {"text": report},
                        }
                    )
                    emit(
                        {
                            "type": "step_finish",
                            "sessionID": session_id,
                            "part": {"reason": "stop"},
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "kimi":
                    prompt = args[args.index("-p") + 1]
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    session_id = os.environ.get("FAKE_KIMI_SESSION") or (
                        args[args.index("-r") + 1]
                        if "-r" in args
                        else "kimi-session-test"
                    )
                    report = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake Kimi report\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    emit({"role": "assistant", "content": "planning the edit"})
                    emit(
                        {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "id": "tool_1",
                                    "function": {
                                        "name": "Write",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    )
                    emit(
                        {
                            "role": "tool",
                            "tool_call_id": "tool_1",
                            "content": "Wrote 2 bytes",
                        }
                    )
                    if os.environ.get("FAKE_REPORT_MODE", "complete") != "missing":
                        emit({"role": "assistant", "content": report})
                    emit(
                        {
                            "role": "meta",
                            "type": "session.resume_hint",
                            "session_id": session_id,
                            "command": f"kimi -r {session_id}",
                        }
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))

                if os.environ.get("FAKE_PROVIDER_KIND") == "" and "--conversation" not in args:
                    conversations = Path(os.environ["UNUSED_REMOVED"])
                    conversations.mkdir(parents=True, exist_ok=True)
                    db = conversations / f"{uuid.uuid4()}.db"
                    with db.open("a+", encoding="utf-8") as fh:
                        fh.write("open")
                        fh.flush()
                        time.sleep(float(os.environ.get("FAKE_SLEEP", "0.35")))
                else:
                    duration = float(os.environ.get("FAKE_SLEEP", "0"))
                    pulse = float(os.environ.get("FAKE_PULSE", "0"))
                    if pulse > 0:
                        deadline = time.monotonic() + duration
                        while time.monotonic() < deadline:
                            if streaming:
                                emit({"type": "thought", "data": "provider pulse"})
                            else:
                                print("provider pulse", flush=True)
                            time.sleep(min(pulse, max(0, deadline - time.monotonic())))
                    else:
                        time.sleep(duration)

                exit_code = int(os.environ.get("FAKE_EXIT", "0"))
                if os.environ.get("FAKE_STDERR"):
                    print(os.environ["FAKE_STDERR"], file=sys.stderr, flush=True)
                if streaming:
                    mode = os.environ.get("FAKE_STREAM_MODE", "valid")
                    session_flag = "--session-id" if "--session-id" in args else "--resume"
                    session_id = args[args.index(session_flag) + 1]
                    model = args[args.index("--model") + 1]
                    rules = args[args.index("--rules") + 1]
                    task_id = re.search(r"task_id=([^;]+)", rules).group(1)
                    prompt_path = Path(args[args.index("--prompt-file") + 1])
                    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
                    if mode == "malformed":
                        print("not-json", flush=True)
                    else:
                        text_size = int(os.environ.get("FAKE_TEXT_SIZE", "0"))
                        text_data = "x" * text_size if text_size else "provider complete"
                        report_mode = os.environ.get("FAKE_REPORT_MODE", "complete")
                        if os.environ.get("FAKE_CONTROL_PROBE"):
                            try:
                                Path(os.environ["FAKE_CONTROL_PROBE"]).write_text(
                                    "provider forged control state\\n", encoding="utf-8"
                                )
                                control_write = "allowed"
                            except OSError:
                                control_write = "denied"
                            Path.cwd().joinpath("provider-write-proof.txt").write_text(
                                "source write allowed\\n", encoding="utf-8"
                            )
                            proc_probe = (
                                Path("/proc")
                                / str(os.getppid())
                                / "root"
                                / str(Path(os.environ["FAKE_CONTROL_PROBE"])).lstrip("/")
                            )
                            try:
                                proc_probe.write_text(
                                    "provider forged through proc\\n", encoding="utf-8"
                                )
                                proc_write = "allowed"
                            except OSError:
                                proc_write = "denied"
                        else:
                            control_write = "not-requested"
                            proc_write = "not-requested"
                        if report_mode != "missing":
                            report_task = os.environ.get("FAKE_REPORT_TASK_ID", task_id)
                            report_prompt = os.environ.get(
                                "FAKE_REPORT_PROMPT_SHA256", prompt_sha256
                            )
                            report_block = (
                                "\\n<<<LANE_REPORT:BEGIN>>>\\n"
                                f"TASK_ID: {report_task}\\n"
                                f"PROMPT_SHA256: {report_prompt}\\n"
                                f"STATUS: {report_mode}\\n"
                                f"CONTROL_PLANE_WRITE: {control_write}\\n"
                                f"PROC_CONTROL_WRITE: {proc_write}\\n"
                                "SUMMARY: fake provider report\\n"
                                "<<<LANE_REPORT:END>>>\\n"
                            )
                            text_data += report_block
                            if os.environ.get("FAKE_DUPLICATE_REPORT"):
                                text_data += report_block
                        if os.environ.get("FAKE_SPLIT_REPORT"):
                            split_at = text_data.index("<<<LANE_REPORT:BEGIN>>>") + 8
                            emit({"type": "text", "data": text_data[:split_at]})
                            emit({"type": "text", "data": text_data[split_at:]})
                        else:
                            emit({"type": "text", "data": text_data})
                        if exit_code != 0 or mode in {"error", "error-end"}:
                            emit(
                                {
                                    "type": "error",
                                    "message": os.environ.get(
                                        "FAKE_ERROR_MESSAGE", "provider failed"
                                    ),
                                }
                            )
                        if exit_code == 0 and mode not in {"error", "missing-end"}:
                            emit(
                                {
                                    "type": "end",
                                    "stopReason": os.environ.get("FAKE_STOP_REASON", "EndTurn"),
                                    "sessionId": session_id,
                                    "requestId": "request-test",
                                    "num_turns": 2,
                                    "usage": {
                                        "input_tokens": 10,
                                        "cache_read_input_tokens": 3,
                                        "output_tokens": 4,
                                        "reasoning_tokens": 2,
                                        "total_tokens": 17,
                                    },
                                    "modelUsage": {
                                        os.environ.get("FAKE_EFFECTIVE_MODEL", model): {
                                            "inputTokens": 10,
                                            "outputTokens": 4,
                                            "modelCalls": 2,
                                            "costUSD": 0.01,
                                        }
                                    },
                                    "total_cost_usd": 0.01,
                                    "total_cost_usd_ticks": 100000000,
                                }
                            )
                else:
                    print("provider complete")
                raise SystemExit(exit_code)
                """
            ),
            encoding="utf-8",
        )
        self.fake_provider.chmod(0o755)

    def _run(
        self,
        provider: str,
        task_id: str,
        *,
        role: str | None = None,
        max_tasks: int | None = 10,
        pool_size: int | None = 2,
        sleep: float | None = None,
        exit_code: int = 0,
        run_dir: Path | None = None,
        extra_env: dict[str, str] | None = None,
        binary: Path | None = None,
        model: str = "test-model",
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        prompt = self.cwd / f"task-{task_id}.md"
        prompt.write_text(f"Implement task {task_id}\n", encoding="utf-8")
        output = self.root / f"task-{task_id}.log"
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.fake_home),
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": provider,
                "FAKE_SLEEP": str(
                    sleep if sleep is not None else (0.35 if provider == "" else 0)
                ),
                "FAKE_EXIT": str(exit_code),
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        env.update(extra_env or {})
        command = [
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            provider,
            "--run-dir",
            str(run_dir or self.run_dir),
            "--task-id",
            task_id,
            "--role",
            role or ("lane-frontend" if provider == "" else "grok"),
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(output),
            "--binary",
            str(binary or self.fake_provider),
            "--model",
            model,
        ]
        if max_tasks is not None:
            command.extend(["--max-tasks", str(max_tasks)])
        if pool_size is not None:
            command.extend(["--pool-size", str(pool_size)])
        result = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=check,
        )
        return result

    def _calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.args_log.read_text().splitlines()]

    def _state(self) -> dict:
        return json.loads((self.run_dir / "sessions.json").read_text())

    def _session_record(self, provider: str) -> dict:
        return self._state()["sessions"][f"{provider}:grok:0"]

    def test_session_max_tasks_defaults_to_ten(self) -> None:
        self._run("grok", "default-max", max_tasks=None)
        self.assertEqual(self._state()["defaults"]["max_tasks"], 10)

        rejected = self._run("grok", "too-long", max_tasks=11, check=False)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("max-tasks must be between 1 and 10", rejected.stderr)

    def test_provider_pool_defaults_to_five_and_accepts_ten(self) -> None:
        self._run("grok", "default-pool", pool_size=None)
        self.assertEqual(self._state()["defaults"]["pool_size"], 5)

        second_run = self.root / ".agents" / "runs" / "ten-pool"
        second_run.mkdir(parents=True)
        self._run("grok", "ten-pool", pool_size=10, run_dir=second_run)
        state = json.loads((second_run / "sessions.json").read_text())
        self.assertEqual(state["defaults"]["pool_size"], 10)

        rejected = self._run("grok", "too-wide", pool_size=11, check=False)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("pool-size must be between 1 and 10", rejected.stderr)

    def test_agy_36_uses_typed_stream_and_reuses_conversation(self) -> None:
        for task_id in ("agy-001", "agy-002"):
            result = self._run(
                "agy", task_id, model="gemini-3.6-flash-high", pool_size=1
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        first, second = self._calls()
        self.assertIn("--output-format", first)
        self.assertEqual(first[first.index("--output-format") + 1], "stream-json")
        self.assertIn("--dangerously-skip-permissions", first)
        self.assertEqual(first[first.index("--agent") + 1], "agy-writer")
        self.assertNotIn("--conversation", first)
        self.assertEqual(
            second[second.index("--conversation") + 1], "agy-conversation-test"
        )
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "agy")
        self.assertEqual(receipt["model"], "gemini-3.6-flash-high")
        self.assertEqual(receipt["permission_mode"], "always-proceed")
        self.assertEqual(receipt["session_id"], "agy-conversation-test")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(
            self._session_record("agy")["session_id"], "agy-conversation-test"
        )

    def test_qwen_uses_typed_stream_and_reuses_session(self) -> None:
        for task_id in ("qwen-001", "qwen-002"):
            result = self._run("qwen", task_id, model="qwen3.8-max-preview", pool_size=1)
            self.assertEqual(result.returncode, 0, result.stderr)

        first, second = self._calls()
        self.assertIn("--output-format", first)
        self.assertEqual(first[first.index("--output-format") + 1], "stream-json")
        self.assertIn("--yolo", first)
        self.assertIn("-p", first)
        self.assertNotIn("--resume", first)
        self.assertEqual(
            second[second.index("--resume") + 1], "qwen-session-test"
        )
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "qwen")
        self.assertEqual(receipt["model"], "qwen3.8-max-preview")
        self.assertEqual(receipt["permission_mode"], "yolo")
        self.assertEqual(receipt["session_id"], "qwen-session-test")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(self._session_record("qwen")["session_id"], "qwen-session-test")

    def test_qwen_effective_model_mismatch_fails_closed(self) -> None:
        result = self._run(
            "qwen",
            "qwen-mismatch",
            model="qwen3.8-max-preview",
            extra_env={"FAKE_EFFECTIVE_MODEL": "qwen3.6-flash"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def _load_lane_session(self):
        import importlib.util
        from importlib.machinery import SourceFileLoader

        name = "lane_session_under_test"
        loader = SourceFileLoader(name, str(LANE_SESSION))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        return module

    def test_qwen_environment_does_not_set_invalid_sandbox(self) -> None:
        # qwen only accepts QWEN_SANDBOX in {docker, podman, sandbox-exec};
        # "off" makes it loop on "Invalid sandbox command" before init. The
        # external bubblewrap provides the sandbox, so it must stay unset.
        env = self._load_lane_session().provider_environment("qwen")
        self.assertNotIn("QWEN_SANDBOX", env)
        self.assertEqual(env["QWEN_CODE_SUPPRESS_YOLO_WARNING"], "1")
        self.assertEqual(env["QWEN_CODE_NO_RELAUNCH"], "1")

    def test_kimi_uses_role_stream_and_reuses_session(self) -> None:
        for task_id in ("kimi-001", "kimi-002"):
            result = self._run(
                "kimi", task_id, model="kimi-code/k3-256k", pool_size=1
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        first, second = self._calls()
        self.assertEqual(first[first.index("--output-format") + 1], "stream-json")
        self.assertIn("-p", first)
        # kimi rejects --yolo/--auto together with -p
        self.assertNotIn("--yolo", first)
        self.assertNotIn("--auto", first)
        self.assertNotIn("-r", first)
        self.assertEqual(second[second.index("-r") + 1], "kimi-session-test")
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "kimi")
        self.assertEqual(receipt["model"], "kimi-code/k3-256k")
        self.assertEqual(receipt["permission_mode"], "headless-auto")
        self.assertEqual(receipt["provider_sandbox"], "off")
        self.assertEqual(receipt["stop_reason"], "TurnCompleted")
        self.assertEqual(receipt["session_id"], "kimi-session-test")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(self._session_record("kimi")["session_id"], "kimi-session-test")

    def test_kimi_resumed_session_mismatch_fails_closed(self) -> None:
        first = self._run("kimi", "kimi-010", model="kimi-code/k3-256k", pool_size=1)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self._run(
            "kimi",
            "kimi-011",
            model="kimi-code/k3-256k",
            pool_size=1,
            extra_env={"FAKE_KIMI_SESSION": "kimi-session-other"},
            check=False,
        )
        self.assertNotEqual(second.returncode, 0)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(receipt["failure_class"], "kimi_session_mismatch")

    def test_kimi_missing_report_fails_closed(self) -> None:
        result = self._run(
            "kimi",
            "kimi-020",
            model="kimi-code/k3-256k",
            pool_size=1,
            extra_env={"FAKE_REPORT_MODE": "missing"},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(receipt["failure_class"], "kimi_protocol_failure")

    def test_opencode_variant_passthrough_and_empty(self) -> None:
        module = self._load_lane_session()
        self.assertEqual(module._opencode_variant("xhigh"), "xhigh")
        self.assertEqual(module._opencode_variant("max"), "max")
        self.assertEqual(module._opencode_variant("none"), "none")
        self.assertEqual(module._opencode_variant(""), "")
        self.assertEqual(module._opencode_variant(None), "")

    def test_kimi_environment_maps_thinking_effort(self) -> None:
        module = self._load_lane_session()
        low = module.provider_environment("kimi", reasoning_effort="low")
        self.assertEqual(low["KIMI_MODEL_THINKING_EFFORT"], "low")
        self.assertEqual(low["KIMI_DISABLE_CRON"], "1")
        medium = module.provider_environment("kimi", reasoning_effort="medium")
        self.assertEqual(medium["KIMI_MODEL_THINKING_EFFORT"], "high")
        self.assertNotIn(
            "KIMI_MODEL_THINKING_EFFORT", module.provider_environment("qwen")
        )

    def test_cursor_uses_stream_json_force_and_reuses_session(self) -> None:
        for task_id in ("cursor-001", "cursor-002"):
            result = self._run(
                "cursor",
                task_id,
                model="composer-2.5",
                pool_size=1,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        first, second = self._calls()
        self.assertIn("-p", first)
        self.assertIn("--force", first)
        self.assertIn("--trust", first)
        self.assertEqual(first[first.index("--output-format") + 1], "stream-json")
        self.assertEqual(first[first.index("--model") + 1], "composer-2.5")
        self.assertNotIn("--resume", first)
        self.assertEqual(
            second[second.index("--resume") + 1], "cursor-session-test"
        )
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "cursor")
        self.assertEqual(receipt["permission_mode"], "force")
        self.assertEqual(receipt["provider_sandbox"], "off")
        self.assertEqual(receipt["session_id"], "cursor-session-test")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(
            self._session_record("cursor")["session_id"], "cursor-session-test"
        )

    def test_opencode_uses_json_run_and_reuses_session(self) -> None:
        for task_id in ("opencode-001", "opencode-002"):
            result = self._run(
                "opencode",
                task_id,
                model="alibaba-token-plan/qwen3.8-max-preview",
                pool_size=1,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        first, second = self._calls()
        self.assertEqual(first[0], "run")
        self.assertIn("--pure", first)
        self.assertEqual(first[first.index("--format") + 1], "json")
        self.assertEqual(first[first.index("--agent") + 1], "lane-writer")
        self.assertEqual(
            first[first.index("--model") + 1],
            "alibaba-token-plan/qwen3.8-max-preview",
        )
        self.assertIn("--dangerously-skip-permissions", first)
        self.assertNotIn("--session", first)
        self.assertEqual(
            second[second.index("--session") + 1], "opencode-session-test"
        )
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "opencode")
        self.assertEqual(receipt["permission_mode"], "skip-permissions")
        self.assertEqual(receipt["provider_sandbox"], "off")
        self.assertEqual(receipt["session_id"], "opencode-session-test")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(
            self._session_record("opencode")["session_id"], "opencode-session-test"
        )

    def test_opencode_environment_isolates_plugins(self) -> None:
        module = self._load_lane_session()
        env = module.provider_environment("opencode")
        self.assertEqual(env["OPENCODE_DISABLE_CLAUDE_CODE"], "1")
        self.assertEqual(env["OPENCODE_DISABLE_DEFAULT_PLUGINS"], "1")
        self.assertIn('"task":"deny"', env["OPENCODE_PERMISSION"])

    def test_cursor_fast_tier_appends_model_suffix(self) -> None:
        module = self._load_lane_session()
        self.assertEqual(
            module._resolve_cursor_model(
                "cursor-grok-4.5-high", service_tier="fast"
            ),
            "cursor-grok-4.5-high-fast",
        )
        self.assertEqual(
            module._resolve_cursor_model(
                "cursor-grok-4.5-high-fast", service_tier="standard"
            ),
            "cursor-grok-4.5-high",
        )

    def test_agy_rejects_tampered_agent_tool_allowlist_before_launch(self) -> None:
        agent = (
            self.fake_home
            / ".gemini"
            / "config"
            / "agents"
            / "agy-writer"
            / "agent.md"
        )
        agent.write_text(
            agent.read_text(encoding="utf-8").replace(
                "  - search_web\n", "  - search_web\n  - invoke_subagent\n"
            ),
            encoding="utf-8",
        )

        result = self._run(
            "agy",
            "agy-tampered-agent",
            model="gemini-3.6-flash-high",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGY agent definition tool allowlist mismatch", result.stderr)
        self.assertFalse(self.args_log.exists())

    def test_read_only_xdg_runtime_falls_back_to_user_tmp(self) -> None:
        unusable = self.root / "runtime-is-a-file"
        unusable.write_text("not a directory\n", encoding="utf-8")

        result = self._run(
            "grok",
            "runtime-fallback",
            extra_env={"XDG_RUNTIME_DIR": str(unusable)},
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._state()["sessions"]["grok:grok:0"]["status"], "idle")

    def test_grok_reuses_session_then_rotates_at_task_limit(self) -> None:
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "002", max_tasks=2)
        self._run("grok", "003", max_tasks=2)

        first, second, third = self._calls()
        self.assertIn("--no-auto-update", first)
        self.assertIn("--no-subagents", first)
        self.assertEqual(
            first[first.index("--permission-mode") + 1], "bypassPermissions"
        )
        self.assertEqual(first[first.index("--sandbox") + 1], "off")
        self.assertEqual(first[first.index("--output-format") + 1], "streaming-json")
        rules = first[first.index("--rules") + 1]
        self.assertIn("task_id=001", rules)
        self.assertIn(f"workspace={self.cwd}", rules)
        expected_prompt_sha = hashlib.sha256(b"Implement task 001\n").hexdigest()
        self.assertIn(f"prompt_sha256={expected_prompt_sha}", rules)
        self.assertIn("owns_paths", rules)
        self.assertIn("--prompt-file", first)
        self.assertNotIn("--single", first)
        first_id = first[first.index("--session-id") + 1]
        self.assertEqual(second[second.index("--resume") + 1], first_id)
        third_id = third[third.index("--session-id") + 1]
        self.assertNotEqual(third_id, first_id)

        state = self._state()
        active = state["sessions"]["grok:grok:0"]
        self.assertEqual(active["session_id"], third_id)
        self.assertEqual(active["tasks"], ["003"])
        self.assertEqual(state["history"][0]["tasks"], ["001", "002"])
        self.assertEqual(state["history"][0]["rotation_reason"], "task_limit")


    def test_parallel_tasks_use_distinct_pool_sessions(self) -> None:
        prompt1 = self.cwd / "parallel-001.md"
        prompt2 = self.cwd / "parallel-002.md"
        prompt1.write_text("Task 001\n", encoding="utf-8")
        prompt2.write_text("Task 002\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.fake_home),
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "0.6",
                "UNUSED_REMOVED": str(self.conversations),
            }
        )

        def command(task_id: str, prompt: Path) -> list[str]:
            return [
                sys.executable,
                str(LANE_SESSION),
                "run",
                "--provider",
                "grok",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                task_id,
                "--role",
                "grok",
                "--cwd",
                str(self.cwd),
                "--prompt-file",
                str(prompt),
                "--output",
                str(self.root / f"parallel-{task_id}.log"),
                "--binary",
                str(self.fake_provider),
                "--model",
                "test-model",
                "--pool-size",
                "2",
            ]

        first = subprocess.Popen(command("001", prompt1), env=env)
        time.sleep(0.1)
        second = subprocess.Popen(command("002", prompt2), env=env)
        self.assertEqual(first.wait(timeout=10), 0)
        self.assertEqual(second.wait(timeout=10), 0)

        calls = self._calls()
        session_ids = {
            call[call.index("--session-id") + 1]
            for call in calls
            if "--session-id" in call
        }
        self.assertEqual(len(session_ids), 2)
        self.assertEqual(set(self._state()["sessions"]), {"grok:grok:0", "grok:grok:1"})

    def test_failed_provider_session_is_rotated_before_next_task(self) -> None:
        failed = self._run("grok", "001", exit_code=9, check=False)
        self.assertEqual(failed.returncode, 9)
        self._run("grok", "002")

        first, second = self._calls()
        failed_id = first[first.index("--session-id") + 1]
        next_id = second[second.index("--session-id") + 1]
        self.assertNotEqual(next_id, failed_id)
        self.assertNotIn("--resume", second)

        state = self._state()
        self.assertEqual(state["history"][0]["rotation_reason"], "provider_exit_9")
        self.assertEqual(state["sessions"]["grok:grok:0"]["tasks"], ["002"])
        self.assertFalse((self.run_dir / ".sessions.lock").exists())
        self.assertFalse((self.run_dir / ".session-locks").exists())

    def test_session_without_workspace_sandbox_is_rotated(self) -> None:
        self._run("grok", "001")
        state_path = self.run_dir / "sessions.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        first_id = state["sessions"]["grok:grok:0"]["session_id"]
        state["sessions"]["grok:grok:0"].pop("sandbox", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")

        self._run("grok", "002")

        active = self._state()["sessions"]["grok:grok:0"]
        self.assertNotEqual(active["session_id"], first_id)
        self.assertEqual(active["sandbox"], "bubblewrap-workspace")
        self.assertEqual(self._state()["history"][0]["rotation_reason"], "sandbox_changed")

    def test_two_runs_in_same_worktree_never_resume_each_others_session(self) -> None:
        second_run = self.root / ".agents" / "runs" / "vk-bot"
        second_run.mkdir(parents=True)

        self._run("grok", "ui-001", run_dir=self.run_dir)
        self._run("grok", "bot-001", run_dir=second_run)
        self._run("grok", "ui-002", run_dir=self.run_dir)
        self._run("grok", "bot-002", run_dir=second_run)

        ui_first, bot_first, ui_second, bot_second = self._calls()
        ui_id = ui_first[ui_first.index("--session-id") + 1]
        bot_id = bot_first[bot_first.index("--session-id") + 1]
        self.assertNotEqual(ui_id, bot_id)
        self.assertEqual(ui_second[ui_second.index("--resume") + 1], ui_id)
        self.assertEqual(bot_second[bot_second.index("--resume") + 1], bot_id)
        self.assertTrue(all("--continue" not in call for call in self._calls()))


    def test_copied_session_state_cannot_cross_run_boundary(self) -> None:
        second_run = self.root / ".agents" / "runs" / "copied-run"
        second_run.mkdir(parents=True)

        self._run("grok", "001", run_dir=self.run_dir)
        shutil.copy2(self.run_dir / "sessions.json", second_run / "sessions.json")
        self._run("grok", "002", run_dir=second_run)

        first, second = self._calls()
        first_id = first[first.index("--session-id") + 1]
        self.assertNotIn("--resume", second)
        second_id = second[second.index("--session-id") + 1]
        self.assertNotEqual(first_id, second_id)
        copied_state = json.loads((second_run / "sessions.json").read_text())
        self.assertEqual(copied_state["history"][0]["rotation_reason"], "run_dir_changed")

    def test_provider_output_is_streamed_through_wrapper_stdout(self) -> None:
        result = self._run("grok", "001")
        self.assertIn("provider complete", result.stdout)

    def test_runtime_materializes_report_from_provider_response(self) -> None:
        result = self._run(
            "grok", "report-001", extra_env={"FAKE_SPLIT_REPORT": "1"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.run_dir / "artifacts" / "report-001" / "report.md"
        self.assertTrue(report.is_file())
        self.assertIn("TASK_ID: report-001", report.read_text(encoding="utf-8"))
        self.assertNotIn("<<<LANE_REPORT", report.read_text(encoding="utf-8"))

    def test_missing_or_wrong_task_report_fails_closed(self) -> None:
        missing = self._run(
            "grok",
            "missing-report",
            extra_env={"FAKE_REPORT_MODE": "missing"},
            check=False,
        )
        self.assertEqual(missing.returncode, 65, missing.stderr)
        missing_receipt = json.loads(
            (self.root / "runtime.json").read_text(encoding="utf-8")
        )
        self.assertEqual(missing_receipt["protocol_error"], "lane report is missing")

        wrong = self._run(
            "grok",
            "wrong-report",
            extra_env={"FAKE_REPORT_TASK_ID": "some-other-task"},
            check=False,
        )
        self.assertEqual(wrong.returncode, 65, wrong.stderr)
        wrong_receipt = json.loads(
            (self.root / "runtime.json").read_text(encoding="utf-8")
        )
        self.assertEqual(wrong_receipt["protocol_error"], "lane report task_id mismatch")

    def test_duplicate_or_wrong_prompt_report_fails_closed(self) -> None:
        duplicate = self._run(
            "grok",
            "duplicate-report",
            extra_env={"FAKE_DUPLICATE_REPORT": "1"},
            check=False,
        )
        self.assertEqual(duplicate.returncode, 65, duplicate.stderr)
        duplicate_receipt = json.loads(
            (self.root / "runtime.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            duplicate_receipt["protocol_error"],
            "lane report envelope must appear exactly once",
        )

        # Model-written PROMPT_SHA256 is ignored — control plane stamps identity.
        wrong_prompt = self._run(
            "grok",
            "wrong-prompt-report",
            extra_env={"FAKE_REPORT_PROMPT_SHA256": "0" * 64},
            check=False,
        )
        self.assertEqual(wrong_prompt.returncode, 0, wrong_prompt.stderr)
        prompt_receipt = json.loads(
            (self.root / "runtime.json").read_text(encoding="utf-8")
        )
        self.assertTrue(prompt_receipt.get("protocol_valid"))
        self.assertIsNone(prompt_receipt.get("protocol_error"))
        # Stamped report uses the real prompt digest, not the model's fake line
        report_path = (
            self.run_dir / "artifacts" / "wrong-prompt-report" / "report.md"
        )
        report_text = report_path.read_text(encoding="utf-8")
        self.assertNotIn("PROMPT_SHA256: " + ("0" * 64), report_text)
        self.assertIn(
            f"PROMPT_SHA256: {prompt_receipt['prompt_sha256']}", report_text
        )

    def test_identity_fields_stamped_even_if_model_omits_or_typos_sha(self) -> None:
        """PROMPT_SHA256 is control-plane stamped; STATUS is required from model."""
        from importlib.machinery import SourceFileLoader
        import importlib.util

        path = str(Path(__file__).resolve().parents[1] / "bin" / "lane-session")
        loader = SourceFileLoader("lane_session_stamp", path)
        spec = importlib.util.spec_from_loader("lane_session_stamp", loader)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["lane_session_stamp"] = mod
        loader.exec_module(mod)

        expected = "a" * 64
        # Typo in SHA
        typo = (
            f"{mod.REPORT_BEGIN}\n"
            f"TASK_ID: 001\n"
            f"PROMPT_SHA256: {expected}4\n"
            f"STATUS: complete\n"
            f"summary here\n"
            f"{mod.REPORT_END}\n"
        )
        report = mod.extract_lane_report(
            typo, task_id="001", prompt_sha256=expected, begin_count=1, end_count=1
        )
        self.assertEqual(
            report.splitlines()[:3],
            [f"TASK_ID: 001", f"PROMPT_SHA256: {expected}", "STATUS: complete"],
        )
        self.assertNotIn(expected + "4", report)

        # Model omits PROMPT_SHA256 entirely
        bare = (
            f"{mod.REPORT_BEGIN}\n"
            f"STATUS: complete\n"
            f"done\n"
            f"{mod.REPORT_END}\n"
        )
        report2 = mod.extract_lane_report(
            bare, task_id="001", prompt_sha256=expected, begin_count=1, end_count=1
        )
        self.assertIn(f"PROMPT_SHA256: {expected}", report2)
        self.assertIn("STATUS: complete", report2)

        # Wrong TASK_ID still fails (real identity confusion)
        with self.assertRaises(ValueError) as ctx:
            mod.extract_lane_report(
                (
                    f"{mod.REPORT_BEGIN}\n"
                    f"TASK_ID: other\n"
                    f"STATUS: complete\n"
                    f"{mod.REPORT_END}\n"
                ),
                task_id="001",
                prompt_sha256=expected,
                begin_count=1,
                end_count=1,
            )
        self.assertIn("task_id mismatch", str(ctx.exception))

        # Trailing chatter after END is ignored (Cursor often adds a summary).
        trailing = (
            f"{mod.REPORT_BEGIN}\n"
            f"STATUS: partial\n"
            f"owned L0 green\n"
            f"{mod.REPORT_END}\n"
            f"Задача **001** сделана. STATUS: **partial** — package red outside owns.\n"
        )
        report3 = mod.extract_lane_report(
            trailing, task_id="001", prompt_sha256=expected, begin_count=1, end_count=1
        )
        self.assertIn("STATUS: partial", report3.splitlines()[:3])
        self.assertIn("owned L0 green", report3)
        self.assertNotIn("Задача", report3)

    def test_cancelled_provider_does_not_materialize_complete_report(self) -> None:
        result = self._run(
            "grok",
            "cancelled-report",
            extra_env={"FAKE_STOP_REASON": "Cancelled"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        self.assertFalse(
            (self.run_dir / "artifacts" / "cancelled-report" / "report.md").exists()
        )

    def test_symlinked_report_target_is_rejected(self) -> None:
        outside = self.root / "outside-report.md"
        outside.write_text("preserve me\n", encoding="utf-8")
        report_dir = self.run_dir / "artifacts" / "symlink-report"
        report_dir.mkdir(parents=True)
        (report_dir / "report.md").symlink_to(outside)

        result = self._run("grok", "symlink-report", check=False)

        self.assertEqual(result.returncode, 65, result.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), "preserve me\n")
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertIn("refusing symlinked lane report path", receipt["protocol_error"])

    def test_symlinked_report_ancestor_is_rejected(self) -> None:
        outside = self.root / "outside-artifacts"
        outside.mkdir()
        (self.run_dir / "artifacts").symlink_to(outside, target_is_directory=True)

        result = self._run("grok", "ancestor-symlink", check=False)

        self.assertEqual(result.returncode, 65, result.stderr)
        self.assertFalse((outside / "ancestor-symlink" / "report.md").exists())
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertIn("refusing symlinked lane report path", receipt["protocol_error"])

    def test_provider_can_write_source_but_cannot_write_run_control_plane(self) -> None:
        forged = self.run_dir / "provider-forged.json"
        result = self._run(
            "grok",
            "boundary-001",
            extra_env={"FAKE_CONTROL_PROBE": str(forged)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(forged.exists())
        self.assertEqual(
            (self.cwd / "provider-write-proof.txt").read_text(encoding="utf-8"),
            "source write allowed\n",
        )
        report = self.run_dir / "artifacts" / "boundary-001" / "report.md"
        report_text = report.read_text(encoding="utf-8")
        self.assertIn("CONTROL_PLANE_WRITE: denied", report_text)
        self.assertIn("PROC_CONTROL_WRITE: denied", report_text)

    def test_sandbox_preserves_systemd_resolved_resolver_target(self) -> None:
        resolver_target = Path("/etc/resolv.conf").resolve(strict=True)
        if not resolver_target.is_relative_to(Path("/run/systemd/resolve")):
            self.skipTest("host resolv.conf does not target systemd-resolved under /run")
        lane_session = runpy.run_path(
            str(LANE_SESSION), run_name="lane_session_dns_regression"
        )
        sandboxed = lane_session["sandbox_provider_command"](
            [
                sys.executable,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    "print(json.dumps({"
                    "'resolv_conf_readable': Path('/etc/resolv.conf').is_file(), "
                    f"'resolver_target_readable': Path({str(resolver_target)!r}).is_file()"
                    "}))"
                ),
            ],
            provider="grok",
            run_dir=self.run_dir,
            cwd=self.cwd,
            home=self.fake_home,
        )

        result = subprocess.run(
            sandboxed,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        probe = json.loads(result.stdout)
        self.assertTrue(probe["resolver_target_readable"])
        self.assertTrue(probe["resolv_conf_readable"])

    def test_provider_cannot_reach_host_socket_tmp_or_unsafe_environment(self) -> None:
        socket_path = self.grok_home / "host-control.sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen(1)
        self.addCleanup(server.close)
        host_tmp = self.root / "host-tmp-secret"
        host_tmp.write_text("host only\n", encoding="utf-8")
        scrub_log = self.grok_home / "sandbox-boundary.json"

        result = self._run(
            "grok",
            "socket-boundary",
            extra_env={
                "FAKE_SOCKET_PROBE": str(socket_path),
                "FAKE_HOST_TMP_PROBE": str(host_tmp),
                "FAKE_ENV_SCRUB_LOG": str(scrub_log),
                "DOCKER_HOST": "unix:///var/run/docker.sock",
                "SSH_AUTH_SOCK": str(socket_path),
                "DBUS_SESSION_BUS_ADDRESS": f"unix:path={socket_path}",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        boundary = json.loads(scrub_log.read_text(encoding="utf-8"))
        self.assertEqual(boundary["socket_connect"], "denied")
        self.assertFalse(boundary["host_tmp_visible"])
        self.assertIsNone(boundary["docker_host"])
        self.assertIsNone(boundary["ssh_auth_sock"])
        self.assertIsNone(boundary["dbus"])

    def test_grok_writer_disables_claude_compat_hooks(self) -> None:
        env_log = self.grok_home / "provider-env.txt"

        result = self._run(
            "grok",
            "hooks-001",
            extra_env={"FAKE_ENV_LOG": str(env_log)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(env_log.read_text(encoding="utf-8"), "0,1")

    def test_streaming_result_writes_sanitized_runtime_receipt(self) -> None:
        result = self._run("grok", "receipt-001")

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["provider"], "grok")
        self.assertEqual(receipt["provider_version"], "0.2.103-test")
        self.assertEqual(receipt["model"], "test-model")
        self.assertEqual(receipt["reasoning_effort"], "high")
        self.assertEqual(receipt["sandbox"], "bubblewrap-workspace")
        self.assertEqual(receipt["provider_sandbox"], "off")
        self.assertFalse(receipt["subagents_enabled"])
        self.assertEqual(receipt["session_id"], self._state()["sessions"]["grok:grok:0"]["session_id"])
        self.assertEqual(receipt["provider_exit_code"], 0)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["stop_reason"], "EndTurn")
        self.assertEqual(receipt["usage"]["total_tokens"], 17)
        self.assertEqual(receipt["total_cost_usd_ticks"], 100000000)
        self.assertNotIn("request_id", receipt)

    def test_provider_control_strings_cannot_leak_into_runtime_artifacts(self) -> None:
        secret = "secret-customer-token"
        result = self._run(
            "grok",
            "control-string-001",
            extra_env={
                "FAKE_VERSION_TEXT": f"grok 9.8.7 {secret}",
                "FAKE_STOP_REASON": secret,
            },
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        receipt_source = (self.root / "runtime.json").read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        diagnostic = (self.root / "task-control-string-001.log").read_text(
            encoding="utf-8"
        )
        self.assertEqual(receipt["provider_version"], "9.8.7")
        self.assertEqual(receipt["stop_reason"], "Other")
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(
            receipt["protocol_error"],
            "unsuccessful terminal reason: Other",
        )
        self.assertNotIn(secret, receipt_source)
        self.assertNotIn(secret, diagnostic)

    def test_malformed_stream_fails_closed_and_invalidates_session(self) -> None:
        result = self._run(
            "grok",
            "malformed-001",
            extra_env={"FAKE_STREAM_MODE": "malformed"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_65")
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(receipt["provider_exit_code"], 0)
        self.assertEqual(receipt["exit_code"], 65)
        self.assertEqual(receipt["protocol_error"], "malformed streaming-json")
        diagnostic = (self.root / "task-malformed-001.log").read_text(encoding="utf-8")
        self.assertIn("grok protocol error", diagnostic)
        self.assertNotIn("not-json", diagnostic)

    def test_missing_end_event_fails_closed(self) -> None:
        result = self._run(
            "grok",
            "missing-end-001",
            extra_env={"FAKE_STREAM_MODE": "missing-end"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["protocol_error"], "stream ended without an end event")

    def test_unsuccessful_terminal_reasons_fail_closed(self) -> None:
        for index, stop_reason in enumerate(("Cancelled", "Error", "MaxTokens"), start=1):
            with self.subTest(stop_reason=stop_reason):
                result = self._run(
                    "grok",
                    f"terminal-failure-{index}",
                    extra_env={"FAKE_STOP_REASON": stop_reason},
                    check=False,
                )

                self.assertEqual(result.returncode, 65, result.stderr)
                receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
                self.assertFalse(receipt["protocol_valid"])
                expected_reason = stop_reason if stop_reason in {"Cancelled", "Error"} else "Other"
                self.assertEqual(receipt["stop_reason"], expected_reason)
                self.assertEqual(
                    receipt["protocol_error"],
                    f"unsuccessful terminal reason: {expected_reason}",
                )

    def test_provider_stderr_is_diagnostic_not_structured_output(self) -> None:
        result = self._run(
            "grok",
            "stderr-001",
            extra_env={"FAKE_STDERR": "provider warning with sensitive detail"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["protocol_valid"])
        diagnostic = (self.root / "task-stderr-001.log").read_text(encoding="utf-8")
        self.assertIn("grok stderr", diagnostic)
        self.assertNotIn("sensitive detail", diagnostic)

    def test_settings_failure_is_typed_without_leaking_raw_stderr(self) -> None:
        secret = "customer-secret-token"
        result = self._run(
            "grok",
            "settings-failure",
            exit_code=1,
            extra_env={
                "FAKE_STDERR": f"Settings fetch failed after 3 attempts {secret}"
            },
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        receipt_source = (self.root / "runtime.json").read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        self.assertEqual(receipt["failure_class"], "grok_bootstrap_transient")
        self.assertTrue(receipt["failure_retryable"])
        self.assertTrue(receipt["fallback_eligible"])
        self.assertNotIn(secret, receipt_source)
        self.assertNotIn(
            secret,
            (self.root / "task-settings-failure.log").read_text(encoding="utf-8"),
        )

    def test_dns_oidc_bootstrap_failure_is_fallback_eligible_without_leaking_detail(self) -> None:
        secret = "customer-secret-token"
        result = self._run(
            "grok",
            "dns-oidc-failure",
            exit_code=1,
            extra_env={
                "FAKE_STDERR": (
                    "Failed to fetch OIDC discovery document: DNS error: "
                    f"temporary failure in name resolution {secret}"
                )
            },
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        receipt_source = (self.root / "runtime.json").read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        self.assertEqual(receipt["failure_class"], "grok_bootstrap_transient")
        self.assertTrue(receipt["failure_retryable"])
        self.assertTrue(receipt["fallback_eligible"])
        self.assertNotIn(secret, receipt_source)
        self.assertNotIn(
            secret,
            (self.root / "task-dns-oidc-failure.log").read_text(encoding="utf-8"),
        )

    def test_zero_exit_rate_limit_error_event_is_fallback_eligible(self) -> None:
        result = self._run(
            "grok",
            "rate-limit-event",
            extra_env={
                "FAKE_STREAM_MODE": "error",
                "FAKE_ERROR_MESSAGE": "rate limit reached",
            },
            check=False,
        )

        self.assertEqual(result.returncode, 65)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider_exit_code"], 0)
        self.assertEqual(receipt["failure_class"], "grok_quota_exhausted")
        self.assertTrue(receipt["failure_retryable"])
        self.assertTrue(receipt["fallback_eligible"])

    def test_rate_limit_error_followed_by_terminal_error_remains_fallback_eligible(self) -> None:
        result = self._run(
            "grok",
            "rate-limit-terminal-error",
            extra_env={
                "FAKE_STREAM_MODE": "error-end",
                "FAKE_ERROR_MESSAGE": "rate limit reached",
                "FAKE_STOP_REASON": "Error",
            },
            check=False,
        )

        self.assertEqual(result.returncode, 65)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["protocol_error"], "unsuccessful terminal reason: Error")
        self.assertEqual(receipt["failure_class"], "grok_quota_exhausted")
        self.assertTrue(receipt["failure_retryable"])
        self.assertTrue(receipt["fallback_eligible"])

    def test_provider_credentials_are_not_shared_across_vendors(self) -> None:
        grok_log = self.cwd / "grok-env.json"
        codex_log = self.cwd / "codex-env.json"
        grok_version_log = self.cwd / "grok-version-env.json"
        codex_version_log = self.cwd / "codex-version-env.json"
        secret_env = {
            "OPENAI_API_KEY": "openai-secret",
            "GROK_API_KEY": "grok-secret",
            "XAI_API_KEY": "xai-secret",
            "CODEX_HOME": str(self.fake_home / ".codex"),
        }

        self._run(
            "grok",
            "grok-credential-boundary",
            extra_env={
                **secret_env,
                "FAKE_PROVIDER_SECRET_LOG": str(grok_log),
                "FAKE_VERSION_PROBE_LOG": str(grok_version_log),
            },
        )
        self._run(
            "codex",
            "codex-credential-boundary",
            model="gpt-5.6-sol",
            extra_env={
                **secret_env,
                "FAKE_PROVIDER_SECRET_LOG": str(codex_log),
                "FAKE_VERSION_PROBE_LOG": str(codex_version_log),
            },
        )

        grok_env = json.loads(grok_log.read_text(encoding="utf-8"))
        self.assertEqual(grok_env["grok"], "grok-secret")
        self.assertEqual(grok_env["xai"], "xai-secret")
        self.assertIsNone(grok_env["openai"])
        self.assertIsNone(grok_env["codex_home"])
        self.assertFalse(grok_env["host_codex_auth_readable"])
        self.assertTrue(grok_env["host_grok_auth_readable"])
        codex_env = json.loads(codex_log.read_text(encoding="utf-8"))
        self.assertEqual(codex_env["openai"], "openai-secret")
        self.assertIsNone(codex_env["grok"])
        self.assertIsNone(codex_env["xai"])
        self.assertNotEqual(codex_env["codex_home"], secret_env["CODEX_HOME"])
        self.assertFalse(codex_env["host_codex_auth_readable"])
        self.assertFalse(codex_env["host_grok_auth_readable"])
        self.assertTrue(codex_env["active_codex_auth_readable"])
        self.assertEqual(
            json.loads(grok_version_log.read_text(encoding="utf-8")), grok_env
        )
        self.assertEqual(
            json.loads(codex_version_log.read_text(encoding="utf-8")), codex_env
        )

    def test_codex_binary_under_hidden_host_home_is_mounted_separately(self) -> None:
        packaged_binary = self.fake_home / ".codex" / "packages" / "fake-provider"
        packaged_binary.parent.mkdir(parents=True)
        shutil.copy2(self.fake_provider, packaged_binary)
        packaged_binary.chmod(0o755)
        binary_link = self.cwd / "codex-provider"
        binary_link.symlink_to(packaged_binary)

        result = self._run(
            "codex",
            "codex-packaged-binary",
            binary=binary_link,
            model="gpt-5.6-sol",
            extra_env={"FAKE_VERSION_WARNING": "WARNING: temporary provider home"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "codex")
        self.assertEqual(receipt["provider_version"], "0.2.103-test")

    def test_effective_grok_model_mismatch_fails_closed(self) -> None:
        result = self._run(
            "grok",
            "model-mismatch",
            model="grok-4.5",
            extra_env={"FAKE_EFFECTIVE_MODEL": "grok-3"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(receipt["failure_class"], "grok_model_mismatch")
        self.assertFalse(
            (self.run_dir / "artifacts" / "model-mismatch" / "report.md").exists()
        )

    def test_codex_sol_high_uses_isolated_typed_runtime(self) -> None:
        codex_home_log = self.cwd / "codex-home.json"
        result = self._run(
            "codex",
            "codex-fallback",
            model="gpt-5.6-sol",
            extra_env={"FAKE_CODEX_HOME_LOG": str(codex_home_log)},
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        args = self._calls()[0]
        self.assertEqual(args[0], "exec")
        self.assertEqual(args[args.index("--model") + 1], "gpt-5.6-sol")
        self.assertIn('model_reasoning_effort="high"', args)
        self.assertNotIn("--ephemeral", args)
        self.assertNotIn("resume", args)
        self.assertIn("--ignore-rules", args)
        self.assertIn("--profile", args)
        self.assertEqual(args[args.index("--profile") + 1], "lane-writer")
        self.assertNotIn("--ignore-user-config", args)
        # Bare lane-writer disables host noise (MCP apps / multi-agent / plugins…).
        disables = [
            args[i + 1]
            for i, token in enumerate(args)
            if token == "--disable" and i + 1 < len(args)
        ]
        for feature in (
            "multi_agent",
            "plugins",
            "memories",
            "apps",
            "browser_use",
            "goals",
            "hooks",
            "skill_search",
            "image_generation",
            "computer_use",
        ):
            self.assertIn(feature, disables)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["provider"], "codex")
        self.assertEqual(receipt["model"], "gpt-5.6-sol")
        self.assertEqual(receipt["reasoning_effort"], "high")
        self.assertEqual(receipt["mode"], "new")
        self.assertEqual(receipt["session_id"], "codex-thread-test")
        self.assertEqual(receipt["stop_reason"], "TurnCompleted")
        self.assertTrue(receipt["protocol_valid"])
        self.assertEqual(
            self._session_record("codex")["session_id"], "codex-thread-test"
        )
        codex_home = json.loads(codex_home_log.read_text(encoding="utf-8"))
        self.assertTrue(codex_home["auth_exists"])
        self.assertTrue(codex_home["config_exists"])
        self.assertTrue(codex_home["skills_empty"])
        self.assertFalse(codex_home["has_mcp_servers_block"])
        self.assertNotEqual(Path(codex_home["path"]), self.fake_home / ".codex")
        self.assertTrue(Path(codex_home["path"]).is_dir())

    def test_codex_reuses_session_then_rotates_at_task_limit(self) -> None:
        home_log = self.cwd / "codex-home.json"
        extra = {"FAKE_CODEX_HOME_LOG": str(home_log)}
        self._run("codex", "001", max_tasks=2, extra_env=extra)
        home1 = json.loads(home_log.read_text(encoding="utf-8"))["path"]
        self._run("codex", "002", max_tasks=2, extra_env=extra)
        home2 = json.loads(home_log.read_text(encoding="utf-8"))["path"]
        self._run("codex", "003", max_tasks=2, extra_env=extra)

        first, second, third = self._calls()
        self.assertEqual(first[0], "exec")
        self.assertNotIn("resume", first)
        self.assertEqual(second[second.index("resume") + 1], "codex-thread-test")
        self.assertNotIn("resume", third)
        self.assertEqual(home1, home2)
        self.assertTrue(Path(home1).is_dir())

        state = self._state()
        self.assertEqual(state["history"][0]["rotation_reason"], "task_limit")
        self.assertEqual(state["history"][0]["tasks"], ["001", "002"])
        self.assertEqual(state["sessions"]["codex:grok:0"]["tasks"], ["003"])

    def test_codex_resumed_thread_mismatch_fails_closed(self) -> None:
        first = self._run("codex", "codex-010", pool_size=1)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self._run(
            "codex",
            "codex-011",
            pool_size=1,
            extra_env={"FAKE_CODEX_SESSION": "codex-thread-other"},
            check=False,
        )
        self.assertNotEqual(second.returncode, 0)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertIn("thread_id mismatch", receipt.get("protocol_error", ""))

    def test_launch_exception_writes_sanitized_failure_receipt(self) -> None:
        broken_provider = self.grok_home / "broken-provider-secret-token"
        broken_provider.write_text("not an executable format\n", encoding="utf-8")
        broken_provider.chmod(0o755)

        result = self._run(
            "grok",
            "launch-failure-001",
            binary=broken_provider,
            check=False,
        )

        self.assertEqual(result.returncode, 127)
        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_127")
        receipt_path = self.root / "runtime.json"
        self.assertTrue(receipt_path.is_file())
        receipt_source = receipt_path.read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        self.assertEqual(receipt["provider_exit_code"], 127)
        self.assertEqual(receipt["exit_code"], 127)
        self.assertEqual(receipt["failure_class"], "grok_provider_failed")
        self.assertFalse(receipt["fallback_eligible"])
        self.assertFalse(receipt["protocol_valid"])
        self.assertNotIn("failure_message", receipt)
        self.assertNotIn("secret-token", receipt_source)
        self.assertNotIn("Exec format", receipt_source)

    def test_provider_log_is_bounded_without_hiding_live_output(self) -> None:
        result = self._run(
            "grok",
            "large-output-001",
            extra_env={"FAKE_TEXT_SIZE": str(1024 * 1024 + 100)},
        )

        self.assertIn("x" * 100, result.stdout)
        self.assertLessEqual((self.root / "task-large-output-001.log").stat().st_size, 1024 * 1024)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["log_truncated"])

    def test_repeated_task_id_still_counts_toward_rotation_limit(self) -> None:
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "001", max_tasks=2)

        first, second, third = self._calls()
        first_id = first[first.index("--session-id") + 1]
        self.assertEqual(second[second.index("--resume") + 1], first_id)
        third_id = third[third.index("--session-id") + 1]
        self.assertNotEqual(third_id, first_id)
        state = self._state()
        self.assertEqual(state["history"][0]["success_count"], 2)


    def test_sigterm_stops_provider_and_invalidates_session(self) -> None:
        prompt = self.cwd / "signal-task.md"
        prompt.write_text("Wait for termination\n", encoding="utf-8")
        provider_pid = self.grok_home / "provider.pid"
        child_pid_file = self.grok_home / "provider-child.pid"
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.fake_home),
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "30",
                "FAKE_PID_FILE": str(provider_pid),
                "FAKE_CHILD_PID_FILE": str(child_pid_file),
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        command = [
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            "grok",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "signal-001",
            "--role",
            "grok",
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(self.root / "signal-task.log"),
            "--binary",
            str(self.fake_provider),
            "--model",
            "test-model",
        ]
        manager = subprocess.Popen(command, env=env)
        deadline = time.monotonic() + 5
        while not provider_pid.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(provider_pid.exists())
        deadline = time.monotonic() + 5
        while not child_pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(child_pid_file.exists())
        ps_output = subprocess.run(
            ["ps", "-eo", "pid=,ppid="],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        children: dict[int, list[int]] = {}
        for raw_line in ps_output.splitlines():
            pid_text, parent_text = raw_line.split()
            children.setdefault(int(parent_text), []).append(int(pid_text))
        descendants: list[int] = []
        pending = [manager.pid]
        while pending:
            parent = pending.pop()
            direct = children.get(parent, [])
            descendants.extend(direct)
            pending.extend(direct)
        self.assertGreaterEqual(len(descendants), 2)

        os.kill(manager.pid, signal.SIGTERM)
        self.assertEqual(manager.wait(timeout=5), 143)
        for pid in descendants:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"provider descendant {pid} survived lane-session SIGTERM")

        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_143")

    def test_lane_exec_observes_streamed_provider_activity(self) -> None:
        prompt = self.cwd / "long-task.md"
        prompt.write_text("Stay active\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.fake_home),
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "6",
                "FAKE_PULSE": "0.5",
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        command = [
            sys.executable,
            str(LANE_EXEC),
            "--idle",
            "5",
            "--max",
            "12",
            "--",
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            "grok",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "long-001",
            "--role",
            "grok",
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(self.root / "long-task.log"),
            "--binary",
            str(self.fake_provider),
            "--model",
            "test-model",
        ]
        result = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GROK_EVENT thought", result.stdout)
        self.assertNotIn("provider pulse", result.stdout)
        self.assertNotIn("IDLE timeout", result.stderr)

if __name__ == "__main__":
    unittest.main()

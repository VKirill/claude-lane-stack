from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "bin" / "agents-doctor"

# This whole file exercises agents-doctor's bubblewrap-era detection and
# gating logic (fake `bwrap` scripts that exit 0/1, or are absent, standing
# in for a real Linux bwrap install). Since agents-doctor now selects its
# sandbox backend per-host (bubblewrap on Linux, seatbelt/sandbox-exec on
# macOS — see bin/sandbox_backend.py), every subprocess below pins the
# backend to "bubblewrap" so this Linux-oriented coverage keeps exercising
# the same code paths regardless of which OS actually runs the test suite.
# macOS/seatbelt-specific coverage lives in its own tests (see
# test_darwin_auto_backend_uses_seatbelt_and_needs_no_bubblewrap below and
# tests/test_sandbox_backend.py).
BUBBLEWRAP_ENV = {"LANE_SANDBOX_BACKEND": "bubblewrap"}


class AgentsDoctorTest(unittest.TestCase):
    def test_grok_is_preferred_and_agy_requires_gemini_36(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                executable.chmod(0o755)
            agy = fake_bin / "agy"
            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.6-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo agy-writer && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            agy.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertTrue(payload["tools"]["agy"]["present"])
            self.assertEqual(payload["lanes"]["fast_write"], "codex")

            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && "
                "printf '%s\\n' 'gemini-3.8-flash-high\tGemini 3.8 Flash (High)' && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo agy-writer && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            labeled = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertTrue(__import__("json").loads(labeled.stdout)["tools"]["agy"]["present"])

            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.5-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo agy-writer && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            missing = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            missing_payload = __import__("json").loads(missing.stdout)
            self.assertFalse(missing_payload["tools"]["agy"]["present"])
            self.assertEqual(
                missing_payload["tools"]["agy"]["unavailable_reason"],
                "gemini-3.8-flash-high unavailable",
            )

            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.6-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo consult && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            missing_agent = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            missing_agent_payload = __import__("json").loads(missing_agent.stdout)
            self.assertFalse(missing_agent_payload["tools"]["agy"]["present"])
            self.assertEqual(
                missing_agent_payload["tools"]["agy"]["unavailable_reason"],
                "agy-writer agent unavailable",
            )

    def test_bubblewrap_probe_matches_lane_network_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            args_log = root / "bwrap-args.log"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            bwrap = fake_bin / "bwrap"
            bwrap.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$BWRAP_ARGS_LOG\"\n",
                encoding="utf-8",
            )
            bwrap.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = str(fake_bin)
            env["BWRAP_ARGS_LOG"] = str(args_log)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            arguments = args_log.read_text(encoding="utf-8").splitlines()
            self.assertIn("--unshare-ipc", arguments)
            run_tmpfs = arguments.index("--tmpfs")
            self.assertEqual(arguments[run_tmpfs + 1], "/run")
            resolver_target = Path("/etc/resolv.conf").resolve(strict=True)
            if resolver_target.is_relative_to(Path("/run")):
                self.assertIn(str(resolver_target), arguments)
            self.assertIn("/etc/resolv.conf", " ".join(arguments))

    def test_resolver_probe_failure_disables_grok_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            bwrap = fake_bin / "bwrap"
            bwrap.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"$*\" == *'/etc/resolv.conf'* ]] && exit 1\n"
                "exit 0\n",
                encoding="utf-8",
            )
            bwrap.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertTrue(payload["tools"]["bubblewrap"]["operational"])
            self.assertFalse(
                payload["tools"]["bubblewrap"]["resolver_operational"]
            )
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(payload["profile"], "full")
            self.assertEqual(payload["lanes"]["main_write"], "codex")
            self.assertEqual(
                payload["tools"]["grok"]["unavailable_reason"],
                "bubblewrap resolver unavailable",
            )

    @unittest.skipUnless(
        sys.platform == "darwin",
        "exercises the real macOS sandbox-exec probe (auto backend selection)",
    )
    def test_darwin_auto_backend_uses_seatbelt_and_needs_no_bubblewrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            # No fake `bwrap` anywhere on PATH and no LANE_SANDBOX_BACKEND
            # override: "auto" selection must land on seatbelt on Darwin and
            # gate providers on the real /usr/bin/sandbox-exec probe instead.
            env = os.environ.copy()
            env.pop("LANE_SANDBOX_BACKEND", None)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertEqual(payload["tools"]["sandbox"]["backend"], "seatbelt")
            self.assertTrue(payload["tools"]["sandbox"]["present"])
            self.assertTrue(payload["tools"]["sandbox"]["operational"])
            self.assertFalse(payload["tools"]["bubblewrap"]["present"])
            self.assertTrue(payload["tools"]["grok"]["present"])
            self.assertIsNone(payload["tools"]["grok"]["unavailable_reason"])

    def test_grok_routing_names_read_only_lane_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [str(DOCTOR), "--apply", "--writer-provider", "grok", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("fast_write: grok  # agent: run-supervisor", profile)
            self.assertIn("main_write: grok  # agent: run-supervisor", profile)
            self.assertNotIn("agent: grok-implementer", profile)

    def test_apply_opencode_writer_writes_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "opencode", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "opencode",
                    "--writer-agent",
                    "wiki-writer",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: opencode  # agent: run-supervisor", profile)
            self.assertIn("provider: opencode", profile)
            self.assertIn("agent: wiki-writer", profile)

    def test_apply_codex_writer_is_luna_max_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "codex",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: codex", profile)
            self.assertIn("provider: codex", profile)
            self.assertIn("model: gpt-5.6-luna", profile)
            self.assertIn("reasoning_effort: max", profile)
            self.assertIn("pm_read:", profile)
            self.assertIn("enabled: false", profile)
            self.assertIn("workspace:", profile)
            self.assertIn("mode: auto", profile)
            self.assertIn("session_max_tasks: 10", profile)
            self.assertIn("ui:", profile)
            self.assertIn("language: en", profile)

            in_place = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "codex",
                    "--workspace-mode",
                    "in_place",
                    "--session-max-tasks",
                    "1",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(in_place.returncode, 0, in_place.stderr + in_place.stdout)
            profile2 = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("mode: in_place", profile2)
            self.assertIn("session_max_tasks: 1", profile2)

    def test_setup_writes_routing_and_night_shift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "qwen", "kimi", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            off = subprocess.run(
                [
                    str(DOCTOR),
                    "setup",
                    str(repo),
                    "--yes",
                    "--writer-provider",
                    "qwen",
                    "--night-review",
                    "off",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(off.returncode, 0, off.stderr + off.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            night = (repo / ".agents" / "night-shift.yaml").read_text(encoding="utf-8")
            self.assertIn("main_write: qwen", profile)
            self.assertIn("enabled: false", night)

            on = subprocess.run(
                [
                    str(DOCTOR),
                    "setup",
                    str(repo),
                    "--yes",
                    "--writer-provider",
                    "qwen",
                    "--night-review",
                    "on",
                    "--max-fix-tasks",
                    "7",
                    "--no-auto-merge",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(on.returncode, 0, on.stderr + on.stdout)
            night = (repo / ".agents" / "night-shift.yaml").read_text(encoding="utf-8")
            self.assertIn("enabled: true", night)
            self.assertIn("provider: qwen", night)
            self.assertIn("max_fix_tasks: 7", night)
            self.assertIn("auto_merge: false", night)

    def test_installed_grok_without_bubblewrap_is_not_routed_as_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(payload["profile"], "full")
            self.assertEqual(payload["lanes"]["main_write"], "codex")
            self.assertIn("bubblewrap is required", " ".join(payload["notes"]))

    def test_installed_but_inoperable_bubblewrap_disables_grok_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            bwrap = fake_bin / "bwrap"
            bwrap.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            bwrap.chmod(0o755)

            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertTrue(payload["tools"]["bubblewrap"]["present"])
            self.assertFalse(payload["tools"]["bubblewrap"]["operational"])
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(
                payload["tools"]["grok"]["unavailable_reason"],
                "bubblewrap probe failed",
            )

    def test_apply_fills_missing_docs_without_resetting_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            agents = repo / ".agents"
            agents.mkdir()
            (agents / "routing.profile.yaml").write_text(
                "\n".join(
                    [
                        "lanes:",
                        "  main_write: grok",
                        "writer:",
                        "  provider: grok",
                        "  model: grok-4.5",
                        "stages:",
                        "  memory:",
                        "    enabled: true",
                        "    provider: codex",
                        "    model: gpt-5.6-luna",
                        "notes:",
                        "  - []",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [str(DOCTOR), "--apply", "--writer-provider", "grok", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            profile = (agents / "routing.profile.yaml").read_text(encoding="utf-8")
            self.assertIn("  docs:", profile)
            self.assertRegex(
                profile, r"(?m)^  memory:\n(?:    .*\n)*    enabled: true"
            )
            (repo / "CLAUDE.md").write_text("# App\n", encoding="utf-8")
            result2 = subprocess.run(
                [str(DOCTOR), "--apply", "--writer-provider", "grok", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result2.returncode, 0, result2.stderr)
            self.assertIn(
                "<!-- lane-memory:core -->",
                (repo / "CLAUDE.md").read_text(encoding="utf-8"),
            )

    def test_apply_browser_qa_provider_and_backend_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "kimi", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "kimi",
                    "--browser-qa",
                    "on",
                    "--browser-qa-provider",
                    "claude",
                    "--browser-qa-backend",
                    "chrome-qa",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("  browser_qa:", profile)
            self.assertRegex(
                profile,
                r"(?m)^  browser_qa:\n(?:    .*\n)*    provider: claude\n",
            )
            self.assertRegex(
                profile,
                r"(?m)^  browser_qa:\n(?:    .*\n)*    backend: chrome-qa\n",
            )
            self.assertNotIn("approve: never", profile)  # default stays auto

    def test_auto_prefers_cursor_grok_46_medium_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            cursor = fake_bin / "cursor-agent"
            cursor.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == --list-models ]] && "
                "printf '%s\\n' 'cursor-grok-4.6-medium-fast' 'composer-2.5' && exit 0\n"
                "echo 'fake 1.0'\n",
                encoding="utf-8",
            )
            cursor.chmod(0o755)
            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "auto",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: cursor", profile)
            self.assertIn("model: cursor-grok-4.6-medium", profile)
            self.assertIn("service_tier: fast", profile)

    def test_auto_falls_back_to_codex_luna_high_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            cursor = fake_bin / "cursor-agent"
            cursor.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == --list-models ]] && "
                "printf '%s\\n' 'composer-2.5' 'gpt-5.6-sol-high' && exit 0\n"
                "echo 'fake 1.0'\n",
                encoding="utf-8",
            )
            cursor.chmod(0o755)
            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "auto",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: codex", profile)
            self.assertIn("model: gpt-5.6-luna", profile)
            self.assertIn("reasoning_effort: high", profile)
            self.assertIn("service_tier: fast", profile)
            listed = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            payload = __import__("json").loads(listed.stdout)
            self.assertIn("luna high fast", " ".join(payload["notes"]))


class DoctorTuiCatalogTest(unittest.TestCase):
    def test_grok_46_is_selectable(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        self.assertIn("gemini-3.8-flash-high", tui.WRITER_MODELS["agy"])
        self.assertEqual(tui._efforts_for("agy", "gemini-3.8-flash-high"), ["high"])
        self.assertEqual(tui.DEFAULT_MODEL["cursor"], "cursor-grok-4.6-medium")
        self.assertIn("grok-4.6", tui.WRITER_MODELS["grok"])
        self.assertIn("opencode", tui.ALL_AGENTS)
        self.assertIn("alibaba-token-plan/qwen3.8-max-preview", tui.WRITER_MODELS["opencode"])
        self.assertEqual(tui.sidebar_hit(2), 0)
        self.assertEqual(tui.sidebar_hit(8), 6)
        self.assertEqual(tui.sidebar_hit(9), 7)
        self.assertEqual(tui.sidebar_hit(11), 9)
        self.assertIsNone(tui.sidebar_hit(1))
        self.assertIsNone(tui.sidebar_hit(12))
        self.assertIn("info", tui.TAB_IDS)
        self.assertIn("memory", tui.TAB_IDS)
        self.assertIn("docs", tui.TAB_IDS)
        self.assertNotIn("memory", tui.STAGE_IDS)
        self.assertNotIn("docs", tui.STAGE_IDS)
        self.assertEqual(tui.TAB_IDS[-1], "apply")
        import agents_doctor_tui_i18n as i18n  # noqa: E402

        self.assertEqual(set(i18n.STRINGS["en"]), set(i18n.STRINGS["ru"]))
        self.assertIn("pm_read_h2", i18n.STRINGS["en"])
        self.assertIn("tab_info", i18n.STRINGS["en"])
        self.assertIn("tab_info", i18n.STRINGS["ru"])
        self.assertIn("tab_memory", i18n.STRINGS["ru"])
        self.assertIn("tab_docs", i18n.STRINGS["ru"])
        self.assertIn("Enabled", i18n.STRINGS["en"]["memory_info"])
        self.assertIn("docs-web", i18n.STRINGS["ru"]["docs_info"])
        self.assertIn("/project-onboard", i18n.STRINGS["en"]["info_start"])
        self.assertIn("project-onboard .", i18n.STRINGS["ru"]["info_cmds"])
        self.assertEqual(tui.pick_window(10, 0, 5), (0, 5))
        self.assertEqual(tui.pick_window(10, 9, 5), (5, 10))
        start, end = tui.pick_window(80, 40, 12)
        self.assertLessEqual(end - start, 12)
        self.assertLessEqual(start, 40)
        self.assertGreater(end, 40)
        for slug in (
            "cursor-grok-4.6-low",
            "cursor-grok-4.6-low-fast",
            "cursor-grok-4.6-medium",
            "cursor-grok-4.6-medium-fast",
            "cursor-grok-4.6-high",
            "cursor-grok-4.6-high-fast",
            "cursor-grok-4.6-xhigh",
            "cursor-grok-4.6-xhigh-fast",
        ):
            self.assertIn(slug, tui.CURSOR_MODEL_FALLBACK)

    def test_browser_qa_stage_card_and_i18n(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402
        import agents_doctor_tui_i18n as i18n  # noqa: E402

        # browser_qa is a card on the Stages tab (like plan_critique/specialist/
        # onboard), not its own top-level module tab like memory/docs.
        self.assertIn("browser_qa", tui.STAGE_IDS)
        self.assertNotIn("browser_qa", tui.MODULE_TAB_IDS)
        self.assertNotIn("browser_qa", tui.TAB_IDS)
        self.assertEqual(tui.BROWSER_QA_PROVIDERS, ("jev", "codex", "claude"))
        self.assertEqual(
            tui.BROWSER_QA_BACKENDS, ("live-chrome", "chrome-qa", "headless")
        )
        self.assertEqual(tui.BROWSER_QA_APPROVALS, ("auto", "never"))
        self.assertEqual(
            tui.STAGE_FIELD_BROWSER_QA,
            ("enabled", "provider", "model", "effort", "backend", "approve"),
        )
        for lang in ("en", "ru"):
            self.assertIn("stage_browser_qa", i18n.STRINGS[lang])
            self.assertIn("sfield_backend", i18n.STRINGS[lang])
            self.assertIn("sfield_approve", i18n.STRINGS[lang])
            self.assertIn("browser_qa_hint", i18n.STRINGS[lang])
        self.assertEqual(set(i18n.STRINGS["en"]), set(i18n.STRINGS["ru"]))

    def test_opencode_catalog_refreshes_live(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        fallback = list(tui.WRITER_MODELS["opencode"])
        tui._OPENCODE_LIVE["models"] = ["stale/provider"]
        tui._OPENCODE_LIVE["agents"] = ["stale-agent"]
        tui._OPENCODE_LIVE["stamp"] = None
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "oc.json"
            with patch.dict(
                os.environ, {"LANE_OPENCODE_CATALOG_CACHE": str(cache)}, clear=False
            ), patch.object(
                tui,
                "_fetch_opencode_models",
                return_value=(
                    ["fresh/model"],
                    {"fresh/model": ["none", "low", "xhigh"]},
                ),
            ), patch.object(
                tui, "_fetch_opencode_agents", return_value=["fresh-agent"]
            ):
                tui.refresh_opencode_catalog(force=True)
        self.assertEqual(tui._probe_opencode_models(), ["fresh/model"])
        self.assertEqual(tui._probe_opencode_agents(), ["fresh-agent"])
        self.assertEqual(
            tui._efforts_for("opencode", "fresh/model"),
            ["none", "low", "xhigh"],
        )
        self.assertEqual(tui._efforts_for("opencode", "missing/model"), [])
        self.assertEqual(tui.WRITER_MODELS["opencode"], fallback)
        tui._OPENCODE_LIVE["models"] = None
        tui._OPENCODE_LIVE["agents"] = None
        tui._OPENCODE_LIVE["variants"] = None
        tui._OPENCODE_LIVE["stamp"] = None

    def test_opencode_catalog_disk_cache_skips_fetch(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        tui._OPENCODE_LIVE["models"] = None
        tui._OPENCODE_LIVE["agents"] = None
        tui._OPENCODE_LIVE["variants"] = None
        tui._OPENCODE_LIVE["stamp"] = None
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "oc.json"
            with patch.dict(
                os.environ, {"LANE_OPENCODE_CATALOG_CACHE": str(cache)}, clear=False
            ), patch.object(tui, "_opencode_catalog_stamp", return_value="stamp-a"):
                with patch.object(
                    tui,
                    "_fetch_opencode_models",
                    return_value=(["cached/model"], {"cached/model": ["medium"]}),
                ) as fetch_models, patch.object(
                    tui, "_fetch_opencode_agents", return_value=["lane-writer"]
                ) as fetch_agents:
                    tui.refresh_opencode_catalog()
                    self.assertEqual(fetch_models.call_count, 1)
                    self.assertEqual(fetch_agents.call_count, 1)
                    tui.refresh_opencode_catalog()
                    self.assertEqual(fetch_models.call_count, 1)
                    tui._OPENCODE_LIVE["models"] = None
                    tui._OPENCODE_LIVE["stamp"] = None
                    tui.refresh_opencode_catalog()
                    self.assertEqual(fetch_models.call_count, 1)
                    self.assertEqual(tui._probe_opencode_models(), ["cached/model"])
                    tui.refresh_opencode_catalog(force=True)
                    self.assertEqual(fetch_models.call_count, 2)
        tui._OPENCODE_LIVE["models"] = None
        tui._OPENCODE_LIVE["agents"] = None
        tui._OPENCODE_LIVE["variants"] = None
        tui._OPENCODE_LIVE["stamp"] = None

    def test_parse_opencode_models_verbose_variants(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        text = (
            "prov/has-var\n"
            '{"id":"has-var","providerID":"prov","variants":'
            '{"low":{},"max":{}}}\n'
            "prov/no-var\n"
            '{"id":"no-var","providerID":"prov","variants":{}}\n'
            "prov/happyhorse-1.1-i2v\n"
            '{"id":"happyhorse-1.1-i2v","providerID":"prov","variants":{"low":{}}}\n'
        )
        models, variants = tui.parse_opencode_models_verbose(text)
        self.assertEqual(models, ["prov/has-var", "prov/no-var"])
        self.assertEqual(variants["prov/has-var"], ["low", "max"])
        self.assertEqual(variants["prov/no-var"], [])
        self.assertNotIn("prov/happyhorse-1.1-i2v", models)

    def test_agy_tui_effort_locked_to_model_suffix(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        self.assertEqual(tui._efforts_for("agy", "gemini-3.7-flash-low"), ["low"])
        self.assertEqual(tui._efforts_for("agy", "gemini-3.7-flash-medium"), ["medium"])
        self.assertEqual(tui._efforts_for("agy", "gemini-3.7-flash-high"), ["high"])
        self.assertEqual(tui._ensure_effort("agy", "high", "gemini-3.7-flash-low"), "low")
        self.assertEqual(
            tui._ensure_effort("agy", "low", "gemini-3.7-flash-medium"), "medium"
        )
        self.assertEqual(
            tui._ensure_effort("agy", "medium", "gemini-3.7-flash-high"), "high"
        )
        self.assertEqual(tui._ensure_effort("agy", "low", "claude-sonnet-4-6"), "low")
        self.assertEqual(tui._ensure_effort("agy", "medium", "claude-sonnet-4-6"), "medium")

    def test_harness_opencode_agents_exist(self) -> None:
        root = ROOT / "profiles" / "opencode" / "agents"
        for name in ("lane-writer", "lane-critic", "lane-reviewer"):
            text = (root / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("mode: all", text)
            self.assertIn("task: deny", text)

    def test_migrate_adds_docs_keeps_memory_enabled(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        from pipeline_stages import migrate_profile_stages  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / ".agents" / "routing.profile.yaml"
            profile.parent.mkdir()
            profile.write_text(
                "\n".join(
                    [
                        "lanes:",
                        "  main_write: grok",
                        "writer:",
                        "  provider: grok",
                        "stages:",
                        "  memory:",
                        "    enabled: true",
                        "    provider: codex",
                        "notes:",
                        "  - []",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            added = migrate_profile_stages(profile)
            self.assertIn("docs", added)
            text = profile.read_text(encoding="utf-8")
            self.assertIn("docs:", text)
            self.assertRegex(text, r"(?m)^  memory:\n(?:    .*\n)*    enabled: true")

    def test_migrate_rewrites_legacy_agy_plan_critique(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        from pipeline_stages import migrate_profile_stages  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / ".agents" / "routing.profile.yaml"
            profile.parent.mkdir()
            profile.write_text(
                "\n".join(
                    [
                        "lanes:",
                        "  main_write: kimi",
                        "writer:",
                        "  provider: kimi",
                        "stages:",
                        "  plan_critique:",
                        "    enabled: true",
                        "    mode: advisory",
                        "    provider: agy",
                        "    model: gemini-3.7-flash-high",
                        "    reasoning_effort: high",
                        "  write:",
                        "    provider: kimi",
                        "  night_review:",
                        "    enabled: false",
                        "    provider: qwen",
                        "  specialist:",
                        "    enabled: false",
                        "    provider: codex",
                        "  onboard:",
                        "    provider: codex",
                        "  memory:",
                        "    enabled: false",
                        "    provider: codex",
                        "  docs:",
                        "    enabled: false",
                        "    provider: codex",
                        "  browser_qa:",
                        "    enabled: true",
                        "    provider: codex",
                        "notes:",
                        "  - []",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            changed = migrate_profile_stages(profile)
            self.assertEqual(set(changed), {"plan_critique", "browser_qa"})
            text = profile.read_text(encoding="utf-8")
            self.assertIn("provider: jev", text)
            self.assertIn("typesafe/jev-1.13", text)
            self.assertNotIn("provider: agy", text)
            self.assertRegex(
                text,
                r"(?m)^  browser_qa:\n(?:    .*\n)*    provider: jev\n",
            )

    def test_adoc_prefers_source_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            src = Path(tmp) / "stack" / "bin"
            dest = home / ".agents" / "bin"
            src.mkdir(parents=True)
            dest.mkdir(parents=True)
            (src / "agents-doctor").write_text(
                "#!/usr/bin/env bash\necho SOURCE\n", encoding="utf-8"
            )
            (src / "agents-doctor").chmod(0o755)
            (home / ".agents" / "install.json").write_text(
                '{"source_repo": "%s"}\n' % (src.parent),
                encoding="utf-8",
            )
            adoc = ROOT / "bin" / "adoc"
            env = os.environ.copy()
            env.update(BUBBLEWRAP_ENV)
            env["HOME"] = str(home)
            result = subprocess.run(
                ["bash", str(adoc), "--json", "."],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.stdout.strip(), "SOURCE", result.stderr)


if __name__ == "__main__":
    unittest.main()

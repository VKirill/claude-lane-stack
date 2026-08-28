from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"


class InstallTest(unittest.TestCase):
    def test_pm_boot_prompt_has_no_copyable_session_example(self) -> None:
        for rel in (
            "agents/claude/dev-orchestrator.md",
            "plugins/lane-stack/agents/dev-orchestrator.md",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("blyt-", text, rel)
            self.assertIn("Do **not** invent a", text, rel)

    def test_acceptance_template_includes_report_digest(self) -> None:
        acceptance = json.loads(
            (ROOT / "templates" / "run-contract" / "acceptance-v2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertRegex(acceptance["report_sha256"], r"^[0-9a-f]{64}$")
        schema = json.loads(
            (ROOT / "schemas" / "acceptance-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(acceptance)

    def test_installs_lane_board_and_serves_health_check(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            legacy_nested = home / ".agents" / "codex" / "instructions" / "instructions"
            legacy_nested.mkdir(parents=True)
            (legacy_nested / "reviewer.md").write_text("stale\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".agents" / "board" / "server" / "server.mjs").is_file())
            self.assertFalse(legacy_nested.exists())
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            board_env = env | {"HOST": "127.0.0.1", "PORT": str(port)}
            process = subprocess.Popen(
                [str(home / ".agents" / "bin" / "lane-board")],
                env=board_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.addCleanup(lambda: process.poll() is None and process.kill())
            url = f"http://127.0.0.1:{port}/healthz"
            for _ in range(50):
                try:
                    with urllib.request.urlopen(url, timeout=0.2) as response:
                        payload = json.load(response)
                    break
                except OSError:
                    if process.poll() is not None:
                        self.fail("installed lane-board exited before becoming healthy")
                    time.sleep(0.05)
            else:
                self.fail("installed lane-board did not become healthy")
            self.assertEqual(payload, {"ok": True})
            process.terminate()
            process.wait(timeout=5)

    def test_installs_daytime_controller_and_read_only_run_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            controller = home / ".agents" / "bin" / "run-controller"
            self.assertTrue(controller.is_file())
            self.assertEqual(controller.stat().st_mode & 0o777, 0o755)

            supervisor = home / ".agents" / "agents" / "claude" / "run-supervisor.md"
            content = supervisor.read_text(encoding="utf-8")
            self.assertIn("name: run-supervisor", content)
            self.assertIn("Bash(run-controller start:*)", content)
            self.assertIn("Bash(run-controller watch:*)", content)
            self.assertNotIn("Write", content.partition("---\n")[2].partition("---\n")[0])
            self.assertNotIn("Edit", content.partition("---\n")[2].partition("---\n")[0])
            self.assertFalse((home / ".claude" / "agents" / "run-supervisor.md").exists())

            orchestrator = (
                home / ".agents" / "agents" / "claude" / "dev-orchestrator.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Agent(run-supervisor", orchestrator)
            self.assertIn("no daytime LLM review", orchestrator)
            self.assertNotIn("blyt-", orchestrator)
            self.assertIn("Do **not** invent a", orchestrator)
            self.assertTrue((home / ".agents" / "codex" / "instructions" / "reviewer.md").is_file())
            self.assertFalse((home / ".agents" / "codex" / "instructions" / "instructions").exists())

            marketplace = home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack"
            self.assertFalse(marketplace.exists())
            settings = json.loads(
                (home / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
            ours = settings["extraKnownMarketplaces"]["claude-lane-stack"]
            self.assertEqual(ours["source"]["source"], "github")
            self.assertEqual(ours["source"]["repo"], "VKirill/claude-lane-stack")
            self.assertTrue(ours["autoUpdate"])
            self.assertTrue(settings["enabledPlugins"]["lane-stack@claude-lane-stack"])
            self.assertEqual(settings["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
            self.assertTrue(
                (ROOT / "plugins" / "lane-stack" / ".claude-plugin" / "plugin.json").is_file()
            )

            pm_skill = home / ".agents" / "pm-skills" / "orchestrator-lanes" / "SKILL.md"
            self.assertTrue(pm_skill.is_file())
            self.assertTrue((home / ".agents" / "pm-skills" / "info" / "SKILL.md").is_file())
            self.assertTrue((home / ".agents" / "pm-skills" / "app-architect" / "SKILL.md").is_file())
            self.assertFalse((home / ".agents" / "skills" / "info").exists())
            self.assertFalse((home / ".agents" / "skills" / "app-architect").exists())
            self.assertFalse((home / ".agents" / "skills" / "orchestrator-lanes").exists())
            self.assertFalse((home / ".claude" / "skills" / "orchestrator-lanes").exists())
            self.assertFalse((home / ".claude" / "skills" / "lane-contract").exists())
            self.assertTrue((home / ".agents" / "skills" / "lane-contract" / "SKILL.md").is_file())

    def test_bin_install_ignores_runtime_cache_directories(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            stack = tmp / "stack"
            home = tmp / "home"
            work = tmp / "outside-repo"
            shutil.copytree(
                ROOT,
                stack,
                ignore=shutil.ignore_patterns(
                    ".agents", ".claude-bridge", ".git", "__pycache__", "*.pyc"
                ),
            )
            cache = stack / "bin" / "__pycache__"
            cache.mkdir()
            (cache / "verification_safety.cpython-test.pyc").write_bytes(b"cache")
            (stack / "bin" / "stray.pyc").write_bytes(b"cache")
            hook_cache = stack / "hooks" / "__pycache__"
            hook_cache.mkdir()
            (hook_cache / "guard_shell.cpython-test.pyc").write_bytes(b"cache")
            installed_cache = home / ".agents" / "hooks" / "__pycache__"
            installed_cache.mkdir(parents=True)
            (installed_cache / "stale.pyc").write_bytes(b"cache")
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(stack / "install.sh")],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed_bin = home / ".agents" / "bin"
            self.assertFalse((installed_bin / "__pycache__").exists())
            self.assertFalse((installed_bin / "stray.pyc").exists())
            self.assertFalse((home / ".agents" / "hooks" / "__pycache__").exists())
            self.assertEqual((installed_bin / "lane-ctl").stat().st_mode & 0o777, 0o755)

    def test_install_does_not_chmod_unrelated_existing_bins(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            existing = home / ".agents" / "bin" / "user-managed"
            existing.parent.mkdir(parents=True)
            existing.write_text("#!/bin/sh\n", encoding="utf-8")
            existing.chmod(0o600)
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(existing.stat().st_mode & 0o777, 0o600)

    def test_doctor_apply_requires_explicit_project_option(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            project = tmp / "project"
            home.mkdir()
            project.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=project, check=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            default = subprocess.run(
                [str(INSTALL)],
                cwd=project,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertFalse((project / ".agents" / "routing.profile.yaml").exists())

            explicit = subprocess.run(
                [str(INSTALL), "--apply-project", str(project)],
                cwd=tmp,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertTrue((project / ".agents" / "routing.profile.yaml").is_file())

    def test_install_merges_guard_hook_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            settings = home / ".claude" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                json.dumps(
                    {
                        "theme": "dark",
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Task",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "/user/hook",
                                            "timeout": 7,
                                        }
                                    ],
                                },
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "AGENT_HOOK_CLIENT=claude "
                                                "/old/install/guard_shell.py"
                                            ),
                                            "timeout": 2,
                                        },
                                        {
                                            "type": "command",
                                            "command": "/same-entry/hook",
                                            "timeout": 4,
                                        },
                                    ],
                                },
                                {
                                    "matcher": "Edit|Write|MultiEdit",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "/home/test/.claude/hooks/"
                                                "guard-orchestrator-no-direct-edits.sh"
                                            ),
                                            "timeout": 2,
                                        }
                                    ],
                                },
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            for _ in range(2):
                result = subprocess.run(
                    [str(INSTALL)],
                    cwd=work,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            installed = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(installed["theme"], "dark")
            self.assertEqual(installed["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
            entries = installed["hooks"]["PreToolUse"]
            self.assertIn(
                {
                    "matcher": "Task",
                    "hooks": [
                        {"type": "command", "command": "/user/hook", "timeout": 7}
                    ],
                },
                entries,
            )
            guards = [
                entry
                for entry in entries
                if any(
                    hook.get("command", "").endswith("/guard_shell.py")
                    for hook in entry.get("hooks", [])
                )
            ]
            self.assertEqual(len(guards), 1)
            self.assertEqual(
                guards[0]["matcher"],
                "Bash|Edit|Write|MultiEdit|NotebookEdit",
            )
            self.assertNotIn(
                "guard-orchestrator-no-direct-edits.sh",
                settings.read_text(encoding="utf-8"),
            )
            self.assertIn(
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/same-entry/hook",
                            "timeout": 4,
                        }
                    ],
                },
                entries,
            )

    def test_install_fails_fast_when_node_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            fake_path = tmp / "bin"
            fake_path.mkdir()
            for command in ("bash", "dirname", "flock", "git", "python3", "rsync"):
                target = shutil.which(command)
                self.assertIsNotNone(target)
                (fake_path / command).symlink_to(target)
            env = os.environ.copy()
            env["PATH"] = str(fake_path)

            result = subprocess.run(
                [str(INSTALL)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required command: node", result.stderr)

    def test_removes_stack_skills_from_claude_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            existing = home / ".claude" / "skills" / "lane-contract"
            existing.mkdir(parents=True)
            work.mkdir()
            (existing / "user-note.txt").write_text("stale catalog copy\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(existing.exists())
            self.assertTrue(
                (home / ".agents" / "skills" / "lane-contract" / "SKILL.md").is_file()
            )
            self.assertFalse(
                (home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack").exists()
            )

    def test_local_marketplace_keeps_checkout_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env["LANE_INSTALL_LOCAL_MARKETPLACE"] = "1"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            marketplace = home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack"
            self.assertTrue(marketplace.is_symlink())
            self.assertEqual(marketplace.resolve(), ROOT)
            settings = json.loads(
                (home / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
            ours = settings["extraKnownMarketplaces"]["claude-lane-stack"]
            self.assertEqual(ours["source"]["path"], str(ROOT))
            self.assertNotIn("autoUpdate", ours)

    def test_installs_dedicated_codex_night_review_profile(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = home / ".codex" / "night-review.config.toml"
            self.assertTrue(installed.is_file())
            content = installed.read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.6-sol"', content)
            self.assertIn('model_reasoning_effort = "high"', content)
            self.assertIn('sandbox_mode = "read-only"', content)
            self.assertIn('approval_policy = "never"', content)


if __name__ == "__main__":
    unittest.main()

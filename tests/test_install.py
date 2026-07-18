from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"


class InstallTest(unittest.TestCase):
    def test_installs_daytime_controller_and_read_only_run_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
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

            supervisor = home / ".claude" / "agents" / "run-supervisor.md"
            content = supervisor.read_text(encoding="utf-8")
            self.assertIn("name: run-supervisor", content)
            self.assertIn("Bash(run-controller start:*)", content)
            self.assertIn("Bash(run-controller watch:*)", content)
            self.assertNotIn("Write", content.partition("---\n")[2].partition("---\n")[0])
            self.assertNotIn("Edit", content.partition("---\n")[2].partition("---\n")[0])

            orchestrator = (home / ".claude" / "agents" / "dev-orchestrator.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Agent(run-supervisor", orchestrator)
            self.assertIn("no daytime LLM review", orchestrator)

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
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
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
            self.assertEqual((installed_bin / "lane-ctl").stat().st_mode & 0o777, 0o755)

    def test_syncs_existing_claude_skill_directory_without_nested_link(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            existing = home / ".claude" / "skills" / "lane-contract"
            existing.mkdir(parents=True)
            work.mkdir()
            sentinel = existing / "user-note.txt"
            sentinel.write_text("preserve me\n", encoding="utf-8")
            nested = existing / "lane-contract"
            nested.symlink_to(home / ".agents" / "skills" / "lane-contract")
            env = os.environ.copy()
            env["HOME"] = str(home)
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
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse(nested.exists())
            self.assertFalse(nested.is_symlink())
            self.assertEqual(
                (existing / "SKILL.md").read_bytes(),
                (ROOT / "skills" / "lane-contract" / "SKILL.md").read_bytes(),
            )

    def test_installs_dedicated_codex_night_review_profile(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
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
            self.assertIn('model_reasoning_effort = "xhigh"', content)
            self.assertIn('sandbox_mode = "read-only"', content)
            self.assertIn('approval_policy = "never"', content)


if __name__ == "__main__":
    unittest.main()

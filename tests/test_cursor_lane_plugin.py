from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "profiles" / "cursor" / "lane-writer"
BEFORE_SHELL = PLUGIN / "scripts" / "before_shell.py"
BEFORE_READ = PLUGIN / "scripts" / "before_read.py"
sys.path.insert(0, str(ROOT / "bin"))

from jev_read import decide_read, packet_paths  # noqa: E402


def _choice(value: str, confidence: float = 0.9) -> dict:
    return {"type": "choice", "choice": value, "confidence": confidence}


class CursorLanePluginTest(unittest.TestCase):
    def test_manifest_and_mcp_are_isolated(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "lane-writer")
        mcp = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(set(mcp["mcpServers"]), {"gitnexus", "agentmemory"})
        self.assertTrue((PLUGIN / "agents" / "lane-writer.md").is_file())
        self.assertTrue((PLUGIN / "rules" / "lane-writer.mdc").is_file())
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("beforeReadFile", hooks["hooks"])

    def test_before_shell_denies_tests_only_on_lane(self) -> None:
        payload = json.dumps({"command": "npm run typecheck"}).encode()
        env = os.environ.copy()
        env.pop("LANE_TASK_FILE", None)
        idle = subprocess.run(
            [sys.executable, str(BEFORE_SHELL)],
            input=payload,
            capture_output=True,
            env=env,
            check=True,
        )
        self.assertEqual(json.loads(idle.stdout)["permission"], "allow")
        env["LANE_TASK_FILE"] = "/tmp/task.yaml"
        blocked = subprocess.run(
            [sys.executable, str(BEFORE_SHELL)],
            input=payload,
            capture_output=True,
            env=env,
            check=True,
        )
        self.assertEqual(json.loads(blocked.stdout)["permission"], "deny")


class JevReadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        self.owned = self.root / "src" / "owned.vue"
        self.owned.write_text("<template></template>\n", encoding="utf-8")
        self.extra = self.root / "src" / "unrelated.ts"
        self.extra.write_text("export const x = 1\n", encoding="utf-8")
        self.task = self.root / "task.yaml"
        self.task.write_text(
            "\n".join(
                [
                    "title: demo",
                    "objective: wire the owned component",
                    "owns_paths:",
                    "  - src/owned.vue",
                    "read_first:",
                    "  - src/owned.vue",
                    "never_touch:",
                    "  - src/secrets.ts",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.prompt = self.root / "prompt.md"
        self.prompt.write_text("x\n", encoding="utf-8")
        self.env = {
            "LANE_TASK_FILE": str(self.task),
            "LANE_PROMPT_FILE": str(self.prompt),
            "LANE_JEV_READ": "1",
        }

    def _decide(self, path: Path):
        payload = {"file_path": str(path), "content": path.read_text(encoding="utf-8")}
        with patch.dict(os.environ, self.env, clear=False):
            return decide_read(payload, cwd=self.root)

    def test_packet_paths_from_yaml(self) -> None:
        self.assertEqual(packet_paths({"read_first": ["src/a.ts"], "owns_paths": ["src/*.vue"]}), {"src/a.ts"})

    def test_idle_without_task_allows(self) -> None:
        with patch.dict(os.environ, {"LANE_TASK_FILE": ""}, clear=False):
            self.assertEqual(
                decide_read({"file_path": str(self.extra)}, cwd=self.root)["permission"],
                "allow",
            )

    def test_packet_first_read_allows_without_jev(self) -> None:
        with patch("jev_read.call_jev") as mocked:
            result = self._decide(self.owned)
        self.assertEqual(result["permission"], "allow")
        mocked.assert_not_called()

    def test_packet_reread_denies(self) -> None:
        with patch("jev_read.call_jev"):
            self.assertEqual(self._decide(self.owned)["permission"], "allow")
            again = self._decide(self.owned)
        self.assertEqual(again["permission"], "deny")
        self.assertIn("Already read", again["user_message"])

    def test_never_touch_denies(self) -> None:
        secret = self.root / "src" / "secrets.ts"
        secret.write_text("nope\n", encoding="utf-8")
        with patch("jev_read.call_jev") as mocked:
            result = self._decide(secret)
        self.assertEqual(result["permission"], "deny")
        mocked.assert_not_called()

    def test_extra_skip_from_jev(self) -> None:
        with patch("jev_read.jev_enabled", return_value=True), patch(
            "jev_read.call_jev",
            return_value={"answers": {"need": _choice("skip")}},
        ) as mocked:
            result = self._decide(self.extra)
        self.assertEqual(result["permission"], "deny")
        self.assertIn("outside the execution packet", result["user_message"])
        mocked.assert_called_once()

    def test_extra_needed_allows(self) -> None:
        with patch("jev_read.jev_enabled", return_value=True), patch(
            "jev_read.call_jev",
            return_value={"answers": {"need": _choice("needed")}},
        ):
            self.assertEqual(self._decide(self.extra)["permission"], "allow")

    def test_extra_fail_open_without_jev(self) -> None:
        with patch("jev_read.jev_enabled", return_value=False), patch("jev_read.call_jev") as mocked:
            self.assertEqual(self._decide(self.extra)["permission"], "allow")
        mocked.assert_not_called()

    def test_low_confidence_skip_allows(self) -> None:
        with patch("jev_read.jev_enabled", return_value=True), patch(
            "jev_read.call_jev",
            return_value={"answers": {"need": _choice("skip", 0.2)}},
        ):
            self.assertEqual(self._decide(self.extra)["permission"], "allow")

    def test_flag_off_skips_jev(self) -> None:
        self.env["LANE_JEV_READ"] = "0"
        with patch("jev_read.jev_enabled", return_value=True), patch("jev_read.call_jev") as mocked:
            self.assertEqual(self._decide(self.extra)["permission"], "allow")
        mocked.assert_not_called()

    def test_hook_script_fail_open_and_deny_reread(self) -> None:
        env = os.environ.copy()
        env.update(self.env)
        env["LANE_STACK_ROOT"] = str(ROOT)
        payload = json.dumps({"file_path": str(self.owned), "content": "x"}).encode()
        first = subprocess.run(
            [sys.executable, str(BEFORE_READ)],
            input=payload,
            capture_output=True,
            env=env,
            cwd=str(self.root),
            check=True,
        )
        self.assertEqual(json.loads(first.stdout)["permission"], "allow")
        second = subprocess.run(
            [sys.executable, str(BEFORE_READ)],
            input=payload,
            capture_output=True,
            env=env,
            cwd=str(self.root),
            check=True,
        )
        self.assertEqual(json.loads(second.stdout)["permission"], "deny")

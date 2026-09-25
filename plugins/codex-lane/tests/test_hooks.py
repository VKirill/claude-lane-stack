from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = PLUGIN_ROOT / "hooks" / "user-prompt-submit.py"
SESSION_PATH = PLUGIN_ROOT / "hooks" / "session-start.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prompt_hook = load_module(HOOK_PATH, "codex_lane_prompt_hook")
session_hook = load_module(SESSION_PATH, "codex_lane_session_hook")


class HookTests(unittest.TestCase):
    def test_session_start_marks_main_and_worker(self) -> None:
        for marker, expected in (
            (None, "Codex Lane active"),
            ("1", "Codex Lane worker mode"),
        ):
            output = io.StringIO()
            with patch.dict(os.environ, {}, clear=True):
                if marker:
                    os.environ["LANE_CODEX_WORKER"] = marker
                with patch("sys.stdout", output):
                    self.assertEqual(session_hook.main(), 0)
            self.assertIn(expected, output.getvalue())

    def test_prompt_hook_skips_worker_and_fails_open_on_timeout(self) -> None:
        with patch.dict(os.environ, {"LANE_CODEX_WORKER": "1"}, clear=True), patch.object(
            prompt_hook.subprocess, "run"
        ) as run:
            self.assertEqual(prompt_hook.main(), 0)
            run.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / ".agents" / "hooks" / "skill_hint.py"
            hook.parent.mkdir(parents=True)
            hook.write_text("", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.object(
                prompt_hook.Path, "home", return_value=Path(tmp)
            ), patch.object(
                prompt_hook.subprocess,
                "run",
                side_effect=prompt_hook.subprocess.TimeoutExpired("skill_hint", 3),
            ) as run:
                with patch("sys.stdin", io.StringIO("{}")):
                    self.assertEqual(prompt_hook.main(), 0)
            self.assertEqual(run.call_args.kwargs["timeout"], 3)

    def test_prompt_hook_forwards_hints_and_suppresses_blocked_catalog_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / ".agents" / "hooks" / "skill_hint.py"
            hook.parent.mkdir(parents=True)
            hook.write_text("", encoding="utf-8")
            for stdout, expected in (
                ("hint", "hint"),
                ("[lane-stack skill] orchestrator-workflow", ""),
            ):
                output = io.StringIO()
                with patch.dict(os.environ, {}, clear=True), patch.object(
                    prompt_hook.Path, "home", return_value=Path(tmp)
                ), patch.object(
                    prompt_hook.subprocess,
                    "run",
                    return_value=SimpleNamespace(stdout=stdout),
                ), patch("sys.stdin", io.StringIO("{}")), patch("sys.stdout", output):
                    self.assertEqual(prompt_hook.main(), 0)
                self.assertEqual(output.getvalue(), expected)


if __name__ == "__main__":
    unittest.main()

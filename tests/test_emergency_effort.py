from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_decisions import JevCritiqueError  # noqa: E402
from jev_slots import classify_emergency_effort  # noqa: E402


def _choice(value: str, confidence: float = 0.8) -> dict:
    return {"type": "choice", "choice": value, "confidence": confidence}


class EmergencyEffortTest(unittest.TestCase):
    def test_jev_selects_each_supported_effort(self) -> None:
        for expected in ("medium", "high", "xhigh"):
            with self.subTest(expected=expected), patch(
                "jev_slots.call_jev",
                return_value={"answers": {"effort": _choice(expected)}},
            ) as call:
                route = classify_emergency_effort("Scope: bin/x.py", "high")
            self.assertEqual(route["chosen_effort"], expected)
            self.assertEqual(route["source"], "jev")
            self.assertEqual(route["fallback_reason"], None)
            self.assertEqual(call.call_args.kwargs["timeout"], 3)

    def test_missing_key_timeout_and_invalid_response_preserve_xhigh(self) -> None:
        errors = (
            (JevCritiqueError("Jev disabled or API key missing"), "missing_api_key"),
            (TimeoutError("timeout"), "request_failed"),
        )
        for response, reason in errors:
            with self.subTest(reason=reason), patch(
                "jev_slots.call_jev", side_effect=response
            ):
                route = classify_emergency_effort("Actual task scope", "xhigh")
            self.assertEqual(route["chosen_effort"], "xhigh")
            self.assertEqual(route["configured_effort"], "xhigh")
            self.assertEqual(route["source"], "configured")
            self.assertEqual(route["fallback_reason"], reason)
            self.assertEqual(route["confidence"], 0.0)
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"effort": _choice("max")}},
        ):
            route = classify_emergency_effort("Actual task scope", "xhigh")
        self.assertEqual(route["chosen_effort"], "xhigh")
        self.assertEqual(route["fallback_reason"], "invalid_response")

    def test_missing_keys_fail_before_network(self) -> None:
        with patch.dict(os.environ, {"LANE_JEV": "1"}), patch(
            "jev_decisions.typesafe_key", return_value=""
        ), patch("jev_decisions.openrouter_key", return_value=""), patch(
            "jev_decisions.urllib.request.urlopen"
        ) as urlopen:
            route = classify_emergency_effort("Actual task scope", "xhigh")
        self.assertEqual(route["fallback_reason"], "missing_api_key")
        urlopen.assert_not_called()

    def test_emergency_runtime_forces_fast_and_keeps_model(self) -> None:
        module = runpy.run_path(str(ROOT / "bin/lane-session"), run_name="lane_session_test")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".agents" / "runs" / "one"
            run_dir.mkdir(parents=True)
            cwd = root / "worktree"
            cwd.mkdir()
            prompt = cwd / "task.md"
            prompt.write_text("Scope: bin/lane-session and tests\n", encoding="utf-8")
            output = root / "artifacts" / "lane.log"
            lease = module["Lease"](
                "codex:emergency-writer:0",
                0,
                types.SimpleNamespace(),
                {"session_id": None},
                True,
            )
            args = argparse.Namespace(
                provider="codex",
                role="emergency-writer",
                run_dir=run_dir,
                cwd=cwd,
                task_id="task-1",
                prompt_file=prompt,
                output=output,
                model="gpt-6-luna-custom",
                reasoning_effort="high",
                service_tier="standard",
                fast_mode=False,
                binary=sys.executable,
                pool_size=1,
                max_tasks=1,
            )
            captured: list[list[str]] = []
            lane_globals = module["run_provider"].__globals__

            def sandbox(command, **_kwargs):
                captured.append(command)
                return command

            replacements = {
                "acquire_lease": lambda **_kwargs: lease,
                "provider_input": lambda *_args, **_kwargs: None,
                "prepare_codex_home": lambda *_args, **_kwargs: None,
                "provider_environment": lambda *_args, **_kwargs: {},
                "sandbox_provider_command": sandbox,
                "provider_version": lambda *_args, **_kwargs: None,
                "stream_provider": lambda *_args, **_kwargs: types.SimpleNamespace(
                    exit_code=0, session_id=None
                ),
                "finish_lease": lambda **_kwargs: {"status": "idle", "success_count": 1},
                "write_runtime_receipt": lambda **_kwargs: None,
                "unlock_file": lambda *_args, **_kwargs: None,
            }
            with patch("jev_slots.call_jev", return_value={"answers": {"effort": _choice("xhigh", 0.91)}}), patch.dict(lane_globals, replacements), patch.object(module["subprocess"], "run", return_value=types.SimpleNamespace(stdout=b"", returncode=0)), patch.object(module["subprocess"], "Popen", return_value=object()):
                self.assertEqual(module["run_provider"](args), 0)

            command = captured[0]
            self.assertEqual(command[command.index("--model") + 1], "gpt-6-luna-custom")
            self.assertIn('model_reasoning_effort="xhigh"', command)
            self.assertIn('service_tier="fast"', command)
            self.assertIn("--enable", command)
            self.assertEqual(command[command.index("--enable") + 1], "fast_mode")
            route = json.loads((output.parent / "effort-route.json").read_text())
            self.assertEqual(route["chosen_effort"], "xhigh")
            self.assertEqual(route["configured_effort"], "high")
            self.assertEqual(route["source"], "jev")

    def test_normal_writer_does_not_route_or_force_fast(self) -> None:
        module = runpy.run_path(str(ROOT / "bin/lane-session"), run_name="lane_session_test")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / ".agents" / "runs" / "one"
            run_dir.mkdir(parents=True)
            cwd = root / "worktree"
            cwd.mkdir()
            prompt = cwd / "task.md"
            prompt.write_text("ordinary task\n", encoding="utf-8")
            output = root / "artifacts" / "lane.log"
            lease = module["Lease"]("codex:lane-writer:0", 0, types.SimpleNamespace(), {"session_id": None}, True)
            args = argparse.Namespace(
                provider="codex", role="lane-writer", run_dir=run_dir, cwd=cwd,
                task_id="task-1", prompt_file=prompt, output=output,
                model="gpt-6-luna", reasoning_effort="high", service_tier="standard",
                fast_mode=False, binary=sys.executable, pool_size=1, max_tasks=1,
            )
            captured: list[list[str]] = []
            lane_globals = module["run_provider"].__globals__

            def sandbox(command, **_kwargs):
                captured.append(command)
                return command

            replacements = {
                "acquire_lease": lambda **_kwargs: lease,
                "provider_input": lambda *_args, **_kwargs: None,
                "prepare_codex_home": lambda *_args, **_kwargs: None,
                "provider_environment": lambda *_args, **_kwargs: {},
                "sandbox_provider_command": sandbox,
                "provider_version": lambda *_args, **_kwargs: None,
                "stream_provider": lambda *_args, **_kwargs: types.SimpleNamespace(exit_code=0, session_id=None),
                "finish_lease": lambda **_kwargs: {"status": "idle", "success_count": 1},
                "write_runtime_receipt": lambda **_kwargs: None,
                "unlock_file": lambda *_args, **_kwargs: None,
            }
            with patch("jev_slots.call_jev", side_effect=AssertionError("normal writer routed")), patch.dict(lane_globals, replacements), patch.object(module["subprocess"], "run", return_value=types.SimpleNamespace(stdout=b"", returncode=0)), patch.object(module["subprocess"], "Popen", return_value=object()):
                self.assertEqual(module["run_provider"](args), 0)

            command = captured[0]
            self.assertIn('model_reasoning_effort="high"', command)
            self.assertIn("--disable", command)
            self.assertNotIn('service_tier="fast"', command)
            self.assertFalse((output.parent / "effort-route.json").exists())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
RUNNER = ROOT / "bin" / "browser-qa-jev"

from browser_qa_jev import expected_hit, format_elements, decide, run_case, snapshot  # noqa: E402
from pipeline_stages import normalize_stages  # noqa: E402


class BrowserQaJevTest(unittest.TestCase):
    def test_expected_hit(self) -> None:
        self.assertTrue(expected_hit("page shows 11 leftover", "Page shows 11"))
        self.assertTrue(expected_hit("anything", "as written"))
        self.assertFalse(expected_hit("empty cart", "Checkout total 4900"))

    def test_format_elements_skips_scroll(self) -> None:
        rows = format_elements(
            [
                {"id": "e1", "kind": "click", "role": "button", "label": "Pay", "value": ""},
                {"id": "scroll_down", "kind": "scroll", "label": "Scroll down"},
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "e1")

    def test_format_elements_keeps_all_action_text(self) -> None:
        rows = format_elements(
            [
                {"id": f"e{index}", "kind": "click", "role": "button", "label": "L" * 120}
                for index in range(81)
            ]
        )
        self.assertEqual(len(rows), 81)
        self.assertEqual(len(rows[-1]["label"]), 120)

    def test_snapshot_keeps_all_actions(self) -> None:
        raw = {"url": "http://x/", "title": "X", "text": "text", "actions": [
            {"id": f"e{index}", "kind": "click"} for index in range(81)
        ]}

        class Dummy:
            def evaluate(self, _expression):
                return raw

        self.assertEqual(len(snapshot(Dummy())["actions"]), 81)

    def test_decide_click(self) -> None:
        page = {
            "url": "http://x/",
            "title": "X",
            "text": "Pay",
            "actions": [
                {"id": "e1", "kind": "click", "role": "button", "label": "Pay", "node": 1}
            ],
        }
        fake = {
            "answers": {
                "operation": {"choice": "CLICK", "confidence": 0.8},
                "click_target": {"choice": "e1", "confidence": 0.7},
            }
        }
        with patch("browser_qa_jev.call_jev", return_value=fake) as call:
            out = decide(
                page,
                "Click " + ("goal " * 300),
                ["history " * 300],
                expected="expected " * 300,
            )
        self.assertEqual(out["operation"], "CLICK")
        self.assertEqual(out["target"], "e1")
        state = call.call_args.args[0]
        self.assertTrue(state["goal"].endswith("goal "))
        self.assertTrue(state["expected"].endswith("expected "))
        self.assertEqual(len(state["recent"]), 1)

    def test_run_case_done_checks_expected(self) -> None:
        page = {
            "url": "http://x/",
            "title": "X",
            "text": "Page shows 11 leftover",
            "actions": [],
        }
        fake = {"answers": {"operation": {"choice": "DONE", "confidence": 0.9}}}

        class Dummy:
            pass

        with (
            patch("browser_qa_jev.snapshot", return_value=page),
            patch("browser_qa_jev.call_jev", return_value=fake),
        ):
            out = run_case(Dummy(), goal="Page shows 11", expected="Page shows 11")
        self.assertEqual(out["status"], "passed")

    def test_default_stage_is_jev(self) -> None:
        s = normalize_stages(None)
        self.assertEqual(s["browser_qa"]["provider"], "jev")
        self.assertEqual(s["browser_qa"]["backend"], "chrome-qa")

    def test_cli_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".agents").mkdir()
            env = os.environ.copy()
            env["LANE_JEV"] = "0"
            result = subprocess.run(
                [
                    str(RUNNER),
                    "--project-cwd",
                    str(project),
                    "--url",
                    "http://127.0.0.1:9/",
                    "--slug",
                    "demo",
                    "--case",
                    "Page shows 11",
                    "--dry-run",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["provider"], "jev")
            self.assertTrue((project / ".agents/qa/demo/cases.md").is_file())


if __name__ == "__main__":
    unittest.main()

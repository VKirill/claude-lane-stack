from __future__ import annotations

import json
import os
import runpy
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "bin" / "lane-benchmark"


FAKE_PROVIDER = r'''#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

args = sys.argv[1:]
if "--version" in args:
    print("fake-provider 1.0")
    raise SystemExit(0)

if "timeout" in Path(__file__).name:
    time.sleep(30)

if "--workspace" in args:
    writer = Path(args[args.index("--workspace") + 1])
    cursor = True
else:
    writer = Path(args[args.index("--dir") + 1])
    cursor = False

if "scope" in Path(__file__).name:
    pricing = writer / "pricing.py"
    pricing.write_text(pricing.read_text(encoding="utf-8") + "\n# unauthorized benchmark mutation\n", encoding="utf-8")

(writer / "invoice.py").write_text(
    "from pricing import PricingBlock\n\n\n"
    "def copy_for_invoice(block: PricingBlock) -> PricingBlock:\n"
    "    return PricingBlock(formal=block.formal, default=block.default)\n",
    encoding="utf-8",
)
(writer / "quote.py").write_text(
    "from pricing import PricingBlock\n\n\n"
    "def copy_for_quote(block: PricingBlock) -> PricingBlock:\n"
    "    return PricingBlock(formal=block.formal, default=block.default)\n",
    encoding="utf-8",
)
report = "<<<LANE_REPORT:BEGIN>>>\nSTATUS: complete\nfixture fixed\n<<<LANE_REPORT:END>>>"
if cursor:
    events = [
        {"type": "system", "subtype": "init", "session_id": "fake-cursor"},
        {"type": "tool_call", "subtype": "started", "tool_call": {"toolCallId": "call-0"}},
        {"type": "tool_call", "subtype": "completed", "tool_call": {
            "toolCallId": "call-1", "readToolCall": {
                "args": {"path": "invoice.py"}, "result": {"content": "ok", "duration": 1}
            }
        }},
        {"type": "tool_call", "subtype": "completed", "tool_call": {
            "toolCallId": "call-1", "readToolCall": {
                "args": {"path": "invoice.py"}, "result": {"content": "ok", "duration": 2}
            }
        }},
        {"type": "tool_call", "subtype": "completed", "tool_call": {
            "toolCallId": "call-2", "readToolCall": {
                "args": {"path": "invoice.py"}, "result": {"content": "ok", "duration": 3}
            }
        }},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": report}]}},
        {"type": "result", "subtype": "success", "session_id": "fake-cursor", "result": report},
    ]
else:
    events = [
        {"type": "step_start", "part": {}},
        {"type": "tool_use", "part": {
            "callID": "call-1", "tool": "read", "state": {
                "status": "completed", "input": {"path": "invoice.py"}, "output": "ok"
            }
        }},
        {"type": "tool_use", "part": {
            "callID": "call-1", "tool": "read", "state": {
                "status": "completed", "input": {"path": "invoice.py"}, "output": "ok"
            }
        }},
        {"type": "tool_use", "part": {
            "callID": "call-2", "tool": "read", "state": {
                "status": "completed", "input": {"path": "invoice.py"}, "output": "ok"
            }
        }},
        {"type": "text", "part": {"text": report}},
        {"type": "step_finish", "part": {"reason": "stop"}},
    ]
for event in events:
    print(json.dumps(event), flush=True)
'''


class LaneBenchmarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fake = self.root / "fake-provider"
        self.fake.write_text(textwrap.dedent(FAKE_PROVIDER), encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)

    def _run(self, *extra: str, binary: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("JEV_API_KEY", None)
        env.pop("LANE_JEV_EFFORT", None)
        return subprocess.run(
            [
                sys.executable,
                str(BENCHMARK),
                "--output-dir",
                str(self.root / "out"),
                "--cursor-binary",
                str(binary or self.fake),
                "--opencode-binary",
                str(binary or self.fake),
                *extra,
            ],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_dry_run_is_default_and_pins_both_models_and_effort(self) -> None:
        result = subprocess.run(
            [sys.executable, str(BENCHMARK)],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        )
        config = json.loads(result.stdout)
        self.assertEqual(config["mode"], "dry-run")
        self.assertEqual(config["effort"], "medium")
        self.assertEqual(
            [(arm["provider"], arm["resolved_model"]) for arm in config["arms"]],
            [
                ("cursor", "grok-4.7-medium"),
                ("opencode", "cursor-acp/grok-4.7-medium"),
            ],
        )
        self.assertFalse((self.root / "out").exists())

    def test_run_records_acceptance_first_edit_raw_logs_and_repeats(self) -> None:
        result = self._run("--run", "--repeat", "2", "--timeout", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.root / "out" / "metrics.json").read_text())
        self.assertEqual(len(report["runs"]), 4)
        self.assertTrue(all(run["outcome"] == "accepted" for run in report["runs"]))
        for run in report["runs"]:
            self.assertEqual(run["reasoning_effort"], "medium")
            self.assertEqual(run["jev_effort"], "0")
            self.assertIsNotNone(run["metrics"]["first_correct_edit_elapsed_seconds"])
            self.assertGreater(run["metrics"]["total_elapsed_seconds"], 0)
            self.assertEqual(run["metrics"]["test_outcome"], "passed")
            self.assertTrue(run["metrics"]["checker_unchanged"])
            checker = Path(run["paths"]["acceptance_checker"])
            writer = Path(run["paths"]["writer"])
            self.assertNotEqual(checker.parent, writer)
            task_file = Path(run["paths"]["task_file"])
            task = json.loads(task_file.read_text())
            self.assertEqual(task["owns_paths"], ["invoice.py", "quote.py"])
            prompt = Path(run["paths"]["prompt"]).read_text()
            self.assertIn("--- RAW TASK YAML (verbatim) ---", prompt)
            self.assertIn("<<<LANE_EXECUTION_PACKET_JSON:BEGIN>>>", prompt)
            lane_session = runpy.run_path(str(ROOT / "bin" / "lane-session"))
            env: dict[str, str] = {}
            lane_session["attach_lane_contract_env"](
                env,
                prompt_file=Path(run["paths"]["prompt"]),
                run_dir=task_file.parent.parent,
                task_id="pricing-block-copy",
            )
            self.assertEqual(env["LANE_TASK_FILE"], str(task_file.resolve()))
            self.assertEqual(run["metrics"]["repeated_toolresults"], 1)
            self.assertGreaterEqual(run["metrics"]["toolresult_events"], 2)
            for path in run["paths"].values():
                self.assertTrue(Path(path).exists(), path)
            raw = Path(run["paths"]["provider_raw_stdout"]).read_text()
            self.assertIn('"type": "result"', raw) if run["provider"] == "cursor" else self.assertIn('"type": "tool_use"', raw)

    def test_timeout_is_reported_and_stays_time_bounded(self) -> None:
        timeout_fake = self.root / "fake-timeout-provider"
        timeout_fake.write_text(textwrap.dedent(FAKE_PROVIDER), encoding="utf-8")
        timeout_fake.chmod(timeout_fake.stat().st_mode | stat.S_IXUSR)
        started = __import__("time").monotonic()
        result = subprocess.run(
            [
                sys.executable,
                str(BENCHMARK),
                "--run",
                "--timeout",
                "0.2",
                "--output-dir",
                str(self.root / "timeout-out"),
                "--cursor-binary",
                str(timeout_fake),
                "--opencode-binary",
                str(timeout_fake),
            ],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        elapsed = __import__("time").monotonic() - started
        self.assertEqual(result.returncode, 1)
        self.assertLess(elapsed, 8)
        report = json.loads((self.root / "timeout-out" / "metrics.json").read_text())
        self.assertEqual([run["outcome"] for run in report["runs"]], ["timeout", "timeout"])
        self.assertTrue(all(run["timed_out"] for run in report["runs"]))
        self.assertTrue(all(run["metrics"]["first_correct_edit_elapsed_seconds"] is None for run in report["runs"]))

    def test_scope_violation_cannot_be_accepted(self) -> None:
        scope_fake = self.root / "fake-scope-provider"
        scope_fake.write_text(textwrap.dedent(FAKE_PROVIDER), encoding="utf-8")
        scope_fake.chmod(scope_fake.stat().st_mode | stat.S_IXUSR)
        result = self._run("--run", "--timeout", "5", binary=scope_fake)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads((self.root / "out" / "metrics.json").read_text())
        self.assertTrue(all(run["outcome"] == "scope_violation" for run in report["runs"]))
        self.assertTrue(all(not run["metrics"]["scope_unchanged"] for run in report["runs"]))
        self.assertTrue(all(run["metrics"]["first_correct_edit_elapsed_seconds"] is None for run in report["runs"]))


if __name__ == "__main__":
    unittest.main()

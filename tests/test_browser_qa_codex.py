import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "bin" / "browser-qa-codex"


class BrowserQaCodexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        (self.project / ".agents").mkdir(parents=True)
        # Fake codex: records argv, writes REPORT.md and the structured last message.
        self.fake = self.root / "fake-codex"
        self.fake.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json, os, sys
                from pathlib import Path
                args = sys.argv[1:]
                Path(os.environ["FAKE_CODEX_LOG"]).write_text(json.dumps(args))
                out = Path(args[args.index("-o") + 1])
                cwd = Path(args[args.index("-C") + 1])
                prompt = args[-1]
                qa_rel = [w for w in prompt.split() if w.startswith(".agents/qa/")][0].rstrip("/,")
                qa_rel = qa_rel.split("/cases.md")[0]
                (cwd / qa_rel).mkdir(parents=True, exist_ok=True)
                (cwd / qa_rel / "REPORT.md").write_text("# QA fake\\n")
                verdict = os.environ.get("FAKE_VERDICT", "pass")
                out.write_text(json.dumps({"backend": "chrome-extension", "verdict": verdict,
                    "cases": [{"id": "TC-001", "status": "passed" if verdict == "pass" else "failed", "evidence": "11"}]}))
                """
            ),
            encoding="utf-8",
        )
        self.fake.chmod(0o755)
        self.log = self.root / "argv.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_runner(self, *extra: str, verdict: str = "pass") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["FAKE_CODEX_LOG"] = str(self.log)
        env["FAKE_VERDICT"] = verdict
        return subprocess.run(
            [str(RUNNER), "--project-cwd", str(self.project), "--url", "http://127.0.0.1:8791/",
             "--slug", "demo", "--codex-bin", str(self.fake), *extra],
            env=env, text=True, capture_output=True, check=False,
        )

    def test_defaults_are_codex_astra_low_live_chrome(self) -> None:
        result = self.run_runner("--case", "Page shows 11")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        argv = json.loads(self.log.read_text())
        self.assertEqual(argv[0], "exec")
        self.assertIn("--json", argv)
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6-astra")
        self.assertIn("model_reasoning_effort=low", argv)
        self.assertIn("--approve-for-me", argv)
        self.assertIn("--output-schema", argv)
        receipt = json.loads((self.project / ".agents/qa/demo/codex-run.json").read_text())
        self.assertEqual(receipt["verdict"], "pass")
        self.assertEqual(receipt["backend"], "live-chrome")
        self.assertTrue((self.project / ".agents/qa/demo/cases.md").is_file())
        self.assertTrue((self.project / ".agents/qa/demo/codex-result.json").is_file())
        self.assertIn("## TC-001 Page shows 11", (self.project / ".agents/qa/demo/cases.md").read_text())

    def test_profile_stage_overrides_model_effort_backend_and_approve(self) -> None:
        (self.project / ".agents/routing.profile.yaml").write_text(
            "pm: claude\nlanes:\n  main_write: cursor\nstages:\n  browser_qa:\n"
            "    enabled: true\n    provider: codex\n    model: gpt-5.6-terra\n"
            "    reasoning_effort: medium\n    backend: headless\n    approve: never\n",
            encoding="utf-8",
        )
        result = self.run_runner("--case", "Page shows 11")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        argv = json.loads(self.log.read_text())
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-5.6-terra")
        self.assertIn("model_reasoning_effort=medium", argv)
        self.assertNotIn("--approve-for-me", argv)
        self.assertIn("workspace-write", argv)
        self.assertIn("in-app / headless browser backend", argv[-1])

    def test_failed_verdict_exits_one_and_disabled_stage_exits_two(self) -> None:
        result = self.run_runner("--case", "Page shows 11", verdict="fail")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        (self.project / ".agents/routing.profile.yaml").write_text(
            "stages:\n  browser_qa:\n    enabled: false\n", encoding="utf-8"
        )
        result = self.run_runner("--case", "x")
        self.assertEqual(result.returncode, 2)
        self.assertIn("disabled", result.stderr)

    def test_production_requires_authorized_and_dry_run_prints_receipt(self) -> None:
        result = self.run_runner("--case", "x", "--env-class", "production")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--authorized", result.stderr)
        result = self.run_runner("--case", "x", "--env-class", "production", "--authorized", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["argv"][-1], "<prompt>")
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from pipeline_stages import (  # noqa: E402
    ack_critique,
    attach_decision,
    compute_decision,
    critique_gate_errors,
    load_stages_from_profile,
    merge_llm_into_critique,
    normalize_stages,
    run_full_critique,
    structural_critique,
    write_critique_artifacts,
)
from routing_profile import load_routing_profile  # noqa: E402
from plan_critique_llm import (  # noqa: E402
    extract_json_payload,
    parse_llm_payload,
)


class PipelineStagesTest(unittest.TestCase):
    def test_normalize_defaults(self) -> None:
        s = normalize_stages(None, write_provider="qwen")
        self.assertTrue(s["plan_critique"]["enabled"])
        self.assertEqual(s["plan_critique"]["mode"], "advisory")
        self.assertEqual(s["plan_critique"]["provider"], "structural")
        self.assertEqual(s["write"]["provider"], "qwen")
        self.assertFalse(s["specialist"]["enabled"])

    def test_load_stages_from_yaml_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                textwrap.dedent(
                    """\
                    pm: claude
                    profile: full
                    lanes:
                      main_write: kimi
                    writer:
                      provider: kimi
                      model: kimi-code/k3-256k
                      reasoning_effort: medium
                    stages:
                      plan_critique:
                        enabled: true
                        mode: gate
                        provider: qwen
                        model: qwen3.8-max-preview
                        reasoning_effort: low
                      write:
                        provider: kimi
                        model: kimi-code/k3-256k
                        reasoning_effort: medium
                      night_review:
                        enabled: true
                        provider: qwen
                      specialist:
                        enabled: true
                        when: high_risk
                        provider: codex
                        model: gpt-5.6-sol
                        reasoning_effort: high
                    """
                ),
                encoding="utf-8",
            )
            profile = load_routing_profile(root)
            stages = load_stages_from_profile(profile)
            self.assertEqual(stages["plan_critique"]["mode"], "gate")
            self.assertEqual(stages["plan_critique"]["provider"], "qwen")
            self.assertTrue(stages["specialist"]["enabled"])
            self.assertEqual(stages["night_review"]["provider"], "qwen")

    def test_structural_critique_flags_thin_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 5\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text("# Plan\nshort\n", encoding="utf-8")
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "x"
                    owns_paths: []
                    verification: []
                    """
                ),
                encoding="utf-8",
            )
            result = structural_critique(run_dir)
            self.assertEqual(result["status"], "fail")
            codes = {f["code"] for f in result["findings"]}
            self.assertIn("plan_thin", codes)
            self.assertIn("owns_empty", codes)

    def test_critique_gate_and_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 1\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n" + ("goals and verification L1 L2 out of scope " * 5),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Ship a focused unit for feature X with clear DoD"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -m unittest tests/test_foo.py"
                        timeout_sec: 60
                    """
                ),
                encoding="utf-8",
            )
            result = structural_critique(run_dir)
            write_critique_artifacts(run_dir, result)
            settings = {"enabled": True, "mode": "gate"}
            # pass or fail depending on findings
            if result["status"] == "fail":
                errs = critique_gate_errors(run_dir, settings)
                self.assertTrue(errs)
                ack_critique(run_dir, note="accepted for micro", by="pm")
                errs2 = critique_gate_errors(run_dir, settings)
                self.assertEqual(errs2, [])
            else:
                self.assertEqual(critique_gate_errors(run_dir, settings), [])

    def test_plan_critique_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 0\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n"
                + ("Enough text for goals verification L1 out of scope risks. " * 4),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Add small helper with tests under owns"
                    owns_paths:
                      - bin/foo.py
                    verification:
                      - command: "python3 -c 'print(1)'"
                        timeout_sec: 30
                    """
                ),
                encoding="utf-8",
            )
            cli = ROOT / "bin" / "plan-critique"
            out = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--run-dir",
                    str(run_dir),
                    "--structural-only",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn(out.returncode, {0, 3}, out.stderr + out.stdout)
            payload = json.loads(out.stdout)
            self.assertIn(payload["status"], {"pass", "fail"})
            self.assertIn(payload["decision"], {"ship", "revise", "revise_required"})
            self.assertTrue((run_dir / "artifacts" / "critique.json").is_file())
            self.assertTrue((run_dir / "artifacts" / "critique.md").is_file())
            md = (run_dir / "artifacts" / "critique.md").read_text(encoding="utf-8")
            self.assertIn("PM decision", md)

    def test_decision_and_llm_merge(self) -> None:
        structural = {
            "schema_version": 1,
            "engine": "structural",
            "status": "pass",
            "summary": {"errors": 0, "warnings": 0, "infos": 0},
            "findings": [],
            "score": 3,
            "task_count": 1,
        }
        attach_decision(structural)
        self.assertEqual(structural["decision"], "ship")

        merged = merge_llm_into_critique(
            structural,
            {
                "verdict": "revise_required",
                "summary": "owns incomplete",
                "findings": [
                    {
                        "severity": "error",
                        "code": "owns_gap",
                        "title": "Missing companion path",
                        "detail": "Add src/bar.py to owns_paths",
                        "path": "tasks/001.yaml",
                        "task_id": "001",
                        "action": "fix_task",
                    }
                ],
            },
            provider="qwen",
            model="qwen3.8-max-preview",
        )
        self.assertEqual(merged["status"], "fail")
        self.assertEqual(merged["decision"], "revise_required")
        self.assertEqual(merged["llm_pass"]["status"], "ok")
        self.assertTrue(any(f["code"] == "llm_owns_gap" for f in merged["findings"]))
        self.assertIn("MUST", merged["pm_action"])

        warn_only = merge_llm_into_critique(
            {
                "schema_version": 1,
                "engine": "structural",
                "status": "pass",
                "summary": {"errors": 0, "warnings": 0, "infos": 0},
                "findings": [],
                "score": 1,
                "task_count": 1,
            },
            {
                "verdict": "revise",
                "summary": "thin notes",
                "findings": [
                    {
                        "severity": "warn",
                        "code": "thin_risk",
                        "title": "Risk notes thin",
                        "detail": "Add failure modes",
                        "path": "PLAN.md",
                    }
                ],
            },
            provider="codex",
            model="gpt-5.6-luna",
        )
        self.assertEqual(warn_only["status"], "pass")
        self.assertEqual(warn_only["decision"], "revise")

        failed_llm = merge_llm_into_critique(
            structural,
            None,
            provider="qwen",
            model="x",
            llm_error="timeout",
        )
        self.assertEqual(failed_llm["llm_pass"]["status"], "error")
        self.assertTrue(
            any(f["code"] == "llm_pass_failed" for f in failed_llm["findings"])
        )

    def test_parse_llm_payload(self) -> None:
        text = 'Here you go:\n```json\n{"verdict":"ship","summary":"ok","findings":[]}\n```\n'
        payload = parse_llm_payload(text)
        self.assertEqual(payload["verdict"], "ship")
        self.assertEqual(extract_json_payload('{"a":1}'), '{"a":1}')

    def test_run_full_critique_structural_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 1\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n" + ("goals verification L1 L2 out of scope risk " * 6),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Ship a focused unit for feature X with clear DoD"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -m unittest tests/test_foo.py"
                        timeout_sec: 60
                    """
                ),
                encoding="utf-8",
            )
            result = run_full_critique(
                run_dir,
                settings={
                    "enabled": True,
                    "mode": "advisory",
                    "provider": "qwen",
                    "model": "qwen3.8-max-preview",
                },
                structural_only=True,
            )
            self.assertIn(result["decision"], {"ship", "revise", "revise_required"})
            self.assertEqual(result["llm_pass"]["status"], "skipped")

    def test_agents_doctor_writes_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "kimi", "codex"):
                p = fake_bin / name
                p.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                p.chmod(0o755)
            env = {**dict(**__import__("os").environ), "PATH": str(fake_bin)}
            doctor = ROOT / "bin" / "agents-doctor"
            result = subprocess.run(
                [
                    sys.executable,
                    str(doctor),
                    "--apply",
                    "--writer-provider",
                    "kimi",
                    "--plan-critique",
                    "on",
                    "--plan-critique-mode",
                    "gate",
                    "--plan-critique-provider",
                    "qwen",
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
            text = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("stages:", text)
            self.assertIn("plan_critique:", text)
            self.assertIn("mode: gate", text)
            self.assertIn("provider: qwen", text)


if __name__ == "__main__":
    unittest.main()

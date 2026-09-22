#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_slots import (  # noqa: E402
    bump_grok_effort,
    classify_intent,
    classify_verify_tail,
    grok_effort_from_run,
    judge_qa_report,
    persist_run_risk,
    score_brief,
    suggest_write_skills,
    triage_night_findings,
    classify_emergency_effort,
)
from handoff_lib import next_act_for_failure  # noqa: E402


def _noul(value: float) -> dict:
    return {"type": "noul", "noul": value}


def _choice(value: str, confidence: float = 0.8) -> dict:
    return {"type": "choice", "choice": value, "confidence": confidence}


class JevSlotsTest(unittest.TestCase):
    def test_triage_dismisses_low_noul(self) -> None:
        findings = {
            "a" * 64: {
                "actionable": True,
                "status": "open",
                "title": "gold plate",
                "summary": "rename for style",
                "severity": "P3",
                "scope": {"owns_paths": ["docs/x.md"]},
            }
        }
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"f0_real": _noul(0.12)}},
        ):
            dismissed = triage_night_findings(findings)
        self.assertEqual(dismissed, ["a" * 64])
        self.assertFalse(findings["a" * 64]["actionable"])
        self.assertEqual(findings["a" * 64]["status"], "dismissed")

    def test_jev_inputs_keep_long_tail_and_all_findings(self) -> None:
        tail = "TAIL" * 2000
        findings = {
            str(index): {
                "actionable": True,
                "status": "open",
                "title": f"finding {index}",
                "summary": tail if index == 12 else "summary",
                "scope": {"owns_paths": ["src/app.py"]},
            }
            for index in range(13)
        }
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {f"f{index}_real": _noul(0.9) for index in range(13)}},
        ) as call:
            triage_night_findings(findings)
        state = call.call_args.args[0]
        self.assertEqual(len(state["findings"]), 13)
        self.assertTrue(state["findings"][12]["summary"].endswith("TAIL"))

    def test_emergency_effort_sends_full_raw_task_after_marker(self) -> None:
        raw_task = "schema_version: 2\n" + "objective: " + ("x" * 12000)
        prompt = "writer contract\n--- RAW TASK YAML (verbatim) ---\n" + raw_task
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"effort": _choice("high")}},
        ) as call:
            classify_emergency_effort(prompt, "medium")
        self.assertEqual(call.call_args.args[0]["task_prompt"], raw_task)

    def test_verify_tail_flake(self) -> None:
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"kind": _choice("flake", 0.72)}},
        ):
            self.assertEqual(
                classify_verify_tail("AssertionError: timeout"),
                "verification_flake",
            )
        self.assertEqual(next_act_for_failure("verification_flake"), "retry_or_fallback")
        self.assertEqual(next_act_for_failure("verification_env"), "operator_intervention")

    def test_verify_tail_uncertain_keeps_regex(self) -> None:
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"kind": _choice("flake", 0.2)}},
        ):
            self.assertIsNone(classify_verify_tail("AssertionError: foo"))

    def test_score_brief_maps_risk(self) -> None:
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"risk": _choice("high", 0.9)}},
        ):
            out = score_brief("Add CloudPayments webhook + lock chat")
        self.assertEqual(out["risk"], "high")
        self.assertEqual(out["score"], 8)

    def test_classify_intent(self) -> None:
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"intent": _choice("transactional", 0.86)}},
        ):
            out = classify_intent("купить подписку")
        self.assertEqual(out["intent"], "transactional")

    def test_judge_qa_report(self) -> None:
        with patch(
            "jev_slots.call_jev",
            return_value={"answers": {"kind": _choice("out_of_scope", 0.7)}},
        ):
            out = judge_qa_report("# QA\n- timeout on unused page", "fail")
        self.assertEqual(out["kind"], "out_of_scope")

    def test_persist_run_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "run.yaml").write_text("schema_version: 2\nslug: demo\n")
            persist_run_risk(run_dir, "high")
            text = (run_dir / "run.yaml").read_text()
        self.assertIn("risk: high", text)

    def test_suggest_write_skills_skips_jev_under_unittest(self) -> None:
        self.assertEqual(suggest_write_skills({"title": "fix auth"}), [])

    def test_grok_effort_from_run_maps_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "run.yaml").write_text("schema_version: 2\nrisk: high\n")
            self.assertEqual(grok_effort_from_run(run_dir, "medium"), "high")
            (run_dir / "run.yaml").write_text("schema_version: 2\nrisk: low\n")
            self.assertEqual(grok_effort_from_run(run_dir, "medium"), "low")
            (run_dir / "run.yaml").write_text("schema_version: 2\nslug: demo\n")
            self.assertEqual(grok_effort_from_run(run_dir, "medium"), "medium")

    def test_grok_effort_fail_open_and_disable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.assertEqual(grok_effort_from_run(run_dir, "medium"), "medium")
            (run_dir / "run.yaml").write_text("schema_version: 2\nrisk: high\n")
            with patch.dict("os.environ", {"LANE_JEV_EFFORT": "0"}):
                self.assertEqual(grok_effort_from_run(run_dir, "medium"), "medium")
                self.assertEqual(bump_grok_effort("medium"), "medium")

    def test_bump_grok_effort(self) -> None:
        self.assertEqual(bump_grok_effort("low"), "medium")
        self.assertEqual(bump_grok_effort("medium"), "high")
        self.assertEqual(bump_grok_effort("high"), "high")
        self.assertEqual(bump_grok_effort("xhigh"), "medium")


if __name__ == "__main__":
    unittest.main()

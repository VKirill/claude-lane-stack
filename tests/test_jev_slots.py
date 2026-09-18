#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_slots import (  # noqa: E402
    classify_intent,
    classify_verify_tail,
    judge_qa_report,
    persist_run_risk,
    score_brief,
    triage_night_findings,
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


if __name__ == "__main__":
    unittest.main()

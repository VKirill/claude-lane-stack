#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from plan_critique_jev import (
    ACTIONABLE_CUT,
    HARD_CODES,
    answers_to_payload,
    overlay_jev,
    pack_jev_state,
)
from pipeline_stages import (
    WRITE_STAGE_PROVIDERS,
    merge_llm_into_critique,
    normalize_stages,
)


class PlanCritiqueJevTest(unittest.TestCase):
    def test_jev_is_not_a_write_provider(self) -> None:
        self.assertNotIn("jev", WRITE_STAGE_PROVIDERS)
        stages = normalize_stages(
            {"write": {"provider": "jev"}, "night_review": {"provider": "jev"}},
            write_provider="jev",
        )
        self.assertEqual(stages["write"]["provider"], "kimi")
        self.assertEqual(stages["night_review"]["provider"], "qwen")
        self.assertEqual(stages["plan_critique"]["provider"], "jev")

    def test_pack_state_is_narrow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "PLAN.md").write_text("Gate chat behind first payment.\n")
            (run_dir / "SPEC.md").write_text("Invariant: from-scratch only.\n")
            (run_dir / "tasks").mkdir()
            (run_dir / "tasks" / "001.yaml").write_text(
                "id: '001'\nowns_paths: [apps/api/src/lib/trial-eligibility.ts]\n"
            )
            state = pack_jev_state(
                run_dir,
                {
                    "findings": [
                        {
                            "id": "structural:plan_path_unowned:dto.ts",
                            "severity": "warn",
                            "code": "plan_path_unowned",
                            "title": "dto unowned",
                            "path": "apps/api/src/routes/v1/admin-payments-dto.ts",
                        },
                        {
                            "id": "structural:owns_gap:wiki/x.md",
                            "severity": "info",
                            "code": "owns_gap",
                            "title": "wiki",
                            "path": "wiki/x.md",
                        },
                    ]
                },
            )
        self.assertIn("first payment", state["plan"])
        self.assertEqual(len(state["structural_findings"]), 1)
        self.assertEqual(state["structural_findings"][0]["code"], "plan_path_unowned")
        self.assertEqual(state["tasks"][0]["file"], "001.yaml")

    def test_pack_state_keeps_full_inputs(self) -> None:
        tail = "PLAN_TAIL" * 1200
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "PLAN.md").write_text(tail)
            (run_dir / "SPEC.md").write_text("SPEC_TAIL" * 700)
            (run_dir / "tasks").mkdir()
            (run_dir / "tasks" / "001.yaml").write_text("task_tail: " + ("T" * 3000))
            state = pack_jev_state(
                run_dir,
                {
                    "findings": [
                        {"id": str(index), "severity": "warn", "code": "owns_gap"}
                        for index in range(13)
                    ]
                },
            )
        self.assertTrue(state["plan"].endswith("PLAN_TAIL"))
        self.assertTrue(state["spec"].endswith("SPEC_TAIL"))
        self.assertTrue(state["tasks"][0]["body"].endswith("T"))
        self.assertEqual(len(state["structural_findings"]), 13)

    def test_answers_uncertain_ship_becomes_revise(self) -> None:
        payload = answers_to_payload(
            {
                "model": "typesafe/jev-1.13-20260917",
                "answers": {
                    "verdict": {
                        "type": "choice",
                        "choice": "ship",
                        "confidence": 0.19,
                    },
                    "warns_actionable": {"type": "noul", "noul": 0.2},
                    "spec_contradicts_plan": {"type": "noul", "noul": 0.1},
                    "risk": {"type": "choice", "choice": "medium", "confidence": 1},
                },
            }
        )
        self.assertEqual(payload["verdict"], "revise")
        self.assertTrue(payload["uncertain"])

    def test_overlay_demotes_soft_warn_when_ship(self) -> None:
        structural = {
            "schema_version": 1,
            "status": "pass",
            "findings": [
                {
                    "severity": "warn",
                    "code": "plan_path_unowned",
                    "title": "dto unowned",
                    "detail": "read-only import",
                    "path": "apps/api/src/routes/v1/admin-payments-dto.ts",
                    "source": "structural",
                    "action": "add_owns",
                }
            ],
        }
        jev = {
            "verdict": "ship",
            "summary": "Jev: dispatch. Soft structural warns look like noise.",
            "findings": [],
            "confidence": 0.65,
            "warns_actionable": 0.26,
            "uncertain": False,
        }
        merged = merge_llm_into_critique(
            structural, jev, provider="jev", model="typesafe/jev-1.13"
        )
        over = overlay_jev(merged, jev)
        self.assertEqual(over["decision"], "ship")
        self.assertEqual(over["findings"][0]["severity"], "info")
        self.assertLess(0.26, ACTIONABLE_CUT)

    def test_overlay_keeps_hard_overlap(self) -> None:
        self.assertIn("owns_overlap", HARD_CODES)
        structural = {
            "schema_version": 1,
            "status": "fail",
            "findings": [
                {
                    "severity": "error",
                    "code": "owns_overlap",
                    "title": "Tasks 001 and 002 overlap",
                    "detail": "same path",
                    "path": "tasks/",
                    "source": "structural",
                    "action": "split_task",
                }
            ],
        }
        jev = {
            "verdict": "ship",
            "summary": "x",
            "findings": [],
            "confidence": 0.9,
            "warns_actionable": 0.1,
            "uncertain": False,
        }
        merged = merge_llm_into_critique(
            structural, jev, provider="jev", model="typesafe/jev-1.13"
        )
        over = overlay_jev(merged, jev)
        self.assertEqual(over["decision"], "revise_required")
        self.assertEqual(over["findings"][0]["severity"], "error")

    def test_spec_contradict_becomes_finding(self) -> None:
        payload = answers_to_payload(
            {
                "answers": {
                    "verdict": {
                        "type": "choice",
                        "choice": "revise",
                        "confidence": 0.6,
                    },
                    "warns_actionable": {"type": "noul", "noul": 0.5},
                    "spec_contradicts_plan": {"type": "noul", "noul": 0.88},
                    "risk": {"type": "choice", "choice": "medium", "confidence": 1},
                }
            }
        )
        self.assertEqual(payload["findings"][0]["code"], "missing_invariant")

    def test_fat_task_becomes_finding(self) -> None:
        payload = answers_to_payload(
            {
                "answers": {
                    "verdict": {
                        "type": "choice",
                        "choice": "revise",
                        "confidence": 0.7,
                    },
                    "warns_actionable": {"type": "noul", "noul": 0.4},
                    "spec_contradicts_plan": {"type": "noul", "noul": 0.1},
                    "fat_task": {"type": "noul", "noul": 0.81},
                    "risk": {"type": "choice", "choice": "medium", "confidence": 1},
                }
            }
        )
        self.assertEqual(payload["findings"][0]["code"], "fat_task")
        self.assertEqual(payload["findings"][0]["action"], "split_task")


if __name__ == "__main__":
    unittest.main()

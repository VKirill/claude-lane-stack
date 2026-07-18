from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "schemas" / "run-controller-v1.schema.json").read_text(encoding="utf-8")
)


class RunControllerSchemaTest(unittest.TestCase):
    def receipt(self) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "schema_version": 1,
            "run_dir": "/tmp/repo/.agents/runs/demo",
            "project_cwd": "/tmp/repo/.worktrees/demo",
            "stage": "running",
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
            "last_event": {
                "type": "transition",
                "event": "task_started",
                "at": now,
                "task_id": "001",
            },
            "next_action": "poll",
            "counts": {
                "total": 1,
                "accepted": 0,
                "blocked": 0,
                "running": 1,
                "pending": 0,
            },
            "tasks": {
                "001": {
                    "task_file": "/tmp/repo/.agents/runs/demo/tasks/001.yaml",
                    "depends_on": [],
                    "stage": "running",
                    "last_status": "running",
                    "retries": 0,
                    "updated_at": now,
                }
            },
        }

    def test_accepts_running_and_terminal_receipts(self) -> None:
        receipt = self.receipt()
        jsonschema.Draft202012Validator(SCHEMA).validate(receipt)

        receipt["stage"] = "accepted"
        receipt["completed_at"] = receipt["updated_at"]
        receipt["next_action"] = "complete"
        receipt["counts"] = {
            "total": 1,
            "accepted": 1,
            "blocked": 0,
            "running": 0,
            "pending": 0,
        }
        task = receipt["tasks"]["001"]
        task["stage"] = "accepted"
        jsonschema.Draft202012Validator(SCHEMA).validate(receipt)

    def test_rejects_unknown_stage_and_retry_count(self) -> None:
        receipt = self.receipt()
        receipt["tasks"]["001"]["stage"] = "mystery"
        receipt["tasks"]["001"]["retries"] = 2

        errors = list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(receipt))

        self.assertEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()

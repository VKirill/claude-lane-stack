"""lane-memory on the BB hub: a fake `bb` stands in for Lane Pilot's session_memory_* RPCs."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

FAKE_BB = r'''#!/usr/bin/env python3
import json, sys, pathlib
store = pathlib.Path(sys.argv[0]).with_suffix(".json")
data = json.loads(store.read_text()) if store.exists() else {"records": [], "lessons": [], "down": False}
if data.get("down"):
    print("Error: Cannot connect to BB server", file=sys.stderr); sys.exit(1)
method = sys.argv[sys.argv.index("lane-pilot") + 1]
payload = json.loads(pathlib.Path(sys.argv[sys.argv.index("--input-file") + 1]).read_text())
if method == "session_memory_project":
    out = {"projectId": "proj_test", "scopes": []}
elif method == "session_memory_write":
    rid = f"m{len(data['records'])}"
    data["records"].append({"id": rid, **payload}); out = {"stored": True, "id": rid, "reason": None}
elif method == "session_memory_search":
    words = payload["query"].lower().split()
    out = {"records": [{"id": r["id"], "kind": r["kind"], "content": r["content"], "concepts": r["concepts"]}
                       for r in data["records"] if any(w in r["content"].lower() for w in words)]}
elif method == "session_memory_core":
    out = {"records": [{"id": r["id"], "content": r["content"]} for r in data["records"] if r["kind"] == "core"]}
elif method == "session_lesson":
    data["lessons"].append(payload); out = {"proposalId": "rule_1", "repeatOf": None, "state": "accepted", "adopted": True}
store.write_text(json.dumps(data)); print(json.dumps(out))
'''

DRAFT = """---
id: ship-from-pm
schema_version: 2
status: active
memory_type: normative
truth_mode: decision
claim: Ship only from the PM chat
language: en
sensitivity: internal
context_priority: always
retrieval:
  areas: [procedures]
  hint: release, deploy
---

Owner rule.
"""


class LaneMemoryHubTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.bb = self.tmp / "bb"
        self.bb.write_text(FAKE_BB, encoding="utf-8")
        self.bb.chmod(0o755)
        self.env = {k: os.environ.get(k) for k in ("BB_CLI", "LANE_MEMORY_HUB", "BB_PROJECT_ID", "BB_HOST_ID")}
        os.environ.update({"BB_CLI": str(self.bb), "BB_HOST_ID": "host_test"})
        os.environ.pop("LANE_MEMORY_HUB", None)
        os.environ.pop("BB_PROJECT_ID", None)
        import lane_memory as lm
        lm._HUB_STATE.clear()
        self.lm = lm
        self.repo = self.tmp / "repo"
        (self.repo / ".agents").mkdir(parents=True)
        (self.repo / "CLAUDE.md").write_text("# App\n", encoding="utf-8")
        (self.repo / ".agents" / "routing.profile.yaml").write_text("stages:\n  memory:\n    enabled: true\n    inject: true\n", encoding="utf-8")
        lm.init_corpus(self.repo)

    def tearDown(self) -> None:
        for key, value in self.env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def store(self) -> dict:
        return json.loads(self.bb.with_suffix(".json").read_text(encoding="utf-8"))

    def test_write_goes_to_the_hub_not_a_local_file(self) -> None:
        draft = self.repo / ".agents" / "memory" / "drafts" / "one.md"
        draft.write_text(DRAFT, encoding="utf-8")
        dest, log = self.lm.write_apply(self.repo, draft, yes=True, confirm=self.repo / ".agents" / "memory" / "ship-from-pm.md")
        self.assertEqual(str(dest), "hub:m0")
        self.assertFalse((self.repo / ".agents" / "memory" / "ship-from-pm.md").exists())
        self.assertEqual(self.store()["records"][0]["kind"], "core")
        self.assertIn("Ship only from the PM chat", self.lm.core_text(self.repo))
        self.assertIn("Ship only from the PM chat", (self.repo / "CLAUDE.md").read_text(encoding="utf-8"))
        hits, _ = self.lm.search(self.repo, "ship")
        self.assertEqual(hits[0]["id"], "m0")
        self.assertTrue(any("hub m0" in line for line in log))

    def test_the_folder_decides_the_project_not_the_session(self) -> None:
        os.environ["BB_PROJECT_ID"] = "proj_session"
        self.assertEqual(self.lm._hub().project(self.repo), "proj_test")

    def test_a_lesson_is_a_rule_proposal_and_waits_while_the_hub_is_down(self) -> None:
        out = self.lm.lesson(self.repo, "Run npm ci in writer worktrees, never npm install", evidence="owner corrected", audience="writer", always=True)
        self.assertEqual(out["state"], "accepted")
        sent = self.store()["lessons"][0]
        self.assertEqual(sent["rule"], "Run npm ci in writer worktrees, never npm install")
        self.assertEqual((sent["audience"], sent["always"]), ("writer", True))
        data = self.store()
        data["down"] = True
        self.bb.with_suffix(".json").write_text(json.dumps(data), encoding="utf-8")
        queued = self.lm.lesson(self.repo, "Keep helpers next to the code you change")
        self.assertIn("queued", queued)
        self.assertFalse((self.repo / ".agents" / "LESSONS.md").exists())
        data["down"] = False
        self.bb.with_suffix(".json").write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.lm._hub().flush(self.repo), 1)
        self.assertEqual(len(self.store()["lessons"]), 2)

    def test_a_pm_lesson_is_never_marked_for_every_writer_task(self) -> None:
        self.lm.lesson(self.repo, "Write owns_paths with every sibling test", audience="pm", always=True)
        self.assertEqual((self.store()["lessons"][0]["audience"], self.store()["lessons"][0]["always"]), ("pm", False))
        with self.assertRaises(ValueError):
            self.lm.lesson(self.repo, "Some other rule for someone", audience="owner")


if __name__ == "__main__":
    unittest.main()

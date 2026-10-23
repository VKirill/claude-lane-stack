"""The owner's presence mark (hooks/owner_presence.py, SMA atlas D2-6)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
import owner_presence  # noqa: E402


class OwnerPresenceTest(unittest.TestCase):
    def test_only_the_owners_own_session_marks_presence(self) -> None:
        self.assertTrue(owner_presence.owner_session({}))
        for marker in owner_presence.MARKERS:
            self.assertFalse(owner_presence.owner_session({marker: "x"}), marker)
        self.assertFalse(owner_presence.owner_session({"LANE_OWNER_PRESENCE": "0"}))

    def test_the_hook_writes_the_time_and_host_never_the_prompt_and_prints_nothing(self) -> None:
        home = Path(tempfile.mkdtemp())
        env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
        out = subprocess.run([sys.executable, str(ROOT / "hooks/owner_presence.py")], input=json.dumps({"prompt": "my secret plan"}), capture_output=True, text=True, env=env)
        self.assertEqual((out.returncode, out.stdout), (0, ""))
        text = (home / ".agents/state/owner-presence.json").read_text()
        self.assertNotIn("secret", text)
        self.assertEqual(sorted(json.loads(text)["claude-code"].keys()), ["at", "host"])
        lane = subprocess.run([sys.executable, str(ROOT / "hooks/owner_presence.py")], input="{}", capture_output=True, text=True, env={**env, "HOME": str(Path(tempfile.mkdtemp())), "LANE_PILOT_AGENT_TYPE": "lane-pilot-writer"})
        self.assertEqual(lane.returncode, 0)

    def test_bbs_model_list_probe_is_not_the_owner(self) -> None:
        self.assertTrue(owner_presence.model_list_probe(".", {"CLAUDE_CODE_ENTRYPOINT": "sdk-ts"}))
        self.assertFalse(owner_presence.model_list_probe(".", {"CLAUDE_CODE_ENTRYPOINT": "cli"}))
        self.assertFalse(owner_presence.model_list_probe(".", {"CLAUDE_CODE_ENTRYPOINT": "sdk-ts", "BB_THREAD_ID": "thr_1"}))
        self.assertFalse(owner_presence.model_list_probe("так делай", {"CLAUDE_CODE_ENTRYPOINT": "sdk-ts"}))
        home = Path(tempfile.mkdtemp())
        env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "CLAUDE_CODE_ENTRYPOINT": "sdk-ts"}
        subprocess.run([sys.executable, str(ROOT / "hooks/owner_presence.py")], input=json.dumps({"prompt": "."}), capture_output=True, text=True, env=env)
        self.assertFalse((home / ".agents/state/owner-presence.json").exists())

    def test_turns_no_person_typed_mark_nothing(self) -> None:
        for prompt in ["<task-notification>done</task-notification>", "[SYSTEM NOTIFICATION - NOT USER INPUT] x", "<system-reminder>r</system-reminder>",
                       "[bb message from thread:thr_1] hi", "Lane Pilot: results of your tasks",
                       "You are the Lane Pilot PM. Do not write production code yourself.", "", None]:
            self.assertFalse(owner_presence.typed_by_a_person(prompt), prompt)
        self.assertTrue(owner_presence.typed_by_a_person("так делай"))
        home = Path(tempfile.mkdtemp())
        env = {"PATH": "/usr/bin:/bin", "HOME": str(home)}
        subprocess.run([sys.executable, str(ROOT / "hooks/owner_presence.py")], input=json.dumps({"prompt": "<task-notification>x</task-notification>"}), capture_output=True, text=True, env=env)
        self.assertFalse((home / ".agents/state/owner-presence.json").exists())

    def test_a_later_mark_keeps_other_providers(self) -> None:
        home = Path(tempfile.mkdtemp())
        owner_presence.record(home, 1, "mini", provider="codex")
        owner_presence.record(home, 2, "mini")
        self.assertEqual(json.loads((home / ".agents/state/owner-presence.json").read_text()), {"codex": {"at": 1, "host": "mini"}, "claude-code": {"at": 2, "host": "mini"}})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"


def load_gate_triage():
    loader = SourceFileLoader("gate_triage", str(BIN / "gate-triage"))
    spec = importlib.util.spec_from_loader("gate_triage", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


gate_triage = load_gate_triage()


VALID_PAYLOAD = {
    "schema_version": 1,
    "summary": "one false positive",
    "findings": [
        {
            "severity": "P2",
            "title": "Ignore generated file in owns gate",
            "summary": "Recurring owns-paths block on a generated infra file.",
            "classification": "false_positive",
            "actionable": True,
            "target": "tool",
            "rationale": "generated file the gate should ignore",
            "evidence": [
                {"path": "bin/check-owns-paths", "line": 30, "detail": "IGNORE_FILES tuple"}
            ],
            "scope": {"owns_paths": ["bin/check-owns-paths"], "never_touch": []},
            "verification": [
                {"command": "python3 -m unittest discover -s tests", "timeout_sec": 900}
            ],
        }
    ],
}


def fenced(payload: dict) -> str:
    return "```json\n" + json.dumps(payload) + "\n```"


class PureHelperTests(unittest.TestCase):
    def test_parse_qwen_stream(self) -> None:
        stdout = "\n".join(
            [
                json.dumps({"type": "system", "subtype": "init", "session_id": "s1", "permission_mode": "yolo"}),
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "thinking..."}]}}),
                json.dumps({"type": "result", "subtype": "success", "is_error": False, "session_id": "s1", "result": "```json\n{}\n```"}),
            ]
        )
        envelope = gate_triage.parse_qwen_stream(stdout)
        self.assertTrue(envelope["saw_result"])
        self.assertEqual(envelope["subtype"], "success")
        self.assertFalse(envelope["is_error"])
        self.assertEqual(envelope["session_id"], "s1")
        self.assertIn("```json", envelope["result"])

    def test_extract_json_payload_fenced_and_bare(self) -> None:
        self.assertEqual(gate_triage.extract_json_payload('x ```json\n{"a": 1}\n``` y'), '{"a": 1}')
        self.assertEqual(gate_triage.extract_json_payload('noise {"a": 1} tail'), '{"a": 1}')
        with self.assertRaises(gate_triage.TriageError):
            gate_triage.extract_json_payload("no json here")

    def test_fingerprint_is_deterministic(self) -> None:
        candidate = VALID_PAYLOAD["findings"][0]
        self.assertEqual(
            gate_triage.candidate_fingerprint(candidate),
            gate_triage.candidate_fingerprint(dict(candidate)),
        )

    def test_canonical_finding_matches_finding_v1_schema(self) -> None:
        candidate = VALID_PAYLOAD["findings"][0]
        fp = gate_triage.candidate_fingerprint(candidate)
        finding = gate_triage.canonical_finding(candidate, fp, "2026-07-24T00:00:00+00:00", None)
        schema = gate_triage.load_schema("finding-v1.schema.json")
        # Should not raise.
        gate_triage.validate_schema(finding, schema, "finding-v1")
        self.assertEqual(finding["status"], "open")
        self.assertEqual(finding["source_chunk"], "gate-triage")

    def test_persist_finding_preserves_first_seen(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            candidate = VALID_PAYLOAD["findings"][0]
            fp = gate_triage.candidate_fingerprint(candidate)
            first = gate_triage.canonical_finding(candidate, fp, "2026-07-01T00:00:00+00:00", None)
            path, created = gate_triage.persist_finding(repo, first)
            self.assertTrue(created)
            second = gate_triage.canonical_finding(candidate, fp, "2026-07-20T00:00:00+00:00", None)
            _, created_again = gate_triage.persist_finding(repo, second)
            self.assertFalse(created_again)
            stored = json.loads(path.read_text())
            self.assertEqual(stored["first_seen"], "2026-07-01T00:00:00+00:00")
            self.assertEqual(stored["last_seen"], "2026-07-20T00:00:00+00:00")


class GateTriageEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.tool_repo = self.root / "tool-repo"
        (self.tool_repo / ".agents").mkdir(parents=True)
        (self.home / ".agents").mkdir(parents=True)
        (self.home / ".agents" / "install.json").write_text(
            json.dumps({"schema_version": 1, "source_repo": str(self.tool_repo)}),
            encoding="utf-8",
        )
        # gate log with one blocking event
        self.gate_log = self.root / "gate-events.jsonl"
        self.gate_log.write_text(
            json.dumps(
                {
                    "v": 1,
                    "ts": "2026-07-23T00:00:00+00:00",
                    "gate": "owns-paths",
                    "status": "failed",
                    "project": "/srv/app",
                    "run_slug": "demo",
                    "task_id": "001",
                    "violations": ["generated.css"],
                    "exit_code": 1,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        # stub qwen
        self.result_file = self.root / "stub-result.txt"
        self.stub = self.root / "stub-qwen"
        self.stub.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            "body = open(os.environ['STUB_RESULT_FILE']).read()\n"
            "print(json.dumps({'type':'system','subtype':'init','session_id':'stub','permission_mode':'yolo'}))\n"
            "print(json.dumps({'type':'result','subtype':'success','is_error':False,'session_id':'stub','result':body,'num_turns':1}))\n",
            encoding="utf-8",
        )
        self.stub.chmod(self.stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_triage(self, *extra: str, result_body: str = "") -> subprocess.CompletedProcess:
        self.result_file.write_text(result_body, encoding="utf-8")
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env["STUB_RESULT_FILE"] = str(self.result_file)
        env.pop("CLAUDE_LANE_GATE_LOG", None)
        return subprocess.run(
            [
                "python3",
                str(BIN / "gate-triage"),
                "--log",
                str(self.gate_log),
                "--qwen-bin",
                str(self.stub),
                *extra,
            ],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_no_blocking_events_writes_clean_report(self) -> None:
        self.gate_log.write_text("", encoding="utf-8")
        result = self.run_triage("--no-repair")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = list((self.home / ".agents" / "logs" / "gate-triage").glob("GATE-TRIAGE-*.md"))
        self.assertEqual(len(reports), 1)
        self.assertIn("no blocking events", reports[0].read_text().lower())

    def test_triage_persists_finding_and_report(self) -> None:
        result = self.run_triage("--no-repair", result_body=fenced(VALID_PAYLOAD))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        findings = list((self.tool_repo / ".agents" / "findings").glob("*.json"))
        self.assertEqual(len(findings), 1)
        finding = json.loads(findings[0].read_text())
        self.assertEqual(finding["status"], "open")
        self.assertEqual(finding["schema_version"], 1)
        self.assertEqual(finding["scope"]["owns_paths"], ["bin/check-owns-paths"])
        # report + json projection + backlog
        reports = list((self.home / ".agents" / "logs" / "gate-triage").glob("GATE-TRIAGE-*.md"))
        self.assertEqual(len(reports), 1)
        self.assertIn("Ignore generated file", reports[0].read_text())
        backlog = (self.tool_repo / ".agents" / "agent-notes" / "OPEN.md")
        self.assertTrue(backlog.is_file())
        self.assertIn("gate-triage", backlog.read_text())

    def test_invalid_qwen_output_fails_closed(self) -> None:
        result = self.run_triage("--no-repair", result_body="```json\n{not valid json}\n```")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        failures = list((self.home / ".agents" / "logs" / "gate-triage").glob("*.failures.md"))
        self.assertEqual(len(failures), 1)
        # no findings persisted
        self.assertEqual(list((self.tool_repo / ".agents" / "findings").glob("*.json")), [])

    def test_schema_violation_fails_closed(self) -> None:
        bad = {"schema_version": 1, "findings": [{"severity": "P9", "title": "x"}]}
        result = self.run_triage("--no-repair", result_body=fenced(bad))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

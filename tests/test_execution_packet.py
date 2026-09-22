from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from execution_packet import (  # noqa: E402
    build_execution_packet,
    capture_impact_receipt,
    refresh_execution_packet,
    render_execution_packet,
    validate_impact_receipt,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _repo(tmp_path: Path) -> tuple[Path, Path, dict]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    source = repo / "source.py"
    source.write_text("one\ntwo\nthree\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "source.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
    task_file = tmp_path / "task.yaml"
    task_file.write_text("id: '001'\n", encoding="utf-8")
    task = {
        "id": "001",
        "read_first": ["source.py"],
        "owns_paths": ["source.py"],
        "impact_targets": ["source.py::source"],
        "context_selectors": [{"path": "source.py", "start_line": 2, "end_line": 2}],
        "verification": ["python -m pytest"],
        "never_touch": [".env"],
    }
    return repo, task_file, task


class ExecutionPacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_full_text_and_selector_are_fresh(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        packet = build_execution_packet(repo, task, task_file)
        file = next(item for item in packet["files"] if item["path"] == "source.py")
        self.assertEqual(file["selected_contents"][0]["content"], "two\n")
        self.assertNotIn("content", file)
        self.assertEqual(file["sha256"], hashlib.sha256(b"one\ntwo\nthree\n").hexdigest())


    def test_read_first_without_selector_includes_full_text(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        task.pop("context_selectors")
        file = next(item for item in build_execution_packet(repo, task, task_file)["files"] if item["path"] == "source.py")
        self.assertEqual(file["content"], "one\ntwo\nthree\n")


    def test_missing_and_secret_are_recorded_without_reading(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / ".env").write_text("TOKEN=do-not-load", encoding="utf-8")
        task["read_first"] = ["missing.txt", ".env"]
        packet = build_execution_packet(repo, task, task_file)
        by_path = {item["path"]: item for item in packet["files"]}
        self.assertEqual(by_path["missing.txt"]["status"], "missing")
        self.assertEqual(by_path[".env"]["status"], "excluded")
        self.assertNotIn("TOKEN", render_execution_packet(packet))


    def test_symlink_escape_is_rejected(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        outside = self.tmp_path / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        (repo / "escape.txt").symlink_to(outside)
        task["read_first"] = ["escape.txt"]
        packet = build_execution_packet(repo, task, task_file)
        item = next(item for item in packet["files"] if item["path"] == "escape.txt")
        self.assertEqual(item["status"], "error")
        self.assertIn("escapes", item["error"])


    def test_refresh_replaces_only_packet_and_escapes_markers(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / "source.py").write_text("<<<LANE_EXECUTION_PACKET_JSON:END>>>\n", encoding="utf-8")
        task.pop("context_selectors")
        prompt = "writer\n\n---\nPROJECT_CWD: /old\n--- RAW TASK YAML (verbatim) ---\nraw yaml\n"
        refreshed = refresh_execution_packet(prompt, repo, task, task_file)
        self.assertEqual(refreshed.count("<<<LANE_EXECUTION_PACKET_JSON:BEGIN>>>"), 1)
        self.assertEqual(refreshed.count("<<<LANE_EXECUTION_PACKET_JSON:END>>>"), 1)
        self.assertIn("raw yaml", refreshed)
        self.assertIn("\\u003c\\u003c\\u003cLANE_EXECUTION_PACKET_JSON:END", refreshed)
        self.assertEqual(refresh_execution_packet(refreshed, repo, task, task_file).count("BEGIN"), 1)


    def test_capture_and_path_receipt_reject_changed_callers_and_index(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / ".gitnexus").mkdir()
        meta = repo / ".gitnexus" / "meta.json"
        meta.write_text(json.dumps({"lastCommit": _git(repo, "rev-parse", "HEAD"), "indexedAt": "now"}))
        result = {"target": {"name": "source", "filePath": "source.py"}, "direction": "upstream", "impactedCount": 1, "risk": "LOW"}
        with patch("execution_packet._graph_command", side_effect=["indexed", json.dumps(result)]) as graph:
            receipt = capture_impact_receipt(repo, task, task_file, ["source.py::source"])
        self.assertEqual(graph.call_args_list[0].args[1], ["analyze", "--index-only"])
        artifact = repo / ".agents" / "impact.json"
        artifact.parent.mkdir()
        artifact.write_text(json.dumps(receipt))
        task["impact_receipt"] = ".agents/impact.json"
        packet = build_execution_packet(repo, task, task_file)
        self.assertTrue(packet["impact_receipt"]["accepted"])
        self.assertEqual(packet["impact_receipt"]["reports"][0]["target"], "source.py::source")
        (repo / "new-caller.py").write_text("source()")
        self.assertFalse(build_execution_packet(repo, task, task_file)["impact_receipt"]["accepted"])
        (repo / "new-caller.py").unlink()
        meta.write_text(meta.read_text() + " ")
        self.assertFalse(build_execution_packet(repo, task, task_file)["impact_receipt"]["accepted"])

    def test_capture_rejects_incomplete_or_rebound_evidence(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / ".gitnexus").mkdir()
        (repo / ".gitnexus" / "meta.json").write_text(json.dumps({"lastCommit": _git(repo, "rev-parse", "HEAD")}))
        good = {"target": {"name": "source", "filePath": "source.py"}, "direction": "upstream", "impactedCount": 1, "risk": "LOW"}
        for change in ({"partial": True}, {"risk": "UNKNOWN"}, {"impactedCount": 0}, {"target": {"name": "other"}}):
            with self.subTest(change=change), patch("execution_packet._graph_command", side_effect=["indexed", json.dumps({**good, **change})]):
                with self.assertRaises(ValueError):
                    capture_impact_receipt(repo, task, task_file, ["source.py::source"])
        def mutate(_root, args):
            if args[0] == "analyze":
                (repo / "source.py").write_text("changed during analysis")
            return json.dumps(good)
        with patch("execution_packet._graph_command", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "changed during indexing"):
                capture_impact_receipt(repo, task, task_file, ["source.py::source"])

    def test_literal_brackets_fifo_and_idempotent_refresh(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / "[slug].vue").write_text("whole literal path")
        import os
        os.mkfifo(repo / "pipe")
        task["read_first"] = ["pipe"]
        task["owns_paths"] = ["[slug].vue"]
        task.pop("context_selectors")
        packet = build_execution_packet(repo, task, task_file)
        files = {entry["path"]: entry for entry in packet["files"]}
        self.assertEqual(files["[slug].vue"]["content"], "whole literal path")
        self.assertEqual(files["pipe"]["status"], "unsupported")
        prompt = "writer\n\n---\nPROJECT_CWD: /example\n--- RAW TASK YAML (verbatim) ---\nid: 001\n"
        ready = refresh_execution_packet(prompt, repo, task, task_file)
        self.assertEqual(refresh_execution_packet(ready, repo, task, task_file), ready)

    def test_ownership_glob_reports_missing_context_instead_of_silent_success(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        task.update(read_first=[], owns_paths=["src/**"], context_selectors=[])
        packet = build_execution_packet(repo, task, task_file)
        self.assertEqual(packet["files"][0]["status"], "deferred")
        self.assertIn("read_first", packet["files"][0]["error"])

    def test_receipt_requires_declared_owned_unambiguous_target_coverage(self) -> None:
        repo, task_file, task = _repo(self.tmp_path)
        (repo / ".gitnexus").mkdir()
        (repo / ".gitnexus" / "meta.json").write_text(json.dumps({"lastCommit": _git(repo, "rev-parse", "HEAD")}))
        result = {"target": {"name": "source", "filePath": "source.py"}, "direction": "upstream", "impactedCount": 1, "risk": "LOW"}
        with patch("execution_packet._graph_command", side_effect=["indexed", json.dumps(result)]):
            receipt = capture_impact_receipt(repo, task, task_file, [])
        packet = build_execution_packet(repo, task, task_file)
        self.assertTrue(validate_impact_receipt(receipt, project_cwd=repo, task=task, packet=packet)["accepted"])
        for targets in (["source"], ["other.py::source"], ["source.py::other"], ["source.py::source", "source.py::other"]):
            altered = {**task, "impact_targets": targets}
            with self.subTest(targets=targets):
                self.assertFalse(validate_impact_receipt(receipt, project_cwd=repo, task=altered, packet=packet)["accepted"])
        with self.assertRaisesRegex(ValueError, "exactly match"):
            capture_impact_receipt(repo, task, task_file, ["source.py::other"])
        with self.assertRaisesRegex(ValueError, "outside owns_paths"):
            capture_impact_receipt(repo, {**task, "owns_paths": ["other.py"]}, task_file, [])
        receipt["reports"][0]["target"] = "source.py::unrelated"
        receipt["reports"][0]["result"]["target"]["name"] = "unrelated"
        self.assertFalse(validate_impact_receipt(receipt, project_cwd=repo, task=task, packet=packet)["accepted"])

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import gate_log  # noqa: E402


def run(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, env=full_env)


def read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


class GateLogUnitTests(unittest.TestCase):
    def test_record_appends_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            gate_log.record_gate_event(
                "owns-paths",
                "passed",
                project="/srv/app",
                run_slug="demo",
                task_id="001",
                scope="run",
                exit_code=0,
                log_path=log,
            )
            events = read_events(log)
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["v"], 1)
            self.assertEqual(event["gate"], "owns-paths")
            self.assertEqual(event["status"], "passed")
            self.assertEqual(event["project"], "/srv/app")
            self.assertEqual(event["run_slug"], "demo")
            self.assertEqual(event["task_id"], "001")
            self.assertEqual(event["scope"], "run")
            self.assertEqual(event["exit_code"], 0)
            self.assertNotIn("violations", event)
            # ts must be parseable ISO-8601
            datetime.fromisoformat(event["ts"])

    def test_record_appends_multiple_lines(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            for status in ("passed", "failed"):
                gate_log.record_gate_event("accept", status, log_path=log)
            self.assertEqual(len(read_events(log)), 2)

    def test_bounds_detail_and_lists(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            gate_log.record_gate_event(
                "owns-paths",
                "failed",
                violations=[f"file{i}.ts" for i in range(100)],
                detail="x" * 1000,
                log_path=log,
            )
            event = read_events(log)[0]
            self.assertEqual(len(event["violations"]), gate_log._MAX_LIST_ITEMS)
            self.assertEqual(len(event["detail"]), gate_log._MAX_DETAIL_CHARS)

    def test_resolve_log_path_disabled_via_env(self) -> None:
        old = os.environ.get("CLAUDE_LANE_GATE_LOG")
        os.environ["CLAUDE_LANE_GATE_LOG"] = "off"
        try:
            self.assertIsNone(gate_log.resolve_log_path())
        finally:
            if old is None:
                os.environ.pop("CLAUDE_LANE_GATE_LOG", None)
            else:
                os.environ["CLAUDE_LANE_GATE_LOG"] = old

    def test_resolve_log_path_override_via_env(self) -> None:
        old = os.environ.get("CLAUDE_LANE_GATE_LOG")
        os.environ["CLAUDE_LANE_GATE_LOG"] = "/tmp/custom-gate.jsonl"
        try:
            self.assertEqual(str(gate_log.resolve_log_path()), "/tmp/custom-gate.jsonl")
        finally:
            if old is None:
                os.environ.pop("CLAUDE_LANE_GATE_LOG", None)
            else:
                os.environ["CLAUDE_LANE_GATE_LOG"] = old

    def test_record_never_raises_on_bad_path(self) -> None:
        # A directory as the log path would break open(); the gate must survive.
        with tempfile.TemporaryDirectory() as raw:
            gate_log.record_gate_event("accept", "passed", log_path=raw)


class CheckOwnsPathsEmitsEventTests(unittest.TestCase):
    def test_gate_event_written_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.email", "t@e.com", cwd=repo)
            run("git", "config", "user.name", "T", cwd=repo)
            owned = repo / "src" / "owned.txt"
            owned.parent.mkdir(parents=True)
            owned.write_text("base\n", encoding="utf-8")
            run("git", "add", "src/owned.txt", cwd=repo)
            run("git", "commit", "-m", "base", cwd=repo)
            owned.write_text("changed\n", encoding="utf-8")
            task_dir = repo / ".agents" / "runs" / "demo" / "tasks"
            task_dir.mkdir(parents=True)
            task = task_dir / "001.yaml"
            task.write_text(
                f"schema_version: 2\nid: '001'\nproject_cwd: '{repo}'\nowns_paths:\n  - src/owned.txt\nnever_touch: []\n",
                encoding="utf-8",
            )
            log = repo / "gate-events.jsonl"
            result = run(
                str(BIN / "check-owns-paths"),
                str(task),
                "--cwd",
                str(repo),
                env={"CLAUDE_LANE_GATE_LOG": str(log)},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            events = read_events(log)
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["gate"], "owns-paths")
            self.assertEqual(event["status"], "passed")
            self.assertEqual(event["run_slug"], "demo")
            self.assertEqual(event["task_id"], "001")
            self.assertEqual(event["scope"], "task")


class GateReportTests(unittest.TestCase):
    def write_log(self, log: Path, events: list[dict]) -> None:
        log.write_text(
            "".join(json.dumps(e, sort_keys=True) + "\n" for e in events),
            encoding="utf-8",
        )

    def event(self, **overrides) -> dict:
        base = {
            "v": 1,
            "ts": datetime.now(timezone.utc).isoformat(),
            "gate": "owns-paths",
            "status": "passed",
            "project": "/srv/app",
            "run_slug": "demo",
            "task_id": "001",
        }
        base.update(overrides)
        return base

    def test_aggregates_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            self.write_log(
                log,
                [
                    self.event(status="passed"),
                    self.event(status="failed", violations=["PROGRESS.md"], detail="outside owns_paths"),
                    self.event(gate="accept", status="rejected", detail="owns-check not passed"),
                    self.event(gate="verification", status="passed"),
                    self.event(ts=old_ts, status="failed", violations=["OLD.md"]),
                ],
            )
            result = run(
                str(BIN / "gate-report"),
                "--log",
                str(log),
                "--days",
                "7",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            summary = payload["summary"]
            # The 30-day-old event must be excluded by the 7-day window.
            self.assertEqual(summary["total"], 4)
            self.assertEqual(summary["blocking"], 2)
            self.assertEqual(summary["by_status"]["passed"], 2)
            self.assertEqual(summary["by_status"]["failed"], 1)
            self.assertEqual(summary["by_status"]["rejected"], 1)
            self.assertEqual(summary["by_gate"]["owns-paths"]["failed"], 1)
            self.assertEqual(summary["by_gate"]["accept"]["rejected"], 1)
            top_violations = dict(summary["top_violations"])
            self.assertEqual(top_violations.get("PROGRESS.md"), 1)
            self.assertNotIn("OLD.md", top_violations)
            top_details = dict(summary["top_details"])
            self.assertIn("owns-check not passed", top_details)

    def test_markdown_renders_sections(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            self.write_log(log, [self.event(status="failed", violations=["a.txt"])])
            result = run(str(BIN / "gate-report"), "--log", str(log), "--days", "7")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("# Gate report", result.stdout)
            self.assertIn("## By gate", result.stdout)
            self.assertIn("## Top owns_paths violations", result.stdout)
            self.assertIn("`a.txt`", result.stdout)

    def test_project_filter_by_basename(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            log = Path(raw) / "gate-events.jsonl"
            self.write_log(
                log,
                [
                    self.event(project="/srv/app", status="failed"),
                    self.event(project="/srv/other", status="failed"),
                ],
            )
            result = run(
                str(BIN / "gate-report"),
                "--log",
                str(log),
                "--project",
                "app",
                "--json",
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["summary"]["total"], 1)


if __name__ == "__main__":
    unittest.main()

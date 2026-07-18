from __future__ import annotations

import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_EXEC = ROOT / "bin" / "lane-exec"


class LaneExecTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _command(
        self,
        child_code: str,
        *,
        log: Path | None = None,
        event_log: Path | None = None,
        event_task: str = "001",
        idle: int = 5,
        maximum: int = 10,
    ) -> list[str]:
        command = [
            sys.executable,
            str(LANE_EXEC),
            "--idle",
            str(idle),
            "--max",
            str(maximum),
            "--label",
            "test-lane",
        ]
        if log is not None:
            command.extend(["--log", str(log)])
        if event_log is not None:
            command.extend(
                ["--event-log", str(event_log), "--event-task", event_task]
            )
        command.extend(["--", sys.executable, "-c", child_code])
        return command

    def _run(self, child_code: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self._command(child_code, **kwargs),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

    @staticmethod
    def _events(path: Path) -> list[dict[str, object]]:
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_success_with_log_preserves_zero_and_records_final_line(self) -> None:
        log = self.root / "lane-exec.log"

        result = self._run("print('child output')", log=log)

        self.assertEqual(result.returncode, 0, result.stderr)
        contents = log.read_text()
        self.assertIn("child output", contents)
        self.assertIn("exit code=0", contents)

    def test_nonzero_child_exit_is_preserved(self) -> None:
        result = self._run("raise SystemExit(23)")

        self.assertEqual(result.returncode, 23, result.stderr)

    def test_event_log_contains_parseable_start_and_exit(self) -> None:
        event_log = self.root / "events.jsonl"

        result = self._run("print('done')", event_log=event_log, event_task="task-7")

        self.assertEqual(result.returncode, 0, result.stderr)
        events = self._events(event_log)
        self.assertEqual([event["type"] for event in events], ["start", "exit"])
        self.assertEqual({event["task_id"] for event in events}, {"task-7"})
        self.assertEqual({event["label"] for event in events}, {"test-lane"})
        self.assertTrue(all(isinstance(event["pid"], int) for event in events))
        self.assertEqual(events[-1]["exit_code"], 0)

    def test_idle_timeout_emits_timeout_and_exit(self) -> None:
        event_log = self.root / "timeout-events.jsonl"

        result = self._run(
            "import time; time.sleep(30)",
            event_log=event_log,
            maximum=60,
        )

        self.assertEqual(result.returncode, 124, result.stderr)
        events = self._events(event_log)
        self.assertEqual(
            [event["type"] for event in events], ["start", "timeout", "exit"]
        )
        self.assertEqual(events[1]["reason"], "idle")
        self.assertEqual(events[-1]["exit_code"], 124)

    def test_sigint_emits_interruption_and_exit(self) -> None:
        event_log = self.root / "interrupt-events.jsonl"
        proc = subprocess.Popen(
            self._command("import time; time.sleep(30)", event_log=event_log),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while not event_log.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(event_log.exists(), "lane-exec did not emit its start event")

        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)

        self.assertEqual(proc.returncode, 130, f"{stdout}\n{stderr}")
        events = self._events(event_log)
        self.assertEqual(
            [event["type"] for event in events],
            ["start", "interruption", "exit"],
        )
        self.assertEqual(events[1]["reason"], "SIGINT")

    def test_concurrent_event_appends_remain_valid_jsonl(self) -> None:
        event_log = self.root / "shared-events.jsonl"
        processes = [
            subprocess.Popen(
                self._command(
                    "print('done')",
                    event_log=event_log,
                    event_task=f"task-{index}",
                ),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(8)
        ]

        errors = []
        for proc in processes:
            _, stderr = proc.communicate(timeout=10)
            if proc.returncode != 0:
                errors.append(stderr)
        self.assertFalse(errors, "\n".join(errors))

        events = self._events(event_log)
        self.assertEqual(len(events), 16)
        self.assertEqual(
            {event["task_id"] for event in events},
            {f"task-{index}" for index in range(8)},
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_INIT = ROOT / "bin" / "run-init"
RUN_VALIDATE = ROOT / "bin" / "run-validate"
RUN_CONTROLLER = ROOT / "bin" / "run-controller"


class LiveRunControllerTest(unittest.TestCase):
    def test_real_detached_stack_closes_provider_to_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            repo = temp / "repo"
            fake_home = temp / "home"
            fake_bin = fake_home / ".grok" / "bin"
            repo.mkdir()
            fake_bin.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "controller@example.test"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Controller Smoke"],
                cwd=repo,
                check=True,
            )
            (repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
            (repo / "second.txt").write_text("second\n", encoding="utf-8")
            subprocess.run(["git", "add", "baseline.txt", "second.txt"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True
            )
            (repo / ".agents").mkdir()
            (repo / ".agents" / "night-shift.yaml").write_text(
                'verification_executables: ["true"]\n', encoding="utf-8"
            )

            initialized = subprocess.run(
                [
                    str(RUN_INIT),
                    str(repo),
                    "live-controller",
                    "--score",
                    "7",
                    "--provider-pool",
                    "2",
                    "--verification-pool",
                    "1",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            run_dir = Path(initialized.stdout.strip())
            task_file = run_dir / "tasks" / "001.yaml"
            task_file.write_text(
                textwrap.dedent(
                    f"""\
                    schema_version: 2
                    id: "001"
                    title: "Exercise the detached controller"
                    risk: low
                    lane: grok
                    project_cwd: {json.dumps(str(repo))}
                    read_first: []
                    interfaces: []
                    invariants:
                      - "Preserve the baseline"
                    out_of_scope: []
                    expected_outputs:
                      - "A complete provider report"
                    owns_paths:
                      - "baseline.txt"
                    never_touch:
                      - ".env*"
                    depends_on: []
                    objective: |
                      Exercise the real lane lifecycle without changing source.
                    acceptance:
                      - "The controller writes an accepted receipt"
                    verify: tests
                    verification:
                      - command: "true"
                        cwd: {json.dumps(str(repo))}
                        timeout_sec: 10
                    """
                ),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "002.yaml").write_text(
                textwrap.dedent(
                    f"""\
                    schema_version: 2
                    id: "002"
                    title: "Exercise a parallel detached lane"
                    risk: low
                    lane: grok
                    project_cwd: {json.dumps(str(repo))}
                    read_first: []
                    interfaces: []
                    invariants:
                      - "Preserve the first lane"
                    out_of_scope: []
                    expected_outputs:
                      - "A second complete provider report"
                    owns_paths:
                      - "second.txt"
                    never_touch:
                      - ".env*"
                    depends_on: []
                    objective: |
                      Exercise shared-worktree run ownership in parallel.
                    acceptance:
                      - "The controller accepts the second lane"
                    verify: tests
                    verification:
                      - command: "true"
                        cwd: {json.dumps(str(repo))}
                        timeout_sec: 10
                    """
                ),
                encoding="utf-8",
            )

            provider = fake_bin / "grok"
            provider.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import hashlib
                    import json
                    import re
                    import sys
                    import time
                    from pathlib import Path

                    args = sys.argv[1:]
                    if "--version" in args:
                        print("grok live-controller-test")
                        raise SystemExit(0)
                    prompt = Path(args[args.index("--prompt-file") + 1])
                    session_flag = "--session-id" if "--session-id" in args else "--resume"
                    session_id = args[args.index(session_flag) + 1]
                    model = args[args.index("--model") + 1]
                    task_id = re.search(r'^id:\\s*["\\']?([^"\\'\\s]+)', prompt.read_text(encoding="utf-8"), re.M).group(1)
                    target = "baseline.txt" if task_id == "001" else "second.txt"
                    (Path.cwd() / target).write_text(f"changed by {task_id}\\n", encoding="utf-8")
                    time.sleep(0.2)
                    forged = prompt.parents[4] / f"provider-forged-{task_id}.json"
                    try:
                        forged.write_text("forged\\n", encoding="utf-8")
                        control_write = "allowed"
                    except OSError:
                        control_write = "denied"
                    prompt_sha256 = hashlib.sha256(prompt.read_bytes()).hexdigest()
                    print(json.dumps({"type": "session", "sessionId": session_id}), flush=True)
                    print(json.dumps({"type": "text", "data": "provider complete\\n"}), flush=True)
                    print(json.dumps({
                        "type": "text",
                        "data": (
                            "<<<LANE_REPORT:BEGIN>>>\\n"
                            f"TASK_ID: {task_id}\\n"
                            f"PROMPT_SHA256: {prompt_sha256}\\n"
                            "STATUS: complete\\n"
                            f"CONTROL_PLANE_WRITE: {control_write}\\n"
                            "SUMMARY: live controller smoke\\n"
                            "<<<LANE_REPORT:END>>>\\n"
                        ),
                    }), flush=True)
                    print(json.dumps({
                        "type": "end",
                        "stopReason": "EndTurn",
                        "sessionId": session_id,
                        "modelUsage": {model: {"inputTokens": 1, "outputTokens": 1, "modelCalls": 1}},
                    }), flush=True)
                    """
                ),
                encoding="utf-8",
            )
            provider.chmod(0o755)
            env = os.environ.copy()
            env["HOME"] = str(fake_home)
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            env["LANE_BG_BACKEND"] = os.environ.get(
                "LIVE_CONTROLLER_BACKEND", "nohup"
            )

            validated = subprocess.run(
                [str(RUN_VALIDATE), "--run-dir", str(run_dir), "--phase", "pre-dispatch"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)

            started = subprocess.run(
                [
                    str(RUN_CONTROLLER),
                    "start",
                    "--run-dir",
                    str(run_dir),
                    "--project-cwd",
                    str(repo),
                    "--poll-interval",
                    "0.05",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=5,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            start_receipt = json.loads(started.stdout)
            self.assertEqual(start_receipt["status"], "started")
            self.assertGreater(start_receipt["pid"], 1)

            watched = subprocess.run(
                [
                    str(RUN_CONTROLLER),
                    "watch",
                    "--run-dir",
                    str(run_dir),
                    "--timeout",
                    "20",
                    "--poll-interval",
                    "0.05",
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
                timeout=25,
            )
            self.assertEqual(watched.returncode, 0, watched.stderr)
            receipt = json.loads(watched.stdout)
            self.assertEqual(receipt["stage"], "accepted")
            self.assertEqual(receipt["counts"]["accepted"], 2)
            self.assertEqual(receipt["tasks"]["001"]["stage"], "accepted")
            self.assertEqual(receipt["tasks"]["002"]["stage"], "accepted")
            for task_id in ("001", "002"):
                self.assertFalse(
                    (run_dir / f"provider-forged-{task_id}.json").exists()
                )
                report = (
                    run_dir / "artifacts" / task_id / "report.md"
                ).read_text(encoding="utf-8")
                self.assertIn("CONTROL_PLANE_WRITE: denied", report)
                self.assertTrue(
                    (run_dir / "artifacts" / task_id / "acceptance.json").is_file()
                )
                control = json.loads(
                    (
                        run_dir
                        / "artifacts"
                        / task_id
                        / "attempts"
                        / "01"
                        / "control.json"
                    ).read_text(encoding="utf-8")
                )
                pool_flag = control["argv"].index("--pool-size")
                self.assertEqual(control["argv"][pool_flag + 1], "2")
                owns = json.loads(
                    (run_dir / "artifacts" / task_id / "owns-check.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(owns["scope"], "run")
                self.assertEqual(owns["scope_task_ids"], ["001", "002"])
            self.assertTrue(
                (run_dir / "controller" / "lane-bg.supervisor.log").is_file()
            )


if __name__ == "__main__":
    unittest.main()

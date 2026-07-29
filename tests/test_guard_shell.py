import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HOOK = Path(__file__).parents[1] / "hooks" / "guard_shell.py"
POST_HOOK = Path(__file__).parents[1] / "hooks" / "guard_code_quality.py"


def run_payload(
    payload: object,
    *,
    client: str = "claude",
    hook: Path = HOOK,
    raw: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "AGENT_HOOK_CLIENT": client}
    return subprocess.run(
        [str(hook)],
        input=str(payload) if raw else json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def run_hook(agent_type: str, command: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "agent_type": agent_type,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    env = {**os.environ, "AGENT_HOOK_CLIENT": "claude"}
    return subprocess.run(
        [str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def run_edit_hook(
    agent_type: str,
    file_path: str,
    tool_name: str = "Write",
    cwd: str = "/srv/app",
) -> subprocess.CompletedProcess[str]:
    payload = {
        "agent_type": agent_type,
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
        "cwd": cwd,
    }
    return run_payload(payload)


class GuardShellTest(unittest.TestCase):
    def test_dev_orchestrator_must_dispatch_supervisor(self) -> None:
        for command in (
            "run-controller start --run-dir /tmp/run",
            "until /home/ubuntu/.agents/bin/run-controller status --run-dir /tmp/run; do :; done",
            "validate && run-controller watch --run-dir /tmp/run --timeout 240",
        ):
            with self.subTest(command=command):
                result = run_hook("dev-orchestrator", command)
                self.assertEqual(result.returncode, 2)
                denial = json.loads(result.stdout)
                self.assertEqual(
                    denial["hookSpecificOutput"]["permissionDecision"], "deny"
                )
                self.assertIn("Agent(run-supervisor)", denial["reason"])

        self.assertEqual(
            run_hook(
                "run-supervisor",
                "run-controller start --run-dir /tmp/run",
            ).returncode,
            0,
        )
        self.assertEqual(
            run_hook("dev-orchestrator", "run-validate --phase pre-dispatch").returncode,
            0,
        )

    def test_dev_orchestrator_keeps_read_only_and_delivery_commands(self) -> None:
        for command in (
            "rg -n demo apps packages",
            "git status --short && git diff --stat",
            "docker logs selfystudio-worker-1 --since 10m | tail -20",
            "docker exec db psql -c 'SELECT id FROM jobs LIMIT 1'",
            "npm -w apps/api run typecheck",
            "npm -w apps/api run test",
            "cat .agents/runs/demo/controller.json",
            "jq . .agents/runs/demo/events.jsonl",
            "lane-stall-check /srv/app --minutes 5",
            "run-init /srv/app demo && run-validate --phase pre-dispatch --run-dir /srv/app/.agents/runs/demo",
            "wt-merge-main /srv/app demo && git push origin main",
        ):
            with self.subTest(command=command):
                self.assertEqual(
                    run_hook("dev-orchestrator", command).returncode,
                    0,
                )

    def test_dev_orchestrator_must_delegate_mutating_shell(self) -> None:
        for command in (
            "npm ci",
            "npm run deploy",
            "project-onboard . --full",
            "bash -c 'npm install'",
            "rm -rf node_modules",
            "mv src/a.ts src/b.ts",
            "pkill -f 'npm ci'",
            "docker restart selfystudio-bot-thin-1",
            "docker exec app env sh -c 'touch /tmp/pwned'",
            "systemctl --user restart lane-board.service",
            "docker exec db psql -c \"UPDATE jobs SET status = 'done'\"",
            "psql postgresql://localhost/app",
            "psql -f scripts/fix.sql",
            "curl --request=POST https://example.test/restart",
            "curl -XPOST https://example.test/restart",
            "curl --json '{}' https://example.test/restart",
            "curl -dpayload https://example.test/restart",
            "curl --data-raw=payload https://example.test/restart",
            "curl --json={} https://example.test/restart",
            "curl --output=/tmp/response https://example.test",
            "find . -fprint /tmp/files",
            "sort -o /tmp/files input.txt",
            "ruff check --fix .",
            "git branch -D main",
            "git -c core.hooksPath=/dev/null commit -m bypass",
            "cat <<'EOF' > src/fix.ts\nexport const fixed = true\nEOF",
            "printf x >> src/fix.ts",
            "tee src/fix.ts",
            "sed -i 's/a/b/' src/fix.ts",
            "sed --in-place 's/a/b/' src/fix.ts",
            "python3 -c \"from pathlib import Path; Path('src/fix.ts').write_text('x')\"",
            "node -e \"require('fs').writeFileSync('src/fix.ts','x')\"",
            "nohup sleep 60 &",
            "lane-ctl start --run-dir /tmp/r --task-file /tmp/t.yaml --project-cwd /tmp",
            "lane-ctl accept --run-dir /tmp/r --task-id 001",
        ):
            with self.subTest(command=command):
                result = run_hook("dev-orchestrator", command)
                self.assertEqual(result.returncode, 2)
                denial = json.loads(result.stdout)
                self.assertIn("delegate", denial["reason"].lower())

        self.assertEqual(run_hook("worker-coder", "npm ci").returncode, 0)

    def test_dev_orchestrator_can_only_edit_control_plane_documents(self) -> None:
        for path in (
            "/srv/app/.agents/runs/demo/tasks/001.yaml",
            "/srv/app/.agents/runs/demo/PLAN.md",
            "/srv/app/.agents/runs/demo/STATUS.md",
            "/srv/app/.agents/runs/demo/merge.json",
            "/srv/app/.agents/todos/idea.md",
            "/srv/app/.agents/findings/foo.json",
            "/srv/app/.agents/session-log/INDEX.md",
            "/srv/app/PROGRESS.md",
            "/srv/app/LESSONS.md",
            "/srv/app/docs/plans/demo.md",
            "docs/plans/demo.md",
            "/tmp/demo.md",
        ):
            with self.subTest(path=path):
                self.assertEqual(run_edit_hook("dev-orchestrator", path).returncode, 0)

        for path in (
            "/srv/app/src/fix.ts",
            "/srv/app/.agents/runs/demo/fix.sh",
            "/srv/app/.agents/runs/demo/tasks/fix.py",
            "/srv/app/.agents/runs/demo/controller.json",
            "/srv/app/.agents/runs/demo/events.jsonl",
            "/srv/app/.agents/runs/demo/sessions.json",
            "/srv/app/.agents/runs/demo/artifacts/001/state.json",
            "/srv/app/.agents/runs/demo/controller/lane-bg.pid",
            "/srv/app/docs/plans/../../src/evil.md",
        ):
            with self.subTest(path=path):
                self.assertEqual(run_edit_hook("dev-orchestrator", path).returncode, 2)

        notebook = {
            "agent_type": "dev-orchestrator",
            "tool_name": "NotebookEdit",
            "tool_input": {"notebook_path": "/srv/app/src/analysis.ipynb"},
            "cwd": "/srv/app",
        }
        self.assertEqual(run_payload(notebook).returncode, 2)

    def test_real_client_payload_shapes_enforce_the_same_shell_policy(self) -> None:
        fixtures = (
            (
                "claude",
                "claude",
                {
                    "agent_type": "dev-orchestrator",
                    "tool_name": "Bash",
                    "tool_input": {"command": "npm ci"},
                },
            ),
            (
                "codex",
                "codex",
                {
                    "agent_type": "dev-orchestrator",
                    "toolCall": {
                        "name": "shell",
                        "arguments": json.dumps({"command": "npm ci"}),
                    },
                },
            ),
            (
                "grok",
                "grok",
                {
                    "agent_type": "dev-orchestrator",
                    "hookEventName": "pre_tool_use",
                    "toolCall": {
                        "name": "run_terminal_command",
                        "args": json.dumps({"command": "npm ci"}),
                    },
                },
            ),
        )
        for label, client, payload in fixtures:
            with self.subTest(client=label):
                self.assertEqual(run_payload(payload, client=client).returncode, 2)

    def test_malformed_pretooluse_payloads_fail_closed(self) -> None:
        malformed = (
            ("invalid-json", "{"),
            ("json-list", "[]"),
            ("json-string", '"payload"'),
            ("empty", ""),
        )
        for label, raw in malformed:
            with self.subTest(payload=label):
                result = run_payload(raw, raw=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("malformed", json.loads(result.stdout)["reason"].lower())

        malformed_arguments = {
            "agent_type": "dev-orchestrator",
            "toolCall": {"name": "shell", "arguments": "{not-json"},
        }
        self.assertEqual(run_payload(malformed_arguments, client="codex").returncode, 2)

    def test_pm_edit_paths_are_canonicalized_from_payload_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            outside = Path(tmp) / "outside"
            (project / "docs" / "plans").mkdir(parents=True)
            outside.mkdir()
            (project / "docs" / "plans" / "escape").symlink_to(
                outside, target_is_directory=True
            )

            allowed = (
                "docs/plans/plan.md",
                "./docs/plans/nested/plan.yaml",
                str(project / "docs" / "plans" / "absolute.md"),
            )
            denied = (
                "docs/plans/../../src/evil.md",
                "docs/plans/escape/evil.md",
                str(project / "docs" / "plans" / "escape" / "absolute-evil.md"),
                "docs/plans/evil\0.md",
                "/etc/docs/plans/lookalike.md",
            )
            for path in allowed:
                with self.subTest(path=path):
                    self.assertEqual(
                        run_edit_hook("dev-orchestrator", path, cwd=str(project)).returncode,
                        0,
                    )
            for path in denied:
                with self.subTest(path=path):
                    self.assertEqual(
                        run_edit_hook("dev-orchestrator", path, cwd=str(project)).returncode,
                        2,
                    )

    def test_malformed_posttooluse_payload_remains_nonblocking(self) -> None:
        self.assertEqual(
            run_payload("{", hook=POST_HOOK, raw=True).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()

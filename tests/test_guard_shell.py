import json
import os
import subprocess
import unittest
from pathlib import Path


HOOK = Path(__file__).parents[1] / "hooks" / "guard_shell.py"


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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "bin" / "agents-doctor"


class AgentsDoctorTest(unittest.TestCase):
    def test_grok_routing_names_read_only_lane_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [str(DOCTOR), "--apply", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("fast_write: grok  # agent: run-supervisor", profile)
            self.assertIn("main_write: grok  # agent: run-supervisor", profile)
            self.assertNotIn("agent: grok-implementer", profile)


if __name__ == "__main__":
    unittest.main()

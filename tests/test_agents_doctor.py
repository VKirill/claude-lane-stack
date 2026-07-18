from __future__ import annotations

import os
import subprocess
import sys
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
            for name in ("claude", "grok", "codex", "bwrap"):
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

    def test_installed_grok_without_bubblewrap_is_not_routed_as_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to("/usr/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(payload["profile"], "claude-codex")
            self.assertIn("bubblewrap is required", " ".join(payload["notes"]))

    def test_installed_but_inoperable_bubblewrap_disables_grok_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to("/usr/bin/bash")
            for name in ("claude", "grok", "codex"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)
            bwrap = fake_bin / "bwrap"
            bwrap.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            bwrap.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = __import__("json").loads(result.stdout)
            self.assertTrue(payload["tools"]["bubblewrap"]["present"])
            self.assertFalse(payload["tools"]["bubblewrap"]["operational"])
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(
                payload["tools"]["grok"]["unavailable_reason"],
                "bubblewrap probe failed",
            )


if __name__ == "__main__":
    unittest.main()

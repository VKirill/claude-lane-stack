from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_BG = ROOT / "bin" / "lane-bg"


class LaneBgTest(unittest.TestCase):
    def wait_exit(self, artifact: Path, timeout: float = 10) -> int:
        exit_file = artifact / "lane-bg.exit"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if exit_file.is_file():
                return int(exit_file.read_text(encoding="utf-8").strip())
            time.sleep(0.05)
        self.fail(f"lane-bg did not write {exit_file}")

    def test_nohup_backend_remains_available_for_hermetic_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "nohup"
            env = os.environ.copy()
            env["LANE_BG_BACKEND"] = "nohup"
            result = subprocess.run(
                [
                    str(LANE_BG),
                    "--dir",
                    str(artifact),
                    "--label",
                    "test-nohup",
                    "--",
                    "/bin/bash",
                    "-c",
                    "exit 7",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.wait_exit(artifact), 7)
            self.assertGreater(
                int((artifact / "lane-bg.pid").read_text(encoding="utf-8")), 1
            )
            self.assertIn("backend=nohup", (artifact / "lane-bg.meta").read_text())

    @unittest.skipUnless(
        subprocess.run(
            ["systemctl", "--user", "show-environment"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0,
        "user systemd manager is unavailable",
    )
    def test_auto_backend_uses_transient_user_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "systemd"
            env = os.environ.copy()
            env.pop("LANE_BG_BACKEND", None)
            result = subprocess.run(
                [
                    str(LANE_BG),
                    "--dir",
                    str(artifact),
                    "--label",
                    "test-systemd",
                    "--",
                    "/bin/bash",
                    "-c",
                    "sleep 0.2; exit 9",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.wait_exit(artifact), 9)
            self.assertGreater(
                int((artifact / "lane-bg.pid").read_text(encoding="utf-8")), 1
            )
            self.assertIn("backend=systemd", (artifact / "lane-bg.meta").read_text())

            (artifact / "lane-bg.pid").write_text("999999\n", encoding="utf-8")
            (artifact / "lane-bg.exit").unlink()
            second = subprocess.run(
                [
                    str(LANE_BG),
                    "--dir",
                    str(artifact),
                    "--label",
                    "test-systemd-retry",
                    "--",
                    "/bin/bash",
                    "-c",
                    "sleep 0.2; exit 0",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotIn("pid=999999", second.stdout)
            self.assertNotEqual(
                int((artifact / "lane-bg.pid").read_text(encoding="utf-8")),
                999999,
            )
            self.assertEqual(self.wait_exit(artifact), 0)


if __name__ == "__main__":
    unittest.main()

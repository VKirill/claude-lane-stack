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
    def test_grok_is_preferred_and_agy_requires_gemini_36(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            (fake_bin / "python3").symlink_to(sys.executable)
            (fake_bin / "bash").symlink_to("/usr/bin/bash")
            for name in ("claude", "grok", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                executable.chmod(0o755)
            agy = fake_bin / "agy"
            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.6-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo agy-writer && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            agy.chmod(0o755)

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
            self.assertTrue(payload["tools"]["agy"]["present"])
            self.assertEqual(payload["lanes"]["fast_write"], "grok")

            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.5-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo agy-writer && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            missing = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            missing_payload = __import__("json").loads(missing.stdout)
            self.assertFalse(missing_payload["tools"]["agy"]["present"])
            self.assertEqual(
                missing_payload["tools"]["agy"]["unavailable_reason"],
                "gemini-3.6-flash-high unavailable",
            )

            agy.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"${1:-}\" == models ]] && echo gemini-3.6-flash-high && exit 0\n"
                "[[ \"${1:-}\" == agents ]] && echo consult && exit 0\n"
                "echo 'agy 1.1.5'\n",
                encoding="utf-8",
            )
            missing_agent = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            missing_agent_payload = __import__("json").loads(missing_agent.stdout)
            self.assertFalse(missing_agent_payload["tools"]["agy"]["present"])
            self.assertEqual(
                missing_agent_payload["tools"]["agy"]["unavailable_reason"],
                "agy-writer agent unavailable",
            )

    def test_bubblewrap_probe_matches_lane_network_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            args_log = root / "bwrap-args.log"
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
            bwrap.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$BWRAP_ARGS_LOG\"\n",
                encoding="utf-8",
            )
            bwrap.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = str(fake_bin)
            env["BWRAP_ARGS_LOG"] = str(args_log)
            result = subprocess.run(
                [str(DOCTOR), "--json", str(repo)],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            arguments = args_log.read_text(encoding="utf-8").splitlines()
            self.assertIn("--unshare-ipc", arguments)
            run_tmpfs = arguments.index("--tmpfs")
            self.assertEqual(arguments[run_tmpfs + 1], "/run")
            resolver_target = Path("/etc/resolv.conf").resolve(strict=True)
            if resolver_target.is_relative_to(Path("/run")):
                self.assertIn(str(resolver_target), arguments)
            self.assertIn("/etc/resolv.conf", " ".join(arguments))

    def test_resolver_probe_failure_disables_grok_writer(self) -> None:
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
            bwrap.write_text(
                "#!/usr/bin/env bash\n"
                "[[ \"$*\" == *'/etc/resolv.conf'* ]] && exit 1\n"
                "exit 0\n",
                encoding="utf-8",
            )
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
            self.assertTrue(payload["tools"]["bubblewrap"]["operational"])
            self.assertFalse(
                payload["tools"]["bubblewrap"]["resolver_operational"]
            )
            self.assertFalse(payload["tools"]["grok"]["present"])
            self.assertEqual(payload["profile"], "claude-codex")
            self.assertEqual(
                payload["tools"]["grok"]["unavailable_reason"],
                "bubblewrap resolver unavailable",
            )

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
                [str(DOCTOR), "--apply", "--writer-provider", "grok", str(repo)],
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

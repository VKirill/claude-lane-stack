from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_apply_opencode_writer_writes_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "opencode", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "opencode",
                    "--writer-agent",
                    "wiki-writer",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: opencode  # agent: run-supervisor", profile)
            self.assertIn("provider: opencode", profile)
            self.assertIn("agent: wiki-writer", profile)

    def test_apply_codex_writer_is_luna_max_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            result = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "codex",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("main_write: codex", profile)
            self.assertIn("provider: codex", profile)
            self.assertIn("model: gpt-5.6-luna", profile)
            self.assertIn("reasoning_effort: max", profile)
            self.assertIn("workspace:", profile)
            self.assertIn("mode: auto", profile)
            self.assertIn("session_max_tasks: 10", profile)
            self.assertIn("ui:", profile)
            self.assertIn("language: en", profile)

            in_place = subprocess.run(
                [
                    str(DOCTOR),
                    "--apply",
                    "--writer-provider",
                    "codex",
                    "--workspace-mode",
                    "in_place",
                    "--session-max-tasks",
                    "1",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(in_place.returncode, 0, in_place.stderr + in_place.stdout)
            profile2 = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("mode: in_place", profile2)
            self.assertIn("session_max_tasks: 1", profile2)

    def test_setup_writes_routing_and_night_shift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_bin = root / "bin"
            repo = root / "repo"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "qwen", "kimi", "codex", "bwrap"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/usr/bin/env bash\necho 'fake 1.0'\n", encoding="utf-8"
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
            off = subprocess.run(
                [
                    str(DOCTOR),
                    "setup",
                    str(repo),
                    "--yes",
                    "--writer-provider",
                    "qwen",
                    "--night-review",
                    "off",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(off.returncode, 0, off.stderr + off.stdout)
            profile = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            night = (repo / ".agents" / "night-shift.yaml").read_text(encoding="utf-8")
            self.assertIn("main_write: qwen", profile)
            self.assertIn("enabled: false", night)

            on = subprocess.run(
                [
                    str(DOCTOR),
                    "setup",
                    str(repo),
                    "--yes",
                    "--writer-provider",
                    "qwen",
                    "--night-review",
                    "on",
                    "--max-fix-tasks",
                    "7",
                    "--no-auto-merge",
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(on.returncode, 0, on.stderr + on.stdout)
            night = (repo / ".agents" / "night-shift.yaml").read_text(encoding="utf-8")
            self.assertIn("enabled: true", night)
            self.assertIn("provider: qwen", night)
            self.assertIn("max_fix_tasks: 7", night)
            self.assertIn("auto_merge: false", night)

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


class DoctorTuiCatalogTest(unittest.TestCase):
    def test_grok_46_is_selectable(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        self.assertIn("grok-4.6", tui.WRITER_MODELS["grok"])
        self.assertIn("opencode", tui.ALL_AGENTS)
        self.assertIn("alibaba-token-plan/qwen3.8-max-preview", tui.WRITER_MODELS["opencode"])
        self.assertEqual(tui.sidebar_hit(2), 0)
        self.assertEqual(tui.sidebar_hit(8), 6)
        self.assertEqual(tui.sidebar_hit(9), 7)
        self.assertIsNone(tui.sidebar_hit(1))
        self.assertIsNone(tui.sidebar_hit(10))
        self.assertIn("info", tui.TAB_IDS)
        self.assertEqual(tui.TAB_IDS[-1], "apply")
        import agents_doctor_tui_i18n as i18n  # noqa: E402

        self.assertIn("tab_info", i18n.STRINGS["en"])
        self.assertIn("tab_info", i18n.STRINGS["ru"])
        self.assertIn("/project-onboard", i18n.STRINGS["en"]["info_start"])
        self.assertIn("project-onboard .", i18n.STRINGS["ru"]["info_cmds"])
        self.assertEqual(tui.pick_window(10, 0, 5), (0, 5))
        self.assertEqual(tui.pick_window(10, 9, 5), (5, 10))
        start, end = tui.pick_window(80, 40, 12)
        self.assertLessEqual(end - start, 12)
        self.assertLessEqual(start, 40)
        self.assertGreater(end, 40)
        for slug in (
            "cursor-grok-4.6-low",
            "cursor-grok-4.6-low-fast",
            "cursor-grok-4.6-medium",
            "cursor-grok-4.6-medium-fast",
            "cursor-grok-4.6-high",
            "cursor-grok-4.6-high-fast",
            "cursor-grok-4.6-xhigh",
            "cursor-grok-4.6-xhigh-fast",
        ):
            self.assertIn(slug, tui.CURSOR_MODEL_FALLBACK)

    def test_opencode_catalog_refreshes_live(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        fallback = list(tui.WRITER_MODELS["opencode"])
        tui._OPENCODE_LIVE["models"] = ["stale/provider"]
        tui._OPENCODE_LIVE["agents"] = ["stale-agent"]
        with patch.object(
            tui,
            "_fetch_opencode_models",
            return_value=(
                ["fresh/model"],
                {"fresh/model": ["none", "low", "xhigh"]},
            ),
        ), patch.object(
            tui, "_fetch_opencode_agents", return_value=["fresh-agent"]
        ):
            tui.refresh_opencode_catalog()
        self.assertEqual(tui._probe_opencode_models(), ["fresh/model"])
        self.assertEqual(tui._probe_opencode_agents(), ["fresh-agent"])
        self.assertEqual(
            tui._efforts_for("opencode", "fresh/model"),
            ["none", "low", "xhigh"],
        )
        self.assertEqual(tui._efforts_for("opencode", "missing/model"), [])
        self.assertEqual(tui.WRITER_MODELS["opencode"], fallback)
        tui._OPENCODE_LIVE["models"] = None
        tui._OPENCODE_LIVE["agents"] = None
        tui._OPENCODE_LIVE["variants"] = None

    def test_parse_opencode_models_verbose_variants(self) -> None:
        sys.path.insert(0, str(ROOT / "bin"))
        import agents_doctor_tui as tui  # noqa: E402

        text = (
            "prov/has-var\n"
            '{"id":"has-var","providerID":"prov","variants":'
            '{"low":{},"max":{}}}\n'
            "prov/no-var\n"
            '{"id":"no-var","providerID":"prov","variants":{}}\n'
            "prov/happyhorse-1.1-i2v\n"
            '{"id":"happyhorse-1.1-i2v","providerID":"prov","variants":{"low":{}}}\n'
        )
        models, variants = tui.parse_opencode_models_verbose(text)
        self.assertEqual(models, ["prov/has-var", "prov/no-var"])
        self.assertEqual(variants["prov/has-var"], ["low", "max"])
        self.assertEqual(variants["prov/no-var"], [])
        self.assertNotIn("prov/happyhorse-1.1-i2v", models)

    def test_harness_opencode_agents_exist(self) -> None:
        root = ROOT / "profiles" / "opencode" / "agents"
        for name in ("lane-writer", "lane-critic", "lane-reviewer"):
            text = (root / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("mode: all", text)
            self.assertIn("task: deny", text)


if __name__ == "__main__":
    unittest.main()

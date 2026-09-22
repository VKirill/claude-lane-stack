from __future__ import annotations

import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
from routing_profile import load_routing_profile, resolve_emergency_writer


class EmergencyWriterTest(unittest.TestCase):
    def test_save_roundtrip_preserves_independent_writer(self) -> None:
        doctor = runpy.run_path(str(ROOT / "bin/agents-doctor"))
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            settings = {"provider": "codex", "model": "gpt-6-luna",
                        "reasoning_effort": "high", "service_tier": "fast"}
            args = (repo, {}, "claude-grok", {"main_write": "grok", "emergency_write": "grok"}, [])
            doctor["write_outputs"](*args, quiet=True)
            self.assertEqual(resolve_emergency_writer(repo), settings)
            doctor["write_outputs"](*args, emergency_writer=settings, quiet=True)
            doctor["write_outputs"](*args, quiet=True)
            profile = load_routing_profile(repo)
            self.assertEqual(resolve_emergency_writer(repo), settings)
            self.assertEqual(profile["lanes"]["main_write"], "grok")
            self.assertEqual(profile["lanes"]["emergency_write"], "codex")
            caps = json.loads((repo / ".agents/capabilities.json").read_text())
            self.assertEqual(caps["emergency_writer"], settings)

    def test_role_launches_selected_provider_with_speed(self) -> None:
        role = (ROOT / "plugins/lane-stack/agents/emergency-writer.md").read_text()
        script = "\n".join(re.findall(r"```bash\n(.*?)```", role, re.S))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "bin"
            fake.mkdir()
            for name, body in {
                "lane-mode-check": "#!/bin/sh\nexit 0\n",
                "lane-bg": "#!/usr/bin/env python3\nimport json, os, sys\nfrom pathlib import Path\nPath(os.environ['ARGV_LOG']).write_text(json.dumps(sys.argv[1:]))\n",
            }.items():
                p = fake / name
                p.write_text(body)
                p.chmod(0o755)
            project = root / "repo"
            (project / ".agents").mkdir(parents=True)
            task = root / "task.yaml"
            task.write_text("id: 003\n")
            env = {**os.environ, "PROJECT_CWD": str(project), "TASK_FILE": str(task),
                   "ARTIFACT_DIR": str(root / "artifacts"), "RUN_DIR": str(root / "run"),
                   "TASK_ID": "003", "MODE": "start", "ARGV_LOG": str(root / "argv.json"),
                   "PYTHONPATH": str(ROOT / "bin")}
            for key in ("EMERGENCY_PROVIDER", "EMERGENCY_MODEL", "EMERGENCY_REASONING",
                        "EMERGENCY_SERVICE_TIER", "CODEX_MODEL", "CODEX_REASONING"):
                env.pop(key, None)
            script = script.replace("$HOME/.agents/bin", str(fake))
            for provider, model, tier in (("codex", "gpt-6-luna", "fast"),
                                          ("opencode", "custom/model", "standard")):
                (project / ".agents/routing.profile.yaml").write_text(
                    f"lanes:\n  main_write: grok\nemergency_writer:\n  provider: {provider}\n"
                    f"  model: {model}\n  reasoning_effort: high\n  service_tier: {tier}\n")
                out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr)
                argv = json.loads((root / "argv.json").read_text())
                self.assertIn("lane-session", argv)
                for flag, value in (("--provider", provider), ("--model", model),
                                    ("--reasoning-effort", "high"), ("--service-tier", tier)):
                    self.assertEqual(argv[argv.index(flag) + 1], value)

            marker = root / "artifacts/started.marker"
            marker.unlink()
            (fake / "lane-bg").write_text("#!/bin/sh\nexit 7\n")
            out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("FAILED emergency writer launch failed", out.stdout)
            self.assertFalse(marker.exists())

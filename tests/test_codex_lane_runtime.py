from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
loader = importlib.machinery.SourceFileLoader("codex_lane_runtime", str(ROOT / "bin/lane-session"))
spec = importlib.util.spec_from_loader(loader.name, loader)
runtime = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = runtime
loader.exec_module(runtime)


class CodexLaneRuntimeTest(unittest.TestCase):
    def test_worker_protocol_is_loaded_without_host_plugins(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex/auth.json").write_text("{}")
            with patch.object(Path, "home", return_value=home), patch.dict(
                os.environ, {"CODEX_HOME": str(home / ".codex")}
            ), patch.object(runtime.tempfile, "gettempdir", return_value=tmp):
                scratch = runtime.prepare_codex_home(
                    "codex", run_dir=Path(tmp) / ".agents/runs/probe", key="writer", reset=True
                )
                expected = ROOT / "plugins/codex-lane/skills/codex-lane-worker/SKILL.md"
                self.assertEqual((scratch / "AGENTS.md").read_bytes(), expected.read_bytes())
                self.assertEqual(list((scratch / "plugins").iterdir()), [])
                self.assertEqual(list((scratch / "skills").iterdir()), [])
                self.assertIn("plugins = false", (scratch / "config.toml").read_text())
                self.assertEqual(runtime.provider_environment("codex")["LANE_CODEX_WORKER"], "1")
                self.assertNotIn("LANE_CODEX_WORKER", runtime.provider_environment("opencode"))


if __name__ == "__main__":
    unittest.main()

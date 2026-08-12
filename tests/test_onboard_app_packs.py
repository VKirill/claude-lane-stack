#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "onboard_app_packs.py"


class OnboardAppPacksTest(unittest.TestCase):
    def test_project_surfaces_and_skeletons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "apps" / "api" / "src").mkdir(parents=True)
            (repo / "apps" / "api" / "package.json").write_text('{"name":"api"}\n', encoding="utf-8")
            (repo / "apps" / "api" / "src" / "x.ts").write_text("export {}\n", encoding="utf-8")
            (repo / "apps" / "worker" / "src").mkdir(parents=True)
            (repo / "apps" / "worker" / "package.json").write_text('{"name":"worker"}\n', encoding="utf-8")
            (repo / "apps" / "worker" / "src" / "x.ts").write_text("export {}\n", encoding="utf-8")
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "API_SURFACE.yaml").write_text(
                "surfaces:\n"
                "  - kind: http\n"
                "    id: GET /ready\n"
                "    path: apps/api/src/server.ts:1\n"
                "  - kind: queue\n"
                "    id: generation\n"
                "    path: apps/worker/src/main.ts:10\n",
                encoding="utf-8",
            )
            env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "HOME": tmp}
            # templates under fake HOME
            tpl = Path(tmp) / ".agents" / "templates" / "app-pack" / "llm"
            tpl.mkdir(parents=True)
            for name, body in (
                ("INDEX.md", "# REPLACE_ME\n"),
                ("ARCHITECTURE.md", "# REPLACE_ME arch\n"),
                ("GOTCHAS.md", "# REPLACE_ME gotchas\n"),
            ):
                (Path(tmp) / ".agents" / "templates" / "app-pack" / name).write_text(body, encoding="utf-8")
            (tpl / "FLOWS.md").write_text("# REPLACE_ME flows\n", encoding="utf-8")
            (Path(tmp) / ".agents" / "templates" / "nested-CLAUDE.md").write_text(
                "# REPLACE_ME\n", encoding="utf-8"
            )

            r = subprocess.run(
                [str(BIN), "prepare", str(repo)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            api_surf = repo / "apps" / "api" / "docs" / "llm" / "API_SURFACE.yaml"
            self.assertTrue(api_surf.is_file())
            text = api_surf.read_text(encoding="utf-8")
            self.assertIn("GET /ready", text)
            self.assertNotIn("generation\n", text.split("surfaces:", 1)[-1][:200] + "x")
            self.assertTrue((repo / "apps" / "api" / "CLAUDE.md").is_file())
            self.assertTrue((repo / "apps" / "worker" / "docs" / "ARCHITECTURE.md").is_file())
            worker_surf = (repo / "apps" / "worker" / "docs" / "llm" / "API_SURFACE.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("generation", worker_surf)


if __name__ == "__main__":
    unittest.main()

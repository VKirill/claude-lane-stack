from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsInitChainTest(unittest.TestCase):
    def test_dry_run_onboards_before_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(
                ["git", "init"], cwd=repo, check=True, capture_output=True
            )
            (repo / "apps" / "web").mkdir(parents=True)
            (repo / "apps" / "web" / "package.json").write_text('{"name":"web"}\n')
            (repo / "apps" / "web" / "CLAUDE.md").write_text("# web\n")
            result = subprocess.run(
                [str(ROOT / "bin" / "docs-init-chain"), str(repo), "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("CHAIN: project-onboard", result.stdout)
            self.assertIn("DRY-RUN: project-onboard", result.stdout)
            self.assertIn("DRY-RUN: docs-maintain-project", result.stdout)
            self.assertNotIn("docs-maintain-project failed", result.stdout)

    def test_onboard_injects_memory_even_on_failed_pass(self) -> None:
        text = (ROOT / "bin" / "project-onboard").read_text(encoding="utf-8")
        self.assertIn("trap '_inject_memory' RETURN", text)
        root = text.find('_onboard_provider_once "$prompt_root"')
        self.assertGreater(root, 0)
        self.assertGreater(text.find("_inject_memory", root), root)

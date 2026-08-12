#!/usr/bin/env python3
"""Smoke: project-onboard default = full pipeline; --seed-only skips model."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "project-onboard"


def _env(tmp: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{ROOT / 'bin'}:{env.get('PATH', '')}"
    env["HOME"] = tmp
    env["ONBOARD_DRY_RUN"] = "1"
    return env


class ProjectOnboardRun(unittest.TestCase):
    def test_help_default_is_one_shot(self) -> None:
        out = subprocess.check_output([str(BIN), "--help"], text=True)
        self.assertIn("project-onboard .", out)
        self.assertIn("--seed-only", out)

    def test_default_runs_fill_dry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"name":"toy"}\n', encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "index.ts").write_text("export {}\n", encoding="utf-8")
            r = subprocess.run(
                [str(BIN), str(repo)],
                cwd=str(ROOT),
                env=_env(tmp),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)
            art = repo / ".agents" / "runs" / "_onboard" / "artifacts" / "001"
            self.assertTrue((art / "prompt.md").is_file(), r.stdout)
            self.assertTrue((art / "dry-run.txt").is_file())

    def test_seed_only_skips_fill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text('{"name":"toy"}\n', encoding="utf-8")
            r = subprocess.run(
                [str(BIN), str(repo), "--seed-only", "--minimal", "--fast"],
                cwd=str(ROOT),
                env=_env(tmp),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)
            art = repo / ".agents" / "runs" / "_onboard" / "artifacts" / "001"
            self.assertFalse((art / "prompt.md").exists())
            self.assertIn("Seed-only", r.stdout)


if __name__ == "__main__":
    unittest.main()

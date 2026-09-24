from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_test_filter import (  # noqa: E402
    affects,
    command_kind,
    discovery_paths,
    git_changed_under,
    lint_argv,
    test_runner_format,
    wrap_verification,
)


class JevTestFilterWrapTest(unittest.TestCase):
    def test_skips_typecheck_and_true(self) -> None:
        self.assertIsNone(test_runner_format(["npm", "run", "typecheck"]))
        self.assertIsNone(test_runner_format(["true"]))
        self.assertEqual(command_kind(["npm", "run", "typecheck"]), "typecheck")
        argv, meta = wrap_verification(["npm", "run", "typecheck"])
        self.assertEqual(argv[0], "npm")
        self.assertTrue(meta.get("full") or meta.get("reason") == "scope-off")

    def test_detects_vitest_node_and_go(self) -> None:
        self.assertEqual(
            test_runner_format(
                [
                    "node",
                    "node_modules/vitest/vitest.mjs",
                    "run",
                    "--root",
                    "apps/admin",
                    "apps/admin/plugins/scenarios/components",
                ]
            ),
            "vitest",
        )
        self.assertEqual(test_runner_format(["node", "--test", "test/cli.test.ts"]), "node")
        self.assertEqual(test_runner_format(["go", "test", "./..."]), "go")
        self.assertEqual(test_runner_format(["npm", "test"]), "auto")

    def test_discovery_skips_root_flag(self) -> None:
        paths = discovery_paths(
            [
                "node",
                "node_modules/vitest/vitest.mjs",
                "run",
                "--root",
                "apps/admin",
                "apps/admin/plugins/scenarios/components",
            ]
        )
        self.assertEqual(paths, ["apps/admin/plugins/scenarios/components"])

    def test_wraps_vitest_when_bin_and_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "jev-test-filter"
            binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            binary.chmod(0o755)
            argv = [
                "node",
                "node_modules/vitest/vitest.mjs",
                "run",
                "--root",
                "apps/admin",
                "apps/admin/x",
            ]
            env = {
                "LANE_JEV_TEST_FILTER": "1",
                "JEV_TEST_FILTER_BIN": str(binary),
                "TYPESAFE_API_KEY": "test-key",
            }
            with patch.dict(os.environ, env, clear=False):
                wrapped, meta = wrap_verification(argv)
            self.assertTrue(meta.get("wrapped"))
            self.assertEqual(wrapped[0], str(binary))
            self.assertEqual(wrapped[1:3], ["--format", "vitest"])
            self.assertIn("apps/admin/x", wrapped)
            self.assertEqual(wrapped[wrapped.index("--exec") + 1], "--")
            self.assertEqual(wrapped[-len(argv) :], argv)

    def test_md_diff_skips_typecheck(self) -> None:
        self.assertFalse(affects("typecheck", "README.md"))
        self.assertTrue(affects("typecheck", "src/foo.ts"))
        self.assertTrue(affects("typecheck", "tsconfig.json"))

    def test_lint_argv_replaces_dot(self) -> None:
        narrowed = lint_argv(["eslint-compat", "."], ["src/a.ts"])
        self.assertEqual(narrowed, ["eslint-compat", "src/a.ts"])
        self.assertIsNone(lint_argv(["npm", "run", "lint"], ["src/a.ts"]))

    def test_git_changed_under_and_skip_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            admin = root / "apps" / "admin"
            admin.mkdir(parents=True)
            (admin / "keep.ts").write_text("export const n = 1\n", encoding="utf-8")
            (root / "README.md").write_text("hi\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            (root / "README.md").write_text("bye\n", encoding="utf-8")
            changed = git_changed_under(admin)
            self.assertEqual(changed, [])
            env = {"LANE_L1_SCOPE": "1"}
            with patch.dict(os.environ, env, clear=False):
                argv, meta = wrap_verification(
                    ["npm", "run", "typecheck"], cwd=admin
                )
            self.assertTrue(meta.get("skip_run"))
            self.assertEqual(argv[0], "npm")
            (admin / "keep.ts").write_text("export const n = 2\n", encoding="utf-8")
            with patch.dict(os.environ, env, clear=False):
                argv, meta = wrap_verification(
                    ["npm", "run", "typecheck"], cwd=admin
                )
            self.assertTrue(meta.get("full"))
            self.assertIn("keep.ts", meta.get("files") or [])

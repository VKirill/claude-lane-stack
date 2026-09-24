from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_test_filter import (  # noqa: E402
    discovery_paths,
    test_runner_format,
    wrap_verification,
)


class JevTestFilterWrapTest(unittest.TestCase):
    def test_skips_typecheck_and_true(self) -> None:
        self.assertIsNone(test_runner_format(["npm", "run", "typecheck"]))
        self.assertIsNone(test_runner_format(["true"]))
        argv, meta = wrap_verification(["npm", "run", "typecheck"])
        self.assertEqual(argv[0], "npm")
        self.assertEqual(meta["skipped"], "not-a-test-runner")

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

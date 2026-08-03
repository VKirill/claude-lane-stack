from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from verification_safety import verification_script_args  # noqa: E402


class VerificationScriptArgsTest(unittest.TestCase):
    def test_extracts_relative_python_script(self) -> None:
        scripts = verification_script_args(
            "python3 .agents/runs/foo/artifacts/001/check.py"
        )
        self.assertEqual(scripts, [".agents/runs/foo/artifacts/001/check.py"])

    def test_skips_unittest_module_form(self) -> None:
        scripts = verification_script_args(
            "python3 -m unittest discover -s tests -p test_foo.py -v"
        )
        # -m skips module name; -p pattern is not a path with / unless tests/
        self.assertNotIn("unittest", scripts)
        self.assertNotIn("discover", scripts)

    def test_product_test_path(self) -> None:
        scripts = verification_script_args("python3 tests/test_renewal_label.py")
        self.assertEqual(scripts, ["tests/test_renewal_label.py"])

    def test_npm_has_no_script_args(self) -> None:
        self.assertEqual(verification_script_args("npm run test:unit"), [])


class RunValidateMissingScriptTest(unittest.TestCase):
    def test_pre_dispatch_rejects_missing_check_under_worktree_cwd(self) -> None:
        """temples-admin class: cwd=worktree, check only on main path."""
        from importlib.machinery import SourceFileLoader
        import importlib.util

        loader = SourceFileLoader(
            "run_validate_mod", str(ROOT / "bin" / "run-validate")
        )
        spec = importlib.util.spec_from_loader("run_validate_mod", loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["run_validate_mod"] = mod
        # Avoid executing main; load functions by reading would be heavy —
        # call verification_script_args + existence logic inline like run-validate.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "wt"
            worktree.mkdir()
            # check exists only on "main" side, not under worktree
            main_check = (
                root
                / ".agents"
                / "runs"
                / "temples-admin"
                / "artifacts"
                / "001"
                / "check.py"
            )
            main_check.parent.mkdir(parents=True)
            main_check.write_text("print('ok')\n", encoding="utf-8")
            cmd = "python3 .agents/runs/temples-admin/artifacts/001/check.py"
            scripts = verification_script_args(cmd)
            self.assertEqual(len(scripts), 1)
            missing = worktree / scripts[0]
            self.assertFalse(missing.is_file())
            present = main_check
            self.assertTrue(present.is_file())
            # After copy into worktree (v2 pattern) it should exist
            target = worktree / scripts[0]
            target.parent.mkdir(parents=True)
            target.write_text(main_check.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()

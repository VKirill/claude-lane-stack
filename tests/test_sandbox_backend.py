"""Unit tests for bin/sandbox_backend.py.

Covers backend selection (LANE_SANDBOX_BACKEND override / sys.platform auto
detection) and the Seatbelt (macOS) SBPL profile generator: rule ordering,
hidden-path deny coverage, control-plane re-lock, readable overrides, and
path quote escaping. Bubblewrap argv construction itself is exercised by
tests/test_lane_session.py, since it lives inline in bin/lane-session and
must stay byte-for-byte identical to its pre-macOS-support behaviour.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

import sandbox_backend  # noqa: E402 - see sys.path setup above


class SelectBackendTest(unittest.TestCase):
    def test_auto_picks_seatbelt_on_darwin(self) -> None:
        self.assertEqual(
            sandbox_backend.select_backend(env={}, platform="darwin"), "seatbelt"
        )

    def test_auto_picks_bubblewrap_elsewhere(self) -> None:
        for plat in ("linux", "linux2", "freebsd13"):
            with self.subTest(platform=plat):
                self.assertEqual(
                    sandbox_backend.select_backend(env={}, platform=plat),
                    "bubblewrap",
                )

    def test_unset_and_auto_are_equivalent(self) -> None:
        self.assertEqual(
            sandbox_backend.select_backend(env={}, platform="darwin"),
            sandbox_backend.select_backend(
                env={"LANE_SANDBOX_BACKEND": "auto"}, platform="darwin"
            ),
        )

    def test_env_override_wins_over_platform(self) -> None:
        self.assertEqual(
            sandbox_backend.select_backend(
                env={"LANE_SANDBOX_BACKEND": "bubblewrap"}, platform="darwin"
            ),
            "bubblewrap",
        )
        self.assertEqual(
            sandbox_backend.select_backend(
                env={"LANE_SANDBOX_BACKEND": "seatbelt"}, platform="linux"
            ),
            "seatbelt",
        )

    def test_override_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            sandbox_backend.select_backend(
                env={"LANE_SANDBOX_BACKEND": "  Seatbelt \n"}, platform="linux"
            ),
            "seatbelt",
        )

    def test_unknown_override_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            sandbox_backend.select_backend(
                env={"LANE_SANDBOX_BACKEND": "none"}, platform="linux"
            )

    def test_there_is_no_unsandboxed_backend(self) -> None:
        # Guard against ever adding a "none"/"off" escape hatch: every known
        # backend name must map to a runtime sandbox profile.
        for backend in sandbox_backend.KNOWN_BACKENDS:
            profile = sandbox_backend.runtime_sandbox_profile(backend)
            self.assertTrue(profile)
        self.assertNotIn("none", sandbox_backend.KNOWN_BACKENDS)
        self.assertNotIn("off", sandbox_backend.KNOWN_BACKENDS)


class RuntimeSandboxProfileTest(unittest.TestCase):
    def test_profiles_are_distinct_and_known(self) -> None:
        bubblewrap = sandbox_backend.runtime_sandbox_profile("bubblewrap")
        seatbelt = sandbox_backend.runtime_sandbox_profile("seatbelt")
        self.assertEqual(bubblewrap, "bubblewrap-workspace")
        self.assertEqual(seatbelt, "seatbelt-workspace")
        self.assertNotEqual(bubblewrap, seatbelt)
        self.assertEqual(
            sandbox_backend.KNOWN_RUNTIME_SANDBOX_PROFILES,
            frozenset({bubblewrap, seatbelt}),
        )

    def test_unknown_backend_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            sandbox_backend.runtime_sandbox_profile("docker")


class BuildSeatbeltProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.cwd = self.root / "worktree"
        self.cwd.mkdir()
        self.control_root = self.root / ".agents"
        self.control_root.mkdir()
        self.other_home = self.root / "home" / ".other-cli"
        self.other_home.mkdir(parents=True)

    def _lines(self, text: str) -> list[str]:
        return [line for line in text.splitlines() if line]

    def test_starts_with_version_and_default_allow_then_deny_write(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(),
        )
        lines = self._lines(text)
        self.assertEqual(lines[0], "(version 1)")
        self.assertEqual(lines[1], "(allow default)")
        self.assertEqual(lines[2], "(deny file-write*)")

    def test_cwd_is_allowed_write_as_subpath(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(),
        )
        self.assertIn(f'(allow file-write* (subpath "{self.cwd}"))', text)

    def test_system_writable_roots_are_always_included(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(),
        )
        for root in ("/private/tmp", "/private/var/folders", "/dev"):
            with self.subTest(root=root):
                self.assertIn(f'(subpath "{root}")', text)

    def test_control_root_write_deny_comes_after_write_allows(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(),
        )
        lines = self._lines(text)
        allow_indexes = [
            i for i, line in enumerate(lines) if line.startswith("(allow file-write*")
        ]
        deny_control_index = lines.index(
            f'(deny file-write* (subpath "{self.control_root}"))'
        )
        self.assertTrue(allow_indexes, "expected at least one allow file-write* rule")
        self.assertGreater(deny_control_index, max(allow_indexes))

    def test_hidden_paths_deny_both_read_and_write_as_subpath(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(self.other_home,),
        )
        self.assertIn(f'(deny file-read* (subpath "{self.other_home}"))', text)
        self.assertIn(f'(deny file-write* (subpath "{self.other_home}"))', text)

    def test_hidden_path_equal_to_provider_state_dir_is_skipped(self) -> None:
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(self.other_home,),
            provider_state_dir=self.other_home,
        )
        self.assertNotIn(str(self.other_home), text)

    def test_nonexistent_hidden_path_is_skipped(self) -> None:
        ghost = self.root / "does-not-exist"
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(ghost,),
        )
        self.assertNotIn(str(ghost), text)

    def test_readable_override_allows_read_after_hidden_deny(self) -> None:
        binary = self.other_home / "codex-provider"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(self.other_home,),
            readable_overrides=(binary,),
        )
        lines = self._lines(text)
        deny_index = lines.index(
            f'(deny file-read* (subpath "{self.other_home}"))'
        )
        allow_index = lines.index(f'(allow file-read* (literal "{binary}"))')
        self.assertGreater(
            allow_index, deny_index, "readable override must come after the deny"
        )

    def test_literal_used_for_files_subpath_used_for_directories(self) -> None:
        a_file = self.other_home / "state.json"
        a_file.write_text("{}", encoding="utf-8")
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(a_file, self.other_home),
        )
        self.assertIn(f'(deny file-read* (literal "{a_file}"))', text)
        self.assertIn(f'(deny file-read* (subpath "{self.other_home}"))', text)

    def test_quotes_and_backslashes_are_escaped(self) -> None:
        tricky = self.root / 'weird "quoted" dir'
        tricky.mkdir()
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd, tricky),
            hidden_paths=(),
        )
        self.assertIn('\\"quoted\\"', text)
        # The profile must remain balanced: every literal/subpath argument is
        # a well-formed double-quoted string once escaping is accounted for.
        unescaped_quotes = text.replace('\\"', "").count('"')
        self.assertEqual(unescaped_quotes % 2, 0)

    def test_symlinked_tmp_resolves_to_canonical_form(self) -> None:
        # Sanity check for the "resolve() so /tmp -> /private/tmp" note in
        # the module docstring; only meaningful where /tmp is actually a
        # symlink (true on macOS, not guaranteed elsewhere).
        if Path("/tmp").resolve() == Path("/tmp"):
            self.skipTest("/tmp is not a symlink on this host")
        text = sandbox_backend.build_seatbelt_profile(
            cwd=self.cwd,
            control_root=self.control_root,
            writable_paths=(self.cwd,),
            hidden_paths=(),
        )
        self.assertIn(str(Path("/tmp").resolve()), text)


@unittest.skipUnless(sys.platform == "darwin", "exercises the real sandbox-exec binary")
class SeatbeltProbeTest(unittest.TestCase):
    def test_seatbelt_binary_is_found_and_operational_on_macos(self) -> None:
        binary = sandbox_backend.seatbelt_binary()
        self.assertEqual(binary, "/usr/bin/sandbox-exec")
        self.assertTrue(sandbox_backend.seatbelt_operational(binary))

    def test_seatbelt_operational_is_false_for_missing_binary(self) -> None:
        self.assertFalse(sandbox_backend.seatbelt_operational(None))
        self.assertFalse(sandbox_backend.seatbelt_operational("/no/such/binary"))


if __name__ == "__main__":
    unittest.main()

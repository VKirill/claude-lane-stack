from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from routing_profile import (  # noqa: E402
    lane_matches_profile,
    load_routing_profile,
    resolve_writer,
)


class RoutingProfileTest(unittest.TestCase):
    def test_resolve_from_agents_doctor_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                textwrap.dedent(
                    """\
                    pm: claude
                    profile: full
                    lanes:
                      main_write: codex
                      fast_write: codex
                    writer:
                      provider: codex
                      model: gpt-5.6-luna
                      reasoning_effort: max
                    """
                ),
                encoding="utf-8",
            )
            resolved = resolve_writer(root, provider_explicit=False)
            self.assertEqual(resolved["provider"], "codex")
            self.assertEqual(resolved["model"], "gpt-5.6-luna")
            self.assertEqual(resolved["reasoning_effort"], "max")
            self.assertTrue(lane_matches_profile("codex", "codex"))
            self.assertFalse(lane_matches_profile("kimi", "codex"))

            # worktree under repo still finds profile
            wt = root / ".worktrees" / "feature"
            wt.mkdir(parents=True)
            nested = resolve_writer(wt, provider_explicit=False)
            self.assertEqual(nested["provider"], "codex")

            # explicit CLI wins
            forced = resolve_writer(
                root, provider="qwen", provider_explicit=True
            )
            self.assertEqual(forced["provider"], "qwen")

    def test_missing_profile_falls_back_to_kimi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_writer(Path(tmp), provider_explicit=False)
            self.assertEqual(resolved["provider"], "kimi")


if __name__ == "__main__":
    unittest.main()

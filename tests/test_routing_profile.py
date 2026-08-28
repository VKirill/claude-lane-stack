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
    resolve_agy_effort,
    resolve_cursor_model,
    resolve_session_max_tasks,
    resolve_workspace,
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

    def test_resolve_workspace_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            profile = root / ".agents" / "routing.profile.yaml"
            profile.write_text(
                textwrap.dedent(
                    """\
                    workspace:
                      mode: in_place
                      worktree_min_score: 4
                      worktree_on_multi_write: true
                    """
                ),
                encoding="utf-8",
            )
            ws = resolve_workspace(root, score=9, write_task_count=3)
            self.assertEqual(ws["mode_setting"], "in_place")
            self.assertEqual(ws["effective"], "in_place")

            profile.write_text(
                textwrap.dedent(
                    """\
                    workspace:
                      mode: worktree
                    """
                ),
                encoding="utf-8",
            )
            ws = resolve_workspace(root, score=0, write_task_count=1)
            self.assertEqual(ws["effective"], "worktree")

            profile.write_text(
                textwrap.dedent(
                    """\
                    workspace:
                      mode: auto
                      worktree_min_score: 4
                      worktree_on_multi_write: true
                    """
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                resolve_workspace(root, score=1, write_task_count=1)["effective"],
                "in_place",
            )
            self.assertEqual(
                resolve_workspace(root, score=4, write_task_count=1)["effective"],
                "worktree",
            )
            self.assertEqual(
                resolve_workspace(root, score=1, write_task_count=2)["effective"],
                "worktree",
            )

    def test_resolve_session_max_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_session_max_tasks(root), 10)
            (root / ".agents").mkdir()
            profile = root / ".agents" / "routing.profile.yaml"
            profile.write_text(
                "workspace:\n  session_max_tasks: 1\n", encoding="utf-8"
            )
            self.assertEqual(resolve_session_max_tasks(root), 1)
            profile.write_text(
                "workspace:\n  session_max_tasks: 99\n", encoding="utf-8"
            )
            self.assertEqual(resolve_session_max_tasks(root), 10)
            ws = resolve_workspace(root, score=0, write_task_count=1)
            self.assertEqual(ws["session_max_tasks"], 10)

    def test_resolve_cursor_model_fast_toggle(self) -> None:
        self.assertEqual(
            resolve_cursor_model("cursor-grok-4.5-high", service_tier="fast"),
            "cursor-grok-4.5-high-fast",
        )
        self.assertEqual(
            resolve_cursor_model("cursor-grok-4.5-high-fast", service_tier="standard"),
            "cursor-grok-4.5-high",
        )
        self.assertEqual(
            resolve_cursor_model("cursor-grok-4.6-high", service_tier="fast"),
            "cursor-grok-4.6-high-fast",
        )
        self.assertEqual(
            resolve_cursor_model("cursor-grok-4.6-xhigh-fast", service_tier="standard"),
            "cursor-grok-4.6-xhigh",
        )
        self.assertEqual(
            resolve_cursor_model("composer-2.5-fast", service_tier="fast"),
            "composer-2.5-fast",
        )

    def test_resolve_writer_applies_cursor_service_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                textwrap.dedent(
                    """\
                    lanes:
                      main_write: cursor
                    writer:
                      provider: cursor
                      model: cursor-grok-4.5-high
                      reasoning_effort: medium
                      service_tier: fast
                    """
                ),
                encoding="utf-8",
            )
            resolved = resolve_writer(root, provider_explicit=False)
            self.assertEqual(resolved["provider"], "cursor")
            self.assertEqual(resolved["service_tier"], "fast")
            self.assertEqual(resolved["model"], "cursor-grok-4.5-high-fast")

    def test_resolve_writer_opencode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                textwrap.dedent(
                    """\
                    lanes:
                      main_write: opencode
                    writer:
                      provider: opencode
                      model: alibaba-token-plan/qwen3.8-max-preview
                      reasoning_effort: medium
                      agent: build
                    """
                ),
                encoding="utf-8",
            )
            resolved = resolve_writer(root, provider_explicit=False)
            self.assertEqual(resolved["provider"], "opencode")
            self.assertEqual(
                resolved["model"], "alibaba-token-plan/qwen3.8-max-preview"
            )
            self.assertEqual(resolved["reasoning_effort"], "medium")
            self.assertEqual(resolved["profile"]["writer"]["agent"], "build")

    def test_resolve_agy_effort_suffix_wins(self) -> None:
        cases = (
            ("gemini-3.7-flash-low", "high", "low"),
            ("gemini-3.7-flash-low", "medium", "low"),
            ("gemini-3.7-flash-low", "low", "low"),
            ("gemini-3.7-flash-medium", "high", "medium"),
            ("gemini-3.7-flash-medium", "low", "medium"),
            ("gemini-3.7-flash-medium", "medium", "medium"),
            ("gemini-3.7-flash-high", "low", "high"),
            ("gemini-3.7-flash-high", "medium", "high"),
            ("gemini-3.7-flash-high", "high", "high"),
            ("gemini-3.6-flash-medium", "high", "medium"),
            ("claude-sonnet-4-6", "low", "low"),
            ("claude-sonnet-4-6", "medium", "medium"),
            ("claude-sonnet-4-6", "high", "high"),
            ("claude-sonnet-4-6", "", "high"),
            ("gemini-3.7-flash-xhigh", "low", "high"),
            ("gpt-oss-120b-medium", "", "medium"),
        )
        for model, incoming, expected in cases:
            self.assertEqual(
                resolve_agy_effort(model, incoming),
                expected,
                f"{model!r} + {incoming!r}",
            )

    def test_resolve_writer_agy_aligns_effort_to_model_suffix(self) -> None:
        for model, yaml_effort, expected in (
            ("gemini-3.7-flash-low", "high", "low"),
            ("gemini-3.7-flash-medium", "low", "medium"),
            ("gemini-3.7-flash-high", "medium", "high"),
        ):
            with self.subTest(model=model):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / ".agents").mkdir()
                    (root / ".agents" / "routing.profile.yaml").write_text(
                        textwrap.dedent(
                            f"""\
                            lanes:
                              main_write: agy
                            writer:
                              provider: agy
                              model: {model}
                              reasoning_effort: {yaml_effort}
                            """
                        ),
                        encoding="utf-8",
                    )
                    resolved = resolve_writer(root, provider_explicit=False)
                    self.assertEqual(resolved["provider"], "agy")
                    self.assertEqual(resolved["model"], model)
                    self.assertEqual(resolved["reasoning_effort"], expected)


if __name__ == "__main__":
    unittest.main()

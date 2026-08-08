from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))

from lane_statusline_lib import (  # noqa: E402
    build_status_line,
    clip_display,
    display_width,
    extract_agent_type,
    make_bar,
    parse_stdin,
    peak_hours_status,
    render_bars,
    use_lane_hud,
)


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class ParseStdinTest(unittest.TestCase):
    def test_rate_limits_context_cost(self) -> None:
        raw = json.dumps(
            {
                "cwd": "/tmp/proj",
                "model": {"display_name": "Claude Sonnet 4"},
                "context_window": {"used_percentage": 42.5},
                "cost": {"total_cost_usd": 12.34},
                "rate_limits": {
                    "five_hour": {
                        "used_percentage": 18,
                        "resets_at": 1785782000,
                    },
                    "seven_day": {
                        "used_percentage": 14,
                        "resets_at": "2026-08-08T01:00:00+00:00",
                    },
                },
            }
        )
        ctx = parse_stdin(raw)
        self.assertEqual(ctx["cwd"], "/tmp/proj")
        self.assertEqual(ctx["model_name"], "Sonnet 4")
        self.assertEqual(ctx["context_pct"], 42.5)
        self.assertEqual(ctx["cost_usd"], 12.34)
        self.assertIn("five_hour", ctx["usage"])
        self.assertEqual(ctx["usage"]["five_hour"]["utilization"], 18.0)
        self.assertTrue(ctx["usage"]["five_hour"]["resets_at"])
        self.assertEqual(ctx["usage"]["seven_day"]["utilization"], 14.0)

    def test_nested_data_shape(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "workspace": {"current_dir": "/home/u/repo"},
                    "context_window": {"used_percentage": 10},
                    "rate_limits": {
                        "five_hour": {"utilization": 5, "resets_at": None},
                    },
                }
            }
        )
        ctx = parse_stdin(raw)
        self.assertEqual(ctx["cwd"], "/home/u/repo")
        self.assertEqual(ctx["usage"]["five_hour"]["utilization"], 5.0)


class DisplayWidthTest(unittest.TestCase):
    def test_ascii_and_clip(self) -> None:
        self.assertEqual(display_width("abc"), 3)
        self.assertEqual(display_width("!2"), 2)
        self.assertEqual(clip_display("hello-world", 8), "hello...")
        self.assertLessEqual(display_width(clip_display("x" * 80, 20)), 20)


class BarsTest(unittest.TestCase):
    def test_make_bar_width(self) -> None:
        plain = _strip_ansi(make_bar(50, width=4))
        self.assertEqual(len(plain), 4)

    def test_render_bars_compact(self) -> None:
        ctx = {
            "usage": {
                "five_hour": {"utilization": 18.0, "resets_at": None},
                "seven_day": {"utilization": 14.0, "resets_at": None},
            },
            "context_pct": 22.0,
            "cost_usd": 33.48,
        }
        line = _strip_ansi(render_bars(ctx))
        self.assertIn("S ", line)
        self.assertIn("18%", line)
        self.assertIn("W ", line)
        self.assertIn("14%", line)
        self.assertIn("C ", line)
        self.assertIn("22%", line)
        self.assertIn("$33.5", line)  # 33.48 → $33.5 under <100 rule
        # peak indicator always present when peak enabled (default)
        self.assertTrue(
            "Off" in line or "Peak" in line or "*Peak" in line or "*in" in line,
            msg=f"expected peak/off marker in: {line!r}",
        )

    def test_peak_in_window(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Wednesday 15:00 local — inside 13–19
        now = datetime(2026, 8, 5, 15, 0, tzinfo=ZoneInfo("UTC"))
        is_peak, plain, ansi = peak_hours_status(now=now, start="13:00", end="19:00")
        self.assertTrue(is_peak)
        self.assertIn("Peak", plain)
        self.assertTrue(ansi)

    def test_peak_weekend_off(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Saturday
        now = datetime(2026, 8, 8, 15, 0, tzinfo=ZoneInfo("UTC"))
        is_peak, plain, _ = peak_hours_status(now=now)
        self.assertFalse(is_peak)
        self.assertEqual(plain, "Off")

    def test_peak_disabled_env(self) -> None:
        old = os.environ.get("LANE_STATUSLINE_PEAK")
        os.environ["LANE_STATUSLINE_PEAK"] = "0"
        try:
            is_peak, plain, ansi = peak_hours_status()
            self.assertFalse(is_peak)
            self.assertEqual(plain, "")
            self.assertEqual(ansi, "")
        finally:
            if old is None:
                os.environ.pop("LANE_STATUSLINE_PEAK", None)
            else:
                os.environ["LANE_STATUSLINE_PEAK"] = old


class HandoffChipTest(unittest.TestCase):
    def test_chip_and_full_line(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            agents = repo / ".agents"
            agents.mkdir(parents=True)
            handoff = {
                "profile": {"main_write": "codex", "workspace_mode": "in_place"},
                "blocked": [{"id": 1}, {"id": 2}],
                "active_runs": [{"slug": "demo-run", "stage": "planning"}],
                "next": [{"action": "fix_control_plane"}],
            }
            (agents / "HANDOFF.json").write_text(
                json.dumps(handoff), encoding="utf-8"
            )
            raw_stdin = json.dumps(
                {
                    "cwd": str(repo),
                    "context_window": {"used_percentage": 10},
                    "cost": {"total_cost_usd": 1.5},
                    "rate_limits": {
                        "five_hour": {"used_percentage": 5, "resets_at": None},
                        "seven_day": {"used_percentage": 3, "resets_at": None},
                    },
                }
            )
            with tempfile.TemporaryDirectory() as cache_raw:
                env_cache = Path(cache_raw)
                old = os.environ.get("LANE_STATUSLINE_CACHE")
                os.environ["LANE_STATUSLINE_CACHE"] = str(env_cache)
                try:
                    line = _strip_ansi(build_status_line(raw_stdin, mode="compact"))
                finally:
                    if old is None:
                        os.environ.pop("LANE_STATUSLINE_CACHE", None)
                    else:
                        os.environ["LANE_STATUSLINE_CACHE"] = old
            self.assertIn("S ", line)
            self.assertIn("C ", line)
            self.assertIn("codex/main", line)
            # Single-width warn marker (emoji ⚠ overlaps text in CC statusLine)
            self.assertIn("!2", line)
            self.assertIn("fix_cp", line)
            self.assertIn("demo-run", line)
            # No double-width emoji in HUD
            for bad in ("⚡", "⚠", "▶", "✓"):
                self.assertNotIn(bad, line)

    def test_no_pulse_dependency_cli(self) -> None:
        """Lane HUD for orchestrator works with no claude-pulse installed."""
        sample = json.dumps(
            {
                "agent_type": "dev-orchestrator",
                "cwd": "/tmp",
                "context_window": {"used_percentage": 15},
                "rate_limits": {
                    "five_hour": {"used_percentage": 7, "resets_at": None},
                    "seven_day": {"used_percentage": 2, "resets_at": None},
                },
            }
        )
        env = os.environ.copy()
        env["HOME"] = str(Path(tempfile.mkdtemp()))
        env["LANE_STATUSLINE_ENGINE"] = "auto"
        # force missing pulse — native path must still work for orchestrator
        env["CLAUDE_PULSE_STATUS"] = str(Path(env["HOME"]) / "missing" / "claude_status.py")
        with tempfile.TemporaryDirectory() as cache:
            env["LANE_STATUSLINE_CACHE"] = cache
            proc = subprocess.run(
                [sys.executable, str(BIN / "lane-statusline")],
                input=sample,
                text=True,
                capture_output=True,
                env=env,
                check=False,
                timeout=5,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = _strip_ansi(proc.stdout)
        self.assertIn("S ", out)
        self.assertIn("7%", out)
        self.assertIn("W ", out)
        self.assertIn("C ", out)
        self.assertIn("15%", out)


class RouterTest(unittest.TestCase):
    def test_extract_agent_type(self) -> None:
        self.assertEqual(
            extract_agent_type('{"agent_type":"dev-orchestrator"}'),
            "dev-orchestrator",
        )
        self.assertEqual(
            extract_agent_type({"data": {"agent_type": "run-supervisor"}}),
            "run-supervisor",
        )
        self.assertEqual(extract_agent_type({"cwd": "/tmp"}), "")

    def test_use_lane_hud_only_for_orchestrator(self) -> None:
        old = os.environ.get("LANE_STATUSLINE_ENGINE")
        os.environ["LANE_STATUSLINE_ENGINE"] = "auto"
        try:
            self.assertTrue(
                use_lane_hud('{"agent_type":"dev-orchestrator","cwd":"/x"}')
            )
            self.assertTrue(
                use_lane_hud('{"agent_type":"frontend-orchestrator"}')
            )
            self.assertFalse(use_lane_hud('{"cwd":"/x","cost":{"total_cost_usd":1}}'))
            self.assertFalse(use_lane_hud("{}"))
        finally:
            if old is None:
                os.environ.pop("LANE_STATUSLINE_ENGINE", None)
            else:
                os.environ["LANE_STATUSLINE_ENGINE"] = old

    def test_engine_force_pulse(self) -> None:
        old = os.environ.get("LANE_STATUSLINE_ENGINE")
        os.environ["LANE_STATUSLINE_ENGINE"] = "pulse"
        try:
            self.assertFalse(use_lane_hud('{"agent_type":"dev-orchestrator"}'))
        finally:
            if old is None:
                os.environ.pop("LANE_STATUSLINE_ENGINE", None)
            else:
                os.environ["LANE_STATUSLINE_ENGINE"] = old

    def test_cli_routes_normal_to_pulse_not_lane_chip(self) -> None:
        """Without agent_type, output must not be our HANDOFF-only compact HUD.

        If pulse is present we get a full pulse line; if not, empty line.
        Never invent lane chip from random cwd without agent.
        """
        sample = json.dumps(
            {
                "cwd": "/tmp/not-a-lane-project",
                "context_window": {"used_percentage": 10},
                "rate_limits": {
                    "five_hour": {"used_percentage": 1, "resets_at": None},
                    "seven_day": {"used_percentage": 2, "resets_at": None},
                },
            }
        )
        env = os.environ.copy()
        env["LANE_STATUSLINE_ENGINE"] = "auto"
        env.pop("CLAUDE_AGENT_TYPE", None)
        with tempfile.TemporaryDirectory() as cache:
            env["LANE_STATUSLINE_CACHE"] = cache
            proc = subprocess.run(
                [sys.executable, str(BIN / "lane-statusline")],
                input=sample,
                text=True,
                capture_output=True,
                env=env,
                check=False,
                timeout=5,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = _strip_ansi(proc.stdout)
        # Must not look like forced lane-only chip with factory tokens
        self.assertNotIn("fix_cp", out)
        self.assertNotIn("codex/main", out)

    def test_cli_lane_agent_gets_native_hud(self) -> None:
        sample = json.dumps(
            {
                "agent_type": "dev-orchestrator",
                "cwd": "/tmp",
                "context_window": {"used_percentage": 15},
                "rate_limits": {
                    "five_hour": {"used_percentage": 7, "resets_at": None},
                    "seven_day": {"used_percentage": 2, "resets_at": None},
                },
            }
        )
        env = os.environ.copy()
        env["LANE_STATUSLINE_ENGINE"] = "auto"
        with tempfile.TemporaryDirectory() as cache:
            env["LANE_STATUSLINE_CACHE"] = cache
            # hide pulse so we prove native path (not pulse)
            env["CLAUDE_PULSE_STATUS"] = str(Path(cache) / "missing-pulse.py")
            proc = subprocess.run(
                [sys.executable, str(BIN / "lane-statusline")],
                input=sample,
                text=True,
                capture_output=True,
                env=env,
                check=False,
                timeout=5,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = _strip_ansi(proc.stdout)
        self.assertIn("S ", out)
        self.assertIn("7%", out)
        self.assertIn("Off", out)  # peak marker on native HUD


class MergeStatuslineTest(unittest.TestCase):
    def test_merge_wires_statusline(self) -> None:
        hooks = ROOT / "hooks" / "merge_claude_settings.py"
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            settings = home / "settings.json"
            settings.write_text("{}\n", encoding="utf-8")
            guard = home / "guard_shell.py"
            guard.write_text("#\n", encoding="utf-8")
            sl = home / "lane-statusline"
            sl.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(hooks),
                    str(settings),
                    str(guard),
                    "--statusline",
                    str(sl),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(settings.read_text(encoding="utf-8"))
            self.assertIn("statusLine", data)
            self.assertIn("lane-statusline", data["statusLine"]["command"])
            self.assertEqual(data["statusLine"]["type"], "command")


if __name__ == "__main__":
    unittest.main()

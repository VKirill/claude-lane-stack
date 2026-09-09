from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
sys.path.insert(0, str(ROOT / "hooks"))

from merge_claude_settings import merge_pm_bulk_read  # noqa: E402
from pm_read import (  # noqa: E402
    BRIEF_MARK,
    BRIEF_RULES,
    HOOK_TIMEOUT,
    build_prompt,
    normalize_pm_read,
    pick_pm_read,
    resolve_pm_read,
    should_block_bash,
    should_block_read,
    worker_brief_for_hook,
)
from routing_profile import load_routing_profile  # noqa: E402


class PmReadTest(unittest.TestCase):
    def test_normalize_defaults_off(self) -> None:
        cfg = normalize_pm_read(None)
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["min_lines"], 350)
        self.assertEqual(cfg["provider"], "agy")
        self.assertEqual(cfg["model"], "gemini-3.8-flash-low")
        self.assertEqual(cfg["reasoning_effort"], "low")

    def test_pick_claude_only_is_sonnet(self) -> None:
        picked = pick_pm_read({"claude": {"present": True}})
        self.assertEqual(picked["provider"], "claude")
        self.assertEqual(picked["model"], "sonnet")

    def test_pick_codex_without_agy_is_terra_fast(self) -> None:
        picked = pick_pm_read(
            {
                "agy": {"present": False},
                "qwen": {"present": False},
                "kimi": {"present": False},
                "grok": {"present": False},
                "codex": {"present": True},
                "claude": {"present": True},
            }
        )
        self.assertEqual(picked["provider"], "codex")
        self.assertEqual(picked["model"], "gpt-5.6-terra")
        self.assertEqual(picked["service_tier"], "fast")
        self.assertEqual(picked["reasoning_effort"], "low")

    def test_resolve_keeps_ready_agy(self) -> None:
        cfg = resolve_pm_read(
            {"enabled": True, "provider": "agy", "model": "gemini-3.7-flash-medium"},
            {"agy": {"present": True}},
        )
        self.assertEqual(cfg["provider"], "agy")
        self.assertEqual(cfg["model"], "gemini-3.7-flash-medium")

    def test_codex_gpt_worker_keeps_effort(self) -> None:
        cfg = normalize_pm_read(
            {
                "enabled": True,
                "provider": "codex",
                "model": "gpt-5.6-luna",
                "reasoning_effort": "medium",
            }
        )
        self.assertEqual(cfg["provider"], "codex")
        self.assertEqual(cfg["model"], "gpt-5.6-luna")
        self.assertEqual(cfg["reasoning_effort"], "medium")

    def test_block_only_when_enabled_and_fat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fat.py"
            path.write_text("x\n" * 400, encoding="utf-8")
            off = normalize_pm_read({"enabled": False, "min_lines": 350})
            block, _, reason = should_block_read(path, cfg=off)
            self.assertFalse(block)
            self.assertEqual(reason, "")

            on = normalize_pm_read({"enabled": True, "min_lines": 350})
            block, lines, reason = should_block_read(path, cfg=on)
            self.assertTrue(block)
            self.assertEqual(lines, 400)
            self.assertIn("pm_read --path", reason)
            self.assertIn("/bulk-reader", reason)
            self.assertIn(BRIEF_MARK, reason)

            small = Path(tmp) / "small.py"
            small.write_text("x\n" * 10, encoding="utf-8")
            block, _, _ = should_block_read(small, cfg=on)
            self.assertFalse(block)

            block, _, _ = should_block_read(path, offset=20, limit=40, cfg=on)
            self.assertFalse(block)

            jpg = Path(tmp) / "shot.jpg"
            jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\n" * 400)
            block, _, _ = should_block_read(jpg, cfg=on)
            self.assertFalse(block)
            png = Path(tmp) / "a.png"
            png.write_text("x\n" * 400, encoding="utf-8")
            block, _, _ = should_block_read(png, cfg=on)
            self.assertFalse(block)

            cmd = (
                f'f=$(ls {path.name} other*.py 2>/dev/null | head -1); '
                f'wc -l "$f"; cat -n "$f"'
            )
            hit, lines, reason = should_block_bash(cmd, Path(tmp), on)
            self.assertEqual(hit, path.resolve())
            self.assertEqual(lines, 400)
            self.assertIn("pm_read --path", reason)
            self.assertIsNone(should_block_bash(f"cat {path.name} | grep foo", Path(tmp), on)[0])
            self.assertEqual(
                should_block_bash(f"sed -n 1,40p {path.name}", Path(tmp), on)[0],
                path.resolve(),
            )
            self.assertEqual(
                should_block_bash(f"head -20 {path.name}", Path(tmp), on)[0],
                path.resolve(),
            )
            self.assertIsNone(should_block_bash(f"cat > {path.name} <<'EOF'\nx\nEOF", Path(tmp), on)[0])
            self.assertIsNone(should_block_bash(f"pm_read --path {path.name}", Path(tmp), on)[0])

    def test_brief_prompt_is_the_fable_contract(self) -> None:
        prompt = build_prompt(Path("a.py"), "Where is auth?", "print(1)\n", 1)
        self.assertIn(BRIEF_MARK, prompt)
        self.assertIn("hotspots:", BRIEF_RULES)
        self.assertIn("No code", BRIEF_RULES)
        self.assertIn("Where is auth?", prompt)

    def test_profile_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                "pm_read:\n  enabled: true\n  min_lines: 200\n"
                "  provider: qwen\n  model: qwen3.6-flash\n",
                encoding="utf-8",
            )
            parsed = load_routing_profile(root)["pm_read"]
            cfg = normalize_pm_read(parsed)
            self.assertTrue(cfg["enabled"])
            self.assertEqual(cfg["min_lines"], 200)
            self.assertEqual(cfg["provider"], "qwen")
            self.assertEqual(cfg["reasoning_effort"], "low")

    def test_merge_read_hook(self) -> None:
        hook = ROOT / "hooks" / "pm_bulk_read.py"
        out = merge_pm_bulk_read({"hooks": {}}, hook)
        entries = out["hooks"]["PreToolUse"]
        self.assertTrue(any(e.get("matcher") == "Read|Bash" for e in entries))
        cmd = entries[0]["hooks"][0]["command"]
        self.assertIn("pm_bulk_read.py", cmd)
        self.assertGreaterEqual(entries[0]["hooks"][0]["timeout"], HOOK_TIMEOUT)
        out2 = merge_pm_bulk_read(out, hook)
        read_hooks = [e for e in out2["hooks"]["PreToolUse"] if e.get("matcher") == "Read|Bash"]
        self.assertEqual(len(read_hooks), 1)

    def test_hook_worker_brief_uses_adoc_model(self) -> None:
        from unittest.mock import patch

        cfg = normalize_pm_read(
            {"enabled": True, "provider": "agy", "model": "gemini-3.7-flash-medium"}
        )
        with patch(
            "pm_read.run_brief",
            return_value=f"{BRIEF_MARK}\npath: a.py\npurpose: map\n",
        ) as run:
            text = worker_brief_for_hook(Path("a.py"), cfg)
        run.assert_called_once()
        self.assertIn(BRIEF_MARK, text)
        self.assertNotIn("print(", text)
        orch = (
            ROOT / "plugins" / "lane-stack" / "agents" / "dev-orchestrator.md"
        ).read_text(encoding="utf-8")
        self.assertIn("pm_read --path", orch)
        self.assertIn("/bulk-reader", orch)
        skill = (
            ROOT / "plugins" / "lane-stack" / "skills" / "bulk-reader" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("pm_read --path FILE", skill)
        self.assertIn("NEVER", skill)

    def test_apply_receipt_shows_pm_read(self) -> None:
        from agents_doctor_tui import _done_pm_read, _print_apply_receipt  # noqa: E402

        self.assertEqual(_done_pm_read("ru", {"pm_read_enabled": False}), "выкл")
        on = _done_pm_read(
            "ru",
            {
                "pm_read_enabled": True,
                "pm_read_min_lines": 350,
                "pm_read_provider": "codex",
                "pm_read_model": "gpt-5.6-luna",
                "pm_read_effort": "medium",
            },
        )
        self.assertIn("codex/gpt-5.6-luna", on)
        self.assertIn("medium", on)
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            _print_apply_receipt(
                {
                    "ok": True,
                    "repo": "/tmp/x",
                    "writer": "cursor",
                    "model": "cursor-grok-4.6-medium-fast",
                    "effort": "medium",
                    "service_tier": "fast",
                    "fast_mode": True,
                    "workspace_mode": "in_place",
                    "session_max_tasks": 10,
                    "lang": "ru",
                    "night": False,
                    "critique": "advisory/agy",
                    "pm_read_enabled": True,
                    "pm_read_min_lines": 350,
                    "pm_read_provider": "agy",
                    "pm_read_model": "gemini-3.8-flash-low",
                    "pm_read_effort": "low",
                }
            )
        text = buf.getvalue()
        self.assertIn("pm_read", text)
        self.assertIn("gemini-3.8-flash-low", text)


if __name__ == "__main__":
    unittest.main()

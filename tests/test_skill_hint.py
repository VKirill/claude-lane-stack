from __future__ import annotations

import io
import json
import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "lane-stack" / "hooks"))
import skill_hint  # noqa: E402


class SkillHintTest(unittest.TestCase):
    def _skill(self, root: Path, folder: str, frontmatter: str) -> Path:
        path = root / folder / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{frontmatter}\n---\n# Skill\n", encoding="utf-8")
        return path

    def test_discovers_seo_and_drmax_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seo = self._skill(
                root,
                "seo-tools",
                'name: seo-tools\ndescription: "SEO routing"',
            )
            drmax = self._skill(
                root,
                "drmax",
                'name: drmax\ndescription: "DrMax navigator"',
            )
            found = skill_hint.discover_skills([root])
            self.assertEqual(found["seo-tools"], {"description": "SEO routing", "path": str(seo)})
            self.assertEqual(found["drmax"]["description"], "DrMax navigator")

    def test_skips_bad_disabled_and_duplicate_entries_deterministically(self) -> None:
        with TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            self._skill(first, "same", 'name: same\ndescription: "first"')
            self._skill(second, "same", 'name: same\ndescription: "second"')
            self._skill(first, "disabled", 'name: disabled\ndescription: nope\ndisable-model-invocation: true')
            self._skill(first, "bad", 'name: bad\ndescription: "unterminated')
            self._skill(first, "missing", "name: missing")
            found = skill_hint.discover_skills([first, second])
            self.assertEqual(set(found), {"same"})
            self.assertEqual(found["same"]["description"], "first")

    def test_project_disabled_skill_masks_global_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            global_root = Path(tmp) / "global"
            self._skill(
                project,
                "seo-tools",
                'name: seo-tools\ndescription: "local"\ndisable-model-invocation: true',
            )
            global_skill = self._skill(
                global_root,
                "seo-tools",
                'name: seo-tools\ndescription: "global"',
            )
            self._skill(
                project,
                "drmax",
                "name: drmax\ndescription: >\n  DrMax folded\n  description",
            )
            found = skill_hint.discover_skills([project, global_root])
            self.assertNotIn("seo-tools", found)
            self.assertNotIn(str(global_skill), {item["path"] for item in found.values()})
            self.assertEqual(found["drmax"]["description"], "DrMax folded description")

    def test_symlinked_skill_directory_is_discovered(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            target = Path(tmp) / "target"
            target_skill = self._skill(target, "seo-tools", 'name: seo-tools\ndescription: "SEO"')
            root.mkdir()
            try:
                (root / "seo-tools").symlink_to(target / "seo-tools", target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            found = skill_hint.discover_skills([root])
            self.assertEqual(found["seo-tools"]["path"], str(root / "seo-tools" / "SKILL.md"))
            self.assertTrue(target_skill.is_file())

    def test_roots_prefer_project_and_include_global_claude_skills(self) -> None:
        with TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "project"
            with patch.object(Path, "home", return_value=home), patch.object(
                skill_hint, "_project_root", return_value=project
            ), patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": ""}):
                roots = skill_hint._skill_roots()
            self.assertEqual(roots[:2], [project / ".claude" / "skills", project / ".agents" / "skills"])
            self.assertIn(home / ".claude" / "skills", roots)
            self.assertIn(home / ".agents" / "skills", roots)

    def test_catalog_skips_oversized_entry_and_keeps_later_skill(self) -> None:
        discovered = {
            "oversized": {"description": "x" * (skill_hint.MAX_CATALOG_BYTES + 1), "path": "/x"},
            "seo-tools": {"description": "SEO", "path": "/seo"},
            "writer": {"description": "Writer", "path": "/writer"},
        }
        skills, paths = skill_hint.select_catalog(discovered)
        self.assertNotIn("oversized", skills)
        self.assertIn("seo-tools", skills)
        self.assertIn("writer", skills)
        self.assertEqual(paths["seo-tools"], "/seo")

    def test_catalog_ranks_by_task_terms(self) -> None:
        discovered = {
            "writer": {"description": "General writing", "path": "/writer"},
            "drmax": {"description": "Cocoon research", "path": "/drmax"},
        }
        skills, _ = skill_hint.select_catalog(discovered, "DrMax cocoon")
        self.assertEqual(list(skills)[1], "drmax")

    def test_task_view_is_byte_bounded(self) -> None:
        task = "Привет " * 10_000
        self.assertLessEqual(len(skill_hint._task_view(task).encode("utf-8")), skill_hint.MAX_TASK_BYTES)

    def test_empty_catalog_and_jev_errors_fail_open(self) -> None:
        with patch.object(skill_hint, "_skill_roots", return_value=[]):
            with patch("sys.stdin", io.StringIO('{"prompt":"write"}')), patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(skill_hint.main(), 0)
                self.assertEqual(out.getvalue(), "")

        with patch.object(skill_hint, "discover_skills", side_effect=AssertionError("subagent catalog")):
            with patch("sys.stdin", io.StringIO('{"prompt":"write","agent_id":"sub-1"}')), patch(
                "sys.stdout", new_callable=io.StringIO
            ) as out:
                self.assertEqual(skill_hint.main(), 0)
                self.assertEqual(out.getvalue(), "")

        fake = types.ModuleType("jev_decisions")
        fake.call_jev = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline"))
        fake.choice = lambda *args, **kwargs: ("none", 0.0)
        with TemporaryDirectory() as tmp, patch.object(skill_hint, "_skill_roots", return_value=[Path(tmp)]), patch.object(
            skill_hint, "_bin_paths", return_value=[ROOT / "bin"]
        ), patch.dict(sys.modules, {"jev_decisions": fake}):
            self._skill(Path(tmp), "writer", 'name: writer\ndescription: "write"')
            with patch("sys.stdin", io.StringIO('{"prompt":"write"}')), patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(skill_hint.main(), 0)
                self.assertEqual(out.getvalue(), "")

    def test_selected_skill_advertises_discovered_path(self) -> None:
        fake = types.ModuleType("jev_decisions")
        requests = []

        def call_jev(*args, **kwargs):
            requests.append((args, kwargs))
            return {"answers": {"skill": {"choice": "seo-tools", "confidence": 0.9}}}

        fake.call_jev = call_jev
        fake.choice = lambda answers, key, allowed, default: ("seo-tools", 0.9)
        with TemporaryDirectory() as tmp, patch.object(skill_hint, "_skill_roots", return_value=[Path(tmp)]), patch.object(
            skill_hint, "_bin_paths", return_value=[ROOT / "bin"]
        ), patch.dict(sys.modules, {"jev_decisions": fake}):
            path = self._skill(Path(tmp), "seo-tools", 'name: seo-tools\ndescription: "SEO routing"')
            with patch("sys.stdin", io.StringIO('{"prompt":"check SEO"}')), patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(skill_hint.main(), 0)
                payload = json.loads(out.getvalue())
                self.assertIn(str(path), payload["hookSpecificOutput"]["additionalContext"])
                self.assertIn("current task", requests[0][0][1]["skill"]["instructions"])
                self.assertIn("none", requests[0][0][1]["skill"]["instructions"])


if __name__ == "__main__":
    unittest.main()

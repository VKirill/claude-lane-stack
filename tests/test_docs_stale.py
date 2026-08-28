from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_LOADER = importlib.machinery.SourceFileLoader("docs_stale", str(ROOT / "bin" / "docs-stale"))
docs_stale = importlib.util.module_from_spec(importlib.util.spec_from_loader(_LOADER.name, _LOADER))
_LOADER.exec_module(docs_stale)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class DocsStaleTest(unittest.TestCase):
    def test_extract_file_tokens(self) -> None:
        cited = docs_stale.extract_cited(
            "See `apps/api/src/foo.ts:12` and packages/core/bar.py"
        )
        self.assertIn("apps/api/src/foo.ts", cited)
        self.assertIn("packages/core/bar.py", cited)
        self.assertFalse(any(p.startswith("wiki/") for p in cited))

    def test_cites_change_prefix(self) -> None:
        self.assertTrue(
            docs_stale.cites_change({"apps/api"}, ["apps/api/src/foo.ts"])
        )
        self.assertFalse(
            docs_stale.cites_change({"apps/web/src/a.ts"}, ["apps/api/src/foo.ts"])
        )

    def test_scan_skip_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init")
            _git(repo, "config", "user.email", "t@example.com")
            _git(repo, "config", "user.name", "T")
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MODULE_MAP.yaml").write_text(
                "modules:\n  - id: api\n    path: apps/api\n    entrypoints:\n      - apps/api/src/foo.ts:1\n",
                encoding="utf-8",
            )
            (repo / "docs" / "llm" / "MANIFEST.yaml").write_text(
                "pack:\n  always_load: [docs/llm/MODULE_MAP.yaml]\n  on_demand: []\n",
                encoding="utf-8",
            )
            (repo / "wiki" / "old.md").parent.mkdir(exist_ok=True)
            (repo / "wiki" / "old.md").write_text("apps/api/src/foo.ts:1\n")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "docs only")
            skipped = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertEqual(skipped["status"], "skip")

            (repo / "apps" / "api" / "src").mkdir(parents=True)
            (repo / "apps" / "api" / "src" / "foo.ts").write_text("export const a = 1\n")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "code")
            stale = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertEqual(stale["status"], "stale")
            self.assertEqual(stale["stale_docs"], ["docs/llm/MODULE_MAP.yaml"])
            self.assertNotIn("wiki/old.md", stale["stale_docs"])

    def test_stub_always_stale_and_owns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init")
            _git(repo, "config", "user.email", "t@example.com")
            _git(repo, "config", "user.name", "T")
            (repo / "docs" / "packages").mkdir(parents=True)
            (repo / "docs" / "packages" / "auth.md").write_text(
                "---\nstatus: stub\nowns:\n  - packages/auth/**\n---\n# Auth\n",
                encoding="utf-8",
            )
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MANIFEST.yaml").write_text(
                "pack:\n  always_load: [docs/packages/auth.md]\n",
                encoding="utf-8",
            )
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "stub only")
            stale = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertEqual(stale["status"], "stale")
            self.assertIn("docs/packages/auth.md", stale["stale_docs"])
            capped = docs_stale.apply_page_cap(
                {"stale_docs": ["a.md", "b.md", "c.md"], "hits": [
                    {"doc": "a.md"}, {"doc": "b.md"}, {"doc": "c.md"}
                ]},
                2,
            )
            self.assertEqual(capped["stale_docs"], ["a.md", "b.md"])
            self.assertEqual(capped["deferred"], ["c.md"])
            stub_first = docs_stale.apply_page_cap(
                {
                    "stale_docs": ["diff.md", "stub.md"],
                    "hits": [
                        {"doc": "diff.md", "stub": False},
                        {"doc": "stub.md", "stub": True},
                    ],
                },
                1,
            )
            self.assertEqual(stub_first["stale_docs"], ["stub.md"])
            self.assertEqual(stub_first["deferred"], ["diff.md"])
            daylog = docs_stale.write_daylog(repo, stale)
            self.assertTrue(daylog.is_file())
            text = daylog.read_text(encoding="utf-8")
            self.assertIn("Pages to edit", text)
            self.assertIn("docs/packages/auth.md", text)
            self.assertIn("## [", (repo / "docs" / "log.md").read_text(encoding="utf-8"))

    def test_cli_exit_codes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "bin" / "docs-stale"), "/no/such"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()

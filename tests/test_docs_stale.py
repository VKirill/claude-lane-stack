from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
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

    def test_thin_active_is_stale_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init")
            _git(repo, "config", "user.email", "t@example.com")
            _git(repo, "config", "user.name", "T")
            (repo / "packages" / "auth" / "src").mkdir(parents=True)
            (repo / "packages" / "auth" / "src" / "index.ts").write_text(
                "export const x = 1\n" * 20, encoding="utf-8"
            )
            (repo / "docs" / "packages").mkdir(parents=True)
            (repo / "docs" / "packages" / "auth.md").write_text(
                "---\nstatus: active\nkind: unit\nowns:\n  - packages/auth/**\n---\n"
                "# Auth\n\n<!-- body:start -->\n"
                "TL;DR: short.\n\n## Purpose\nTiny.\n\n## Public API\n- x\n\n"
                "## Gotchas\n- none\n"
                "<!-- body:end -->\n",
                encoding="utf-8",
            )
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MANIFEST.yaml").write_text(
                "pack:\n  always_load: [docs/packages/auth.md]\n",
                encoding="utf-8",
            )
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "thin active")
            reasons = docs_stale.thin_reasons(repo / "docs" / "packages" / "auth.md", repo)
            self.assertTrue(reasons)
            stale = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertEqual(stale["status"], "stale")
            self.assertIn("docs/packages/auth.md", stale["stale_docs"])
            hit = next(h for h in stale["hits"] if h["doc"] == "docs/packages/auth.md")
            self.assertTrue(hit["thin"])
            thin_first = docs_stale.apply_page_cap(
                {
                    "stale_docs": ["diff.md", "thin.md"],
                    "hits": [
                        {"doc": "diff.md", "stub": False, "thin": []},
                        {"doc": "thin.md", "stub": False, "thin": ["words:10<700"]},
                    ],
                },
                1,
            )
            self.assertEqual(thin_first["stale_docs"], ["thin.md"])

    def test_complete_unit_not_stale_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init")
            _git(repo, "config", "user.email", "t@example.com")
            _git(repo, "config", "user.name", "T")
            src = repo / "packages" / "auth" / "src" / "index.ts"
            src.parent.mkdir(parents=True)
            src.write_text("export const x = 1\n" * 20, encoding="utf-8")
            cites = " ".join(f"(packages/auth/src/index.ts:{i})" for i in range(1, 13))
            body = (
                "TL;DR: full auth unit.\n\n## Purpose\n"
                + ("word " * 700)
                + "\n\n## Public API\n"
                + "| Symbol | file:line | Purpose |\n| --- | --- | --- |\n"
                + "| `x` | packages/auth/src/index.ts:1 | export |\n\n"
                + "## Gotchas\n- check the secret env name only "
                + cites
                + "\n"
            )
            (repo / "docs" / "packages").mkdir(parents=True)
            (repo / "docs" / "packages" / "auth.md").write_text(
                "---\nstatus: active\nkind: unit\nowns:\n  - packages/auth/**\n---\n"
                f"# Auth\n\n<!-- body:start -->\n{body}<!-- body:end -->\n",
                encoding="utf-8",
            )
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MANIFEST.yaml").write_text(
                "pack:\n  always_load: [docs/packages/auth.md]\n",
                encoding="utf-8",
            )
            _git(repo, "add", ".")
            env_commit = {
                "GIT_AUTHOR_DATE": "2020-01-01T00:00:00",
                "GIT_COMMITTER_DATE": "2020-01-01T00:00:00",
            }
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-m", "complete"],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, **env_commit},
            )
            self.assertEqual(
                docs_stale.thin_reasons(repo / "docs" / "packages" / "auth.md", repo),
                [],
            )
            skipped = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertEqual(skipped["status"], "skip")

    def test_thin_app_claude_is_stub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            _git(repo, "init")
            _git(repo, "config", "user.email", "t@example.com")
            _git(repo, "config", "user.name", "T")
            claude = repo / "apps" / "web" / "CLAUDE.md"
            claude.parent.mkdir(parents=True)
            claude.write_text(
                "# web\n\n## Owns\n\n- `apps/web/**`\n\n## Pointers\n\n- `docs/INDEX.md`\n",
                encoding="utf-8",
            )
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MANIFEST.yaml").write_text(
                "pack:\n  always_load: [docs/ARCHITECTURE.md]\n",
                encoding="utf-8",
            )
            (repo / "docs" / "ARCHITECTURE.md").write_text("# A\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "thin claude")
            self.assertTrue(docs_stale.is_app_claude(claude))
            self.assertTrue(docs_stale.is_stub_page(claude))
            stale = docs_stale.scan_repo(repo, "24 hours ago")
            self.assertIn("apps/web/CLAUDE.md", stale["stale_docs"])

            src = repo / "apps" / "web" / "src" / "index.ts"
            src.parent.mkdir(parents=True)
            src.write_text("export const x = 1\n" * 20, encoding="utf-8")
            cites = " ".join(f"(apps/web/src/index.ts:{i})" for i in range(1, 5))
            claude.write_text(
                "# web\n\n## What\nNext.js HTTP app.\n\n## Owns\n- `apps/web/**`\n\n"
                "## Never / Always\n"
                f"- **Never** skip session check {cites}\n"
                "- **Always** use the module context\n\n"
                "## Verify\n\n```bash\nnpm test --workspace web\n```\n\n"
                "## Pointers\n- `docs/INDEX.md`\n\n"
                + ("word " * 160)
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(docs_stale.is_stub_page(claude))
            self.assertEqual(docs_stale.thin_reasons(claude, repo), [])

    def test_passport_gaps_then_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "apps" / "web" / "src").mkdir(parents=True)
            (repo / "apps" / "web" / "package.json").write_text('{"name":"web"}\n')
            (repo / "apps" / "web" / "src" / "index.ts").write_text("export const x = 1\n" * 20)
            (repo / "apps" / "web" / "CLAUDE.md").write_text("# web\n\n## Owns\n- apps/web/**\n")
            gaps = docs_stale.passport_gaps(repo)
            self.assertTrue(any("stub:apps/web/CLAUDE.md" in g or "thin:" in g for g in gaps))
            self.assertIn("root-claude-missing", gaps)
            self.assertIn("module-map-missing", gaps)
            cli = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "docs-stale"), str(repo), "--passport-gaps"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cli.returncode, 0)
            payload = json.loads(cli.stdout)
            self.assertTrue(payload["needed"])

            src = repo / "apps" / "web" / "src" / "index.ts"
            cites = " ".join(f"(apps/web/src/index.ts:{i})" for i in range(1, 5))
            (repo / "CLAUDE.md").write_text("# Offerta\n\nReal passport.\n")
            (repo / "docs" / "llm").mkdir(parents=True)
            (repo / "docs" / "llm" / "MODULE_MAP.yaml").write_text("modules: []\n")
            (repo / "apps" / "web" / "CLAUDE.md").write_text(
                "# web\n\n## What\nHTTP app.\n\n## Owns\n- `apps/web/**`\n\n"
                "## Never / Always\n"
                f"- **Never** skip session {cites}\n"
                "- **Always** use context\n\n"
                "## Verify\n\n```bash\nnpm test --workspace web\n```\n\n"
                "## Pointers\n- `docs/INDEX.md`\n\n"
                + ("word " * 160)
                + "\n"
            )
            self.assertEqual(docs_stale.passport_gaps(repo), [])
            cli_ok = subprocess.run(
                [sys.executable, str(ROOT / "bin" / "docs-stale"), str(repo), "--passport-gaps"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(cli_ok.returncode, 2)

    def test_cite_oob_and_design_token_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            src = repo / "pkg" / "a.ts"
            src.parent.mkdir(parents=True)
            src.write_text("a\nb\n", encoding="utf-8")
            problems = docs_stale.cite_line_problems(
                repo, "see pkg/a.ts:9 and pkg/missing.ts:1"
            )
            self.assertTrue(any(p.startswith("oob:pkg/a.ts:9") for p in problems))
            self.assertTrue(any(p.startswith("missing:pkg/missing.ts") for p in problems))
            design = repo / "docs" / "DESIGN.md"
            design.parent.mkdir(parents=True)
            design.write_text(
                "---\ncolors:\n  primary: '#000'\n---\n# Tokens\nshort\n",
                encoding="utf-8",
            )
            self.assertEqual(docs_stale.thin_reasons(design, repo), [])
            wiki_design = repo / "apps" / "web" / "docs" / "DESIGN.md"
            wiki_design.parent.mkdir(parents=True)
            wiki_design.write_text(
                "---\nstatus: active\nkind: unit\n---\n# Tokens\nshort\n",
                encoding="utf-8",
            )
            self.assertEqual(docs_stale.thin_reasons(wiki_design, repo), [])

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

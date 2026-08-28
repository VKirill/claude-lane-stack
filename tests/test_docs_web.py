from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
_LOADER = importlib.machinery.SourceFileLoader("docs_web", str(ROOT / "bin" / "docs-web"))
docs_web = importlib.util.module_from_spec(importlib.util.spec_from_loader(_LOADER.name, _LOADER))
_LOADER.exec_module(docs_web)


class DocsWebTest(unittest.TestCase):
    def test_merge_web_keeps_body(self) -> None:
        src = (
            "---\ntitle: Auth\nstatus: active\nsources:\n  - packages/auth/src/index.ts\n"
            "id: old\n---\n\n# Auth\n\nkeep me\n"
        )
        out = docs_web.merge_web(src, {"id": "auth", "kind": "unit", "owns": ["packages/auth/**"]})
        self.assertIn("keep me", out)
        self.assertIn("status: active", out)
        self.assertIn("packages/auth/src/index.ts", out)
        self.assertIn("id: auth", out)
        self.assertNotIn("id: old", out)

    def test_rebuild_discovers_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            pkg = repo / "packages" / "auth"
            pkg.mkdir(parents=True)
            (pkg / "package.json").write_text('{"name":"auth"}\n', encoding="utf-8")
            (pkg / "src").mkdir()
            (pkg / "src" / "index.ts").write_text("export const x = 1\n", encoding="utf-8")
            result = docs_web.rebuild(repo)
            self.assertIn("auth", result["units"])
            page = repo / "docs" / "packages" / "auth.md"
            self.assertTrue(page.is_file())
            text = page.read_text(encoding="utf-8")
            self.assertIn("status: stub", text)
            self.assertIn("packages/auth/**", text)
            self.assertTrue((repo / "docs" / "web.yaml").is_file())
            self.assertTrue((repo / "docs" / "INDEX.md").is_file())
            self.assertTrue((repo / "docs" / "log.md").is_file())
            self.assertTrue((repo / "llms.txt").is_file())
            self.assertIn("docs/INDEX.md", (repo / "llms.txt").read_text(encoding="utf-8"))
            self.assertTrue((repo / "docs" / "ARCHITECTURE.md").is_file())
            self.assertTrue((repo / "docs" / "llm" / "MANIFEST.yaml").is_file())
            self.assertIn("| auth |", (repo / "docs" / "glossary.md").read_text(encoding="utf-8"))
            self.assertIn("## units", (repo / "docs" / "INDEX.md").read_text(encoding="utf-8"))
            self.assertEqual(
                __import__("yaml").safe_load((repo / "docs" / "web.yaml").read_text())["gitnexus"],
                "missing",
            )
            again = docs_web.merge_web(text, {"owns": ["packages/auth/**"], "id": "auth"})
            self.assertIn("TL;DR", again)

    def test_pyproject_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            pkg = repo / "packages" / "core"
            pkg.mkdir(parents=True)
            (pkg / "pyproject.toml").write_text("[project]\nname='core'\n", encoding="utf-8")
            units = docs_web.discover_units(repo)
            self.assertEqual([u["id"] for u in units], ["core"])

    def test_gitnexus_stale_and_data_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertEqual(docs_web.gitnexus_status(repo), "missing")
            gn = repo / ".gitnexus"
            gn.mkdir()
            (gn / "meta.json").write_text(
                '{"lastCommit": "deadbeef"}\n', encoding="utf-8"
            )
            self.assertEqual(docs_web.gitnexus_status(repo), "stale")
            prisma = repo / "prisma"
            prisma.mkdir()
            (prisma / "schema.prisma").write_text(
                "model User {\n  id Int\n}\nmodel Session {\n  id Int\n}\n",
                encoding="utf-8",
            )
            result = docs_web.rebuild(repo)
            self.assertTrue((repo / "docs" / "data-model.md").is_file())
            text = (repo / "docs" / "data-model.md").read_text(encoding="utf-8")
            self.assertIn("## User", text)
            self.assertIn("## Session", text)
            self.assertIn("data-model.md", (repo / "docs" / "llm" / "MANIFEST.yaml").read_text())
            self.assertEqual(result.get("gitnexus"), "stale")

    def test_hub_fanin_and_language_lint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for name, deps in (
                ("auth", {}),
                ("api", {"auth": "1"}),
                ("bot", {"auth": "1"}),
                ("cabinet", {"auth": "1"}),
            ):
                pkg = repo / "packages" / name
                pkg.mkdir(parents=True)
                (pkg / "package.json").write_text(
                    __import__("json").dumps({"name": name, "dependencies": deps}),
                    encoding="utf-8",
                )
                (pkg / "src").mkdir()
                (pkg / "src" / "index.ts").write_text("export const x = 1\n", encoding="utf-8")
            result = docs_web.rebuild(repo)
            self.assertIn("auth-hub", result["hubs"])
            self.assertTrue((repo / "docs" / "hubs" / "auth.md").is_file())
            page = repo / "docs" / "packages" / "api.md"
            text = page.read_text(encoding="utf-8")
            page.write_text(
                text.replace("status: stub", "status: active").replace(
                    "TL;DR: _stub — fill from owns_", "TL;DR: Привет"
                ),
                encoding="utf-8",
            )
            lint = docs_web.lint_repo(repo)
            self.assertTrue(any(e.startswith("language:") for e in lint["errors"]))

    def test_tombstone_and_secret_lint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            gone = repo / "docs" / "packages"
            gone.mkdir(parents=True)
            (gone / "old.md").write_text(
                "---\nid: old\nkind: unit\nstatus: active\nowns:\n  - packages/old/**\n---\n# Old\n",
                encoding="utf-8",
            )
            (repo / "docs" / "leak.md").write_text(
                "api_key = \"abcdefghijkl\"\n",
                encoding="utf-8",
            )
            result = docs_web.rebuild(repo)
            self.assertIn("docs/packages/old.md", result["deprecated"])
            text = (repo / "docs" / "packages" / "old.md").read_text(encoding="utf-8")
            self.assertIn("status: deprecated", text)
            lint = docs_web.lint_repo(repo)
            self.assertFalse(lint["ok"])
            self.assertTrue(any(e.startswith("secret:") for e in lint["errors"]))


if __name__ == "__main__":
    unittest.main()

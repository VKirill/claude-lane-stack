#!/usr/bin/env python3
"""Deterministic monorepo app-pack helpers for project-onboard.

Pipeline role (not a docs rewriter for humans):
  1. list apps that need a local pack
  2. project root docs/llm/API_SURFACE.yaml → apps/<name>/docs/llm/API_SURFACE.yaml
  3. ensure skeleton files exist from templates (model fills prose later)

Usage:
  onboard_app_packs.py list <repo>
  onboard_app_packs.py project-surfaces <repo>
  onboard_app_packs.py ensure-skeletons <repo>
  onboard_app_packs.py prepare <repo>   # skeletons + project-surfaces
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


BOUNDARY_SKIP = re.compile(r"^(node_modules|\.git|\.agents)$")


def _apps(repo: Path) -> list[Path]:
    root = repo / "apps"
    if not root.is_dir():
        return []
    out: list[Path] = []
    for pkg in sorted(root.glob("*/package.json")):
        app = pkg.parent
        if BOUNDARY_SKIP.match(app.name):
            continue
        codeish = any(
            (app / n).exists() for n in ("src", "app", "server", "lib", "cmd", "internal")
        ) or any(app.glob("*.ts")) or any(app.glob("*.tsx")) or (app / "Dockerfile").exists()
        if codeish:
            out.append(app)
    return out


def _load_yaml(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required")
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _dump_yaml(data: dict) -> str:
    assert yaml is not None
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def cmd_list(repo: Path) -> int:
    apps = _apps(repo)
    for a in apps:
        print(a.name)
    print(f"count={len(apps)}", file=sys.stderr)
    return 0


def project_surfaces(repo: Path) -> int:
    root_api = repo / "docs" / "llm" / "API_SURFACE.yaml"
    if not root_api.is_file():
        print("skip project-surfaces: no root docs/llm/API_SURFACE.yaml", file=sys.stderr)
        return 0
    root = _load_yaml(root_api)
    surfs = root.get("surfaces") or []
    if not isinstance(surfs, list):
        surfs = []
    sources = root.get("sources") or [
        "docs/llm/API_SURFACE.yaml",
        f"apps/*/ (projected {date.today()})",
    ]
    n_apps = 0
    for app in _apps(repo):
        prefix = f"apps/{app.name}/"
        local = [
            dict(s)
            for s in surfs
            if isinstance(s, dict) and str(s.get("path") or "").startswith(prefix)
        ]
        # Always write file so phase4b has a real catalog to expand (may be empty for pure UI)
        dest = app / "docs" / "llm" / "API_SURFACE.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "project": f"{repo.name}-{app.name}",
            "generated_by": "onboard_app_packs.project-surfaces",
            "updated_at": str(date.today()),
            "note": (
                "Projected from root docs/llm/API_SURFACE.yaml. "
                "Phase4b must expand families/webhooks from code; do not collapse to catch-alls."
            ),
            "sources": list(sources) + [prefix],
            "surfaces": local,
        }
        dest.write_text(_dump_yaml(payload), encoding="utf-8")
        print(f"projected {app.name}: {len(local)} surfaces → {dest.relative_to(repo)}")
        n_apps += 1
    print(f"project-surfaces done apps={n_apps}", file=sys.stderr)
    return 0


def _tpl_root() -> Path:
    home = Path.home() / ".agents" / "templates" / "app-pack"
    if home.is_dir():
        return home
    sibling = Path(__file__).resolve().parents[1] / "templates" / "app-pack"
    return sibling


def ensure_skeletons(repo: Path) -> int:
    tpl = _tpl_root()
    nested = Path.home() / ".agents" / "templates" / "nested-CLAUDE.md"
    if not nested.is_file():
        nested = Path(__file__).resolve().parents[1] / "templates" / "nested-CLAUDE.md"
    files = [
        ("docs/INDEX.md", tpl / "INDEX.md"),
        ("docs/ARCHITECTURE.md", tpl / "ARCHITECTURE.md"),
        ("docs/GOTCHAS.md", tpl / "GOTCHAS.md"),
        ("docs/llm/FLOWS.md", tpl / "llm" / "FLOWS.md"),
    ]
    for app in _apps(repo):
        for rel, src in files:
            dest = app / rel
            if dest.is_file():
                continue
            if not src.is_file():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8").replace("REPLACE_ME", app.name)
            dest.write_text(text, encoding="utf-8")
            print(f"skeleton {dest.relative_to(repo)}")
        claude = app / "CLAUDE.md"
        if not claude.is_file() and nested.is_file():
            text = nested.read_text(encoding="utf-8").replace("REPLACE_ME", app.name)
            claude.write_text(text, encoding="utf-8")
            print(f"skeleton {claude.relative_to(repo)}")
    return 0


def prepare(repo: Path) -> int:
    ensure_skeletons(repo)
    return project_surfaces(repo)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["list", "project-surfaces", "ensure-skeletons", "prepare"])
    ap.add_argument("repo", nargs="?", default=".")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if args.command == "list":
        return cmd_list(repo)
    if args.command == "project-surfaces":
        return project_surfaces(repo)
    if args.command == "ensure-skeletons":
        return ensure_skeletons(repo)
    return prepare(repo)


if __name__ == "__main__":
    raise SystemExit(main())

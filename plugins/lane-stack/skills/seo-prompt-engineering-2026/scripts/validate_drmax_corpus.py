#!/usr/bin/env python3
"""Validate the rebuilt DrMax skill and byte-identical source corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
import re
import sys
from urllib.parse import unquote


FORBIDDEN_TEXT = (
    "/home/ubuntu/.claude/skills/seo-prompt-engineering-2026",
    "file://",
    "legacy-telegram-pack",
)
EXPECTED_BOOKS = {
    "gist-content-logic-v3.3-pocketbook.md",
    "prompt-engineering-for-seo-strategists-v1.5.md",
    "evidence-based-seo.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_frontmatter(skill: Path, errors: list[str]) -> None:
    text = skill.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        fail(errors, "SKILL.md has no YAML frontmatter")
        return
    try:
        closing = lines.index("---", 1)
    except ValueError:
        fail(errors, "SKILL.md frontmatter is not closed")
        return
    keys = {
        line.split(":", 1)[0].strip()
        for line in lines[1:closing]
        if ":" in line and not line.startswith(" ")
    }
    if keys != {"name", "description"}:
        fail(errors, f"SKILL.md frontmatter keys are {sorted(keys)}")
    if len(lines) >= 500:
        fail(errors, f"SKILL.md is too long: {len(lines)} lines")


def validate_manifest(root: Path, errors: list[str]) -> int:
    originals = root / "references" / "originals"
    manifest_file = originals / "MANIFEST.tsv"
    if not manifest_file.is_file():
        fail(errors, "Original source manifest is missing")
        return 0

    with manifest_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    destinations: set[Path] = set()
    for row in rows:
        destination = root / row["destination"]
        source = Path(row["source_file"])
        destinations.add(destination.resolve())
        if not source.is_file():
            fail(errors, f"Source file is missing: {source}")
            continue
        if not destination.is_file():
            fail(errors, f"Copied original is missing: {destination}")
            continue
        expected = row["sha256"]
        source_hash = sha256(source)
        destination_hash = sha256(destination)
        if source_hash != expected:
            fail(errors, f"Source hash drift: {source}")
        if destination_hash != expected:
            fail(errors, f"Original copy was modified: {destination}")
        if destination.stat().st_size != int(row["bytes"]):
            fail(errors, f"Original size drift: {destination}")

    unmanaged = {
        path.resolve()
        for path in originals.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".txt", ".md"}
        and path.name not in {"INDEX.md"}
    } - destinations
    for path in sorted(unmanaged):
        fail(errors, f"Unmanaged original prompt: {path}")
    return len(rows)


def validate_structure(root: Path, errors: list[str]) -> None:
    required = [
        root / "SKILL.md",
        root / "agents" / "openai.yaml",
        root / "references" / "source-catalog.md",
        root / "references" / "workflow-routing.md",
        root / "references" / "prompt-systems-guide.md",
        root / "references" / "book-methods-guide.md",
    ]
    for path in required:
        if not path.is_file():
            fail(errors, f"Required file is missing: {path}")

    books = root / "references" / "books"
    found_books = {path.name for path in books.glob("*.md")} - {"INDEX.md"}
    if found_books != EXPECTED_BOOKS:
        fail(errors, f"Unexpected converted book set: {sorted(found_books)}")

    for corpus in (
        "drmax-prompt-channel-corpus",
        "drmax-channel-corpus",
        "drmax-chat-corpus",
    ):
        directory = root / "references" / corpus
        for filename in ("INDEX.md", "OMITTED-MEDIA.md"):
            if not (directory / filename).is_file():
                fail(errors, f"{corpus}/{filename} is missing")
    if not (
        root / "references" / "drmax-prompt-channel-corpus" / "CATALOG.md"
    ).is_file():
        fail(errors, "Prompt channel catalog is missing")


def validate_text(root: Path, errors: list[str]) -> None:
    checked_roots = [root / "SKILL.md", root / "references"]
    for checked in checked_roots:
        paths = [checked] if checked.is_file() else checked.rglob("*.md")
        for path in paths:
            if "references/originals" in str(path):
                continue
            text = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_TEXT:
                if forbidden in text:
                    fail(errors, f"Forbidden stale reference in {path}: {forbidden}")

    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    relative_links = re.findall(r"\]\((references/[^)#]+)(?:#[^)]+)?\)", skill_text)
    for link in relative_links:
        target = root / unquote(link)
        if not target.exists():
            fail(errors, f"Broken SKILL.md reference: {link}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    return parser.parse_args()


def main() -> int:
    root = parse_args().skill_root.resolve()
    errors: list[str] = []
    validate_structure(root, errors)
    validate_frontmatter(root / "SKILL.md", errors)
    originals = validate_manifest(root, errors)
    validate_text(root, errors)
    if errors:
        print("DrMax corpus validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"DrMax corpus validation passed: {originals} exact original files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

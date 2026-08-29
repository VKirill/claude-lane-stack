#!/usr/bin/env python3
"""Build the canonical, text-only DrMax corpus for this skill.

The importer has two deliberately different output classes:

1. ``references/originals`` contains byte-identical copies of DrMax prompt
   attachments and source prompt packs. These files are never reformatted.
2. The channel/chat archives and the GIST pocketbook are derived Markdown for
   search and reading. Every derived entry retains its source message id/date.

The script reads only the explicitly configured source directories and writes
only generated directories owned by this script.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote


DEFAULT_DOWNLOADS = Path("/home/ubuntu/downloads/drmax")
DEFAULT_CHAT = DEFAULT_DOWNLOADS / "ChatExport_2026-07-15 (1)"
DEFAULT_CHANNEL = DEFAULT_DOWNLOADS / "Telegram Channel"
DEFAULT_PROMPT_CHANNEL = DEFAULT_DOWNLOADS / "ChatExport_2026-07-19"
DEFAULT_GIST = DEFAULT_DOWNLOADS / "GIST Content Logic Skill v3.3"
DEFAULT_BOOK_PACK = DEFAULT_DOWNLOADS / "v1-5"
DEFAULT_EVIDENCE_PDF = (
    DEFAULT_DOWNLOADS / "Доказательное SEO 2026 [Максим Храповицкий] [skladchik.org] (2).pdf"
)

DRMAX_CHAT_AUTHOR_ID = "channel1682731429"
DRMAX_CHANNEL_AUTHOR_ID = "channel1436673793"
DRMAX_PROMPT_CHANNEL_AUTHOR_ID = "channel3748077780"
TEXT_ATTACHMENT_SUFFIXES = {".txt", ".md"}
MEDIA_SUFFIXES = {
    ".aac",
    ".avi",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".png",
    ".svg",
    ".tgs",
    ".webm",
    ".webp",
    ".wav",
}
GENERATED_MARKER = ".generated-by-import_drmax_sources"
MAX_ARCHIVE_LINES = 470


@dataclass(frozen=True)
class ExactCopy:
    source_kind: str
    source_file: Path
    destination: Path
    message_id: str = ""
    date: str = ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_export(export_dir: Path) -> dict[str, Any]:
    result = export_dir / "result.json"
    if not result.is_file():
        raise FileNotFoundError(f"Telegram export is missing: {result}")
    with result.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("messages"), list):
        raise ValueError(f"Telegram export has no messages array: {result}")
    return payload


def telegram_text(value: Any) -> str:
    """Render Telegram's string-or-rich-entity text without media."""

    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""

    parts: list[str] = []
    for item in value:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        label = str(item.get("text", ""))
        href = item.get("href")
        if href and label and href != label:
            parts.append(f"[{label}]({href})")
        else:
            parts.append(label)
    return "".join(parts)


def usable_attachment(message: dict[str, Any]) -> str:
    value = message.get("file")
    if not isinstance(value, str) or value.startswith("("):
        return ""
    suffix = Path(value).suffix.lower()
    if suffix in MEDIA_SUFFIXES:
        return ""
    return value


def text_attachment(message: dict[str, Any]) -> str:
    value = usable_attachment(message)
    if value and Path(value).suffix.lower() in TEXT_ATTACHMENT_SUFFIXES:
        return value
    return ""


def safe_source_file(export_dir: Path, relative: str) -> Path:
    candidate = (export_dir / relative).resolve()
    root = export_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Attachment escapes its export directory: {relative}")
    return candidate


def reset_generated_dir(path: Path) -> None:
    if path.exists():
        marker = path / GENERATED_MARKER
        if not marker.is_file():
            raise RuntimeError(f"Refusing to replace non-generated directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)
    (path / GENERATED_MARKER).write_text(
        "Owned by scripts/import_drmax_sources.py\n", encoding="utf-8"
    )


def relative_markdown_link(from_file: Path, target: Path) -> str:
    relative = Path(os.path.relpath(target, start=from_file.parent))
    return quote(str(relative), safe="/()_-.~")


def render_attachment_line(
    message: dict[str, Any], export_dir: Path, archive_file: Path, skill_root: Path
) -> str:
    relative = text_attachment(message)
    if not relative:
        return ""
    source = safe_source_file(export_dir, relative)
    if not source.is_file():
        return f"**Текстовое вложение:** `{Path(relative).name}` (нет в экспорте)"

    source_names = {
        "Telegram Channel": "telegram-channel",
        "ChatExport_2026-07-15 (1)": "telegram-chat",
        "ChatExport_2026-07-19": "drmax-prompt-channel",
    }
    source_name = source_names.get(export_dir.name, "telegram-export")
    destination = (
        skill_root
        / "references"
        / "originals"
        / source_name
        / str(message.get("id", "unknown"))
        / source.name
    )
    try:
        link = relative_markdown_link(archive_file, destination)
        return f"**Оригинальное текстовое вложение:** [{source.name}]({link})"
    except ValueError:
        return f"**Оригинальное текстовое вложение:** `{source.name}`"


def render_channel_message(
    message: dict[str, Any],
    export_dir: Path,
    archive_file: Path,
    skill_root: Path,
    source_url_base: str,
) -> str:
    message_id = message.get("id")
    date = str(message.get("date", ""))
    text = telegram_text(message.get("text")).strip()
    attachment = render_attachment_line(message, export_dir, archive_file, skill_root)
    source_url = f"{source_url_base}/{message_id}"
    body = [f"## Пост {message_id} — {date}", "", f"Источник: {source_url}", ""]
    if text:
        body.extend([text, ""])
    if attachment:
        body.extend([attachment, ""])
    return "\n".join(body).rstrip() + "\n"


def quote_context(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in text.splitlines())


def render_chat_message(
    message: dict[str, Any],
    by_id: dict[int, dict[str, Any]],
    export_dir: Path,
    archive_file: Path,
    skill_root: Path,
) -> str:
    message_id = message.get("id")
    date = str(message.get("date", ""))
    text = telegram_text(message.get("text")).strip()
    attachment = render_attachment_line(message, export_dir, archive_file, skill_root)
    body = [f"## Сообщение администраторского канала {message_id} — {date}", ""]

    reply_id = message.get("reply_to_message_id")
    if isinstance(reply_id, int) and reply_id in by_id:
        context = telegram_text(by_id[reply_id].get("text")).strip()
        if context:
            body.extend(
                [
                    f"**Контекст сообщения {reply_id}, на которое дан ответ:**",
                    "",
                    quote_context(context),
                    "",
                ]
            )

    if text:
        body.extend([text, ""])
    if attachment:
        body.extend([attachment, ""])
    return "\n".join(body).rstrip() + "\n"


def write_chunked_archive(
    *,
    messages: list[dict[str, Any]],
    destination: Path,
    archive_name: str,
    archive_description: str,
    renderer: Any,
) -> list[dict[str, Any]]:
    reset_generated_dir(destination)
    chunks: list[dict[str, Any]] = []
    current_blocks: list[tuple[dict[str, Any], str]] = []
    current_lines = 8

    def flush() -> None:
        nonlocal current_blocks, current_lines
        if not current_blocks:
            return
        first = current_blocks[0][0]
        last = current_blocks[-1][0]
        filename = f"{archive_name}-{int(first['id']):05d}-{int(last['id']):05d}.md"
        output = destination / filename
        header = (
            f"# {archive_description}: {first['id']}–{last['id']}\n\n"
            "> Производный текстовый архив. Изображения, видео, аудио, стикеры и "
            "служебные события Telegram исключены. Видимый текст сообщений не "
            "перефразировывался.\n\n---\n\n"
        )
        output.write_text(
            header + "\n---\n\n".join(block for _, block in current_blocks),
            encoding="utf-8",
        )
        chunks.append(
            {
                "file": filename,
                "first_id": first["id"],
                "last_id": last["id"],
                "first_date": first.get("date", ""),
                "last_date": last.get("date", ""),
                "messages": len(current_blocks),
                "lines": sum(1 for _ in output.open("r", encoding="utf-8")),
            }
        )
        current_blocks = []
        current_lines = 8

    for message in messages:
        placeholder = destination / "INDEX.md"
        block = renderer(message, placeholder)
        block_lines = block.count("\n") + 1
        if current_blocks and current_lines + block_lines > MAX_ARCHIVE_LINES:
            flush()
        current_blocks.append((message, block))
        current_lines += block_lines + 3
    flush()

    index_lines = [
        f"# {archive_description}",
        "",
        "> Канонический очищенный текстовый архив. Медиафайлы не копируются и не "
        "подставляются в контекст навыка.",
        "",
        f"Сообщений: **{len(messages)}**. Фрагментов: **{len(chunks)}**.",
        "",
        "| Диапазон | Даты | Сообщений | Строк | Файл |",
        "|---|---|---:|---:|---|",
    ]
    for chunk in chunks:
        index_lines.append(
            f"| {chunk['first_id']}–{chunk['last_id']} | "
            f"{chunk['first_date']} — {chunk['last_date']} | {chunk['messages']} | "
            f"{chunk['lines']} | [{chunk['file']}]({quote(chunk['file'])}) |"
        )
    (destination / "INDEX.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8"
    )
    return chunks


def collect_channel_messages(
    payload: dict[str, Any], author_id: str
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for message in payload["messages"]:
        if message.get("type") != "message":
            continue
        if message.get("from_id") != author_id:
            continue
        text = telegram_text(message.get("text")).strip()
        if text or text_attachment(message):
            selected.append(message)
    return selected


def collect_chat_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for message in payload["messages"]:
        if message.get("type") != "message":
            continue
        if message.get("from_id") != DRMAX_CHAT_AUTHOR_ID:
            continue
        text = telegram_text(message.get("text")).strip()
        if text or text_attachment(message):
            selected.append(message)
    return selected


def write_omissions_manifest(
    *,
    payload: dict[str, Any],
    author_ids: set[str],
    selected: list[dict[str, Any]],
    destination: Path,
) -> int:
    """Record non-text messages so media removal is explicit and auditable."""

    selected_ids = {message.get("id") for message in selected}
    omitted: list[dict[str, Any]] = []
    for message in payload["messages"]:
        if message.get("type") != "message":
            continue
        if message.get("from_id") not in author_ids:
            continue
        if message.get("id") in selected_ids:
            continue
        file_value = message.get("file")
        media_type = message.get("media_type") or message.get("mime_type") or ""
        omitted.append(
            {
                "id": message.get("id", ""),
                "date": message.get("date", ""),
                "media_type": media_type,
                "file": file_value if isinstance(file_value, str) else "",
            }
        )

    lines = [
        "# Исключённые нетекстовые сообщения",
        "",
        "Эти сообщения присутствуют в исходной Telegram-выгрузке, но не включены "
        "в текстовый корпус: у них нет видимого текста или поддерживаемого текстового "
        "вложения. Медиафайлы не копировались. Запись сохраняет возможность позднего "
        "OCR-аудита без ложного утверждения, что сведения из изображения уже изучены.",
        "",
        f"Сообщений: **{len(omitted)}**.",
        "",
        "| ID | Дата | Тип | Файл в исходной выгрузке |",
        "|---:|---|---|---|",
    ]
    for row in omitted:
        lines.append(
            f"| {row['id']} | {row['date']} | {row['media_type']} | "
            f"`{row['file']}` |"
        )
    (destination / "OMITTED-MEDIA.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return len(omitted)


def write_prompt_channel_catalog(
    *,
    messages: list[dict[str, Any]],
    export_dir: Path,
    destination: Path,
    skill_root: Path,
) -> None:
    """Create a compact navigation catalog without altering prompt attachments."""

    catalog = destination / "CATALOG.md"
    lines = [
        "# Каталог канала «Промпты от DrMax»",
        "",
        "Это навигация. Описание берётся из текста официального поста; сам промпт "
        "нужно открывать в `references/originals/drmax-prompt-channel/` и применять "
        "без редактирования.",
        "",
        "| ID | Дата | Начало описания | Оригинальное вложение |",
        "|---:|---|---|---|",
    ]
    for message in messages:
        text = " ".join(telegram_text(message.get("text")).split())
        summary = text[:150] + ("…" if len(text) > 150 else "")
        summary = summary.replace("|", "\\|")
        relative = text_attachment(message)
        attachment_cell = "—"
        if relative:
            source = safe_source_file(export_dir, relative)
            target = (
                skill_root
                / "references"
                / "originals"
                / "drmax-prompt-channel"
                / str(message.get("id", "unknown"))
                / source.name
            )
            attachment_cell = (
                f"[{source.name}]({relative_markdown_link(catalog, target)})"
            )
        lines.append(
            f"| {message.get('id', '')} | {message.get('date', '')} | "
            f"{summary or '—'} | {attachment_cell} |"
        )
    catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_exact(copy: ExactCopy) -> tuple[int, str]:
    copy.destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(copy.source_file, copy.destination)
    source_hash = sha256(copy.source_file)
    destination_hash = sha256(copy.destination)
    if source_hash != destination_hash:
        raise RuntimeError(
            f"Byte identity check failed: {copy.source_file} -> {copy.destination}"
        )
    return copy.source_file.stat().st_size, source_hash


def attachment_copies(
    *, export_dir: Path, payload: dict[str, Any], author_ids: set[str], source_kind: str
) -> Iterable[ExactCopy]:
    for message in payload["messages"]:
        if message.get("type") != "message" or message.get("from_id") not in author_ids:
            continue
        relative = text_attachment(message)
        if not relative:
            continue
        source = safe_source_file(export_dir, relative)
        if not source.is_file():
            continue
        destination = (
            Path(source_kind)
            / str(message.get("id", "unknown"))
            / source.name
        )
        yield ExactCopy(
            source_kind=source_kind,
            source_file=source,
            destination=destination,
            message_id=str(message.get("id", "")),
            date=str(message.get("date", "")),
        )


def tree_copies(
    *, source_root: Path, source_kind: str, exclude_names: set[str] | None = None
) -> Iterable[ExactCopy]:
    excluded = exclude_names or set()
    if not source_root.is_dir():
        return
    for source in sorted(source_root.rglob("*")):
        if not source.is_file() or source.suffix.lower() not in TEXT_ATTACHMENT_SUFFIXES:
            continue
        if source.name in excluded or source.name.startswith("usage-notes-"):
            continue
        yield ExactCopy(
            source_kind=source_kind,
            source_file=source,
            destination=Path(source_kind) / source.relative_to(source_root),
        )


def build_originals(
    *,
    skill_root: Path,
    chat_dir: Path,
    chat_payload: dict[str, Any],
    channel_dir: Path,
    channel_payload: dict[str, Any],
    prompt_channel_dir: Path,
    prompt_channel_payload: dict[str, Any],
    book_pack_dir: Path,
    gist_dir: Path,
) -> list[dict[str, Any]]:
    originals = skill_root / "references" / "originals"
    reset_generated_dir(originals)

    planned: list[ExactCopy] = []
    planned.extend(
        attachment_copies(
            export_dir=channel_dir,
            payload=channel_payload,
            author_ids={DRMAX_CHANNEL_AUTHOR_ID},
            source_kind="telegram-channel",
        )
    )
    planned.extend(
        attachment_copies(
            export_dir=prompt_channel_dir,
            payload=prompt_channel_payload,
            author_ids={DRMAX_PROMPT_CHANNEL_AUTHOR_ID},
            source_kind="drmax-prompt-channel",
        )
    )
    planned.extend(
        attachment_copies(
            export_dir=chat_dir,
            payload=chat_payload,
            author_ids={DRMAX_CHAT_AUTHOR_ID, DRMAX_CHANNEL_AUTHOR_ID},
            source_kind="telegram-chat",
        )
    )
    planned.extend(
        tree_copies(
            source_root=book_pack_dir / "Prompts",
            source_kind="book-v1.5-prompts",
        )
    )

    gist_v33 = gist_dir / "GIST Content Logic Skill-v-3-3.md"
    if not gist_v33.is_file():
        raise FileNotFoundError(f"GIST v3.3 Markdown source is missing: {gist_v33}")
    planned.append(
        ExactCopy(
            source_kind="gist-v3.3",
            source_file=gist_v33,
            destination=Path("gist-v3.3") / gist_v33.name,
        )
    )

    manifest: list[dict[str, Any]] = []
    seen_destinations: set[Path] = set()
    for copy in planned:
        destination = originals / copy.destination
        if destination in seen_destinations:
            continue
        seen_destinations.add(destination)
        size, digest = copy_exact(
            ExactCopy(
                source_kind=copy.source_kind,
                source_file=copy.source_file,
                destination=destination,
                message_id=copy.message_id,
                date=copy.date,
            )
        )
        manifest.append(
            {
                "source_kind": copy.source_kind,
                "message_id": copy.message_id,
                "date": copy.date,
                "bytes": size,
                "sha256": digest,
                "source_file": str(copy.source_file),
                "destination": str(destination.relative_to(skill_root)),
            }
        )

    manifest.sort(key=lambda row: (row["source_kind"], row["destination"]))
    tsv_header = [
        "source_kind",
        "message_id",
        "date",
        "bytes",
        "sha256",
        "source_file",
        "destination",
    ]
    tsv_lines = ["\t".join(tsv_header)]
    for row in manifest:
        tsv_lines.append("\t".join(str(row[key]) for key in tsv_header))
    (originals / "MANIFEST.tsv").write_text(
        "\n".join(tsv_lines) + "\n", encoding="utf-8"
    )
    (originals / "SHA256SUMS").write_text(
        "\n".join(f"{row['sha256']}  {row['destination']}" for row in manifest) + "\n",
        encoding="utf-8",
    )

    counts: dict[str, int] = {}
    for row in manifest:
        counts[row["source_kind"]] = counts.get(row["source_kind"], 0) + 1
    index_lines = [
        "# Неизменяемые оригиналы DrMax",
        "",
        "Все файлы в подкаталогах скопированы побайтово из указанных источников. "
        "Их нельзя исправлять, переформатировать, сокращать или переводить. Для "
        "пояснений создавайте отдельный производный reference-файл.",
        "",
        "| Корпус | Файлов | Назначение |",
        "|---|---:|---|",
    ]
    descriptions = {
        "drmax-prompt-channel": "Оригиналы из официального канала «Промпты от DrMax»",
        "telegram-channel": "Текстовые вложения официального Telegram-канала",
        "telegram-chat": "Текстовые вложения из сообщений администраторского канала в чате",
        "book-v1.5-prompts": "Промпты из книжного пакета v1.5",
        "gist-v3.3": "Оригинальный GIST Content Logic Skill v3.3",
    }
    for key in sorted(counts):
        index_lines.append(
            f"| `{key}/` | {counts[key]} | {descriptions.get(key, '')} |"
        )
    index_lines.extend(
        [
            "",
            "Контроль происхождения: [MANIFEST.tsv](MANIFEST.tsv).",
            "Контроль целостности: [SHA256SUMS](SHA256SUMS).",
        ]
    )
    (originals / "INDEX.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8"
    )
    return manifest


HEADING_REPAIRS = {
    "А КТИВАЦИЯ": "АКТИВАЦИЯ",
    "С КИЛЛА": "СКИЛЛА",
    "СК ИЛЛОМ": "СКИЛЛОМ",
    "ПО ЛНЫЙ": "ПОЛНЫЙ",
    "СУЩЕСТВУЮЩ УЮ": "СУЩЕСТВУЮЩУЮ",
    "СТРА НИЦУ": "СТРАНИЦУ",
    "ТО ЛЬКО": "ТОЛЬКО",
    "Д ЛЯ": "ДЛЯ",
    "КОМБИНИРОВ АННЫЕ": "КОМБИНИРОВАННЫЕ",
    "НЕСКО ЛЬКИМИ": "НЕСКОЛЬКИМИ",
    "РО ЛЯМИ": "РОЛЯМИ",
    "КА К": "КАК",
    "ИСПРА ВИТЬ": "ИСПРАВИТЬ",
    "PATTER NS": "PATTERNS",
    "ПРИЛО ЖЕНИЕ": "ПРИЛОЖЕНИЕ",
    "ПРОМПТО В": "ПРОМПТОВ",
    "Б ЫСТРАЯ": "БЫСТРАЯ",
    "ПРО ВЕРКА": "ПРОВЕРКА",
    "ОДНО ГО": "ОДНОГО",
    "БЛО КА": "БЛОКА",
    "БЫСТРЫ Е": "БЫСТРЫЕ",
    "ИНТ ЕГРАЦИЯ": "ИНТЕГРАЦИЯ",
    "CLA UDE": "CLAUDE",
    "PROJECT S": "PROJECTS",
    "C USTO M": "CUSTOM",
    "А ВТОПАЙПЛАЙНАХ": "АВТОПАЙПЛАЙНАХ",
    "С ОЗДАНИЯ": "СОЗДАНИЯ",
    "СПИСКАКАНДИДАТОВ": "СПИСКА КАНДИДАТОВ",
    "МЕТА -ПОЛЕЙ": "МЕТА-ПОЛЕЙ",
    "( STEP": "(STEP",
    "ПО ЛЕЙ": "ПОЛЕЙ",
    "С ЛУЧАИ": "СЛУЧАИ",
}


def repair_heading(text: str) -> str:
    repaired = " ".join(text.strip().split())
    for broken, fixed in HEADING_REPAIRS.items():
        repaired = repaired.replace(broken, fixed)
    return repaired


def extract_pdf_pages(pdf: Path) -> list[list[str]]:
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF source is missing: {pdf}")
    process = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    text = process.stdout.decode("utf-8", errors="strict")
    return [page.splitlines() for page in text.split("\f") if page.strip()]


def repeated_pdf_margins(pages: list[list[str]]) -> set[str]:
    candidates: Counter[str] = Counter()
    for page in pages:
        nonempty = [" ".join(line.split()) for line in page if line.strip()]
        for line in nonempty[:3] + nonempty[-3:]:
            if len(line) >= 5:
                candidates[line] += 1
    minimum = max(4, len(pages) // 5)
    return {line for line, count in candidates.items() if count >= minimum}


def repair_pdf_line(raw: str) -> str:
    leading = raw[: len(raw) - len(raw.lstrip())]
    content = raw.lstrip()
    for broken, fixed in HEADING_REPAIRS.items():
        content = content.replace(broken, fixed)
    return leading + content


def merge_pdf_heading_lines(page: list[str]) -> list[str]:
    merged: list[str] = []
    for raw in page:
        repaired = repair_pdf_line(raw)
        candidate = " ".join(repaired.split())
        if merged and candidate and candidate.upper() == candidate:
            previous = " ".join(merged[-1].split())
            combined = f"{previous} {candidate}".strip()
            if (
                previous
                and previous.upper() == previous
                and len(combined) <= 180
                and re.search(r"[А-ЯA-Z]", previous)
                and (previous.startswith(("ГЛАВА", "ЧАСТЬ", "ПРИЛО")) or raw[:1].isspace())
            ):
                merged[-1] = combined
                continue
        merged.append(repaired)
    return merged


def markdown_from_pdf(
    pdf: Path,
    output: Path,
    title: str,
    *,
    skip_pages: set[int] | None = None,
) -> dict[str, Any]:
    pages = extract_pdf_pages(pdf)
    repeated = repeated_pdf_margins(pages)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {title}",
        "",
        f"> Конвертировано непосредственно из `{pdf}`.",
        f"> Страниц: {len(pages)}. SHA-256: `{sha256(pdf)}`.",
        "> Колонтитулы и номера страниц удалены; номера исходных страниц сохранены "
        "HTML-комментариями. Формулировки и промпты не перефразировывались.",
        "",
    ]
    heading_pattern = re.compile(
        r"^(?:ГЛАВА\s+\d+|ЧАСТЬ\s+[IVX]+|ПРИЛО|ОГЛАВЛЕНИЕ|"
        r"[0-9]+\.[0-9]+\.|[А-Я]\.\d+\.)"
    )
    page_number = re.compile(r"^(?:стр\.?\s*)?\d{1,4}$", re.IGNORECASE)

    omitted = skip_pages or set()
    for page_index, page in enumerate(pages, start=1):
        if page_index in omitted:
            continue
        lines.extend([f"<!-- source-page: {page_index} -->", ""])
        previous_blank = True
        for raw in merge_pdf_heading_lines(page):
            normalized = " ".join(raw.split())
            if not normalized:
                if not previous_blank:
                    lines.append("")
                previous_blank = True
                continue
            if normalized in repeated or page_number.fullmatch(normalized):
                continue
            if normalized.startswith("DrMax:") and len(normalized) < 180:
                continue

            candidate = repair_heading(normalized)
            uppercase_heading = (
                candidate.upper() == candidate
                and len(candidate.split()) >= 3
                and bool(re.search(r"[А-ЯA-Z]", candidate))
                and not candidate.startswith(("●", "•", "➡", "→"))
            )
            if (
                len(candidate) <= 180
                and (heading_pattern.match(candidate) or uppercase_heading)
            ):
                lines.extend([f"## {candidate}", ""])
                previous_blank = True
                continue
            lines.append(raw.rstrip())
            previous_blank = False
        if lines and lines[-1]:
            lines.append("")

    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "file": output.name,
        "title": title,
        "pages": len(pages),
        "bytes": output.stat().st_size,
        "source": str(pdf),
        "sha256": sha256(pdf),
    }


def build_books(
    *, skill_root: Path, gist_dir: Path, book_pack_dir: Path, evidence_pdf: Path
) -> list[dict[str, Any]]:
    destination = skill_root / "references" / "books"
    reset_generated_dir(destination)
    prompt_book_candidates = sorted(book_pack_dir.glob("DrMax - Prompt Engineering*.pdf"))
    if len(prompt_book_candidates) != 1:
        raise RuntimeError(
            f"Expected one Prompt Engineering PDF in {book_pack_dir}, "
            f"found {len(prompt_book_candidates)}"
        )
    sources = [
        (
            gist_dir / "10425108_x5159d35p2100w847q3353o1113d189.pdf",
            destination / "gist-content-logic-v3.3-pocketbook.md",
            "GIST в примерах: как писать контент, который невозможно скопировать",
            {1, 2, 3, 4, 5},
        ),
        (
            prompt_book_candidates[0],
            destination / "prompt-engineering-for-seo-strategists-v1.5.md",
            "Промптоведение для SEO-стратегов",
            set(),
        ),
        (
            evidence_pdf,
            destination / "evidence-based-seo.md",
            "Доказательное SEO",
            set(),
        ),
    ]
    records = [
        markdown_from_pdf(pdf, output, title, skip_pages=skip_pages)
        for pdf, output, title, skip_pages in sources
    ]
    index_lines = [
        "# Книги DrMax — конвертированный корпус",
        "",
        "Markdown создан заново непосредственно из исходных PDF в "
        "`/home/ubuntu/downloads/drmax`. Старые конверсии навыка не использованы.",
        "",
        "| Книга | Страниц | Markdown | SHA-256 исходного PDF |",
        "|---|---:|---|---|",
    ]
    for record in records:
        index_lines.append(
            f"| {record['title']} | {record['pages']} | "
            f"[{record['file']}]({quote(record['file'])}) | `{record['sha256']}` |"
        )
    (destination / "INDEX.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8"
    )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--chat", type=Path, default=DEFAULT_CHAT)
    parser.add_argument("--channel", type=Path, default=DEFAULT_CHANNEL)
    parser.add_argument("--prompt-channel", type=Path, default=DEFAULT_PROMPT_CHANNEL)
    parser.add_argument("--gist", type=Path, default=DEFAULT_GIST)
    parser.add_argument("--book-pack", type=Path, default=DEFAULT_BOOK_PACK)
    parser.add_argument("--evidence-pdf", type=Path, default=DEFAULT_EVIDENCE_PDF)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = args.skill_root.resolve()
    chat_dir = args.chat.resolve()
    channel_dir = args.channel.resolve()
    prompt_channel_dir = args.prompt_channel.resolve()
    gist_dir = args.gist.resolve()
    book_pack_dir = args.book_pack.resolve()
    evidence_pdf = args.evidence_pdf.resolve()

    chat_payload = load_export(chat_dir)
    channel_payload = load_export(channel_dir)
    prompt_channel_payload = load_export(prompt_channel_dir)

    manifest = build_originals(
        skill_root=skill_root,
        chat_dir=chat_dir,
        chat_payload=chat_payload,
        channel_dir=channel_dir,
        channel_payload=channel_payload,
        prompt_channel_dir=prompt_channel_dir,
        prompt_channel_payload=prompt_channel_payload,
        book_pack_dir=book_pack_dir,
        gist_dir=gist_dir,
    )

    channel_messages = collect_channel_messages(
        channel_payload, DRMAX_CHANNEL_AUTHOR_ID
    )
    channel_destination = skill_root / "references" / "drmax-channel-corpus"
    channel_chunks = write_chunked_archive(
        messages=channel_messages,
        destination=channel_destination,
        archive_name="channel",
        archive_description="DrMax SEO — официальный канал",
        renderer=lambda message, archive_file: render_channel_message(
            message,
            channel_dir,
            archive_file,
            skill_root,
            "https://t.me/drmaxseo",
        ),
    )
    channel_omissions = write_omissions_manifest(
        payload=channel_payload,
        author_ids={DRMAX_CHANNEL_AUTHOR_ID},
        selected=channel_messages,
        destination=channel_destination,
    )

    prompt_channel_messages = collect_channel_messages(
        prompt_channel_payload, DRMAX_PROMPT_CHANNEL_AUTHOR_ID
    )
    prompt_channel_destination = (
        skill_root / "references" / "drmax-prompt-channel-corpus"
    )
    prompt_channel_chunks = write_chunked_archive(
        messages=prompt_channel_messages,
        destination=prompt_channel_destination,
        archive_name="prompt-channel",
        archive_description="Промпты от DrMax — официальный канал",
        renderer=lambda message, archive_file: render_channel_message(
            message,
            prompt_channel_dir,
            archive_file,
            skill_root,
            "https://t.me/drmaxprompt",
        ),
    )
    prompt_channel_omissions = write_omissions_manifest(
        payload=prompt_channel_payload,
        author_ids={DRMAX_PROMPT_CHANNEL_AUTHOR_ID},
        selected=prompt_channel_messages,
        destination=prompt_channel_destination,
    )
    write_prompt_channel_catalog(
        messages=prompt_channel_messages,
        export_dir=prompt_channel_dir,
        destination=prompt_channel_destination,
        skill_root=skill_root,
    )

    chat_messages = collect_chat_messages(chat_payload)
    by_id = {
        message["id"]: message
        for message in chat_payload["messages"]
        if isinstance(message.get("id"), int)
    }
    chat_destination = skill_root / "references" / "drmax-chat-corpus"
    chat_chunks = write_chunked_archive(
        messages=chat_messages,
        destination=chat_destination,
        archive_name="chat",
        archive_description=(
            "DrMax SEO Chat — сообщения от имени администраторского канала с контекстом"
        ),
        renderer=lambda message, archive_file: render_chat_message(
            message, by_id, chat_dir, archive_file, skill_root
        ),
    )
    chat_omissions = write_omissions_manifest(
        payload=chat_payload,
        author_ids={DRMAX_CHAT_AUTHOR_ID},
        selected=chat_messages,
        destination=chat_destination,
    )

    books = build_books(
        skill_root=skill_root,
        gist_dir=gist_dir,
        book_pack_dir=book_pack_dir,
        evidence_pdf=evidence_pdf,
    )

    print(
        json.dumps(
            {
                "exact_original_files": len(manifest),
                "channel_messages": len(channel_messages),
                "channel_chunks": len(channel_chunks),
                "channel_omissions": channel_omissions,
                "prompt_channel_messages": len(prompt_channel_messages),
                "prompt_channel_chunks": len(prompt_channel_chunks),
                "prompt_channel_omissions": prompt_channel_omissions,
                "chat_messages": len(chat_messages),
                "chat_chunks": len(chat_chunks),
                "chat_omissions": chat_omissions,
                "books": books,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

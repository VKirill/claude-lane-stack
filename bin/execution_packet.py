#!/usr/bin/env python3
"""Deterministic, source-backed context packets for lane writers.

The packet is data-only: it does not expand globs or rewrite source text.
Files named in interfaces/objective become path pointers (interface_refs),
not dumped source. Explicit read_first/owns still inline content.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any


PACKET_SCHEMA_VERSION = 1
_PACKET_BEGIN = "<<<LANE_EXECUTION_PACKET_JSON:BEGIN>>>"
_PACKET_END = "<<<LANE_EXECUTION_PACKET_JSON:END>>>"
_SECRET_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
}
_SECRET_SUFFIXES = (".pem", ".p12", ".key")
_SKIP_TREE_DIRS = {".git", ".gitnexus", ".agents", "node_modules"}
# ponytail: harvest only slash-paths that already exist; cap stops a novel-length
# interfaces dump. Upgrade: PM context_selectors, or fail pre-dispatch on unnamed refs.
_MAX_INTERFACE_REFS = 20
_INTERFACE_PATH_RE = re.compile(
    r"(?<![\w./])((?:[\w][\w.-]*/)+[\w.-]+\.[A-Za-z][\w.-]*)"
    r"(?::(\d+)(?:-(\d+))?)?"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_hash(value: object) -> str:
    return _sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _as_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _is_secret(relative: Path) -> bool:
    parts = {part.lower() for part in relative.parts}
    if parts & {".ssh", ".aws", ".gnupg"}:
        return True
    name = relative.name.lower()
    return (
        name in _SECRET_NAMES
        or name.startswith(".env.")
        or name.startswith(".env-")
        or name.endswith(_SECRET_SUFFIXES)
    )


def _safe_relative(project_cwd: Path, raw: object) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "path must be a non-empty string"
    supplied = Path(raw)
    root = project_cwd.resolve(strict=False)
    lexical = supplied if not supplied.is_absolute() else Path(os.path.relpath(supplied, root))
    if _is_secret(lexical):
        return lexical, "secret path is excluded"
    try:
        candidate = (supplied if supplied.is_absolute() else root / supplied).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        return None, f"cannot resolve path: {exc}"
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None, "path escapes project_cwd"
    if _is_secret(relative):
        return relative, "secret path is excluded"
    return relative, None


def _read_text_record(
    project_cwd: Path,
    relative: Path,
    *,
    ranges: list[dict[str, int]],
    sources: list[str],
    include_full: bool = False,
) -> dict[str, Any]:
    path = project_cwd / relative
    record: dict[str, Any] = {
        "path": relative.as_posix(),
        "sources": sorted(set(sources)),
        "ranges": ranges,
    }
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            record.update({"status": "unsupported", "error": "path is not a regular file"})
            return record
    except FileNotFoundError:
        record.update({"status": "missing", "error": "file does not exist"})
        return record
    except OSError as exc:
        record.update({"status": "error", "error": str(exc)})
        return record
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        record.update({"status": "missing", "error": "file does not exist"})
        return record
    except OSError as exc:
        record.update({"status": "error", "error": str(exc)})
        return record
    record["sha256"] = _sha256(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        record.update({"status": "binary", "error": "file is not valid UTF-8"})
        return record
    record["status"] = "ok"
    if include_full:
        record["content"] = text
    if not ranges:
        return record
    lines = text.splitlines(keepends=True)
    selected: list[dict[str, Any]] = []
    for selection in ranges:
        start, end = selection["start_line"], selection["end_line"]
        if start > len(lines) or end > len(lines):
            selected.append(
                {
                    "start_line": start,
                    "end_line": end,
                    "status": "error",
                    "error": f"line range {start}-{end} exceeds {len(lines)} lines",
                }
            )
            continue
        selected.append(
            {
                "start_line": start,
                "end_line": end,
                "status": "ok",
                "content": "".join(lines[start - 1 : end]),
            }
        )
    record["selected_contents"] = selected
    return record


def _selector(raw: object) -> tuple[str | None, dict[str, int] | None, str | None]:
    if not isinstance(raw, dict):
        return None, None, "context selector must be an object"
    path = raw.get("path", raw.get("file"))
    if not isinstance(path, str) or not path.strip():
        return None, None, "context selector requires path"
    start, end = raw.get("start_line"), raw.get("end_line")
    if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
        return path, None, "context selector requires positive start_line <= end_line"
    return path, {"start_line": start, "end_line": end}, None


def _task_prose(task: dict) -> str:
    chunks: list[str] = []
    for key in ("interfaces", "objective"):
        value = task.get(key)
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, list):
            chunks.extend(item for item in value if isinstance(item, str))
    return "\n".join(chunks)


def _never_touch_match(posix: str, never_touch: list[object]) -> bool:
    for pattern in never_touch:
        if not isinstance(pattern, str) or not pattern:
            continue
        if fnmatch.fnmatchcase(posix, pattern) or fnmatch.fnmatchcase(Path(posix).name, pattern):
            return True
    return False


def _interface_ref_records(
    refs: list[tuple[str, dict[str, int] | None]], dumped: set[str]
) -> list[dict[str, Any]]:
    """Path pointers only. An unadorned path wins over a :start-end mention."""
    by_path: dict[str, dict[str, Any]] = {}
    for raw_path, line_range in refs:
        if raw_path in dumped:
            continue
        current = by_path.get(raw_path)
        if current is None:
            record: dict[str, Any] = {"path": raw_path}
            if line_range:
                record.update(line_range)
            by_path[raw_path] = record
        elif line_range is None:
            by_path[raw_path] = {"path": raw_path}
    return list(by_path.values())


def _interface_refs(root: Path, task: dict) -> list[tuple[str, dict[str, int] | None]]:
    """Existing project files named in interfaces/objective, optional :start-end."""
    never_touch = _as_list(task.get("never_touch"))
    found: list[tuple[str, dict[str, int] | None]] = []
    seen: set[tuple[str, int, int] | tuple[str]] = set()
    for match in _INTERFACE_PATH_RE.finditer(_task_prose(task)):
        relative, error = _safe_relative(root, match.group(1))
        if relative is None or error or any(part in _SKIP_TREE_DIRS for part in relative.parts):
            continue
        posix = relative.as_posix()
        if _never_touch_match(posix, never_touch):
            continue
        path = root / relative
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        start_raw, end_raw = match.group(2), match.group(3)
        line_range = None
        if start_raw is not None:
            start_i = int(start_raw)
            end_i = int(end_raw) if end_raw is not None else start_i
            if start_i >= 1 and end_i >= start_i:
                line_range = {"start_line": start_i, "end_line": end_i}
        key: tuple[str, int, int] | tuple[str] = (
            (posix, line_range["start_line"], line_range["end_line"]) if line_range else (posix,)
        )
        if key in seen:
            continue
        seen.add(key)
        found.append((posix, line_range))
        if len(found) >= _MAX_INTERFACE_REFS:
            break
    return found


def _explicit_owned_files(project_cwd: Path, owns_paths: list[object]) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for raw in owns_paths:
        if not isinstance(raw, str):
            continue
        relative, error = _safe_relative(project_cwd, raw)
        if relative is None or error is not None:
            continue
        path = project_cwd / relative
        if path.is_file() or (not path.exists() and not any(char in raw for char in "*?")):
            found.append((relative, "owned_path"))
        elif any(char in raw for char in "*?[]"):
            # A literal path wins; only then treat metacharacters as a glob.
            continue
    return found


def _git(project_cwd: Path, *args: str) -> tuple[bytes | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_cwd), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return None, str(exc)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        return None, detail or f"git exited {result.returncode}"
    return result.stdout, None


def _source_tree_digest(project_cwd: Path) -> tuple[str | None, list[str]]:
    """Hash current source files, including untracked files, without secrets."""
    manifest: list[dict[str, Any]] = []
    errors: list[str] = []
    root = project_cwd.resolve(strict=False)
    paths, error = _git(root, "ls-files", "-co", "--exclude-standard", "-z")
    if paths is None:
        return None, [error or "cannot enumerate source files"]
    for raw_path in sorted(set(paths.split(b"\0"))):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8", errors="surrogateescape"))
        if not relative.parts or relative.parts[0] in _SKIP_TREE_DIRS:
            continue
        path = root / relative
        if _is_secret(relative):
            try:
                stat = path.lstat()
                manifest.append(
                    {
                        "path": relative.as_posix(),
                        "secret": True,
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                    }
                )
            except OSError as exc:
                errors.append(f"{relative}: {exc}")
            continue
        try:
            if path.is_symlink():
                manifest.append({"path": relative.as_posix(), "symlink": os.readlink(path)})
            elif path.is_file():
                manifest.append({"path": relative.as_posix(), "sha256": _sha256(path.read_bytes())})
            elif not path.exists():
                manifest.append({"path": relative.as_posix(), "missing": True})
            else:
                errors.append(f"{relative}: unsupported source entry")
        except OSError as exc:
            errors.append(f"{relative}: {exc}")
    return _json_hash(manifest) if not errors else None, errors


def _working_tree_snapshot(project_cwd: Path, *, full_tree: bool = False) -> dict[str, Any]:
    # Content, not git-index stat-cache bytes: git status can refresh that cache.
    head, error = _git(project_cwd, "rev-parse", "HEAD")
    snapshot: dict[str, Any] = {"head": head.decode().strip() if head else None}
    errors = [error] if error else []
    if full_tree:
        snapshot["tree_sha256"], tree_errors = _source_tree_digest(project_cwd)
        errors.extend(tree_errors)
    snapshot.update(complete=not errors, errors=errors)
    return snapshot


def _scope(task: dict) -> dict[str, Any]:
    keys = ("read_first", "owns_paths", "impact_targets")
    return {key: task[key] for key in keys if key in task}


def _impact_targets(root: Path, task: dict) -> list[str]:
    targets = task.get("impact_targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("declare non-empty impact_targets as path::symbol in the task")
    owns = _as_list(task.get("owns_paths", task.get("files", [])))
    for target in targets:
        if not isinstance(target, str):
            raise ValueError("impact target must be path::symbol")
        file, separator, name = target.rpartition("::")
        relative, error = _safe_relative(root, file)
        if not separator or not name or name.startswith("-") or error or relative is None or relative.as_posix() != file:
            raise ValueError("impact target must use a canonical project-relative path::symbol")
        if not any(isinstance(pattern, str) and (
            file == pattern or fnmatch.fnmatchcase(file, pattern)
            or file.startswith(pattern.rstrip("/") + "/")
        ) for pattern in owns):
            raise ValueError(f"impact target {target} is outside owns_paths")
    return list(dict.fromkeys(targets))


def _index_snapshot(project_cwd: Path) -> dict[str, Any]:
    meta_path = project_cwd / ".gitnexus" / "meta.json"
    try:
        raw = meta_path.read_bytes()
        meta = json.loads(raw)
        if not isinstance(meta, dict):
            raise ValueError("GitNexus metadata must be an object")
    except (OSError, ValueError) as exc:
        return {"error": str(exc)}
    return {
        "meta_sha256": _sha256(raw),
        "last_commit": meta.get("lastCommit"),
        "indexed_at": meta.get("indexedAt"),
    }


def build_execution_packet(project_cwd: Path, task: dict, task_file: Path) -> dict[str, Any]:
    """Build a fresh packet from explicit task declarations and current files."""
    root = Path(project_cwd).expanduser().resolve(strict=False)
    task_path = Path(task_file).expanduser().resolve(strict=False)
    try:
        task_raw = task_path.read_bytes()
        task_sha256 = _sha256(task_raw)
        task_source = task_raw.decode("utf-8")
    except OSError as exc:
        task_raw, task_source, task_sha256 = b"", "", None
        task_error = str(exc)
    except UnicodeDecodeError as exc:
        task_source, task_sha256 = "", _sha256(task_raw)
        task_error = f"task file is not valid UTF-8: {exc}"
    else:
        task_error = None

    entries: dict[str, dict[str, Any]] = {}
    def add(raw_path: object, source: str, line_range: dict[str, int] | None = None, error: str | None = None) -> None:
        relative, safety_error = _safe_relative(root, raw_path)
        if relative is None:
            key = str(raw_path)
            entries.setdefault(key, {"path": key, "status": "error", "error": safety_error})
            return
        key = relative.as_posix()
        if safety_error:
            entries.setdefault(key, {"path": key, "status": "excluded", "error": safety_error})
            return
        if error:
            entries[key] = {"path": key, "status": "error", "error": error}
            return
        current = entries.get(key)
        if current is None:
            entries[key] = {
                "path": key,
                "sources": [source],
                "ranges": [line_range] if line_range else [],
                "full": line_range is None,
            }
        else:
            if source == "context_selector" and "context_selector" not in current.get("sources", []):
                current["full"] = False
                current["ranges"] = []
            current.setdefault("sources", []).append(source)
            if line_range and line_range not in current.setdefault("ranges", []):
                current["ranges"].append(line_range)
            if line_range is None:
                current["full"] = True

    read_first = _as_list(task.get("read_first"))
    for raw_path in read_first:
        add(raw_path, "read_first")
    owns_paths = _as_list(task.get("owns_paths", task.get("files", [])))
    for relative, source in _explicit_owned_files(root, owns_paths):
        add(relative.as_posix(), source)
    for raw_path in owns_paths:
        relative, error = _safe_relative(root, raw_path)
        if relative is None or error:
            add(raw_path, "owned_path")
        elif relative.as_posix() not in entries:
            # Ownership globs can span an entire repository. Report the gap;
            # the task author selects relevant files/ranges, not a blind sweep.
            entries[relative.as_posix()] = {
                "path": relative.as_posix(), "status": "deferred",
                "error": "Ownership pattern/directory is not source context. Declare explicit read_first files or context_selectors; writer must obtain missing context.",
            }
    selectors = task.get("context_selectors", [])
    if not isinstance(selectors, list):
        selectors = []
    for raw_selector in selectors:
        raw_path, line_range, selector_error = _selector(raw_selector)
        if selector_error:
            add(raw_path or "<invalid-context-selector>", "context_selector", error=selector_error)
        elif raw_path is not None and line_range is not None:
            add(raw_path, "context_selector", line_range)
    interface_refs = _interface_ref_records(_interface_refs(root, task), set(entries))

    files: list[dict[str, Any]] = []
    for key in sorted(entries):
        entry = entries[key]
        if entry.get("status") in {"error", "excluded", "deferred"}:
            files.append(entry)
            continue
        files.append(
            _read_text_record(
                root,
                Path(key),
                ranges=entry.get("ranges", []),
                sources=entry.get("sources", []),
                include_full=bool(entry.get("full")),
            )
        )
    source_hashes = {
        item["path"]: item["sha256"]
        for item in files
        if item.get("status") in {"ok", "binary"} and item.get("sha256")
    }
    packet: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_type": "lane_execution_packet",
        "project_cwd": str(root),
        "task_file": str(task_path),
        "task_sha256": task_sha256,
        "scope": _scope(task),
        "files": files,
        "interface_refs": interface_refs,
        "source_hashes": source_hashes,
        "source_snapshot_sha256": _json_hash(source_hashes),
        "constraints": {
            key: task.get(key, [])
            for key in (
                "verification",
                "never_touch",
                "interfaces",
                "invariants",
                "out_of_scope",
                "acceptance",
                "expected_outputs",
            )
            if key in task
        },
        "working_tree": _working_tree_snapshot(root),
    }
    if task_error:
        packet["task_source_error"] = task_error
    receipt = task.get("impact_receipt")
    if receipt is not None:
        packet["impact_receipt"] = validate_impact_receipt(
            receipt, project_cwd=root, task=task, packet=packet
        )
    return packet


def render_execution_packet(packet: dict) -> str:
    """Render one machine-delimited JSON block; values remain source data."""
    # Escaping '<' ensures source data cannot produce a delimiter line; JSON
    # already escapes embedded newlines as ``\\n``.
    encoded = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True).replace(
        "<", "\\u003c"
    )
    return f"\n{_PACKET_BEGIN}\n{encoded}\n{_PACKET_END}\n"


def refresh_execution_packet(
    prompt: str, project_cwd: Path, task: dict, task_file: Path
) -> str:
    """Replace only the packet block, preserving writer text and raw task YAML."""
    packet = render_execution_packet(build_execution_packet(project_cwd, task, task_file))
    begin_line = "\n" + _PACKET_BEGIN + "\n"
    end_line = "\n" + _PACKET_END + "\n"
    begin = prompt.find(begin_line)
    if begin >= 0:
        end = prompt.find(end_line, begin + len(begin_line))
        if end >= 0:
            prompt = prompt[:begin] + prompt[end + len(end_line) :]
    header = "\n\n---\nPROJECT_CWD:"
    header_index = prompt.find(header)
    if header_index < 0:
        return prompt.rstrip() + packet
    return prompt[:header_index] + packet + prompt[header_index:]


def _impact_error(result: object, target: str) -> str | None:
    if not isinstance(target, str) or not target:
        return "impact target is absent or invalid"
    if not isinstance(result, dict) or result.get("error"):
        return "impact result is absent or errored"
    if result.get("risk") not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return "impact risk is unknown"
    def incomplete(value: object) -> bool:
        if isinstance(value, dict):
            return any((key in {"partial", "truncated"} and item is True)
                       or incomplete(item) for key, item in value.items())
        return isinstance(value, list) and any(incomplete(item) for item in value)
    if incomplete(result) or not result.get("impactedCount"):
        return "impact result is partial, truncated or empty"
    file, separator, name = target.rpartition("::")
    identity = result.get("target", {})
    if not isinstance(identity, dict) or identity.get("name") != (name if separator else target):
        return "impact target does not match"
    if separator and identity.get("filePath") != file:
        return "impact file does not match"
    if result.get("direction") != "upstream":
        return "impact direction is not upstream"
    return None


def _graph_command(root: Path, args: list[str]) -> str:
    runner = root / ".gitnexus" / "run.cjs"
    if not runner.is_file():
        raise ValueError("project .gitnexus/run.cjs is missing; initialize GitNexus first")
    command = ["node", str(runner), *args]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise ValueError(f"GitNexus {args[0]} failed (exit {result.returncode}); no reusable receipt")
    return result.stdout


def capture_impact_receipt(root: Path, task: dict, task_file: Path, targets: list[str]) -> dict:
    """Run analysis ourselves; never rebind an old saved result to fresh files."""
    root = root.resolve()
    declared = _impact_targets(root, task)
    if targets and set(targets) != set(declared):
        raise ValueError("requested impact targets must exactly match task impact_targets")
    targets = declared
    before = _working_tree_snapshot(root, full_tree=True)
    if not before["complete"]:
        raise ValueError("cannot snapshot project sources")
    _graph_command(root, ["analyze", "--index-only"])
    indexed = _working_tree_snapshot(root, full_tree=True)
    if indexed != before:
        raise ValueError("sources changed during indexing (including generated instructions); rerun capture")
    index = _index_snapshot(root)
    if index.get("error") or index.get("last_commit") != indexed["head"]:
        raise ValueError("GitNexus index is not bound to current HEAD")
    reports = []
    for target in dict.fromkeys(targets):
        file, separator, name = target.rpartition("::")
        command = ["impact", name if separator else target, "--direction", "upstream", "--repo", "."]
        if separator:
            relative, error = _safe_relative(root, file)
            if relative is None or error or relative.as_posix() != file:
                raise ValueError("target file must be a canonical project-relative path")
            command.extend(["--file", file])
        output = _graph_command(root, command)
        start = output.find("{")
        try:
            result, _ = json.JSONDecoder().raw_decode(output[start:])
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("GitNexus did not return structured impact evidence") from exc
        error = _impact_error(result, target)
        if error:
            raise ValueError(f"{target}: {error}; writer must perform a fresh check")
        reports.append({"target": target, "result": result})
    if indexed != _working_tree_snapshot(root, full_tree=True) or index != _index_snapshot(root):
        raise ValueError("sources or index changed during impact analysis")
    return {
        "schema_version": 1, "receipt_type": "gitnexus_impact",
        "project_cwd": str(root), "task_sha256": _sha256(task_file.read_bytes()),
        "scope_sha256": _json_hash(_scope(task)), "working_tree": indexed,
        "index": index, "reports": reports,
        "capture": "analyze_then_impact_with_unchanged_sources",
    }


def validate_impact_receipt(receipt: object, *, project_cwd: Path, task: dict, packet: dict) -> dict:
    root = project_cwd.resolve()
    if isinstance(receipt, str):
        relative, error = _safe_relative(root, receipt)
        if relative is None or error:
            return {"accepted": False, "errors": [error or "invalid receipt path"]}
        try:
            path = root / relative
            if not path.is_file():
                raise ValueError("receipt is not a regular file")
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"accepted": False, "errors": [f"cannot load impact receipt: {exc}"]}
    if not isinstance(receipt, dict):
        return {"accepted": False, "errors": ["receipt must be an object or project-relative path"]}
    errors = []
    try:
        declared = _impact_targets(root, task)
    except ValueError as exc:
        errors.append(str(exc))
        declared = []
    expected = {
        "schema_version": 1, "receipt_type": "gitnexus_impact",
        "project_cwd": str(root), "task_sha256": packet.get("task_sha256"),
        "scope_sha256": _json_hash(_scope(task)),
        "capture": "analyze_then_impact_with_unchanged_sources",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"{key} does not match")
    current = _working_tree_snapshot(root, full_tree=True)
    index = _index_snapshot(root)
    if not current["complete"] or receipt.get("working_tree") != current:
        errors.append("source tree changed or could not be read")
    if index.get("error") or receipt.get("index") != index or index.get("last_commit") != current["head"]:
        errors.append("GitNexus index changed or is stale")
    reports = receipt.get("reports")
    if not isinstance(reports, list) or not reports:
        errors.append("impact evidence is missing")
        reports = []
    for report in reports:
        if not isinstance(report, dict):
            errors.append("invalid impact evidence")
            continue
        error = _impact_error(report.get("result"), report.get("target", ""))
        if error:
            errors.append(error)
    reported = [report.get("target") for report in reports if isinstance(report, dict)]
    if sorted(str(target) for target in reported) != sorted(declared):
        errors.append("impact evidence does not exactly cover task impact_targets")
    return {"accepted": not errors, "errors": errors,
            "reports": reports if not errors else [],
            "reuse_rule": "Only covered targets; revalidate immediately before editing. Project policy wins."}


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Capture or validate reusable GitNexus impact evidence")
    parser.add_argument("action", choices=["capture", "validate"])
    parser.add_argument("--task-file", type=Path, required=True)
    parser.add_argument("--target", action="append", default=[], help="path::symbol; defaults to task impact_targets, must match when supplied")
    parser.add_argument("--output", type=Path, help="receipt path; defaults to task impact_receipt")
    args = parser.parse_args()
    try:
        import yaml
        task_file = args.task_file.resolve()
        task = yaml.safe_load(task_file.read_text(encoding="utf-8"))
        if not isinstance(task, dict) or not task.get("project_cwd"):
            raise ValueError("task must declare project_cwd")
        root = Path(task["project_cwd"]).resolve()
        output = args.output or Path(task.get("impact_receipt", ""))
        if not str(output) or str(output) == ".":
            raise ValueError("declare impact_receipt or --output")
        relative, error = _safe_relative(root, str(output))
        if relative is None or error or relative.parts[0] != ".agents":
            raise ValueError("receipt output must be under project .agents control plane")
        output = root / relative
        if args.action == "capture":
            receipt = capture_impact_receipt(root, task, task_file, args.target)
            output.parent.mkdir(parents=True, exist_ok=True)
            # Only the orchestrator writes this artifact; writer has read-only access.
            temp = output.with_name(output.name + ".tmp")
            temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
            temp.replace(output)
        packet = build_execution_packet(root, {**task, "impact_receipt": None}, task_file)
        decision = validate_impact_receipt(str(output), project_cwd=root, task=task, packet=packet)
        print(json.dumps(decision, ensure_ascii=False))
        return 0 if decision["accepted"] else 1
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"accepted": False, "errors": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli())

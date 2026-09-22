"""Pull judgeable text out of a tool response, and put it back.

Claude Code's ``updatedToolOutput`` must match the tool's own output shape or
it is silently ignored, so each supported tool gets an explicit extractor that
knows which field holds the text and how to rebuild the object around a
rewritten version of it. Unknown shapes return ``None`` and the hook passes the
result through untouched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Extracted:
    text: str
    line_offset: int
    describe: str
    rebuild: Callable[[str], Any]


def _short(value: object, limit: int = 200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def extract(tool_name: str, tool_input: Any, tool_response: Any) -> Extracted | None:
    tool_input = tool_input if isinstance(tool_input, dict) else {}

    if tool_name == "Bash" and isinstance(tool_response, dict):
        stdout = tool_response.get("stdout")
        if not isinstance(stdout, str):
            return None

        def rebuild_bash(new_text: str) -> dict:
            out = dict(tool_response)
            out["stdout"] = new_text
            return out

        return Extracted(stdout, 1, f"Bash: {_short(tool_input.get('command', ''))}", rebuild_bash)

    if tool_name == "Read" and isinstance(tool_response, dict):
        file = tool_response.get("file")
        if not isinstance(file, dict) or not isinstance(file.get("content"), str):
            return None
        try:
            start = int(file.get("startLine") or 1)
        except (TypeError, ValueError):
            start = 1

        def rebuild_read(new_text: str) -> dict:
            out = json.loads(json.dumps(tool_response))
            out["file"]["content"] = new_text
            out["file"]["numLines"] = new_text.count("\n") + 1
            return out

        return Extracted(file["content"], start, f"Read: {_short(file.get('filePath') or tool_input.get('file_path', ''))}", rebuild_read)

    if tool_name == "Grep" and isinstance(tool_response, dict):
        content = tool_response.get("content")
        if not isinstance(content, str) or not content:
            return None

        def rebuild_grep(new_text: str) -> dict:
            out = dict(tool_response)
            out["content"] = new_text
            out["numLines"] = new_text.count("\n") + 1
            return out

        describe = "Grep: pattern=%s path=%s" % (
            _short(tool_input.get("pattern", ""), 80),
            _short(tool_input.get("path", ""), 80),
        )
        return Extracted(content, 1, describe, rebuild_grep)

    if isinstance(tool_response, str):
        return Extracted(tool_response, 1, f"{tool_name}: {_short(tool_input)}", lambda new_text: new_text)

    return None


def trimmed_input(tool_name: str, tool_input: Any) -> dict[str, Any]:
    """A compact view of the tool call for the judge's state."""
    if not isinstance(tool_input, dict):
        return {"raw": _short(tool_input, 300)}
    if tool_name == "Bash":
        return {"command": _short(tool_input.get("command", ""), 500)}
    if tool_name == "Read":
        return {k: tool_input[k] for k in ("file_path", "offset", "limit") if k in tool_input}
    if tool_name == "Grep":
        return {k: tool_input[k] for k in ("pattern", "path", "glob", "type") if k in tool_input}
    return {k: _short(v, 200) for k, v in list(tool_input.items())[:8]}

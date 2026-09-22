"""MCP server exposing recall and stats to the agent."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from winnow import cache, log
from winnow.config import Config

server = MCPServer(
    name="winnow",
    instructions=(
        "winnow hides low-relevance blocks of large tool results behind stubs. "
        "Use winnow_recall with the key printed in a stub to restore the hidden text."
    ),
)


@server.tool()
def winnow_recall(key: str, start: int | None = None, end: int | None = None) -> str:
    """Return the full cached text behind a winnow stub.

    Args:
        key: the 12-character key printed in the stub.
        start: first line to return (inclusive), in the numbering the stub used.
        end: last line to return (inclusive).
    """
    cfg = Config.from_env()
    entry = cache.load(cfg, key)
    if entry is None:
        return f"winnow: no cached output for key {key!r}. It may have been created in another WINNOW_HOME, or the key is mistyped."
    log.log_event(cfg, {"event": "recall", "key": key, "start": start, "end": end})
    text = cache.slice_lines(str(entry.get("text", "")), start, end, int(entry.get("line_offset") or 1))
    header = f"winnow recall {key} ({entry.get('describe', '')})"
    return f"{header}\n{text}"


@server.tool()
def winnow_stats() -> dict[str, Any]:
    """Tokens saved, outputs rewritten, and the regret rate (pruned keys later recalled)."""
    return log.stats(Config.from_env())


def main() -> None:
    server.run("stdio")

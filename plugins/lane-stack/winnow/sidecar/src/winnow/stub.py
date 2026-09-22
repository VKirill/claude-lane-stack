"""Render the stub that replaces hidden blocks, and reassemble the output."""

from __future__ import annotations

import re
from collections import Counter

from winnow.chunk import Block
from winnow.policy import Verdict

_GREP_LINE = re.compile(r"^(.*?):(\d+)[:-]")


def digest(tool_name: str, text: str) -> str:
    """A deterministic one-line description of hidden text, for when there is no summarizer.

    Without it a stub only says how many lines are gone, and Claude cannot tell
    whether it lost dependency versions from a lockfile or the function it was
    looking for. This never calls a model.
    """
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return "blank lines"
    if tool_name == "Grep":
        files: Counter[str] = Counter()
        for line in lines:
            m = _GREP_LINE.match(line)
            if m:
                files[m.group(1)] += 1
        if files:
            top = ", ".join(f"{name} ({n})" for name, n in files.most_common(4))
            more = f", +{len(files) - 4} more files" if len(files) > 4 else ""
            return f"{sum(files.values())} matching lines in {len(files)} file{'s' if len(files) != 1 else ''}: {top}{more}"
    first = lines[0].strip()
    first = first if len(first) <= 70 else first[:69] + "…"
    kinds = []
    if sum(1 for l in lines if l.lstrip().startswith(("#", "//", "/*", "*", "--"))) > len(lines) / 2:
        kinds.append("mostly comments")
    if sum(1 for l in lines if l.lstrip().startswith(("import ", "from ", "using ", "require("))) > len(lines) / 2:
        kinds.append("mostly imports")
    if len({l.strip() for l in lines}) < len(lines) / 3:
        kinds.append("highly repetitive")
    kind = f" ({', '.join(kinds)})" if kinds else ""
    return f"{len(lines)} lines{kind}, starting: {first}"


def render_stub(
    group: list[Block],
    key: str,
    summary: str | None,
    max_probability: float,
    line_offset: int = 1,
    digest_text: str | None = None,
) -> str:
    first = group[0].start + line_offset - 1
    last = group[-1].end + line_offset - 1
    count = last - first + 1
    lines = [
        f"[winnow] Lines {first}-{last} ({count} lines) hidden: judged unlikely to matter "
        f"for the current task (relevance <= {max_probability:.2f})."
    ]
    if summary:
        lines.append(f"[winnow] Summary: {summary}")
    elif digest_text:
        lines.append(f"[winnow] Hidden content: {digest_text}")
    else:
        lines.append("[winnow] Summary unavailable.")
    lines.append(
        f"[winnow] Full text cached as key {key}. "
        f'Call winnow_recall(key="{key}", start={first}, end={last}) if you need it.'
    )
    return "\n".join(lines)


def assemble(blocks: list[Block], verdict: Verdict, stubs: dict[int, str]) -> str:
    """Rebuild the text: kept blocks verbatim, each hidden group replaced by its stub.

    ``stubs`` is keyed by the index of the first block in each hidden group.
    """
    hidden = {b.id for b in verdict.pruned}
    parts: list[str] = []
    for block in blocks:
        if block.id in hidden:
            if block.index in stubs:
                parts.append(stubs[block.index])
            continue
        parts.append(block.text)
    return "\n".join(parts)

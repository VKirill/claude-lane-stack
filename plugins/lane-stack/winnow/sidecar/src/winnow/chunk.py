"""Split tool output into tagged blocks the judge can vote on individually."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    id: str
    index: int
    start: int  # 1-based line number within the text
    end: int
    text: str

    @property
    def n_lines(self) -> int:
        return self.end - self.start + 1


def chunk(text: str, *, block_lines: int = 25, max_blocks: int = 200) -> list[Block]:
    """Group consecutive lines into blocks.

    Blocks close at ``block_lines`` lines, or earlier at a blank line once they
    are at least half full, so paragraphs and stanzas of output tend to stay
    whole. If the text would produce more than ``max_blocks`` blocks, the block
    size grows so the judge never sees more than ``max_blocks`` questions.
    Joining the block texts with newlines reproduces the input exactly.
    """
    if text == "":
        return []
    lines = text.split("\n")
    total = len(lines)
    size = max(1, block_lines)
    if math.ceil(total / size) > max_blocks:
        size = math.ceil(total / max_blocks)

    blocks: list[Block] = []
    current: list[str] = []
    start = 1

    def flush(end: int) -> None:
        nonlocal current, start
        index = len(blocks)
        blocks.append(Block(f"b{index + 1:03d}", index, start, end, "\n".join(current)))
        current = []
        start = end + 1

    for number, line in enumerate(lines, 1):
        current.append(line)
        at_blank = line.strip() == "" and len(current) >= max(1, size // 2)
        if len(current) >= size or at_blank:
            flush(number)
    if current:
        flush(total)
    return blocks


def group_contiguous(blocks: list[Block]) -> list[list[Block]]:
    """Group blocks whose indexes are consecutive, preserving order."""
    groups: list[list[Block]] = []
    for block in sorted(blocks, key=lambda b: b.index):
        if groups and groups[-1][-1].index == block.index - 1:
            groups[-1].append(block)
        else:
            groups.append([block])
    return groups

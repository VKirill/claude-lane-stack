"""Turn probabilities into a keep / hide decision. Deterministic and tunable."""

from __future__ import annotations

from dataclasses import dataclass, field

from winnow.chunk import Block
from winnow.config import Config


@dataclass
class Verdict:
    kept: list[Block]
    pruned: list[Block]
    reason: str
    uncertain: list[Block] = field(default_factory=list)

    @property
    def pruned_chars(self) -> int:
        return sum(len(b.text) for b in self.pruned)


def decide(
    blocks: list[Block],
    probabilities: dict[str, float],
    error_present: float | None,
    cfg: Config,
) -> Verdict:
    """Hide only what the judge is confident is not needed.

    - If the output looks like it contains an error, keep everything. Hiding
      the one line that explains a failure is the worst possible outcome.
    - A block with no probability (judge did not see it) is kept.
    - ``drop`` <= p < ``keep`` is uncertain; uncertain blocks are kept.
    - If hiding would save less than ``min_prune_ratio`` of the text, the
      rewrite is not worth the stub, so keep everything.
    """
    if error_present is not None and error_present >= cfg.keep:
        return Verdict(list(blocks), [], "error_present")

    kept: list[Block] = []
    pruned: list[Block] = []
    uncertain: list[Block] = []
    for block in blocks:
        p = probabilities.get(block.id)
        if p is None or p >= cfg.keep:
            kept.append(block)
        elif p >= cfg.drop:
            kept.append(block)
            uncertain.append(block)
        else:
            pruned.append(block)

    total = sum(len(b.text) for b in blocks) or 1
    if not pruned:
        return Verdict(kept, [], "nothing_to_prune", uncertain)
    if sum(len(b.text) for b in pruned) / total < cfg.min_prune_ratio:
        return Verdict(list(blocks), [], "below_min_prune_ratio", uncertain)
    return Verdict(kept, pruned, "pruned", uncertain)

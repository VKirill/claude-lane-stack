"""Hand labels: the ground truth the weak labels are checked against.

``winnow replay sample`` draws blocks from a judged file, stratified by the
judge's probability, and writes them out blind (no probability, no weak label)
as JSONL plus a Markdown sheet a person can read top to bottom. Labels go into
``labels.jsonl`` as one line per (case, block, labeler). ``winnow replay score
--labels`` then scores the judge against those labels instead of the weak ones,
and ``winnow replay agreement`` shows how the labelers and the weak label
relate to each other.
"""

from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from winnow.chunk import chunk
from winnow.config import Config
from winnow.replay import case_from_dict, read_jsonl, write_jsonl

BINS: dict[str, tuple[float, float]] = {"low": (0.0, 0.2), "mid": (0.2, 0.5), "high": (0.5, 1.01)}
LABELS = ("needed", "not_needed", "unsure")
ANSWER_ALIASES = {
    "y": "needed", "yes": "needed", "n": "needed", "needed": "needed", "1": "needed",
    "x": "not_needed", "no": "not_needed", "not": "not_needed", "not_needed": "not_needed", "0": "not_needed",
    "u": "unsure", "?": "unsure", "unsure": "unsure",
}
# "n" is ambiguous in English (no / needed); it is deliberately mapped to needed above and
# documented on the sheet. Use x for not needed.


def sample(
    cfg: Config,
    judged_path: Path,
    cases_path: Path,
    *,
    n_low: int = 50,
    n_mid: int = 25,
    n_high: int = 25,
    seed: int = 1,
) -> list[dict[str, Any]]:
    cases = {d["id"]: case_from_dict(d) for d in read_jsonl(cases_path)}
    pool: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {name: [] for name in BINS}
    for record in read_jsonl(judged_path):
        for block in record.get("blocks", []):
            p = block.get("p")
            if p is None or block.get("label") not in ("needed", "not_needed"):
                continue
            for name, (lo, hi) in BINS.items():
                if lo <= float(p) < hi:
                    pool[name].append((record, block))
                    break

    rng = random.Random(seed)
    items: list[dict[str, Any]] = []
    block_cache: dict[str, dict[str, Any]] = {}
    for name, n in (("low", n_low), ("mid", n_mid), ("high", n_high)):
        for record, block in rng.sample(pool[name], min(n, len(pool[name]))):
            case = cases.get(record["case_id"])
            if case is None:
                continue
            if case.id not in block_cache:
                block_cache[case.id] = {b.id: b for b in chunk(case.text, block_lines=cfg.block_lines, max_blocks=cfg.max_blocks)}
            blk = block_cache[case.id].get(block["id"])
            if blk is None:
                continue
            items.append(
                {
                    "case_id": case.id,
                    "block_id": blk.id,
                    "bin": name,
                    "p": block["p"],
                    "weak_label": block["label"],
                    "weak_reason": block.get("reason"),
                    "tool": record["tool"],
                    "tool_input": case.tool_input,
                    "task": record["task"],
                    "start": blk.start + case.line_offset - 1,
                    "end": blk.end + case.line_offset - 1,
                    "text": blk.text,
                }
            )
    rng.shuffle(items)  # so the sheet order says nothing about the bin
    for n, item in enumerate(items, 1):
        item["n"] = n
    return items


def write_sample(items: list[dict[str, Any]], jsonl_path: Path, md_path: Path) -> None:
    write_jsonl(jsonl_path, items)
    lines = [
        "# winnow labeling sheet",
        "",
        "For each item: would the assistant have needed to read this block to do the task correctly?",
        "Answer per item number in a text file, one per line: `<n> y` (needed), `<n> x` (not needed), `<n> u` (unsure).",
        "Then: `winnow replay import-labels --sample sample.jsonl --answers answers.txt --labeler <you>`.",
        "The judge's probability and the weak label are hidden on purpose.",
        "",
    ]
    for item in items:
        task = item.get("task") or {}
        tool_input = json.dumps(item.get("tool_input") or {}, ensure_ascii=False)
        lines += [
            f"## {item['n']}",
            "",
            f"**Tool:** {item['tool']} {tool_input}",
            f"**Lines:** {item['start']}-{item['end']}",
            f"**User asked:** {(task.get('user_request') or '(unknown)')[:600]}",
            f"**Assistant was about to:** {(task.get('assistant_intent') or '(unknown)')[:400]}",
            "",
            "```",
            item["text"],
            "```",
            "",
        ]
    md_path.write_text("\n".join(lines), encoding="utf-8")


def parse_answers(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*[:=\-]?\s*(\S+)", line)
        if not m:
            continue
        label = ANSWER_ALIASES.get(m.group(2).lower())
        if label:
            answers[int(m.group(1))] = label
    return answers


def append_labels(labels_path: Path, entries: Iterable[dict[str, Any]]) -> int:
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with labels_path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps({"ts": time.time(), **entry}, ensure_ascii=False) + "\n")
            n += 1
    return n


def import_answers(items: list[dict[str, Any]], answers: dict[int, str], labels_path: Path, labeler: str) -> int:
    by_n = {item["n"]: item for item in items}
    entries = [
        {"case_id": by_n[n]["case_id"], "block_id": by_n[n]["block_id"], "label": label, "labeler": labeler, "n": n}
        for n, label in sorted(answers.items())
        if n in by_n
    ]
    return append_labels(labels_path, entries)


def load_labels(labels_path: Path) -> dict[str, dict[tuple[str, str], str]]:
    """labeler -> {(case_id, block_id): label}; the last line for a key wins."""
    out: dict[str, dict[tuple[str, str], str]] = {}
    if not labels_path.exists():
        return out
    for entry in read_jsonl(labels_path):
        labeler = str(entry.get("labeler") or "?")
        key = (str(entry.get("case_id")), str(entry.get("block_id")))
        out.setdefault(labeler, {})[key] = str(entry.get("label"))
    return out


def label_interactive(
    items: list[dict[str, Any]],
    labels_path: Path,
    labeler: str,
    *,
    limit: int | None = None,
    seed: int | None = None,
    show_judge: bool = False,
    input_fn=input,
    print_fn=print,
) -> int:
    done = load_labels(labels_path).get(labeler, {})
    todo = [it for it in items if (it["case_id"], it["block_id"]) not in done]
    if seed is not None:
        random.Random(seed).shuffle(todo)
    if limit is not None:
        todo = todo[:limit]
    print_fn(f"{len(todo)} blocks to label as {labeler!r}. y = needed, x = not needed, u = unsure, s = skip, q = quit.")
    n_saved = 0
    for i, item in enumerate(todo, 1):
        task = item.get("task") or {}
        print_fn("")
        print_fn(f"[{i}/{len(todo)}]  #{item['n']}  {item['tool']} {json.dumps(item.get('tool_input') or {}, ensure_ascii=False)}  lines {item['start']}-{item['end']}")
        print_fn(f"User asked: {(task.get('user_request') or '(unknown)')[:400]}")
        print_fn(f"Assistant was about to: {(task.get('assistant_intent') or '(unknown)')[:300]}")
        if show_judge:
            print_fn(f"judge p={item['p']}  weak={item['weak_label']}/{item.get('weak_reason')}")
        print_fn("-" * 72)
        text_lines = item["text"].splitlines()
        print_fn("\n".join(text_lines[:60]) + ("\n... (%d more lines)" % (len(text_lines) - 60) if len(text_lines) > 60 else ""))
        print_fn("-" * 72)
        while True:
            answer = input_fn("needed? [y/x/u/s/q] ").strip().lower()
            if answer == "q":
                return n_saved
            if answer == "s":
                break
            label = ANSWER_ALIASES.get(answer)
            if label:
                append_labels(labels_path, [{"case_id": item["case_id"], "block_id": item["block_id"], "label": label, "labeler": labeler, "n": item["n"]}])
                n_saved += 1
                break
            print_fn("y, x, u, s, or q")
    return n_saved


def agreement(items: list[dict[str, Any]], labels: dict[str, dict[tuple[str, str], str]]) -> dict[str, Any]:
    """How the weak label and each labeler relate, plus each labeler's needed rate by judge bin."""
    key_of = lambda it: (it["case_id"], it["block_id"])  # noqa: E731
    result: dict[str, Any] = {"labelers": {}, "pairs": {}}
    for labeler, lab in labels.items():
        counted = [it for it in items if key_of(it) in lab and lab[key_of(it)] != "unsure"]
        confusion: Counter[str] = Counter()
        by_bin: dict[str, Counter[str]] = {name: Counter() for name in BINS}
        for it in counted:
            hand = lab[key_of(it)]
            confusion[f"weak={it['weak_label']} hand={hand}"] += 1
            by_bin[it["bin"]][hand] += 1
        result["labelers"][labeler] = {
            "n": len(counted),
            "unsure": sum(1 for it in items if lab.get(key_of(it)) == "unsure"),
            "weak_vs_hand": dict(confusion),
            "agreement_with_weak": round(sum(1 for it in counted if lab[key_of(it)] == it["weak_label"]) / len(counted), 3) if counted else None,
            "hand_needed_rate_by_bin": {
                name: {"n": sum(c.values()), "needed_rate": round(c["needed"] / sum(c.values()), 3) if sum(c.values()) else None}
                for name, c in by_bin.items()
            },
        }
    names = sorted(labels)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            both = [it for it in items if labels[a].get(key_of(it)) in ("needed", "not_needed") and labels[b].get(key_of(it)) in ("needed", "not_needed")]
            if both:
                agree = sum(1 for it in both if labels[a][key_of(it)] == labels[b][key_of(it)])
                result["pairs"][f"{a} vs {b}"] = {"n": len(both), "agreement": round(agree / len(both), 3)}
    return result


def hand_label_map(labels: dict[str, dict[tuple[str, str], str]], labeler: str | None) -> dict[tuple[str, str], str]:
    """Flatten to one label per block: the named labeler, or the last-written label across labelers."""
    if labeler:
        return {k: v for k, v in labels.get(labeler, {}).items() if v != "unsure"}
    merged: dict[tuple[str, str], str] = {}
    for lab in labels.values():
        for k, v in lab.items():
            if v != "unsure":
                merged[k] = v
    return merged

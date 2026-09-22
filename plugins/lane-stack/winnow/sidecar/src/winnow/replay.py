"""Replay: score a judge against your own Claude Code history, offline.

Your session transcripts already contain hundreds of large tool results, each
followed by what Claude actually did next. That "what happened next" is a free,
if weak, label for every block of every result:

- a block is **needed** if a later edit, write, command, or assistant message in
  the same turn reproduces one of its lines, or mentions a distinctive
  identifier that appears in few other blocks of that output;
- otherwise it is **not needed**;
- if nothing at all happened after the result before the next human turn, the
  whole case is **unknown** and is excluded from scoring.

The label is biased toward "not needed": Claude can read something, use it to
understand the code, and never quote it. Treat the resulting regret as an
upper bound on real regret, and the savings as an estimate.

Three stages, each a subcommand, so the expensive one can be re-run with a
different judge:

    winnow replay extract   transcripts -> cases.jsonl        (offline)
    winnow replay judge     cases.jsonl -> judged-<judge>.jsonl (calls the judge)
    winnow replay score     judged file -> report + score json (offline)

``winnow replay run`` does all three. The built-in ``lexical`` judge needs no
key and is the baseline any real judge has to beat.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from winnow.chunk import Block, chunk
from winnow.config import Config
from winnow.extract import extract, trimmed_input
from winnow.hooks import _block_questions, _judge_window
from winnow.judge import Judge, JudgeResult
from winnow.log import JEV_USD_PER_MILLION_INPUT
from winnow.transcript import _text_of

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{5,}")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,}")
STOP = {
    "this", "that", "with", "from", "have", "what", "when", "where", "which", "there", "their", "about",
    "would", "could", "should", "into", "then", "than", "them", "they", "your", "will", "just", "also",
    "like", "make", "need", "want", "please", "help", "does", "done", "here", "some", "only", "more",
    "file", "files", "code", "line", "lines", "function", "class", "test", "tests", "error", "errors",
    "read", "check", "look", "find", "update", "change", "changes", "the", "and", "for", "are", "not",
}


# --------------------------------------------------------------------------- #
# Cases                                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class Case:
    id: str
    transcript: str
    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    task: dict[str, str]
    line_offset: int
    text: str
    evidence: list[str] = field(default_factory=list)  # everything Claude produced next (line overlap)
    references: list[str] = field(default_factory=list)  # prose, commands, edit targets only (identifier mentions)
    evidence_events: int = 0
    actions: list[str] = field(default_factory=list)  # one line per later assistant event, for humans


DEFAULT_WINDOW = 12  # assistant events after the result that count as "used it"


def _block_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _tool_input_evidence(name: str, inp: dict[str, Any]) -> tuple[str, str]:
    """(line-overlap evidence, identifier-reference evidence) for one tool call.

    A ``Write`` or an edit's ``new_string`` reproduces content wholesale, so it
    counts for line overlap but not for identifier mentions; otherwise rewriting
    a file marks every block of it as needed through incidental names.
    """
    if name in ("Edit", "MultiEdit"):
        olds = [str(inp.get("old_string", ""))]
        news = [str(inp.get("new_string", ""))]
        for edit in inp.get("edits", []) if isinstance(inp.get("edits"), list) else []:
            if isinstance(edit, dict):
                olds.append(str(edit.get("old_string", "")))
                news.append(str(edit.get("new_string", "")))
        return "\n".join(olds + news), "\n".join(olds)
    if name == "Write":
        return str(inp.get("content", "")), ""
    if name == "Bash":
        command = str(inp.get("command", ""))
        return command, command
    if name == "Read":
        return "", str(inp.get("file_path", ""))
    if name == "Grep":
        ref = " ".join(str(inp.get(k, "")) for k in ("pattern", "path", "glob"))
        return "", ref
    dumped = json.dumps(inp, ensure_ascii=False)[:2000]
    return dumped, dumped


def _describe_action(name: str, inp: dict[str, Any]) -> str:
    def short(value: Any, n: int = 90) -> str:
        text = str(value).replace("\n", " ").strip()
        return text if len(text) <= n else text[: n - 1] + "…"

    if name in ("Edit", "MultiEdit"):
        return f"Edit {short(inp.get('file_path', ''), 60)}  replacing: {short(inp.get('old_string', ''), 80)}"
    if name == "Write":
        return f"Write {short(inp.get('file_path', ''), 60)} ({len(str(inp.get('content', '')))} chars)"
    if name == "Bash":
        return f"Bash: {short(inp.get('command', ''))}"
    if name == "Read":
        extra = "".join(f" {k}={inp[k]}" for k in ("offset", "limit") if k in inp)
        return f"Read {short(inp.get('file_path', ''), 70)}{extra}"
    if name == "Grep":
        return f"Grep {short(inp.get('pattern', ''), 40)} in {short(inp.get('path', '.'), 40)}"
    return f"{name} {short(json.dumps(inp, ensure_ascii=False), 70)}"


def _append_evidence(cases: list[Case], line_text: str, ref_text: str, window: int, action: str = "") -> None:
    for case in cases:
        if case.evidence_events >= window:
            continue
        case.evidence_events += 1
        if line_text:
            case.evidence.append(line_text)
        if ref_text:
            case.references.append(ref_text)
        if action:
            case.actions.append(action)


def iter_cases(
    path: str | Path,
    *,
    tools: Iterable[str],
    min_chars: int,
    window: int = DEFAULT_WINDOW,
    include_sidechain: bool = False,
) -> Iterator[Case]:
    """Walk one transcript and yield every large tool result with its task and evidence.

    ``window`` bounds how many later assistant events (messages and tool calls)
    count as evidence, so a result is judged by what Claude did soon after
    reading it, not by everything in a long autonomous turn.

    Subagent transcripts (``<session>/subagents/agent-*.jsonl``) mark every
    entry as a sidechain; pass ``include_sidechain=True`` to walk one of those.
    """
    tools = set(tools)
    path = Path(path)
    user_request, intent = "", ""
    pending: dict[str, tuple[str, dict[str, Any], dict[str, str]]] = {}
    open_cases: list[Case] = []
    count = 0
    stem = path.stem[:8]

    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or (entry.get("isSidechain") and not include_sidechain):
                continue
            kind = entry.get("type")
            message = entry.get("message") or {}
            content = message.get("content") if isinstance(message, dict) else None

            if kind == "user":
                if entry.get("isMeta"):
                    continue
                results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] if isinstance(content, list) else []
                if results:
                    for block in results:
                        tid = str(block.get("tool_use_id"))
                        if tid not in pending:
                            continue
                        name, inp, task = pending.pop(tid)
                        response: Any = entry.get("toolUseResult") if len(results) == 1 and entry.get("toolUseResult") is not None else _block_text(block)
                        extracted = extract(name, inp, response)
                        if extracted is None or len(extracted.text) < min_chars:
                            continue
                        count += 1
                        open_cases.append(
                            Case(
                                id=f"{stem}-{count:04d}",
                                transcript=str(path),
                                tool_use_id=tid,
                                tool_name=name,
                                tool_input=trimmed_input(name, inp),
                                task=dict(task),
                                line_offset=extracted.line_offset,
                                text=extracted.text,
                            )
                        )
                    continue
                text = _text_of(content).strip()
                if text:
                    yield from open_cases
                    open_cases = []
                    pending.clear()
                    user_request, intent = text, ""

            elif kind == "assistant":
                text = _text_of(content).strip()
                if text:
                    intent = text
                    said = text.replace("\n", " ")
                    _append_evidence(open_cases, text, text, window, action=f"said: {said[:120]}{'…' if len(said) > 120 else ''}")
                if isinstance(content, list):
                    for block in content:
                        if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                            continue
                        name = str(block.get("name") or "")
                        inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                        line_text, ref_text = _tool_input_evidence(name, inp)
                        _append_evidence(open_cases, line_text, ref_text, window, action=_describe_action(name, inp))
                        if name in tools:
                            pending[str(block.get("id"))] = (
                                name,
                                inp,
                                {"user_request": user_request, "assistant_intent": intent},
                            )
    yield from open_cases


def transcripts_root() -> Path:
    import os

    return Path(os.environ.get("WINNOW_TRANSCRIPTS_ROOT") or (Path.home() / ".claude" / "projects"))


def find_transcript(session_id: str) -> Path | None:
    """Locate a session's transcript by id under the Claude Code projects directory."""
    if not session_id:
        return None
    root = transcripts_root()
    if not root.is_dir():
        return None
    matches = list(root.glob(f"*/{session_id}.jsonl"))
    return matches[0] if matches else None


def session_title(path: Path) -> str:
    """The session's title, if Claude Code recorded one (custom titles win over AI titles)."""
    custom = ai = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "title" not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                kind = entry.get("type")
                value = entry.get("customTitle") or entry.get("aiTitle") or entry.get("title")
                if kind == "custom-title" and value:
                    custom = str(value)
                elif kind == "ai-title" and value:
                    ai = str(value)
    except OSError:
        return ""
    return custom or ai


def subagent_transcripts(session_id: str) -> list[Path]:
    """Transcripts of the subagents a session spawned: ``<project>/<session>/subagents/agent-*.jsonl``."""
    if not session_id:
        return []
    root = transcripts_root()
    if not root.is_dir():
        return []
    return sorted(root.glob(f"*/{session_id}/subagents/agent-*.jsonl"))


def subagent_meta(path: Path) -> dict[str, Any]:
    """The ``.meta.json`` next to a subagent transcript: agentType, description, parent tool use."""
    meta = path.with_suffix("").with_suffix(".meta.json") if path.name.endswith(".jsonl") else None
    if meta is None or not meta.exists():
        return {}
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def default_transcripts() -> list[Path]:
    root = transcripts_root()
    if not root.is_dir():
        return []
    files = [p for p in root.glob("*/*.jsonl") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


# --------------------------------------------------------------------------- #
# Weak labels                                                                  #
# --------------------------------------------------------------------------- #


def _norm(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().lower()


def _significant(norm: str) -> bool:
    return len(norm) >= 12 and sum(ch.isalnum() for ch in norm) >= 6


def _idents(text: str) -> set[str]:
    return {m.group(0) for m in IDENT.finditer(text)}


def _distinctive(token: str) -> bool:
    if "_" in token or any(ch.isdigit() for ch in token):
        return True
    if token[1:] != token[1:].lower() and token != token.upper():
        return True  # camelCase or PascalCase with an inner capital
    return len(token) >= 10


def label_blocks_with_reasons(case: Case, blocks: list[Block]) -> dict[str, tuple[str, str]]:
    """Per block: (label, reason). Reasons: line, ident, none, unknown."""
    if case.evidence_events == 0 or not any(e.strip() for e in case.evidence + case.references):
        return {b.id: ("unknown", "unknown") for b in blocks}
    evidence = "\n".join(case.evidence)
    evidence_lines = {n for n in (_norm(l) for l in evidence.splitlines()) if _significant(n)}
    reference_idents = _idents("\n".join(case.references))

    ident_block_counts: Counter[str] = Counter()
    per_block_idents: dict[str, set[str]] = {}
    for block in blocks:
        idents = {t for t in _idents(block.text) if _distinctive(t)}
        per_block_idents[block.id] = idents
        ident_block_counts.update(idents)

    labels: dict[str, tuple[str, str]] = {}
    for block in blocks:
        lines = {n for n in (_norm(l) for l in block.text.splitlines()) if _significant(n)}
        if lines & evidence_lines:
            labels[block.id] = ("needed", "line")
            continue
        rare = {t for t in per_block_idents[block.id] if ident_block_counts[t] <= 2}
        if rare & reference_idents:
            labels[block.id] = ("needed", "ident")
        else:
            labels[block.id] = ("not_needed", "none")
    return labels


def label_blocks(case: Case, blocks: list[Block]) -> dict[str, str]:
    return {bid: label for bid, (label, _) in label_blocks_with_reasons(case, blocks).items()}


# --------------------------------------------------------------------------- #
# Judges                                                                       #
# --------------------------------------------------------------------------- #


class LexicalJudge:
    """Keyless baseline: P(needed) grows with the share of task words the block contains."""

    name = "lexical"

    def nouls(self, state: Any, questions: Mapping[str, Any]) -> JudgeResult:
        task = state.get("task", {}) if isinstance(state, dict) else {}
        text = f"{task.get('user_request', '')} {task.get('assistant_intent', '')}"
        terms = {w.lower() for w in WORD.findall(text)} - STOP
        blocks = state.get("blocks", {}) if isinstance(state, dict) else {}
        probabilities: dict[str, float] = {}
        for qid in questions:
            if qid == "error_present":
                probabilities[qid] = 0.0
                continue
            if not terms:
                probabilities[qid] = 0.5
                continue
            words = {w.lower() for w in WORD.findall(str(blocks.get(qid, "")))}
            overlap = len(terms & words) / len(terms)
            probabilities[qid] = min(0.95, 0.05 + 2.0 * overlap)
        return JudgeResult(probabilities, self.name, None, None, 0)


def build_replay_judge(name: str, cfg: Config) -> Judge:
    if name == "lexical":
        return LexicalJudge()
    from winnow.judge import AdapterJudge, TypeSafeJudge

    if name == "typesafe":
        return TypeSafeJudge(cfg.model, cfg.judge_timeout)
    if name == "adapter":
        return AdapterJudge(cfg.adapter_provider, cfg.adapter_model)
    raise ValueError(f"unknown judge {name!r}; expected lexical, typesafe, or adapter")


def judge_case(case: Case, blocks: list[Block], judge: Judge, cfg: Config, questions: str | None = None) -> JudgeResult:
    judged = _judge_window(blocks, cfg.max_state_chars)
    state = {
        "task": case.task,
        "tool": {"name": case.tool_name, "input": case.tool_input},
        "blocks": {b.id: b.text for b in judged},
    }
    return judge.nouls(state, _block_questions(judged, questions or cfg.questions))


def judge_cases(
    cases: Iterable[Case], judge: Judge, cfg: Config, *, limit: int | None = None, questions: str | None = None
) -> Iterator[dict[str, Any]]:
    for index, case in enumerate(cases):
        if limit is not None and index >= limit:
            break
        blocks = chunk(case.text, block_lines=cfg.block_lines, max_blocks=cfg.max_blocks)
        labeled = label_blocks_with_reasons(case, blocks)
        record: dict[str, Any] = {
            "case_id": case.id,
            "transcript": case.transcript,
            "tool": case.tool_name,
            "task": case.task,
            "judge": judge.name,
            "questions": questions or cfg.questions,
        }
        try:
            result = judge_case(case, blocks, judge, cfg, questions)
        except Exception as exc:  # noqa: BLE001 - keep going, record the failure
            record["error"] = repr(exc)
            yield record
            continue
        record.update(
            model=result.model,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            error_present=result.probabilities.get("error_present"),
            evidence_events=case.evidence_events,
            blocks=[
                {
                    "id": b.id,
                    "start": b.start,
                    "end": b.end,
                    "chars": len(b.text),
                    "label": labeled[b.id][0],
                    "reason": labeled[b.id][1],
                    "p": result.probabilities.get(b.id),
                }
                for b in blocks
            ],
        )
        yield record


# --------------------------------------------------------------------------- #
# Scoring                                                                      #
# --------------------------------------------------------------------------- #


def score(records: Iterable[dict[str, Any]], hand_labels: Mapping[tuple[str, str], str] | None = None) -> dict[str, Any]:
    """Score judged records against the weak labels, or against ``hand_labels`` when given.

    ``hand_labels`` maps (case_id, block_id) to needed / not_needed; only those
    blocks are scored, using the hand label in place of the weak one.
    """
    rows: list[tuple[float, str, int]] = []
    cases = errors = unknown_blocks = 0
    tokens = 0
    judges: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    question_sets: Counter[str] = Counter()
    latencies: list[int] = []
    for record in records:
        cases += 1
        judges[str(record.get("judge", "?"))] += 1
        tools[str(record.get("tool", "?"))] += 1
        question_sets[str(record.get("questions", "default"))] += 1
        if "error" in record:
            errors += 1
            continue
        tokens += int(record.get("input_tokens") or 0)
        if record.get("latency_ms") is not None:
            latencies.append(int(record["latency_ms"]))
        for block in record.get("blocks", []):
            p = block.get("p")
            reasons[str(block.get("reason", "?"))] += 1
            if hand_labels is not None:
                label = hand_labels.get((str(record.get("case_id")), str(block.get("id"))))
            else:
                label = block.get("label")
            if p is None or label not in ("needed", "not_needed"):
                unknown_blocks += 1
                continue
            rows.append((float(p), str(label), int(block.get("chars") or 0)))

    total_chars = sum(c for _, _, c in rows) or 1
    needed = [(p, l, c) for p, l, c in rows if l == "needed"]
    thresholds = []
    for i in range(1, 10):
        t = round(i / 10, 1)
        hidden = [(p, l, c) for p, l, c in rows if p < t]
        hidden_needed = [r for r in hidden if r[1] == "needed"]
        thresholds.append(
            {
                "threshold": t,
                "hidden_blocks": len(hidden),
                "hidden_fraction_chars": round(sum(c for _, _, c in hidden) / total_chars, 4),
                "regret": round(len(hidden_needed) / len(needed), 4) if needed else None,
                "hidden_precision": round(1 - len(hidden_needed) / len(hidden), 4) if hidden else None,
            }
        )

    bins = []
    ece = 0.0
    for i in range(10):
        lo, hi = i / 10, (i + 1) / 10
        sel = [(p, l, c) for p, l, c in rows if lo <= p < hi or (i == 9 and p == 1.0)]
        if not sel:
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": 0, "mean_p": None, "needed_rate": None})
            continue
        mean_p = sum(p for p, _, _ in sel) / len(sel)
        rate = sum(1 for _, l, _ in sel if l == "needed") / len(sel)
        ece += len(sel) / len(rows) * abs(rate - mean_p)
        bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(sel), "mean_p": round(mean_p, 3), "needed_rate": round(rate, 3)})

    return {
        "cases": cases,
        "cases_with_errors": errors,
        "judges": dict(judges),
        "auc": _auc(rows),
        "question_sets": dict(question_sets),
        "label_source": "hand" if hand_labels is not None else "weak",
        "tools": dict(tools),
        "label_reasons": dict(reasons),
        "blocks_scored": len(rows),
        "blocks_unknown": unknown_blocks,
        "needed_fraction": round(len(needed) / len(rows), 4) if rows else None,
        "judge_input_tokens": tokens,
        "est_cost_usd_at_jev_price": round(tokens / 1_000_000 * JEV_USD_PER_MILLION_INPUT, 6),
        "latency_ms_median": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "thresholds": thresholds,
        "calibration": bins,
        "ece": round(ece, 4) if rows else None,
    }


def _auc(rows: list[tuple[float, str, int]]) -> float | None:
    """ROC AUC of p for "needed": the chance a needed block scores above a not-needed one.

    Calibration alone rewards a judge that predicts the base rate for every block
    (ECE near zero, nothing to hide); this is the number that says whether the
    ordering means anything. Ties count half.
    """
    pos = sorted(p for p, l, _ in rows if l == "needed")
    neg = sorted(p for p, l, _ in rows if l == "not_needed")
    if not pos or not neg:
        return None
    from bisect import bisect_left, bisect_right

    wins = 0.0
    for p in pos:
        below = bisect_left(neg, p)
        ties = bisect_right(neg, p) - below
        wins += below + 0.5 * ties
    return round(wins / (len(pos) * len(neg)), 4)


def _pct(value: float | None, width: int = 6) -> str:
    return "n/a".rjust(width) if value is None else f"{value:.1%}".rjust(width)


def format_report(scored: dict[str, Any]) -> str:
    out = []
    out.append(
        "cases %d  (errors %d)   judges %s   questions %s   labels: %s"
        % (scored["cases"], scored["cases_with_errors"], scored["judges"], scored.get("question_sets"), scored.get("label_source", "weak"))
    )
    out.append("tools %s   label reasons %s" % (scored.get("tools"), scored.get("label_reasons")))
    out.append(
        "blocks scored %d  unknown %d  needed fraction %s   ECE %s   AUC %s"
        % (scored["blocks_scored"], scored["blocks_unknown"], scored["needed_fraction"], scored["ece"], scored.get("auc"))
    )
    if scored["judge_input_tokens"]:
        out.append(
            "judge input tokens %d  (~$%s at Jev's price)   median latency %s ms"
            % (scored["judge_input_tokens"], scored["est_cost_usd_at_jev_price"], scored["latency_ms_median"])
        )
    out.append("")
    out.append("threshold  hidden_blocks  hidden_chars  regret  hidden_precision")
    for row in scored["thresholds"]:
        out.append(
            "   %.1f     %8d        %s   %s   %s"
            % (
                row["threshold"],
                row["hidden_blocks"],
                _pct(row["hidden_fraction_chars"]),
                _pct(row["regret"]),
                _pct(row["hidden_precision"]),
            )
        )
    out.append("")
    out.append("calibration   n     mean_p   needed_rate")
    for b in scored["calibration"]:
        if b["n"]:
            out.append("  %s   %5d   %.3f    %.3f" % (b["bin"], b["n"], b["mean_p"], b["needed_rate"]))
    out.append("")
    out.append("regret = share of needed blocks a threshold would hide; hidden_precision = share of hidden blocks that were not needed.")
    out.append("ECE = calibration (0 is perfect); AUC = ordering (0.5 is a coin flip). A judge needs both: the base rate alone scores a low ECE.")
    if scored.get("label_source", "weak") == "weak":
        out.append("Labels are weak (see docs/DESIGN.md): treat regret as an upper bound.")
    else:
        out.append("Scored against hand labels on the sampled blocks only.")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Files                                                                        #
# --------------------------------------------------------------------------- #


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def case_to_dict(case: Case) -> dict[str, Any]:
    return asdict(case)


def case_from_dict(d: dict[str, Any]) -> Case:
    return Case(**{k: d[k] for k in Case.__dataclass_fields__ if k in d})


def extract_cases(paths: Iterable[Path], cfg: Config, *, limit: int | None = None, window: int = DEFAULT_WINDOW) -> Iterator[Case]:
    n = 0
    for path in paths:
        for case in iter_cases(path, tools=cfg.tools, min_chars=cfg.min_chars, window=window):
            yield case
            n += 1
            if limit is not None and n >= limit:
                return


def run_replay(
    cfg: Config,
    *,
    paths: list[Path] | None,
    judge_name: str,
    limit: int | None,
    judge: Judge | None = None,
    window: int = DEFAULT_WINDOW,
) -> tuple[dict[str, Any], Path]:
    """extract -> judge -> score in one go. Returns (score, score_path)."""
    transcripts = paths or default_transcripts()
    cases_path = cfg.replay_dir / "cases.jsonl"
    judged_path = cfg.replay_dir / f"judged-{judge_name}.jsonl"
    score_path = cfg.replay_dir / f"score-{judge_name}.json"

    cases = list(extract_cases(transcripts, cfg, limit=limit, window=window))
    write_jsonl(cases_path, (case_to_dict(c) for c in cases))
    judge = judge or build_replay_judge(judge_name, cfg)
    started = time.perf_counter()
    write_jsonl(judged_path, judge_cases(cases, judge, cfg))
    scored = score(read_jsonl(judged_path))
    scored["wall_seconds"] = round(time.perf_counter() - started, 1)
    scored["transcripts"] = len(transcripts)
    scored["window"] = window
    scored["paths"] = {"cases": str(cases_path), "judged": str(judged_path)}
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")
    return scored, score_path

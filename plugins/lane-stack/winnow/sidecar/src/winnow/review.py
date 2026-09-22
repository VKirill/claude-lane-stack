"""``winnow review``: judge recent stubs while the session is still in your head.

Replay labels old transcripts from a 600-character task excerpt, which is hard
for a person who no longer remembers the session. This is the other way round:
walk the stubs winnow produced recently, newest first, and show the whole
picture a person needs to judge them: what was asked, what Claude said it was
doing, what it kept and what it lost, and, because a human judging ground truth
is allowed hindsight, what Claude actually did next. The answers are human
regret, recorded in ``~/.winnow/review.jsonl`` and reported by ``winnow stats``.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from winnow import cache, log
from winnow.chunk import Block
from winnow.config import Config

VERDICTS = {"y": "fine", "x": "should_have_kept", "u": "unsure"}


def reviewed_keys(cfg: Config) -> set[str]:
    path = cfg.home / "review.jsonl"
    keys: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and entry.get("key"):
                keys.add(str(entry["key"]))
    return keys


def candidates(cfg: Config, *, limit: int, since_days: float, session: str | None = None) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Recent rewritten decisions with their cache entries, newest first, not yet reviewed."""
    cutoff = time.time() - since_days * 86400
    seen = reviewed_keys(cfg)
    events = [
        e
        for e in log.read_events(cfg)
        if e.get("event") == "post_tool_use"
        and e.get("rewritten")
        and not e.get("demo")
        and e.get("key")
        and float(e.get("ts") or 0) >= cutoff
        and str(e["key"]) not in seen
        and (session is None or e.get("session_id") == session)
    ]
    events.sort(key=lambda e: float(e.get("ts") or 0), reverse=True)
    out: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for event in events:
        entry = cache.load(cfg, str(event["key"]))
        if entry is not None:
            out.append((event, entry))
        if len(out) >= limit:
            break
    return out


def _regions(entry: dict[str, Any], hidden: bool) -> list[dict[str, Any]]:
    """Consecutive blocks of one kind, with their text and original line numbers."""
    lines = str(entry.get("text", "")).split("\n")
    offset = int(entry.get("line_offset") or 1)
    groups: list[dict[str, Any]] = []
    for block in entry.get("blocks", []):
        if bool(block.get("hidden")) != hidden:
            continue
        start, end = int(block["start"]), int(block["end"])
        if groups and groups[-1]["end_idx"] == start - 1:
            groups[-1]["end_idx"] = end
        else:
            groups.append({"start_idx": start, "end_idx": end})
    for g in groups:
        g["text"] = "\n".join(lines[g["start_idx"] - 1 : g["end_idx"]])
        g["start"] = g["start_idx"] + offset - 1
        g["end"] = g["end_idx"] + offset - 1
    return groups


def hidden_groups(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return _regions(entry, hidden=True)


def kept_groups(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return _regions(entry, hidden=False)


class SessionContext:
    """What the transcripts know about a stub: the task, the session title, which subagent ran it,
    and what Claude did next.

    A session's main transcript is parsed once and cached. Subagent transcripts
    (one file per spawned agent, every entry a sidechain) are parsed on demand:
    directly when the stub recorded its agent id, otherwise all of them.
    """

    def __init__(self, cfg: Config, window: int = 8) -> None:
        self.cfg = cfg
        self.window = window
        self._cases: dict[str, Any] = {}
        self._agent_of: dict[str, dict[str, Any]] = {}  # tool_use_id -> subagent meta
        self._titles: dict[str, str] = {}
        self._loaded_main: set[str] = set()
        self._loaded_files: set[str] = set()
        self._scanned_all: set[str] = set()

    def _walk(self, path: Any, *, sidechain: bool, meta: dict[str, Any] | None = None) -> None:
        from winnow import replay

        if str(path) in self._loaded_files:
            return
        self._loaded_files.add(str(path))
        try:
            for case in replay.iter_cases(path, tools=self.cfg.tools, min_chars=1, window=self.window, include_sidechain=sidechain):
                self._cases[case.tool_use_id] = case
                if meta:
                    self._agent_of[case.tool_use_id] = meta
        except OSError:
            return

    def _load_main(self, session_id: str) -> None:
        from winnow import replay

        if session_id in self._loaded_main:
            return
        self._loaded_main.add(session_id)
        path = replay.find_transcript(session_id)
        if path is None:
            return
        self._titles[session_id] = replay.session_title(path)
        self._walk(path, sidechain=False)

    def _load_subagent(self, session_id: str, agent_id: str | None) -> None:
        from winnow import replay

        files = replay.subagent_transcripts(session_id)
        if agent_id:
            files = [f for f in files if f.name == f"agent-{agent_id}.jsonl"] or files
        elif session_id in self._scanned_all:
            return
        else:
            self._scanned_all.add(session_id)
        for f in files:
            self._walk(f, sidechain=True, meta={"file": f.name, **replay.subagent_meta(f)})

    def title(self, session_id: str) -> str:
        self._load_main(session_id)
        return self._titles.get(session_id, "")

    def case(self, session_id: str, tool_use_id: str, agent_id: str | None = None) -> Any:
        self._load_main(session_id)
        if tool_use_id not in self._cases:
            self._load_subagent(session_id, agent_id)
        return self._cases.get(tool_use_id)

    def agent(self, tool_use_id: str) -> dict[str, Any]:
        return self._agent_of.get(tool_use_id, {})


def automatic_check(case: Any, entry: dict[str, Any]) -> str:
    """Did anything Claude did next reuse a line or a distinctive name from the hidden text?"""
    from winnow.replay import label_blocks_with_reasons

    if case is None or case.evidence_events == 0:
        return "no later actions found in the transcript to check against"
    blocks = [
        Block(id=str(b["id"]), index=i, start=int(b["start"]), end=int(b["end"]), text="\n".join(str(entry.get("text", "")).split("\n")[int(b["start"]) - 1 : int(b["end"])]))
        for i, b in enumerate(entry.get("blocks", []))
    ]
    hidden_ids = {str(b["id"]) for b in entry.get("blocks", []) if b.get("hidden")}
    labeled = label_blocks_with_reasons(case, blocks)
    offset = int(entry.get("line_offset") or 1)
    hits = []
    for b in blocks:
        if b.id in hidden_ids and labeled.get(b.id, ("", ""))[0] == "needed":
            reason = labeled[b.id][1]
            what = "reused a line from" if reason == "line" else "mentioned a distinctive name from"
            hits.append(f"{what} hidden lines {b.start + offset - 1}-{b.end + offset - 1}")
    if hits:
        return "a later action " + "; ".join(hits)
    return f"none of Claude's next {min(case.evidence_events, 8)} actions reused a line or a distinctive name from the hidden text"


def record(cfg: Config, *, key: str, verdict: str, reviewer: str, event: dict[str, Any]) -> None:
    cfg.home.mkdir(parents=True, exist_ok=True)
    with (cfg.home / "review.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "ts": time.time(),
                    "key": key,
                    "verdict": verdict,
                    "reviewer": reviewer,
                    "session_id": event.get("session_id"),
                    "tool": event.get("tool"),
                    "decision_ts": event.get("ts"),
                    "questions": event.get("questions"),
                    "n_hidden": event.get("n_hidden"),
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def _clip(text: str, max_lines: int) -> str:
    text_lines = text.splitlines()
    if len(text_lines) <= max_lines:
        return "\n".join(text_lines)
    return "\n".join(text_lines[:max_lines]) + f"\n... ({len(text_lines) - max_lines} more lines)"


def run_review(
    cfg: Config,
    *,
    limit: int = 10,
    reviewer: str = "human",
    since_days: float = 7,
    session: str | None = None,
    max_lines: int = 40,
    show_judge: bool = False,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> int:
    items = candidates(cfg, limit=limit, since_days=since_days, session=session)
    if not items:
        print_fn(f"No unreviewed stubs from the last {since_days:g} days. Nothing was hidden, or you've reviewed it all.")
        return 0
    context = SessionContext(cfg)
    print_fn(f"{len(items)} stubs to review. y = hiding it was fine, x = it should have been kept, u = unsure, s = skip, q = quit.")
    print_fn("The question each time: given what was asked and what Claude did next, did hiding these lines cost anything?")
    saved = 0
    for i, (event, entry) in enumerate(items, 1):
        session_id = str(event.get("session_id") or "")
        tool_use_id = str(event.get("tool_use_id") or "")
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(event.get("ts") or 0)))
        title = context.title(session_id)
        case = context.case(session_id, tool_use_id, event.get("agent_id") or entry.get("agent_id"))
        agent = context.agent(tool_use_id)
        recorded = entry.get("task") or {}
        # A stub from a subagent recorded the orchestrator's task before 0.3.4; the subagent's own
        # transcript (its delegation prompt) is the task that call was actually serving.
        if case is not None and (agent or not any(recorded.values())):
            task = case.task
        else:
            task = recorded

        print_fn("")
        print_fn("=" * 72)
        print_fn(f"[{i}/{len(items)}]  {entry.get('describe') or event.get('tool')}")
        print_fn(f"when: {when}   session: {title or '(untitled)'} [{session_id[:8]}]   questions: {event.get('questions', '?')}")
        agent_type = agent.get("agentType") or event.get("agent_type") or entry.get("agent_type")
        if agent_type:
            desc = agent.get("description")
            print_fn(f"run by subagent: {agent_type}" + (f" ({desc})" if desc else ""))
        one_line = lambda s, n: " ".join(str(s).split())[:n]  # noqa: E731
        if task.get("user_request"):
            print_fn(f"user asked:      {one_line(task['user_request'], 600)}")
        if task.get("assistant_intent"):
            print_fn(f"claude intended: {one_line(task['assistant_intent'], 400)}")
        if not task:
            print_fn("task: (not recorded, and the session transcript was not found)")

        kept = kept_groups(entry)
        hidden = hidden_groups(entry)
        print_fn("-" * 72)
        print_fn(f"Claude SAW {len(kept)} region(s), {sum(g['end'] - g['start'] + 1 for g in kept)} lines:")
        for g in kept:
            first = next((l for l in g["text"].splitlines() if l.strip()), "")
            print_fn(f"  lines {g['start']}-{g['end']}: {first[:100]}")
        print_fn("-" * 72)
        print_fn(f"Claude LOST {len(hidden)} region(s), {sum(g['end'] - g['start'] + 1 for g in hidden)} lines:")
        for g in hidden:
            print_fn(f"  --- hidden lines {g['start']}-{g['end']} ---")
            print_fn(_clip(g["text"], max_lines))
        print_fn("-" * 72)
        if case is not None and case.actions:
            print_fn("what Claude did next:")
            for n, action in enumerate(case.actions[:8], 1):
                print_fn(f"  {n}. {action}")
        else:
            print_fn("what Claude did next: (transcript not found or nothing followed)")
        print_fn(f"automatic check: {automatic_check(case, entry)}")
        if show_judge:
            ps = [b.get("p") for b in entry.get("blocks", []) if b.get("hidden") and b.get("p") is not None]
            print_fn(f"judge: hidden blocks scored {', '.join(f'{p:.2f}' for p in ps)}")
        print_fn("-" * 72)
        while True:
            answer = input_fn("was hiding this fine? [y/x/u/s/q] ").strip().lower()
            if answer == "q":
                print_fn(f"{saved} reviews saved.")
                return saved
            if answer == "s":
                break
            verdict = VERDICTS.get(answer)
            if verdict:
                record(cfg, key=str(event["key"]), verdict=verdict, reviewer=reviewer, event=event)
                saved += 1
                break
            print_fn("y, x, u, s, or q")
    print_fn(f"{saved} reviews saved to {cfg.home / 'review.jsonl'}. `winnow stats` reports human regret.")
    return saved


def review_stats(cfg: Config) -> dict[str, Any]:
    path = cfg.home / "review.jsonl"
    counts = {"fine": 0, "should_have_kept": 0, "unsure": 0}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            v = entry.get("verdict") if isinstance(entry, dict) else None
            if v in counts:
                counts[v] += 1
    decided = counts["fine"] + counts["should_have_kept"]
    return {
        "human_reviewed": sum(counts.values()),
        "human_fine": counts["fine"],
        "human_should_have_kept": counts["should_have_kept"],
        "human_unsure": counts["unsure"],
        "human_regret_rate": round(counts["should_have_kept"] / decided, 4) if decided else None,
    }

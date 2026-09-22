"""Command-line entry point.

``winnow hook <event>`` is what Claude Code runs. It reads the hook payload from
stdin, prints JSON to stdout when it has something to say, and always exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from winnow import __version__, cache, log
from winnow.config import Config, credential_status, env_file_path, load_env_file


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    payload = json.loads(raw) if raw.strip() else {}
    return payload if isinstance(payload, dict) else {}


def _write_json(obj: Any) -> None:
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _notify_once(cfg: Config, session_id: str, message: str) -> dict[str, Any] | None:
    """Return a systemMessage the first time per session; stay silent afterwards."""
    marker = cfg.home / "notified" / (session_id or "no-session")
    try:
        if marker.exists():
            return None
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return None
    return {"systemMessage": message}


def run_hook(event: str) -> int:
    cfg = Config.from_env()
    try:
        from winnow.hooks import Runtime, post_tool_use, user_prompt_submit, worth_judging

        payload = _read_stdin_json()
        payload.setdefault("source", "cli")  # a direct `winnow hook` call; the module tags its own
        if event == "post-tool-use" and not worth_judging(payload, cfg):
            return 0  # fast path: most tool results are small; no judge, no SDK import
        try:
            runtime = Runtime.from_config(cfg)
        except Exception as exc:  # noqa: BLE001 - most often: no key for the configured judge
            log.log_error(cfg, "runtime", exc)
            notice = _notify_once(
                cfg,
                str(payload.get("session_id") or ""),
                f"winnow is installed but its judge could not start ({type(exc).__name__}: {str(exc)[:140]}). "
                "Tool results are passing through untouched. Run `winnow doctor` to fix it.",
            )
            if notice is not None:
                _write_json(notice)
            return 0
        if event == "post-tool-use":
            output = post_tool_use(payload, runtime)
        elif event == "user-prompt-submit":
            output = user_prompt_submit(payload, runtime)
        else:
            output = None
        if output is not None:
            _write_json(output)
    except Exception as exc:  # noqa: BLE001 - a hook must never break the tool call
        log.log_error(cfg, f"hook:{event}", exc)
    return 0


def run_recall(key: str, start: int | None, end: int | None) -> int:
    cfg = Config.from_env()
    entry = cache.load(cfg, key)
    if entry is None:
        print(f"no cached output for key {key!r}", file=sys.stderr)
        return 1
    log.log_event(cfg, {"event": "recall", "key": key, "start": start, "end": end, "via": "cli"})
    print(cache.slice_lines(str(entry.get("text", "")), start, end, int(entry.get("line_offset") or 1)))
    return 0


def run_stats() -> int:
    for name, value in log.stats(Config.from_env()).items():
        print(f"{name:24} {value}")
    return 0


def run_doctor(loaded_from_env_file: list[str]) -> int:
    cfg = Config.from_env()
    print(f"winnow {__version__}")
    print(f"home                     {cfg.home}")
    print(f"mode                     {cfg.mode}" + ("  (judging and logging only; tool results are never changed)" if cfg.shadow else ""))
    env_path = env_file_path()
    print(f"env file                 {env_path} ({'found, loaded ' + ', '.join(loaded_from_env_file) if loaded_from_env_file else ('found, nothing new' if env_path.is_file() else 'not present')})")
    for name, status in credential_status().items():
        print(f"{name:24} {status}")
    print(f"judge                    {cfg.judge} (model={cfg.model if cfg.judge == 'typesafe' else cfg.adapter_model})")
    print(f"tools                    {', '.join(cfg.tools)}")
    print(f"thresholds               drop<{cfg.drop}  keep>={cfg.keep}  min_prune_ratio={cfg.min_prune_ratio}")
    print(f"summary                  {'on' if cfg.summary else 'off'} ({cfg.summary_model})")
    ok = True
    try:
        from winnow.judge import build_judge

        judge = build_judge(cfg)
        print(f"judge backend            {'ok: ' + judge.name if judge else 'off'}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"judge backend            FAILED: {exc!r}")
    try:
        from winnow.summarize import build_summarizer

        summarizer = build_summarizer(cfg)
        print(f"summarizer               {'ok: ' + summarizer.name if summarizer else 'off'}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"summarizer               FAILED: {exc!r}")
    try:
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"cache dir                writable: {cfg.cache_dir}")
    except OSError as exc:
        ok = False
        print(f"cache dir                FAILED: {exc!r}")
    from winnow import serve as serve_mod

    port = int(os.environ.get("WINNOW_PORT") or serve_mod.DEFAULT_PORT)
    info = serve_mod.health(port)
    if info:
        print(f"sidecar                  running on 127.0.0.1:{port} (pid {info.get('pid')}, {info.get('requests')} requests, judge {'ready' if info.get('judge_ready') else 'not built yet'})")
    else:
        print(f"sidecar                  not running on 127.0.0.1:{port} (started by the SessionStart hook; `winnow serve --ensure` starts one)")
    flag = function_hooks_flag()
    if flag == "settings":
        print("function hooks           enabled in ~/.claude/settings.json")
    elif flag == "env":
        print("function hooks           enabled in this shell only; put CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 in the env block of ~/.claude/settings.json so every session has it")
    else:
        ok = False
        print(
            "function hooks           NOT ENABLED: winnow does nothing until ~/.claude/settings.json has "
            '{"env": {"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1"}} (Claude Code 2.1.260+); sessions started after adding it load the module'
        )
    return 0 if ok else 1


def function_hooks_flag() -> str | None:
    """Where CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 is set: "settings", "env", or None. The module never loads without it."""
    import json
    from pathlib import Path

    try:
        settings = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
        if str((settings.get("env") or {}).get("CLAUDE_CODE_ENABLE_FUNCTION_HOOKS", "")) == "1":
            return "settings"
    except (OSError, ValueError, AttributeError):
        pass
    if os.environ.get("CLAUDE_CODE_ENABLE_FUNCTION_HOOKS") == "1":
        return "env"
    return None


def _transcript_paths(raw: list[str]):
    from pathlib import Path

    from winnow.replay import default_transcripts

    if not raw:
        return default_transcripts()
    paths = []
    for item in raw:
        p = Path(item).expanduser()
        if p.is_dir():
            paths.extend(sorted(p.rglob("*.jsonl")))
        elif p.is_file():
            paths.append(p)
        else:
            print(f"winnow replay: not found: {p}", file=sys.stderr)
    return paths


def run_label_command(args: Any, cfg: Config) -> int:
    from pathlib import Path

    from winnow import labels as labels_mod
    from winnow import replay

    if args.replay_command == "sample":
        judged = Path(args.judged)
        cases_path = Path(args.cases) if args.cases else cfg.replay_dir / "cases.jsonl"
        out = Path(args.out) if args.out else cfg.replay_dir / "sample.jsonl"
        items = labels_mod.sample(cfg, judged, cases_path, n_low=args.n_low, n_mid=args.n_mid, n_high=args.n_high, seed=args.seed)
        md = out.with_suffix(".md")
        labels_mod.write_sample(items, out, md)
        bins = {name: sum(1 for it in items if it["bin"] == name) for name in labels_mod.BINS}
        print(f"{len(items)} blocks sampled {bins} -> {out}\nlabeling sheet -> {md}")
        return 0
    sample_path = Path(args.sample)
    items = list(replay.read_jsonl(sample_path))
    labels_path = Path(args.labels) if getattr(args, "labels", None) else sample_path.with_name("labels.jsonl")
    if args.replay_command == "label":
        n = labels_mod.label_interactive(items, labels_path, args.labeler, limit=args.limit, seed=args.seed, show_judge=args.show_judge)
        print(f"{n} labels saved to {labels_path}")
        return 0
    if args.replay_command == "import-labels":
        answers = labels_mod.parse_answers(Path(args.answers).read_text(encoding="utf-8"))
        n = labels_mod.import_answers(items, answers, labels_path, args.labeler)
        print(f"{n} labels imported for {args.labeler!r} -> {labels_path}")
        return 0
    if args.replay_command == "agreement":
        result = labels_mod.agreement(items, labels_mod.load_labels(labels_path))
        print(json.dumps(result, indent=2))
        return 0
    return 2


def run_replay_command(args: Any) -> int:
    from pathlib import Path

    from winnow import replay

    cfg = Config.from_env()
    if args.replay_command == "extract":
        paths = _transcript_paths(args.paths)
        out = Path(args.out) if args.out else cfg.replay_dir / "cases.jsonl"
        n = replay.write_jsonl(out, (replay.case_to_dict(c) for c in replay.extract_cases(paths, cfg, limit=args.limit, window=args.window)))
        print(f"{n} cases from {len(paths)} transcripts -> {out}")
        return 0
    if args.replay_command == "judge":
        cases_path = Path(args.cases) if args.cases else cfg.replay_dir / "cases.jsonl"
        if not cases_path.exists():
            print(f"winnow replay: no cases file at {cases_path}; run `winnow replay extract` first", file=sys.stderr)
            return 1
        try:
            judge = replay.build_replay_judge(args.judge, cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"winnow replay: the {args.judge} judge could not start: {exc}", file=sys.stderr)
            return 1
        qname = args.questions or cfg.questions
        suffix = f"{args.judge}" if qname == "default" else f"{args.judge}-{qname}"
        out = Path(args.out) if args.out else cfg.replay_dir / f"judged-{suffix}.jsonl"
        cases = (replay.case_from_dict(d) for d in replay.read_jsonl(cases_path))
        n = replay.write_jsonl(out, replay.judge_cases(cases, judge, cfg, limit=args.limit, questions=qname))
        print(f"{n} cases judged by {judge.name} with questions={qname} -> {out}")
        scored = replay.score(replay.read_jsonl(out))
        score_path = out.with_name(out.name.replace("judged-", "score-", 1)).with_suffix(".json")
        score_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")
        print(replay.format_report(scored))
        print(f"\nscore written to {score_path}")
        return 0
    if args.replay_command == "score":
        from winnow import labels as labels_mod

        hand = None
        if args.labels:
            hand = labels_mod.hand_label_map(labels_mod.load_labels(Path(args.labels)), args.labeler)
            if not hand:
                print(f"winnow replay: no usable labels in {args.labels}" + (f" for labeler {args.labeler!r}" if args.labeler else ""), file=sys.stderr)
                return 1
        scored = replay.score(replay.read_jsonl(Path(args.judged)), hand_labels=hand)
        print(replay.format_report(scored))
        if args.json:
            Path(args.json).write_text(json.dumps(scored, indent=2), encoding="utf-8")
        return 0
    if args.replay_command in ("sample", "label", "import-labels", "agreement"):
        return run_label_command(args, cfg)
    if args.replay_command == "run":
        paths = _transcript_paths(args.paths)
        if not paths:
            print("winnow replay: no transcripts found", file=sys.stderr)
            return 1
        try:
            scored, score_path = replay.run_replay(cfg, paths=paths, judge_name=args.judge, limit=args.limit, window=args.window)
        except Exception as exc:  # noqa: BLE001
            print(f"winnow replay: failed: {exc}", file=sys.stderr)
            return 1
        print(replay.format_report(scored))
        print(f"\nscore written to {score_path}")
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="winnow", description="A calibrated context sieve for Claude Code.")
    parser.add_argument("--version", action="version", version=f"winnow {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    hook = sub.add_parser("hook", help="run as a Claude Code hook (payload on stdin)")
    hook.add_argument("event", choices=["post-tool-use", "user-prompt-submit"])

    recall = sub.add_parser("recall", help="print the cached text behind a stub key")
    recall.add_argument("key")
    recall.add_argument("--start", type=int)
    recall.add_argument("--end", type=int)

    sub.add_parser("stats", help="tokens saved, rewrites, regret rate")
    sub.add_parser("mcp", help="run the recall MCP server on stdio")
    sub.add_parser("doctor", help="check configuration and backends")

    demo = sub.add_parser("demo", help="judge a synthetic tool result and show what Claude would see")
    demo.add_argument("--fake", action="store_true", help="use a keyword judge; needs no keys")

    bench = sub.add_parser("bench", help="measure hook startup overhead with the judge off")
    bench.add_argument("--runs", type=int, default=10)
    bench.add_argument("--skip-uv", action="store_true", help="time only the Python entry point, not uv run")
    bench.add_argument("--http", action="store_true", help="also time the resident sidecar, if one is running")

    serve = sub.add_parser("serve", help="run the resident sidecar that http hooks talk to")
    serve.add_argument("--port", type=int, default=None, help="default: WINNOW_PORT or 47311")
    serve.add_argument("--idle-minutes", type=float, default=45, help="exit after this long without a request")
    serve.add_argument("--ensure", action="store_true", help="start a detached server only if none is running (SessionStart)")
    serve.add_argument("--stop", action="store_true")
    serve.add_argument("--status", action="store_true")

    clean = sub.add_parser("clean", help="delete old cache entries")
    clean.add_argument("--older-than-days", type=float, default=30)
    clean.add_argument("--max-mb", type=float, default=200)
    clean.add_argument("--dry-run", action="store_true")

    review = sub.add_parser("review", help="judge recent stubs from your own sessions: was hiding that fine?")
    review.add_argument("--limit", type=int, default=10)
    review.add_argument("--reviewer", default=os.environ.get("USERNAME") or os.environ.get("USER") or "human")
    review.add_argument("--since-days", type=float, default=7)
    review.add_argument("--session", help="only stubs from this session id")
    review.add_argument("--max-lines", type=int, default=40, help="lines of hidden text to show per group")
    review.add_argument("--show-judge", action="store_true", help="also show the judge's probabilities for the hidden blocks")

    replay = sub.add_parser("replay", help="score a judge against your own Claude Code transcripts")
    replay_sub = replay.add_subparsers(dest="replay_command", required=True)
    rp_extract = replay_sub.add_parser("extract", help="transcripts -> cases.jsonl (offline)")
    rp_extract.add_argument("paths", nargs="*", help="transcript .jsonl files or directories; default: all of ~/.claude/projects")
    rp_extract.add_argument("--out")
    rp_extract.add_argument("--limit", type=int)
    rp_extract.add_argument("--window", type=int, default=12, help="assistant events after a result that count as evidence")
    rp_judge = replay_sub.add_parser("judge", help="cases.jsonl -> judged file (calls the judge)")
    rp_judge.add_argument("--cases")
    rp_judge.add_argument("--judge", default="lexical", choices=["lexical", "typesafe", "adapter"])
    rp_judge.add_argument("--questions", help="question set to ask with (default: WINNOW_QUESTIONS)")
    rp_judge.add_argument("--out")
    rp_judge.add_argument("--limit", type=int)
    rp_score = replay_sub.add_parser("score", help="judged file -> report (offline)")
    rp_score.add_argument("--judged", required=True)
    rp_score.add_argument("--labels", help="labels.jsonl; score against hand labels instead of weak ones")
    rp_score.add_argument("--labeler", help="use only this labeler's labels")
    rp_score.add_argument("--json", help="also write the score as JSON here")
    rp_sample = replay_sub.add_parser("sample", help="draw blocks from a judged file for hand labeling (blind)")
    rp_sample.add_argument("--judged", required=True)
    rp_sample.add_argument("--cases")
    rp_sample.add_argument("--n-low", type=int, default=50)
    rp_sample.add_argument("--n-mid", type=int, default=25)
    rp_sample.add_argument("--n-high", type=int, default=25)
    rp_sample.add_argument("--seed", type=int, default=1)
    rp_sample.add_argument("--out", help="output .jsonl path; a .md sheet is written next to it")
    rp_label = replay_sub.add_parser("label", help="label sampled blocks interactively")
    rp_label.add_argument("--sample", required=True)
    rp_label.add_argument("--labeler", required=True)
    rp_label.add_argument("--labels", help="labels.jsonl to append to (default: next to the sample)")
    rp_label.add_argument("--limit", type=int)
    rp_label.add_argument("--seed", type=int)
    rp_label.add_argument("--show-judge", action="store_true")
    rp_import = replay_sub.add_parser("import-labels", help="import answers from a text file (`<n> y|x|u` per line)")
    rp_import.add_argument("--sample", required=True)
    rp_import.add_argument("--answers", required=True)
    rp_import.add_argument("--labeler", required=True)
    rp_import.add_argument("--labels")
    rp_agree = replay_sub.add_parser("agreement", help="weak label vs each labeler, and labeler vs labeler")
    rp_agree.add_argument("--sample", required=True)
    rp_agree.add_argument("--labels")
    rp_run = replay_sub.add_parser("run", help="extract, judge, and score in one go")
    rp_run.add_argument("paths", nargs="*")
    rp_run.add_argument("--judge", default="lexical", choices=["lexical", "typesafe", "adapter"])
    rp_run.add_argument("--limit", type=int, help="max cases to extract")
    rp_run.add_argument("--window", type=int, default=12, help="assistant events after a result that count as evidence")

    args = parser.parse_args(argv)
    loaded = load_env_file()
    if args.command == "demo":
        from winnow.demo import run_demo

        return run_demo(fake=args.fake)
    if args.command == "bench":
        from winnow.bench import run_bench

        return run_bench(runs=args.runs, skip_uv=args.skip_uv, http=args.http)
    if args.command == "serve":
        from winnow import serve as serve_mod

        port = args.port or int(os.environ.get("WINNOW_PORT") or serve_mod.DEFAULT_PORT)
        if args.status:
            info = serve_mod.health(port)
            print(json.dumps(info, indent=2) if info else f"no sidecar answering on 127.0.0.1:{port}")
            return 0 if info else 1
        if args.stop:
            print("stopped" if serve_mod.stop(port) else f"no sidecar answering on 127.0.0.1:{port}")
            return 0
        if args.ensure:
            ok = serve_mod.ensure(port)
            return 0 if ok else 1  # silent: SessionStart stdout would go into Claude's context
        return serve_mod.run_server(port=port, idle_minutes=args.idle_minutes)
    if args.command == "clean":
        result = cache.clean(Config.from_env(), older_than_days=args.older_than_days, max_mb=args.max_mb, dry_run=args.dry_run)
        for name, value in result.items():
            print(f"{name:32} {value}")
        return 0
    if args.command == "review":
        from winnow.review import run_review

        run_review(
            Config.from_env(),
            limit=args.limit,
            reviewer=args.reviewer,
            since_days=args.since_days,
            session=args.session,
            max_lines=args.max_lines,
            show_judge=args.show_judge,
        )
        return 0
    if args.command == "replay":
        return run_replay_command(args)
    if args.command == "hook":
        return run_hook(args.event)
    if args.command == "recall":
        return run_recall(args.key, args.start, args.end)
    if args.command == "stats":
        return run_stats()
    if args.command == "mcp":
        from winnow.mcp_server import main as mcp_main

        mcp_main()
        return 0
    if args.command == "doctor":
        return run_doctor(loaded)
    return 2

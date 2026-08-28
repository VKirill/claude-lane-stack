from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from usage_ledger import (  # noqa: E402
    backfill_api_usd,
    cost_from_receipt,
    critique_follow_stats,
    estimate_api_usd,
    match_openrouter_model,
    merge_usage,
    model_slug,
    normalize_usage,
    record_critique_dispatch,
    record_critique_result,
    record_hook_payload,
    rebuild_day,
    record_receipt,
    record_transcript,
    row_payload,
    rows,
    tokens_from_usage,
    usage_from_event,
    usage_from_stdout,
    write_openrouter_prices_table,
)

_FAKE_CATALOG = [
    {
        "id": "openai/gpt-5.6-sol:batch",
        "pricing": {"prompt": "9", "completion": "9"},
    },
    {
        "id": "openai/gpt-5.6-sol-pro",
        "pricing": {"prompt": "0.000003", "completion": "0.00002", "input_cache_read": "0.0000003"},
    },
    {
        "id": "openai/gpt-5.6-sol",
        "pricing": {"prompt": "0.000002", "completion": "0.00001", "input_cache_read": "0.0000002"},
    },
    {
        "id": "x-ai/grok-4.6",
        "pricing": {"prompt": "0.000001", "completion": "0.000003", "input_cache_read": "0.0000001"},
    },
    {
        "id": "anthropic/claude-haiku-4.5",
        "pricing": {"prompt": "0.000001", "completion": "0.000005", "input_cache_read": "0.0000001"},
    },
    {
        "id": "z-ai/glm-5.3-flash",
        "pricing": {"prompt": "0.0000001", "completion": "0.0000004", "input_cache_read": "0.00000001"},
    },
]


class UsageLedgerTest(unittest.TestCase):
    def test_sums_in_out_cache_per_cli_per_day(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "usage.sqlite"
            first = {
                "provider": "grok",
                "model": "grok-4.5",
                "finished_at": "2026-08-26T10:00:00+00:00",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "reasoning_tokens": 2,
                    "cache_read_input_tokens": 3,
                    "total_tokens": 17,
                },
                "total_cost_usd": 0.01,
            }
            second = {
                "provider": "grok",
                "model": "grok-4.5",
                "finished_at": "2026-08-26T18:00:00+00:00",
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 1,
                    "cached_input_tokens": 2,
                    "total_tokens": 8,
                },
                "total_cost_usd_ticks": 100000000,
            }
            other = {
                "provider": "opencode",
                "model": "qwen3.8",
                "finished_at": "2026-08-26T12:00:00+00:00",
                "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            }
            next_day = {
                "provider": "grok",
                "model": "grok-4.5",
                "finished_at": "2026-08-27T01:00:00+00:00",
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
            self.assertTrue(record_receipt(first, path=path))
            self.assertTrue(record_receipt(second, path=path))
            self.assertTrue(record_receipt(other, path=path))
            self.assertTrue(record_receipt(next_day, path=path))
            self.assertFalse(
                record_receipt({"provider": "kimi", "finished_at": "2026-08-26T00:00:00Z"}, path=path)
            )

            day = {f"{row['cli']}:{row['model']}": row for row in rows(path, day="2026-08-26")}
            grok = day["grok:grok-4.5"]
            self.assertEqual(grok["input_tokens"], 15)
            self.assertEqual(grok["output_tokens"], 7)
            self.assertEqual(grok["cache_tokens"], 5)
            self.assertEqual(grok["total_tokens"], 25)
            self.assertAlmostEqual(grok["cost_usd"], 0.02)
            self.assertEqual(grok["calls"], 2)
            self.assertEqual(day["opencode:qwen3.8"]["input_tokens"], 100)
            self.assertEqual(len(rows(path, day="2026-08-27")), 1)

    def test_token_and_cost_helpers(self) -> None:
        self.assertEqual(
            tokens_from_usage(
                {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "reasoning_tokens": 2,
                    "cache_read_input_tokens": 3,
                    "total_tokens": 17,
                }
            ),
            (10, 6, 3, 17),
        )
        self.assertEqual(cost_from_receipt({"total_cost_usd_ticks": 100000000}), 0.01)

    def test_normalizes_cursor_opencode_claude_shapes(self) -> None:
        self.assertEqual(
            normalize_usage({"inputTokens": 10, "outputTokens": 5, "cacheReadTokens": 3}),
            {
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_input_tokens": 3,
            },
        )
        self.assertEqual(
            normalize_usage({"prompt_tokens": 8, "completion_tokens": 3})["input_tokens"],
            8,
        )
        usage, cost = usage_from_event(
            {
                "type": "step_finish",
                "part": {
                    "cost": 0.001,
                    "tokens": {
                        "input": 671,
                        "output": 8,
                        "reasoning": 2,
                        "cache": {"read": 3, "write": 1},
                    },
                },
            }
        )
        self.assertEqual(cost, 0.001)
        self.assertEqual(usage["input_tokens"], 671)
        self.assertEqual(usage["cache_creation_input_tokens"], 1)
        self.assertEqual(
            normalize_usage(
                {
                    "input_tokens": 10,
                    "cached_input_tokens": 4,
                    "cache_write_input_tokens": 2,
                    "output_tokens": 5,
                }
            )["cache_creation_input_tokens"],
            2,
        )
        self.assertEqual(
            tokens_from_usage(
                {
                    "input_tokens": 2,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 4,
                    "output_tokens": 8,
                }
            ),
            (2, 8, 14, 24),
        )

    def test_usage_from_stdout_agy_envelope(self) -> None:
        usage, cost = usage_from_stdout(
            json.dumps(
                {
                    "result": {
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 3,
                            "cache_read_tokens": 40,
                        },
                        "cost": 0.002,
                        "response": {"verdict": "ship", "findings": []},
                    }
                }
            )
        )
        self.assertEqual(usage["input_tokens"], 12)
        self.assertEqual(usage["cache_read_input_tokens"], 40)
        self.assertEqual(cost, 0.002)

    def test_transcript_delta_does_not_double_count(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            transcript = Path(raw) / "session.jsonl"
            transcript.write_text(
                json.dumps(
                    {
                        "message": {
                            "model": "claude-opus",
                            "usage": {
                                "input_tokens": 2,
                                "cache_creation_input_tokens": 10,
                                "output_tokens": 8,
                            },
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(
                record_transcript(transcript, cli="claude", session_id="s1", path=db)
            )
            self.assertFalse(
                record_transcript(transcript, cli="claude", session_id="s1", path=db)
            )
            row = rows(db, day=rows(db)[0]["day"])[0]
            self.assertEqual(row["cli"], "claude")
            self.assertEqual(row["input_tokens"], 2)
            self.assertEqual(row["cache_tokens"], 10)
            self.assertEqual(row["calls"], 1)

    def test_hook_ingests_sibling_subagent_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            parent = Path(raw) / "sess.jsonl"
            parent.write_text(
                json.dumps(
                    {
                        "message": {
                            "model": "claude-fable-5",
                            "usage": {
                                "input_tokens": 2,
                                "cache_creation_input_tokens": 10,
                                "output_tokens": 3,
                            },
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            sub = Path(raw) / "sess" / "subagents"
            sub.mkdir(parents=True)
            (sub / "agent-ars.jsonl").write_text(
                json.dumps(
                    {
                        "isSidechain": True,
                        "sessionId": "sess",
                        "message": {
                            "model": "claude-sonnet-5",
                            "usage": {
                                "input_tokens": 4,
                                "cache_read_input_tokens": 20,
                                "output_tokens": 5,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertTrue(
                record_hook_payload(
                    {"transcript_path": str(parent), "client": "claude"},
                    path=db,
                )
            )
            day = {row["model"]: row for row in rows(db)}
            self.assertEqual(day["claude-fable-5"]["input_tokens"], 2)
            self.assertEqual(day["claude-sonnet-5"]["input_tokens"], 4)
            self.assertEqual(day["claude-sonnet-5"]["cache_tokens"], 20)

    def test_transcript_cache_is_session_peak_not_sum(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            transcript = Path(raw) / "session.jsonl"
            turns = [
                {
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 2,
                            "cache_creation_input_tokens": 30,
                            "output_tokens": 8,
                        },
                    }
                },
                {
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 2,
                            "cache_read_input_tokens": 30,
                            "cache_creation_input_tokens": 20,
                            "output_tokens": 4,
                        },
                    }
                },
                {
                    "isSidechain": True,
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 9,
                            "cache_read_input_tokens": 999,
                            "output_tokens": 9,
                        },
                    },
                },
                {
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 2,
                            "cache_read_input_tokens": 80,
                            "output_tokens": 3,
                        },
                    }
                },
            ]
            transcript.write_text(
                "".join(json.dumps(turn) + "\n" for turn in turns[:2]),
                encoding="utf-8",
            )
            self.assertTrue(
                record_transcript(transcript, cli="claude", session_id="s-peak", path=db)
            )
            row = rows(db)[0]
            self.assertEqual(row["input_tokens"], 4)
            self.assertEqual(row["output_tokens"], 12)
            self.assertEqual(row["cache_tokens"], 50)
            transcript.write_text(
                "".join(json.dumps(turn) + "\n" for turn in turns),
                encoding="utf-8",
            )
            self.assertTrue(
                record_transcript(transcript, cli="claude", session_id="s-peak", path=db)
            )
            row = rows(db)[0]
            self.assertEqual(row["input_tokens"], 6)
            self.assertEqual(row["output_tokens"], 15)
            self.assertEqual(row["cache_tokens"], 80)
            self.assertEqual(row["total_tokens"], 101)

    def test_rebuild_day_uses_session_cache_peak(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            projects = Path(raw) / "projects" / "app"
            projects.mkdir(parents=True)
            runs = Path(raw) / "apps" / "demo" / ".agents" / "runs" / "t1" / "artifacts" / "001" / "attempts" / "01"
            runs.mkdir(parents=True)
            transcript = projects / "sess-1.jsonl"
            turns = [
                {
                    "timestamp": "2026-08-27T10:00:00.000Z",
                    "sessionId": "sess-1",
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 2,
                            "cache_creation_input_tokens": 30,
                            "output_tokens": 8,
                        },
                    },
                },
                {
                    "timestamp": "2026-08-27T11:00:00.000Z",
                    "sessionId": "sess-1",
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 2,
                            "cache_read_input_tokens": 80,
                            "output_tokens": 4,
                        },
                    },
                },
                {
                    "timestamp": "2026-08-26T11:00:00.000Z",
                    "sessionId": "sess-1",
                    "message": {
                        "model": "claude-fable-5",
                        "usage": {
                            "input_tokens": 9,
                            "cache_read_input_tokens": 900,
                            "output_tokens": 9,
                        },
                    },
                },
            ]
            transcript.write_text(
                "".join(json.dumps(turn) + "\n" for turn in turns),
                encoding="utf-8",
            )
            sub = projects / "sess-1" / "subagents"
            sub.mkdir(parents=True)
            (sub / "agent-ars-demo.jsonl").write_text(
                json.dumps(
                    {
                        "timestamp": "2026-08-27T12:00:00.000Z",
                        "isSidechain": True,
                        "sessionId": "sess-1",
                        "message": {
                            "model": "claude-sonnet-5",
                            "usage": {
                                "input_tokens": 3,
                                "cache_read_input_tokens": 40,
                                "output_tokens": 5,
                            },
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (runs / "runtime.json").write_text(
                json.dumps(
                    {
                        "provider": "opencode",
                        "model": "zai-coding-plan/glm-5.3-flash",
                        "finished_at": "2026-08-27T12:00:00+00:00",
                        "usage": {"input_tokens": 10, "output_tokens": 3, "cache_read_input_tokens": 7},
                    }
                ),
                encoding="utf-8",
            )
            record_receipt(
                {
                    "provider": "agy",
                    "model": "gemini-3.7-flash-high",
                    "finished_at": "2026-08-27T09:00:00+00:00",
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
                path=db,
            )
            record_receipt(
                {
                    "provider": "claude",
                    "model": "claude-fable-5",
                    "finished_at": "2026-08-27T09:00:00+00:00",
                    "usage": {
                        "input_tokens": 50,
                        "output_tokens": 50,
                        "cache_read_input_tokens": 50000,
                    },
                },
                path=db,
            )
            stats = rebuild_day(
                "2026-08-27",
                path=db,
                transcript_root=Path(raw) / "projects",
                receipt_roots=[Path(raw) / "apps"],
            )
            self.assertEqual(stats["sessions"], 2)
            self.assertEqual(stats["receipts"], 1)
            self.assertEqual(stats["kept"], 1)
            day = {f"{row['cli']}:{row['model']}": row for row in rows(db, day="2026-08-27")}
            self.assertEqual(day["claude:claude-sonnet-5"]["input_tokens"], 3)
            self.assertEqual(day["claude:claude-sonnet-5"]["cache_tokens"], 40)
            fable = day["claude:claude-fable-5"]
            self.assertEqual(fable["input_tokens"], 4)
            self.assertEqual(fable["output_tokens"], 12)
            self.assertEqual(fable["cache_tokens"], 80)
            self.assertEqual(day["opencode:zai-coding-plan/glm-5.3-flash"]["input_tokens"], 10)
            self.assertEqual(day["agy:gemini-3.7-flash-high"]["input_tokens"], 1)

    def test_merge_usage_keeps_cache_read_peak(self) -> None:
        merged = merge_usage(
            {"input_tokens": 2, "cache_read_input_tokens": 10, "output_tokens": 1},
            {"input_tokens": 3, "cache_read_input_tokens": 40, "output_tokens": 4},
        )
        self.assertEqual(merged["input_tokens"], 5)
        self.assertEqual(merged["output_tokens"], 5)
        self.assertEqual(merged["cache_read_input_tokens"], 40)

    def test_openrouter_match_and_estimate(self) -> None:
        self.assertEqual(model_slug("cursor-grok-4.6-high"), "grok-4.6")
        self.assertEqual(model_slug("claude-haiku-4-5-20251001"), "claude-haiku-4.5")
        self.assertEqual(
            match_openrouter_model("gpt-5.6-sol", _FAKE_CATALOG)["id"],
            "openai/gpt-5.6-sol",
        )
        self.assertEqual(
            match_openrouter_model("zai-coding-plan/glm-5.3-flash", _FAKE_CATALOG)["id"],
            "z-ai/glm-5.3-flash",
        )
        self.assertIsNone(match_openrouter_model("composer-2.5", _FAKE_CATALOG))
        usd, ident = estimate_api_usd("gpt-5.6-sol", 1000, 100, 50, _FAKE_CATALOG)
        self.assertEqual(ident, "openai/gpt-5.6-sol")
        self.assertAlmostEqual(usd, 0.00301)

    def test_writes_openrouter_prices_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / "openrouter-prices.tsv"
            path = write_openrouter_prices_table(_FAKE_CATALOG, dest=dest)
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "openai/gpt-5.6-sol\t\t0.000002\t0.00001\t0.0000002\t\t2.000000\t10.000000",
                text,
            )
            self.assertTrue(text.startswith("id\tname\tprompt\tcompletion"))

    def test_stores_api_usd_from_cached_prices(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            prices = Path(raw) / "openrouter-models.json"
            prices.write_text(
                json.dumps({"fetched_at": 1, "models": _FAKE_CATALOG}),
                encoding="utf-8",
            )
            self.assertTrue(
                record_receipt(
                    {
                        "provider": "codex",
                        "model": "gpt-5.6-sol",
                        "finished_at": "2026-08-26T10:00:00+00:00",
                        "usage": {
                            "input_tokens": 1000,
                            "output_tokens": 100,
                            "cache_read_input_tokens": 50,
                            "total_tokens": 1150,
                        },
                    },
                    path=db,
                )
            )
            payload = row_payload(rows(db)[0])
            self.assertAlmostEqual(payload["api_usd"], 0.00301)
            self.assertEqual(payload["cost_usd"], 0.0)
            self.assertEqual(backfill_api_usd(path=db, catalog=_FAKE_CATALOG), 1)
            self.assertAlmostEqual(row_payload(rows(db)[0])["api_usd"], 0.00301)

    def test_critique_follow_counts_accept_and_ignore(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            db = Path(raw) / "usage.sqlite"
            run_dir = Path(raw) / "app" / ".agents" / "runs" / "demo"
            run_dir.mkdir(parents=True)
            advised = {
                "decision": "revise",
                "summary": {"errors": 0, "warnings": 1},
                "llm_pass": {"provider": "agy", "model": "gemini-3.7-flash-high", "verdict": "revise"},
            }
            record_critique_result(run_dir, advised, mode="advisory", path=db)
            record_critique_result(
                run_dir,
                {"decision": "ship", "summary": {"errors": 0, "warnings": 0}, "llm_pass": {"verdict": "ship"}},
                mode="advisory",
                path=db,
            )
            other = Path(raw) / "app" / ".agents" / "runs" / "skip"
            other.mkdir(parents=True)
            (other / "artifacts").mkdir()
            (other / "artifacts" / "critique.json").write_text(
                json.dumps({"decision": "revise", "llm_pass": {"verdict": "revise"}}),
                encoding="utf-8",
            )
            record_critique_result(
                other,
                {"decision": "revise", "summary": {"errors": 0, "warnings": 1}, "llm_pass": {"verdict": "revise"}},
                path=db,
            )
            record_critique_dispatch(other, path=db)
            stats = critique_follow_stats(path=db)
            self.assertEqual(stats["advised"], 2)
            self.assertEqual(stats["followed"], 1)
            self.assertEqual(stats["ignored"], 1)
            self.assertEqual(stats["open"], 0)


if __name__ == "__main__":
    unittest.main()

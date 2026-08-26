from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from pipeline_stages import (  # noqa: E402
    ack_critique,
    attach_decision,
    compute_decision,
    critique_gate_errors,
    critique_should_run,
    gitnexus_caller_files,
    load_stages_from_profile,
    merge_llm_into_critique,
    normalize_stages,
    resolve_onboard,
    run_full_critique,
    stages_to_yaml_lines,
    structural_critique,
    write_critique_artifacts,
)
from routing_profile import load_routing_profile  # noqa: E402
from plan_critique_llm import (  # noqa: E402
    extract_json_payload,
    invoke_codex,
    invoke_opencode,
    parse_llm_payload,
)


class PipelineStagesTest(unittest.TestCase):
    def test_normalize_defaults(self) -> None:
        s = normalize_stages(None, write_provider="qwen")
        self.assertTrue(s["plan_critique"]["enabled"])
        self.assertEqual(s["plan_critique"]["mode"], "advisory")
        self.assertEqual(s["plan_critique"]["provider"], "structural")
        self.assertEqual(s["plan_critique"]["min_score"], 7)
        self.assertEqual(s["plan_critique"]["min_write_tasks"], 3)
        self.assertTrue(s["plan_critique"]["on_high_risk"])
        self.assertEqual(s["write"]["provider"], "qwen")
        self.assertFalse(s["specialist"]["enabled"])
        self.assertEqual(s["onboard"]["provider"], "codex")
        self.assertEqual(s["onboard"]["model"], "gpt-5.6-terra")
        self.assertEqual(s["onboard"]["reasoning_effort"], "high")
        self.assertEqual(s["onboard"]["service_tier"], "standard")
        self.assertEqual(s["plan_critique"]["service_tier"], "standard")

    def test_normalize_onboard_fast_and_yaml(self) -> None:
        s = normalize_stages(
            {
                "onboard": {
                    "provider": "codex",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "xhigh",
                    "service_tier": "fast",
                }
            },
            write_provider="kimi",
        )
        self.assertEqual(s["onboard"]["model"], "gpt-5.6-sol")
        self.assertEqual(s["onboard"]["reasoning_effort"], "xhigh")
        self.assertEqual(s["onboard"]["service_tier"], "fast")
        yaml_text = "\n".join(stages_to_yaml_lines(s))
        self.assertIn("onboard:", yaml_text)
        self.assertIn("service_tier: fast", yaml_text)
        # Non-codex/cursor: tier forced to standard and omitted from yaml
        s2 = normalize_stages(
            {"onboard": {"provider": "qwen", "service_tier": "fast"}},
            write_provider="qwen",
        )
        self.assertEqual(s2["onboard"]["service_tier"], "standard")
        lines = stages_to_yaml_lines(s2)
        start = lines.index("  onboard:")
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if lines[i].startswith("  ") and not lines[i].startswith("    "):
                end = i
                break
        onboard_yaml = "\n".join(lines[start:end])
        self.assertIn("provider: qwen", onboard_yaml)
        self.assertNotIn("service_tier:", onboard_yaml)

    def test_normalize_plan_critique_fast(self) -> None:
        s = normalize_stages(
            {
                "plan_critique": {
                    "provider": "codex",
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "low",
                    "service_tier": "fast",
                }
            },
            write_provider="kimi",
        )
        self.assertEqual(s["plan_critique"]["service_tier"], "fast")
        yaml_text = "\n".join(stages_to_yaml_lines(s))
        start = yaml_text.index("  plan_critique:")
        end = yaml_text.index("  write:")
        self.assertIn("service_tier: fast", yaml_text[start:end])
        s2 = normalize_stages(
            {"plan_critique": {"provider": "qwen", "service_tier": "fast"}},
            write_provider="kimi",
        )
        self.assertEqual(s2["plan_critique"]["service_tier"], "standard")

    def test_load_stages_from_yaml_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".agents").mkdir()
            (root / ".agents" / "routing.profile.yaml").write_text(
                textwrap.dedent(
                    """\
                    pm: claude
                    profile: full
                    lanes:
                      main_write: kimi
                    writer:
                      provider: kimi
                      model: kimi-code/k3-256k
                      reasoning_effort: medium
                    stages:
                      plan_critique:
                        enabled: true
                        mode: gate
                        provider: qwen
                        model: qwen3.8-max-preview
                        reasoning_effort: low
                      write:
                        provider: kimi
                        model: kimi-code/k3-256k
                        reasoning_effort: medium
                      night_review:
                        enabled: true
                        provider: qwen
                      specialist:
                        enabled: true
                        when: high_risk
                        provider: codex
                        model: gpt-5.6-sol
                        reasoning_effort: high
                      onboard:
                        provider: codex
                        model: gpt-5.6-sol
                        reasoning_effort: high
                        service_tier: fast
                    """
                ),
                encoding="utf-8",
            )
            profile = load_routing_profile(root)
            stages = load_stages_from_profile(profile)
            self.assertEqual(stages["plan_critique"]["mode"], "gate")
            self.assertEqual(stages["plan_critique"]["provider"], "qwen")
            self.assertTrue(stages["specialist"]["enabled"])
            self.assertEqual(stages["night_review"]["provider"], "qwen")
            self.assertEqual(stages["onboard"]["model"], "gpt-5.6-sol")
            self.assertEqual(stages["onboard"]["service_tier"], "fast")
            resolved = resolve_onboard(root)
            self.assertEqual(resolved["provider"], "codex")
            self.assertEqual(resolved["model"], "gpt-5.6-sol")
            self.assertEqual(resolved["service_tier"], "fast")

    def test_structural_critique_flags_empty_owns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 5\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text("# Plan\nshort\n", encoding="utf-8")
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "x"
                    owns_paths: []
                    verification: []
                    """
                ),
                encoding="utf-8",
            )
            result = structural_critique(run_dir)
            self.assertEqual(result["status"], "fail")
            codes = {f["code"] for f in result["findings"]}
            self.assertNotIn("plan_thin", codes)
            self.assertIn("owns_empty", codes)

    def test_critique_skips_small_runs(self) -> None:
        self.assertFalse(critique_should_run({"score": 2}, 1, {})[0])
        self.assertTrue(critique_should_run({"score": 8}, 1, {})[0])
        self.assertTrue(critique_should_run({"score": 2}, 3, {})[0])
        self.assertTrue(critique_should_run({"score": 1, "risk": "high"}, 1, {})[0])

    def test_coverage_flags_unlisted_importer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "foo.py").write_text("def foo():\n    return 1\n")
            (repo / "src" / "bar.py").write_text("from src.foo import foo\n")
            run_dir = repo / ".agents" / "runs" / "big"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                f"schema_version: 2\nscore: 8\nproject_cwd: {repo}\n",
                encoding="utf-8",
            )
            (run_dir / "PLAN.md").write_text("# Plan\nTouch foo helper.\n")
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Change foo helper used by the rest of the package"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -c 'print(1)'"
                    """
                ),
                encoding="utf-8",
            )
            result = run_full_critique(
                run_dir,
                settings={
                    "enabled": True,
                    "mode": "advisory",
                    "provider": "structural",
                    "min_score": 7,
                    "min_write_tasks": 3,
                    "on_high_risk": True,
                },
                structural_only=True,
            )
            codes = {f["code"] for f in result["findings"]}
            self.assertIn("owns_gap", codes)
            self.assertEqual(result["decision"], "revise")

    def test_owns_overlap_and_sibling_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "tests").mkdir()
            (repo / "src" / "foo.py").write_text("def foo():\n    return 1\n")
            (repo / "tests" / "test_foo.py").write_text("from src.foo import foo\n")
            run_dir = repo / ".agents" / "runs" / "big"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                f"schema_version: 2\nscore: 8\nproject_cwd: {repo}\n",
                encoding="utf-8",
            )
            (run_dir / "PLAN.md").write_text("# Plan\nTouch foo.\n")
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -c 'print(1)'"
                    """
                ),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "002.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "002"
                    owns_paths:
                      - src/
                    verification:
                      - command: "python3 -c 'print(1)'"
                    """
                ),
                encoding="utf-8",
            )
            result = structural_critique(run_dir)
            codes = {f["code"] for f in result["findings"]}
            self.assertIn("owns_overlap", codes)
            self.assertIn("owns_gap", codes)
            self.assertEqual(result["decision"], "revise_required")

    def test_critique_gate_and_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 1\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n" + ("goals and verification L1 L2 out of scope " * 5),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Ship a focused unit for feature X with clear DoD"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -m unittest tests/test_foo.py"
                        timeout_sec: 60
                    """
                ),
                encoding="utf-8",
            )
            result = structural_critique(run_dir)
            write_critique_artifacts(run_dir, result)
            settings = {"enabled": True, "mode": "gate"}
            # pass or fail depending on findings
            if result["status"] == "fail":
                errs = critique_gate_errors(run_dir, settings)
                self.assertTrue(errs)
                ack_critique(run_dir, note="accepted for micro", by="pm")
                errs2 = critique_gate_errors(run_dir, settings)
                self.assertEqual(errs2, [])
            else:
                self.assertEqual(critique_gate_errors(run_dir, settings), [])

    def test_plan_critique_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 0\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n"
                + ("Enough text for goals verification L1 out of scope risks. " * 4),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Add small helper with tests under owns"
                    owns_paths:
                      - bin/foo.py
                    verification:
                      - command: "python3 -c 'print(1)'"
                        timeout_sec: 30
                    """
                ),
                encoding="utf-8",
            )
            cli = ROOT / "bin" / "plan-critique"
            out = subprocess.run(
                [
                    sys.executable,
                    str(cli),
                    "--run-dir",
                    str(run_dir),
                    "--structural-only",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn(out.returncode, {0, 3}, out.stderr + out.stdout)
            payload = json.loads(out.stdout)
            self.assertIn(payload["status"], {"pass", "fail"})
            self.assertIn(payload["decision"], {"ship", "revise", "revise_required"})
            self.assertTrue((run_dir / "artifacts" / "critique.json").is_file())
            self.assertTrue((run_dir / "artifacts" / "critique.md").is_file())
            md = (run_dir / "artifacts" / "critique.md").read_text(encoding="utf-8")
            self.assertIn("PM decision", md)

    def test_decision_and_llm_merge(self) -> None:
        structural = {
            "schema_version": 1,
            "engine": "structural",
            "status": "pass",
            "summary": {"errors": 0, "warnings": 0, "infos": 0},
            "findings": [],
            "score": 3,
            "task_count": 1,
        }
        attach_decision(structural)
        self.assertEqual(structural["decision"], "ship")

        merged = merge_llm_into_critique(
            structural,
            {
                "verdict": "revise_required",
                "summary": "Add src/bar.py to owns_paths",
                "findings": [
                    {
                        "severity": "error",
                        "code": "owns_gap",
                        "title": "Missing companion path",
                        "detail": "Add src/bar.py to owns_paths",
                        "path": "tasks/001.yaml",
                        "task_id": "001",
                        "action": "fix_task",
                    }
                ],
            },
            provider="qwen",
            model="qwen3.8-max-preview",
        )
        self.assertEqual(merged["status"], "pass")
        self.assertEqual(merged["decision"], "ship")
        self.assertEqual(merged["llm_pass"]["status"], "ok")
        self.assertEqual(merged["llm_pass"]["summary"], "Add src/bar.py to owns_paths")
        self.assertFalse(any(str(f.get("source")) == "llm" for f in merged["findings"]))

        warn_only = merge_llm_into_critique(
            {
                "schema_version": 1,
                "engine": "coverage",
                "status": "pass",
                "summary": {"errors": 0, "warnings": 0, "infos": 0},
                "findings": [],
                "score": 1,
                "task_count": 1,
            },
            {
                "verdict": "revise",
                "summary": "outcome.json is stale; run-validate schema enum",
                "findings": [
                    {
                        "severity": "warn",
                        "code": "thin_risk",
                        "title": "Risk notes thin",
                        "detail": "Add failure modes",
                        "path": "PLAN.md",
                    }
                ],
            },
            provider="codex",
            model="gpt-5.6-luna",
        )
        self.assertEqual(warn_only["status"], "pass")
        self.assertEqual(warn_only["decision"], "ship")
        self.assertEqual(warn_only["llm_pass"]["summary"], "")

        failed_llm = merge_llm_into_critique(
            structural,
            None,
            provider="qwen",
            model="x",
            llm_error="timeout",
        )
        self.assertEqual(failed_llm["llm_pass"]["status"], "error")
        self.assertEqual(failed_llm["decision"], "ship")
        self.assertFalse(
            any(f["code"] == "llm_pass_failed" for f in failed_llm["findings"])
        )

    def test_parse_llm_payload(self) -> None:
        text = 'Here you go:\n```json\n{"verdict":"ship","summary":"ok","findings":[]}\n```\n'
        payload = parse_llm_payload(text)
        self.assertEqual(payload["verdict"], "ship")
        self.assertEqual(extract_json_payload('{"a":1}'), '{"a":1}')

    def test_run_full_critique_structural_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            (run_dir / "tasks").mkdir(parents=True)
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\nscore: 1\n", encoding="utf-8"
            )
            (run_dir / "PLAN.md").write_text(
                "# Plan\n" + ("goals verification L1 L2 out of scope risk " * 6),
                encoding="utf-8",
            )
            (run_dir / "tasks" / "001.yaml").write_text(
                textwrap.dedent(
                    """\
                    id: "001"
                    objective: "Ship a focused unit for feature X with clear DoD"
                    owns_paths:
                      - src/foo.py
                    verification:
                      - command: "python3 -m unittest tests/test_foo.py"
                        timeout_sec: 60
                    """
                ),
                encoding="utf-8",
            )
            result = run_full_critique(
                run_dir,
                settings={
                    "enabled": True,
                    "mode": "advisory",
                    "provider": "qwen",
                    "model": "qwen3.8-max-preview",
                },
                structural_only=True,
            )
            self.assertIn(result["decision"], {"ship", "revise", "revise_required"})
            self.assertEqual(result["llm_pass"]["status"], "skipped")

    def test_agents_doctor_writes_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            repo.mkdir()
            for name in ("claude", "kimi", "codex"):
                p = fake_bin / name
                p.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
                p.chmod(0o755)
            env = {**dict(**__import__("os").environ), "PATH": str(fake_bin)}
            doctor = ROOT / "bin" / "agents-doctor"
            result = subprocess.run(
                [
                    sys.executable,
                    str(doctor),
                    "--apply",
                    "--writer-provider",
                    "kimi",
                    "--plan-critique",
                    "on",
                    "--plan-critique-mode",
                    "gate",
                    "--plan-critique-provider",
                    "qwen",
                    "--night-review",
                    "off",
                    str(repo),
                ],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            text = (repo / ".agents" / "routing.profile.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn("stages:", text)
            self.assertIn("plan_critique:", text)
            self.assertIn("mode: gate", text)
            self.assertIn("provider: qwen", text)

    def test_invoke_codex_fast_flags(self) -> None:
        captured: list[list[str]] = []

        def fake_run(argv, **_kwargs):
            captured.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout='{"ok":true}', stderr="")

        with patch("plan_critique_llm._run", side_effect=fake_run), patch(
            "plan_critique_llm._which", return_value="/usr/bin/codex"
        ):
            invoke_codex(
                "prompt",
                model="gpt-5.6-terra",
                effort="low",
                timeout=5,
                service_tier="fast",
            )
        self.assertEqual(len(captured), 1)
        self.assertIn('service_tier="fast"', captured[0])
        self.assertIn("fast_mode", captured[0])

    def test_normalize_opencode_keeps_agent(self) -> None:
        s = normalize_stages(
            {
                "plan_critique": {
                    "provider": "opencode",
                    "model": "google/gemini-3.6-flash",
                    "agent": "plan",
                },
                "write": {
                    "provider": "opencode",
                    "model": "alibaba-token-plan/qwen3.8-max-preview",
                    "agent": "wiki-writer",
                },
            },
            write_provider="opencode",
        )
        self.assertEqual(s["plan_critique"]["agent"], "plan")
        self.assertEqual(s["write"]["agent"], "wiki-writer")
        yaml_text = "\n".join(stages_to_yaml_lines(s))
        self.assertIn("agent: plan", yaml_text)
        self.assertIn("agent: wiki-writer", yaml_text)

    def test_normalize_opencode_defaults_lane_agents(self) -> None:
        s = normalize_stages(
            {
                "plan_critique": {"provider": "opencode"},
                "night_review": {"provider": "opencode"},
                "specialist": {"provider": "opencode"},
            },
            write_provider="opencode",
        )
        self.assertEqual(s["write"]["agent"], "lane-writer")
        self.assertEqual(s["plan_critique"]["agent"], "lane-critic")
        self.assertEqual(s["night_review"]["agent"], "lane-reviewer")
        self.assertEqual(s["specialist"]["agent"], "lane-reviewer")

    def test_normalize_keeps_empty_opencode_effort(self) -> None:
        s = normalize_stages(
            {"write": {"reasoning_effort": ""}},
            write_provider="opencode",
        )
        self.assertEqual(s["write"]["reasoning_effort"], "")

    def test_invoke_opencode_flags(self) -> None:
        captured: list[list[str]] = []

        def fake_run(argv, **_kwargs):
            captured.append(list(argv))
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout='{"type":"text","part":{"text":"{\\"verdict\\":\\"ok\\"}"}}\n',
                stderr="",
            )

        with patch("plan_critique_llm._run", side_effect=fake_run), patch(
            "plan_critique_llm._which", return_value="/usr/bin/opencode"
        ):
            text = invoke_opencode(
                "prompt",
                model="alibaba-token-plan/qwen3.8-max-preview",
                effort="low",
                timeout=5,
                agent="plan",
            )
        self.assertEqual(len(captured), 1)
        self.assertIn("run", captured[0])
        self.assertIn("--pure", captured[0])
        self.assertEqual(captured[0][captured[0].index("--agent") + 1], "plan")
        self.assertEqual(captured[0][captured[0].index("--variant") + 1], "low")
        self.assertIn("--dangerously-skip-permissions", captured[0])
        self.assertIn('{"verdict":"ok"}', text)

    def test_invoke_opencode_omits_variant_when_empty(self) -> None:
        captured: list[list[str]] = []

        def fake_run(argv, **_kwargs):
            captured.append(list(argv))
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout='{"type":"text","part":{"text":"{\\"verdict\\":\\"ok\\"}"}}\n',
                stderr="",
            )

        with patch("plan_critique_llm._run", side_effect=fake_run), patch(
            "plan_critique_llm._which", return_value="/usr/bin/opencode"
        ):
            invoke_opencode(
                "prompt",
                model="alibaba-token-plan/kimi-k2.7-code",
                effort="",
                timeout=5,
                agent="lane-critic",
            )
        self.assertNotIn("--variant", captured[0])

    def test_gitnexus_skipped_without_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                gitnexus_caller_files(root, symbol="foo", file_path="src/foo.py"),
                [],
            )


if __name__ == "__main__":
    unittest.main()

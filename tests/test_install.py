from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"


class InstallTest(unittest.TestCase):
    def test_pm_boot_prompt_has_no_copyable_session_example(self) -> None:
        for rel in (
            "agents/claude/dev-orchestrator.md",
            "plugins/lane-stack/agents/dev-orchestrator.md",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("blyt-", text, rel)
            self.assertIn("Do **not** invent a", text, rel)
            self.assertIn("gitnexus analyze", text, rel)

    def test_lane_pm_does_not_resubmit_initial_prompt(self) -> None:
        text = (ROOT / "bin" / "lane-pm").read_text(encoding="utf-8")
        self.assertNotIn("extract_boot", text)
        self.assertNotIn('"$BOOT"', text)
        self.assertIn('exec claude --agent "$AGENT" --name "$NAME" "$@"', text)

    def test_lane_stack_resume_command_runs_cli(self) -> None:
        cmd = (
            ROOT / "plugins" / "lane-stack" / "commands" / "resume-project.md"
        ).read_text(encoding="utf-8")
        skill = (
            ROOT / "plugins" / "lane-stack" / "skills" / "resume-project" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("resume-project \"$(pwd)\" --compact", cmd)
        self.assertIn("Do not explain the skill", cmd)
        self.assertIn("user-invocable: false", skill)
        self.assertLess(skill.find("## MUST"), skill.find("## Info"))

    def test_site_copy_skills_are_shipped(self) -> None:
        skills = ROOT / "plugins" / "lane-stack" / "skills"
        for name in (
            "copy-project-life",
            "site-copy-audience",
            "site-copy-headlines",
            "site-copy-ux",
            "copy-research",
            "tavily",
            "page-prototype",
        ):
            text = (skills / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"name: {name}", text)
            self.assertIn("## NEVER", text)
        info = (skills / "info" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("copy-project-life", info)
        self.assertIn("опрос", info)
        self.assertIn("first-interview.md", info)
        self.assertIn("INDEX.md", info)
        refs = skills / "copy-project-life" / "references"
        for name in (
            "ANAMNESIS.template.md",
            "audience.template.md",
            "buyer-persona.template.md",
            "voice.template.md",
            "page-brief.template.md",
            "awareness-levels.md",
            "headline-types.md",
            "first-interview.md",
            "craft.md",
            "INDEX.template.md",
            "research-note.template.md",
        ):
            self.assertTrue((refs / name).is_file(), name)
        index = (refs / "INDEX.template.md").read_text(encoding="utf-8")
        self.assertIn("locked", index)
        self.assertIn("research/inbox", index)
        self.assertIn("on_site", index)
        craft = (refs / "craft.md").read_text(encoding="utf-8")
        self.assertIn("research/inbox/", craft)
        self.assertIn("locked", craft)
        playbook = skills / "copy-research" / "references" / "search-playbook.md"
        self.assertTrue(playbook.is_file())
        self.assertIn("firecrawl-deep-research", playbook.read_text(encoding="utf-8"))
        helpers = (skills / "copy-research" / "references" / "helpers.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("cursor-grok-4.6-medium-fast", helpers)
        self.assertIn("alibaba-token-plan/deepseek-v4-flash", helpers)
        self.assertIn("alibaba-token-plan/deepseek-v4-pro", helpers)
        self.assertIn("gpt-5.6-luna", helpers)
        self.assertIn("gpt-5.6-terra", helpers)
        self.assertIn("Do not `run-init`", helpers)
        tavily = (skills / "tavily" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("~/secrets/tavily.env", tavily)
        self.assertIn("https://api.tavily.com/search", tavily)
        self.assertIn("https://api.tavily.com/research", tavily)
        self.assertIn("research/inbox", tavily)
        self.assertNotIn("> .agents/copy/research/web.json", tavily)
        proto = (skills / "page-prototype" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(".agents/prototypes/", proto)
        self.assertIn("site/<slug>/index.html", proto)
        self.assertIn("app/<app>/<slug>/index.html", proto)
        self.assertIn("flows/<flow>/", proto)
        self.assertIn("shell.html", proto)
        self.assertIn("_kit/proto.css", proto)
        self.assertIn("data-proto-slider", proto)
        self.assertIn("publish.py", proto)
        self.assertIn("--bundle", proto)
        self.assertIn("html.vechkasov.pro", proto)
        pub = (skills / "page-prototype" / "references" / "publish.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"files"', pub)
        self.assertIn("--bundle", pub)
        self.assertIn(".host.json", pub)
        self.assertIn("force_new", pub)
        self.assertNotIn("No JavaScript", proto)
        self.assertTrue(
            (skills / "page-prototype" / "references" / "publish.py").is_file()
        )
        self.assertTrue((skills / "page-prototype" / "references" / "shell.html").is_file())
        self.assertTrue((skills / "page-prototype" / "references" / "kit" / "proto.css").is_file())
        self.assertTrue((skills / "page-prototype" / "references" / "kit" / "proto.js").is_file())
        self.assertTrue(
            (skills / "page-prototype" / "references" / "INDEX.template.md").is_file()
        )
        shell = (skills / "page-prototype" / "references" / "shell.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("_kit/proto.css", shell)
        self.assertIn("data-proto-slider", shell)

    def test_plugin_commands_hide_same_named_skills(self) -> None:
        commands = ROOT / "plugins" / "lane-stack" / "commands"
        skills = ROOT / "plugins" / "lane-stack" / "skills"
        for path in sorted(commands.glob("*.md")):
            skill = skills / path.stem / "SKILL.md"
            self.assertTrue(skill.is_file(), skill)
            self.assertIn("user-invocable: false", skill.read_text(encoding="utf-8"))

    def test_copy_lead_pack_is_shipped(self) -> None:
        agent = ROOT / "plugins" / "lane-stack" / "agents" / "copy-lead.md"
        self.assertTrue(agent.is_file())
        body = agent.read_text(encoding="utf-8")
        self.assertIn("name: copy-lead", body)
        self.assertIn("model: opus", body)
        self.assertIn("initialPrompt:", body)
        self.assertIn("copy-project-life", body)
        self.assertIn("site-copy-audience", body)
        self.assertIn("copy-research", body)
        self.assertIn("tavily", body)
        self.assertIn("page-prototype", body)
        self.assertIn("firecrawl-deep-research", body)
        self.assertIn("cursor-grok-4.6-medium-fast", body)
        self.assertIn("deepseek-v4-flash", body)
        self.assertIn("first-interview.md", body)
        self.assertIn("craft.md", body)
        self.assertIn("INDEX.md", body)
        self.assertIn("locked", body)
        self.assertIn("Agent(Explore, Plan, general-purpose)", body)
        self.assertNotIn("Agent(run-supervisor", body)
        self.assertNotIn("- karpathy-guidelines", body)
        style = ROOT / "plugins" / "lane-stack" / "output-styles" / "copywriter.md"
        self.assertTrue(style.is_file())
        style_text = style.read_text(encoding="utf-8")
        self.assertIn("keep-coding-instructions: false", style_text)
        self.assertIn("force-for-plugin: false", style_text)
        link = ROOT / "agents" / "claude" / "copy-lead.md"
        self.assertTrue(link.is_symlink() or link.is_file())
        info = (
            ROOT / "plugins" / "lane-stack" / "skills" / "info" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("copy-lead", info)
        orch = (
            ROOT / "plugins" / "lane-stack" / "agents" / "dev-orchestrator.md"
        ).read_text(encoding="utf-8")
        self.assertIn("copy-lead", orch)
        self.assertIn("page-prototype", orch)

    def test_tavily_pack_is_shipped(self) -> None:
        agent = ROOT / "plugins" / "lane-stack" / "agents" / "tavily.md"
        self.assertTrue(agent.is_file())
        body = agent.read_text(encoding="utf-8")
        self.assertIn("name: tavily", body)
        self.assertIn("initialPrompt:", body)
        self.assertIn("~/secrets/tavily.env", body)
        self.assertIn(".agents/research/", body)
        self.assertIn("inbox/", body)
        self.assertNotIn("Agent(run-supervisor", body)
        self.assertNotIn("- karpathy-guidelines", body)
        skill = (
            ROOT / "plugins" / "lane-stack" / "skills" / "tavily" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("name: tavily", skill)
        self.assertIn("https://api.tavily.com/search", skill)
        link = ROOT / "agents" / "claude" / "tavily.md"
        self.assertTrue(link.is_symlink() or link.is_file())
        info = (
            ROOT / "plugins" / "lane-stack" / "skills" / "info" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("`tavily`", info)
        orch = (
            ROOT / "plugins" / "lane-stack" / "agents" / "dev-orchestrator.md"
        ).read_text(encoding="utf-8")
        self.assertIn("tavily", orch)
        self.assertIn("Agent(run-supervisor, lane-supervisor, emergency-writer, night-reviewer, project-onboarder, docs-maintainer, design-lead, seo-specialist, copy-lead, tavily,", orch)

    def test_seo_specialist_pack_is_shipped(self) -> None:
        agent = ROOT / "plugins" / "lane-stack" / "agents" / "seo-specialist.md"
        self.assertTrue(agent.is_file())
        body = agent.read_text(encoding="utf-8")
        self.assertIn("name: seo-specialist", body)
        self.assertIn("initialPrompt:", body)
        self.assertIn("seo-drmax-orchestrator", body)
        self.assertIn("SendMessage", body)
        self.assertIn("ListAgents", body)
        self.assertIn("TaskStop", body)
        link = ROOT / "agents" / "claude" / "seo-specialist.md"
        self.assertTrue(link.is_symlink() or link.is_file())
        skills = ROOT / "plugins" / "lane-stack" / "skills"
        for name in (
            "seo-drmax-orchestrator",
            "seo-prompt-engineering-2026",
            "seo-evidence-based-2026",
            "seo-copywriting",
            "ai-detect",
            "drmax-latent-intent",
            "drmax-cvd",
            "drmax-text-humanization",
            "drmax-lexadapt",
            "mutagen",
            "xmlstock",
            "proxy6",
            "yandex-webmaster",
            "yandex-metrica",
            "google-search-console",
            "ga4-data-api",
            "google-cloud-auth",
            "page-prototype",
        ):
            skill = skills / name / "SKILL.md"
            self.assertTrue(skill.is_file(), skill)
            self.assertIn(f"name: {name}", skill.read_text(encoding="utf-8"))
        originals = skills / "seo-prompt-engineering-2026" / "references" / "originals"
        self.assertTrue(originals.is_dir(), originals)
        life = skills / "seo-project-life" / "SKILL.md"
        self.assertTrue(life.is_file(), life)
        self.assertIn("seo-project-life — карта SEO-проекта", life.read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "seo-system" / "modules" / "passport-onboard" / "module.yaml").is_file())
        self.assertTrue((ROOT / "docs" / "seo" / "SOLO-SEO-ORCHESTRATION.md").is_file())

    def test_plugin_agents_whitelist_sendmessage(self) -> None:
        missing: list[str] = []
        for path in sorted((ROOT / "plugins" / "lane-stack" / "agents").glob("*.md")):
            line = next(
                (
                    raw
                    for raw in path.read_text(encoding="utf-8").splitlines()
                    if raw.startswith("tools:")
                ),
                "",
            )
            if not line:
                missing.append(f"{path.name}: no tools")
                continue
            for tool in ("SendMessage", "ListAgents"):
                if tool not in line:
                    missing.append(f"{path.name}: missing {tool}")
        self.assertEqual(missing, [])

    def test_acceptance_template_includes_report_digest(self) -> None:
        acceptance = json.loads(
            (ROOT / "templates" / "run-contract" / "acceptance-v2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertRegex(acceptance["report_sha256"], r"^[0-9a-f]{64}$")
        schema = json.loads(
            (ROOT / "schemas" / "acceptance-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(acceptance)

    def test_installs_lane_board_and_serves_health_check(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            legacy_nested = home / ".agents" / "codex" / "instructions" / "instructions"
            legacy_nested.mkdir(parents=True)
            (legacy_nested / "reviewer.md").write_text("stale\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".agents" / "board" / "server" / "server.mjs").is_file())
            self.assertFalse(legacy_nested.exists())
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            board_env = env | {"HOST": "127.0.0.1", "PORT": str(port)}
            process = subprocess.Popen(
                [str(home / ".agents" / "bin" / "lane-board")],
                env=board_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.addCleanup(lambda: process.poll() is None and process.kill())
            url = f"http://127.0.0.1:{port}/healthz"
            for _ in range(50):
                try:
                    with urllib.request.urlopen(url, timeout=0.2) as response:
                        payload = json.load(response)
                    break
                except OSError:
                    if process.poll() is not None:
                        self.fail("installed lane-board exited before becoming healthy")
                    time.sleep(0.05)
            else:
                self.fail("installed lane-board did not become healthy")
            self.assertEqual(payload, {"ok": True})
            process.terminate()
            process.wait(timeout=5)

    def test_installs_daytime_controller_and_read_only_run_supervisor(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)
            stale_agent = home / ".claude" / "agents" / "seo-specialist.md"
            stale_agent.parent.mkdir(parents=True)
            stale_agent.write_text("stale user copy\n", encoding="utf-8")

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(stale_agent.exists())
            self.assertTrue(
                (
                    home
                    / ".agents"
                    / "skills"
                    / "seo-drmax-orchestrator"
                    / "SKILL.md"
                ).is_file()
            )
            self.assertTrue(
                (
                    home
                    / ".agents"
                    / "seo-system"
                    / "modules"
                    / "passport-onboard"
                    / "module.yaml"
                ).is_file()
            )
            self.assertTrue(
                (home / ".agents" / "skills" / "seo-project-life" / "SKILL.md").is_file()
            )
            controller = home / ".agents" / "bin" / "run-controller"
            self.assertTrue(controller.is_file())
            self.assertEqual(controller.stat().st_mode & 0o777, 0o755)

            supervisor = home / ".agents" / "agents" / "claude" / "run-supervisor.md"
            content = supervisor.read_text(encoding="utf-8")
            self.assertIn("name: run-supervisor", content)
            self.assertIn("Bash(run-controller start:*)", content)
            self.assertIn("Bash(run-controller watch:*)", content)
            self.assertNotIn("Write", content.partition("---\n")[2].partition("---\n")[0])
            self.assertNotIn("Edit", content.partition("---\n")[2].partition("---\n")[0])
            self.assertFalse((home / ".claude" / "agents" / "run-supervisor.md").exists())

            orchestrator = (
                home / ".agents" / "agents" / "claude" / "dev-orchestrator.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Agent(run-supervisor", orchestrator)
            self.assertIn("no daytime LLM review", orchestrator)
            self.assertNotIn("blyt-", orchestrator)
            self.assertIn("Do **not** invent a", orchestrator)
            self.assertTrue((home / ".agents" / "codex" / "instructions" / "reviewer.md").is_file())
            self.assertFalse((home / ".agents" / "codex" / "instructions" / "instructions").exists())

            marketplace = home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack"
            self.assertFalse(marketplace.exists())
            settings = json.loads(
                (home / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
            ours = settings["extraKnownMarketplaces"]["claude-lane-stack"]
            self.assertEqual(ours["source"]["source"], "github")
            self.assertEqual(ours["source"]["repo"], "VKirill/claude-lane-stack")
            self.assertTrue(ours["autoUpdate"])
            self.assertTrue(settings["enabledPlugins"]["lane-stack@claude-lane-stack"])
            self.assertEqual(settings["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
            self.assertTrue(
                (ROOT / "plugins" / "lane-stack" / ".claude-plugin" / "plugin.json").is_file()
            )

            pm_skill = home / ".agents" / "pm-skills" / "orchestrator-lanes" / "SKILL.md"
            self.assertTrue(pm_skill.is_file())
            self.assertTrue((home / ".agents" / "pm-skills" / "info" / "SKILL.md").is_file())
            self.assertTrue((home / ".agents" / "pm-skills" / "app-architect" / "SKILL.md").is_file())
            self.assertFalse((home / ".agents" / "skills" / "info").exists())
            self.assertFalse((home / ".agents" / "skills" / "app-architect").exists())
            self.assertFalse((home / ".agents" / "skills" / "orchestrator-lanes").exists())
            self.assertFalse((home / ".claude" / "skills" / "orchestrator-lanes").exists())
            self.assertFalse((home / ".claude" / "skills" / "lane-contract").exists())
            self.assertTrue((home / ".agents" / "skills" / "lane-contract" / "SKILL.md").is_file())

    def test_bin_install_ignores_runtime_cache_directories(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            stack = tmp / "stack"
            home = tmp / "home"
            work = tmp / "outside-repo"
            shutil.copytree(
                ROOT,
                stack,
                ignore=shutil.ignore_patterns(
                    ".agents", ".claude-bridge", ".git", "__pycache__", "*.pyc"
                ),
            )
            cache = stack / "bin" / "__pycache__"
            cache.mkdir()
            (cache / "verification_safety.cpython-test.pyc").write_bytes(b"cache")
            (stack / "bin" / "stray.pyc").write_bytes(b"cache")
            hook_cache = stack / "hooks" / "__pycache__"
            hook_cache.mkdir()
            (hook_cache / "guard_shell.cpython-test.pyc").write_bytes(b"cache")
            installed_cache = home / ".agents" / "hooks" / "__pycache__"
            installed_cache.mkdir(parents=True)
            (installed_cache / "stale.pyc").write_bytes(b"cache")
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(stack / "install.sh")],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed_bin = home / ".agents" / "bin"
            self.assertFalse((installed_bin / "__pycache__").exists())
            self.assertFalse((installed_bin / "stray.pyc").exists())
            self.assertFalse((home / ".agents" / "hooks" / "__pycache__").exists())
            self.assertEqual((installed_bin / "lane-ctl").stat().st_mode & 0o777, 0o755)

    def test_install_does_not_chmod_unrelated_existing_bins(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            existing = home / ".agents" / "bin" / "user-managed"
            existing.parent.mkdir(parents=True)
            existing.write_text("#!/bin/sh\n", encoding="utf-8")
            existing.chmod(0o600)
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(existing.stat().st_mode & 0o777, 0o600)

    def test_doctor_apply_requires_explicit_project_option(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            project = tmp / "project"
            home.mkdir()
            project.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=project, check=True)
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            default = subprocess.run(
                [str(INSTALL)],
                cwd=project,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(default.returncode, 0, default.stderr)
            self.assertFalse((project / ".agents" / "routing.profile.yaml").exists())

            explicit = subprocess.run(
                [str(INSTALL), "--apply-project", str(project)],
                cwd=tmp,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertTrue((project / ".agents" / "routing.profile.yaml").is_file())

    def test_install_merges_guard_hook_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            settings = home / ".claude" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(
                json.dumps(
                    {
                        "theme": "dark",
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Task",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "/user/hook",
                                            "timeout": 7,
                                        }
                                    ],
                                },
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "AGENT_HOOK_CLIENT=claude "
                                                "/old/install/guard_shell.py"
                                            ),
                                            "timeout": 2,
                                        },
                                        {
                                            "type": "command",
                                            "command": "/same-entry/hook",
                                            "timeout": 4,
                                        },
                                    ],
                                },
                                {
                                    "matcher": "Edit|Write|MultiEdit",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "/home/test/.claude/hooks/"
                                                "guard-orchestrator-no-direct-edits.sh"
                                            ),
                                            "timeout": 2,
                                        }
                                    ],
                                },
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            for _ in range(2):
                result = subprocess.run(
                    [str(INSTALL)],
                    cwd=work,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            installed = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(installed["theme"], "dark")
            self.assertEqual(installed["env"]["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
            entries = installed["hooks"]["PreToolUse"]
            self.assertIn(
                {
                    "matcher": "Task",
                    "hooks": [
                        {"type": "command", "command": "/user/hook", "timeout": 7}
                    ],
                },
                entries,
            )
            guards = [
                entry
                for entry in entries
                if any(
                    hook.get("command", "").endswith("/guard_shell.py")
                    for hook in entry.get("hooks", [])
                )
            ]
            self.assertEqual(len(guards), 1)
            self.assertEqual(
                guards[0]["matcher"],
                "Bash|Edit|Write|MultiEdit|NotebookEdit",
            )
            self.assertNotIn(
                "guard-orchestrator-no-direct-edits.sh",
                settings.read_text(encoding="utf-8"),
            )
            self.assertIn(
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "/same-entry/hook",
                            "timeout": 4,
                        }
                    ],
                },
                entries,
            )

    def test_install_fails_fast_when_node_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            fake_path = tmp / "bin"
            fake_path.mkdir()
            for command in ("bash", "dirname", "flock", "git", "python3", "rsync"):
                target = shutil.which(command)
                self.assertIsNotNone(target)
                (fake_path / command).symlink_to(target)
            env = os.environ.copy()
            env["PATH"] = str(fake_path)

            result = subprocess.run(
                [str(INSTALL)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required command: node", result.stderr)

    def test_removes_stack_skills_from_claude_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            existing = home / ".claude" / "skills" / "lane-contract"
            existing.mkdir(parents=True)
            work.mkdir()
            (existing / "user-note.txt").write_text("stale catalog copy\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(existing.exists())
            self.assertTrue(
                (home / ".agents" / "skills" / "lane-contract" / "SKILL.md").is_file()
            )
            self.assertFalse(
                (home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack").exists()
            )

    def test_local_marketplace_keeps_checkout_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env["LANE_INSTALL_LOCAL_MARKETPLACE"] = "1"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            marketplace = home / ".claude" / "plugins" / "marketplaces" / "claude-lane-stack"
            self.assertTrue(marketplace.is_symlink())
            self.assertEqual(marketplace.resolve(), ROOT)
            settings = json.loads(
                (home / ".claude" / "settings.json").read_text(encoding="utf-8")
            )
            ours = settings["extraKnownMarketplaces"]["claude-lane-stack"]
            self.assertEqual(ours["source"]["path"], str(ROOT))
            self.assertNotIn("autoUpdate", ours)

    def test_installs_dedicated_codex_night_review_profile(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            home = tmp / "home"
            work = tmp / "outside-repo"
            home.mkdir()
            work.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["LANE_INSTALL_CLAUDE_PLUGIN"] = "0"
            env.pop("CODEX_HOME", None)

            result = subprocess.run(
                [str(INSTALL)],
                cwd=work,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=60,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = home / ".codex" / "night-review.config.toml"
            self.assertTrue(installed.is_file())
            content = installed.read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.6-sol"', content)
            self.assertIn('model_reasoning_effort = "high"', content)
            self.assertIn('sandbox_mode = "read-only"', content)
            self.assertIn('approval_policy = "never"', content)


if __name__ == "__main__":
    unittest.main()

"""Every hook the stack installs for the whole machine says what it does in the owner's own (non-lane) session.

The OpenCode writer guard ran in every OpenCode session and refused skills in a plain one (2026-10-13). A hook added
without an entry here fails this test: decide whether it acts only behind a lane marker (and test that) or is a
deliberate machine-wide feature (and say why).

Lane markers: LANE_PROMPT_FILE / LANE_TASK_FILE (lane-session), LANE_PILOT_ROLE (Lane Pilot non-Claude threads),
LANE_PILOT_AGENT_TYPE (Lane Pilot Claude threads), LANE_STACK_SESSION (lane-pm), LANE_CODEX_WORKER (Codex worker),
a lane-stack agent_type in the hook payload.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LANE = "lane"
MACHINE = "machine"
SCOPE = {
    # Claude Code settings.json (merge_claude_settings.py)
    "guard_shell.py": (MACHINE, "protection from mistakes (rm → agent-trash, force push, SQL wipes); role rules need agent_type or LANE_PILOT_AGENT_TYPE"),
    "pm_bulk_read.py": (LANE, "only when a routing profile enables pm_read"),
    "owner_presence.py": (MACHINE, "records only the time of the owner's own prompts (non-lane sessions) so Lane Pilot keeps its writers off his account; no output"),
    "stall_check.py": (LANE, "LANE_STACK_SESSION/LANE_PILOT_AGENT_TYPE/LANE_PILOT_ROLE/LANE_PROMPT_FILE/LANE_TASK_FILE/LANE_CODEX_WORKER"),
    "lane_statusline_session.py": (MACHINE, "records agent_type only; the lane HUD shows for lane agents"),
    "teammate_idle_sentinel.py": (LANE, "lane-stack/rs-* teammate or LANE_STACK_SESSION/LANE_PILOT_AGENT_TYPE"),
    "pm_stop_sentinel.py": (LANE, "PM agent_type only"),
    "session_ledger.py": (MACHINE, "usage ledger, no output"),
    "lane-statusline": (MACHINE, "falls back to claude-pulse outside lane agents"),
    # lane-stack Claude plugin
    "ensure_subagent_model.py": (MACHINE, "SUBAGENT_MODEL default"),
    "winnow-sidecar": (MACHINE, "starts the winnow sidecar"),
    "skillranker-hook.sh": (MACHINE, "skill suggestions for the main session"),
    "fast-jev": (MACHINE, "/compact without a summary"),
    "winnow": (MACHINE, "trims large tool output"),
    "jev-router": (LANE, "picks model and effort of a subagent a lane session spawns; never the session's own turns"),
    # codex-lane plugin
    "session-start.py": (LANE, "prints only for LANE_CODEX_WORKER"),
    "user-prompt-submit.py": (MACHINE, "skill suggestions, same as skillranker-hook.sh"),
    # OpenCode global plugin
    "opencode-lane": (LANE, "writer guard, notes, hub guard and sticky contract only for a lane-* agent (v2 shared service) or a LANE_* marker (v1); winnow and telemetry for every session"),
}

SCRIPT = re.compile(r"([\w.-]+\.(?:py|sh|cjs|js|ts)|lane-statusline)\b")


def _name(command: str) -> str:
    if "winnow serve" in command:
        return "winnow-sidecar"
    found = SCRIPT.findall(command)
    return found[-1] if found else command


def installed_hooks() -> set[str]:
    names: set[str] = set()
    with tempfile.TemporaryDirectory() as home:
        settings = Path(home) / "settings.json"
        settings.write_text("{}", encoding="utf-8")
        subprocess.run(
            [
                sys.executable, str(ROOT / "hooks" / "merge_claude_settings.py"), str(settings),
                str(ROOT / "hooks" / "guard_shell.py"),
                "--statusline", str(ROOT / "bin" / "lane-statusline"),
                "--session-mark", str(ROOT / "hooks" / "lane_statusline_session.py"),
                "--plugin-root", str(ROOT), "--plugin-local",
            ],
            env={"HOME": home, "PATH": "/usr/bin:/bin"},
            capture_output=True,
            check=True,
        )
        data = json.loads(settings.read_text(encoding="utf-8"))
    for entries in data.get("hooks", {}).values():
        for entry in entries:
            names.update(_name(hook.get("command", "")) for hook in entry.get("hooks", []))
    if data.get("statusLine"):
        names.add(_name(data["statusLine"]["command"]))
    for plugin in ("lane-stack", "codex-lane"):
        hooks = json.loads((ROOT / "plugins" / plugin / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        for entries in hooks.values():
            for entry in entries:
                names.update(_name(hook.get("command", "")) for hook in entry.get("hooks", []))
    mods = (ROOT / "plugins" / "lane-stack" / "hooks" / "lane-mods.ts").read_text(encoding="utf-8")
    names.update(re.findall(r"from '\./([\w-]+)\.js'", mods))
    if (ROOT / "profiles" / "opencode" / "opencode-lane.ts").is_file():
        names.add("opencode-lane")
    return names


class PlainSessionScopeTest(unittest.TestCase):
    def test_every_machine_wide_hook_declares_its_plain_session_scope(self) -> None:
        missing = sorted(installed_hooks() - SCOPE.keys())
        self.assertEqual(missing, [], "add each to SCOPE: lane-gated (with a test) or machine-wide (with a reason)")


if __name__ == "__main__":
    unittest.main()

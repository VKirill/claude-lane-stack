from __future__ import annotations

import datetime
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "bin" / "docs-maintain-project"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _lane_repo(tmp: str, *, enabled: bool, hour: int) -> Path:
    repo = Path(tmp)
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "CLAUDE.md").write_text("# X\n\nClaude Lane Stack\n", encoding="utf-8")
    agents = repo / ".agents"
    agents.mkdir()
    flag = "true" if enabled else "false"
    (agents / "routing.profile.yaml").write_text(
        "pm: claude\n"
        "stages:\n"
        "  docs:\n"
        f"    enabled: {flag}\n"
        "    maintain: true\n"
        "    provider: codex\n"
        "    model: gpt-5.6-luna\n"
        f"    hour: {hour}\n"
        "    page_cap: 1\n"
        "    since: yesterday\n",
        encoding="utf-8",
    )
    app = repo / "apps" / "web"
    (app / "src").mkdir(parents=True)
    (app / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")
    (app / "src" / "index.ts").write_text("export const w = 1\n", encoding="utf-8")
    (app / "CLAUDE.md").write_text("# web\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


def _run(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [str(RUNNER), str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


class DocsMaintainProjectTest(unittest.TestCase):
    def test_disabled_is_skip_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _lane_repo(tmp, enabled=False, hour=5)
            result = _run(repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("SKIP: stages.docs.enabled=false", result.stdout)
            self.assertNotIn("WARN: failed", result.stdout)
            self.assertNotIn("BLOCKED:", result.stdout)

    def test_wrong_hour_is_skip(self) -> None:
        now = datetime.datetime.now().hour
        hour = 5 if now != 5 else 4
        with tempfile.TemporaryDirectory() as tmp:
            repo = _lane_repo(tmp, enabled=True, hour=hour)
            result = _run(repo, env={"DOCS_IF_HOUR": "1"})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("SKIP: stages.docs.hour != now", result.stdout)

    def test_thin_passport_runs_web_and_onboard_dry(self) -> None:
        hour = datetime.datetime.now().hour
        with tempfile.TemporaryDirectory() as tmp:
            repo = _lane_repo(tmp, enabled=True, hour=hour)
            result = _run(repo, "--dry-run")
            out = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, out)
            self.assertNotIn("BLOCKED:", out)
            self.assertIn("ONBOARD: passport incomplete", out)
            self.assertIn("DRY-RUN: project-onboard", out)
            self.assertTrue((repo / "docs" / "INDEX.md").is_file())

    def test_cron_path_finds_codex(self) -> None:
        script = (ROOT / "bin" / "lane-cron-path.sh").read_text(encoding="utf-8")
        self.assertIn(".local/bin", script)
        result = subprocess.run(
            [
                "env",
                "-i",
                f"HOME={os.environ.get('HOME', '/home/ubuntu')}",
                "PATH=/usr/bin:/bin",
                "bash",
                "-c",
                f". {ROOT / 'bin' / 'lane-cron-path.sh'}; command -v codex",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("codex", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIGEST = ROOT / "bin" / "qa-digest"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(DIGEST), *args], text=True, capture_output=True, check=False)


class QaDigestTest(unittest.TestCase):
    def test_cases_target_script_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cases = Path(raw) / "cases.md"
            cases.write_text(
                "# Cases demo\n\n## TC-001 Click\n- Steps: open /\n- Expected: h1\n\n## TC-002 Other\n- Steps: open /b\n",
                encoding="utf-8",
            )
            first = run("cases", str(cases))
            self.assertEqual(first.returncode, 0, first.stderr)
            payload = json.loads(first.stdout)
            self.assertEqual(set(payload["cases"]), {"TC-001", "TC-002"})
            again = json.loads(run("cases", str(cases)).stdout)
            self.assertEqual(payload, again)

            script = Path(raw) / "TC-001.js"
            script.write_text(
                '// case_digest: x\nasync (page) => { await page.goto("BASE_URL"); }\n',
                encoding="utf-8",
            )
            a = run("script", str(script)).stdout.strip()
            b = run("script", str(script)).stdout.strip()
            self.assertEqual(len(a), 64)
            self.assertEqual(a, b)

            t1 = run("target", "local", "http://127.0.0.1:5173/app/").stdout.strip()
            t2 = run("target", "local", "http://127.0.0.1:5173/app").stdout.strip()
            t3 = run("target", "staging", "http://127.0.0.1:5173/app").stdout.strip()
            self.assertEqual(t1, t2)
            self.assertNotEqual(t1, t3)

    def test_trailing_space_changes_case_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "cases.md"
            path.write_text("## TC-001 A\n- Steps: x\n", encoding="utf-8")
            d1 = json.loads(run("cases", str(path)).stdout)["cases"]["TC-001"]
            path.write_text("## TC-001 A\n- Steps: y\n", encoding="utf-8")
            d2 = json.loads(run("cases", str(path)).stdout)["cases"]["TC-001"]
            self.assertNotEqual(d1, d2)

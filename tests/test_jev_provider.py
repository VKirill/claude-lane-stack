from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_provider import (  # noqa: E402
    JEV_PROVIDERS,
    choose_jev_provider,
    jev_timeout,
)
import jev_decisions  # noqa: E402

TS_TABLE = ROOT / "plugins" / "lane-stack" / "fast-jev" / "src" / "provider.ts"
WINNOW_TABLE = (
    ROOT / "plugins" / "lane-stack" / "winnow" / "sidecar" / "src" / "winnow" / "jev_provider.py"
)
OPENLUX_URL = "https://api.openlux.ai/v1/systemone"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
OPENLUX_MODEL = "jev-1.13.0:stable"
TYPESAFE_MODEL = "jev-latest"


class ProviderChoiceTest(unittest.TestCase):
    def test_openlux_key_wins_over_typesafe(self) -> None:
        provider, key = choose_jev_provider({"openlux": "o-key", "typesafe": "t-key"})
        self.assertEqual(provider.id, "openlux")
        self.assertEqual(key, "o-key")

    def test_typesafe_is_used_when_only_its_key_exists(self) -> None:
        provider, key = choose_jev_provider({"openlux": "", "typesafe": "t-key"})
        self.assertEqual(provider.id, "typesafe")
        self.assertEqual(key, "t-key")

    def test_no_key_means_no_jev(self) -> None:
        self.assertIsNone(choose_jev_provider({}))

    def test_forced_typesafe_beats_openlux_key(self) -> None:
        provider, _ = choose_jev_provider({"openlux": "o-key", "typesafe": "t-key"}, "typesafe")
        self.assertEqual(provider.id, "typesafe")

    def test_forced_openlux_without_key_is_none(self) -> None:
        self.assertIsNone(choose_jev_provider({"typesafe": "t-key"}, "openlux"))

    def test_unknown_forced_value_is_ignored(self) -> None:
        provider, _ = choose_jev_provider({"openlux": "o-key"}, "bogus")
        self.assertEqual(provider.id, "openlux")


class ProviderTableTest(unittest.TestCase):
    def test_model_ids_and_urls(self) -> None:
        self.assertEqual(JEV_PROVIDERS["openlux"].url, OPENLUX_URL)
        self.assertEqual(JEV_PROVIDERS["openlux"].model, OPENLUX_MODEL)
        self.assertEqual(JEV_PROVIDERS["typesafe"].url, TYPESAFE_URL)
        self.assertEqual(JEV_PROVIDERS["typesafe"].model, TYPESAFE_MODEL)

    def test_openlux_adds_one_and_a_half_seconds(self) -> None:
        self.assertEqual(jev_timeout(20, JEV_PROVIDERS["openlux"]), 21.5)
        self.assertEqual(jev_timeout(20, JEV_PROVIDERS["typesafe"]), 20)

    def test_typescript_and_winnow_tables_match_python(self) -> None:
        ts = TS_TABLE.read_text(encoding="utf-8")
        winnow = WINNOW_TABLE.read_text(encoding="utf-8")
        expected = [JEV_PROVIDERS["openlux"], JEV_PROVIDERS["typesafe"]]
        self.assertEqual(re.findall(r"url: '([^']+)'", ts), [p.url for p in expected])
        self.assertEqual(re.findall(r"model: '([^']+)'", ts), [p.model for p in expected])
        self.assertEqual(
            re.findall(r"timeoutPadMs: (\d+)", ts),
            [str(int(p.timeout_pad_s * 1000)) for p in expected],
        )
        self.assertEqual(re.findall(r'url="([^"]+)"', winnow), [p.url for p in expected])
        self.assertEqual(re.findall(r'model="([^"]+)"', winnow), [p.model for p in expected])


class NativeCallTest(unittest.TestCase):
    def _call(self, env: dict[str, str]) -> tuple[str, dict, float]:
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *exc: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"answers": {}}).encode()

        def fake_urlopen(req, timeout):  # type: ignore[no-untyped-def]
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode())
            captured["timeout"] = timeout
            return FakeResponse()

        with tempfile.TemporaryDirectory() as raw_home:
            base = {"HOME": raw_home}
            with patch.dict(os.environ, base, clear=False):
                for name in ("OPENLUX_API_KEY", "TYPESAFE_API_KEY", "JEV_API_KEY", "JEV_PROVIDER", "JEV_NATIVE_MODEL", "LANE_JEV", "TYPESAFE_API_KEY_FILE"):
                    os.environ.pop(name, None)
                os.environ.update(env)
                with patch("jev_decisions.urllib.request.urlopen", fake_urlopen):
                    jev_decisions.call_jev({}, {}, timeout=20)
        return str(captured["url"]), captured["body"], float(captured["timeout"])  # type: ignore[index]

    def test_openlux_key_calls_openlux_with_padding(self) -> None:
        url, body, timeout = self._call({"OPENLUX_API_KEY": "o-key", "TYPESAFE_API_KEY": "t-key"})
        self.assertEqual(url, OPENLUX_URL)
        self.assertEqual(body["model"], OPENLUX_MODEL)
        self.assertAlmostEqual(timeout, 21.5)

    def test_typesafe_only_calls_typesafe_unchanged(self) -> None:
        url, body, timeout = self._call({"TYPESAFE_API_KEY": "t-key"})
        self.assertEqual(url, TYPESAFE_URL)
        self.assertEqual(body["model"], TYPESAFE_MODEL)
        self.assertAlmostEqual(timeout, 20)

    def test_forced_typesafe_ignores_openlux_key(self) -> None:
        url, body, _ = self._call(
            {"OPENLUX_API_KEY": "o-key", "TYPESAFE_API_KEY": "t-key", "JEV_PROVIDER": "typesafe"}
        )
        self.assertEqual(url, TYPESAFE_URL)
        self.assertEqual(body["model"], TYPESAFE_MODEL)

    def test_native_model_override_still_wins(self) -> None:
        _, body, _ = self._call({"TYPESAFE_API_KEY": "t-key", "JEV_NATIVE_MODEL": "jev-custom"})
        self.assertEqual(body["model"], "jev-custom")


class WinnowJudgeTest(unittest.TestCase):
    """The winnow judge hands the SDK the OpenLux host (the SDK adds /v1/systemone) and the OpenLux key."""

    def _client_options(self, env: dict[str, str]) -> dict[str, object]:
        import types

        seen: dict[str, object] = {}

        class FakeClient:
            def __init__(self, *, api_key=None, model=None, retry=None, timeout=None, headers=None, base_url=None):  # type: ignore[no-untyped-def]
                seen.update(api_key=api_key, model=model, timeout=timeout, base_url=base_url)

        fake = types.ModuleType("typesafe_sdk")
        fake.TypeSafeClient = FakeClient  # type: ignore[attr-defined]
        fake.RetryPolicy = lambda **kw: kw  # type: ignore[attr-defined]
        sidecar = str(ROOT / "plugins" / "lane-stack" / "winnow" / "sidecar" / "src")
        with tempfile.TemporaryDirectory() as raw_home:
            with patch.dict(os.environ, {"HOME": raw_home}, clear=False), patch.dict(sys.modules, {"typesafe_sdk": fake}):
                for name in ("OPENLUX_API_KEY", "TYPESAFE_API_KEY", "JEV_API_KEY", "JEV_PROVIDER", "WINNOW_MODEL"):
                    os.environ.pop(name, None)
                os.environ.update(env)
                sys.path.insert(0, sidecar)
                try:
                    from winnow.config import Config
                    from winnow.judge import build_judge

                    build_judge(Config.from_env())
                finally:
                    sys.path.remove(sidecar)
        return seen

    def test_openlux_gets_host_key_and_model(self) -> None:
        seen = self._client_options({"OPENLUX_API_KEY": "o-key", "TYPESAFE_API_KEY": "t-key"})
        self.assertEqual(seen["base_url"], "https://api.openlux.ai")
        self.assertEqual(seen["api_key"], "o-key")
        self.assertEqual(seen["model"], OPENLUX_MODEL)
        self.assertAlmostEqual(float(seen["timeout"]), 16.5)  # type: ignore[arg-type]

    def test_typesafe_keeps_sdk_defaults(self) -> None:
        seen = self._client_options({"TYPESAFE_API_KEY": "t-key"})
        self.assertIsNone(seen["base_url"])
        self.assertIsNone(seen["api_key"])
        self.assertEqual(seen["model"], TYPESAFE_MODEL)


class NoHardcodedEndpointTest(unittest.TestCase):
    """Only the provider tables may name the System One endpoints or Jev model ids."""

    ALLOWED = {TS_TABLE.resolve(), WINNOW_TABLE.resolve(), (ROOT / "bin" / "jev_provider.py").resolve()}
    NEEDLES = ("api.openlux.ai", "api.typesafe.ai/v1/systemone", OPENLUX_MODEL, "'jev-latest'", '"jev-latest"')

    def test_no_other_source_names_the_endpoints(self) -> None:
        offenders: list[str] = []
        for folder in ("bin", "hooks", "profiles", "plugins"):
            for path in (ROOT / folder).rglob("*"):
                if not path.is_file() or path.suffix in {".md", ".lock", ".json", ".toml", ".pyc"}:
                    continue
                if any(part in {"tests", "node_modules", ".gitnexus", "__pycache__"} for part in path.parts):
                    continue
                if path.resolve() in self.ALLOWED:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if any(needle in text for needle in self.NEEDLES):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

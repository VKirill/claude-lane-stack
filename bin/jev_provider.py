#!/usr/bin/env python3
"""The one Python table of System One endpoints, and the key lookup behind it.

Keep the table in step with plugins/lane-stack/fast-jev/src/provider.ts;
tests/test_jev_provider.py compares the two.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class JevProvider:
    id: str
    url: str
    model: str
    key_name: str
    # Fixed headroom added to every timeout on this provider, in seconds.
    timeout_pad_s: float


JEV_PROVIDERS: dict[str, JevProvider] = {
    "openlux": JevProvider(
        id="openlux",
        url="https://api.openlux.ai/v1/systemone",
        model="jev-1.13.0:stable",
        key_name="OPENLUX_API_KEY",
        timeout_pad_s=1.5,
    ),
    "typesafe": JevProvider(
        id="typesafe",
        url="https://api.typesafe.ai/v1/systemone",
        model="jev-latest",
        key_name="TYPESAFE_API_KEY",
        timeout_pad_s=0.0,
    ),
}


def choose_jev_provider(
    keys: Mapping[str, str], forced: str | None = None
) -> tuple[JevProvider, str] | None:
    """Picks the provider and its key; mirrors chooseJevProvider in provider.ts.

    ``forced`` (JEV_PROVIDER) selects one and returns None when that provider
    has no key. Otherwise OpenLux wins when its key exists, then TypeSafe.
    """
    wanted = (forced or "").strip().lower()
    if wanted in JEV_PROVIDERS:
        key = (keys.get(wanted) or "").strip()
        return (JEV_PROVIDERS[wanted], key) if key else None
    for name in ("openlux", "typesafe"):
        key = (keys.get(name) or "").strip()
        if key:
            return JEV_PROVIDERS[name], key
    return None


def jev_timeout(base_s: float, provider: JevProvider) -> float:
    return base_s + provider.timeout_pad_s


def _key_from_env_file(path: Path, names: tuple[str, ...]) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        if key.strip() in names:
            return value.strip().strip('"').strip("'")
    return ""


def openlux_key() -> str:
    env = (os.environ.get("OPENLUX_API_KEY") or "").strip()
    if env:
        return env
    return _key_from_env_file(Path.home() / "secrets" / "openlux.env", ("OPENLUX_API_KEY",))


def typesafe_key() -> str:
    env = (os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY") or "").strip()
    if env:
        return env
    raw = os.environ.get("TYPESAFE_API_KEY_FILE")
    if raw:
        path = Path(raw).expanduser()
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8").strip()
            except OSError:
                return ""
    secrets = Path.home() / "secrets"
    for name in ("typesafe.env", "jev.env"):
        found = _key_from_env_file(secrets / name, ("TYPESAFE_API_KEY", "JEV_API_KEY"))
        if found:
            return found
    return ""

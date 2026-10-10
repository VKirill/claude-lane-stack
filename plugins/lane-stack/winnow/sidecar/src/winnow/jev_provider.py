"""System One endpoints for the winnow judge.

The sidecar is its own package, so it carries a mirror of the table in
bin/jev_provider.py; tests/test_jev_provider.py keeps the mirrors equal.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    """Same rule as bin/jev_provider.py: forced wins, else OpenLux, else TypeSafe."""
    wanted = (forced or "").strip().lower()
    if wanted in JEV_PROVIDERS:
        key = (keys.get(wanted) or "").strip()
        return (JEV_PROVIDERS[wanted], key) if key else None
    for name in ("openlux", "typesafe"):
        key = (keys.get(name) or "").strip()
        if key:
            return JEV_PROVIDERS[name], key
    return None

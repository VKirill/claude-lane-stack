"""Cross-platform sandbox backend selection and Seatbelt (macOS) policy build.

Writer lanes must always run behind an OS-enforced filesystem sandbox that
protects the `.agents` control plane from a compromised or misbehaving
provider CLI. Two backends implement that contract:

- ``bubblewrap``: Linux, via the external ``bwrap`` binary (mount namespace
  isolation). This is the original, still-default-on-Linux backend; its
  argv construction lives in bin/lane-session and must stay byte-for-byte
  identical to the pre-macOS-support behaviour.
- ``seatbelt``: macOS, via ``/usr/bin/sandbox-exec -f <profile-file>``
  running a generated SBPL (Sandbox Profile Language) policy file.

There is intentionally no "unsandboxed" backend. Callers must fail closed
(raise) when the platform's backend binary is missing or non-operational,
exactly like the historical bwrap-required behaviour.

Selection is controlled by the ``LANE_SANDBOX_BACKEND`` environment variable
(``bubblewrap`` | ``seatbelt`` | ``auto``/unset). ``auto`` picks a backend
from ``sys.platform``: ``darwin`` -> seatbelt, everything else -> bubblewrap.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping

KNOWN_BACKENDS = ("bubblewrap", "seatbelt")

# Per-backend runtime.json / session-record sandbox profile identifiers.
# These are recorded so a session can be safely rotated if the effective
# sandbox backend changes between two invocations that share a run dir
# (e.g. a run directory copied between a Linux CI host and a macOS laptop).
RUNTIME_SANDBOX_PROFILES: dict[str, str] = {
    "bubblewrap": "bubblewrap-workspace",
    "seatbelt": "seatbelt-workspace",
}
KNOWN_RUNTIME_SANDBOX_PROFILES = frozenset(RUNTIME_SANDBOX_PROFILES.values())

SEATBELT_BINARY_PATH = "/usr/bin/sandbox-exec"
# Minimal profile used purely to probe whether sandbox-exec is operational.
SEATBELT_PROBE_PROFILE = "(version 1)(allow default)(deny file-write*)"

# Always-writable system roots required by writer CLIs on macOS, regardless
# of provider: scratch space (/tmp, its resolved form /private/tmp, and the
# per-user TMPDIR root under /private/var/folders) plus /dev for tty/null
# device nodes. These mirror the bwrap branch's `--tmpfs /tmp`, `--dev /dev`.
SYSTEM_WRITABLE_ROOTS: tuple[Path, ...] = (
    Path("/tmp"),
    Path("/private/tmp"),
    Path("/private/var/folders"),
    Path("/dev"),
)


def select_backend(
    *, env: Mapping[str, str] | None = None, platform: str | None = None
) -> str:
    """Return the active sandbox backend name.

    ``env`` and ``platform`` are injectable for unit testing; production
    callers pass no arguments and get ``os.environ`` / ``sys.platform``.
    """
    active_env = os.environ if env is None else env
    active_platform = sys.platform if platform is None else platform
    override = str(active_env.get("LANE_SANDBOX_BACKEND") or "").strip().lower()
    if override in ("", "auto"):
        return "seatbelt" if active_platform == "darwin" else "bubblewrap"
    if override not in KNOWN_BACKENDS:
        raise RuntimeError(
            "invalid LANE_SANDBOX_BACKEND="
            f"{override!r}; expected one of "
            f"{', '.join(('auto', *KNOWN_BACKENDS))}"
        )
    return override


def runtime_sandbox_profile(backend: str) -> str:
    try:
        return RUNTIME_SANDBOX_PROFILES[backend]
    except KeyError as exc:
        raise RuntimeError(f"unknown sandbox backend: {backend!r}") from exc


def seatbelt_binary() -> str | None:
    """Locate sandbox-exec: fixed system path first, then PATH lookup."""
    fixed = Path(SEATBELT_BINARY_PATH)
    try:
        if fixed.is_file() and os.access(fixed, os.X_OK):
            return str(fixed)
    except OSError:
        pass
    return shutil.which("sandbox-exec")


def seatbelt_operational(binary: str | None) -> bool:
    """Probe sandbox-exec with a minimal deny-write profile against /usr/bin/true."""
    if not binary:
        return False
    probe_target = shutil.which("true") or "/usr/bin/true"
    try:
        result = subprocess.run(
            [binary, "-p", SEATBELT_PROBE_PROFILE, probe_target],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _quote(path: Path) -> str:
    """Escape backslashes and double quotes for an SBPL string literal."""
    text = str(path)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _path_rule(path: Path) -> str:
    """`(subpath ...)` for directories, `(literal ...)` for files."""
    kind = "subpath" if path.is_dir() else "literal"
    return f"({kind} {_quote(path)})"


def _resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def build_seatbelt_profile(
    *,
    cwd: Path,
    control_root: Path,
    writable_paths: Iterable[Path],
    hidden_paths: Iterable[Path],
    provider_state_dir: Path | None = None,
    readable_overrides: Iterable[Path] = (),
) -> str:
    """Build an SBPL policy implementing the same writer-lane contract as bwrap.

    Rule ordering matters: later rules win for the same operation. Layout:
      1. ``(allow default)`` — baseline, everything allowed (same posture as
         bwrap's ``--ro-bind / /``: the whole filesystem is visible).
      2. ``(deny file-write*)`` — baseline, nothing writable.
      3. ``(allow file-write* (subpath ...))`` for cwd, the provider state
         dir, provider-specific writable home dirs, and always-writable
         system roots (/tmp, /private/tmp, /private/var/folders, /dev).
      4. ``(deny file-write* (subpath control_root))`` — re-lock the
         `.agents` control plane even though it may be nested under one of
         the writable roots above (mirrors bwrap's ro-bind-after-bind).
      5. ``(deny file-read*)`` + ``(deny file-write*)`` for each hidden path
         (other providers' state dirs, host ~/.codex, a configured
         CODEX_HOME) — skipped for a path equal to provider_state_dir.
      6. ``(allow file-read*)`` for each entry in ``readable_overrides`` —
         re-opens read/exec access to a specific file that would otherwise
         fall under one of the hidden-path denies above. Bubblewrap handles
         the equivalent case (a provider binary that physically lives under
         a hidden host state dir, e.g. Codex installed under ~/.codex) by
         re-binding the real binary at a fresh path (/opt/claude-lane-codex);
         seatbelt keeps the binary at its original path and instead carves
         out an explicit read allowance, since rule 6 is applied last.

    All paths are resolved (`Path.resolve()`) before being written into the
    profile, since e.g. macOS `/tmp` is a symlink to `/private/tmp`.
    """
    resolved_control = _resolve(control_root)
    resolved_provider_state_dir = (
        _resolve(provider_state_dir) if provider_state_dir is not None else None
    )

    lines = [
        "(version 1)",
        "(allow default)",
        "(deny file-write*)",
    ]

    seen_write: set[Path] = set()
    for candidate in (*writable_paths, *SYSTEM_WRITABLE_ROOTS):
        if candidate is None:
            continue
        resolved = _resolve(candidate)
        if resolved in seen_write:
            continue
        seen_write.add(resolved)
        if not resolved.exists():
            continue
        lines.append(f"(allow file-write* {_path_rule(resolved)})")

    lines.append(f"(deny file-write* {_path_rule(resolved_control)})")

    seen_hidden: set[Path] = set()
    for hidden in hidden_paths:
        if hidden is None:
            continue
        resolved_hidden = _resolve(hidden)
        if resolved_hidden in seen_hidden:
            continue
        seen_hidden.add(resolved_hidden)
        if (
            resolved_provider_state_dir is not None
            and resolved_hidden == resolved_provider_state_dir
        ):
            continue
        if not resolved_hidden.exists():
            continue
        rule = _path_rule(resolved_hidden)
        lines.append(f"(deny file-read* {rule})")
        lines.append(f"(deny file-write* {rule})")

    seen_override: set[Path] = set()
    for override in readable_overrides:
        if override is None:
            continue
        resolved_override = _resolve(override)
        if resolved_override in seen_override:
            continue
        seen_override.add(resolved_override)
        if not resolved_override.exists():
            continue
        lines.append(f"(allow file-read* {_path_rule(resolved_override)})")

    lines.append("")
    return "\n".join(lines)

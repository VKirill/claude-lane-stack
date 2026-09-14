#!/usr/bin/env python3
"""Shared path-canonicalization helpers.

On macOS the system temp dir (and other paths) can live under a symlink,
e.g. ``/var/folders/...`` -> ``/private/var/folders/...``. Comparing a path
captured before resolving symlinks (a caller-supplied string, a value read
back from a receipt) against one captured after (``Path.resolve()``,
``os.path.realpath``, ``git rev-parse --show-toplevel``, ``pwd -P``) fails
spuriously unless both sides are canonicalized first.

Use these helpers instead of ad hoc ``==`` on raw path strings whenever the
two sides may have travelled through different resolution paths. This does
not change what gets persisted in receipts/state — only how paths are
compared.
"""
from __future__ import annotations

import os
from pathlib import Path


def canonical_path(value: str | Path) -> Path:
    """Resolve symlinks the same way ``pwd -P``/``realpath`` would.

    Works even when ``value`` does not (yet) exist: missing trailing
    components are normalized but not required to be real.
    """
    return Path(os.path.realpath(str(value)))


def same_path(a: str | Path, b: str | Path) -> bool:
    """True if two path strings/Paths refer to the same filesystem location."""
    return canonical_path(a) == canonical_path(b)

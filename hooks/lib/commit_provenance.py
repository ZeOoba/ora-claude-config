"""Shared helpers for the commit-provenance guard pair.

commit-provenance-recorder.py (PostToolUse) and commit-provenance-guard.py
(PreToolUse/Bash) MUST agree byte-for-byte on the touched-file path format and
storage location, or every comparison silently misses and the guard becomes a
no-op that still reports success. Centralising norm() + the path convention
here makes that agreement structural rather than a copy-paste invariant. Full
rationale: docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

Stdlib only. ASCII-only. Windows (`python`).
"""

import os

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"
DEFAULT_TTL_H = 6.0  # matches fleet-session-hook.py's SESSION_PRUNE_H = 6
TOUCHED_BASENAME = "touched-files.txt"


def sessions_dir():
    return os.environ.get("COMMIT_PROVENANCE_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def ttl_h():
    try:
        return float(os.environ.get("COMMIT_PROVENANCE_TTL_H") or DEFAULT_TTL_H)
    except Exception:
        return DEFAULT_TTL_H


def norm(path):
    """The canonical on-disk form. BOTH hooks import and use this identically."""
    return os.path.normcase(os.path.abspath(path))

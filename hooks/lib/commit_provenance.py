"""Shared helpers for the commit-provenance guard pair.

commit-provenance-recorder.py (PostToolUse) and commit-provenance-guard.py
(PreToolUse/Bash) MUST agree byte-for-byte on the touched-file path format and
storage location, or every comparison silently misses and the guard becomes a
no-op that still reports success. Centralising norm() + the path convention
here makes that agreement structural rather than a copy-paste invariant. Full
rationale: docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

Line format (2026-07-17, was bare-path): `<norm(path)>\t<epoch-seconds>\n`.
The guard uses the per-path timestamp to check whether the path has already
been committed since this session touched it (see the recency-heuristic fix
in commit-provenance-guard.py's foreign_hits()) instead of relying purely on
the whole-touched-set-file's mtime + a TTL window, which false-positived on
already-committed content 3 times in one session on 2026-07-17. A line with
no tab (pre-2026-07-17 format, or hand-edited) has no known touch time;
read_touched() maps it to None, and the guard treats "unknown timestamp" as
"just touched" -- its existing, more conservative behaviour -- rather than
assuming it is safe.

Stdlib only. ASCII-only. Windows (`python`).
"""

import os
import time

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


def touch_line(path, when=None):
    """The recorder's append-line for `path`, touched at `when` (default now)."""
    ts = when if when is not None else time.time()
    return "%s\t%.6f\n" % (norm(path), ts)


def read_touched(fh):
    """Parse an open touched-files.txt handle into {norm_path: last_touch_ts}.

    A path touched more than once keeps its LATEST known timestamp
    (append-only log, duplicates expected) -- UNLESS any occurrence of that
    path has no tab (old format, or a hand-written bare path), in which case
    the whole path maps to None: "touch time unknown, somewhere in this
    path's history" is exactly the case callers must treat as the
    conservative default (equivalent to "just touched"), never as "safe",
    since a later unknown-time touch could have happened after any known one.
    """
    per_path = {}
    for raw in fh:
        line = raw.strip()
        if not line:
            continue
        if "\t" in line:
            path, _, ts_str = line.partition("\t")
            try:
                ts = float(ts_str)
            except ValueError:
                ts = None
        else:
            path, ts = line, None
        per_path.setdefault(path, []).append(ts)
    out = {}
    for path, timestamps in per_path.items():
        out[path] = None if any(t is None for t in timestamps) else max(timestamps)
    return out

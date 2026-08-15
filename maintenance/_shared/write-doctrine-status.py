#!/usr/bin/env python3
"""Layer-2 durable status-file writer for the doctrine/governor drift notification chain.

WHY (audit Phase 3, 2026-07-08): the triple-redundant drift-notification design needs a
DURABLE, human-readable trace of the last doctrine/governor health check that survives
the ephemeral console output of a pre-push gate run. This module writes that snapshot.

Layers of the chain:
  1. the pre-push gate block itself (in-band; hooks/git-prepush-doctrine-gate.py),
  2. THIS local status file (last-known-state snapshot),
  3. a Notion Ops Hub row (a separate scheduled task -- not this module),
  with email best-effort only.

CURRENT-STATE ONLY. This file is OVERWRITTEN every run -- it answers "what did the last
check find?", NOT "what has ever happened" (that append-only history is memory/event_log.md).
Mirrors the snapshot discipline already used by maintenance/_state/registry-membership.json.

USABLE BY MULTIPLE CALLERS by design:
  - the git pre-push doctrine gate runs ONLY the doctrine probe -> passes governor_* = None,
  - ora-cc-schematic-refresh (2x/week) runs all three probes -> passes governor_rc/_summary
    and memory_rc/_summary too (added 2026-08-13, closing the gap where governor-drift-probe.py
    and memory-integrity-probe.py had no durable log of their own -- their results previously
    survived only inside the System Schematic artifact's prose, unlike the doctrine probe).

Pure stdlib. No package install. Import by path (this file is hyphenated, so importlib
util.spec_from_file_location -- the idiom already used in maintenance/_tests/test_hardening.py).
Running this file directly prints a demo snapshot to stdout WITHOUT writing any file.
"""
import json
import os
import sys
import tempfile
from datetime import datetime

# Robust to the caller's cwd: this module lives at maintenance/_shared/, the snapshot
# lives at maintenance/_state/ alongside registry-membership.json.
_MAINT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STATUS_PATH = os.path.join(_MAINT_DIR, "_state", "doctrine-status.json")


def build_snapshot(source, doctrine_rc, doctrine_summary,
                   governor_rc=None, governor_summary=None, guard_orphans=None,
                   memory_rc=None, memory_summary=None, now=None):
    """The pure, in-memory snapshot dict. Separated from the write so it is trivially
    testable and so the (in-memory) build can never be the thing that raises during a
    best-effort write. `now` is injectable for deterministic tests."""
    now = now or datetime.now()
    return {
        "last_check": now.isoformat(),
        "source": source,
        "doctrine_probe": {"exit_code": doctrine_rc, "summary": doctrine_summary},
        "governor_probe": {"exit_code": governor_rc, "summary": governor_summary},
        # memory-integrity-probe.py result -- same optional/None-when-not-run shape as
        # governor_probe above. Added 2026-08-13.
        "memory_probe": {"exit_code": memory_rc, "summary": memory_summary},
        # None/empty -> [] ; any iterable of WARN strings passes through unchanged.
        "guard_orphans": list(guard_orphans) if guard_orphans else [],
    }


def write_status(source, doctrine_rc, doctrine_summary,
                 governor_rc=None, governor_summary=None, guard_orphans=None,
                 memory_rc=None, memory_summary=None, path=None):
    """Atomically write the current doctrine/governor/memory health snapshot to
    maintenance/_state/doctrine-status.json (or `path` for tests). OVERWRITES.

    source            "pre-push" | "scheduled".
    doctrine_rc       doctrine-integrity-probe.py exit code (int).
    doctrine_summary  short string ("clean", a [MISSING]/[WARN] line, or a count).
    governor_rc /     governor-drift-probe.py exit code + summary; None when the caller
      governor_summary  did not run the governor probe this invocation (the pre-push gate).
    memory_rc /       memory-integrity-probe.py exit code + summary; None when the caller
      memory_summary    did not run the memory probe this invocation (the pre-push gate).
    guard_orphans     optional list of guard-liveness WARN strings; None/empty -> [].
    path              target override (tests); None -> DEFAULT_STATUS_PATH.

    Writes atomically: a uniquely-named temp file in the SAME directory then os.replace()
    over the target, so a reader never observes a partial write (same atomic-replace idiom
    as maintenance/append-event-log.py / registry-membership-probe.py, minus their
    append/collision complexity -- this is a plain overwrite).

    BEST-EFFORT: any failure is caught, logged to stderr, and swallowed. A status-file
    write must NEVER make the caller (the pre-push gate) block a push or fail a scheduled
    task. Returns True on success, False on any failure -- callers MAY check but need not.
    """
    target = path or DEFAULT_STATUS_PATH
    try:
        snapshot = build_snapshot(source, doctrine_rc, doctrine_summary,
                                  governor_rc, governor_summary, guard_orphans,
                                  memory_rc, memory_summary)
        # Temp file MUST be on the same volume/dir as the target for os.replace to be
        # atomic. If target's dir does not exist, mkstemp raises -> caught below (best-effort).
        target_dir = os.path.dirname(os.path.abspath(target))
        fd, tmp = tempfile.mkstemp(dir=target_dir, prefix=".doctrine-status-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
                f.write("\n")  # trailing newline so a human `cat` reads cleanly
            os.replace(tmp, target)  # atomic on the same volume
        except Exception:
            # Replace never happened -> the temp file is orphaned; remove it.
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        return True
    except Exception as e:
        sys.stderr.write(
            "write-doctrine-status: could not write status file %r (%s) - "
            "continuing (best-effort, non-fatal).\n" % (target, e))
        return False


if __name__ == "__main__":
    # Manual eyeball only -- prints the shape to stdout, writes NOTHING (never clobbers
    # the real operational snapshot).
    demo = build_snapshot("pre-push", 0, "clean")
    print("DEMO snapshot (not written to disk):")
    print(json.dumps(demo, indent=2))
    print("\nDefault target when write_status() is called for real:")
    print("  " + DEFAULT_STATUS_PATH)

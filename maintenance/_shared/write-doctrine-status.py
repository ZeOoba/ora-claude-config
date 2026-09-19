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

CURRENT STATE ON TOP + A BOUNDED HISTORY. The top-level fields are OVERWRITTEN every run --
they answer "what did the last check find?". Since 2026-09-06 the file also carries a
`history` array (newest first, capped at HISTORY_MAX compact records, one per write) so a
monthly reader can count doctrine/governor/memory pass/fail over a window without the
narrative event_log.md. Why: ora-consolidate-memory-monthly's Phase-3 audit line found on
2026-09-02 that a latest-only snapshot cannot yield a month-level count at all. The file is
still not a log -- HISTORY_MAX bounds it, and the long-form record stays in memory/event_log.md.
Mirrors the snapshot discipline already used by maintenance/_state/registry-membership.json.

Readers that pin the top-level key set (maintenance/_tests/test_git_prepush_doctrine_gate.py
EXPECTED_KEYS) must list `history` -- that set compares with == by design.

Read-only CLI (never writes): `python write-doctrine-status.py --summary [--since-days N]
[--path FILE]` prints per-probe ran/pass/fail counts over the window as JSON.

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
from datetime import datetime, timedelta

# Robust to the caller's cwd: this module lives at maintenance/_shared/, the snapshot
# lives at maintenance/_state/ alongside registry-membership.json.
_MAINT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STATUS_PATH = os.path.join(_MAINT_DIR, "_state", "doctrine-status.json")

# Bound on the `history` array. Writers: every push (pre-push gate) + ora-cc-schematic-refresh
# 2x/week. 120 records covers a busy month several times over while keeping the file small
# (~150 B/record). Raise deliberately, never remove -- an unbounded list is the class of
# defect Automation Audit Rev 22 closed elsewhere (2026-09-06, "3 unbounded logs bounded").
HISTORY_MAX = 120
_SUMMARY_MAX_CHARS = 200  # per-record summary truncation; the full line is in the top-level snapshot


def _history_record(snapshot):
    """Compact, flat record of one check for the `history` array. Pure. Tolerates a legacy
    (pre-history) file shape so the existing top-level snapshot can be seeded as record #1."""
    def _rc(name):
        p = snapshot.get(name) or {}
        return p.get("exit_code")

    def _summary(name):
        p = snapshot.get(name) or {}
        s = p.get("summary")
        if isinstance(s, str) and len(s) > _SUMMARY_MAX_CHARS:
            return s[:_SUMMARY_MAX_CHARS - 3] + "..."
        return s

    return {
        "last_check": snapshot.get("last_check"),
        "source": snapshot.get("source"),
        "doctrine_rc": _rc("doctrine_probe"),
        "governor_rc": _rc("governor_probe"),
        "memory_rc": _rc("memory_probe"),
        "doctrine_summary": _summary("doctrine_probe"),
        "governor_summary": _summary("governor_probe"),
        "memory_summary": _summary("memory_probe"),
        "guard_orphan_count": len(snapshot.get("guard_orphans") or []),
    }


def _load_prior_history(target):
    """Read the existing status file and return its `history` list (newest first).
    A legacy file with no `history` key seeds the list from its own top-level snapshot so
    the last pre-upgrade result is not lost. Any failure (missing file, bad JSON, wrong
    shape) -> [] -- history is best-effort and must never break the write."""
    try:
        with open(target, encoding="utf-8") as f:
            prior = json.load(f)
        if not isinstance(prior, dict):
            return []
        hist = prior.get("history")
        if isinstance(hist, list):
            return [h for h in hist if isinstance(h, dict)]
        if prior.get("last_check"):
            return [_history_record(prior)]
        return []
    except Exception:
        return []


def merge_history(snapshot, prior_history, max_records=HISTORY_MAX):
    """Pure: return `snapshot` with `history` = [this check] + prior (newest first),
    capped at max_records. Does not mutate its inputs."""
    out = dict(snapshot)
    out["history"] = ([_history_record(snapshot)] + list(prior_history or []))[:max_records]
    return out


def summarize_history(data, since_days=30, now=None):
    """Pure: per-probe ran/pass/fail counts over the trailing window, from a loaded status
    dict. A probe 'ran' when its rc is not None; pass == rc 0; fail == any other int.
    Records with an unparseable last_check are counted under `unparsed` and skipped.
    Also returns the failing records' (last_check, source, summary) for the audit line."""
    now = now or datetime.now()
    cutoff = now - timedelta(days=since_days)
    hist = data.get("history") if isinstance(data, dict) else None
    if not isinstance(hist, list) or not hist:
        # Legacy shape: treat the top-level snapshot as the only record.
        hist = [_history_record(data)] if isinstance(data, dict) and data.get("last_check") else []
    counts = {p: {"ran": 0, "pass": 0, "fail": 0} for p in ("doctrine", "governor", "memory")}
    fails, unparsed, in_window = [], 0, 0
    for rec in hist:
        try:
            ts = datetime.fromisoformat(str(rec.get("last_check")))
        except Exception:
            unparsed += 1
            continue
        if ts < cutoff:
            continue
        in_window += 1
        for p in counts:
            rc = rec.get(p + "_rc")
            if rc is None:
                continue
            counts[p]["ran"] += 1
            if rc == 0:
                counts[p]["pass"] += 1
            else:
                counts[p]["fail"] += 1
                fails.append({"probe": p, "last_check": rec.get("last_check"),
                              "source": rec.get("source"), "summary": rec.get(p + "_summary")})
    return {
        "window_days": since_days,
        "since": cutoff.isoformat(),
        "checks_in_window": in_window,
        "records_total": len(hist),
        "unparsed": unparsed,
        "probes": counts,
        "fails": fails,
    }


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
        # Carry the bounded history forward (newest first). Reading the prior file is
        # best-effort inside _load_prior_history; a missing/corrupt prior -> fresh list.
        snapshot = merge_history(snapshot, _load_prior_history(target))
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


def _cli(argv):
    """`--summary` = read-only window summary of the status file (for the monthly audit
    line). No args = the original demo (prints a snapshot shape, writes nothing)."""
    import argparse
    ap = argparse.ArgumentParser(description="doctrine-status.json writer (library) / read-only summary CLI")
    ap.add_argument("--summary", action="store_true",
                    help="print per-probe ran/pass/fail counts over the window as JSON (reads only)")
    ap.add_argument("--since-days", type=int, default=30, help="window length in days (default 30)")
    ap.add_argument("--path", default=None, help="status file to read (default: canonical)")
    args = ap.parse_args(argv)
    if not args.summary:
        demo = merge_history(build_snapshot("pre-push", 0, "clean"), [])
        print("DEMO snapshot (not written to disk):")
        print(json.dumps(demo, indent=2, ensure_ascii=False))
        print("\nDefault target when write_status() is called for real:")
        print("  " + DEFAULT_STATUS_PATH)
        return 0
    target = args.path or DEFAULT_STATUS_PATH
    try:
        with open(target, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"error": "cannot read %s: %s" % (target, e)}))
        return 2
    print(json.dumps(summarize_history(data, since_days=args.since_days), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))

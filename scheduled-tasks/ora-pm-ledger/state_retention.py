#!/usr/bin/env python3
"""
state_retention.py -- ora-pm-ledger state/ directory retention.

WHY THIS EXISTS (2026-08-28, workflow-optimization follow-up to ORA Automation
Audit Revision 19)
  Each of the five snapshot-diff engines in this folder (acquisition_pipeline_,
  capex_, deal_sourcing_, property_register_, tenant_db_snapshot_diff.py)
  writes a dated JSON archive into state/ on every run, plus a `-latest.json`
  pointer it actually reads back. None of the five ever prunes its own dated
  archives -- by design, per each script's own docstring, they are small,
  independent, self-contained engines and deliberately share no code (a
  shared library "would touch a working, reviewed production script for a
  refactor nobody asked for"). Retention is the same kind of concern as
  event_log.md's rollover (memory/rollover-event-log.py) or MEMORY.md's size
  gate: a housekeeping pass that stands OUTSIDE the producers, not a change to
  any of them. Root finding: state/ reached 31MB / 74 files with no retention
  at all (Automation Audit Rev 19, 2026-08-28), the oldest snapshot dating back
  to 2026-07-20 (tenant-db) though the diff engines only ever compare today
  against `-latest.json` -- every dated file past that one comparison exists
  purely as an audit trail, not a live dependency.

WHAT IT DOES
  Scans state/ for files matching `<category>-YYYY-MM-DD.json`, groups by
  category, and for each category MOVES (never deletes -- CLAUDE.md invariant
  6) every dated snapshot older than --keep-days (default 14) into
  state/_archive/<category>/, preserving the original filename. `-latest.json`
  pointer files and any non-dated file (e.g. outbox-qc-coverage.json) are
  never touched -- only files matching the dated pattern are in scope.

USAGE
  python state_retention.py                  # keep 14 days live, archive older
  python state_retention.py --dry-run         # show what would move, change nothing
  python state_retention.py --keep-days 30
  python state_retention.py --selftest        # synthetic dir, no real state touched

This is a STRUCTURAL edit under the same class of shared-checkout risk as
rollover-event-log.py -- check for other active sessions on this path before
running it live (claim_work.py, paths: scheduled-tasks/ora-pm-ledger/state/).
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import tempfile

SNAPSHOT_RE = re.compile(r"^(?P<category>.+)-(?P<date>\d{4}-\d{2}-\d{2})\.json$")


def plan(state_dir, keep_days, today=None):
    """Return {category: [(filename, date_str), ...]} of files to archive --
    every dated snapshot for that category older than the most recent
    --keep-days worth, computed against `today` (injected for tests)."""
    if today is None:
        today = datetime.date.today()

    by_category = {}
    for fname in os.listdir(state_dir):
        if not os.path.isfile(os.path.join(state_dir, fname)):
            continue
        m = SNAPSHOT_RE.match(fname)
        if not m:
            continue
        by_category.setdefault(m.group("category"), []).append(
            (fname, m.group("date")))

    to_archive = {}
    for category, entries in by_category.items():
        cutoff = today - datetime.timedelta(days=keep_days)
        stale = [
            (fname, date_str) for fname, date_str in entries
            if datetime.date.fromisoformat(date_str) < cutoff
        ]
        if stale:
            to_archive[category] = sorted(stale, key=lambda e: e[1])
    return to_archive


def apply_plan(state_dir, to_archive):
    """Move planned files into state/_archive/<category>/. Returns the number
    of files moved. Refuses (raises FileExistsError) rather than overwrite an
    existing archived copy -- a second run against an already-archived date
    is a no-op for that file, not a silent clobber."""
    archive_root = os.path.join(state_dir, "_archive")
    moved = 0
    for category, entries in to_archive.items():
        dest_dir = os.path.join(archive_root, category)
        os.makedirs(dest_dir, exist_ok=True)
        for fname, _date_str in entries:
            src = os.path.join(state_dir, fname)
            dst = os.path.join(dest_dir, fname)
            if os.path.exists(dst):
                raise FileExistsError(
                    "refusing to overwrite existing archive copy: %s" % dst)
            shutil.move(src, dst)
            moved += 1
    return moved


def _selftest():
    with tempfile.TemporaryDirectory() as tmp:
        names = [
            "capex-2026-07-27.json", "capex-2026-08-10.json",
            "capex-2026-08-20.json", "capex-latest.json",
            "deal-sourcing-2026-08-01.json", "deal-sourcing-2026-08-27.json",
            "outbox-qc-coverage.json",
        ]
        for n in names:
            with open(os.path.join(tmp, n), "w", encoding="utf-8") as f:
                f.write("{}")

        today = datetime.date(2026, 8, 28)
        p = plan(tmp, keep_days=14, today=today)

        assert set(p.keys()) == {"capex", "deal-sourcing"}, p
        assert [f for f, _ in p["capex"]] == [
            "capex-2026-07-27.json", "capex-2026-08-10.json"], p["capex"]
        assert [f for f, _ in p["deal-sourcing"]] == [
            "deal-sourcing-2026-08-01.json"], p["deal-sourcing"]

        moved = apply_plan(tmp, p)
        assert moved == 3, moved
        assert not os.path.exists(os.path.join(tmp, "capex-2026-07-27.json"))
        assert os.path.exists(os.path.join(tmp, "_archive", "capex", "capex-2026-07-27.json"))
        # untouched: latest pointer, non-dated file, and anything inside the window
        assert os.path.exists(os.path.join(tmp, "capex-latest.json"))
        assert os.path.exists(os.path.join(tmp, "outbox-qc-coverage.json"))
        assert os.path.exists(os.path.join(tmp, "capex-2026-08-20.json"))
        assert os.path.exists(os.path.join(tmp, "deal-sourcing-2026-08-27.json"))

        # re-running against an already-archived file must not raise or duplicate
        with open(os.path.join(tmp, "capex-2026-07-20.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        os.makedirs(os.path.join(tmp, "_archive", "capex"), exist_ok=True)
        with open(os.path.join(tmp, "_archive", "capex", "capex-2026-07-20.json"), "w", encoding="utf-8") as f:
            f.write("{}")  # pre-existing archive copy for the same date
        p2 = plan(tmp, keep_days=14, today=today)
        try:
            apply_plan(tmp, p2)
        except FileExistsError:
            pass
        else:
            raise AssertionError("expected FileExistsError on a pre-archived duplicate")

    print("selftest: PASS")
    return 0


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep-days", type=int, default=14,
                     help="dated snapshots newer than this many days stay live (default 14)")
    ap.add_argument("--dry-run", action="store_true",
                     help="show what would move without writing anything")
    ap.add_argument("--state-dir", default=os.path.dirname(os.path.abspath(__file__)) + os.sep + "state")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    if not os.path.isdir(a.state_dir):
        sys.stderr.write("no such directory: %s\n" % a.state_dir)
        return 1

    to_archive = plan(a.state_dir, a.keep_days)
    total = sum(len(v) for v in to_archive.values())

    if total == 0:
        print("nothing older than %d days in %s -- nothing to archive" % (a.keep_days, a.state_dir))
        return 0

    for category, entries in sorted(to_archive.items()):
        print("%s: %d file(s) -> _archive/%s/  (%s .. %s)" % (
            category, len(entries), category, entries[0][1], entries[-1][1]))
    print("total: %d file(s)" % total)

    if a.dry_run:
        print("--dry-run: no files moved")
        return 0

    moved = apply_plan(a.state_dir, to_archive)
    print("archived %d file(s) under %s" % (moved, os.path.join(a.state_dir, "_archive")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

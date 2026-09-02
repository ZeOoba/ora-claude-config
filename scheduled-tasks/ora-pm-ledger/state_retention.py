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
    """Return (to_archive, invalid): to_archive is {category: [(filename,
    date_str), ...]} of files to archive; invalid is a list of filenames
    that matched the dated-snapshot pattern but carry a calendar-invalid
    date. Computed against `today` (injected for tests).

    Two invariants, both found by independent review (2026-08-28) against
    the actual producer scripts before being accepted -- neither is
    hypothetical:

    1. A regex-matching but calendar-invalid date (e.g. `capex-2026-02-30
       .json`) must not crash the whole run. `date.fromisoformat` raises
       ValueError on those; caught per-file and reported, not left to
       blow up per-directory.
    2. Each producer's own `newest_archive()` fallback (e.g.
       capex_snapshot_diff.py) recovers from a missing/corrupt `-latest.json`
       by scanning `state/` -- not `state/_archive/<category>/` -- for the
       newest dated snapshot, so a collapsed pull doesn't silently overwrite
       the baseline with an empty one. Archiving every stale snapshot for a
       category would strand that fallback with nothing to find. The newest
       VALID dated snapshot per category is therefore never archived,
       independent of --keep-days -- guaranteeing the producers' own
       recovery path always has a live candidate in state/ root."""
    if today is None:
        today = datetime.date.today()

    by_category = {}
    invalid = []
    for fname in os.listdir(state_dir):
        if not os.path.isfile(os.path.join(state_dir, fname)):
            continue
        m = SNAPSHOT_RE.match(fname)
        if not m:
            continue
        category, date_str = m.group("category"), m.group("date")
        try:
            parsed = datetime.date.fromisoformat(date_str)
        except ValueError:
            invalid.append(fname)
            continue
        by_category.setdefault(category, []).append((fname, date_str, parsed))

    to_archive = {}
    cutoff = today - datetime.timedelta(days=keep_days)
    for category, entries in by_category.items():
        entries.sort(key=lambda e: e[2])
        newest_fname = entries[-1][0]  # never archived -- producer fallback candidate
        stale = [
            (fname, date_str) for fname, date_str, parsed in entries
            if parsed < cutoff and fname != newest_fname
        ]
        if stale:
            to_archive[category] = stale
    return to_archive, invalid


def apply_plan(state_dir, to_archive):
    """Move planned files into state/_archive/<category>/. Returns the number
    of files moved. Refuses (raises FileExistsError) rather than overwrite an
    existing archived copy -- aborts the remainder of the run rather than
    silently clobbering; already-moved files stay moved, and the next run
    re-plans cleanly against whatever is left. Only reachable if a producer
    regenerates an already-archived date."""
    archive_root = os.path.join(state_dir, "_archive")
    moved = 0
    for category, entries in to_archive.items():
        dest_dir = os.path.join(archive_root, category)
        os.makedirs(dest_dir, exist_ok=True)
        for fname, _date_str in entries:
            src = os.path.join(state_dir, fname)
            dst = os.path.join(dest_dir, fname)
            if os.path.exists(dst):
                exc = FileExistsError(
                    "refusing to overwrite existing archive copy: %s" % dst)
                exc.moved = moved
                raise exc
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
        p, invalid = plan(tmp, keep_days=14, today=today)

        assert invalid == [], invalid
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

        # re-running against an already-archived duplicate is expected to raise
        # FileExistsError (refuse-not-clobber) -- it must not silently overwrite
        # or duplicate the existing archive copy
        with open(os.path.join(tmp, "capex-2026-07-20.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        os.makedirs(os.path.join(tmp, "_archive", "capex"), exist_ok=True)
        with open(os.path.join(tmp, "_archive", "capex", "capex-2026-07-20.json"), "w", encoding="utf-8") as f:
            f.write("{}")  # pre-existing archive copy for the same date
        p2, _ = plan(tmp, keep_days=14, today=today)
        try:
            apply_plan(tmp, p2)
        except FileExistsError:
            pass
        else:
            raise AssertionError("expected FileExistsError on a pre-archived duplicate")

    # independent-review fixes (2026-08-28): invalid date + newest-always-kept
    with tempfile.TemporaryDirectory() as tmp2:
        # a whole category with EVERY dated snapshot older than keep-days --
        # the newest one must survive regardless, so a producer's own
        # newest_archive() fallback always has a live candidate in state/ root
        names2 = [
            "property-register-2026-01-05.json",   # oldest
            "property-register-2026-01-12.json",   # newest -- must be kept live
            "capex-2026-02-30.json",                # calendar-invalid (regex matches, date doesn't)
            "capex-2026-08-27.json",                # valid, within window
        ]
        for n in names2:
            with open(os.path.join(tmp2, n), "w", encoding="utf-8") as f:
                f.write("{}")

        today2 = datetime.date(2026, 8, 28)
        p3, invalid3 = plan(tmp2, keep_days=14, today=today2)

        assert invalid3 == ["capex-2026-02-30.json"], invalid3
        assert set(p3.keys()) == {"property-register"}, p3
        assert [f for f, _ in p3["property-register"]] == [
            "property-register-2026-01-05.json"], p3["property-register"]
        # the newest property-register snapshot is >14 days stale too, but must
        # NOT appear in the archive plan -- it's the producer fallback candidate
        stale_names = [f for f, _ in p3["property-register"]]
        assert "property-register-2026-01-12.json" not in stale_names, stale_names

        moved3 = apply_plan(tmp2, p3)
        assert moved3 == 1, moved3
        assert os.path.exists(os.path.join(tmp2, "property-register-2026-01-12.json")), \
            "newest snapshot must stay live even though it is stale by date"
        # the invalid-date file is left alone, not silently deleted or moved
        assert os.path.exists(os.path.join(tmp2, "capex-2026-02-30.json"))

    # independent-review fix (2026-09-02): a negative --keep-days must be
    # rejected at the CLI layer, not silently accepted -- it would push the
    # cutoff into the future and archive every current snapshot as "stale"
    with tempfile.TemporaryDirectory() as tmp3:
        with open(os.path.join(tmp3, "capex-2026-08-27.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        rc = main(["--keep-days", "-1", "--state-dir", tmp3])
        assert rc == 1, rc
        # rejected before touching anything -- the file must still be untouched
        assert os.path.exists(os.path.join(tmp3, "capex-2026-08-27.json"))

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
                     help="dated snapshots from today back through today-N days stay "
                          "live, inclusive (default 14); must be >= 0")
    ap.add_argument("--dry-run", action="store_true",
                     help="show what would move without writing anything")
    ap.add_argument("--state-dir", default=os.path.dirname(os.path.abspath(__file__)) + os.sep + "state")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    if a.keep_days < 0:
        sys.stderr.write(
            "--keep-days must be >= 0 (got %d) -- a negative value pushes the "
            "cutoff into the future and would archive every current snapshot\n"
            % a.keep_days)
        return 1

    if not os.path.isdir(a.state_dir):
        sys.stderr.write("no such directory: %s\n" % a.state_dir)
        return 1

    to_archive, invalid = plan(a.state_dir, a.keep_days)
    total = sum(len(v) for v in to_archive.values())

    for fname in invalid:
        print("INVALID DATE (left in place, not archived): %s" % fname)

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

    try:
        moved = apply_plan(a.state_dir, to_archive)
    except FileExistsError as exc:
        partial = getattr(exc, "moved", 0)
        sys.stderr.write(
            "aborted after archiving %d of %d file(s): %s\n" % (partial, total, exc))
        return 3
    print("archived %d file(s) under %s" % (moved, os.path.join(a.state_dir, "_archive")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""allocate-oi-id.py -- hand out the next free OI-NNN id, atomically.

WHY THIS EXISTS (2026-08-04): `check-open-items-duplicate-ids.py` is the standing
CATCH for two sessions independently stamping the same OI-NNN. It works -- it
caught OI-027 (2026-07-27), OI-061 and OI-066 (2026-08-03/04, two collisions
inside one hour). But it catches AFTER the fact, and because it runs in the
pre-push hook-tests gate, one session's collision blocks EVERY session's push
until somebody renumbers. This allocator removes the collision instead.

THE WINDOW IS NOT THE READ. The naive procedure -- "read the tracker's highest
OI-NNN, add one" -- is not wrong because reading is slow. It is wrong because
minutes pass between reading the max and committing the row, and throughout that
window the tracker still shows the OLD max. A second session reading in good
faith gets the same answer. Both were correct at the instant they looked; see
memory/feedback_findings_decay_recheck_before_writing.md.

So a counter alone does not fix this. Allocation must record a DURABLE
RESERVATION at the moment the id is handed out, and every later allocation must
consider reservations as well as the tracker:

    next id = max(highest in tracker, highest reserved) + 1

Reservations live in an append-only ledger next to the tracker.

THE LEDGER IS LOCAL-ONLY AND NOT BACKED UP. `.gitignore`'s `*.log` catches
`_state/oi-id-reservations.log`, deliberately: committing a file that gains a
line on every allocation would drop it straight into the shared-checkout
contention this tool exists to avoid. The BASELINE is tracked; the reservations
are not. So after a restore or fresh clone the ledger reads empty while the
tracker still holds every id, and enforcement flags everything above the
baseline. Recovery is a re-baseline, documented in full at the bottom of
`_state/oi-id-baseline.txt` -- including how to tell a lost ledger (empty
ledger, many violations) from a real hand-assigned id (populated ledger, one or
two), because re-baselining to paper over the latter would grandfather a genuine
collision.

An id is therefore burned the moment it is handed out, whether or not the row is
ever written. That is deliberate: ids are free, collisions are not. A reservation
that never becomes a row shows up in `--report` as ORPHANED, for a human to
notice; it is NEVER auto-reclaimed, because reclaiming is precisely how you
re-open the window this file closes.

CONCURRENCY. Serialisation is an O_EXCL lock file, which is atomic on Windows
and POSIX alike. A crashed holder cannot wedge the allocator forever: a lock
older than `stale_lock_secs` is broken and reported. Verified under 12 racing
threads AND 8 racing processes -- threads alone would not prove it, since real
sessions are separate processes.

Usage:
  python maintenance/allocate-oi-id.py --session <id> --note "<why>"
  python maintenance/allocate-oi-id.py --report        # reservations vs tracker
  python maintenance/allocate-oi-id.py --tracker <p> --ledger <p> ...   # tests

Prints the allocated id (e.g. `OI-069`) on stdout and nothing else, so it can be
used as `ID=$(python maintenance/allocate-oi-id.py --session $S --note x)`.
"""
import argparse
import errno
import io
import os
import re
import sys
import time
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
DEFAULT_TRACKER = os.path.join(
    HOME, ".claude", "projects",
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory",
    "open-items-tracker.md")
DEFAULT_LEDGER = os.path.join(
    HOME, ".claude", "maintenance", "_state", "oi-id-reservations.log")
# Highest id predating enforcement. Ids <= this are grandfathered: at switch-on
# the ledger held 0 reservations against 69 tracker ids, so a whole-file rule
# would have blocked every push on day one.
DEFAULT_BASELINE = os.path.join(
    HOME, ".claude", "maintenance", "_state", "oi-id-baseline.txt")

# Same shapes check-open-items-duplicate-ids.py uses -- kept identical on
# purpose so the allocator and the checker can never disagree about what
# counts as a taken id.
ROW_ID_RE = re.compile(r"^\|\s*\[OI-(\d+)\]\(#OI-\d+\)\s*\|", re.MULTILINE)
SECTION_ID_RE = re.compile(r"^### OI-(\d+)\s*$", re.MULTILINE)
LEDGER_ID_RE = re.compile(r"^OI-(\d+)\s*\|", re.MULTILINE)

STALE_LOCK_SECS = 120
LOCK_WAIT_SECS = 30


class AllocatorError(RuntimeError):
    pass


def _read(path):
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def tracker_ids(text):
    """Every id the tracker considers taken: rows AND detail sections. A
    section with no row yet is still taken -- it is somebody's in-flight item."""
    return {int(n) for n in ROW_ID_RE.findall(text)} | \
           {int(n) for n in SECTION_ID_RE.findall(text)}


def ledger_ids(text):
    return {int(n) for n in LEDGER_ID_RE.findall(text)}


def _acquire(lock_path, stale_lock_secs=STALE_LOCK_SECS,
             wait_secs=LOCK_WAIT_SECS):
    """O_EXCL lock with stale-breaking. Returns a note about any break, so the
    caller can surface it rather than silently papering over a crash."""
    deadline = time.time() + wait_secs
    note = ""
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ("%d %s\n" % (os.getpid(),
                                       datetime.now().isoformat())).encode())
            os.close(fd)
            return note
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            try:
                age = time.time() - os.path.getmtime(lock_path)
            except OSError:
                continue                      # holder vanished; retry
            if age > stale_lock_secs:
                try:
                    os.unlink(lock_path)
                    note = ("broke a stale lock (age %.0fs > %ds)"
                            % (age, stale_lock_secs))
                except OSError:
                    pass
                continue
            if time.time() > deadline:
                raise AllocatorError(
                    "could not acquire %s within %ds (held, not stale)"
                    % (lock_path, wait_secs))
            time.sleep(0.05)


def _release(lock_path):
    try:
        os.unlink(lock_path)
    except OSError:
        pass


def allocate(tracker_path=None, ledger_path=None, session="unknown", note="",
             stale_lock_secs=STALE_LOCK_SECS):
    """Reserve and return the next free id as `OI-NNN`.

    Refuses if the tracker is unreadable: allocating from a missing tracker
    would return OI-001 and collide with everything. A loud failure beats a
    confidently wrong id."""
    tracker_path = tracker_path or DEFAULT_TRACKER
    ledger_path = ledger_path or DEFAULT_LEDGER
    if not os.path.isfile(tracker_path):
        raise AllocatorError(
            "tracker not readable at %s -- refusing to allocate (a missing "
            "tracker would yield OI-001 and collide with everything)"
            % tracker_path)

    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    lock_path = ledger_path + ".lock"
    broke = _acquire(lock_path, stale_lock_secs=stale_lock_secs)
    try:
        taken = tracker_ids(_read(tracker_path))
        if os.path.isfile(ledger_path):
            taken |= ledger_ids(_read(ledger_path))
        nxt = (max(taken) + 1) if taken else 1
        oid = "OI-%03d" % nxt
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = "%s | %s | %s | %s\n" % (
            oid, stamp, session,
            " ".join(str(note).split()) or "(no note)")
        with io.open(ledger_path, "a", encoding="utf-8", newline="") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())      # durable BEFORE the lock drops
    finally:
        _release(lock_path)
    if broke:
        sys.stderr.write("allocate-oi-id: %s\n" % broke)
    return oid


def backfill(oid, ledger_path=None, session="unknown", note=""):
    """Record a reservation for an id that already exists but was never
    allocated -- a hand-edit, a historical import, a merge resolution.

    This is the escape hatch, and it is NOT optional. Enforcement without one
    wedges honest work, and a wedged gate gets bypassed, which is strictly worse
    than no gate. Entries are marked BACKFILL so a human can later see exactly
    which ids went round the allocator and how often -- if that list grows, the
    allocator is too inconvenient and THAT is the thing to fix."""
    ledger_path = ledger_path or DEFAULT_LEDGER
    if not re.fullmatch(r"OI-\d+", str(oid or "")):
        raise AllocatorError("not an OI-NNN id: %r" % (oid,))
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    lock_path = ledger_path + ".lock"
    _acquire(lock_path)
    try:
        existing = ledger_ids(_read(ledger_path)) if os.path.isfile(ledger_path) else set()
        if int(str(oid).split("-")[1]) in existing:
            raise AllocatorError("%s is already reserved -- nothing to backfill" % oid)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with io.open(ledger_path, "a", encoding="utf-8", newline="") as f:
            f.write("%s | %s | %s | BACKFILL %s\n" % (
                oid, stamp, session, " ".join(str(note).split()) or "(no note)"))
            f.flush()
            os.fsync(f.fileno())
    finally:
        _release(lock_path)
    return oid


def read_baseline(path=None):
    """Highest id that predates enforcement. Ids <= this are grandfathered.

    Returns None when unreadable -- callers must treat that as SKIP, never as
    'baseline 0', which would turn every id in the file into a violation."""
    path = path or DEFAULT_BASELINE
    try:
        for ln in _read(path).splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                m = re.search(r"(\d+)", ln)
                if m:
                    return int(m.group(1))
    except Exception:
        return None
    return None


def enforce(tracker_path=None, ledger_path=None, baseline=None):
    """Ids ABOVE the baseline must carry a ledger reservation.

    Deliberately baseline-scoped rather than whole-file: at switch-on the ledger
    held 0 reservations against 69 tracker ids, so a whole-file rule would have
    failed every push on day one. Grandfathering is what makes enforcement
    adoptable at all.

    Fails OPEN on a missing baseline (skipped=True). A gate that cannot read its
    own config must not convert that into a total outage."""
    tracker_path = tracker_path or DEFAULT_TRACKER
    ledger_path = ledger_path or DEFAULT_LEDGER
    if baseline is None:
        return {"violations": [], "skipped": True,
                "reason": "no readable baseline -- enforcement skipped, not asserted"}
    taken = tracker_ids(_read(tracker_path)) if os.path.isfile(tracker_path) else set()
    reserved = ledger_ids(_read(ledger_path)) if os.path.isfile(ledger_path) else set()
    violations = [{"id": "OI-%03d" % n} for n in sorted(taken)
                  if n > baseline and n not in reserved]
    return {"violations": violations, "skipped": False, "baseline": baseline,
            "checked": len([n for n in taken if n > baseline])}


def format_enforcement(result):
    if result.get("skipped"):
        return "OI-id enforcement: SKIPPED -- %s" % result.get("reason", "")
    if not result["violations"]:
        return ("OI-id enforcement: clean (%d id(s) above baseline OI-%03d, all "
                "reserved)" % (result["checked"], result["baseline"]))
    lines = ["OI-id enforcement: %d unreserved id(s) above baseline OI-%03d"
             % (len(result["violations"]), result["baseline"])]
    for v in result["violations"]:
        lines.append(
            "[ACTION] %s was added without a reservation. Ids must come from "
            "`python maintenance/allocate-oi-id.py --session <id> --note \"<why>\"`, "
            "which is what makes two sessions unable to pick the same number. "
            "If %s is legitimate but was hand-assigned, merged in from a branch, "
            "or imported, regularise it with `python maintenance/allocate-oi-id.py "
            "--backfill %s --note \"<why it bypassed the allocator>\"`."
            % (v["id"], v["id"], v["id"]))
    return "\n".join(lines)


def report(tracker_path=None, ledger_path=None):
    """Reservations that never became rows. Informational only -- never
    reclaimed, because reclaiming re-opens the window this file closes."""
    tracker_path = tracker_path or DEFAULT_TRACKER
    ledger_path = ledger_path or DEFAULT_LEDGER
    t = tracker_ids(_read(tracker_path)) if os.path.isfile(tracker_path) else set()
    lines = _read(ledger_path).splitlines() if os.path.isfile(ledger_path) else []
    orphans = []
    for ln in lines:
        m = LEDGER_ID_RE.match(ln)
        if m and int(m.group(1)) not in t:
            orphans.append(ln)
    return {"reserved": len(lines), "in_tracker": len(t), "orphans": orphans}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--session", default=os.environ.get(
        "CLAUDE_CODE_SESSION_ID", "unknown"))
    ap.add_argument("--note", default="")
    ap.add_argument("--tracker", default=None)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--enforce", action="store_true",
                    help="exit 1 if any id above the baseline lacks a reservation")
    ap.add_argument("--backfill", metavar="OI-NNN",
                    help="regularise an id that was hand-assigned, merged in, or "
                         "imported (escape hatch; recorded as BACKFILL)")
    ap.add_argument("--baseline", default=None,
                    help="path to the baseline file (tests only)")
    a = ap.parse_args(argv)

    if a.backfill:
        try:
            print(backfill(a.backfill, a.ledger, session=a.session, note=a.note))
        except AllocatorError as e:
            sys.stderr.write("allocate-oi-id: %s\n" % e)
            return 1
        return 0

    if a.enforce:
        base = read_baseline(a.baseline)
        r = enforce(a.tracker, a.ledger, baseline=base)
        print(format_enforcement(r))
        return 1 if r["violations"] else 0

    if a.report:
        r = report(a.tracker, a.ledger)
        print("reservations: %d | ids in tracker: %d | orphaned reservations: %d"
              % (r["reserved"], r["in_tracker"], len(r["orphans"])))
        for o in r["orphans"]:
            print("  ORPHAN " + o)
        print("(orphans are reservations whose row was never written. They are "
              "NOT reclaimed -- reclaiming re-opens the collision window.)")
        return 0
    try:
        print(allocate(a.tracker, a.ledger, session=a.session, note=a.note))
    except AllocatorError as e:
        sys.stderr.write("allocate-oi-id: %s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

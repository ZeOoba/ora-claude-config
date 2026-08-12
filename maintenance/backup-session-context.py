#!/usr/bin/env python3
"""Scrubbed local backup for ~/.claude/session-context.md.

WHY (2026-08-09): session-context.md is auto-loaded into EVERY session and is
one of the two homes of the active-confidential-deal roster (CLAUDE.md Hard
Invariant 3; the other is hooks/confidential-terms.json). It sits at the root of
~/.claude, which .gitignore denies by default (`/*` + explicit `!` opt-ins), and
it has never been tracked on any branch -- so it has NO history and NO backup.

That exclusion is CORRECT and must stay: this repo pushes to
github.com/ZeOoba/ora-claude-config, and tracking the file would publish active
deal names the moment a deal goes live. confidential-terms.json is excluded from
the same repo for the same reason (an explicit re-ignore, since hooks/ IS opted
in). Both roster homes are out, by two mechanisms, deliberately.

So the durability gap cannot be closed by opting in. This closes it the only
other way -- copies that never touch the git remote:

  1. LOCAL rotation  -> ~/.claude/backups/session-context/
     `backups` is already in doctrine-integrity-probe.py's
     BACKUP_SWEEP_TRANSIENT_DIRS, i.e. untracked BY CONSTRUCTION. Protects
     against the realistic failure: an overwrite or truncation of a file with no
     `git checkout --` to undo it.
  2. OFF-MACHINE mirror -> Claude_Workspace/_state/session-context-backup/
     OneDrive-synced. CLAUDE.md invariant 5 designates Claude_Workspace a free
     working surface, and OneDrive already legitimately holds firm deal data --
     the invariant-3 concern is the GitHub remote, not the firm's own storage.
     This is the leg that actually survives losing the machine.

Three failure classes of this exact shape are already recorded in .gitignore's
own comments (scheduled-task specs 2b, memory/ 2c, _shared/send-via-outlook.ps1)
-- each "silently fell out of backup, unnoticed". Each was fixed by opting in.
This is the first one where opting in is the unavailable answer.

=== SCRUB VERDICT: CLEAN | UNVERIFIED | HITS ===

Each run asks scrub-before-optin.py whether the snapshot carries active
confidential terms or secret shapes, and records the answer beside the
snapshots. The verdict is INFORMATIONAL and never blocks a backup -- both
destinations tolerate confidential content by design. It exists so a future
reader deciding whether a snapshot could ever be published has a real answer
rather than a comforting blank.

The whole difficulty is that "the scan found nothing" and "no scan happened"
both surface as exit 0. THREE distinct doors lead to a false CLEAN, and all
three must be shut (findings 1/4/5 of the 2026-08-09 review; the first was a
live Critical -- an undecodable snapshot was being filed CLEAN):

  a. ROSTER unreachable -> the scrub prints "[WARN] confidential-term scan
     skipped (fail-open)" and still exits 0 CLEAN. Caught two ways: we check
     the roster ourselves before calling, and we match the fail-open marker on
     the scrub's [WARN] lines.
  b. TARGET unreadable/undecodable -> scan_file_for_terms returns None and
     scan_file_for_secrets returns [], both SILENTLY, with zero warnings; the
     scrub then reports "0 hits, 0 warning(s)" and exits 0. No marker fires
     because this failure is upstream of the roster entirely. Caught by
     pre-reading the target through the scanner's OWN reader
     (doctrine-integrity-probe.read_optional) so the check cannot drift from
     the ladder the scan will actually use.
  c. SCRUB CRASHED -> a traceback exits non-zero, which naively reads as HITS.
     Caught by requiring the scrub's own "SCRUB FOUND ISSUES" banner before
     believing a non-zero exit means findings.

A scan that could not actually run records UNVERIFIED. Never CLEAN.

Marker matching is restricted to [WARN]-prefixed lines and runs only AFTER the
returncode check, because the scrub echoes scanned PATHS in its hit report -- an
unrestricted substring match let a snapshot path containing "fail-open" convert
a genuine HITS into UNVERIFIED.

Read-only on the source. Never writes into the git-tracked tree.

Usage:
  python backup-session-context.py [--source P] [--local-dir P] [--mirror-dir P]
                                   [--retain N] [--scrub P] [--quiet]
Exit 0 = snapshot taken, or a no-op because content was unchanged (a failed
mirror also exits 0 -- it degrades to local-only). Exit 1 = the source is
missing/empty, or the LOCAL snapshot could not be written.
"""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE_DIR = HERE.parent

DEFAULT_SOURCE = CLAUDE_DIR / "session-context.md"
DEFAULT_LOCAL = CLAUDE_DIR / "backups" / "session-context"
DEFAULT_MIRROR = Path(r"C:\Users\Owner\OneDrive - Oxford Capital Partners"
                      r"\Claude_Workspace\_state\session-context-backup")
DEFAULT_SCRUB = HERE / "scrub-before-optin.py"
DEFAULT_RETAIN = 30

LEDGER_NAME = "backup-log.txt"
SNAPSHOT_PREFIX = "session-context_"
# Second-resolution and lexicographically sortable, so a plain filename sort is
# a chronological sort -- retention and "newest" never need to stat anything.
STAMP_FMT = "%Y-%m-%dT%H%M%S"
# Collision suffix for two content-distinct runs inside one second. "_02" is
# chosen so it sorts AFTER the bare name ('_' 0x5F > '.' 0x2E), preserving the
# filename-sort-is-time-sort property. A "-2" suffix would sort BEFORE it and
# silently invert which snapshot retention treats as newest.
COLLISION_FMT = "_%02d"

# The scrub's own fail-open wording. Matched on [WARN] lines only -- see the
# module docstring. test_scrub_fail_open_wording_is_still_coupled pins this
# against the helper's source so a reword there fails a test instead of
# silently turning every fail-open into CLEAN.
FAIL_OPEN_MARKERS = ("fail-open", "scan skipped")
# The scrub's findings banner. A non-zero exit WITHOUT this is a crashed
# scanner, not a detection.
HITS_BANNER = "SCRUB FOUND ISSUES"


def log(msg, quiet=False, stream=None):
    if not quiet or stream is sys.stderr:
        print(msg, file=stream or sys.stdout)


def snapshots(local_dir):
    """Existing snapshots, oldest first. Excludes the ledger (.txt)."""
    if not local_dir.is_dir():
        return []
    return sorted(p for p in local_dir.iterdir()
                  if p.is_file() and p.name.startswith(SNAPSHOT_PREFIX)
                  and p.suffix == ".md")


def load_probe(scrub_path):
    """Import the SAME doctrine-integrity-probe module the scrub imports, so our
    decodability pre-check uses the scan's own reader rather than a re-derived
    copy of its encoding ladder. Returns (module, error)."""
    probe_path = scrub_path.parent / "doctrine-integrity-probe.py"
    if not probe_path.is_file():
        return None, "scanner module not found: %s" % probe_path
    try:
        spec = importlib.util.spec_from_file_location("dip_for_backup", probe_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:                      # noqa: BLE001 - any import failure
        return None, "scanner module import failed: %s" % exc


def scrub_verdict(scrub_path, target):
    """Returns (verdict, detail) where verdict is CLEAN | UNVERIFIED | HITS.

    UNVERIFIED whenever the scan could not actually be performed. Never collapse
    UNVERIFIED into CLEAN -- that asserts "no confidential terms present" when
    the truth is "nobody looked"."""
    scrub_path = Path(scrub_path).resolve()
    if not scrub_path.is_file():
        return "UNVERIFIED", "scrub script not found: %s" % scrub_path

    # Resolve the roster the SAME way the scrub does, so the verification claim
    # describes the scan that actually ran rather than a different file.
    roster = scrub_path.parent.parent / "hooks" / "confidential-terms.json"
    if not roster.is_file():
        return "UNVERIFIED", "roster not reachable from the scrub: %s" % roster

    # Door (b): the scrub SILENTLY skips a file it cannot decode and still
    # reports "0 hits, 0 warning(s)" at exit 0. Pre-read through its own reader.
    probe, probe_err = load_probe(scrub_path)
    if probe is None:
        return "UNVERIFIED", probe_err
    try:
        body, read_err = probe.read_optional(target)
    except Exception as exc:                      # noqa: BLE001
        return "UNVERIFIED", "scanner reader raised on the target: %s" % exc
    if body is None:
        return "UNVERIFIED", ("target not readable by the scanner's own reader "
                              "(it would be skipped, not scanned): %s" % read_err)

    try:
        r = subprocess.run([sys.executable, str(scrub_path), str(target)],
                           capture_output=True, text=True, timeout=180)
    except (subprocess.SubprocessError, OSError) as exc:
        return "UNVERIFIED", "scrub failed to run: %s" % exc

    stdout = r.stdout or ""
    combined = stdout + (r.stderr or "")

    # Door (c): returncode FIRST, and only trust it as "findings" if the scrub
    # printed its own banner. Anything else non-zero is a broken scanner.
    if r.returncode != 0:
        if HITS_BANNER in stdout:
            # Deliberately does NOT echo matched text -- the scrub reports by
            # index/label only, and that discipline must survive being relayed.
            return "HITS", "scrub reported findings (index-only; exit %d)" % r.returncode
        first = next((ln.strip() for ln in combined.splitlines() if ln.strip()), "")
        return "UNVERIFIED", ("scrub exited %d with no findings banner -- scanner "
                              "error, not a detection: %s" % (r.returncode, first[:200]))

    # Door (a): fail-open marker, on [WARN] lines only -- never on echoed paths.
    for line in combined.splitlines():
        stripped = line.strip()
        if not stripped.startswith("[WARN]"):
            continue
        low = stripped.lower()
        if any(m in low for m in FAIL_OPEN_MARKERS):
            return "UNVERIFIED", "scrub reported a fail-open skip: %s" % stripped[:200]

    return "CLEAN", "scrub exit 0; roster reachable; target readable and scanned"


def append_ledger(local_dir, mirror_dir, stamp, verdict, detail, action):
    """Append one run line. Mirrored too -- a verdict that dies with the machine
    leaves recovered snapshots with exactly the comforting blank this exists to
    prevent. Returns (ok, error); mirroring the ledger is best-effort."""
    line = "%s  %-10s  %-10s  %s\n" % (stamp, action, verdict, detail)
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        ledger = local_dir / LEDGER_NAME
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError as exc:
        return False, str(exc)
    try:
        if mirror_dir.is_dir():
            shutil.copy2(str(ledger), str(mirror_dir / LEDGER_NAME))
    except (OSError, shutil.Error):
        pass          # mirror health is reported separately; never fail on this
    return True, None


def copy_to_mirror(mirror_dir, snapshot):
    """Best-effort off-machine copy. Returns (ok, error). NEVER fatal: OneDrive
    can be offline, locked, or mid-sync, and losing the mirror must not cost the
    local snapshot.

    Pruning is deliberately NOT done here. Folding it in would let a prune
    failure report the copy as failed, which would write "local-only" to the
    ledger for a snapshot that did reach the mirror -- the ledger recording a
    state that never happened is the one thing this script exists to avoid."""
    try:
        mirror_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(snapshot), str(mirror_dir / snapshot.name))
    except (OSError, shutil.Error) as exc:
        return False, str(exc)
    return True, None


def prune(directory, retain):
    """Drop oldest snapshots beyond `retain`. Ledger is never pruned."""
    existing = snapshots(directory)
    for old in existing[:max(0, len(existing) - retain)]:
        old.unlink()


def unique_target(local_dir, stamp):
    """A never-colliding snapshot path. Two content-distinct runs inside one
    second would otherwise land on the same filename and the second would
    OVERWRITE the first -- destroying good history in a tool whose entire
    purpose is retaining it."""
    base = "%s%s" % (SNAPSHOT_PREFIX, stamp)
    candidate = local_dir / ("%s.md" % base)
    n = 2
    while candidate.exists():
        candidate = local_dir / ("%s%s.md" % (base, COLLISION_FMT % n))
        n += 1
    return candidate


def write_atomic(target, data):
    """Write via a temp sibling + os.replace so a crash mid-write cannot leave a
    truncated .md that snapshots() counts as valid history."""
    tmp = target.with_name(target.name + ".tmp-write")
    try:
        tmp.write_bytes(data)
        os.replace(str(tmp), str(target))
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--local-dir", default=str(DEFAULT_LOCAL))
    ap.add_argument("--mirror-dir", default=str(DEFAULT_MIRROR))
    ap.add_argument("--scrub", default=str(DEFAULT_SCRUB))
    ap.add_argument("--retain", type=int, default=DEFAULT_RETAIN,
                    help="snapshots to keep (>=1); 0 is rejected rather than "
                         "silently promoted to 1")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.retain < 1:
        ap.error("--retain must be >= 1 (got %d)" % args.retain)

    source = Path(args.source)
    local_dir = Path(args.local_dir)
    mirror_dir = Path(args.mirror_dir)
    retain = args.retain

    if not source.is_file():
        print("FAIL -- source not found: %s" % source, file=sys.stderr)
        return 1
    try:
        data = source.read_bytes()
    except OSError as exc:
        print("FAIL -- source unreadable: %s (%s)" % (source, exc), file=sys.stderr)
        return 1
    if not data.strip():
        # Refusing here is the point: at --retain N, snapshotting a truncation
        # spends a slot on the damage and is the mechanism by which the last
        # good copies get rotated out.
        print("FAIL -- source is empty (%s) -- refusing to snapshot a likely "
              "truncation; existing snapshots left untouched" % source, file=sys.stderr)
        return 1

    existing = snapshots(local_dir)
    if existing:
        newest = existing[-1]
        try:
            unchanged = newest.read_bytes() == data
        except OSError:
            unchanged = False      # unreadable newest -> take a fresh snapshot
        if unchanged:
            # The mirror is NOT implied by the local snapshot. If a previous run
            # failed to mirror and the content then stops changing, every later
            # run would exit "unchanged" and the off-machine copy -- the leg that
            # survives losing the machine -- would never appear, silently.
            repaired = False
            if not (mirror_dir / newest.name).is_file():
                ok, err = copy_to_mirror(mirror_dir, newest)
                if ok:
                    repaired = True
                    log("mirror CATCH-UP: copied %s (a previous run had not "
                        "mirrored it)" % newest.name, args.quiet)
                    append_ledger(local_dir, mirror_dir, time.strftime(STAMP_FMT),
                                  "n/a", "catch-up copy of %s" % newest.name,
                                  "mirror-fix")
                else:
                    log("WARN -- unchanged, but the newest snapshot is STILL not "
                        "mirrored (%s): %s" % (mirror_dir, err), args.quiet, sys.stderr)
            log("unchanged -- no new snapshot (%d retained)%s"
                % (len(existing), " [mirror repaired]" if repaired else ""), args.quiet)
            return 0

    stamp = time.strftime(STAMP_FMT)
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        target = unique_target(local_dir, stamp)
        write_atomic(target, data)
    except OSError as exc:
        print("FAIL -- could not write the local snapshot: %s" % exc, file=sys.stderr)
        return 1

    verdict, detail = scrub_verdict(args.scrub, target)

    mirrored, mirror_err = copy_to_mirror(mirror_dir, target)
    if mirrored:
        try:
            prune(mirror_dir, retain)
        except OSError as exc:
            log("WARN -- mirror pruning failed: %s" % exc, args.quiet, sys.stderr)
    try:
        prune(local_dir, retain)
    except OSError as exc:
        log("WARN -- local pruning failed: %s" % exc, args.quiet, sys.stderr)

    action = "snapshot" if mirrored else "local-only"
    ok, ledger_err = append_ledger(local_dir, mirror_dir, stamp, verdict, detail, action)

    log("snapshot: %s" % target.name, args.quiet)
    log("scrub:    %s (%s)" % (verdict, detail), args.quiet)
    if verdict == "UNVERIFIED":
        log("WARN -- scrub UNVERIFIED: recorded as 'nobody looked', NOT as clean. "
            "Do not treat this snapshot as confirmed publishable.", args.quiet, sys.stderr)
    elif verdict == "HITS":
        log("WARN -- scrub found confidential/secret matches. Both destinations "
            "tolerate this by design; it must NEVER reach the git remote.",
            args.quiet, sys.stderr)
    if mirrored:
        log("mirror:   %s" % mirror_dir, args.quiet)
    else:
        log("WARN -- mirror FAILED (%s): %s -- local snapshot kept, off-machine "
            "copy skipped this run" % (mirror_dir, mirror_err), args.quiet, sys.stderr)
    if not ok:
        log("WARN -- ledger append failed: %s" % ledger_err, args.quiet, sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

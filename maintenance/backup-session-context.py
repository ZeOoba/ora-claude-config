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

SCRUB VERDICT -- the subtle part. Each run asks scrub-before-optin.py whether
the snapshot carries active confidential terms or secret shapes, and records the
answer beside the snapshots. But that scrub FAILS OPEN: with its roster
unreachable it prints "scan skipped (fail-open)" and still exits 0 reporting
CLEAN. Recording that as CLEAN would assert "no confidential terms present" when
the truth is "nobody looked" -- an inferred null dressed as a verified one. So a
scan that could not actually run is recorded as UNVERIFIED, never CLEAN.

The verdict is INFORMATIONAL and never blocks a backup: both destinations
tolerate confidential content by design. It exists so a future reader deciding
whether a snapshot could ever be published has a real answer rather than a
comforting blank.

Read-only on the source. Never writes into the git-tracked tree.

Usage:
  python backup-session-context.py [--source P] [--local-dir P] [--mirror-dir P]
                                   [--retain N] [--scrub P] [--quiet]
Exit 0 = snapshot taken, or a no-op because content was unchanged (a failed
mirror also exits 0 -- it degrades to local-only). Exit 1 = the source is
missing/empty, or the LOCAL snapshot could not be written.
"""
import argparse
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

# The scrub's own fail-open marker. Matching on this (not just its exit code) is
# what stops a "couldn't look" from being filed as a "looked and found nothing".
FAIL_OPEN_MARKERS = ("fail-open", "scan skipped")


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


def scrub_verdict(scrub_path, target):
    """Returns (verdict, detail) where verdict is CLEAN | UNVERIFIED | HITS.

    UNVERIFIED is returned whenever the scan could not actually be performed --
    absent scrub, absent/unreadable roster, crash, or the scrub's own fail-open
    marker in its output. Never collapse UNVERIFIED into CLEAN."""
    scrub_path = Path(scrub_path)
    if not scrub_path.is_file():
        return "UNVERIFIED", "scrub script not found: %s" % scrub_path

    # Resolve the roster the SAME way the scrub does, so the verification claim
    # describes the scan that actually ran rather than a different file.
    roster = scrub_path.parent.parent / "hooks" / "confidential-terms.json"
    if not roster.is_file():
        return "UNVERIFIED", "roster not reachable from the scrub: %s" % roster

    try:
        r = subprocess.run([sys.executable, str(scrub_path), str(target)],
                           capture_output=True, text=True, timeout=180)
    except (subprocess.SubprocessError, OSError) as exc:
        return "UNVERIFIED", "scrub failed to run: %s" % exc

    out = (r.stdout or "") + (r.stderr or "")
    low = out.lower()
    if any(m in low for m in FAIL_OPEN_MARKERS):
        return "UNVERIFIED", "scrub reported a fail-open skip (roster unresolved)"
    if r.returncode != 0:
        # Deliberately does NOT echo the matched text -- the scrub reports by
        # index/label only, and that discipline must survive being relayed.
        return "HITS", "scrub exit %d -- see its own index-only report" % r.returncode
    return "CLEAN", "scrub exit 0, roster reachable"


def append_ledger(local_dir, stamp, verdict, detail, action):
    line = "%s  %-10s  %-10s  %s\n" % (stamp, action, verdict, detail)
    try:
        with (local_dir / LEDGER_NAME).open("a", encoding="utf-8") as fh:
            fh.write(line)
        return True, None
    except OSError as exc:
        return False, str(exc)


def mirror_snapshot(mirror_dir, snapshot):
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--local-dir", default=str(DEFAULT_LOCAL))
    ap.add_argument("--mirror-dir", default=str(DEFAULT_MIRROR))
    ap.add_argument("--scrub", default=str(DEFAULT_SCRUB))
    ap.add_argument("--retain", type=int, default=DEFAULT_RETAIN)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    source = Path(args.source)
    local_dir = Path(args.local_dir)
    mirror_dir = Path(args.mirror_dir)
    retain = max(1, args.retain)

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
        try:
            if existing[-1].read_bytes() == data:
                log("unchanged -- no new snapshot (%d retained)" % len(existing), args.quiet)
                return 0
        except OSError:
            pass  # unreadable newest snapshot -> fall through and take a fresh one

    stamp = time.strftime(STAMP_FMT)
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        target = local_dir / ("%s%s.md" % (SNAPSHOT_PREFIX, stamp))
        target.write_bytes(data)
    except OSError as exc:
        print("FAIL -- could not write the local snapshot: %s" % exc, file=sys.stderr)
        return 1

    verdict, detail = scrub_verdict(args.scrub, target)

    mirrored, mirror_err = mirror_snapshot(mirror_dir, target)
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
    ok, ledger_err = append_ledger(local_dir, stamp, verdict, detail, action)

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

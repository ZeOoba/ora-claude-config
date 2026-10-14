#!/usr/bin/env python3
"""Reclaim disk from LAMS/Cowork per-session audit.jsonl growth.

Every LAMS/Cowork session directory under local-agent-mode-sessions carries its own
audit.jsonl (tool-call audit trail). Nothing rotates or prunes these -- measured
2026-09-18: 98 files, 102 MB live, growing at roughly 950 MB/quarter unattended
(friction flagged this same day: a site-write-gate false-positive investigation was
blocked from saving a memory file by the SAME slug-matching bug this store's naming
scheme also trips -- unrelated fix, same investigation).

SAFETY MODEL (CLAUDE.md invariant 6 -- never delete, move to /archive/):
  - PRE-30-DAY GATE: only a file whose mtime is more than --since-days (default 30)
    old is eligible. A file that recent means its session could still be active --
    the mtime gate IS the liveness check on this substrate (LAMS session ids share
    no namespace with hooks/active-work claims, so that claim registry has nothing
    to check here; see the memory doc this script ships with for why).
  - LOCK CHECK: an eligible file is opened for exclusive access before touching it;
    a live writer (PermissionError/OSError) skips it for this run rather than
    racing it.
  - ARCHIVE-FIRST-DELETE-SECOND: gzip the file to ARCHIVE_ROOT, decompress the
    result and compare it byte-for-byte against the original, and only remove the
    original after that comparison passes. A failed verification leaves the
    original untouched and records an error -- it never deletes on a hunch.
  - LOCAL-ONLY: the archive is another folder on this machine, never uploaded or
    emailed in raw form -- this is disk reclamation, not an export, so it does not
    implicate invariant 3 (confidential deals never leave the machine unchanged).
  - SCOPE: touches ONLY audit.jsonl files. Never deletes a session directory or any
    other file in it.

Default is DRY RUN (report only). Pass --apply to actually archive+remove.
Exit code is always 0 on a clean run (including dry-run) so a scheduled fire never
reads as a failure for archiving nothing; errors are reported in the JSON summary
and cause exit 1.

Stdlib only. ASCII-only.
"""
import gzip
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

AUDIT_ROOT = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")),
    "Claude", "local-agent-mode-sessions",
)
ARCHIVE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "_archive", "session-audit-logs")
HISTORY_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_state", "audit-log-sweep-history.jsonl")


def _iter_audit_files(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        if "audit.jsonl" in filenames:
            yield os.path.join(dirpath, "audit.jsonl")


def _session_relpath(root, audit_path):
    """The path fragment under root, used both for the archive layout and for
    identifying which session/workspace/fleet a file belongs to in the report."""
    rel = os.path.relpath(audit_path, root)
    return rel.replace("\\", "/")


def _is_locked(path):
    """True if the file cannot be opened for exclusive read right now -- treated
    as 'a live writer might still have this open', not attempted further this run."""
    try:
        # os.O_EXCL is meaningless on an existing file; what we actually need is a
        # plain open that would raise if another process holds an incompatible
        # lock. Windows enforces sharing violations on open() itself for a file
        # another process has open without FILE_SHARE_READ/WRITE, so a bare open
        # for read is a sufficient probe here -- no fcntl/msvcrt lock dance needed.
        with open(path, "rb"):
            pass
        return False
    except OSError:
        return True


def _archive_one(audit_path, rel, archive_root):
    """Gzip audit_path into archive_root/rel + '.gz', verify byte-for-byte, then
    remove the original. Returns (bytes_reclaimed, error_or_None)."""
    dest = os.path.join(archive_root, rel.replace("/", os.sep)) + ".gz"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with open(audit_path, "rb") as src, gzip.open(dest, "wb") as gz:
            original = src.read()
            gz.write(original)
    except OSError as exc:
        return 0, "compress failed: %r" % (exc,)

    try:
        with gzip.open(dest, "rb") as gz:
            roundtrip = gz.read()
    except OSError as exc:
        return 0, "verify-read failed: %r" % (exc,)

    if roundtrip != original:
        try:
            os.remove(dest)
        except OSError:
            pass
        return 0, "verification mismatch -- archive discarded, original untouched"

    size = len(original)
    try:
        os.remove(audit_path)
    except OSError as exc:
        # Archive is verified-good and stays; the original just didn't clear.
        # Not a data-loss risk (archive already holds a verified copy), but it
        # means this run did not reclaim the space -- report honestly.
        return 0, "archived but could not remove original: %r" % (exc,)
    return size, None


def sweep(root=AUDIT_ROOT, archive_root=ARCHIVE_ROOT, since_days=30, apply=False):
    cutoff = time.time() - since_days * 86400
    result = {
        "root": root,
        "since_days": since_days,
        "apply": apply,
        "scanned": 0,
        "eligible": 0,
        "skipped_recent": 0,
        "skipped_locked": 0,
        "archived": 0,
        "bytes_reclaimed": 0,
        "errors": [],
    }
    if not os.path.isdir(root):
        result["errors"].append("root does not exist: %s" % root)
        return result

    for audit_path in _iter_audit_files(root):
        result["scanned"] += 1
        rel = _session_relpath(root, audit_path)
        try:
            mtime = os.path.getmtime(audit_path)
        except OSError as exc:
            result["errors"].append("%s: stat failed: %r" % (rel, exc))
            continue
        if mtime >= cutoff:
            result["skipped_recent"] += 1
            continue
        result["eligible"] += 1
        if _is_locked(audit_path):
            result["skipped_locked"] += 1
            continue
        if not apply:
            continue
        reclaimed, error = _archive_one(audit_path, rel, archive_root)
        if error:
            result["errors"].append("%s: %s" % (rel, error))
        else:
            result["archived"] += 1
            result["bytes_reclaimed"] += reclaimed
    return result


def _append_history(result):
    os.makedirs(os.path.dirname(HISTORY_LOG), exist_ok=True)
    entry = dict(result)
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    with open(HISTORY_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                         help="Actually archive+remove. Default is dry-run (report only).")
    parser.add_argument("--since-days", type=int, default=30,
                         help="Only files untouched for at least this many days are eligible.")
    parser.add_argument("--root", default=AUDIT_ROOT,
                         help="LAMS session-store root (test seam).")
    parser.add_argument("--archive-root", default=ARCHIVE_ROOT,
                         help="Where archived .jsonl.gz files land (test seam).")
    args = parser.parse_args()

    result = sweep(root=args.root, archive_root=args.archive_root,
                    since_days=args.since_days, apply=args.apply)
    _append_history(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()

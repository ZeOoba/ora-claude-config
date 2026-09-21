#!/usr/bin/env python3
"""Age-gated sweep of leaked TEST fixtures in the shared temp dir. DRY RUN unless --apply.

Why it exists: test fixtures across ~64 test files left ~1.7M top-level entries in %TEMP%
(measured 2026-09-19; OI-119). git-prepush-hook-tests-gate.py now gives every test its own
private TEMP, so the leak stops growing -- this removes the backlog.

Safety model (deliberately conservative -- this deletes from a directory other programs share):
  * only names starting with a KNOWN test-fixture prefix (FIXTURE_PREFIXES); generic
    `tmpXXXXXXXX` names are never touched -- any program's mkdtemp() makes those.
  * only entries whose mtime is older than --min-age-days (default 7): a live test run or a
    live session's scratch is never that old.
  * top-level reparse points (symlink/junction) are unlinked, never followed; junctions
    INSIDE a fixture are unlinked, never descended into (shutil.rmtree semantics, asserted
    by the test).
  * an entry that cannot be deleted (locked, in use) is skipped, not forced.
  * refuses any --temp that is not the real temp dir (tempfile.gettempdir()) unless
    --allow-other-temp: matching is by name prefix, so pointing it at e.g. hooks/ would
    match production files such as eos-plan-gate.py (independent review, 2026-09-19).
  * refuses a temp path shorter than 3 components (after stripping a Win32 long-path prefix).
Usage: python sweep-test-temp.py [--apply] [--min-age-days N] [--max-seconds S] [--temp DIR]
"""
import argparse
import concurrent.futures
import json
import os
import shutil
import stat
import sys
import tempfile
import time

# Measured leakers (2026-09-19 census). Extend when a new fixture family shows up.
FIXTURE_PREFIXES = (
    "eos-", "cwg-", "cpg-", "lcg-", "oag-", "scg-", "scs-", "ces-", "pps-", "wgc-", "fsgd-",
    "dfor-", "cwd-sess-", "srn-", "cpr-sess-", "prg-", "tpm-test-", "mfu-", "tcp-sess-",
    "mut-", "mutant-", "fc-", "claim-restore-", "chg-sessions-", "cmf-", "wig-", "wcc-",
    "wwg-", "ael-warn-", "cdp-", "dsr-test-", "gdp-", "subidx-guard-", "unrelated-repo-",
    "orphan-guard-", "gitfixture-", "drift-probe-", "scale-a-", "scale-b-", "xref-", "cbp-",
    "ora-oi100-", "mcp-tasks-", "mcp-empty-", "gt-", "leak-census-",
    "fsmc_", "hgb_", "pw_", "mcs_test_", "fpz_", "mip_",
    # another repo's Node test suite (mkdtemp, 6-char suffix); same class of leak
    "debt-api-test-", "acq-api-test-",
)


def is_fixture_name(name):
    return name.startswith(FIXTURE_PREFIXES)


def _is_link(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def _force_rmtree(path):
    def _fix(func, p, *_):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_fix)
    else:
        shutil.rmtree(path, onerror=_fix)


def _remove(path):
    """True if the entry is gone afterwards."""
    try:
        if _is_link(path):
            os.rmdir(path) if os.path.isdir(path) else os.unlink(path)
        elif os.path.isdir(path):
            _force_rmtree(path)
        else:
            os.chmod(path, stat.S_IWRITE)
            os.unlink(path)
    except OSError:
        pass
    return not os.path.lexists(path)


def scan(temp, min_age_days, now=None):
    """(candidates, stats). Scans the top level of `temp` once."""
    now = time.time() if now is None else now
    cutoff = now - min_age_days * 86400
    cands, stats = [], {"entries": 0, "fixture_old": 0, "fixture_fresh": 0, "unclaimed": 0}
    with os.scandir(temp) as it:
        for e in it:
            stats["entries"] += 1
            if not is_fixture_name(e.name):
                stats["unclaimed"] += 1
                continue
            try:
                mtime = e.stat(follow_symlinks=False).st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                cands.append(e.path)
                stats["fixture_old"] += 1
            else:
                stats["fixture_fresh"] += 1
    return cands, stats


def _norm(path):
    p = os.path.abspath(path)
    for pre in ("\\?\\", "//?/"):
        if p.startswith(pre):
            p = p[len(pre):]
    return os.path.normcase(os.path.normpath(p))


def run(temp, apply=False, min_age_days=7.0, max_seconds=None, workers=4, log=print,
        allow_other_temp=False):
    temp = _norm(temp)
    if not allow_other_temp and temp != _norm(tempfile.gettempdir()):
        raise SystemExit("refusing: %r is not this machine's temp dir (%r); pass --allow-other-temp "
                         "only for a scratch directory you created" % (temp, _norm(tempfile.gettempdir())))
    if len([q for q in temp.replace("\\", "/").split("/") if q and not q.endswith(":")]) < 3:
        raise SystemExit("refusing: temp path %r is too shallow to sweep" % temp)
    t0 = time.time()
    cands, stats = scan(temp, min_age_days)
    stats.update(temp=temp, apply=apply, min_age_days=min_age_days,
                 scan_seconds=round(time.time() - t0, 1), removed=0, skipped_locked=0)
    log("scanned %d top-level entries in %.1fs: %d old fixtures (sweepable), %d fresh fixtures "
        "(kept), %d unclaimed (never touched)" % (stats["entries"], stats["scan_seconds"],
                                                  stats["fixture_old"], stats["fixture_fresh"],
                                                  stats["unclaimed"]))
    if not apply:
        log("DRY RUN -- nothing deleted. Re-run with --apply to remove the %d old fixtures."
            % stats["fixture_old"])
        return stats
    deadline = None if not max_seconds else time.time() + max_seconds
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for i, ok in enumerate(pool.map(_remove, cands), 1):
            stats["removed" if ok else "skipped_locked"] += 1
            if i % 5000 == 0:
                log("  ... %d/%d (%d removed, %d skipped)" % (i, len(cands), stats["removed"],
                                                             stats["skipped_locked"]))
            if deadline and time.time() > deadline:
                log("time budget reached; re-run to continue (idempotent)")
                break
    log("removed %d, skipped %d (locked/in use)" % (stats["removed"], stats["skipped_locked"]))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-age-days", type=float, default=7.0)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--temp", default=tempfile.gettempdir())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-other-temp", action="store_true")
    a = ap.parse_args(argv)
    stats = run(a.temp, a.apply, a.min_age_days, a.max_seconds, allow_other_temp=a.allow_other_temp)
    if a.json:
        print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())

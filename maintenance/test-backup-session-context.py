#!/usr/bin/env python3
"""Tests for backup-session-context.py.

House style matches the other maintenance test rigs: plain python, no pytest,
assert + print PASS, one main() runner, subprocess against the real script so
the CLI contract itself is what's under test (not an importable internal).

Every case runs fully sandboxed (temp source + temp local dir + temp mirror
dir) -- the rig must never touch the live session-context.md or the live
backup rotation.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "backup-session-context.py"
PY = sys.executable

# The scrub resolves its roster as <scrub>/../hooks/confidential-terms.json, and
# that roster is gitignored -- so a WORKTREE copy of the scrub has no roster and
# fails OPEN (prints "scan skipped (fail-open)" and still exits 0 "CLEAN").
# That gives both verdict branches real, unmocked components to test against:
#   - HERE/scrub-before-optin.py      -> roster absent  -> UNVERIFIED
#   - LIVE_SCRUB (the live install)   -> roster present -> CLEAN
LIVE_SCRUB = Path(r"C:\Users\Owner\.claude\maintenance\scrub-before-optin.py")
LIVE_ROSTER = Path(r"C:\Users\Owner\.claude\hooks\confidential-terms.json")


def run_backup(args, expect_rc=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PY, str(SCRIPT)] + args,
                       capture_output=True, text=True, env=env, timeout=120)
    if expect_rc is not None:
        assert r.returncode == expect_rc, (
            "expected rc=%d got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (expect_rc, r.returncode, r.stdout, r.stderr))
    return r


class Sandbox:
    """Temp source file + local rotation dir + mirror dir, all disposable."""

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="bsc-test-"))
        self.source = self.root / "session-context.md"
        self.local = self.root / "local"
        self.mirror = self.root / "mirror"
        self.source.write_text("# ORA Active Context\n\n- initial content\n",
                               encoding="utf-8")
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.root, ignore_errors=True)

    def args(self, *extra):
        return ["--source", str(self.source),
                "--local-dir", str(self.local),
                "--mirror-dir", str(self.mirror)] + list(extra)

    def snapshots(self):
        if not self.local.is_dir():
            return []
        return sorted(p for p in self.local.iterdir() if p.suffix == ".md")

    def mirrors(self):
        if not self.mirror.is_dir():
            return []
        return sorted(p for p in self.mirror.iterdir() if p.suffix == ".md")


def test_first_run_creates_snapshot_and_mirror():
    with Sandbox() as sb:
        r = run_backup(sb.args(), expect_rc=0)
        snaps = sb.snapshots()
        assert len(snaps) == 1, "expected exactly 1 snapshot, got %d\n%s" % (len(snaps), r.stdout)
        assert snaps[0].read_text(encoding="utf-8") == sb.source.read_text(encoding="utf-8"), \
            "snapshot content must match the source byte-for-byte"
        mirrors = sb.mirrors()
        assert len(mirrors) == 1, "expected the mirror copy, got %d\n%s" % (len(mirrors), r.stdout)
        assert mirrors[0].read_text(encoding="utf-8") == sb.source.read_text(encoding="utf-8")
    print("  PASS test_first_run_creates_snapshot_and_mirror")


def test_unchanged_content_is_a_noop():
    """Re-running with identical content must NOT mint a second snapshot.

    Same trap as the portfolio.json generatedAt churn: a backup that rewrites
    on every fire produces noise no one reads and buries the real changes."""
    with Sandbox() as sb:
        run_backup(sb.args(), expect_rc=0)
        r = run_backup(sb.args(), expect_rc=0)
        assert len(sb.snapshots()) == 1, \
            "unchanged content must not create a second snapshot:\n%s" % r.stdout
        assert "unchanged" in r.stdout.lower(), \
            "the no-op must say so explicitly:\n%s" % r.stdout
    print("  PASS test_unchanged_content_is_a_noop (no churn)")


def test_changed_content_creates_new_snapshot():
    with Sandbox() as sb:
        run_backup(sb.args(), expect_rc=0)
        time.sleep(1.1)  # timestamped filenames are second-resolution
        sb.source.write_text("# ORA Active Context\n\n- CHANGED\n", encoding="utf-8")
        run_backup(sb.args(), expect_rc=0)
        snaps = sb.snapshots()
        assert len(snaps) == 2, "expected 2 snapshots after a real change, got %d" % len(snaps)
        assert "CHANGED" in snaps[-1].read_text(encoding="utf-8"), \
            "newest snapshot must carry the new content"
        assert "initial content" in snaps[0].read_text(encoding="utf-8"), \
            "the older snapshot must still hold the PRIOR content -- that is the whole point"
    print("  PASS test_changed_content_creates_new_snapshot (history preserved)")


def test_retention_prunes_oldest_only():
    with Sandbox() as sb:
        for i in range(4):
            sb.source.write_text("rev %d\n" % i, encoding="utf-8")
            run_backup(sb.args("--retain", "2"), expect_rc=0)
            time.sleep(1.1)
        snaps = sb.snapshots()
        assert len(snaps) == 2, "retain=2 must leave exactly 2, got %d" % len(snaps)
        bodies = [p.read_text(encoding="utf-8") for p in snaps]
        assert "rev 3" in bodies[-1], "newest must survive pruning"
        assert "rev 0" not in "".join(bodies), "oldest must be pruned"
    print("  PASS test_retention_prunes_oldest_only")


def test_missing_source_fails_loudly():
    """A vanished source must be a LOUD failure, never a silent success that
    quietly stops protecting the file (verified-null vs inferred-null)."""
    with Sandbox() as sb:
        sb.source.unlink()
        r = run_backup(sb.args(), expect_rc=1)
        combined = (r.stdout + r.stderr).lower()
        assert "source" in combined and ("missing" in combined or "not found" in combined), \
            "must name the missing source:\n%s\n%s" % (r.stdout, r.stderr)
        assert sb.snapshots() == [], "a failed run must not leave a partial snapshot"
    print("  PASS test_missing_source_fails_loudly")


def test_empty_source_is_refused():
    """A zero-byte source is almost certainly a truncation in progress -- backing
    it up would spend a rotation slot on the damage and, at retain=N, is the
    mechanism by which good history gets pushed out."""
    with Sandbox() as sb:
        run_backup(sb.args(), expect_rc=0)          # bank one good snapshot
        sb.source.write_text("", encoding="utf-8")
        r = run_backup(sb.args(), expect_rc=1)
        assert len(sb.snapshots()) == 1, \
            "an empty source must not add a snapshot:\n%s" % r.stdout
        assert "initial content" in sb.snapshots()[0].read_text(encoding="utf-8"), \
            "the good prior snapshot must survive"
    print("  PASS test_empty_source_is_refused (truncation guard)")


def test_scrub_verdict_clean_is_recorded():
    """With a real roster reachable, a benign source records a VERIFIED clean."""
    if not (LIVE_SCRUB.is_file() and LIVE_ROSTER.is_file()):
        print("  SKIP test_scrub_verdict_clean_is_recorded (live scrub/roster absent)")
        return
    with Sandbox() as sb:
        r = run_backup(sb.args("--scrub", str(LIVE_SCRUB)), expect_rc=0)
        assert "scrub" in r.stdout.lower(), "the run must report a scrub verdict:\n%s" % r.stdout
        ledger = sb.local / "backup-log.txt"
        assert ledger.is_file(), "expected a durable verdict ledger next to the snapshots"
        body = ledger.read_text(encoding="utf-8").upper()
        assert "CLEAN" in body, "a benign fixture with a live roster must record CLEAN:\n%s" % body
        assert "UNVERIFIED" not in body, \
            "a reachable roster must NOT be downgraded to UNVERIFIED:\n%s" % body
    print("  PASS test_scrub_verdict_clean_is_recorded")


def test_unverifiable_scrub_is_never_recorded_as_clean():
    """The load-bearing case. The scrub fails OPEN when its roster is missing:
    it prints 'scan skipped (fail-open)' and still exits 0 saying CLEAN. Taking
    that at face value would record 'no confidential terms' when the truth is
    'nobody looked' -- a verified-null vs inferred-null failure. The verdict
    must degrade to UNVERIFIED and must not contain the word CLEAN."""
    scrub_roster = HERE.parent / "hooks" / "confidential-terms.json"
    assert not scrub_roster.is_file(), (
        "this test needs the worktree roster to be ABSENT (it is gitignored); "
        "found one at %s -- the fail-open branch is no longer being exercised"
        % scrub_roster)
    with Sandbox() as sb:
        r = run_backup(sb.args("--scrub", str(HERE / "scrub-before-optin.py")), expect_rc=0)
        ledger = (sb.local / "backup-log.txt").read_text(encoding="utf-8").upper()
        assert "UNVERIFIED" in ledger, \
            "a fail-open scrub must record UNVERIFIED:\n%s" % ledger
        assert "CLEAN" not in ledger, \
            "a fail-open scrub must NEVER be recorded as CLEAN:\n%s" % ledger
        combined = (r.stdout + r.stderr).lower()
        assert "unverified" in combined, \
            "the run must say out loud that the scan was not verifiable:\n%s" % r.stdout
    print("  PASS test_unverifiable_scrub_is_never_recorded_as_clean (no inferred nulls)")


def test_missing_scrub_script_is_unverified_not_clean():
    with Sandbox() as sb:
        r = run_backup(sb.args("--scrub", str(sb.root / "no-such-scrub.py")), expect_rc=0)
        ledger = (sb.local / "backup-log.txt").read_text(encoding="utf-8").upper()
        assert "UNVERIFIED" in ledger and "CLEAN" not in ledger, \
            "an absent scrub must record UNVERIFIED, never CLEAN:\n%s" % ledger
        assert len(sb.snapshots()) == 1, \
            "an unverifiable scrub must not block the backup itself:\n%s" % r.stdout
    print("  PASS test_missing_scrub_script_is_unverified_not_clean")


def test_mirror_failure_is_nonfatal():
    """OneDrive can be offline/locked. Losing the mirror must not cost us the
    LOCAL snapshot -- degrade to local-only and say so, never abort."""
    with Sandbox() as sb:
        # A regular file where the mirror DIR should be -> mkdir/copy must fail.
        sb.mirror.write_text("not a directory", encoding="utf-8")
        r = run_backup(sb.args(), expect_rc=0)
        assert len(sb.snapshots()) == 1, \
            "local snapshot must still be taken when the mirror fails:\n%s" % r.stdout
        combined = (r.stdout + r.stderr).lower()
        assert "mirror" in combined, "the mirror failure must be reported:\n%s" % r.stdout
    print("  PASS test_mirror_failure_is_nonfatal (degrades to local-only)")


def test_source_is_never_modified():
    with Sandbox() as sb:
        before = sb.source.read_bytes()
        run_backup(sb.args(), expect_rc=0)
        assert sb.source.read_bytes() == before, \
            "the backup must be strictly read-only on the source"
    print("  PASS test_source_is_never_modified (read-only on source)")


def main():
    assert SCRIPT.is_file(), "missing script under test: %s" % SCRIPT
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print("ALL BACKUP-SESSION-CONTEXT TESTS PASS (%d)" % len(tests))


if __name__ == "__main__":
    main()

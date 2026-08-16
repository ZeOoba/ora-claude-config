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

# The scrub resolves its roster as <scrub>/../hooks/confidential-terms.json.
# Whether HERE's sibling roster exists depends on the checkout (gitignored, so
# absent in a fresh worktree but legitimately PRESENT in the production
# install) -- so the roster-absent branch is exercised against an ISOLATED
# staged copy (stage_scrub_tree with roster_body=None), never against HERE.
# That gives both verdict branches real, unmocked components to test against:
#   - staged scrub, no roster staged  -> roster absent  -> UNVERIFIED
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
        # Windows holds briefly-locked files (AV/indexer) right after a
        # subprocess exits, and a bare ignore_errors=True leaves the tree behind
        # forever -- an unbounded temp leak from a rig meant to run on a
        # schedule. Retry a few times, then give up loudly rather than silently.
        for attempt in range(5):
            shutil.rmtree(self.root, ignore_errors=(attempt < 4))
            if not self.root.exists():
                return
            time.sleep(0.2)
        print("  WARN sandbox not fully removed: %s" % self.root, file=sys.stderr)

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


def test_missing_roster_is_never_recorded_as_clean():
    """Roster ABSENT -> UNVERIFIED via the early return, before the scrub is even
    launched.

    Naming/docstring corrected 2026-08-09: this previously claimed to exercise
    the scrub's fail-open path ('scan skipped (fail-open)' at exit 0). It never
    did -- the roster-existence check returns first, so no subprocess ran, and
    FAIL_OPEN_MARKERS had zero coverage while the suite's headline test appeared
    to guard it. That branch is now covered by
    test_corrupt_roster_hits_the_fail_open_branch, which stages a roster that is
    PRESENT but unparseable. This test keeps the weaker property it actually
    pins."""
    with Sandbox() as sb:
        # Environment decoupled 2026-08-15: the old version ran the LIVE scrub at HERE
        # and ASSERTED the live checkout's hooks/confidential-terms.json did not exist
        # -- true only in a fresh worktree, so in the production checkout (roster
        # legitimately present) the precondition itself failed before the behavioral
        # assertions ever ran. Staging an isolated tree with roster_body=None makes the
        # staged copy's <scrub>/../hooks/confidential-terms.json resolution absent by
        # construction, regardless of what the live checkout looks like.
        staged = stage_scrub_tree(sb.root / "staged", None)
        if staged is None:
            print("  SKIP test_missing_roster_is_never_recorded_as_clean (live sources absent)")
            return
        assert not (sb.root / "staged" / "hooks" / "confidential-terms.json").is_file(), \
            "staging with roster_body=None must leave the staged roster ABSENT"
        r = run_backup(sb.args("--scrub", str(staged)), expect_rc=0)
        ledger = (sb.local / "backup-log.txt").read_text(encoding="utf-8").upper()
        assert "UNVERIFIED" in ledger, \
            "a roster-absent scrub must record UNVERIFIED:\n%s" % ledger
        assert "CLEAN" not in ledger, \
            "a roster-absent scrub must NEVER be recorded as CLEAN:\n%s" % ledger
        combined = (r.stdout + r.stderr).lower()
        assert "unverified" in combined, \
            "the run must say out loud that the scan was not verifiable:\n%s" % r.stdout
    print("  PASS test_missing_roster_is_never_recorded_as_clean (early return, isolated tree)")


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


def stage_scrub_tree(root, roster_body):
    """Build a minimal REAL scrub install under `root` with a roster we control:
        root/maintenance/{scrub-before-optin.py, doctrine-integrity-probe.py}
        root/hooks/{confidential-terms.json, lib/secret_patterns.py}
    The scrub resolves its roster as <scrub>/../hooks/confidential-terms.json, so
    staging is the only way to exercise a roster that is PRESENT but unusable --
    the fail-open branch a roster-existence check can never reach.
    roster_body=None stages everything EXCEPT the roster file itself, so the
    staged copy's roster resolution is guaranteed ABSENT no matter what the live
    checkout's real roster looks like (the roster-missing early return).
    Returns the staged scrub path, or None if the live sources are unavailable."""
    live_maint = Path(r"C:\Users\Owner\.claude\maintenance")
    live_lib = Path(r"C:\Users\Owner\.claude\hooks\lib\secret_patterns.py")
    needed = [live_maint / "scrub-before-optin.py",
              live_maint / "doctrine-integrity-probe.py", live_lib]
    if not all(p.is_file() for p in needed):
        return None
    (root / "maintenance").mkdir(parents=True, exist_ok=True)
    (root / "hooks" / "lib").mkdir(parents=True, exist_ok=True)
    for src in needed[:2]:
        shutil.copy2(str(src), str(root / "maintenance" / src.name))
    shutil.copy2(str(live_lib), str(root / "hooks" / "lib" / "secret_patterns.py"))
    if roster_body is not None:
        (root / "hooks" / "confidential-terms.json").write_text(roster_body, encoding="utf-8")
    return root / "maintenance" / "scrub-before-optin.py"


def test_undecodable_target_is_unverified_not_clean():
    """REGRESSION -- the 2026-08-09 review's Critical.

    scan_file_for_terms returns None and scan_file_for_secrets returns [] for a
    file they cannot decode, both SILENTLY. The scrub then prints
    '0 hits, 0 secret-pattern hits, 0 warning(s)' and exits 0 -- so exit code and
    fail-open markers BOTH say clean while the file was never scanned. Before the
    fix this recorded 'CLEAN (scrub exit 0, roster reachable)' for content that
    had not been looked at."""
    if not (LIVE_SCRUB.is_file() and LIVE_ROSTER.is_file()):
        print("  SKIP test_undecodable_target_is_unverified_not_clean (live scrub absent)")
        return
    with Sandbox() as sb:
        # Undecodable by the scanner's whole ladder (utf-8 -> utf-16 -> cp1252).
        sb.source.write_bytes(b"# ORA Active Context\n\n- SENSITIVE\x81\x8d\x8f\x90\x9d\n")
        r = run_backup(sb.args("--scrub", str(LIVE_SCRUB)), expect_rc=0)
        ledger = (sb.local / "backup-log.txt").read_text(encoding="utf-8").upper()
        assert "UNVERIFIED" in ledger, \
            "an unscannable target must record UNVERIFIED:\n%s" % ledger
        assert "CLEAN" not in ledger, \
            "an unscannable target must NEVER be recorded CLEAN:\n%s" % ledger
        assert len(sb.snapshots()) == 1, "the snapshot itself must still be taken"
        assert "unverified" in (r.stdout + r.stderr).lower()
    print("  PASS test_undecodable_target_is_unverified_not_clean (Critical regression)")


def test_corrupt_roster_hits_the_fail_open_branch():
    """The branch a roster-EXISTENCE check cannot reach: roster present but
    unparseable -> the scrub warns 'scan skipped (fail-open)' and exits 0 CLEAN.
    This is the only test that exercises FAIL_OPEN_MARKERS end-to-end."""
    with Sandbox() as sb:
        staged = stage_scrub_tree(sb.root / "staged", "{ this is not json")
        if staged is None:
            print("  SKIP test_corrupt_roster_hits_the_fail_open_branch (live sources absent)")
            return
        run_backup(sb.args("--scrub", str(staged)), expect_rc=0)
        body = (sb.local / "backup-log.txt").read_text(encoding="utf-8")
        assert "UNVERIFIED" in body.upper(), "a corrupt roster must record UNVERIFIED:\n%s" % body
        assert "CLEAN" not in body.upper(), "must never record CLEAN:\n%s" % body
        assert "fail-open" in body.lower(), (
            "the detail must show the FAIL-OPEN branch was the one taken (not the "
            "roster-missing early return):\n%s" % body)
    print("  PASS test_corrupt_roster_hits_the_fail_open_branch (marker logic covered)")


def test_scrub_fail_open_wording_is_still_coupled():
    """FAIL_OPEN_MARKERS matches the helper's free text. Nothing stops a reword
    of scrub-before-optin.py from silently turning every fail-open into CLEAN,
    so pin the coupling here: this test fails instead."""
    if not LIVE_SCRUB.is_file():
        print("  SKIP test_scrub_fail_open_wording_is_still_coupled (live scrub absent)")
        return
    helper = LIVE_SCRUB.read_text(encoding="utf-8", errors="replace").lower()
    script = SCRIPT.read_text(encoding="utf-8")
    markers = [m for m in ("fail-open", "scan skipped") if '"%s"' % m in script]
    assert markers, "could not find FAIL_OPEN_MARKERS literals in the script"
    for m in markers:
        assert m in helper, (
            "backup-session-context.py matches on %r but scrub-before-optin.py no "
            "longer emits it -- every fail-open would now be recorded CLEAN. "
            "Update FAIL_OPEN_MARKERS (or switch to a machine-readable verdict)." % m)
    print("  PASS test_scrub_fail_open_wording_is_still_coupled (text coupling pinned)")


def test_crashed_scrub_is_unverified_not_hits():
    """A non-zero exit without the findings banner is a broken scanner, not a
    detection. Filing it as HITS makes 'found terms' and 'scanner is dead'
    indistinguishable forever."""
    with Sandbox() as sb:
        (sb.root / "hooks").mkdir(parents=True, exist_ok=True)
        (sb.root / "hooks" / "confidential-terms.json").write_text("{}", encoding="utf-8")
        (sb.root / "maintenance").mkdir(parents=True, exist_ok=True)
        # A "scrub" that dies on import, like a real traceback would.
        (sb.root / "maintenance" / "scrub-before-optin.py").write_text(
            "import sys\nsys.stderr.write('Traceback: boom\\n')\nsys.exit(1)\n",
            encoding="utf-8")
        # read_optional comes from the sibling probe; stub it so the pre-check passes.
        (sb.root / "maintenance" / "doctrine-integrity-probe.py").write_text(
            "def read_optional(p):\n"
            "    try:\n"
            "        return open(p, encoding='utf-8').read(), None\n"
            "    except Exception as e:\n"
            "        return None, str(e)\n",
            encoding="utf-8")
        run_backup(sb.args("--scrub", str(sb.root / "maintenance" / "scrub-before-optin.py")),
                   expect_rc=0)
        body = (sb.local / "backup-log.txt").read_text(encoding="utf-8").upper()
        assert "UNVERIFIED" in body, "a crashed scrub must record UNVERIFIED:\n%s" % body
        assert "HITS" not in body, "a crashed scrub must NOT be recorded as HITS:\n%s" % body
    print("  PASS test_crashed_scrub_is_unverified_not_hits")


def test_same_second_collision_never_overwrites():
    """Two content-distinct runs inside one second must not land on the same
    filename. Overwriting would destroy good history in a tool that exists to
    retain it -- and would leave the ledger claiming two snapshots for one file."""
    with Sandbox() as sb:
        sb.source.write_text("REVISION ONE - the good history\n", encoding="utf-8")
        run_backup(sb.args(), expect_rc=0)
        sb.source.write_text("REVISION TWO\n", encoding="utf-8")
        run_backup(sb.args(), expect_rc=0)          # deliberately NO sleep
        snaps = sb.snapshots()
        assert len(snaps) == 2, \
            "expected 2 distinct snapshots within one second, got %d: %s" \
            % (len(snaps), [p.name for p in snaps])
        bodies = "".join(p.read_text(encoding="utf-8") for p in snaps)
        assert "REVISION ONE - the good history" in bodies, \
            "the earlier snapshot was overwritten -- history lost"
        assert "REVISION TWO" in bodies
        assert "REVISION TWO" in snaps[-1].read_text(encoding="utf-8"), \
            "sort order must still put the NEWER snapshot last, or retention " \
            "will prune the wrong one"
    print("  PASS test_same_second_collision_never_overwrites (history + sort order)")


def test_mirror_catches_up_after_a_failure():
    """The failure the mirror is documented to tolerate must not become
    permanent. If a run cannot mirror and the content then stops changing, every
    later run says 'unchanged' -- and the off-machine copy, the leg that
    survives losing the machine, never appears."""
    with Sandbox() as sb:
        sb.mirror.write_text("not a directory", encoding="utf-8")   # force failure
        run_backup(sb.args(), expect_rc=0)
        assert len(sb.snapshots()) == 1 and not sb.mirror.is_dir()
        sb.mirror.unlink()                                          # OneDrive returns
        r = run_backup(sb.args(), expect_rc=0)                      # content UNCHANGED
        assert len(sb.mirrors()) == 1, \
            "the unchanged path must catch the mirror up, not skip it:\n%s" % r.stdout
        assert sb.mirrors()[0].read_text(encoding="utf-8") == \
            sb.source.read_text(encoding="utf-8")
        assert "catch" in r.stdout.lower(), "the repair must be reported:\n%s" % r.stdout
    print("  PASS test_mirror_catches_up_after_a_failure")


def test_ledger_is_mirrored():
    """A verdict ledger that dies with the machine leaves every recovered
    snapshot with exactly the comforting blank it exists to prevent."""
    with Sandbox() as sb:
        run_backup(sb.args(), expect_rc=0)
        mirrored = sb.mirror / "backup-log.txt"
        assert mirrored.is_file(), "the ledger must reach the mirror too"
        assert (sb.local / "backup-log.txt").read_text(encoding="utf-8") == \
            mirrored.read_text(encoding="utf-8")
    print("  PASS test_ledger_is_mirrored")


def test_retain_zero_is_rejected():
    with Sandbox() as sb:
        r = run_backup(sb.args("--retain", "0"), expect_rc=2)
        assert "retain" in (r.stdout + r.stderr).lower(), \
            "must say which argument was rejected:\n%s\n%s" % (r.stdout, r.stderr)
    print("  PASS test_retain_zero_is_rejected")


def main():
    assert SCRIPT.is_file(), "missing script under test: %s" % SCRIPT
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print("ALL BACKUP-SESSION-CONTEXT TESTS PASS (%d)" % len(tests))


if __name__ == "__main__":
    main()

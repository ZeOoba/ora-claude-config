#!/usr/bin/env python3
"""Pin: audit-log-sweep.py's gzip archive of LAMS/Cowork session transcripts is never
tracked by git.

WHY (2026-11-08): maintenance/audit-log-sweep.py --apply (scheduled task
ora-audit-log-sweep, monthly) gzips every stale per-session audit.jsonl -- a full
tool-call transcript, which can carry roster terms and credentials -- into
maintenance/_archive/session-audit-logs/<...>/audit.jsonl.gz. Nothing ignored that
directory, so the dirty-tree triage commit 927d1c0e on live/primary-checkout
("track settled archive records", 2026-11-04) swept 13 of them into git. The
confidentiality pre-push scan could not see inside .gz until #427. The archive is
local-only disk reclamation by design (the script's own LOCAL-ONLY safety note), so
it must stay one `git add -A` away from nothing.

Checks use `git check-ignore --no-index` against THIS checkout's .gitignore, so an
already-tracked copy on another branch cannot mask a missing rule. Exit 1 means a
rule is not ignored; 128 is a git error and must not read as a pass.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SWEEP = os.path.join(ROOT, "maintenance", "audit-log-sweep.py")

SAMPLE = ("a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3/583f08bc-0123-4111-8158-8fe3d927e350/"
          "local_1ae3a9d0-73b4-4cfc-a882-697dba3de1ba/audit.jsonl.gz")


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def ignored(rel):
    rc, out = git("check-ignore", "-q", "--no-index", rel)
    assert rc != 128, "git check-ignore errored on %s: %s" % (rel, out)
    return rc == 0


def sweep_archive_rel():
    """The archive root as audit-log-sweep.py itself computes it, relative to the repo
    root -- so moving ARCHIVE_ROOT without moving the ignore rule fails here."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_log_sweep", SWEEP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return os.path.relpath(mod.ARCHIVE_ROOT, ROOT).replace("\\", "/")


def test_sweep_archive_root_is_ignored():
    rel = sweep_archive_rel()
    assert rel == "maintenance/_archive/session-audit-logs", rel
    for p in (rel + "/" + SAMPLE,
              rel + "/x/audit.jsonl.gz",
              rel + "/anything-else.txt"):
        assert ignored(p), "%s is NOT git-ignored" % p


def test_audit_transcript_gz_ignored_anywhere():
    """A relocated archive (or a hand copy) must not slip through either."""
    for p in ("maintenance/_archive/2026-12-01_moved/" + SAMPLE,
              "projects/some-project/audit.jsonl.gz",
              "audit.jsonl.gz"):
        assert ignored(p), "%s is NOT git-ignored" % p


def test_dirty_tree_snapshot_tarballs_ignored():
    """Same 2026-11-04 triage (cf2591ba) tracked a .tgz snapshot of a dirty tree; the
    #427 compressed scan flags a credential-shaped string inside it. origin/main tracks
    no .tgz; none should ever be tracked."""
    for p in ("maintenance/_state/_archive/2026-10-17_scratch-triage/r27-baseline/claude-dirty-snapshot.tgz",
              "anywhere/else/snapshot.tgz"):
        assert ignored(p), "%s is NOT git-ignored" % p


def test_rule_is_not_too_broad():
    """Control: the rest of maintenance/_archive/ and ordinary maintenance files stay
    trackable, so the checks above are not passing because of a blanket rule."""
    for p in ("maintenance/_archive/2026-09-22_checkout-sync/CLAUDE.md",
              "maintenance/_archive/session-audit-logs-README.md",
              "maintenance/audit-log-sweep.py",
              "maintenance/_state/audit-log-sweep-history.jsonl.example"):
        assert not ignored(p), "%s is git-ignored -- a rule is too broad" % p


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print("PASS %s" % t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL %s: %s" % (t.__name__, e))
    print("\nsession-audit archive ignore tests: %d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

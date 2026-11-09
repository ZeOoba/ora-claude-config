"""push-live-backup.py pure-unit checks: push classifier, gate precondition, beacons,
off-box verdict. No git network, no pushes.

The git-heavy suite (real bare remote, real pre-push hook, lease, containment) lives in
_tests/integration/test_push_live_backup_git.py, which the pre-push hook-tests gate does
not discover (same reason as safe-push's: git-spawn suites blow the 240s per-file budget
under load). Run it by hand after any change to push-live-backup.py:
    python maintenance/_tests/integration/test_push_live_backup_git.py
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "push-live-backup.py")

_spec = importlib.util.spec_from_file_location("push_live_backup", TOOL)
plb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plb)

def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _json(p):
    return json.loads(_read(p))


TARGET = "refs/heads/backup/live-primary"
HDR = "To https://github.com/x/y.git\n"


def porcelain(flag, summary):
    return HDR + "%s\tf00:%s\t%s\nDone\n" % (flag, TARGET, summary)


class ClassifyPushTest(unittest.TestCase):
    def test_success_flags(self):
        self.assertEqual(plb.classify_push(0, porcelain("*", "[new branch]"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain("+", "a..b (forced update)"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain(" ", "a..b"), TARGET), "PUSHED")
        self.assertEqual(plb.classify_push(0, porcelain("=", "[up to date]"), TARGET), "UP_TO_DATE")

    def test_lease_rejection_is_its_own_verdict(self):
        self.assertEqual(plb.classify_push(1, porcelain("!", "[rejected] (stale info)"), TARGET), "LEASE_REJECTED")

    def test_other_rejections(self):
        self.assertEqual(plb.classify_push(1, porcelain("!", "[remote rejected] (protected branch hook declined)"), TARGET), "REJECTED")
        self.assertEqual(plb.classify_push(1, porcelain("!", "[rejected] (fetch first)"), TARGET), "REJECTED")

    def test_gate_block_has_no_status_block(self):
        # pre-push hook exit 1: git prints no porcelain status for the ref at all
        out = "confidential-scan: BLOCKED (deal #2, 1 hit)\nerror: failed to push some refs to 'x'\n"
        self.assertEqual(plb.classify_push(1, out, TARGET), "BLOCKED_OR_FAILED")

    def test_status_shaped_text_before_header_is_ignored(self):
        # a gate's own log can contain status-shaped lines; only git's block after "To <url>" counts
        gate = "*\tf00:%s\t[new branch]\n" % TARGET
        self.assertEqual(plb.classify_push(1, gate + "error: failed to push\n", TARGET), "BLOCKED_OR_FAILED")
        self.assertEqual(plb.classify_push(0, gate, TARGET), "BLOCKED_OR_FAILED")

    def test_rc_zero_with_rejected_line_is_not_success(self):
        self.assertEqual(plb.classify_push(0, porcelain("!", "[rejected] (stale info)"), TARGET), "LEASE_REJECTED")

    def test_other_ref_line_is_ignored(self):
        out = HDR + "*\tf00:refs/heads/other\t[new branch]\nDone\n"
        self.assertEqual(plb.classify_push(0, out, TARGET), "BLOCKED_OR_FAILED")


class PushArgvTest(unittest.TestCase):
    def test_argv_uses_explicit_lease_and_never_skips_hooks(self):
        argv = plb.push_argv("origin", "a" * 40, TARGET, "b" * 40)
        self.assertIn("--force-with-lease=%s:%s" % (TARGET, "b" * 40), argv)
        self.assertIn("%s:%s" % ("a" * 40, TARGET), argv)
        self.assertIn("--porcelain", argv)
        for bad in ("--no-verify", "-n", "--force", "-f", "--mirror", "--all"):
            self.assertNotIn(bad, argv)

    def test_absent_remote_ref_leases_on_nonexistence(self):
        argv = plb.push_argv("origin", "a" * 40, TARGET, None)
        self.assertIn("--force-with-lease=%s:" % TARGET, argv)

    def test_source_never_contains_no_verify(self):
        src = _read(TOOL)
        code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        # the literal may appear in prose (docstring) but never as an argv element
        self.assertNotIn('"--no-verify"', code)
        self.assertNotIn("'--no-verify'", code)


class GatePreconditionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="plb-unit-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.hooks = os.path.join(self.root, "githooks")
        os.makedirs(self.hooks)
        os.makedirs(os.path.join(self.root, "hooks"))

    def _write(self, rel, text):
        p = os.path.join(self.root, rel)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)

    def _good(self):
        self._write("githooks/pre-push", '#!/bin/sh\npython "$ROOT/hooks/git-prepush-confidential-scan.py" "$@" <"$REFS"\n')
        self._write("hooks/git-prepush-confidential-scan.py", "def scan_compressed(rng, terms):\n    pass\n\nhits = scan_compressed(r, t)\n")

    def test_ok(self):
        self._good()
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertTrue(ok, why)

    def test_missing_pre_push(self):
        self._good()
        os.remove(os.path.join(self.hooks, "pre-push"))
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)
        self.assertIn("pre-push", why)

    def test_pre_push_without_confidential_scan(self):
        self._good()
        self._write("githooks/pre-push", "#!/bin/sh\nexit 0\n")
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)
        self.assertIn("confidential", why)

    def test_scan_without_compressed_scan(self):
        # the live branch's state on 2026-11-08: scan present, #427's compressed scan absent
        self._good()
        self._write("hooks/git-prepush-confidential-scan.py", "def main():\n    pass\n")
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)
        self.assertIn("scan_compressed", why)

    def test_scan_defines_but_never_calls_compressed_scan(self):
        self._good()
        self._write("hooks/git-prepush-confidential-scan.py", "def scan_compressed(rng, terms):\n    pass\n")
        ok, why = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)

    def test_scan_file_missing(self):
        self._good()
        os.remove(os.path.join(self.root, "hooks", "git-prepush-confidential-scan.py"))
        ok, _ = plb.gate_precondition(self.root, self.hooks)
        self.assertFalse(ok)


class BeaconTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="plb-beacon-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.ok = os.path.join(self.d, plb.OK_STAMP)
        self.failed = os.path.join(self.d, plb.FAILED_MARKER)

    def test_failure_writes_marker_and_keeps_ok_stamp(self):
        plb.write_beacon(self.d, True, {"verdict": "PUSHED", "sha": "a"})
        before = _read(self.ok)
        plb.write_beacon(self.d, False, {"verdict": "BLOCKED_OR_FAILED", "sha": "b"})
        self.assertTrue(os.path.exists(self.failed))
        self.assertEqual(_json(self.failed)["verdict"], "BLOCKED_OR_FAILED")
        self.assertEqual(_read(self.ok), before)  # last success preserved

    def test_success_clears_marker(self):
        plb.write_beacon(self.d, False, {"verdict": "REJECTED"})
        plb.write_beacon(self.d, True, {"verdict": "PUSHED"})
        self.assertFalse(os.path.exists(self.failed))
        self.assertEqual(_json(self.ok)["verdict"], "PUSHED")

    def test_beacon_carries_timestamp(self):
        plb.write_beacon(self.d, False, {"verdict": "X"})
        self.assertIn("ts", _json(self.failed))

    def test_creates_missing_state_dir(self):
        sub = os.path.join(self.d, "nested", "_state")
        self.assertTrue(plb.write_beacon(sub, False, {"verdict": "X"}))
        self.assertTrue(os.path.exists(os.path.join(sub, plb.FAILED_MARKER)))

    def test_never_raises(self):
        # a file where the directory should be: write fails, returns False, does not raise
        blocker = os.path.join(self.d, "blocker")
        open(blocker, "w").close()
        self.assertFalse(plb.write_beacon(os.path.join(blocker, "x"), False, {"verdict": "X"}))


class OffboxVerdictTest(unittest.TestCase):
    NOW = 1_800_000_000

    def test_contained(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual((v["verdict"], v["rc"]), ("CONTAINED", 0))

    def test_pending_within_grace(self):
        v = plb.offbox_verdict(pending_times=[self.NOW - 3600, self.NOW - 7200], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual((v["verdict"], v["rc"]), ("PENDING_WITHIN_GRACE", 0))
        self.assertEqual(v["pending_count"], 2)

    def test_not_offbox_past_grace_keys_on_oldest(self):
        v = plb.offbox_verdict(pending_times=[self.NOW - 3600, self.NOW - 30 * 3600], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual((v["verdict"], v["rc"]), ("NOT_OFFBOX", 1))
        self.assertAlmostEqual(v["oldest_pending_hours"], 30.0, places=1)

    def test_future_dated_commit_does_not_hide_an_old_one(self):
        v = plb.offbox_verdict(pending_times=[self.NOW + 99999, self.NOW - 40 * 3600], now=self.NOW, grace_hours=26, failed_marker=None)
        self.assertEqual(v["rc"], 1)

    def test_failed_marker_alarms_even_when_contained(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26,
                               failed_marker={"verdict": "BLOCKED_OR_FAILED", "ts": "2026-11-08T00:00:00Z"})
        self.assertEqual(v["rc"], 1)
        self.assertIn("BACKUP_PUSH_FAILED", v["problems"][0])

    def test_unreadable_failed_marker_is_a_problem_not_a_pass(self):
        v = plb.offbox_verdict(pending_times=[], now=self.NOW, grace_hours=26, failed_marker={"_unreadable": True})
        self.assertEqual(v["rc"], 1)


class BeaconsIgnoredTest(unittest.TestCase):
    """A tracked outage marker or a daily-changing stamp would be committed by the next
    `git add -A` sweep; both beacons (and their atomic-write .tmp) must be git-ignored."""
    def test_beacons_are_git_ignored(self):
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for name in (plb.OK_STAMP, plb.FAILED_MARKER, plb.OK_STAMP + ".tmp", plb.FAILED_MARKER + ".tmp"):
            rel = "maintenance/_state/" + name
            p = subprocess.run(["git", "-C", root, "check-ignore", "-q", "--no-index", rel])
            self.assertNotEqual(p.returncode, 128, "git check-ignore errored on " + rel)
            self.assertEqual(p.returncode, 0, rel + " is NOT git-ignored")


if __name__ == "__main__":
    unittest.main(verbosity=1)

"""push-live-backup.py end-to-end against real git: a bare 'remote', a clone on
live/primary-checkout, and a REAL pre-push hook that runs a stand-in confidential scan.

Not discovered by the pre-push hook-tests gate (git-spawn suite; see
_tests/test_push_live_backup.py). Run by hand after any change to push-live-backup.py:
    python maintenance/_tests/integration/test_push_live_backup_git.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(os.path.dirname(HERE)), "push-live-backup.py")
_spec = importlib.util.spec_from_file_location("push_live_backup", TOOL)
plb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plb)

BRANCH = "live/primary-checkout"
TARGET_REF = "refs/heads/backup/live-primary"
PY = sys.executable.replace("\\", "/")

# The hook-tests gate stand-in: the shim runs it before the scan. It records that the hook
# ran (RAN) and blocks when a BLOCK file exists, so a gate block can be simulated without
# a confidential term. The doctrine gate stand-in always passes. The confidentiality scan
# is the REAL one from this checkout (the canary requires it to actually block).
HOOK_TESTS_STUB = (
    "import os, sys\n"
    "here = os.path.dirname(os.path.abspath(__file__))\n"
    "sys.stdin.read()\n"
    "open(os.path.join(here, 'RAN'), 'a').write('x')\n"
    "if os.path.exists(os.path.join(here, 'BLOCK')):\n"
    "    print('hook-tests-gate: BLOCKED (stand-in) \u2014 non-ascii')\n"
    "    sys.exit(1)\n"
)
DOCTRINE_STUB = "import sys\nsys.exit(0)\n"
REAL_HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "hooks")
SCAN_OLD = "import sys\nsys.stdin.read()\nsys.exit(0)\n"   # the live branch's pre-#427 shape


def run(cwd, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, env=e)
    if p.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), p.stdout + p.stderr))
    return p.stdout.strip()


class PushLiveBackupGitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="plb-git-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.remote = os.path.join(self.root, "remote.git")
        self.repo = os.path.join(self.root, "live")
        self.state = os.path.join(self.root, "state")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", self.repo], check=True)
        run(self.repo, "config", "user.name", "t")
        run(self.repo, "config", "user.email", "t@t")
        run(self.repo, "config", "commit.gpgsign", "false")
        run(self.repo, "remote", "add", "origin", self.remote)
        hooks = os.path.join(self.repo, "hooks")
        os.makedirs(os.path.join(hooks, "lib"))
        self.scan = os.path.join(hooks, "git-prepush-confidential-scan.py")
        shutil.copy(os.path.join(REAL_HOOKS, "git-prepush-confidential-scan.py"), self.scan)
        shutil.copy(os.path.join(REAL_HOOKS, "lib", "secret_patterns.py"), os.path.join(hooks, "lib"))
        with open(os.path.join(hooks, "git-prepush-hook-tests-gate.py"), "w", newline="\n", encoding="utf-8") as fh:
            fh.write(HOOK_TESTS_STUB)
        with open(os.path.join(hooks, "git-prepush-doctrine-gate.py"), "w", newline="\n", encoding="utf-8") as fh:
            fh.write(DOCTRINE_STUB)
        with open(os.path.join(hooks, "confidential-terms.json"), "w") as fh:
            json.dump({"_doc": "test"}, fh)
        with open(os.path.join(self.repo, ".gitignore"), "w") as fh:
            fh.write("hooks/confidential-terms.json\n__pycache__/\nhooks/RAN\nhooks/BLOCK\n")
        self.commit("base")
        run(self.repo, "push", "-q", "origin", "main")  # fixture setup, before any hook is installed
        run(self.repo, "checkout", "-q", "-b", BRANCH)
        # the EXACT allowlisted shim v2 -- the precondition refuses anything else
        hook = os.path.join(self.repo, ".git", "hooks", "pre-push")
        with open(hook, "w", newline="\n") as fh:
            fh.write(plb.KNOWN_GOOD_SHIMS["v2 (installed 2026-11-08)"])
        os.chmod(hook, 0o755)

    # -- helpers
    def _write_scan(self, src):
        with open(self.scan, "w", newline="\n") as fh:
            fh.write(src)

    def commit(self, msg, when=None):
        with open(os.path.join(self.repo, "f.txt"), "a") as fh:
            fh.write(msg + "\n")
        run(self.repo, "add", "-A")
        env = {"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when} if when else None
        run(self.repo, "commit", "-q", "-m", msg, env=env)
        return run(self.repo, "rev-parse", "HEAD")

    def push(self, *extra):
        argv = ["--repo", self.repo, "--state-dir", self.state, "--push-timeout", "120"] + list(extra)
        return self._main(argv)

    def check(self, *extra):
        return self._main(["--check", "--repo", self.repo, "--state-dir", self.state] + list(extra))

    def _main(self, argv):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = plb.main(argv)
        last = buf.getvalue().strip().splitlines()[-1]
        self.assertTrue(last.startswith("RESULT_JSON="), buf.getvalue())
        return rc, json.loads(last[len("RESULT_JSON="):])

    def remote_tip(self):
        out = subprocess.run(["git", "--git-dir", self.remote, "rev-parse", "-q", "--verify", TARGET_REF],
                             capture_output=True, text=True)
        return out.stdout.strip() or None

    def marker(self):
        return os.path.join(self.state, plb.FAILED_MARKER)

    def stamp(self):
        return os.path.join(self.state, plb.OK_STAMP)

    def hook_ran(self):
        return os.path.exists(os.path.join(self.repo, "hooks", "RAN"))

    # -- tests
    def test_first_push_creates_backup_through_the_hook(self):
        sha = self.commit("live work")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (0, "PUSHED"), res)
        self.assertEqual(self.remote_tip(), sha)
        self.assertTrue(self.hook_ran(), "pre-push hook did not run -- hooks were skipped")
        self.assertTrue(os.path.exists(self.stamp()))
        self.assertFalse(os.path.exists(self.marker()))
        rc, res = self.check()
        self.assertEqual((rc, res["verdict"]), (0, "CONTAINED"), res)

    def test_second_run_is_up_to_date(self):
        self.commit("live work")
        self.assertEqual(self.push()[0], 0)
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (0, "UP_TO_DATE"), res)

    def test_gate_block_fails_loud_and_writes_marker(self):
        self.commit("live work")
        open(os.path.join(self.repo, "hooks", "BLOCK"), "w").close()
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (1, "BLOCKED_OR_FAILED"), res)
        self.assertIsNone(self.remote_tip())
        self.assertEqual(json.load(open(self.marker()))["verdict"], "BLOCKED_OR_FAILED")
        rc, res = self.check()
        self.assertEqual(rc, 1, res)
        self.assertTrue(any("BACKUP_PUSH_FAILED" in p for p in res["problems"]), res)

    def test_success_after_failure_clears_marker(self):
        self.commit("live work")
        open(os.path.join(self.repo, "hooks", "BLOCK"), "w").close()
        self.assertEqual(self.push()[0], 1)
        os.remove(os.path.join(self.repo, "hooks", "BLOCK"))
        self.assertEqual(self.push()[0], 0)
        self.assertFalse(os.path.exists(self.marker()))

    def test_refuses_when_gate_lacks_compressed_scan(self):
        self._write_scan(SCAN_OLD)
        self.commit("live work on a stale gate")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (4, "PRECONDITION"), res)
        self.assertIn("scan_compressed", res["detail"])
        self.assertIsNone(self.remote_tip())
        self.assertFalse(self.hook_ran())
        self.assertTrue(os.path.exists(self.marker()))

    def test_refuses_without_pre_push_hook(self):
        os.remove(os.path.join(self.repo, ".git", "hooks", "pre-push"))
        self.commit("live work")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (4, "PRECONDITION"), res)
        self.assertIsNone(self.remote_tip())

    def test_honours_core_hookspath(self):
        # git would run the hook from core.hooksPath, so the precondition must look THERE
        alt = os.path.join(self.root, "althooks")
        os.makedirs(alt)
        run(self.repo, "config", "core.hooksPath", alt.replace("\\", "/"))
        self.commit("live work")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (4, "PRECONDITION"), res)
        shutil.copy(os.path.join(self.repo, ".git", "hooks", "pre-push"), os.path.join(alt, "pre-push"))
        self.assertEqual(self.push()[0], 0)

    def test_refuses_on_other_branch_and_detached(self):
        self.commit("live work")
        run(self.repo, "checkout", "-q", "main")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (4, "PRECONDITION"), res)
        run(self.repo, "checkout", "-q", "--detach", BRANCH)
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (4, "PRECONDITION"), res)
        self.assertIsNone(self.remote_tip())

    def test_rewritten_live_branch_still_backs_up(self):
        self.commit("a")
        self.assertEqual(self.push()[0], 0)
        run(self.repo, "reset", "-q", "--hard", "HEAD~1")
        sha = self.commit("a-rewritten")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (0, "PUSHED"), res)
        self.assertEqual(self.remote_tip(), sha)

    def test_lease_protects_a_concurrently_moved_backup(self):
        first = self.commit("a")
        self.assertEqual(self.push()[0], 0)
        # another writer moves the backup ref after our ls-remote read: simulate by handing
        # the push a stale expected value
        self.commit("b")
        real = plb.remote_ref_sha
        calls = {"n": 0}

        def stale(repo, remote, ref, timeout=120):
            calls["n"] += 1
            return ("f" * 40) if calls["n"] == 1 else real(repo, remote, ref, timeout)
        plb.remote_ref_sha = stale
        try:
            rc, res = self.push()
        finally:
            plb.remote_ref_sha = real
        self.assertEqual((rc, res["verdict"]), (2, "LEASE_REJECTED"), res)
        self.assertEqual(self.remote_tip(), first)
        self.assertTrue(os.path.exists(self.marker()))

    def test_success_requires_the_remote_reread(self):
        # REFUTE 2026-11-08: removing the post-push ls-remote verification passed every test
        self.commit("live work")
        real = plb.remote_ref_sha
        calls = {"n": 0}

        def lying(repo, remote, ref, timeout=120):
            calls["n"] += 1
            return real(repo, remote, ref, timeout) if calls["n"] == 1 else "e" * 40
        plb.remote_ref_sha = lying
        try:
            rc, res = self.push()
        finally:
            plb.remote_ref_sha = real
        self.assertEqual((rc, res["verdict"]), (5, "PUSHED_UNVERIFIED"), res)
        self.assertTrue(os.path.exists(self.marker()))
        self.assertFalse(os.path.exists(self.stamp()))

    def test_real_confidential_scan_blocks_a_term_inside_a_gz(self):
        # The REAL #427 scan (installed by setUp): a planted roster term inside a gzip blob
        # must block the backup push through the shim, with no remote ref created.
        import gzip
        term = "zqplantedrosterterm" + "xq"
        with open(os.path.join(self.repo, "hooks", "confidential-terms.json"), "w") as fh:
            json.dump({"_doc": "test", "deal-x": {"active": True, "always": [term]}}, fh)
        self.commit("clean live work")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (0, "PUSHED"), res)
        with gzip.open(os.path.join(self.repo, "audit.jsonl.gz"), "wt") as fh:
            fh.write('{"tool":"x","text":"%s"}\n' % term)
        self.commit("transcript archive")
        rc, res = self.push()
        self.assertEqual((rc, res["verdict"]), (1, "BLOCKED_OR_FAILED"), res)
        self.assertIn("COMPRESSED", res.get("detail", ""))
        self.assertNotIn(term, json.dumps(res))
        self.assertTrue(os.path.exists(self.marker()))
        self.assertNotEqual(self.remote_tip(), run(self.repo, "rev-parse", "HEAD"))

    def test_check_grace_and_not_offbox(self):
        self.assertEqual(self.push()[0], 0)        # a recent successful backup on record
        self.commit("fresh")
        rc, res = self.check()
        self.assertEqual((rc, res["verdict"]), (0, "PENDING_WITHIN_GRACE"), res)
        old = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 86400))
        run(self.repo, "reset", "-q", "--hard", "HEAD~1")
        self.commit("old", when=old)
        self.commit("fresh-on-top")
        rc, res = self.check()
        self.assertEqual((rc, res["verdict"]), (1, "NOT_OFFBOX"), res)
        self.assertEqual(res["pending_count"], 2)

    def test_check_counts_backup_ref_as_offbox(self):
        old = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 86400))
        self.commit("old", when=old)
        self.assertEqual(self.check()[0], 1)
        self.assertEqual(self.push()[0], 0)
        self.assertEqual(self.check()[0], 0)

    def test_check_prunes_deleted_remote_refs(self):
        old = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 86400))
        self.commit("old", when=old)
        self.assertEqual(self.push()[0], 0)
        self.assertEqual(self.check()[0], 0)
        subprocess.run(["git", "--git-dir", self.remote, "update-ref", "-d", TARGET_REF], check=True)
        rc, res = self.check()
        self.assertEqual((rc, res["verdict"]), (1, "NOT_OFFBOX"), res)

    def test_check_unreachable_remote_is_could_not_look(self):
        run(self.repo, "remote", "set-url", "origin", os.path.join(self.root, "nope.git"))
        rc, res = self.check()
        self.assertEqual((rc, res["verdict"]), (2, "COULD_NOT_LOOK"), res)

    def test_push_unreachable_remote_fails_with_marker(self):
        self.commit("x")
        run(self.repo, "remote", "set-url", "origin", os.path.join(self.root, "nope.git"))
        rc, res = self.push()
        self.assertNotEqual(rc, 0, res)
        self.assertTrue(os.path.exists(self.marker()))


if __name__ == "__main__":
    unittest.main(verbosity=1)

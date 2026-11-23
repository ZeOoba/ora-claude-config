"""Tests for leased_push.py (stdlib unittest; gated by tools/run_skill_suites.sh)."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "leased_push.py")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True,
                          env=ENV).stdout.strip()


def run(*args):
    return subprocess.run([sys.executable, "-I", SCRIPT] + list(args), capture_output=True, text=True, env=ENV)


class LeasedPushTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.remote = os.path.join(t, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True, env=ENV)
        src = os.path.join(t, "src")
        subprocess.run(["git", "init", "-q", "-b", "main", src], check=True, env=ENV)
        for i in range(5):
            with open(os.path.join(src, "f.txt"), "w") as fh:
                fh.write("v%d\n" % i)
            git(src, "add", "f.txt")
            git(src, "commit", "-q", "-m", "c%d" % i)
            git(src, "branch", "b%d" % i)
        git(src, "tag", "v1")
        git(src, "push", "-q", self.remote, "refs/heads/*:refs/heads/*", "refs/tags/*:refs/tags/*")
        # The rewritten copy: same refs, every commit different (amended).
        self.work = os.path.join(t, "work.git")
        subprocess.run(["git", "clone", "-q", "--mirror", "--no-local", self.remote, self.work], check=True, env=ENV)
        for ref in git(self.work, "for-each-ref", "--format=%(refname)").split():
            tree = git(self.work, "rev-parse", ref + "^{tree}")
            new = git(self.work, "commit-tree", tree, "-m", "rewritten " + ref)
            git(self.work, "update-ref", ref, new)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pushes_all_refs_in_batches_main_last(self):
        r = run(self.work, self.remote, "--batch", "2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("rejected: 0", r.stdout)
        for ref in git(self.work, "for-each-ref", "--format=%(refname)").split():
            self.assertEqual(git(self.work, "rev-parse", ref), git(self.remote, "rev-parse", ref), ref)
        order = [l for l in r.stdout.splitlines() if l.startswith("batch ")]
        self.assertIn("refs/heads/main", order[-1])
        self.assertNotIn("refs/heads/main", " ".join(order[:-1]))

    def test_ref_moved_after_snapshot_is_rejected_and_exit_nonzero(self):
        # Someone pushes to b1 after our snapshot: the lease must protect it.
        r = run(self.work, self.remote, "--batch", "2", "--snapshot-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        other = os.path.join(self.tmp.name, "other")
        subprocess.run(["git", "clone", "-q", self.remote, other], check=True, env=ENV)
        git(other, "checkout", "-q", "b1")
        with open(os.path.join(other, "g.txt"), "w") as fh:
            fh.write("late\n")
        git(other, "add", "g.txt")
        git(other, "commit", "-q", "-m", "late push")
        moved = git(other, "rev-parse", "HEAD")
        git(other, "push", "-q", "origin", "b1")
        r = run(self.work, self.remote, "--batch", "2", "--use-snapshot")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("rejected: 1", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), moved)

    def test_dry_run_changes_nothing(self):
        before = git(self.remote, "for-each-ref")
        r = run(self.work, self.remote, "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(before, git(self.remote, "for-each-ref"))


if __name__ == "__main__":
    unittest.main()

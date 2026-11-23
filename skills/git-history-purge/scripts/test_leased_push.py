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


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class LeasedPushTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.remote = os.path.join(t, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remote], check=True, env=ENV)
        src = os.path.join(t, "src")
        subprocess.run(["git", "init", "-q", "-b", "main", src], check=True, env=ENV)
        for i in range(5):
            write(os.path.join(src, "f.txt"), "v%d\n" % i)
            git(src, "add", "f.txt")
            git(src, "commit", "-q", "-m", "c%d" % i)
            git(src, "branch", "b%d" % i)
        git(src, "tag", "-a", "v1", "-m", "release")
        git(src, "push", "-q", self.remote, "refs/heads/*:refs/heads/*", "refs/tags/*:refs/tags/*")
        # The backup, then the rewrite made from it (every commit and the tag object change).
        self.mirror = os.path.join(t, "mirror.git")
        subprocess.run(["git", "clone", "-q", "--mirror", self.remote, self.mirror], check=True, env=ENV)
        self.work = os.path.join(t, "work.git")
        subprocess.run(["git", "clone", "-q", "--mirror", "--no-local", self.mirror, self.work], check=True, env=ENV)
        for ref in git(self.work, "for-each-ref", "--format=%(refname)", "refs/heads").split():
            new = git(self.work, "commit-tree", git(self.work, "rev-parse", ref + "^{tree}"), "-m", "rw " + ref)
            git(self.work, "update-ref", ref, new)
        git(self.work, "tag", "-f", "-a", "v1", "-m", "release (rewritten)", "refs/heads/main")
        self.before = git(self.remote, "for-each-ref")

    def tearDown(self):
        self.tmp.cleanup()

    def run_push(self, *extra, env=None):
        e = dict(ENV, **(env or {}))
        return subprocess.run([sys.executable, "-I", SCRIPT, self.mirror, self.work, self.remote] + list(extra),
                              capture_output=True, text=True, env=e)

    def late_push(self, branch="b1"):
        """Another actor pushes a new commit to <branch>; returns its SHA."""
        other = os.path.join(self.tmp.name, "other-" + branch)
        if not os.path.isdir(other):
            subprocess.run(["git", "clone", "-q", self.remote, other], check=True, env=ENV)
        git(other, "checkout", "-q", branch)
        write(os.path.join(other, "late.txt"), "late\n")
        git(other, "add", "late.txt")
        git(other, "commit", "-q", "-m", "late push")
        git(other, "push", "-q", "origin", branch)
        return git(other, "rev-parse", "HEAD")

    def hook_cmd(self, code):
        path = os.path.join(self.tmp.name, "hook.py")
        write(path, code)
        return "%s -I %s" % (sys.executable, path)

    def test_pushes_all_refs_in_batches_main_last(self):
        r = self.run_push("--batch", "2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for ref in git(self.work, "for-each-ref", "--format=%(refname)").split():
            self.assertEqual(git(self.work, "rev-parse", ref), git(self.remote, "rev-parse", ref), ref)
        batches = [l for l in r.stdout.splitlines() if l.startswith("batch ")]
        self.assertIn("refs/heads/main", batches[-1])
        self.assertNotIn("refs/heads/main", " ".join(batches[:-1]))

    def test_push_after_backup_stops_everything_before_any_push(self):
        late = self.late_push("b1")
        r = self.run_push()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("MOVED refs/heads/b1", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/main"),
                         git(self.mirror, "rev-parse", "refs/heads/main"))

    def test_push_landing_during_the_run_is_rejected_main_held_and_rerun_refuses(self):
        other = os.path.join(self.tmp.name, "other-b1")
        subprocess.run(["git", "clone", "-q", self.remote, other], check=True, env=ENV)
        code = ("import subprocess\n"
                "g = ['git', '-C', %r]\n"
                "subprocess.run(g + ['checkout', '-q', 'b1'], check=True)\n"
                "open(%r, 'w').write('late\\n')\n"
                "subprocess.run(g + ['add', 'late.txt'], check=True)\n"
                "subprocess.run(g + ['commit', '-q', '-m', 'late'], check=True)\n"
                "subprocess.run(g + ['push', '-q', 'origin', 'b1'], check=True)\n"
                % (other, os.path.join(other, "late.txt")))
        r = self.run_push("--batch", "2", env={"LEASED_PUSH_TEST_BEFORE_PUSH": self.hook_cmd(code)})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        late = git(other, "rev-parse", "HEAD")
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)
        self.assertIn("HELD refs/heads/main", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/main"),
                         git(self.mirror, "rev-parse", "refs/heads/main"))
        again = self.run_push("--batch", "2")
        self.assertEqual(again.returncode, 3, again.stdout + again.stderr)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)

    def test_partial_push_then_rerun_skips_done_refs_and_finishes(self):
        mark = os.path.join(self.tmp.name, "reject-b2")
        write(mark, "x")
        hook = os.path.join(self.remote, "hooks", "update")
        write(hook, '#!/bin/sh\nif [ "$1" = refs/heads/b2 ] && [ -f "%s" ]; then echo no b2 >&2; exit 1; fi\n'
              % mark.replace("\\", "/"))
        os.chmod(hook, 0o755)
        r = self.run_push("--batch", "2")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("HELD refs/heads/main", r.stdout)
        os.remove(mark)
        again = self.run_push("--batch", "2")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertRegex(again.stdout, r"refs: 2 to push, [1-9]\d* already done")
        for ref in git(self.work, "for-each-ref", "--format=%(refname)").split():
            self.assertEqual(git(self.work, "rev-parse", ref), git(self.remote, "rev-parse", ref), ref)

    def test_batch_failing_without_porcelain_is_a_failure(self):
        code = "import os\nos.rename(%r, %r)\n" % (self.remote, self.remote + ".gone")
        r = self.run_push(env={"LEASED_PUSH_TEST_BEFORE_PUSH": self.hook_cmd(code)})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("batch 1 failed", r.stdout)

    def test_dry_run_changes_nothing(self):
        r = self.run_push("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.before, git(self.remote, "for-each-ref"))

    def test_bad_work_path_is_an_error(self):
        r = subprocess.run([sys.executable, "-I", SCRIPT, self.mirror, self.work + "-typo", self.remote],
                           capture_output=True, text=True, env=ENV)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.before, git(self.remote, "for-each-ref"))


if __name__ == "__main__":
    unittest.main()

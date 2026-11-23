"""Tests for leased_push.py and old_history_guard.py (stdlib unittest; gated by tools/run_skill_suites.sh).

The rewrite under test is a real `git filter-repo` run on a mirror clone of the backup,
exactly as SKILL.md Step 3 makes it, so ref-map is the real file.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "leased_push.py")
GUARD = os.path.join(HERE, "old_history_guard.py")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="t",
           GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True,
                          env=ENV).stdout.strip()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class Base(unittest.TestCase):
    CLEAN_ROOT = False      # True: the first commit holds nothing private, so the purge keeps its SHA
    BRANCH = "main"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.remote = os.path.join(t, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", self.BRANCH, self.remote], check=True, env=ENV)
        src = self.src = os.path.join(t, "src")
        subprocess.run(["git", "init", "-q", "-b", self.BRANCH, src], check=True, env=ENV)
        if self.CLEAN_ROOT:
            write(os.path.join(src, "README.md"), "readme\n")
            git(src, "add", "README.md")
            git(src, "commit", "-q", "-m", "init")
        for i in range(5):
            write(os.path.join(src, "f.txt"), "secret v%d\n" % i)
            git(src, "add", "f.txt")
            git(src, "commit", "-q", "-m", "c%d" % i)
            git(src, "branch", "b%d" % i)
        git(src, "tag", "-a", "v1", "-m", "release")
        git(src, "push", "-q", self.remote, "refs/heads/*:refs/heads/*", "refs/tags/*:refs/tags/*")
        self.mirror = os.path.join(t, "mirror.git")
        subprocess.run(["git", "clone", "-q", "--mirror", self.remote, self.mirror], check=True, env=ENV)
        self.rules = os.path.join(t, "rules.txt")
        write(self.rules, "secret==>[private]\n")
        self.work = os.path.join(t, "work.git")
        self.rewrite()
        self.before = git(self.remote, "for-each-ref")

    def rewrite(self, extra=()):
        """Step 3: fresh mirror clone of the backup, ONE filter-repo run."""
        if os.path.isdir(self.work):
            shutil.move(self.work, self.work + "-old%d" % len(os.listdir(self.tmp.name)))
        subprocess.run(["git", "clone", "-q", "--mirror", "--no-local", self.mirror, self.work], check=True, env=ENV)
        git(self.work, "filter-repo", "--force", "--replace-text", self.rules, "--replace-message", self.rules,
            *extra)

    def tearDown(self):
        self.tmp.cleanup()

    def run_push(self, *extra, env=None, mirror=None, work=None, url=None):
        e = dict(ENV, **(env or {}))
        return subprocess.run([sys.executable, "-I", SCRIPT, mirror or self.mirror, work or self.work,
                               url or self.remote] + list(extra), capture_output=True, text=True, env=e)

    def late_push(self, branch="b1"):
        other = os.path.join(self.tmp.name, "other-" + branch)
        if not os.path.isdir(other):
            subprocess.run(["git", "clone", "-q", self.remote, other], check=True, env=ENV)
        git(other, "checkout", "-q", branch)
        git(other, "pull", "-q", "origin", branch)
        write(os.path.join(other, "late.txt"), "late %s\n" % len(os.listdir(other)))
        git(other, "add", "late.txt")
        git(other, "commit", "-q", "-m", "late push")
        git(other, "push", "-q", "origin", branch)
        return git(other, "rev-parse", "HEAD")

    def hook_cmd(self, code):
        path = os.path.join(self.tmp.name, "hook.py")
        write(path, code)
        return path

    def reject_on_remote(self, ref):
        mark = os.path.join(self.tmp.name, "reject")
        write(mark, "x")
        hook = os.path.join(self.remote, "hooks", "update")
        write(hook, '#!/bin/sh\nif [ "$1" = %s ] && [ -f "%s" ]; then echo no >&2; exit 1; fi\n'
              % (ref, mark.replace("\\", "/")))
        os.chmod(hook, 0o755)
        return mark

    def assert_remote_matches_work(self):
        for ref in git(self.work, "for-each-ref", "--format=%(refname)").split():
            self.assertEqual(git(self.work, "rev-parse", ref), git(self.remote, "rev-parse", ref), ref)


class LeasedPushTest(Base):
    def test_pushes_everything_with_main_alone_and_last(self):
        r = self.run_push("--batch", "2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_remote_matches_work()
        pushes = [l for l in r.stdout.splitlines() if l.startswith(("batch ", "main:"))]
        self.assertEqual(pushes[-1], "main: refs/heads/main")
        self.assertNotIn("refs/heads/main", " ".join(pushes[:-1]))

    def test_rejection_holds_main_at_default_batch_size(self):
        self.reject_on_remote("refs/heads/b2")
        r = self.run_push()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("HELD refs/heads/main", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/main"), git(self.mirror, "rev-parse", "refs/heads/main"))

    def test_partial_push_then_rerun_skips_done_refs_and_finishes(self):
        mark = self.reject_on_remote("refs/heads/b2")
        self.assertEqual(self.run_push("--batch", "2").returncode, 1)
        os.remove(mark)
        again = self.run_push("--batch", "2")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertRegex(again.stdout, r"refs: 2 to push, [1-9]\d* already done")
        self.assert_remote_matches_work()

    def test_push_after_backup_stops_everything_before_any_push(self):
        late = self.late_push("b1")
        r = self.run_push()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("MOVED refs/heads/b1", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)
        self.assertEqual(self.before.replace(git(self.mirror, "rev-parse", "refs/heads/b1"), late),
                         git(self.remote, "for-each-ref"))

    def test_push_landing_during_the_run_is_rejected_and_rerun_refuses(self):
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
        r = self.run_push(env={"LEASED_PUSH_TEST_BEFORE_PUSH": self.hook_cmd(code)})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        late = git(other, "rev-parse", "HEAD")
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)
        self.assertIn("HELD refs/heads/main", r.stdout)
        again = self.run_push()
        self.assertEqual(again.returncode, 3, again.stdout + again.stderr)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)

    def test_recovery_with_stale_rewrite_is_refused(self):
        late = self.late_push("b1")
        self.assertEqual(self.run_push().returncode, 3)
        git(self.mirror, "fetch", "-q", self.remote, "+refs/heads/b1:refs/heads/b1")   # backup now has the late commit
        r = self.run_push()                                                           # but work.git was NOT redone
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("STALE refs/heads/b1", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/b1"), late)
        self.rewrite()                                                                # the documented recovery
        ok = self.run_push()
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("late.txt", git(self.remote, "ls-tree", "--name-only", "refs/heads/b1"))

    def test_second_filter_repo_pass_on_same_copy_is_allowed(self):
        second = os.path.join(self.tmp.name, "rules2.txt")
        write(second, "v3==>vX\n")       # e.g. a separate mailmap pass: ref-map keeps the backup as "old"
        git(self.work, "filter-repo", "--force", "--replace-text", second)
        r = self.run_push()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_remote_matches_work()

    def test_missing_ref_map_is_refused(self):
        bare = os.path.join(self.tmp.name, "plain.git")
        subprocess.run(["git", "clone", "-q", "--mirror", self.mirror, bare], check=True, env=ENV)
        r = self.run_push(work=bare)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.before, git(self.remote, "for-each-ref"))

    def test_ref_deleted_by_rewrite_needs_explicit_delete(self):
        git(self.src, "checkout", "-q", "--orphan", "notesonly")
        git(self.src, "rm", "-q", "-rf", ".")
        os.makedirs(os.path.join(self.src, "notes"))
        write(os.path.join(self.src, "notes", "x.md"), "secret\n")
        git(self.src, "add", "notes")
        git(self.src, "commit", "-q", "-m", "notes only")
        git(self.src, "push", "-q", self.remote, "notesonly")
        git(self.mirror, "fetch", "-q", self.remote, "+refs/heads/*:refs/heads/*")
        self.rewrite(extra=("--invert-paths", "--path", "notes"))
        r = self.run_push()
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("DELETED-BY-REWRITE refs/heads/notesonly", r.stdout)
        self.assertEqual(git(self.remote, "for-each-ref", "--format=%(refname)", "refs/heads/notesonly"),
                         "refs/heads/notesonly")
        d = self.run_push("--delete-removed")
        self.assertEqual(d.returncode, 0, d.stdout + d.stderr)
        self.assertEqual(git(self.remote, "for-each-ref", "--format=%(refname)", "refs/heads/notesonly"), "")
        self.assert_remote_matches_work()

    def test_branch_created_after_backup_stops_everything(self):
        other = os.path.join(self.tmp.name, "other-new")
        subprocess.run(["git", "clone", "-q", self.remote, other], check=True, env=ENV)
        git(other, "push", "-q", "origin", "HEAD~1:refs/heads/late-new")      # old history, new name
        r = self.run_push()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("MOVED refs/heads/late-new", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/main"), git(self.mirror, "rev-parse", "refs/heads/main"))

    def test_batch_failing_without_porcelain_is_a_failure(self):
        code = "import os\nos.rename(%r, %r)\n" % (self.remote, self.remote + ".gone")
        r = self.run_push(env={"LEASED_PUSH_TEST_BEFORE_PUSH": self.hook_cmd(code)})
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("batch 1 failed", r.stdout)

    def test_dry_run_changes_nothing(self):
        r = self.run_push("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.before, git(self.remote, "for-each-ref"))

    def test_bad_paths_and_url_are_errors(self):
        for kw in ({"work": self.work + "-typo"}, {"mirror": self.mirror + "-typo"},
                   {"url": os.path.join(self.tmp.name, "nope.git")}):
            r = self.run_push(**kw)
            self.assertEqual(r.returncode, 2, "%s: %s" % (kw, r.stdout + r.stderr))
        self.assertEqual(self.before, git(self.remote, "for-each-ref"))


class MasterBranchTest(Base):
    BRANCH = "master"

    def test_main_ref_option_holds_the_default_branch(self):
        self.reject_on_remote("refs/heads/b2")
        r = self.run_push("--main-ref", "refs/heads/master")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("HELD refs/heads/master", r.stdout)
        self.assertEqual(git(self.remote, "rev-parse", "refs/heads/master"),
                         git(self.mirror, "rev-parse", "refs/heads/master"))


class OldHistoryGuardTest(Base):
    CLEAN_ROOT = True       # the hard case: the purge keeps the first commit, every old branch shares it

    def setUp(self):
        super().setUp()
        # an orphan branch in the backup whose own history also gets purged
        git(self.src, "checkout", "-q", "--orphan", "side")
        write(os.path.join(self.src, "side.txt"), "secret side\n")
        git(self.src, "add", "side.txt")
        git(self.src, "commit", "-q", "-m", "side")
        git(self.src, "push", "-q", self.remote, "side")
        git(self.mirror, "fetch", "-q", self.remote, "+refs/heads/*:refs/heads/*")
        self.rewrite()
        self.assertEqual(self.run_push().returncode, 0)
        self.purged = os.path.join(self.tmp.name, "verify.git")
        subprocess.run(["git", "clone", "-q", "--bare", self.remote, self.purged], check=True, env=ENV)
        self.listfile = os.path.join(self.tmp.name, "old-commits.txt")
        g = subprocess.run([sys.executable, "-I", GUARD, "commits", self.mirror, self.purged, self.listfile],
                           capture_output=True, text=True, env=ENV)
        self.assertEqual(g.returncode, 0, g.stdout + g.stderr)
        self.zero = "0" * 40

    def check(self, line, *nxt, listfile=None):
        args = [sys.executable, "-I", GUARD, "check", listfile or self.listfile]
        if nxt:
            args += ["--"] + list(nxt)
        return subprocess.run(args, input=line, capture_output=True, text=True, env=ENV, cwd=self.mirror)

    def test_root_commit_survives_the_purge(self):
        self.assertEqual(git(self.mirror, "rev-list", "--max-parents=0", "refs/heads/main"),
                         git(self.purged, "rev-list", "--max-parents=0", "refs/heads/main"))

    def test_old_branches_are_refused_even_with_a_shared_root(self):
        for ref in ("refs/heads/b1", "refs/heads/side"):
            old = git(self.mirror, "rev-parse", ref)
            bad = self.check("refs/heads/feat %s refs/heads/feat %s\n" % (old, self.zero))
            self.assertEqual(bad.returncode, 1, "%s: %s" % (ref, bad.stdout + bad.stderr))
            self.assertIn("refusing to push refs/heads/feat", bad.stderr)

    def test_purged_history_and_deletions_are_allowed(self):
        git(self.mirror, "fetch", "-q", self.remote, "refs/heads/b1:refs/purged/b1")
        new = git(self.mirror, "rev-parse", "refs/purged/b1")
        self.assertEqual(self.check("refs/heads/b1 %s refs/heads/b1 %s\n" % (new, self.zero)).returncode, 0)
        self.assertEqual(self.check("(delete) %s refs/heads/x %s\n" % (self.zero, new)).returncode, 0)

    def test_empty_commit_list_refuses(self):
        empty = os.path.join(self.tmp.name, "empty.txt")
        write(empty, "\n")
        git(self.mirror, "fetch", "-q", self.remote, "refs/heads/b1:refs/purged/b1")
        new = git(self.mirror, "rev-parse", "refs/purged/b1")
        r = self.check("refs/heads/b1 %s refs/heads/b1 %s\n" % (new, self.zero), listfile=empty)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_commits_mode_fails_when_nothing_changed(self):
        out = os.path.join(self.tmp.name, "none.txt")
        g = subprocess.run([sys.executable, "-I", GUARD, "commits", self.purged, self.purged, out],
                           capture_output=True, text=True, env=ENV)
        self.assertEqual(g.returncode, 1, g.stdout + g.stderr)

    def test_chained_next_hook_gets_the_same_stdin_and_its_exit_code(self):
        echo = os.path.join(self.tmp.name, "next.py")
        seen = os.path.join(self.tmp.name, "seen.txt")
        write(echo, "import sys\ndata = sys.stdin.read()\nopen(%r, 'w').write(data)\nsys.exit(int(sys.argv[1]))\n" % seen)
        git(self.mirror, "fetch", "-q", self.remote, "refs/heads/b1:refs/purged/b1")
        new = git(self.mirror, "rev-parse", "refs/purged/b1")
        line = "refs/heads/b1 %s refs/heads/b1 %s\n" % (new, self.zero)
        ok = self.check(line, sys.executable, "-I", echo, "0")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        with open(seen, encoding="utf-8") as fh:
            self.assertEqual(fh.read().replace("\r\n", "\n"), line)
        self.assertEqual(self.check(line, sys.executable, "-I", echo, "7").returncode, 7)
        os.remove(seen)
        old = git(self.mirror, "rev-parse", "refs/heads/b1")
        bad = self.check("refs/heads/f %s refs/heads/f %s\n" % (old, self.zero), sys.executable, "-I", echo, "0")
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(os.path.exists(seen))    # refused before the next hook runs


if __name__ == "__main__":
    unittest.main()

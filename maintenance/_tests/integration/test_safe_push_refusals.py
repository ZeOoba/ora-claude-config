"""safe-push.py every refusal path -- each must leave HEAD, tree and the remote as found.

Split from one file (2026-09-23): under heavy machine load the combined suite took ~600s,
past the pre-push hook-tests gate's 240s per-file budget (480s on its one retry), so these
live in _tests/integration/, which the gate does not discover. Run by hand after changes.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _safe_push_fixture import Race, git, run_tool  # noqa: E402


class SafePushRefusalsTest(unittest.TestCase):
    def setUp(self):
        self.r = Race()

    def tearDown(self):
        self.r.cleanup()

    def test_rebase_conflict_aborts_and_leaves_head(self):
        self.r.commit(self.r.a, "g.txt", "mine\n", "mine")
        self.r.other_session_pushes(name="g.txt", text="theirs\n")
        before = git(self.r.a, "rev-parse", "HEAD")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 4, out)
        self.assertEqual(res["verdict"], "REBASE_CONFLICT")
        self.assertEqual(git(self.r.a, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.r.a, "status", "--porcelain"), "")
        self.assertFalse(os.path.exists(os.path.join(self.r.a, ".git", "rebase-merge")))

    def test_dirty_tracked_tree_refused_before_anything(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.write(self.r.a, "g.txt", "someone else's wip\n")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 3, out)
        self.assertEqual(res["verdict"], "DIRTY_TREE")
        self.assertEqual(open(os.path.join(self.r.a, "g.txt")).read(), "someone else's wip\n")
        self.assertNotEqual(self.r.remote_tip(), git(self.r.a, "rev-parse", "HEAD"))

    def test_untracked_files_do_not_block(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.write(self.r.a, "scratch.tmp", "x\n")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)

    def test_merge_commit_in_range_refuses_rebase(self):
        git(self.r.a, "checkout", "-q", "-b", "side")
        self.r.commit(self.r.a, "f.txt", "side\n", "side")
        git(self.r.a, "checkout", "-q", "main")
        self.r.commit(self.r.a, "g.txt", "main-local\n", "local")
        git(self.r.a, "merge", "-q", "--no-edit", "side")
        # stage the race on an untouched file so only the merge-commit rule can stop it
        git(self.r.b, "pull", "-q", "origin", "main")
        Race.write(self.r.b, "new.txt", "n\n")
        git(self.r.b, "add", "new.txt")
        git(self.r.b, "commit", "-q", "-m", "other")
        git(self.r.b, "push", "-q", "origin", "main")
        before = git(self.r.a, "rev-parse", "HEAD")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 5, out)
        self.assertEqual(res["verdict"], "MERGES_IN_RANGE")
        self.assertEqual(git(self.r.a, "rev-parse", "HEAD"), before)

    def test_target_required(self):
        rc, res, out = run_tool(self.r.a)
        self.assertNotEqual(rc, 0)

    def test_retries_capped(self):
        rc, res, out = run_tool(self.r.a, "--to", "main", "--retries", "9")
        self.assertEqual(rc, 6, out)
        self.assertEqual(res["verdict"], "USAGE")

    def test_other_sessions_rebase_in_progress_is_never_touched(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.other_session_pushes()
        marker = os.path.join(self.r.a, ".git", "rebase-merge")
        os.makedirs(marker)  # a paused rebase: tree looks clean
        with open(os.path.join(marker, "head-name"), "w") as f:
            f.write("refs/heads/main\n")
        before = git(self.r.a, "rev-parse", "HEAD")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 7, out)
        self.assertEqual(res["verdict"], "OPERATION_IN_PROGRESS")
        self.assertTrue(os.path.isdir(marker), "their rebase state must survive")
        self.assertEqual(git(self.r.a, "rev-parse", "HEAD"), before)

    def test_unresolved_merge_in_progress_refused(self):
        self.r.commit(self.r.a, "g.txt", "mine\n", "mine")
        self.r.other_session_pushes(name="g.txt", text="theirs\n")
        git(self.r.a, "fetch", "-q", "origin")
        git(self.r.a, "merge", "-q", "origin/main", check=False)  # leaves MERGE_HEAD + conflict
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 7, out)
        self.assertTrue(os.path.exists(os.path.join(self.r.a, ".git", "MERGE_HEAD")))

    def test_already_published_feature_branch_is_not_rebased(self):
        git(self.r.a, "checkout", "-q", "-b", "feat")
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        git(self.r.a, "push", "-q", "-u", "origin", "feat")
        self.r.other_session_pushes()
        before = git(self.r.a, "rev-parse", "HEAD")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 5, out)
        self.assertEqual(res["verdict"], "ALREADY_PUBLISHED")
        self.assertEqual(git(self.r.a, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.r.a, "rev-parse", "origin/feat"), before)

    def test_already_published_but_no_rebase_needed_still_pushes(self):
        git(self.r.a, "checkout", "-q", "-b", "feat")
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        git(self.r.a, "push", "-q", "-u", "origin", "feat")
        rc, res, out = run_tool(self.r.a, "--to", "main")  # fast-forward: no history rewritten
        self.assertEqual(rc, 0, out)

    def test_missing_target_branch_is_usage_error(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        rc, res, out = run_tool(self.r.a, "--to", "no-such-branch")
        self.assertEqual(rc, 6, out)
        self.assertIn("does not exist", res["detail"])

    def test_bad_target_and_remote_rejected(self):
        self.assertEqual(run_tool(self.r.a, "--to", "main:evil")[0], 6)
        self.assertEqual(run_tool(self.r.a, "--to", "main", "--remote", "https://x/y.git")[0], 6)

    def test_skip_worktree_entry_counts_as_dirty(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        git(self.r.a, "update-index", "--skip-worktree", "g.txt")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 3, out)


if __name__ == "__main__":
    unittest.main()

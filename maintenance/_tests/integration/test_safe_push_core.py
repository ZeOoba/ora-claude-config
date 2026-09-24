"""safe-push.py push, retry and race paths (spawn-heavy: each test builds a bare origin + 2 clones).

Split from one file (2026-09-23): under heavy machine load the combined suite took ~600s,
past the pre-push hook-tests gate's 240s per-file budget (480s on its one retry), so these
live in _tests/integration/, which the gate does not discover. Run by hand after changes.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _safe_push_fixture import Race, git, run_tool  # noqa: E402


class SafePushCoreTest(unittest.TestCase):
    def setUp(self):
        self.r = Race()

    def tearDown(self):
        self.r.cleanup()

    def test_plain_push_lands(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(res["verdict"], "PUSHED")
        self.assertEqual(res["attempts"], 1)
        self.assertEqual(self.r.remote_tip(), git(self.r.a, "rev-parse", "HEAD"))

    def test_stale_ref_race_rebases_and_lands(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.other_session_pushes()
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(res["verdict"], "PUSHED")
        # pre-flight fetch sees the stale ref and rebases BEFORE pushing: no gate run wasted
        self.assertEqual(res["attempts"], 1)
        self.assertIn("rebasing 1 local commit", out)
        log = git(self.r.a, "log", "--format=%s", "origin/main").splitlines()
        self.assertEqual(log[:3], ["mine", "other", "init"])  # linear: rebased, not merged
        self.assertEqual(self.r.remote_tip(), git(self.r.a, "rev-parse", "HEAD"))

    def test_mid_gate_race_every_attempt_gives_up_after_bound(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        # every pre-push run, the other session lands a commit first -> every attempt loses
        self.r.hook("git -C '%s' commit -q --allow-empty -m race && git -C '%s' push -q origin main"
                    % (self.r.b.replace("\\", "/"), self.r.b.replace("\\", "/")))
        git(self.r.b, "pull", "-q", "origin", "main")
        rc, res, out = run_tool(self.r.a, "--to", "main", "--retries", "2")
        self.assertEqual(rc, 2, out)
        self.assertEqual(res["verdict"], "LOST_RACE")
        self.assertEqual(self.r.runs(), 3)  # first try + exactly 2 retries, never more

    def test_gate_failure_is_not_retried(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.hook("exit 1")
        rc, res, out = run_tool(self.r.a, "--to", "main", "--retries", "3")
        self.assertEqual(rc, 1, out)
        self.assertEqual(res["verdict"], "PUSH_FAILED")
        self.assertEqual(self.r.runs(), 1)

    def test_detached_head_pushes_to_named_target(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        git(self.r.a, "checkout", "-q", "--detach")
        self.r.other_session_pushes()
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.r.remote_tip(), git(self.r.a, "rev-parse", "HEAD"))

    def test_nothing_to_push_is_success_without_pushing(self):
        self.r.hook("exit 1")  # would fail if a push were attempted
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(res["verdict"], "NOTHING_TO_PUSH")
        self.assertEqual(self.r.runs(), 0)

    def test_non_utf8_hook_output_does_not_crash(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.hook(r"printf '\201\215\217\220\235 cp1252-undefined bytes\n'; exit 0")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(res["verdict"], "PUSHED")

    def test_race_looking_gate_output_is_not_a_race(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        self.r.hook("echo ' ! [rejected]        main -> main (fetch first)'; "
                    "echo \"error: cannot lock ref 'refs/heads/main': is at aaa but expected bbb\"; exit 1")
        rc, res, out = run_tool(self.r.a, "--to", "main", "--retries", "3")
        self.assertEqual(rc, 1, out)
        self.assertEqual(res["verdict"], "PUSH_FAILED")
        self.assertEqual(self.r.runs(), 1)

    def test_tip_advanced_right_after_our_push_still_counts(self):
        self.r.commit(self.r.a, "f.txt", "mine\n", "mine")
        hook = os.path.join(self.r.bare, "hooks", "post-receive")
        with open(hook, "w", newline="\n") as f:
            f.write("#!/bin/sh\nc=$(git commit-tree -p refs/heads/main -m after 'refs/heads/main^{tree}')\n"
                    "git update-ref refs/heads/main \"$c\"\n")
        rc, res, out = run_tool(self.r.a, "--to", "main")
        self.assertEqual(rc, 0, out)
        self.assertEqual(res["verdict"], "PUSHED")
        self.assertIn("tip", res)


if __name__ == "__main__":
    unittest.main()

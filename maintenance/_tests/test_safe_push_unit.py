"""safe-push.py pure-unit checks: race classifier, rebase ownership, source guards (no git spawns).

This is the only safe-push suite the pre-push hook-tests gate runs. The git-heavy suites
(push/race paths, refusals) live in _tests/integration/, which the gate does not discover:
under heavy machine load each took 600-1000s, past the gate's 240s per-file budget.
Run them by hand after any change to safe-push.py:
    python maintenance/_tests/integration/test_safe_push_core.py
    python maintenance/_tests/integration/test_safe_push_refusals.py
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "safe-push.py")

_spec = importlib.util.spec_from_file_location("safe_push", TOOL)
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)

HDR = "To C:/x/origin.git\n"


class SafePushUnitTest(unittest.TestCase):
    def test_classifier_each_pattern_individually(self):
        line = HDR + "!\tHEAD:refs/heads/main\t%s\nDone\n"
        self.assertTrue(sp.is_race(line % "[rejected] (fetch first)", "main"))
        self.assertTrue(sp.is_race(line % "[rejected] (non-fast-forward)", "main"))
        self.assertTrue(sp.is_race(line % "[remote rejected] (cannot lock ref 'refs/heads/main': is at 1a but expected 2b)", "main"))
        self.assertTrue(sp.is_race(line % "[remote rejected] (incorrect old value provided)", "main"))
        self.assertFalse(sp.is_race(line % "[remote rejected] (protected branch hook declined)", "main"))
        self.assertFalse(sp.is_race(line % "[rejected] (fetch first)", "other"))  # other ref
        self.assertFalse(sp.is_race(HDR + " ! [rejected]        main -> main (fetch first)", "main"))  # human form

    def test_status_shaped_gate_output_before_header_is_ignored(self):
        # the gate's log (e.g. pytest echoing these very tests) precedes git's "To <url>" block
        gate = "!\tHEAD:refs/heads/main\t[rejected] (fetch first)\nhook-tests-gate: 1 fail\n"
        self.assertFalse(sp.is_race(gate, "main"))  # no header at all: the push never reached git's status
        self.assertFalse(sp.is_race(gate + HDR + "!\tHEAD:refs/heads/main\t[remote rejected] (pre-receive hook declined)\n",
                                    "main"))

    def _rebase_dir(self, orig_head):
        root = tempfile.mkdtemp(prefix="safe-push-unit-")
        self.addCleanup(shutil.rmtree, root, True)
        d = os.path.join(root, "rebase-merge")
        os.makedirs(d)
        with open(os.path.join(d, "orig-head"), "w") as f:
            f.write(orig_head + "\n")
        return root, d

    def test_own_rebase_only_when_orig_head_matches(self):
        root, d = self._rebase_dir("aaa")
        real = sp.git_path
        sp.git_path = lambda repo, n: d if n == "rebase-merge" else os.path.join(root, "absent-" + n)
        try:
            self.assertTrue(sp.own_rebase(root, "aaa", "CONFLICT (content)"))
            self.assertFalse(sp.own_rebase(root, "bbb", "CONFLICT (content)"))  # a concurrent run's rebase
            self.assertFalse(sp.own_rebase(root, "aaa", "It seems that there is already a rebase-merge directory"))
        finally:
            sp.git_path = real

    def test_no_rebase_state_is_not_ours(self):
        real = sp.git_path
        sp.git_path = lambda repo, n: os.path.join(tempfile.gettempdir(), "definitely-absent-" + n)
        try:
            self.assertFalse(sp.own_rebase(".", "aaa", "fatal: index.lock exists"))
        finally:
            sp.git_path = real

    def test_source_never_forces_or_skips_hooks(self):
        src = open(TOOL, encoding="utf-8").read()
        for bad in ("--force", "--no-verify", "-f\"", "+HEAD", "--autostash", "--for", "no-ver"):
            self.assertNotIn(bad, src, bad)


if __name__ == "__main__":
    unittest.main()

"""Tests for maintenance/propagate-task-spec.py (register-scheduled-task v2.29 steps 4-6).

Run: python maintenance/_tests/test_propagate_task_spec.py
"""
import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pts", HERE / "propagate-task-spec.py")
pts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pts)


class PropagateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def pair(self, src_bytes, live_bytes):
        src, live = self.tmp / "src.md", self.tmp / "live" / "SKILL.md"
        live.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(src_bytes)
        live.write_bytes(live_bytes)
        return src, live

    def test_writes_in_live_eol_style_and_backs_up(self):
        src, live = self.pair(b"a\r\nB\r\nc\r\n", b"a\nb\nc\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertTrue(r.ok, r.reason)
        self.assertEqual(live.read_bytes(), b"a\nB\nc\n")
        self.assertEqual((live.parent / "SKILL.md.bak-t").read_bytes(), b"a\nb\nc\n")

    def test_dry_run_changes_nothing(self):
        src, live = self.pair(b"a\nB\n", b"a\nb\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=False)
        self.assertTrue(r.ok, r.reason)
        self.assertEqual(live.read_bytes(), b"a\nb\n")
        self.assertFalse((live.parent / "SKILL.md.bak-t").exists())

    def test_refuses_more_replaced_lines_than_planned(self):
        src, live = self.pair(b"X\nY\nc\n", b"a\nb\nc\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertFalse(r.ok)
        self.assertEqual(live.read_bytes(), b"a\nb\nc\n")

    def test_refuses_mixed_eol_live(self):
        src, live = self.pair(b"a\nB\n", b"a\r\nb\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertFalse(r.ok)
        self.assertIn("mixed", r.reason)

    def test_existing_backup_is_never_overwritten(self):
        src, live = self.pair(b"a\nB\n", b"a\nb\n")
        bak = live.parent / "SKILL.md.bak-t"
        bak.write_bytes(b"a\nb\n")  # matching backup from an interrupted earlier run
        before = bak.stat().st_mtime_ns
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertTrue(r.ok, r.reason)
        self.assertEqual(bak.read_bytes(), b"a\nb\n")
        self.assertEqual(bak.stat().st_mtime_ns, before)

    def test_missing_live_is_refusal_not_crash(self):
        src, live = self.pair(b"a\n", b"a\n")
        live.unlink()
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertFalse(r.ok)
        self.assertFalse(live.exists())

    def test_unplanned_insertions_are_capped(self):
        src, live = self.pair(b"a\nX\nY\nZ\nb\n", b"a\nb\n")
        r = pts.propagate(src, live, max_replaced=0, tag="t", apply=True)
        self.assertFalse(r.ok)
        self.assertEqual(live.read_bytes(), b"a\nb\n")

    def test_stale_backup_refuses(self):
        src, live = self.pair(b"a\nB\n", b"a\nb\n")
        (live.parent / "SKILL.md.bak-t").write_bytes(b"something else\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertFalse(r.ok)
        self.assertIn("stale backup", r.reason)
        self.assertEqual(live.read_bytes(), b"a\nb\n")

    def test_git_failure_is_refusal(self):
        src, live = self.pair(b"a\nB\n", b"a\nb\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True, git_repo=self.tmp)
        self.assertFalse(r.ok)
        self.assertEqual(live.read_bytes(), b"a\nb\n")

    def test_git_committed_blob_match_and_uncommitted_refusal(self):
        repo = self.tmp / "repo"
        (repo / "scheduled-tasks" / "t").mkdir(parents=True)
        run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)
        run("init", "-q")
        run("config", "core.autocrlf", "true")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        src = repo / "scheduled-tasks" / "t" / "SKILL.md"
        src.write_bytes(b"a\r\nB\r\n")
        run("add", ".")
        run("commit", "-qm", "x")
        live = self.tmp / "live" / "SKILL.md"
        live.parent.mkdir()
        live.write_bytes(b"a\nb\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True, git_repo=repo)
        self.assertTrue(r.ok, r.reason)
        self.assertEqual(live.read_bytes(), b"a\nB\n")
        src.write_bytes(b"a\r\nC\r\n")  # edited, not committed
        r = pts.propagate(src, live, max_replaced=1, tag="t2", apply=True, git_repo=repo)
        self.assertFalse(r.ok)
        self.assertIn("commit it first", r.reason)
        self.assertEqual(live.read_bytes(), b"a\nB\n")

    def test_identical_is_noop_not_error(self):
        src, live = self.pair(b"a\n", b"a\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertTrue(r.ok)
        self.assertEqual(r.reason, "unchanged")


if __name__ == "__main__":
    unittest.main(verbosity=2)

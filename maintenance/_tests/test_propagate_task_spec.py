"""Tests for maintenance/propagate-task-spec.py (register-scheduled-task v2.29 steps 4-6).

Run: python maintenance/_tests/test_propagate_task_spec.py
"""
import importlib.util
import pathlib
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
        (live.parent / "SKILL.md.bak-t").write_bytes(b"original\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertTrue(r.ok, r.reason)
        self.assertEqual((live.parent / "SKILL.md.bak-t").read_bytes(), b"original\n")

    def test_identical_is_noop_not_error(self):
        src, live = self.pair(b"a\n", b"a\n")
        r = pts.propagate(src, live, max_replaced=1, tag="t", apply=True)
        self.assertTrue(r.ok)
        self.assertEqual(r.reason, "unchanged")


if __name__ == "__main__":
    unittest.main(verbosity=2)

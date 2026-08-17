"""Tests for update-memory-index-line.py's pure upsert_line() logic.

Stdlib only -- run with `python test_update_memory_index_line.py` (no pytest).
Covers the 2026-08-16 fix for MEMORY.md's missing single-writer protocol: index
pointer lines were being silently clobbered by concurrent sessions doing plain
Read+Edit. These tests exercise only the pure content-transform function; the
file-I/O retry/atomic-write layer is exercised by the live end-to-end run this
tool was built and proven against (see event_log.md 2026-08-16 entry).
"""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "update_memory_index_line",
    Path(__file__).resolve().parent / "update-memory-index-line.py",
)
umil = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(umil)


class UpsertLine(unittest.TestCase):
    def test_replaces_matching_line_in_place(self):
        content = "line a\n- **[Old Pointer](old.md)** — stale summary\nline c\n"

        new_content, changed = umil.upsert_line(
            content, r"\[Old Pointer\]", "- **[New Pointer](new.md)** — fresh summary"
        )

        self.assertTrue(changed)
        self.assertEqual(
            new_content,
            "line a\n- **[New Pointer](new.md)** — fresh summary\nline c\n",
        )

    def test_identical_line_is_a_noop(self):
        line = "- **[Pointer](p.md)** — summary"
        content = "a\n%s\nb\n" % line

        new_content, changed = umil.upsert_line(content, r"\[Pointer\]", line)

        self.assertFalse(changed)
        self.assertEqual(new_content, content)

    def test_inserts_after_anchor_when_no_match(self):
        content = "## Section\n- existing line\n## Next Section\n"

        new_content, changed = umil.upsert_line(
            content, r"\[Nonexistent\]", "- **[New](n.md)** — brand new",
            anchor_after_re=r"^## Section$",
        )

        self.assertTrue(changed)
        self.assertEqual(
            new_content,
            "## Section\n- **[New](n.md)** — brand new\n- existing line\n## Next Section\n",
        )

    def test_no_match_and_no_anchor_raises(self):
        content = "a\nb\nc\n"

        with self.assertRaises(ValueError):
            umil.upsert_line(content, r"\[Nonexistent\]", "- new line")

    def test_no_match_and_anchor_also_missing_raises(self):
        content = "a\nb\nc\n"

        with self.assertRaises(ValueError):
            umil.upsert_line(
                content, r"\[Nonexistent\]", "- new line",
                anchor_after_re=r"\[AlsoNonexistent\]",
            )

    def test_only_first_match_is_replaced(self):
        # A regex matching more than one line (e.g. a topic keyword appearing in
        # two unrelated pointer entries) must not touch the second occurrence --
        # callers are expected to supply a specific-enough --match.
        content = "- **[Rev 15](a.md)** — audit note\n- **[Rev 15 detail](b.md)** — audit note 2\n"

        new_content, changed = umil.upsert_line(content, r"Rev 15", "- **[Rev 16](c.md)** — new")

        self.assertTrue(changed)
        self.assertEqual(
            new_content,
            "- **[Rev 16](c.md)** — new\n- **[Rev 15 detail](b.md)** — audit note 2\n",
        )


if __name__ == "__main__":
    unittest.main()

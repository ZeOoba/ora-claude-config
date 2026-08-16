#!/usr/bin/env python3
"""Unit tests for append-event-log.py's frontmatter `modified:` stamping.

Closes a systemic metadata gap found 2026-08-16: the harness refreshes a memory
file's `modified:` frontmatter only when IT writes the file via Edit/Write. A
script write -- which is exactly what this tool does -- bypasses that. So every
append left `modified:` reading older than the file actually was, and the drift
compounds silently: event_log.md had accumulated 8 entries across 4 days while
still claiming `modified: 2026-08-12T20:13:19.038Z`.

That field is used to judge how current, and therefore how trustworthy, a memory
file is, so a stale stamp makes the canonical append-only log look less reliable
than it is.

Design note: stamp_modified() takes `when` as a parameter rather than calling
datetime.now() internally, so it stays a pure, deterministically-testable
function -- the same property insert_newest() documents about itself. The
callers supply the clock.
"""
import datetime
import importlib.util
import os
import tempfile
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "append-event-log.py")
spec = importlib.util.spec_from_file_location("append_event_log", MODULE_PATH)
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)

WHEN = datetime.datetime(2026, 8, 16, 19, 20, 1, 670000, tzinfo=datetime.timezone.utc)
EXPECTED = "2026-08-16T19:20:01.670Z"

DOC = (
    "---\n"
    "name: event_log\n"
    'description: "ORA append-only event log"\n'
    "metadata:\n"
    "  node_type: memory\n"
    "  type: log\n"
    "  modified: 2026-08-12T20:13:19.038Z\n"
    "---\n"
    "\n"
    "# ORA Event Log (append-only, newest first)\n"
    "\n"
    "## 2026-08-15 — an older entry\n"
    "\n"
    "body text mentioning modified: not-a-frontmatter-key\n"
)


class TestStampModified(unittest.TestCase):
    def test_refreshes_an_existing_frontmatter_stamp(self):
        out = ael.stamp_modified(DOC, when=WHEN)
        self.assertIn("  modified: " + EXPECTED, out)
        self.assertNotIn("2026-08-12T20:13:19.038Z", out)

    def test_is_deterministic_for_a_given_when(self):
        """Purity guard: same input + same clock -> same output, no hidden now()."""
        self.assertEqual(ael.stamp_modified(DOC, when=WHEN),
                         ael.stamp_modified(DOC, when=WHEN))

    def test_only_the_stamp_line_changes(self):
        out = ael.stamp_modified(DOC, when=WHEN)
        before = DOC.splitlines()
        after = out.splitlines()
        self.assertEqual(len(before), len(after))
        diffs = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(len(diffs), 1, "exactly one line should change")
        self.assertTrue(after[diffs[0]].strip().startswith("modified:"))

    def test_body_level_modified_is_not_touched(self):
        """A 'modified:' occurring in the BODY must never be rewritten."""
        out = ael.stamp_modified(DOC, when=WHEN)
        self.assertIn("body text mentioning modified: not-a-frontmatter-key", out)

    def test_no_frontmatter_is_left_unchanged(self):
        doc = "# Just a heading\n\n## 2026-08-15 — entry\n"
        self.assertEqual(ael.stamp_modified(doc, when=WHEN), doc)

    def test_frontmatter_without_a_modified_key_is_left_unchanged(self):
        """Conservative: do not invent a key the file never had."""
        doc = "---\nname: x\n---\n\n## 2026-08-15 — entry\n"
        self.assertEqual(ael.stamp_modified(doc, when=WHEN), doc)


class TestWritePathsStamp(unittest.TestCase):
    """Both write paths must stamp -- stamping only one would leave the gap open."""

    def _log(self):
        fd, path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(DOC)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_atomic_insert_stamps_and_appends(self):
        path = self._log()
        self.assertTrue(ael._atomic_insert(path, "## 2026-08-16 — new entry\n- x"))
        with open(path, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("## 2026-08-16 — new entry", out)
        self.assertNotIn("2026-08-12T20:13:19.038Z", out,
                         "atomic insert left the stamp stale")

    def test_inplace_insert_stamps_and_appends(self):
        path = self._log()
        self.assertTrue(ael._inplace_insert(path, "## 2026-08-16 — new entry\n- x"))
        with open(path, encoding="utf-8") as f:
            out = f.read()
        self.assertIn("## 2026-08-16 — new entry", out)
        self.assertNotIn("2026-08-12T20:13:19.038Z", out,
                         "in-place fallback left the stamp stale")


if __name__ == "__main__":
    unittest.main(verbosity=2)

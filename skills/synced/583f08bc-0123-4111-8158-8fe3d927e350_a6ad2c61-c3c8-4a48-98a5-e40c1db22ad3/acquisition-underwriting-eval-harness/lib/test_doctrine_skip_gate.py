"""Tests for doctrine_skip_gate -- the scheduled poll's changelog/description-only skip."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.doctrine_skip_gate import RUN, SKIP, classify  # noqa: E402

GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doctrine_skip_gate.py")

BASE = """---
name: acquisition-underwriting
description: "Trigger on: underwriting. v4.20"
---

# Acquisition Underwriting (v4.20)

**v4.20 (2026-09-10):** Length cap adopted.

## BODY TRIGGERS
Routing terms.

## STAGE -1 — INTAKE RULES
6. SF variance >5% -> HARD STOP.

## STAGE 1 — FLOORS
- Yield floor: stabilized YoC >8%.
"""


def edit(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class ClassifyTests(unittest.TestCase):
    def test_description_version_token_only_skips(self):
        cur = edit(BASE, "underwriting. v4.20", "underwriting. v4.21")
        self.assertEqual(classify(BASE, cur).decision, SKIP)

    def test_changelog_entry_added_skips(self):
        cur = edit(BASE, "**v4.20 (2026-09-10):**", "**v4.21 (2026-09-12):** New note.\n\n**v4.20 (2026-09-10):**")
        self.assertEqual(classify(BASE, cur).decision, SKIP)

    def test_stage_minus_one_edit_runs(self):
        # The defect in the first draft: STAGE -1 sits above STAGE 0 but is operative doctrine.
        cur = edit(BASE, ">5% -> HARD STOP", ">10% -> HARD STOP")
        self.assertEqual(classify(BASE, cur).decision, RUN)

    def test_floor_edit_runs(self):
        cur = edit(BASE, "YoC >8%", "YoC >7.5%")
        self.assertEqual(classify(BASE, cur).decision, RUN)

    def test_body_triggers_edit_runs(self):
        # Conservative: everything from the first ## heading on is never skippable.
        cur = edit(BASE, "Routing terms.", "Routing terms, more.")
        self.assertEqual(classify(BASE, cur).decision, RUN)

    def test_mixed_preamble_and_operative_edit_runs(self):
        cur = edit(BASE, "underwriting. v4.20", "underwriting. v4.21")
        cur = edit(cur, "YoC >8%", "YoC >9%")
        self.assertEqual(classify(BASE, cur).decision, RUN)

    def test_new_section_heading_inserted_runs(self):
        cur = edit(BASE, "## STAGE 1", "## STAGE 0.5 — NEW\nrule\n\n## STAGE 1")
        self.assertEqual(classify(BASE, cur).decision, RUN)

    def test_line_ending_only_change_skips(self):
        cur = BASE.replace("\n", "\r\n")
        self.assertEqual(classify(BASE, cur).decision, SKIP)

    def test_missing_heading_in_either_version_runs(self):
        headless = "---\nname: x\n---\n\nno sections at all\n"
        self.assertEqual(classify(headless, BASE).decision, RUN)
        self.assertEqual(classify(BASE, headless).decision, RUN)

    def test_empty_prior_runs(self):
        self.assertEqual(classify("", BASE).decision, RUN)

    def test_heading_text_moved_into_preamble_runs(self):
        # Deleting the first heading shifts operative text into the "preamble" -- must not skip.
        cur = edit(BASE, "## BODY TRIGGERS\n", "")
        self.assertEqual(classify(BASE, cur).decision, RUN)


class CliTests(unittest.TestCase):
    def _run(self, prior, current):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name, text in (("prior.md", prior), ("current.md", current)):
                p = os.path.join(d, name)
                if text is not None:
                    with open(p, "w", encoding="utf-8", newline="") as f:
                        f.write(text)
                paths.append(p)
            return subprocess.run(
                [sys.executable, GATE, "--prior", paths[0], "--current", paths[1]],
                capture_output=True, text=True,
            )

    def test_cli_skip_exit_0(self):
        r = self._run(BASE, edit(BASE, "underwriting. v4.20", "underwriting. v4.21"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["decision"], SKIP)

    def test_cli_run_exit_10(self):
        r = self._run(BASE, edit(BASE, "YoC >8%", "YoC >7%"))
        self.assertEqual(r.returncode, 10, r.stderr)
        self.assertEqual(json.loads(r.stdout)["decision"], RUN)

    def test_cli_missing_prior_snapshot_exit_10(self):
        r = self._run(None, BASE)
        self.assertEqual(r.returncode, 10, r.stderr)
        self.assertEqual(json.loads(r.stdout)["decision"], RUN)


if __name__ == "__main__":
    unittest.main()

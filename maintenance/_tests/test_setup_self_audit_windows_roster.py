#!/usr/bin/env python3
"""Tests for setup-self-audit.py's roster-driven windows-tasks check (2026-09-03).

Covers the classification the Automation Audit Rev 21 misread needed: a task rostered
`state=retired` reading Disabled is EXPECTED, never a finding; only Ready/Running is.
Pure functions only (parse_windows_roster / classify_windows_tasks) -- no PowerShell.

Run: python test_setup_self_audit_windows_roster.py
"""
import importlib.util
import os
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "setup-self-audit.py")
spec = importlib.util.spec_from_file_location("setup_self_audit", MODULE_PATH)
ssa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssa)

ROSTER = """
<!--BEGIN-WINDOWS-TASK-ROSTER-->
<!-- comment line, ignored -->
- ORA Fleet Dead-Man | state=active | crit=yes | exit1-ok=yes | note=exits 1 on alert
- ORA Nightly Disk Clean | state=active | crit=no | exit1-ok=no
- ClaudeFleetMirror | state=active | crit=no | exit1-ok=no
- ORA PM Crons | state=retired | crit=no | exit1-ok=no | since=2026-08-16 | superseded-by=ora-pm-daily-crons
<!--END-WINDOWS-TASK-ROSTER-->
"""


def entries():
    return ssa.parse_windows_roster(ROSTER)


def healthy_live():
    return {
        "ORA Fleet Dead-Man": ("Ready", "1"),          # exit1-ok -> clean
        "ORA Nightly Disk Clean": ("Ready", "0"),
        "ClaudeFleetMirror": ("Ready", "267009"),       # SCHED_S_TASK_RUNNING -> clean
        "ORA PM Crons": ("Disabled", "2147943467"),     # retired + Disabled + 0x8007042B -> expected
    }


class TestParse(unittest.TestCase):
    def test_parses_fields_and_skips_comments(self):
        e = entries()
        self.assertEqual([n for n, _ in e],
                         ["ORA Fleet Dead-Man", "ORA Nightly Disk Clean", "ClaudeFleetMirror", "ORA PM Crons"])
        self.assertEqual(e[3][1]["superseded-by"], "ora-pm-daily-crons")
        self.assertEqual(e[0][1]["exit1-ok"], "yes")

    def test_grammar_example_inside_html_comment_is_ignored(self):
        """The live 2026-09-03 defect: a '- <TaskName> | state=<active|retired> ...' grammar line
        inside the block's HTML comment was parsed as a (malformed) task line."""
        text = ROSTER.replace("<!-- comment line, ignored -->",
                              "<!-- grammar:\n     - <TaskName> | state=<active|retired> | crit=<yes|no> [| since=YYYY-MM-DD]\n     multi-line -->")
        e = ssa.parse_windows_roster(text)
        self.assertEqual(len(e), 4)

    def test_missing_markers_raise(self):
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster("no markers here")

    def test_malformed_line_raises(self):
        bad = ROSTER.replace("state=retired", "retired")
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster(bad)

    def test_empty_block_raises(self):
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster("<!--BEGIN-WINDOWS-TASK-ROSTER-->\n<!--END-WINDOWS-TASK-ROSTER-->")


    def test_crit_typo_raises_instead_of_downgrading(self):
        """crit=yees must not silently classify a CRIT task as WARN."""
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster(ROSTER.replace("crit=yes", "crit=yees"))

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster(ROSTER.replace(" | exit1-ok=no\n- ClaudeFleetMirror", "\n- ClaudeFleetMirror"))

    def test_duplicate_field_raises(self):
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster(ROSTER.replace("crit=no | exit1-ok=no\n- ClaudeFleetMirror",
                                                    "crit=no | crit=yes | exit1-ok=no\n- ClaudeFleetMirror"))

    def test_duplicate_task_name_raises(self):
        with self.assertRaises(ValueError):
            ssa.parse_windows_roster(ROSTER.replace("<!--END-WINDOWS-TASK-ROSTER-->",
                                                    "- ORA Nightly Disk Clean | state=active | crit=no | exit1-ok=no\n<!--END-WINDOWS-TASK-ROSTER-->"))


class TestClassify(unittest.TestCase):
    def test_empty_live_set_is_crit_every_active_missing(self):
        """A completed query with ZERO rows is a real answer: the whole backbone is gone."""
        status, detail, _ = ssa.classify_windows_tasks(entries(), {})
        self.assertEqual(status, "CRIT")
        for name in ("ORA Fleet Dead-Man MISSING", "ORA Nightly Disk Clean MISSING", "ClaudeFleetMirror MISSING"):
            self.assertIn(name, detail)
        self.assertNotIn("ORA PM Crons MISSING", detail)   # retired + absent = expected

    def test_three_tuple_rows_with_task_path_are_accepted(self):
        live = {k: v + ("\\",) for k, v in healthy_live().items()}
        live["ORA Brand New Thing"] = ("Ready", "0", "\\Sub\\")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("ORA Brand New Thing (folder \\Sub\\) is live but has no line", detail)

    def test_all_healthy_including_retired_disabled_is_ok(self):
        status, detail, _ = ssa.classify_windows_tasks(entries(), healthy_live())
        self.assertEqual(status, "OK", detail)
        self.assertIn("3 active", detail)
        self.assertIn("1 retired", detail)

    def test_retired_and_absent_is_ok(self):
        live = healthy_live()
        del live["ORA PM Crons"]
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "OK", detail)

    def test_retired_but_ready_is_documented_retired_but_alive(self):
        live = healthy_live()
        live["ORA PM Crons"] = ("Ready", "0")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("documented-retired-but-alive", detail)
        self.assertIn("ora-pm-daily-crons", detail)

    def test_retired_0x8007042B_is_not_reported(self):
        """The exact Rev 21 misread: Disabled + 0x8007042B on a retired task."""
        status, detail, _ = ssa.classify_windows_tasks(entries(), healthy_live())
        self.assertNotIn("8007042B", detail)
        self.assertNotIn("2147943467", detail)

    def test_active_crit_missing_is_crit(self):
        live = healthy_live()
        del live["ORA Fleet Dead-Man"]
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "CRIT")
        self.assertIn("ORA Fleet Dead-Man MISSING", detail)

    def test_active_crit_disabled_is_crit(self):
        live = healthy_live()
        live["ORA Fleet Dead-Man"] = ("Disabled", "0")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "CRIT")
        self.assertIn("Disabled but rostered active", detail)

    def test_active_noncrit_missing_is_warn(self):
        live = healthy_live()
        del live["ClaudeFleetMirror"]
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("ClaudeFleetMirror MISSING", detail)

    def test_exit1_is_warn_only_when_not_by_design(self):
        live = healthy_live()
        live["ORA Nightly Disk Clean"] = ("Ready", "1")   # exit1-ok=no
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("ORA Nightly Disk Clean last result 0x1", detail)
        self.assertNotIn("Dead-Man", detail)              # exit1-ok=yes stays clean

    def test_bad_result_is_decoded(self):
        live = healthy_live()
        live["ORA Nightly Disk Clean"] = ("Ready", "2147946720")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("0x800710E0", detail)

    def test_live_unrostered_task_is_untracked_warn(self):
        live = healthy_live()
        live["ORA Brand New Thing"] = ("Ready", "0")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "WARN")
        self.assertIn("ORA Brand New Thing is live but has no line", detail)

    def test_crit_wins_over_warn(self):
        live = healthy_live()
        del live["ORA Fleet Dead-Man"]
        live["ORA Brand New Thing"] = ("Ready", "0")
        status, detail, _ = ssa.classify_windows_tasks(entries(), live)
        self.assertEqual(status, "CRIT")
        self.assertIn("MISSING", detail)
        self.assertIn("untracked", detail)


if __name__ == "__main__":
    unittest.main(verbosity=1)

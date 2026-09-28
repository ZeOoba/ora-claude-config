import csv
import json
import os
import shutil
import tempfile
import unittest

from record_run import record_run


def _result(deal_id, status="PASS", scored=True):
    return {"deal_id": deal_id, "status": status, "scored": scored}


class TestRecordRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="eval_harness_runs_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_dated_snapshot_json(self):
        out = record_run(
            [_result("a"), _result("b", status="FLAG")],
            self.tmp,
            skill_sha="abc123",
            run_label="unit-test",
            run_timestamp="2026-08-14T120000Z",
        )
        self.assertTrue(os.path.exists(out["snapshot_path"]))
        with open(out["snapshot_path"]) as f:
            snap = json.load(f)
        self.assertEqual(snap["scored_deals"], 2)
        self.assertEqual(snap["scored_pass"], 1)
        self.assertEqual(snap["scored_flag"], 1)
        self.assertEqual(snap["skill_sha"], "abc123")

    def test_informational_rows_excluded_from_scored_counts(self):
        out = record_run(
            [_result("a", scored=True), _result("b", scored=False, status="FLAG")],
            self.tmp,
            run_timestamp="2026-08-14T120100Z",
        )
        self.assertEqual(out["summary"]["scored_deals"], 1)
        self.assertEqual(out["summary"]["informational_deals"], 1)

    def test_second_run_appends_not_overwrites(self):
        record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T120200Z")
        record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T130200Z")
        json_files = [f for f in os.listdir(self.tmp) if f.endswith(".json")]
        self.assertEqual(len(json_files), 2)
        with open(os.path.join(self.tmp, "summary.csv")) as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 3)  # header + 2 runs

    def test_refuses_to_clobber_same_timestamp(self):
        record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T120300Z")
        with self.assertRaises(ValueError):
            record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T120300Z")

    def test_empty_results_rejected(self):
        with self.assertRaises(ValueError):
            record_run([], self.tmp)

    def test_missing_required_key_rejected(self):
        with self.assertRaises(ValueError):
            record_run([{"deal_id": "a"}], self.tmp)  # missing status/scored

    def test_run_label_with_unsafe_filename_characters_is_sanitized(self):
        """REFUTE-pass finding: SKILL.md's own Step 4 example run_label
        ('post-<doctrine-change>') contains characters invalid in Windows
        filenames; a colon in a label crashes outright. Must not raise and
        must not silently produce a mis-scoped file."""
        out = record_run(
            [_result("a")],
            self.tmp,
            run_label="post-<doctrine-change>: v4.12",
            run_timestamp="2026-08-14T120400Z",
        )
        self.assertTrue(os.path.exists(out["snapshot_path"]))
        for char in '<>:"/\\|?*':
            self.assertNotIn(char, os.path.basename(out["snapshot_path"]))

    def test_no_orphaned_tmp_file_after_clobber_refusal(self):
        record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T120500Z")
        with self.assertRaises(ValueError):
            record_run([_result("a")], self.tmp, run_timestamp="2026-08-14T120500Z")
        tmp_files = [f for f in os.listdir(self.tmp) if f.endswith(".tmp")]
        self.assertEqual(tmp_files, [], f"orphaned temp file(s): {tmp_files}")


if __name__ == "__main__":
    unittest.main()

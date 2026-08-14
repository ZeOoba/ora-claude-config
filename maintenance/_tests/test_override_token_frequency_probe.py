#!/usr/bin/env python3
"""Unit tests for override-token-frequency-probe.py (OI-136).

Isolates the probe from the real ~/.claude/hooks/sessions tree by monkeypatching its
module-level path constants to a tempdir per test, mirroring test_fleet_contract_check.py's
approach of exercising the pure logic directly rather than the real filesystem.
"""
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

MODULE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "override-token-frequency-probe.py"
)
spec = importlib.util.spec_from_file_location("override_token_frequency_probe", MODULE_PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def _touch(path, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("scope: test\n")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


class OverrideTokenFrequencyProbeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sessions_dir = os.path.join(self.tmpdir, "sessions")
        self.archive_dir = os.path.join(self.sessions_dir, "_archive_override_tokens")
        self.sweep_log = os.path.join(self.tmpdir, "override-token-sweep.log")
        os.makedirs(self.archive_dir, exist_ok=True)

        self._orig_sessions_dir = probe.SESSIONS_DIR
        self._orig_archive_dir = probe.ARCHIVE_DIR
        self._orig_sweep_log = probe.SWEEP_LOG
        probe.SESSIONS_DIR = self.sessions_dir
        probe.ARCHIVE_DIR = self.archive_dir
        probe.SWEEP_LOG = self.sweep_log

        self.now = datetime.datetime(2026, 8, 13, 12, 0, 0).timestamp()

    def tearDown(self):
        probe.SESSIONS_DIR = self._orig_sessions_dir
        probe.ARCHIVE_DIR = self._orig_archive_dir
        probe.SWEEP_LOG = self._orig_sweep_log
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _days_ago(self, days):
        return self.now - days * 86400.0

    # ---- empty state ----

    def test_no_sources_present_reports_nothing_and_no_signal(self):
        shutil.rmtree(self.archive_dir)  # not even the archive dir exists yet
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"], {})
        self.assertEqual(report["signals"], [])

    def test_empty_archive_dir_no_sweep_log_no_sessions_dir(self):
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"], {})
        self.assertEqual(report["signals"], [])

    # ---- archive-dir counting + the exact OI-136 shape ----

    def test_five_uses_in_window_trips_the_signal(self):
        for i in range(5):
            sid = "sid-%d" % i
            path = os.path.join(self.archive_dir, "%s_overrides_allow-hook-test-failure" % sid)
            _touch(path, mtime=self._days_ago(1))
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        entry = report["per_name"]["allow-hook-test-failure"]
        self.assertEqual(entry["count_trailing_window"], 5)
        self.assertEqual(entry["distinct_sessions_trailing_window"], 5)
        self.assertEqual(len(report["signals"]), 1)
        self.assertEqual(report["signals"][0]["name"], "allow-hook-test-failure")

    def test_four_uses_in_window_does_not_trip_the_signal(self):
        for i in range(4):
            sid = "sid-%d" % i
            path = os.path.join(self.archive_dir, "%s_overrides_allow-hook-test-failure" % sid)
            _touch(path, mtime=self._days_ago(1))
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"]["allow-hook-test-failure"]["count_trailing_window"], 4)
        self.assertEqual(report["signals"], [])

    def test_events_outside_trailing_window_land_in_prior_bucket(self):
        path = os.path.join(self.archive_dir, "sid-old_overrides_allow-config-write")
        _touch(path, mtime=self._days_ago(10))  # outside a 7-day trailing window
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        entry = report["per_name"]["allow-config-write"]
        self.assertEqual(entry["count_trailing_window"], 0)
        self.assertEqual(entry["count_prior_window"], 1)

    # ---- per-tier isolation ----

    def test_different_tiers_counted_independently(self):
        _touch(
            os.path.join(self.archive_dir, "sid-1_overrides_allow-hook-test-failure"),
            mtime=self._days_ago(1),
        )
        _touch(
            os.path.join(self.archive_dir, "sid-2_overrides_allow-config-write"),
            mtime=self._days_ago(1),
        )
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"]["allow-hook-test-failure"]["count_trailing_window"], 1)
        self.assertEqual(report["per_name"]["allow-config-write"]["count_trailing_window"], 1)

    def test_legacy_flat_override_file_has_no_attributable_name_and_is_skipped(self):
        _touch(os.path.join(self.archive_dir, "sid-legacy_override"), mtime=self._days_ago(1))
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"], {})

    # ---- sweep-log fallback ----

    def test_sweep_log_fallback_when_archived_file_no_longer_exists(self):
        line = (
            "2026-08-12T10:00:00 ARCHIVED "
            r"C:\Users\Owner\.claude\hooks\sessions\sid-9\overrides\allow-hook-test-failure"
            " -> "
            r"C:\Users\Owner\.claude\hooks\sessions\_archive_override_tokens\sid-9_overrides_allow-hook-test-failure"
            "\n"
        )
        with open(self.sweep_log, "w", encoding="utf-8") as fh:
            fh.write(line)
        # archive dir stays empty -- the file the log points at is gone; log is the only source
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"]["allow-hook-test-failure"]["count_trailing_window"], 1)

    def test_sweep_log_malformed_line_is_skipped_not_fatal(self):
        with open(self.sweep_log, "w", encoding="utf-8") as fh:
            fh.write("this is not a valid sweep log line\n")
            fh.write("2026-08-12T10:00:00 LIVE sweep done: tokens-archived=3\n")
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"], {})

    def test_same_token_in_log_and_archive_dir_counted_once(self):
        line = (
            "2026-08-01T10:00:00 ARCHIVED "
            r"C:\...\sessions\sid-dup\overrides\allow-hook-test-failure"
            " -> "
            r"C:\...\_archive_override_tokens\sid-dup_overrides_allow-hook-test-failure"
            "\n"
        )
        with open(self.sweep_log, "w", encoding="utf-8") as fh:
            fh.write(line)
        _touch(
            os.path.join(self.archive_dir, "sid-dup_overrides_allow-hook-test-failure"),
            mtime=self._days_ago(1),
        )
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        # one session, one tier -> exactly one count, regardless of appearing in both sources
        self.assertEqual(report["per_name"]["allow-hook-test-failure"]["count_trailing_window"], 1)

    # ---- live (not-yet-swept) tokens ----

    def test_live_unswept_token_is_counted(self):
        live_path = os.path.join(self.sessions_dir, "sid-live", "overrides", "allow-hook-test-failure")
        _touch(live_path, mtime=self._days_ago(0.5))
        report = probe.build_report(window_days=7, threshold=5, now=self.now)
        self.assertEqual(report["per_name"]["allow-hook-test-failure"]["count_trailing_window"], 1)

    # ---- output formatting doesn't crash on either branch ----

    def test_human_format_handles_empty_and_signal_reports(self):
        empty_report = probe.build_report(window_days=7, threshold=5, now=self.now)
        text = probe.format_human(empty_report)
        self.assertIn("no override-token activity", text)

        for i in range(5):
            _touch(
                os.path.join(self.archive_dir, "sid-%d_overrides_allow-hook-test-failure" % i),
                mtime=self._days_ago(1),
            )
        signal_report = probe.build_report(window_days=7, threshold=5, now=self.now)
        text = probe.format_human(signal_report)
        self.assertIn("SIGNAL", text)
        self.assertIn("OI-136", text)


if __name__ == "__main__":
    unittest.main()

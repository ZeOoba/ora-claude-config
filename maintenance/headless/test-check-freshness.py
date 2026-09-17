#!/usr/bin/env python3
"""Tests for the freshness check. Run: python test-check-freshness.py

The cases that matter are the ones where a wrong answer costs Gabriel trust in
the pager: a registered-but-not-yet-due task must be SILENT, and a weekend must
not make the weekday-only mirror check look dead.
"""
import datetime
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("runcheck", os.path.join(HERE, "run-check.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
lib = rc.lib


def fake_task(found=True, last_run=None, next_run="tomorrow"):
    info = {"LastRunTime": last_run, "LastTaskResult": 0, "NextRunTime": next_run}
    return lambda _name: (found, info)


def write_heartbeat(state_dir, name, age_hours):
    path = os.path.join(state_dir, "%s-latest.json" % name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"check": name, "status": "CLEAN"}, fh)
    stamp = (datetime.datetime.now() - datetime.timedelta(hours=age_hours)).timestamp()
    os.utime(path, (stamp, stamp))
    return path


class Freshness(unittest.TestCase):
    def setUp(self):
        self._orig = rc._task_info
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.watched = {"demo": {"task": "ORA Headless - demo", "max_age_h": 30}}

    def tearDown(self):
        rc._task_info = self._orig
        self.tmp.cleanup()

    def run_check(self):
        r = lib.CheckResult("freshness")
        rc.check_freshness(r, watched=self.watched, state_dir=self.dir)
        return r

    def test_fresh_heartbeat_is_silent(self):
        rc._task_info = fake_task(last_run="2026-09-10T07:20:00")
        write_heartbeat(self.dir, "demo", age_hours=2)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_CLEAN)

    def test_stale_heartbeat_is_a_finding(self):
        rc._task_info = fake_task(last_run="2026-09-08T07:20:00")
        write_heartbeat(self.dir, "demo", age_hours=50)
        r = self.run_check()
        self.assertEqual(r.exit_code(), lib.EXIT_FINDINGS)
        self.assertIn("gone silent", r.findings[0]["summary"])

    def test_registered_but_never_fired_is_silent(self):
        """The window between registering and first fire must not page."""
        rc._task_info = fake_task(last_run="/Date(-2208988800000)/")  # 1900 sentinel
        r = self.run_check()
        self.assertEqual(r.exit_code(), lib.EXIT_CLEAN)
        self.assertTrue(any("not yet fired" in n for n in r.notes))

    def test_deleted_task_is_a_finding(self):
        rc._task_info = fake_task(found=False)
        r = self.run_check()
        self.assertEqual(r.exit_code(), lib.EXIT_FINDINGS)
        self.assertIn("no longer exists", r.findings[0]["summary"])

    def test_ran_but_wrote_nothing_is_a_finding(self):
        """Task fires, wrapper dies before reporting -- looks healthy to Windows."""
        rc._task_info = fake_task(last_run="2026-09-10T07:20:00")
        r = self.run_check()
        self.assertEqual(r.exit_code(), lib.EXIT_FINDINGS)
        self.assertIn("wrote no findings file", r.findings[0]["summary"])

    def test_unqueryable_task_is_cant_verify(self):
        rc._task_info = lambda _n: (None, None)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_CANT_VERIFY)

    def test_a_full_week_between_runs_stays_silent(self):
        """THE weekly case, and the reason the threshold is 176h (2026-09-17).

        All four checks are Monday-only. freshness runs Mon 07:50, BEFORE
        mirror-drift's Mon 10:55, so it necessarily reads LAST Monday's
        heartbeat: 168h - 3h05m = 164.9h. That is the NORMAL, healthy state --
        it must be silent, or the check pages every single week forever."""
        self.watched = {"mirror-drift": {"task": "ORA Headless - mirror-drift",
                                         "max_age_h": rc._WEEKLY_MAX_AGE_H}}
        rc._task_info = fake_task(last_run="2026-09-14T10:55:00")
        write_heartbeat(self.dir, "mirror-drift", age_hours=164.9)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_CLEAN)

    def test_the_old_weekday_threshold_would_now_false_page_every_week(self):
        """Guards the 96h -> 176h move: 96h was derived from a WEEKDAY cadence
        (Friday run still fresh on Monday). At weekly it is below the healthy
        floor, so it would fire on a check that is working perfectly."""
        self.watched = {"mirror-drift": {"task": "ORA Headless - mirror-drift", "max_age_h": 96}}
        rc._task_info = fake_task(last_run="2026-09-14T10:55:00")
        write_heartbeat(self.dir, "mirror-drift", age_hours=164.9)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_FINDINGS)

    def test_a_genuinely_missed_week_still_pages(self):
        """The threshold must not be so loose it stops detecting real silence:
        two missed Mondays (~333h) is a stopped check and must still fire."""
        self.watched = {"mirror-drift": {"task": "ORA Headless - mirror-drift",
                                         "max_age_h": rc._WEEKLY_MAX_AGE_H}}
        rc._task_info = fake_task(last_run="2026-09-07T10:55:00")
        write_heartbeat(self.dir, "mirror-drift", age_hours=332.9)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_FINDINGS)

    def test_catch_up_burst_ordering_does_not_false_page(self):
        """With StartWhenAvailable ON, a slept-through Monday fires all four
        missed triggers together with NO defined ordering, so freshness can run
        BEFORE the checks it ages -- reading a full 168h-old heartbeat. The
        thresholds, not the 07:50-after-07:20 offset, are what keep that quiet."""
        self.watched = {"integrity-guard": {"task": "ORA Headless - integrity-guard",
                                            "max_age_h": rc._WEEKLY_MAX_AGE_H}}
        rc._task_info = fake_task(last_run="2026-09-14T07:20:00")
        write_heartbeat(self.dir, "integrity-guard", age_hours=168.0)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_CLEAN)


class DateParsing(unittest.TestCase):
    def test_ps_epoch_format(self):
        self.assertEqual(rc._parse_ps_date("/Date(1757500800000)/").year, 2025)

    def test_iso_format(self):
        self.assertEqual(rc._parse_ps_date("2026-09-10T07:20:00").hour, 7)

    def test_us_locale_format(self):
        self.assertEqual(rc._parse_ps_date("09/10/2026 7:20:00 AM").hour, 7)

    def test_garbage_is_none_not_a_crash(self):
        self.assertIsNone(rc._parse_ps_date("not a date"))
        self.assertIsNone(rc._parse_ps_date(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)

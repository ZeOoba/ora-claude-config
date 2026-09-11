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

    def test_weekend_does_not_kill_the_weekday_only_check(self):
        """Friday 10:55 run, checked Monday 07:20 = ~66h. Must stay silent at 96h."""
        self.watched = {"mirror-drift": {"task": "ORA Headless - mirror-drift", "max_age_h": 96}}
        rc._task_info = fake_task(last_run="2026-09-04T10:55:00")
        write_heartbeat(self.dir, "mirror-drift", age_hours=66)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_CLEAN)

    def test_thirty_hour_threshold_would_have_false_paged_on_that_weekend(self):
        """Guards the reason mirror-drift gets 96h and not the daily 30h."""
        self.watched = {"mirror-drift": {"task": "ORA Headless - mirror-drift", "max_age_h": 30}}
        rc._task_info = fake_task(last_run="2026-09-04T10:55:00")
        write_heartbeat(self.dir, "mirror-drift", age_hours=66)
        self.assertEqual(self.run_check().exit_code(), lib.EXIT_FINDINGS)


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

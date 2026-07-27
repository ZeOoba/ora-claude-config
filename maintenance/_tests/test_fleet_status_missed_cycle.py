#!/usr/bin/env python3
"""Unit tests for fleet-status.py's missed-single-cycle detector (OI-031).

Closes the gap that let ora-master-workbook-ingest's 2026-07-20 Monday fire
go unnoticed for a full week: never_ran_overdue only covers tasks that have
NEVER fired; expired_needs_attention only covers expired one-time tasks;
throttle skips only cover a task that fired and got rate-limited. None of the
three catch an established recurring task silently skipping its most recent
single scheduled cycle -- that is what find_missed_cycles() checks.
"""
import datetime
import importlib.util
import os
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet-status.py")
spec = importlib.util.spec_from_file_location("fleet_status", MODULE_PATH)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)


class TestFindMissedCycles(unittest.TestCase):
    def setUp(self):
        # Fixed "now": Monday 2026-07-27 15:00 local, well past a 05:45 Monday cron.
        self.now_local = datetime.datetime(2026, 7, 27, 15, 0, 0)

    def _iso_utc(self, dt_local, offset_hours=4):
        """Helper: render a local datetime as the UTC 'Z' string lastRunAt uses."""
        utc = dt_local + datetime.timedelta(hours=offset_hours)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def test_flags_a_genuinely_missed_weekly_cycle(self):
        # cron fires Mondays 05:45; last real run was 8 days ago (missed last Monday).
        last_run = self.now_local - datetime.timedelta(days=8)
        tasks = [{
            "id": "ora-master-workbook-ingest", "_fleet": "cc", "enabled": True,
            "cronExpression": "45 5 * * 1",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        ids = [m["id"] for m in out]
        self.assertIn("ora-master-workbook-ingest", ids)

    def test_does_not_flag_a_task_that_fired_this_cycle(self):
        # Fired this morning at its 05:45 Monday slot -- current, not missed.
        last_run = self.now_local.replace(hour=5, minute=50, second=0, microsecond=0)
        tasks = [{
            "id": "ora-master-workbook-ingest", "_fleet": "cc", "enabled": True,
            "cronExpression": "45 5 * * 1",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])

    def test_within_grace_window_not_flagged(self):
        # Late by a few hours (Desktop app opened late that morning) -- within
        # the 24h grace, this is normal catch-up behavior, not a miss.
        last_run = self.now_local.replace(hour=9, minute=0, second=0, microsecond=0)
        tasks = [{
            "id": "ora-am-brief", "_fleet": "cc", "enabled": True,
            "cronExpression": "0 6 * * *",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])

    def test_disabled_task_never_flagged(self):
        last_run = self.now_local - datetime.timedelta(days=30)
        tasks = [{
            "id": "ora-paused-thing", "_fleet": "cc", "enabled": False,
            "cronExpression": "45 5 * * 1",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])

    def test_one_time_task_never_flagged(self):
        tasks = [{
            "id": "ora-one-off", "_fleet": "cc", "enabled": True,
            "cronExpression": None, "fireAt": 1700000000000,
            "lastRunAt": self._iso_utc(self.now_local - datetime.timedelta(days=90)),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])

    def test_never_ran_task_not_this_checks_job(self):
        # No lastRunAt at all -- that is never_ran/never_ran_overdue's job.
        tasks = [{
            "id": "ora-brand-new", "_fleet": "lams", "enabled": True,
            "cronExpression": "45 5 * * 1", "lastRunAt": None,
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])

    def test_non_fixed_cron_not_flagged(self):
        # Frequent/step crons ('*/n') aren't single-fixed-time -- cron_hm()
        # returns None for these, so this detector correctly stays silent
        # rather than guessing.
        tasks = [{
            "id": "ora-frequent-thing", "_fleet": "cc", "enabled": True,
            "cronExpression": "*/15 * * * *",
            "lastRunAt": self._iso_utc(self.now_local - datetime.timedelta(days=5)),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

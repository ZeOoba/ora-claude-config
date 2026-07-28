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

    def test_compound_dom_dow_cron_uses_first_match_semantics_not_or(self):
        # Real incident, 2026-07-28: ora-entry-market-scan uses "0 11 1-7 * 2"
        # (day-of-month 1-7 AND day-of-week Tuesday -- "first Tuesday of the
        # month", the live scheduler's actual nextRunAt behavior, confirmed by
        # the fact that nextRunAt skipped Aug 1-3 (dom-only OR-matches) and
        # landed on Aug 4, the first AND-match). POSIX cron's textbook OR
        # semantics (fire if EITHER field matches, when both are restricted)
        # would instead treat this as "every day 1-7 OR every Tuesday" and
        # falsely expect an 11:00 fire on ANY Tuesday -- e.g. today,
        # 2026-07-28 (a Tuesday, but the 28th -- outside 1-7 and NOT the
        # AND-match date). That false expectation, compared against a real
        # lastRunAt from an off-cycle manual run on 07-22, manufactured a
        # bogus 137-hour "missed cycle" (fleet-status --json,
        # expected_fire_utc: 2026-07-28T15:00Z) for a task that was only
        # registered 2026-07-16 and has never actually missed a real fire --
        # its true next occurrence (first Tuesday within days 1-7) is
        # 2026-08-04, not yet due. Task registered after July's AND-match
        # (07-07) had already passed, so no real cycle exists to compare
        # against yet -- this detector must stay silent, not invent one via
        # OR semantics.
        last_run = datetime.datetime(2026, 7, 22, 18, 9, 15)  # the real manual run
        now_local = datetime.datetime(2026, 7, 28, 15, 0, 0)  # a Tuesday, day 28
        tasks = [{
            "id": "ora-entry-market-scan", "_fleet": "cc", "enabled": True,
            "cronExpression": "0 11 1-7 * 2",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=now_local)
        self.assertEqual(out, [], "compound dom+dow cron must use AND (intersection) "
                                   "semantics to match the live scheduler, not POSIX OR")


if __name__ == "__main__":
    unittest.main(verbosity=2)

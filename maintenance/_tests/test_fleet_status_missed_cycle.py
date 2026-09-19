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
        # cron fires Mondays 05:45; last real run was 16 days ago -- two
        # consecutive weekly slots missed (unambiguous starvation, gap well
        # past the 1.5x-cadence cron-aware threshold), not just this week's
        # slot still catching up.
        last_run = self.now_local - datetime.timedelta(days=16)
        tasks = [{
            "id": "ora-master-workbook-ingest", "_fleet": "cc", "enabled": True,
            "cronExpression": "45 5 * * 1",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        ids = [m["id"] for m in out]
        self.assertIn("ora-master-workbook-ingest", ids)

    def test_weekly_task_mid_catchup_not_flagged(self):
        # CRON-AWARE GUARD regression (2026-08-10 live false positive, 8 of
        # 13 flagged entries): a weekly task whose own current-day slot
        # simply has not dispatched yet during a throttle-contended catch-up
        # burst reads a raw gap of ~1 cadence interval against the flat 24h
        # grace and gets misreported as starved. It is not -- it will fire
        # later the same day as the burst drains.
        last_run = self.now_local - datetime.timedelta(hours=175)
        tasks = [{
            "id": "ora-weekly-task", "_fleet": "cc", "enabled": True,
            "cronExpression": "45 5 * * 1",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=self.now_local)
        self.assertEqual(out, [], "one un-dispatched slot (~1x weekly cadence) must "
                                   "not flag as a missed cycle")

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


    def test_multifire_weekday_cron_prior_gap_not_used_as_interval(self):
        # Adversarial-review regression (2026-08-11): deriving "the task's own
        # interval" from only the SINGLE most recent inter-fire hop picks up
        # the weekend/day-boundary outlier when sampled right at the FIRST
        # fire of the day (Fri 19:40 -> Mon 07:40 = 60h for this cron), which
        # inflates the threshold enough to hide multiple real consecutive
        # misses. (Sampling later in the day, after a same-day fire has
        # already happened, hits the same-day 6h hop instead and does not
        # reproduce this -- the bug is specifically in the first-fire-of-the-
        # day / first-fire-of-the-week sampling window.)
        now_local = datetime.datetime(2026, 8, 3, 8, 0, 0)  # a Monday, just past 07:40
        last_run = now_local - datetime.timedelta(hours=90)  # ~5 missed weekday fires
        tasks = [{
            "id": "ora-lease-snapshot-refresh", "_fleet": "cc", "enabled": True,
            "cronExpression": "40 7,13,19 * * 1-5",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=now_local)
        ids = [m["id"] for m in out]
        self.assertIn("ora-lease-snapshot-refresh", ids,
                      "5 consecutive missed weekday fires must still flag, even "
                      "sampled on a Monday where the single most-recent hop is "
                      "the 60h+ weekend gap, not the task's true ~6h cadence")

    def test_weekday_daily_cron_missed_friday_and_monday_flagged(self):
        # Same class of bug for a plain weekday-only daily cron: sampled on a
        # Monday, the single most-recent hop is the 72h weekend gap, which
        # must not be mistaken for "this task's normal cadence is 72h."
        now_local = datetime.datetime(2026, 8, 3, 15, 0, 0)  # a Monday
        last_run = now_local - datetime.timedelta(hours=96)  # missed Fri AND Mon
        tasks = [{
            "id": "ora-weekday-daily-task", "_fleet": "cc", "enabled": True,
            "cronExpression": "45 5 * * 1-5",
            "lastRunAt": self._iso_utc(last_run),
        }]
        out = fs.find_missed_cycles(tasks, now_local=now_local)
        ids = [m["id"] for m in out]
        self.assertIn("ora-weekday-daily-task", ids,
                      "missing both Friday's and Monday's weekday-cron fires "
                      "must flag despite the 72h weekend gap in the sample")


class TestCronHms(unittest.TestCase):
    """Unit tests for cron_hms() / cron_hm() multi-fire parsing (2026-08-09).

    Closes the gap flagged 2026-07-27c and still open 2026-08-09: cron_hm()
    called int(hr)/int(mn) directly, so a multi-fire hour field like "7,13,19"
    raised ValueError and the whole task vanished from cron_hm()'s output --
    not undercounted, completely invisible -- to AM-pileup, collision
    detection, and the missed-cycle detector alike."""

    def test_single_fire_unchanged(self):
        self.assertEqual(fs.cron_hms("40 7 * * 1-5"), [(7, 40)])
        self.assertEqual(fs.cron_hm("40 7 * * 1-5"), (7, 40))

    def test_multifire_comma_hours_parsed(self):
        # ora-lease-snapshot-refresh's real cron.
        self.assertEqual(fs.cron_hms("40 7,13,19 * * 1-5"), [(7, 40), (13, 40), (19, 40)])

    def test_multifire_returns_none_from_cron_hm(self):
        # cron_hm() stays a single-fire-only accessor -- multi-fire callers
        # must use cron_hms() explicitly, so any call site not yet updated
        # fails closed (silently excluded) rather than picking an arbitrary
        # one of the fire times.
        self.assertIsNone(fs.cron_hm("40 7,13,19 * * 1-5"))

    def test_wildcard_hour_or_minute_not_a_fixed_time(self):
        self.assertIsNone(fs.cron_hms("*/15 * * * *"))
        self.assertIsNone(fs.cron_hms("0 * * * *"))
        self.assertIsNone(fs.cron_hms("* 7 * * *"))

    def test_hour_range_expands_like_a_list(self):
        self.assertEqual(fs.cron_hms("0 7-9 * * *"), [(7, 0), (8, 0), (9, 0)])

    def test_malformed_field_fails_closed(self):
        self.assertIsNone(fs.cron_hms("0 not-a-cron * * *"))


class TestMultiFireMissedCycle(unittest.TestCase):
    """most_recent_expected_fire_utc() must check every fire time of a
    multi-fire cron, not just the (nonexistent) single one, and pick the most
    recent one at/before now_local."""

    def test_picks_latest_fire_time_at_or_before_now(self):
        # 07:40/13:40/19:40 weekdays; "now" is Wed 15:00 -- most recent
        # expected fire is today's 13:40, not 07:40 or yesterday's 19:40.
        now_local = datetime.datetime(2026, 7, 29, 15, 0, 0)  # a Wednesday
        expected = fs.most_recent_expected_fire_utc("40 7,13,19 * * 1-5", now_local)
        self.assertEqual(expected, datetime.datetime(2026, 7, 29, 13, 40) -
                          fs._local_utc_offset())

    def test_multifire_task_missing_a_cycle_is_flagged(self):
        # Last real run was 07:40 two days ago -- both the 13:40/19:40 slots
        # that day and the next full day's three slots were silently skipped.
        now_local = datetime.datetime(2026, 7, 29, 15, 0, 0)
        last_run = now_local - datetime.timedelta(days=2)
        tasks = [{
            "id": "ora-lease-snapshot-refresh", "_fleet": "cc", "enabled": True,
            "cronExpression": "40 7,13,19 * * 1-5",
            "lastRunAt": last_run.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }]
        out = fs.find_missed_cycles(tasks, now_local=now_local)
        ids = [m["id"] for m in out]
        self.assertIn("ora-lease-snapshot-refresh", ids)

    def test_multifire_task_current_not_flagged(self):
        # Fired at today's 13:40 slot -- current, not missed.
        now_local = datetime.datetime(2026, 7, 29, 15, 0, 0)
        last_run = now_local.replace(hour=13, minute=45)
        tasks = [{
            "id": "ora-lease-snapshot-refresh", "_fleet": "cc", "enabled": True,
            "cronExpression": "40 7,13,19 * * 1-5",
            "lastRunAt": last_run.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }]
        out = fs.find_missed_cycles(tasks, now_local=now_local)
        self.assertEqual(out, [])


class TestPauseAwareMissedCycles(unittest.TestCase):
    """2026-09-12: the first health-guard run after the 09-07 -> 09-11 CC pause listed 11
    'missed' tasks, every one of whose missed slots fell inside the pause. Hours a task
    was held by a RECORDED pause (_shared/pause_windows.py) are subtracted before the
    gap is judged; explained entries move to a separate list instead of vanishing."""

    def setUp(self):
        import tempfile
        pw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared",
                               "pause_windows.py")
        s = importlib.util.spec_from_file_location("pause_windows", pw_path)
        self.pw = importlib.util.module_from_spec(s)
        s.loader.exec_module(self.pw)
        self.store = os.path.join(tempfile.mkdtemp(prefix="fsmc_"), "fleet-pause-windows.json")
        utc = datetime.timezone.utc
        self.pw.record_window("cc", datetime.datetime(2026, 9, 7, 17, 7, 11, tzinfo=utc),
                              datetime.datetime(2026, 9, 11, 20, 1, 42, tzinfo=utc),
                              task_ids=["ora-deal-aging-sla"], key="cc:t", path=self.store)
        self.now_local = datetime.datetime(2026, 9, 12, 16, 26, 1)  # Saturday, live replay

    def _task(self, tid="ora-deal-aging-sla", last="2026-09-07T16:03:56.824Z"):
        return [{"id": tid, "_fleet": "cc", "enabled": True,
                 "cronExpression": "25 9 * * 1-5", "lastRunAt": last}]

    def test_no_pause_store_keeps_legacy_behaviour(self):
        out = fs.find_missed_cycles(self._task(), now_local=self.now_local)
        self.assertEqual([m["id"] for m in out], ["ora-deal-aging-sla"])

    def test_gap_inside_recorded_pause_is_explained_not_missed(self):
        explained = []
        out = fs.find_missed_cycles(self._task(), now_local=self.now_local,
                                    pause_store=self.store, explained_out=explained)
        self.assertEqual(out, [])
        self.assertEqual([m["id"] for m in explained], ["ora-deal-aging-sla"])
        self.assertGreater(explained[0]["pause_hours"], 90)
        self.assertLessEqual(explained[0]["effective_gap_hours"], explained[0]["threshold_hours"])

    def test_pause_for_a_different_task_does_not_excuse(self):
        explained = []
        out = fs.find_missed_cycles(self._task(tid="ora-sofr-direct-prefetch"),
                                    now_local=self.now_local, pause_store=self.store,
                                    explained_out=explained)
        self.assertEqual([m["id"] for m in out], ["ora-sofr-direct-prefetch"])
        self.assertEqual(explained, [])

    def test_gap_that_started_long_before_the_pause_still_flags(self):
        # last ran 08-20: ~18 days stale before the pause even began
        explained = []
        out = fs.find_missed_cycles(self._task(last="2026-08-20T13:30:00.000Z"),
                                    now_local=self.now_local, pause_store=self.store,
                                    explained_out=explained)
        self.assertEqual([m["id"] for m in out], ["ora-deal-aging-sla"])
        self.assertGreater(out[0]["pause_hours"], 90)
        self.assertEqual(explained, [])

    def test_unreadable_pause_store_flags_as_before(self):
        with open(self.store, "w") as fh:
            fh.write("{broken")
        out = fs.find_missed_cycles(self._task(), now_local=self.now_local,
                                    pause_store=self.store, explained_out=[])
        self.assertEqual([m["id"] for m in out], ["ora-deal-aging-sla"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

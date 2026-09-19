#!/usr/bin/env python3
"""Tests for _shared/pause_windows.py -- the DURABLE record of past bounded pauses.

WHY THIS EXISTS. _shared/fleet_pause.py answers "is this fleet paused RIGHT NOW". The
moment the resume task fires, that answer becomes "no" and the pause window is gone, so
every detector that looks BACK across the pause has nothing to read. Live 2026-09-12:
the first ora-health-guard run after the 2026-09-07 -> 09-11 pause reported 5 FAILs, 3 of
which were the pause itself.

DESIGN HISTORY THESE TESTS PIN. The first two cuts inferred pause membership by parsing
the resume task's SKILL.md text. Two adversarial refute passes (2026-09-12) found ten ways
that could HIDE a real miss (prose or bulleted carve-outs, efficacy checks saying
"re-enable", cancelled-then-repaused merges, early hand re-enables, ids in code blocks,
manual re-runs stretching windows...). All share one cause: text is not state. The
module now records OBSERVED registry state -- a task is "held" at a capture only if it is
actually disabled AND a resume that names it is pending -- so every one of those cases
is decided by the registry, not by wording.

Run: python _tests/test_pause_windows.py   (exit 0 = pass)
"""
import datetime
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(os.path.dirname(HERE), "_shared", "pause_windows.py")
spec = importlib.util.spec_from_file_location("pause_windows", MOD)
pw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pw)

UTC = datetime.timezone.utc


def dt(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=UTC)


def ms(d):
    return int(d.timestamp() * 1000)


IDS = ["t0", "t1", "t2", "t3", "t4", "t5"]


class Fleet:
    """A mutable fake registry: recurring tasks t0..t5 (+ extras) and optional one-time tasks."""

    def __init__(self, extra_recurring=()):
        self.dir = tempfile.mkdtemp(prefix="pw_")
        self.reg = os.path.join(self.dir, "scheduled-tasks.json")
        self.store = os.path.join(self.dir, "fleet-pause-windows.json")
        self.tasks = {i: {"id": i, "cronExpression": "0 6 * * *", "enabled": True,
                          "lastRunAt": "2026-09-01T10:00:00.000Z"}
                      for i in IDS + list(extra_recurring)}
        self.onetime = {}

    def set_enabled(self, ids, enabled):
        for i in ids:
            self.tasks[i]["enabled"] = enabled

    def ran(self, i, when):
        self.tasks[i]["lastRunAt"] = when.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def add_resume(self, tid, text, fire, enabled=True, fired_at=None):
        p = os.path.join(self.dir, tid + ".md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        t = {"id": tid, "fireAt": ms(fire), "enabled": enabled, "filePath": p,
             "createdAt": ms(dt(2026, 9, 1))}
        if fired_at:
            t["lastRunAt"] = fired_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        self.onetime[tid] = t

    def capture(self, now):
        with open(self.reg, "w", encoding="utf-8") as fh:
            json.dump({"scheduledTasks": list(self.tasks.values()) + list(self.onetime.values())}, fh)
        return pw.capture(fleets=("cc",), registries={"cc": self.reg}, path=self.store, now=now)

    def hours(self, task, start, end):
        return pw.overlap_hours("cc", task, start, end, path=self.store)


RESUME = "Re-enable exactly these:\n" + "\n".join("%d. %s" % (n + 1, i) for n, i in enumerate(IDS))


class TestObservedPause(unittest.TestCase):
    def test_basic_pause_observed_across_captures(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 11, 20))
        for d in (7, 8, 9, 10, 11):
            f.capture(dt(2026, 9, d, 18))
        f.set_enabled(IDS, True)
        f.onetime["resume"]["enabled"] = False
        f.onetime["resume"]["lastRunAt"] = "2026-09-11T20:01:00.000Z"
        f.capture(dt(2026, 9, 12, 0))
        # held from first disabled observation to last disabled observation -- never beyond
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 96.0)

    def test_disabled_without_pending_resume_is_not_a_pause(self):
        f = Fleet()
        f.set_enabled(["t0"], False)            # disabled for its own reasons, no resume
        f.capture(dt(2026, 9, 7))
        f.capture(dt(2026, 9, 9))
        self.assertEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 0.0)

    def test_single_observation_counts_zero_hours(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 11, 20))
        f.capture(dt(2026, 9, 7, 18))
        self.assertEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 0.0)


class TestRefutedCases(unittest.TestCase):
    """Every case the two 2026-09-12 refute passes used to hide a real miss."""

    def test_carve_outs_in_prose_or_bullets_are_never_covered(self):
        f = Fleet(extra_recurring=("heartbeat", "monitor"))
        text = ("Carve-outs, never paused, do NOT touch:\n- heartbeat\n- monitor\n\n" + RESUME)
        f.set_enabled(IDS, False)                # carve-outs stay enabled
        f.add_resume("resume", text, fire=dt(2026, 9, 11, 20))
        for d in (7, 8, 9, 10):
            f.capture(dt(2026, 9, d))
        self.assertEqual(f.hours("heartbeat", dt(2026, 9, 1), dt(2026, 9, 13)), 0.0)
        self.assertGreater(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 0.0)

    def test_efficacy_check_saying_reenable_creates_nothing(self):
        f = Fleet()
        text = "If any of these is disabled, re-enable it:\n" + "\n".join("- " + i for i in IDS)
        f.add_resume("check", text, fire=dt(2026, 9, 15))   # tasks all enabled
        for d in (1, 5, 10, 14):
            f.capture(dt(2026, 9, d))
        self.assertEqual(f.hours("t0", dt(2026, 8, 30), dt(2026, 9, 16)), 0.0)

    def test_cancelled_then_repaused_does_not_bridge_the_live_gap(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 20))
        f.capture(dt(2026, 9, 2))
        f.capture(dt(2026, 9, 3))                # held 24h
        f.set_enabled(IDS, True)                 # pause cancelled by hand
        f.capture(dt(2026, 9, 5))
        f.set_enabled(IDS, False)                # re-paused later
        f.capture(dt(2026, 9, 10))
        f.capture(dt(2026, 9, 12))               # held 48h
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 72.0)

    def test_task_that_ran_between_captures_splits_the_interval(self):
        # machine asleep between captures: task re-enabled, ran, re-disabled, unobserved
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 20))
        f.capture(dt(2026, 9, 2))
        f.capture(dt(2026, 9, 3))
        f.ran("t0", dt(2026, 9, 4, 6))           # re-enabled, ran, re-disabled -- unobserved
        f.capture(dt(2026, 9, 4, 12))
        f.capture(dt(2026, 9, 5))
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 36.0)
        self.assertAlmostEqual(f.hours("t1", dt(2026, 9, 1), dt(2026, 9, 13)), 72.0)

    def test_task_reenabled_early_by_hand_stops_being_covered(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 12))
        f.capture(dt(2026, 9, 5))
        f.capture(dt(2026, 9, 6))
        f.set_enabled(["t0"], True)
        for d in (7, 8, 9, 10, 11):
            f.capture(dt(2026, 9, d))
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 24.0)
        self.assertAlmostEqual(f.hours("t1", dt(2026, 9, 1), dt(2026, 9, 13)), 144.0)

    def test_resume_long_overdue_and_never_fired_stops_excusing(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 5))
        f.capture(dt(2026, 9, 4))
        f.capture(dt(2026, 9, 5, 12))            # 12h past fireAt: still a catch-up window
        f.capture(dt(2026, 9, 8))                # 3 days overdue: no longer a pause
        f.capture(dt(2026, 9, 9))
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 36.0)

    def test_manual_rerun_of_fired_resume_cannot_reopen_anything(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 5))
        f.capture(dt(2026, 9, 3))
        f.capture(dt(2026, 9, 4))
        f.set_enabled(IDS, True)
        f.onetime["resume"]["lastRunAt"] = "2026-09-05T00:00:00.000Z"
        f.capture(dt(2026, 9, 6))
        f.onetime["resume"]["lastRunAt"] = "2026-09-30T00:00:00.000Z"
        f.capture(dt(2026, 9, 30))
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 10, 2)), 24.0)


class TestThirdRefute(unittest.TestCase):
    """Third refute pass 2026-09-12 (against the observation design)."""

    def test_B_reminder_naming_one_disabled_task_is_not_a_pause(self):
        f = Fleet()
        f.set_enabled(["t0"], False)            # disabled by accident
        f.add_resume("reminder", "Re-check whether t0 alerts are still useful.",
                     fire=dt(2027, 1, 1))
        for d in range(1, 11):
            f.capture(dt(2026, 9, d))
        self.assertEqual(f.hours("t0", dt(2026, 8, 30), dt(2026, 9, 12)), 0.0)

    def test_B_observed_interval_is_capped(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 12, 1))
        d0 = dt(2026, 9, 1)
        for n in range(0, 40):
            f.capture(d0 + datetime.timedelta(days=n))
        # a hold longer than MAX_WINDOW_DAYS is not a bounded pause: excuse NONE of it
        self.assertEqual(f.hours("t0", dt(2026, 8, 30), dt(2026, 10, 15)), 0.0)

    def test_A_long_unobserved_span_is_not_bridged(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 20))
        f.capture(dt(2026, 9, 2))
        f.capture(dt(2026, 9, 2, 12))            # 12h held
        f.capture(dt(2026, 9, 6))                # 3.5 days unobserved -> new interval
        f.capture(dt(2026, 9, 6, 12))            # 12h held
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 24.0)

    def test_overnight_unobserved_span_is_bridged(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 20))
        f.capture(dt(2026, 9, 2, 0))
        f.capture(dt(2026, 9, 2, 16))            # 16h sleep gap: still one interval
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 16.0)

    def test_deleted_task_interval_closes_and_is_not_bridged_on_recreation(self):
        f = Fleet()
        f.set_enabled(IDS, False)
        f.add_resume("resume", RESUME, fire=dt(2026, 9, 20))
        f.capture(dt(2026, 9, 2))
        f.capture(dt(2026, 9, 2, 12))
        gone = f.tasks.pop("t0")
        f.capture(dt(2026, 9, 3))
        f.tasks["t0"] = gone                     # re-created, still disabled and named
        f.capture(dt(2026, 9, 3, 6))
        f.capture(dt(2026, 9, 3, 12))
        self.assertAlmostEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 18.0)


class TestManualRecords(unittest.TestCase):
    def setUp(self):
        self.f = Fleet()
        pw.record_window("cc", dt(2026, 9, 7, 17, 7), dt(2026, 9, 11, 20, 1),
                         task_ids=["t0", "t1"], key="cc:pause-a", note="backfill",
                         path=self.f.store)

    def test_full_containment(self):
        self.assertAlmostEqual(self.f.hours("t0", dt(2026, 9, 7, 15, 36), dt(2026, 9, 12, 20, 21)),
                               98.9, places=1)

    def test_other_task_not_covered(self):
        self.assertEqual(self.f.hours("t5", dt(2026, 9, 7), dt(2026, 9, 12)), 0.0)

    def test_other_fleet_not_covered(self):
        self.assertEqual(pw.overlap_hours("lams", "t0", dt(2026, 9, 7), dt(2026, 9, 12),
                                          path=self.f.store), 0.0)

    def test_upsert_by_key_and_partial_edges(self):
        pw.record_window("cc", dt(2026, 9, 7, 17, 7), dt(2026, 9, 11, 0, 1),
                         task_ids=["t0"], key="cc:pause-a", path=self.f.store)
        self.assertEqual(len(pw.load_windows(self.f.store)), 1)
        self.assertAlmostEqual(self.f.hours("t0", dt(2026, 9, 10, 0, 1), dt(2026, 9, 13)), 24.0)

    def test_manual_window_over_cap_is_refused(self):
        with self.assertRaises(ValueError):
            pw.record_window("cc", dt(2026, 8, 1), dt(2026, 9, 1), task_ids=["t0"],
                             key="cc:too-long", path=self.f.store)

    def test_manual_and_observed_do_not_double_count(self):
        self.f.set_enabled(["t0", "t1", "t2", "t3", "t4", "t5"], False)
        self.f.add_resume("resume", RESUME, fire=dt(2026, 9, 12))
        self.f.capture(dt(2026, 9, 8))
        self.f.capture(dt(2026, 9, 10))
        self.assertAlmostEqual(self.f.hours("t0", dt(2026, 9, 7, 17, 7), dt(2026, 9, 11, 20, 1)),
                               98.9, places=1)


class TestFailureModes(unittest.TestCase):
    def test_corrupt_store_reads_empty_flags_error_and_refuses_write(self):
        f = Fleet()
        with open(f.store, "w") as fh:
            fh.write("{not json")
        wins, err = pw.load_windows(f.store, with_error=True)
        self.assertEqual(wins, [])
        self.assertTrue(err)
        out = f.capture(dt(2026, 9, 7))
        self.assertTrue(out["errors"])
        with open(f.store) as fh:
            self.assertEqual(fh.read(), "{not json")
        self.assertEqual(f.hours("t0", dt(2026, 9, 1), dt(2026, 9, 13)), 0.0)

    def test_capture_never_raises_on_missing_registry(self):
        f = Fleet()
        out = pw.capture(fleets=("cc",), registries={"cc": os.path.join(f.dir, "nope.json")},
                         path=f.store, now=dt(2026, 9, 7))
        self.assertTrue(out["errors"])

    def test_no_store_means_zero(self):
        self.assertEqual(pw.overlap_hours("cc", "x", dt(2026, 1, 1), dt(2026, 1, 2),
                                          path=os.path.join(tempfile.mkdtemp(), "absent.json")), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=1)

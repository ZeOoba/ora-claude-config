#!/usr/bin/env python3
"""Unit tests for fleet-status.py's collision / cross-fleet-duplicate reporting.

Closes the defect found by Automation Audit R13-3 (2026-08-16): the same task id
registered on BOTH fleets was reported as a same-time "collision" whose member
list contained a SINGLE name -- because the inner loop deduped by task id and
discarded the fleet. A collision of one is nonsense on its face, and it actively
misled a reader into recommending the wrong copy be retired (the hazardous
direction: a same-id cross-fleet delete is folder-destructive).

The two conditions are genuinely different and have different remedies:
  * COLLISION        -- two DIFFERENT tasks fire at the same time. Remedy: retime
                        one of them. Cheap and safe.
  * CROSS-FLEET DUP  -- the SAME task id is registered on both fleets. Remedy: a
                        supervised single-writer retirement of one copy, with
                        opposite archive/delete ordering per fleet. Hazardous.

A duplicate is also detected INDEPENDENTLY of cron here: two copies of one task
with DIFFERENT schedules are still a duplicate, and were invisible to the old
time-bucketed logic entirely.
"""
import importlib.util
import os
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet-status.py")
spec = importlib.util.spec_from_file_location("fleet_status", MODULE_PATH)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)


def task(tid, cron, fleet, enabled=True):
    return {"id": tid, "cronExpression": cron, "_fleet": fleet, "enabled": enabled}


class TestCrossFleetDuplicates(unittest.TestCase):
    def test_same_id_both_fleets_same_cron_is_a_duplicate_not_a_collision(self):
        """The R13-3 case: ora-passed-deal-tracker on cc AND lams, identical cron."""
        tasks = [
            task("ora-passed-deal-tracker", "30 6 15 * *", "cc"),
            task("ora-passed-deal-tracker", "30 6 15 * *", "lams"),
        ]
        collisions = fs.find_collisions(tasks)
        dups = fs.find_cross_fleet_duplicates(tasks)

        self.assertEqual(collisions, {}, "a same-id pair must NOT be reported as a collision")
        self.assertIn("ora-passed-deal-tracker", dups)
        self.assertEqual(sorted(dups["ora-passed-deal-tracker"]["fleets"]), ["cc", "lams"])

    def test_duplicate_is_detected_even_when_crons_differ(self):
        """Time-bucketed logic missed this entirely -- same task, two schedules."""
        tasks = [
            task("ora-thing", "30 6 15 * *", "cc"),
            task("ora-thing", "0 12 * * 1", "lams"),
        ]
        dups = fs.find_cross_fleet_duplicates(tasks)
        self.assertIn("ora-thing", dups)
        self.assertEqual(sorted(dups["ora-thing"]["fleets"]), ["cc", "lams"])
        self.assertEqual(fs.find_collisions(tasks), {})

    def test_single_fleet_task_is_not_a_duplicate(self):
        tasks = [task("ora-solo", "0 9 * * *", "cc")]
        self.assertEqual(fs.find_cross_fleet_duplicates(tasks), {})

    def test_same_id_twice_on_ONE_fleet_is_still_reported(self):
        """Refute-pass catch: excluding same-id pairs from find_collisions() would
        otherwise make a duplicate REGISTRATION on a single fleet invisible in both
        detectors. That is a documented failure mode (duplicate-id registration,
        2026-07-08), so it must still surface -- flagged as NOT cross-fleet."""
        tasks = [
            task("ora-twice", "0 9 * * *", "cc"),
            task("ora-twice", "0 9 * * *", "cc"),
        ]
        dups = fs.find_cross_fleet_duplicates(tasks)
        self.assertIn("ora-twice", dups)
        self.assertFalse(dups["ora-twice"]["cross_fleet"])
        self.assertEqual(fs.find_collisions(tasks), {})

    def test_cross_fleet_pair_is_flagged_cross_fleet(self):
        tasks = [
            task("ora-both", "0 9 * * *", "cc"),
            task("ora-both", "0 9 * * *", "lams"),
        ]
        self.assertTrue(fs.find_cross_fleet_duplicates(tasks)["ora-both"]["cross_fleet"])


class TestGenuineCollisions(unittest.TestCase):
    def test_two_distinct_tasks_sharing_a_day_collide(self):
        """Regression guard: the real collision case must keep working."""
        tasks = [
            task("ora-a", "0 9 * * *", "cc"),
            task("ora-b", "0 9 * * 1-5", "lams"),
        ]
        collisions = fs.find_collisions(tasks)
        self.assertIn("09:00", collisions)
        self.assertEqual(sorted(collisions["09:00"]), ["ora-a", "ora-b"])

    def test_same_time_different_days_is_not_a_collision(self):
        """Pre-existing crons_share_a_day() behaviour must be preserved (Mon vs Wed)."""
        tasks = [
            task("ora-a", "30 13 * * 1", "cc"),
            task("ora-b", "30 13 * * 3", "cc"),
        ]
        self.assertEqual(fs.find_collisions(tasks), {})

    def test_duplicate_and_a_real_collision_in_the_same_bucket(self):
        """A duplicate pair must not mask a genuine third-task collision at that time."""
        tasks = [
            task("ora-dup", "30 6 15 * *", "cc"),
            task("ora-dup", "30 6 15 * *", "lams"),
            task("ora-other", "30 6 15 * *", "cc"),
        ]
        collisions = fs.find_collisions(tasks)
        dups = fs.find_cross_fleet_duplicates(tasks)

        self.assertIn("ora-dup", dups)
        self.assertIn("06:30", collisions)
        self.assertEqual(sorted(collisions["06:30"]), ["ora-dup", "ora-other"])

    def test_multi_fire_cron_still_buckets_into_every_fire_time(self):
        """Preserve the 2026-08-09 cron_hms() fix."""
        tasks = [
            task("ora-multi", "40 7,13,19 * * 1-5", "cc"),
            task("ora-single", "40 13 * * 1-5", "cc"),
        ]
        collisions = fs.find_collisions(tasks)
        self.assertIn("13:40", collisions)
        self.assertEqual(sorted(collisions["13:40"]), ["ora-multi", "ora-single"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

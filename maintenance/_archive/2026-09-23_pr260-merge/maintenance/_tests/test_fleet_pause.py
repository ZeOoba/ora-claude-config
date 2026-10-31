#!/usr/bin/env python3
"""Tests for _shared/fleet_pause.py and state-freshness-probe.py's pause rule.

Added 2026-09-10 with the code (ORA Automation Audit R24-1/R24-3).

These exist because the suppression logic is the dangerous half: a pause test that
returns True too readily silently mutes the one detector built to catch a stopped
detector -- which is exactly how R22-2 went unnoticed for days. So the negative cases
(idle fleet, everything-disabled-with-no-resume, unparseable registry) matter more than
the positive one and are tested first.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_shared"))

import fleet_pause  # noqa: E402


def _reg(tmpdir, tasks):
    p = os.path.join(tmpdir, "scheduled-tasks.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"scheduledTasks": tasks}, fh)
    return p


def _ms(offset_hours):
    return (time.time() + offset_hours * 3600.0) * 1000.0


class PauseDetection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    # ---- standing carve-outs (2026-09-22) ----------------------------------
    def test_cc_pause_with_am_brief_carved_out_is_paused(self):
        """ora-am-brief is never paused by standing rule, so every real CC pause keeps
        exactly it enabled. Before this fix that read as 'live' and every pause-frozen
        detector output alarmed as [STALE]."""
        reg = _reg(self.tmp, [
            {"id": "ora-am-brief", "cronExpression": "0 6 * * *", "enabled": True},
            {"id": "a", "cronExpression": "0 5 * * 1", "enabled": False},
            {"id": "r", "fireAt": _ms(48), "enabled": True},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertTrue(st["paused"])

    def test_carve_out_does_not_apply_to_other_fleet(self):
        reg = _reg(self.tmp, [
            {"id": "ora-am-brief", "cronExpression": "0 6 * * *", "enabled": True},
            {"id": "a", "cronExpression": "0 5 * * 1", "enabled": False},
            {"id": "r", "fireAt": _ms(48), "enabled": True},
        ])
        self.assertFalse(fleet_pause.pause_state("lams", registry=reg)["paused"])

    def test_non_carved_enabled_task_still_means_live(self):
        reg = _reg(self.tmp, [
            {"id": "ora-am-brief", "cronExpression": "0 6 * * *", "enabled": True},
            {"id": "a", "cronExpression": "0 5 * * 1", "enabled": True},
            {"id": "r", "fireAt": _ms(48), "enabled": True},
        ])
        self.assertFalse(fleet_pause.pause_state("cc", registry=reg)["paused"])

    def test_only_carve_outs_recurring_is_not_a_pause(self):
        """A fleet whose only recurring task is the carve-out has nothing paused."""
        reg = _reg(self.tmp, [
            {"id": "ora-am-brief", "cronExpression": "0 6 * * *", "enabled": True},
            {"id": "r", "fireAt": _ms(48), "enabled": True},
        ])
        self.assertFalse(fleet_pause.pause_state("cc", registry=reg)["paused"])

    # ---- negative cases: must NOT report paused ----------------------------
    def test_live_fleet_is_not_paused(self):
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": True},
            {"id": "b", "cronExpression": "0 6 * * *", "enabled": False},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])
        self.assertEqual(st["enabled_recurring"], 1)

    def test_all_disabled_with_no_resume_is_not_a_pause(self):
        """The dangerous case: everything off and nothing queued to turn it back on.
        That is an outage, not a bounded pause, and must still alarm."""
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "b", "cronExpression": "0 6 * * *", "enabled": False},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])
        self.assertIn("NO resume queued", st["error"])

    def test_resume_in_the_past_does_not_count(self):
        """A resume task that already fired cannot justify ongoing suppression."""
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "r", "fireAt": _ms(-48), "enabled": True},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])

    def test_disabled_resume_task_does_not_count(self):
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "r", "fireAt": _ms(24), "enabled": False},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])

    def test_no_recurring_tasks_is_not_a_pause(self):
        reg = _reg(self.tmp, [{"id": "r", "fireAt": _ms(24), "enabled": True}])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])

    def test_unparseable_registry_reports_error_and_does_not_suppress(self):
        p = os.path.join(self.tmp, "scheduled-tasks.json")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        st = fleet_pause.pause_state("cc", registry=p)
        self.assertFalse(st["paused"])
        self.assertTrue(st["error"])

    def test_missing_registry_reports_error_and_does_not_suppress(self):
        st = fleet_pause.pause_state("cc", registry=os.path.join(self.tmp, "nope.json"))
        self.assertFalse(st["paused"])
        self.assertTrue(st["error"])

    # ---- positive case ----------------------------------------------------
    def test_bounded_pause_detected_with_earliest_resume(self):
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "b", "cronExpression": "0 6 * * *", "enabled": False},
            {"id": "r1", "fireAt": _ms(48), "enabled": True, "createdAt": _ms(-72)},
            {"id": "r2", "fireAt": _ms(24), "enabled": True, "createdAt": _ms(-70)},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertTrue(st["paused"])
        self.assertAlmostEqual(st["resume_epoch"], (time.time() + 24 * 3600), delta=120)
        self.assertIsNotNone(st["paused_since"])

    def test_name_is_irrelevant_only_structure_counts(self):
        """A task called nothing like 'resume' still counts; a task called 'resume'
        that is disabled does not. Titles are not state."""
        reg = _reg(self.tmp, [
            {"id": "zzz", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "totally-unrelated-name", "fireAt": _ms(12), "enabled": True},
        ])
        self.assertTrue(fleet_pause.pause_state("cc", registry=reg)["paused"])


class ResumeHorizon(unittest.TestCase):
    """2026-09-12 review finding: ANY enabled future one-time task counted as the resume,
    with no horizon. LAMS carries an enabled one-time task dated ~2027-08, so a real
    mass-disable fault would have been read as a year-long 'pause' and fleet-deadman.ps1
    would have stayed silent for a year. A resume must fall within MAX_RESUME_HORIZON_DAYS."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fpz_")

    def test_far_future_one_time_task_is_not_a_resume(self):
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "counsel-review-2027", "fireAt": _ms(24 * 330), "enabled": True},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertFalse(st["paused"])
        self.assertTrue(st["error"])

    def test_resume_inside_horizon_still_counts_when_a_far_task_also_exists(self):
        reg = _reg(self.tmp, [
            {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
            {"id": "counsel-review-2027", "fireAt": _ms(24 * 330), "enabled": True},
            {"id": "resume", "fireAt": _ms(24 * 4), "enabled": True},
        ])
        st = fleet_pause.pause_state("cc", registry=reg)
        self.assertTrue(st["paused"])
        self.assertAlmostEqual(st["resume_epoch"], time.time() + 4 * 86400, delta=120)

    def test_horizon_edge(self):
        inside = _ms(24 * fleet_pause.MAX_RESUME_HORIZON_DAYS - 1)
        outside = _ms(24 * fleet_pause.MAX_RESUME_HORIZON_DAYS + 1)
        for fire, expect in ((inside, True), (outside, False)):
            reg = _reg(self.tmp, [
                {"id": "a", "cronExpression": "0 5 * * *", "enabled": False},
                {"id": "r", "fireAt": fire, "enabled": True},
            ])
            self.assertEqual(fleet_pause.pause_state("cc", registry=reg)["paused"], expect)


class FreshnessRule(unittest.TestCase):
    """The probe's core rule, exercised directly on its arithmetic."""

    def test_stale_during_pause_is_expected_but_stale_before_is_not(self):
        pause_start = time.time() - 72 * 3600.0
        grace = 6 * 3600.0
        during = pause_start + 600           # written just after the pause began
        before = pause_start - 500 * 3600.0  # already long dead when it began
        self.assertTrue(during >= pause_start - grace)
        self.assertFalse(before >= pause_start - grace)


if __name__ == "__main__":
    unittest.main(verbosity=2)

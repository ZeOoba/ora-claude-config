#!/usr/bin/env python3
"""Unit tests for phantom-dispatch-probe.py -- synthetic fixtures ONLY.

Never asserts against the live %APPDATA%\\Claude\\logs tree: those rotate and
would make the suite time-dependent (same discipline as
test-stuck-session-watchdog.ps1, which tests Get-KillCandidates against
synthetic process records and never against real processes).
"""
import datetime
import importlib.util
import pathlib
import sys
import unittest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "phantom_dispatch_probe", _HERE / "phantom-dispatch-probe.py")
pdp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pdp)


def L(ts, level, prefix, msg):
    return f"{ts} [{level}] [{prefix}] {msg}"


def spawn(ts, task, prefix="CCDScheduledTasks"):
    return L(ts, "info", prefix,
             "Spawning new session for scheduled task %s { cronExpression: '5 7 * * *', "
             "fireAt: undefined, lastRunAt: '2026-08-04T11:45:05.316Z', missed: undefined }" % task)


def confirm(ts, task, prefix="CCDScheduledTasks"):
    return L(ts, "info", prefix, "Confirmed task run for: %s" % task)


def stale(ts, task, prefix="CCDScheduledTasks"):
    return L(ts, "warn", prefix, "Cleared stale pending dispatch for: %s" % task)


NOW = datetime.datetime(2026, 8, 5, 12, 0, 0)


class TestParse(unittest.TestCase):
    def test_parses_all_three_event_kinds(self):
        ev = pdp.parse_events([
            spawn("2026-08-05 07:14:41", "ora-task-integrity-guard"),
            confirm("2026-08-05 07:14:45", "ora-task-integrity-guard"),
            stale("2026-08-05 07:20:22", "ora-task-integrity-guard"),
        ])
        self.assertEqual([e.kind for e in ev], ["spawn", "confirm", "stale"])
        self.assertEqual(ev[0].ts, datetime.datetime(2026, 8, 5, 7, 14, 41))
        self.assertEqual(ev[0].task, "ora-task-integrity-guard")

    def test_recognises_both_fleets(self):
        ev = pdp.parse_events([
            spawn("2026-08-05 07:14:41", "a", prefix="CCDScheduledTasks"),
            spawn("2026-08-05 07:14:42", "b", prefix="ScheduledTasks"),
        ])
        self.assertEqual([e.fleet for e in ev], ["CC/MCP", "LAMS/Cowork"])

    def test_dedupes_double_written_lines(self):
        # The desktop app writes most CCDScheduledTasks lines twice, verbatim.
        line = spawn("2026-08-05 07:14:41", "ora-x")
        self.assertEqual(len(pdp.parse_events([line, line])), 1)

    def test_ignores_unrelated_and_malformed_lines(self):
        ev = pdp.parse_events([
            "2026-08-05 07:14:37 [info] [process-memory] trigger=interval tree_rss_sum=985MB",
            "2026-08-05 07:05:22 [info] [CCDScheduledTasks] Delaying dispatch for ora-x by 559s (jitter)",
            "garbage",
            "",
        ])
        self.assertEqual(ev, [])

    def test_delaying_dispatch_is_not_a_spawn(self):
        # Jitter delay precedes the real spawn; counting it would double-count.
        ev = pdp.parse_events([
            "2026-08-05 07:05:22 [info] [CCDScheduledTasks] Delaying dispatch for ora-y by 559s (jitter)",
            spawn("2026-08-05 07:14:41", "ora-y"),
        ])
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0].kind, "spawn")


class TestClassify(unittest.TestCase):
    def classify(self, lines, now=NOW, hours=26):
        return pdp.find_phantoms(pdp.parse_events(lines), now=now, hours=hours)

    def test_spawn_then_confirm_is_healthy(self):
        self.assertEqual(self.classify([
            spawn("2026-08-05 11:05:25", "ora-doctrine-integrity-guard"),
            confirm("2026-08-05 11:05:26", "ora-doctrine-integrity-guard"),
        ]), [])

    def test_spawn_then_stale_clear_is_phantom(self):
        # The real 2026-08-05 ora-task-integrity-guard failure.
        ph = self.classify([
            spawn("2026-08-05 07:14:41", "ora-task-integrity-guard"),
            stale("2026-08-05 07:20:22", "ora-task-integrity-guard"),
        ])
        self.assertEqual(len(ph), 1)
        self.assertEqual(ph[0].task, "ora-task-integrity-guard")
        self.assertEqual(ph[0].reason, "cleared-stale")

    def test_stale_clear_without_a_matching_spawn_still_counts(self):
        # Log rotation can drop the Spawning line; the stale-clear alone is proof.
        ph = self.classify([stale("2026-08-05 07:20:22", "ora-orphan")])
        self.assertEqual([p.reason for p in ph], ["cleared-stale"])

    def test_spawn_never_confirmed_never_cleared_is_phantom_once_aged_out(self):
        ph = self.classify([spawn("2026-08-05 08:00:00", "ora-silent")])
        self.assertEqual([p.reason for p in ph], ["never-confirmed"])

    def test_confirm_in_the_SAME_SECOND_as_the_spawn_is_healthy(self):
        # Live regression: ora-cowork-heartbeat 2026-08-01 20:23:14 spawned AND
        # confirmed inside the same log second. A naive (ts, kind) sort orders
        # "confirm" < "spawn" alphabetically, hides the confirm behind the spawn,
        # and reports a healthy run as never-confirmed. Fast confirms are the
        # NORMAL case, so this false positive would have been the common one.
        # NB: timestamps must sit INSIDE the 26h window or classify() skips them
        # and the assertion passes vacuously (this test did exactly that once).
        self.assertEqual(self.classify([
            spawn("2026-08-05 05:50:14", "ora-cowork-heartbeat", prefix="ScheduledTasks"),
            confirm("2026-08-05 05:50:14", "ora-cowork-heartbeat", prefix="ScheduledTasks"),
        ]), [])

    def test_same_second_confirm_survives_reversed_input_order(self):
        self.assertEqual(self.classify([
            confirm("2026-08-05 05:50:14", "ora-x", prefix="ScheduledTasks"),
            spawn("2026-08-05 05:50:14", "ora-x", prefix="ScheduledTasks"),
        ]), [])

    def test_same_second_stale_clear_is_still_a_phantom(self):
        ph = self.classify([
            stale("2026-08-05 07:20:22", "ora-y"),
            spawn("2026-08-05 07:20:22", "ora-y"),
        ])
        self.assertEqual([p.reason for p in ph], ["cleared-stale"])

    def test_recent_unresolved_spawn_is_pending_not_phantom(self):
        # 60s old at NOW -- the session may still be attaching. Must not alarm.
        self.assertEqual(self.classify([spawn("2026-08-05 11:59:00", "ora-inflight")]), [])

    def test_confirm_after_the_window_does_not_rescue_the_spawn(self):
        # A confirm 30min later belongs to a LATER dispatch, not this one.
        ph = self.classify([
            spawn("2026-08-05 08:00:00", "ora-late"),
            confirm("2026-08-05 08:30:00", "ora-late"),
        ])
        self.assertEqual([p.reason for p in ph], ["never-confirmed"])

    def test_two_dispatches_same_task_are_scored_independently(self):
        ph = self.classify([
            spawn("2026-08-05 07:14:41", "ora-twice"),
            stale("2026-08-05 07:20:22", "ora-twice"),
            spawn("2026-08-05 09:14:41", "ora-twice"),
            confirm("2026-08-05 09:14:45", "ora-twice"),
        ])
        self.assertEqual(len(ph), 1)
        self.assertEqual(ph[0].ts.hour, 7)

    def test_interleaved_tasks_do_not_cross_match(self):
        # B's confirm must not rescue A's spawn.
        ph = self.classify([
            spawn("2026-08-05 07:14:41", "ora-a"),
            spawn("2026-08-05 07:14:42", "ora-b"),
            confirm("2026-08-05 07:14:45", "ora-b"),
            stale("2026-08-05 07:20:22", "ora-a"),
        ])
        self.assertEqual([p.task for p in ph], ["ora-a"])

    def test_events_outside_the_window_are_excluded(self):
        ph = self.classify([
            spawn("2026-08-01 07:14:41", "ora-old"),
            stale("2026-08-01 07:20:22", "ora-old"),
        ], hours=26)
        self.assertEqual(ph, [])

    def test_out_of_order_lines_are_handled(self):
        # main1.log (older) is read after main.log unless sorted.
        ph = self.classify([
            stale("2026-08-05 07:20:22", "ora-unsorted"),
            spawn("2026-08-05 07:14:41", "ora-unsorted"),
        ])
        self.assertEqual([p.reason for p in ph], ["cleared-stale"])


class TestVerifiedNull(unittest.TestCase):
    """A zero that could mean 'could not look' must never read as healthy."""

    def test_no_readable_logs_is_an_error_not_a_clean_run(self):
        with self.assertRaises(pdp.ProbeError):
            pdp.load_lines([_HERE / "does-not-exist-main.log"])

    def test_empty_event_set_from_a_readable_log_is_reported_distinctly(self):
        self.assertIsNone(pdp.find_phantoms([], now=NOW, hours=26) or None)


class TestLiveness(unittest.TestCase):
    """A log can be perfectly READABLE and still be dead.

    Live regression, 2026-08-24: the probe returned exit 0 and printed
    "OK -- every dispatch in the window confirmed" over a window that held at
    least 12 real dispatches. The parser was fine; the desktop app had simply
    stopped writing to %APPDATA%\\Claude\\logs at 2026-08-20 20:51, so all five
    logs were 4 days stale and genuinely contained nothing recent. Readability
    and liveness are different properties -- these tests pin both gates.
    """

    def _log(self, lines, age_hours):
        """Write a temp log and backdate its mtime by age_hours."""
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix="-main.log", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        when = (datetime.datetime.now()
                - datetime.timedelta(hours=age_hours)).timestamp()
        os.utime(path, (when, when))
        return path

    def _run(self, path):
        import tempfile
        state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(state_dir.cleanup)
        return pdp.main(["--log", path, "--hours", "26", "--quiet",
                         "--state-dir", state_dir.name])

    def _now_line_pair(self, task="ora-live"):
        ts = (datetime.datetime.now()
              - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        return [spawn(ts, task), confirm(ts, task)]

    def test_frozen_log_is_exit_2_not_exit_0(self):
        # The exact 2026-08-24 shape: real dispatch lines, but all of them
        # predate the window because the file stopped being written.
        path = self._log([
            spawn("2026-08-20 20:50:00", "ora-frozen"),
            confirm("2026-08-20 20:50:01", "ora-frozen"),
        ], age_hours=86.8)
        self.assertEqual(self._run(path), 2)

    def test_fresh_log_with_zero_dispatch_events_is_exit_2_not_exit_0(self):
        # mtime is current, so the frozen-log gate passes -- the zero-dispatch
        # gate is what has to catch this one. 0 of 0 is unverified, not clean.
        path = self._log([
            "2026-08-24 10:00:00 [info] [process-memory] trigger=interval tree_rss_sum=985MB",
        ], age_hours=0)
        self.assertEqual(self._run(path), 2)

    def test_fresh_log_with_a_healthy_dispatch_is_still_exit_0(self):
        # The happy path must survive both new gates, or they are worse than
        # the bug: a probe that always exits 2 is a probe nobody reads.
        path = self._log(self._now_line_pair(), age_hours=0)
        self.assertEqual(self._run(path), 0)

    def test_fresh_log_with_a_phantom_is_still_exit_1(self):
        ts = (datetime.datetime.now() - datetime.timedelta(minutes=30))
        path = self._log([
            spawn(ts.strftime("%Y-%m-%d %H:%M:%S"), "ora-ghost"),
            stale((ts + datetime.timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S"),
                  "ora-ghost"),
        ], age_hours=0)
        self.assertEqual(self._run(path), 1)

    def test_load_lines_reports_the_newest_mtime(self):
        path = self._log(["irrelevant"], age_hours=5)
        _lines, read, _problems, newest = pdp.load_lines([path])
        self.assertEqual(len(read), 1)
        self.assertIsNotNone(newest)
        age_h = (datetime.datetime.now() - newest).total_seconds() / 3600.0
        self.assertAlmostEqual(age_h, 5.0, delta=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

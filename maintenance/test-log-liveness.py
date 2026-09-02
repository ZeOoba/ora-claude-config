#!/usr/bin/env python3
"""Unit tests for _shared/log_liveness.py -- synthetic fixtures ONLY.

Never asserts against the live %APPDATA%\\Claude\\logs tree: it rotates, and on
this machine it has been genuinely frozen since 2026-08-20, which would make a
live-tree assertion pass for the wrong reason. Same discipline as
test-phantom-dispatch-probe.py.

The last class here is the one that matters most: it asserts this module and
phantom-dispatch-probe.py's own inline gate reach the SAME verdict on identical
inputs. Two frozen-log detectors that disagree are worse than one.
"""
import datetime as dt
import importlib.util
import os
import pathlib
import tempfile
import unittest
import unittest.mock as mock

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("log_liveness", _HERE / "_shared" / "log_liveness.py")
ll = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ll)

NOW = dt.datetime(2026, 8, 26, 11, 16, 38)


class Isolated(unittest.TestCase):
    """Pin candidate discovery OFF for fixture-based tests.

    Without this, every test that passes an explicit temp dir trips the real
    STALE-LOCATION check against THIS MACHINE's genuinely-live log tree â€” the
    fixture is, correctly, older than it. Stubbing the candidate list to empty
    isolates the unit under test from the host. (TestStaleLocation overrides
    this with its own two-directory fixture, which is the point of that class.)
    """

    def setUp(self):
        self._orig_candidates = ll.log_dir_candidates
        ll.log_dir_candidates = lambda: []

    def tearDown(self):
        ll.log_dir_candidates = self._orig_candidates


def make_logs(tmp, ages_hours):
    """Create main*.log files whose mtimes are N hours before NOW."""
    d = pathlib.Path(tmp)
    for name, age in ages_hours.items():
        p = d / name
        p.write_text("2026-08-20 20:51:03 [info] [ScheduledTasks] whatever\n", encoding="utf-8")
        stamp = (NOW - dt.timedelta(hours=age)).timestamp()
        os.utime(p, (stamp, stamp))
    return d


class TestMissing(Isolated):
    def test_absent_directory_is_missing_not_ok(self):
        r = ll.assess(pathlib.Path(tempfile.gettempdir()) / "no-such-dir-xyz",
                      window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "MISSING")
        self.assertFalse(r.usable)

    def test_empty_directory_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "MISSING")
        self.assertFalse(r.usable)

    def test_missing_exits_2_not_1(self):
        # "could not look" and "found a problem" are different outcomes.
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ll.main(["--log-dir", tmp, "--no-registry-check"]), 2)


class TestReadabilityVsStatability(Isolated):
    """Qodo #1/#2 (log_liveness.py PR review): stat() succeeding is not proof
    a candidate can actually be read. Both are real bugs in `_read_mtimes()`
    -- it used to add a `main*.log` name to files_read (and let its mtime
    drive OK/FROZEN/BEHIND) on os.stat() alone, never attempting an open().
    Every real caller (dispatch-skip-probe.py, phantom-dispatch-probe.py,
    host-availability-report.py) actually open()s the candidate paths, so a
    file that stats but can't be opened -- or isn't a regular file at all --
    was being counted as usable evidence when nothing downstream could
    actually read it.
    """

    def test_directory_named_like_a_log_is_excluded(self):
        # Qodo #2: a directory named main.log stats fine and carries a real,
        # fresh mtime. Any real consumer's open(main.log) raises
        # IsADirectoryError on it.
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            (d / "main.log").mkdir()
            fresh = (NOW - dt.timedelta(hours=1)).timestamp()
            os.utime(d / "main.log", (fresh, fresh))
            r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "MISSING")
        self.assertFalse(r.usable)
        self.assertNotIn("main.log", r.files_read)
        self.assertTrue(any("not a regular file" in p for p in r.problems))

    def test_unreadable_but_statable_file_is_excluded(self):
        # Qodo #1: os.stat() succeeds on a permission-denied (or ACL-locked)
        # regular file -- only an actual open() attempt reveals it can't be
        # read. Simulated with a mock rather than real chmod/ACLs so the
        # assertion holds on any platform, Windows included, where a chmod
        # bit doesn't reliably block the owner's own read.
        with tempfile.TemporaryDirectory() as tmp:
            d = make_logs(tmp, {"main.log": 1.0})
            target = str(d / "main.log")
            real_open = open

            def fake_open(path, *a, **kw):
                if str(path) == target:
                    raise PermissionError(13, "Permission denied", target)
                return real_open(path, *a, **kw)

            with mock.patch("builtins.open", side_effect=fake_open):
                r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "MISSING")
        self.assertFalse(r.usable)
        self.assertNotIn("main.log", r.files_read)
        self.assertTrue(any("PermissionError" in p for p in r.problems))

    def test_a_readable_regular_file_still_counts(self):
        # Guard against an over-broad fix: a normal, readable file must still
        # pass -- this is the module's entire OK path.
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 1.0})
            r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "OK")
        self.assertIn("main.log", r.files_read)


class TestFrozen(Isolated):
    def test_the_live_2026_08_incident(self):
        # 134.5h stale against a 24h window -- the exact shape of the real one.
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5, "main1.log": 200.0})
            r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "FROZEN")
        self.assertFalse(r.usable)
        self.assertAlmostEqual(r.age_hours, 134.5, places=1)

    def test_readable_and_wellformed_is_still_not_live(self):
        # The whole point: the file opened fine and parsed fine.
        with tempfile.TemporaryDirectory() as tmp:
            d = make_logs(tmp, {"main.log": 50.0})
            self.assertTrue((d / "main.log").read_text(encoding="utf-8"))
            r = ll.assess(tmp, window_hours=26, now=NOW)
        self.assertEqual(r.verdict, "FROZEN")

    def test_newest_of_several_wins(self):
        # A fresh main.log rescues a stale rotation set.
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 1.0, "main1.log": 300.0, "main2.log": 400.0})
            r = ll.assess(tmp, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "OK")

    def test_frozen_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5})
            self.assertEqual(ll.main(["--log-dir", tmp, "--no-registry-check"]), 1)

    def test_banner_names_the_downstream_blast_radius(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5})
            b = ll.assess(tmp, window_hours=24, now=NOW).banner()
        self.assertIn("[ACTION]", b)
        self.assertIn("phantom-dispatch-probe", b)
        self.assertIn("registry evidence", b)


class TestBehind(Isolated):
    """The sharper detector: catches a partial freeze in minutes, not a day."""

    def test_registry_newer_than_log_is_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 3.0})          # log last written 3h ago
            r = ll.assess(tmp, window_hours=24, now=NOW,
                          newest_activity=NOW - dt.timedelta(minutes=2))
        self.assertEqual(r.verdict, "BEHIND")
        self.assertFalse(r.usable)
        self.assertGreater(r.behind_by_min, 150)

    def test_would_have_caught_the_freeze_the_same_evening(self):
        # Freeze at 20:51; a task dispatches at 21:30. The mtime test needs 24h
        # to fire. This fires in 39 minutes.
        froze = dt.datetime(2026, 8, 20, 20, 51, 3)
        now = dt.datetime(2026, 8, 20, 21, 35, 0)
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "main.log"
            p.write_text("x\n", encoding="utf-8")
            os.utime(p, (froze.timestamp(), froze.timestamp()))
            r = ll.assess(tmp, window_hours=24, now=now,
                          newest_activity=dt.datetime(2026, 8, 20, 21, 30, 0))
        self.assertEqual(r.verdict, "BEHIND")

    def test_within_tolerance_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 0.05})
            r = ll.assess(tmp, window_hours=24, now=NOW,
                          newest_activity=NOW - dt.timedelta(minutes=1))
        self.assertEqual(r.verdict, "OK")

    def test_log_ahead_of_registry_is_ok(self):
        # Normal: the log line is written at/just after dispatch.
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 0.01})
            r = ll.assess(tmp, window_hours=24, now=NOW,
                          newest_activity=NOW - dt.timedelta(hours=2))
        self.assertEqual(r.verdict, "OK")

    def test_frozen_outranks_behind(self):
        # Both conditions true -> report the more fundamental one.
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5})
            r = ll.assess(tmp, window_hours=24, now=NOW, newest_activity=NOW)
        self.assertEqual(r.verdict, "FROZEN")

    def test_no_activity_supplied_skips_behind_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 3.0})
            r = ll.assess(tmp, window_hours=24, now=NOW, newest_activity=None)
        self.assertEqual(r.verdict, "OK")
        self.assertIsNone(r.behind_by_min)


class TestReportContract(Isolated):
    def test_as_dict_is_json_safe_and_complete(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5})
            d = ll.assess(tmp, window_hours=24, now=NOW).as_dict()
        json.dumps(d)
        for k in ("verdict", "usable", "newest_write", "age_hours",
                  "window_hours", "detail", "files_read"):
            self.assertIn(k, d)
        self.assertFalse(d["usable"])

    def test_usable_is_true_only_for_ok(self):
        for verdict in ("MISSING", "FROZEN", "BEHIND"):
            r = ll.LivenessReport(verdict, [], [], None, None, 24, None, None, "x")
            self.assertFalse(r.usable, verdict)
        self.assertTrue(ll.LivenessReport("OK", [], [], NOW, 0.1, 24, None, None, "x").usable)


class TestStaleLocation(unittest.TestCase):
    """The 2026-08-20 directory move: an abandoned tree must not read as FROZEN.

    FROZEN says "the app stopped logging" and sends you at the app â€” restart it,
    check ACLs, check disk. All three were chased for six days against a writer
    that was working perfectly, because the real answer was that the logs had
    moved Roaming -> Local. STALE-LOCATION outranks FROZEN so the reader is told
    which directory is live instead of being pointed at a healthy app.
    """

    def _two_dirs(self, tmp, old_age, new_age):
        old = pathlib.Path(tmp) / "roaming"; old.mkdir()
        new = pathlib.Path(tmp) / "local"; new.mkdir()
        make_logs(old, {"main.log": old_age})
        make_logs(new, {"main.log": new_age})
        ll.log_dir_candidates = lambda: [new, old]
        return old, new

    def setUp(self):
        self._orig = ll.log_dir_candidates

    def tearDown(self):
        ll.log_dir_candidates = self._orig

    def test_abandoned_dir_reports_moved_not_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._two_dirs(tmp, old_age=134.5, new_age=0.2)
            r = ll.assess(old, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "STALE-LOCATION")
        self.assertNotEqual(r.verdict, "FROZEN")
        self.assertFalse(r.usable)

    def test_the_banner_forbids_the_wrong_remedies(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._two_dirs(tmp, old_age=134.5, new_age=0.2)
            b = ll.assess(old, window_hours=24, now=NOW).banner()
        self.assertIn("MOVED", b)
        self.assertIn("Do NOT restart", b)
        self.assertIn("ACLs", b)

    def test_discovery_picks_the_live_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._two_dirs(tmp, old_age=134.5, new_age=0.2)
            chosen, survey = ll.discover_log_dir()
        self.assertEqual(str(chosen), str(new))
        self.assertEqual(len(survey), 2)

    def test_default_assess_follows_the_move(self):
        # No explicit dir -> reads the live tree -> OK, not FROZEN.
        with tempfile.TemporaryDirectory() as tmp:
            self._two_dirs(tmp, old_age=134.5, new_age=0.2)
            r = ll.assess(window_hours=24, now=NOW, newest_activity=None)
        self.assertEqual(r.verdict, "OK")

    def test_genuinely_frozen_everywhere_is_still_frozen(self):
        # Both candidates dead -> the move explanation must NOT be offered.
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._two_dirs(tmp, old_age=134.5, new_age=140.0)
            r = ll.assess(old, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "FROZEN")

    def test_five_minute_tolerance_avoids_flapping(self):
        # Near-simultaneous writes must not be called a move.
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._two_dirs(tmp, old_age=0.25, new_age=0.2)
            r = ll.assess(old, window_hours=24, now=NOW)
        self.assertEqual(r.verdict, "OK")


class TestAgreesWithPhantomProbe(Isolated):
    """Two detectors, one machine, one answer. Guards against silent drift.

    Scope note (2026-08-26): agreement is asserted on the FROZEN judgement with
    candidate discovery stubbed off — i.e. when there is no live alternative
    directory. The two are deliberately no longer identical above that: only
    this module has STALE-LOCATION, and phantom-dispatch-probe now defers to
    this module's `discover_log_dir()` for WHERE to read, so the vocabulary
    divergence is intentional and the path can no longer differ.
    """

    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location(
            "pdp_for_agreement", _HERE / "phantom-dispatch-probe.py")
        self.pdp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pdp)

    def _phantom_says_frozen(self, tmp, hours, now):
        _, read, _, newest = self.pdp.load_lines(
            [pathlib.Path(tmp) / n for n in ll.LOG_GLOB_ORDER])
        return newest is not None and newest < now - dt.timedelta(hours=hours)

    def test_both_call_the_live_incident_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 134.5, "main1.log": 200.0})
            mine = ll.assess(tmp, window_hours=26, now=NOW).verdict == "FROZEN"
            theirs = self._phantom_says_frozen(tmp, 26, NOW)
        self.assertTrue(mine)
        self.assertEqual(mine, theirs)

    def test_both_clear_a_fresh_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_logs(tmp, {"main.log": 0.5})
            mine = ll.assess(tmp, window_hours=26, now=NOW).verdict == "FROZEN"
            theirs = self._phantom_says_frozen(tmp, 26, NOW)
        self.assertFalse(mine)
        self.assertEqual(mine, theirs)

    def test_both_agree_at_the_boundary(self):
        for age in (25.5, 26.5):
            with tempfile.TemporaryDirectory() as tmp:
                make_logs(tmp, {"main.log": age})
                mine = ll.assess(tmp, window_hours=26, now=NOW).verdict == "FROZEN"
                theirs = self._phantom_says_frozen(tmp, 26, NOW)
            self.assertEqual(mine, theirs, "disagreement at age=%.1fh" % age)


if __name__ == "__main__":
    unittest.main(verbosity=2)

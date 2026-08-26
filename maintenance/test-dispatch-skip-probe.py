#!/usr/bin/env python3
"""Unit tests for dispatch-skip-probe.py -- synthetic registries and log dirs.

This suite did not exist before 2026-08-26. Its absence is part of why the
`log_scan=ok`-against-a-dead-log defect shipped and survived two incidents:
there was nothing that could have asserted the header told the truth.

Never touches the live registries or %APPDATA%\\Claude\\logs -- both are
mutating state on this machine and would make the suite time-dependent.
"""
import datetime as dt
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "dispatch_skip_probe", _HERE / "dispatch-skip-probe.py")
dsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dsp)


def write_log(d, name, age_hours, body=""):
    p = pathlib.Path(d) / name
    p.write_text(body or "2026-08-20 20:51:03 [info] [ScheduledTasks] noise\n", encoding="utf-8")
    stamp = time.time() - age_hours * 3600
    os.utime(p, (stamp, stamp))
    return p


def registry(tmp, name, task_id, last_run_offset_s, skip_offset_s, n=3):
    """A store with one task that was skipped, then (optionally) recovered."""
    now_ms = time.time() * 1000
    last_run = None
    if last_run_offset_s is not None:
        last_run = dt.datetime.fromtimestamp(
            (now_ms + last_run_offset_s * 1000) / 1000.0,
            dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    doc = {
        "scheduledTasks": [{"id": task_id, "lastRunAt": last_run}],
        "recordedSkips": {task_id: [
            {"at": now_ms + skip_offset_s * 1000, "reason": "global_limit"}
            for _ in range(n)]},
    }
    p = pathlib.Path(tmp) / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


class ProbeHarness(unittest.TestCase):
    """Drives main() against synthetic stores; restores globals afterwards."""

    def setUp(self):
        self._reg, self._logdir = dsp.REG, dsp.LOGDIR
        self.tmp = tempfile.TemporaryDirectory()
        self.logs = pathlib.Path(self.tmp.name) / "logs"
        self.logs.mkdir()
        dsp.LOGDIR = str(self.logs)
        # Isolate from THIS MACHINE's real log tree. dsp passes LOGDIR to
        # assess() explicitly, which enables the STALE-LOCATION check — and
        # against the host's genuinely-live directory every temp fixture is
        # (correctly) stale, so without this stub the whole suite would report
        # STALE-LOCATION instead of exercising FROZEN/BEHIND/OK.
        self._cand = dsp._ll.log_dir_candidates
        dsp._ll.log_dir_candidates = lambda: []

    def tearDown(self):
        dsp.REG, dsp.LOGDIR = self._reg, self._logdir
        dsp._ll.log_dir_candidates = self._cand
        self.tmp.cleanup()

    def run_probe(self, argv=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = dsp.main(argv or ["--window-hours", "24"])
        return code, buf.getvalue()


class TestFrozenLogGate(ProbeHarness):
    """The 2026-08-26 defect: a dead log must never render as log_scan=ok."""

    def test_frozen_log_is_not_reported_ok(self):
        write_log(self.logs, "main.log", 134.5)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        code, out = self.run_probe()
        self.assertIn("log_scan=FROZEN", out)
        self.assertNotIn("log_scan=ok", out)
        self.assertEqual(code, 2, "a dead confirmation leg is 'could not look', not clean")

    def test_frozen_log_still_prints_every_registry_row(self):
        # The registry leg is log-independent and must NOT be suppressed --
        # Step 0.08 item 5: report the gap and continue, never block the audit.
        write_log(self.logs, "main.log", 134.5)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        _, out = self.run_probe()
        self.assertIn("ora-x", out)
        self.assertIn("THROTTLED-THEN-RECOVERED", out)
        self.assertIn("throttled_ids=1", out)

    def test_frozen_log_emits_an_action_banner(self):
        write_log(self.logs, "main.log", 134.5)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        _, out = self.run_probe()
        self.assertIn("[ACTION]", out)
        self.assertIn("[unverifiable]", out)
        self.assertIn("registry evidence", out)

    def test_live_log_exits_normally(self):
        write_log(self.logs, "main.log", 0.1)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        code, out = self.run_probe()
        self.assertIn("log_scan=ok", out)
        self.assertEqual(code, 0)

    def test_live_log_with_open_finding_exits_1(self):
        write_log(self.logs, "main.log", 0.1)
        # skipped 1h ago, never recovered -> DISPATCH-THROTTLED
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", None, -3600)}
        code, out = self.run_probe()
        self.assertIn("DISPATCH-THROTTLED", out)
        self.assertEqual(code, 1)

    def test_missing_log_directory_is_not_ok(self):
        dsp.LOGDIR = str(pathlib.Path(self.tmp.name) / "gone")
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        code, out = self.run_probe()
        self.assertIn("log_scan=MISSING", out)
        self.assertEqual(code, 2)


class TestBehindRegistryGate(ProbeHarness):
    """A log that is merely BEHIND is caught in minutes, not after a full day."""

    def test_registry_newer_than_log_is_behind(self):
        write_log(self.logs, "main.log", 3.0)          # written 3h ago
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -60, -3600)}
        code, out = self.run_probe()
        self.assertIn("log_scan=BEHIND", out)
        self.assertEqual(code, 2)

    def test_fresh_log_abreast_of_registry_is_ok(self):
        write_log(self.logs, "main.log", 0.01)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -60, -3600)}
        code, out = self.run_probe()
        self.assertIn("log_scan=ok", out)
        self.assertEqual(code, 0)


class TestWeakRecoveryAnnotation(ProbeHarness):
    """The `and log_ok` inversion: the caveat must survive a dead log."""

    def test_lastrunat_only_recovery_is_flagged_even_when_log_is_dead(self):
        write_log(self.logs, "main.log", 134.5)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        _, out = self.run_probe()
        self.assertIn("dispatch-confirmed only", out,
                      "the caveat matters MOST when nothing can corroborate lastRunAt")

    def test_lastrunat_only_recovery_is_flagged_when_log_is_live(self):
        write_log(self.logs, "main.log", 0.1)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        _, out = self.run_probe()
        self.assertIn("dispatch-confirmed only", out)

    def test_confirmed_task_run_line_clears_the_caveat(self):
        stamp = dt.datetime.now() - dt.timedelta(minutes=5)
        body = ("%s [info] [CCDScheduledTasks] Confirmed task run for: ora-x\n"
                % stamp.strftime("%Y-%m-%d %H:%M:%S"))
        write_log(self.logs, "main.log", 0.01, body=body)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        _, out = self.run_probe()
        self.assertIn("confirmed_task_run", out)
        self.assertNotIn("dispatch-confirmed only", out)


class TestProvisionalStillHolds(ProbeHarness):
    """The ~60s retry blind spot must survive the new gate untouched."""

    def test_recent_skip_is_provisional_not_open(self):
        write_log(self.logs, "main.log", 0.1)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", None, -10)}
        code, out = self.run_probe()
        self.assertIn("PROVISIONAL", out)
        self.assertIn("open=0", out)
        self.assertEqual(code, 0)

    def test_provisional_note_is_printed(self):
        write_log(self.logs, "main.log", 0.1)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", None, -10)}
        _, out = self.run_probe()
        self.assertIn("Never include them in an alert email", out)


class TestJsonContract(ProbeHarness):
    def test_json_out_carries_the_liveness_verdict(self):
        write_log(self.logs, "main.log", 134.5)
        dsp.REG = {"cc": registry(self.tmp.name, "cc.json", "ora-x", -600, -3600)}
        out_path = str(pathlib.Path(self.tmp.name) / "out.json")
        self.run_probe(["--window-hours", "24", "--json-out", out_path])
        doc = json.loads(pathlib.Path(out_path).read_text(encoding="utf-8"))
        self.assertIn("log_liveness", doc)
        self.assertEqual(doc["log_liveness"]["verdict"], "FROZEN")
        self.assertFalse(doc["log_liveness"]["usable"])
        self.assertTrue(doc["rows"], "rows must still be written when the log is dead")


if __name__ == "__main__":
    unittest.main(verbosity=2)

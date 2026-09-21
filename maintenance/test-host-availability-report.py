#!/usr/bin/env python3
"""Tests for host-availability-report.py -- the AM-cluster first-dispatch
availability table.

Black-box, subprocess-driven against synthetic fixtures (own throwaway
%LOCALAPPDATA%/%APPDATA% trees), matching the house convention (see
maintenance/test-dirty-file-owner-report.py, hooks/tests/test-shared-checkout-guard.py).

Bug covered (Qodo report, "Frozen logs remain trusted"): the script DISCOVERS
the newest log directory via log_liveness.discover_log_dir() but, before this
fix, never called log_liveness.assess() against it -- so a readable directory
whose newest log predates the reporting window could still emit a table with
no indication the data was stale. These tests prove:

  1. a FRESH log directory prints "log liveness : OK" and exits 0.
  2. a FROZEN log directory (newest write older than the 24h window) is
     flagged with an [ACTION] banner AND exits non-zero -- it is no longer
     silently trusted.
  3. the frozen run still prints the historical table (same discipline as
     dispatch-skip-probe.py: stale evidence is reported as unverifiable, not
     suppressed).

Run: python test-host-availability-report.py
Stdlib only. Self-contained (creates its own temp dirs).
"""
import datetime
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "host-availability-report.py")
PY = sys.executable

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("   (%s)" % detail if detail else ""))
        _failures.append(name)


def write_main_log(logdir, mtime_hours_ago, n_lines=3):
    """Write a main.log with N dispatch lines, then back-date its mtime.

    Line CONTENT timestamps are independent of the file's mtime -- exactly
    like a real frozen log: the bytes on disk describe days that are
    genuinely in the past relative to the file's last write. Content dates
    are set a few days behind "today" so the table has rows to print
    regardless of which freshness bucket the mtime lands in.
    """
    os.makedirs(logdir, exist_ok=True)
    p = os.path.join(logdir, "main.log")
    base = datetime.date.today() - datetime.timedelta(days=3)
    lines = []
    for i in range(n_lines):
        d = base + datetime.timedelta(days=i)
        lines.append("%s 06:%02d:03.000 [info] Spawning new session for scheduled task ora-x\n"
                     % (d.isoformat(), 10 + i))
    with open(p, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    stamp = (datetime.datetime.now() - datetime.timedelta(hours=mtime_hours_ago)).timestamp()
    os.utime(p, (stamp, stamp))
    return p


def run_report(local_appdata, roaming_appdata):
    env = dict(os.environ)
    env["LOCALAPPDATA"] = local_appdata
    env["APPDATA"] = roaming_appdata
    # Force log_liveness.newest_registry_dispatch() to find nothing under
    # these fixture roots rather than accidentally reading whatever real
    # scheduled-tasks store exists on the machine running the test.
    proc = subprocess.run([PY, SCRIPT], capture_output=True, text=True, env=env, timeout=30)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    with tempfile.TemporaryDirectory() as tmp:
        local = os.path.join(tmp, "local")
        roaming = os.path.join(tmp, "roaming")
        logdir = os.path.join(local, "Claude", "Logs")
        write_main_log(logdir, mtime_hours_ago=1.0)  # fresh
        rc, out, err = run_report(local, roaming)
        check("fresh log reports OK verdict", "log liveness : OK" in out, out[:400])
        check("fresh log does not print the unverifiable banner", "[ACTION]" not in out, out)
        check("fresh log exits 0", rc == 0, "rc=%r stderr=%s" % (rc, err[:400]))
        check("fresh log still prints the DATE table", "DATE" in out and "FIRST-DISP" in out)

    with tempfile.TemporaryDirectory() as tmp:
        local = os.path.join(tmp, "local")
        roaming = os.path.join(tmp, "roaming")
        logdir = os.path.join(local, "Claude", "Logs")
        write_main_log(logdir, mtime_hours_ago=305.0)  # far past the 24h window
        rc, out, err = run_report(local, roaming)
        check("frozen log reports FROZEN verdict", "log liveness : FROZEN" in out, out[:400])
        check("frozen log prints the unverifiable action banner",
              "TABLE ABOVE IS UNVERIFIABLE" in out and "FROZEN" in out)
        check("frozen log is not reported clean (non-zero exit)", rc != 0, "rc=%r" % rc)
        check("frozen log still prints the historical DATE table (evidence not suppressed)",
              "DATE" in out and "FIRST-DISP" in out)

    with tempfile.TemporaryDirectory() as tmp:
        # No main*.log anywhere under either candidate root -> MISSING.
        local = os.path.join(tmp, "local")
        roaming = os.path.join(tmp, "roaming")
        os.makedirs(os.path.join(local, "Claude", "Logs"), exist_ok=True)
        rc, out, err = run_report(local, roaming)
        check("missing logs report MISSING verdict", "log liveness : MISSING" in out, out[:400])
        check("missing logs exit non-zero", rc != 0, "rc=%r" % rc)

    print()
    if _failures:
        print("FAILED: %d" % len(_failures))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

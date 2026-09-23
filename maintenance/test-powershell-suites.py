#!/usr/bin/env python3
"""Run every PowerShell unit suite in maintenance/ (test-*.ps1) under the pre-push gate.

WHY (follow-up from PR #260, 2026-09-23): hooks/git-prepush-hook-tests-gate.py discovers
and runs only `python <file>` tests, so the PowerShell suites -- including the dead-man's
60-check test-fleet-deadman-ps1.ps1, which pins the pause carve-out, the bounded python
children and the START-log split -- were run by no gate at all. This file matches the
gate's `test-*.py` pattern, so the gate picks it up with no gate change.

Contract:
  * exit 0  -- every test-*.ps1 exited 0.
  * exit 1  -- at least one suite failed (named, with its last output lines), or NO
               suites were found (a silent zero would hide a moved directory).
  * `CANNOT RUN:` + exit 1 -- PowerShell itself is unavailable. That is the gate's
               ENV-SKIP sentinel, so a machine without Windows PowerShell does not block.
Suites run concurrently (each ~2-35s; all six ~35s wall) so the whole file stays well
inside the gate's 240s per-file budget. ORA_POWERSHELL_EXE overrides the interpreter
(used by _tests/test_powershell_suites_runner.py to simulate its absence).
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Overridable for the runner's own tests (ORA_PS_SUITE_TIMEOUT). A timeout is always a FAIL.
PER_SUITE_TIMEOUT = int(os.environ.get("ORA_PS_SUITE_TIMEOUT", "200"))
ENV_SKIP_SENTINEL = "CANNOT RUN:"


def kill_tree(p):
    """Kill the suite AND anything it started. p.kill() alone left a suite's child holding
    the output pipe, so the runner waited on it far past the bound (review of #269)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p.kill()
    except OSError:
        pass


def find_powershell():
    override = os.environ.get("ORA_POWERSHELL_EXE")
    if override:
        return override if os.path.isfile(override) else None
    return shutil.which("powershell") or shutil.which("pwsh")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE, help="directory holding test-*.ps1 (default: this file's)")
    args = ap.parse_args()

    ps = find_powershell()
    if not ps:
        print("CANNOT RUN: no PowerShell interpreter found (powershell/pwsh); PowerShell suites not executed")
        return 1

    suites = sorted(glob.glob(os.path.join(args.dir, "test-*.ps1")))
    if not suites:
        print("FAIL no test-*.ps1 suites found in %s" % args.dir)
        return 1

    procs = []
    for s in suites:
        p = subprocess.Popen([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", s],
                             cwd=args.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        procs.append((s, p))

    failed = 0
    for s, p in procs:
        name = os.path.basename(s)
        try:
            out, _ = p.communicate(timeout=PER_SUITE_TIMEOUT)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            kill_tree(p)
            try:
                out, _ = p.communicate(timeout=10)   # bounded: never wait on a straggler's pipe
            except subprocess.TimeoutExpired:
                out = ""
            rc = "timeout(%ss)" % PER_SUITE_TIMEOUT
        if rc == 0:
            print("PASS %s" % name)
        else:
            failed += 1
            # A failing suite's text must never carry the gate's ENV-SKIP sentinel, or the gate
            # would reclassify this runner's FAILURE as an env-skip (review of #269).
            lines = (out or "").replace(ENV_SKIP_SENTINEL, "CANNOT-RUN:").strip().splitlines()
            # the FAIL lines are what a reader needs; a suite's tail is usually PASS noise
            shown = [l for l in lines if "FAIL" in l][:12] or lines[-12:]
            tail = "\n    ".join(shown)
            print("FAIL %s (exit %s)\n    %s" % (name, rc, tail))

    print("powershell suites: %d/%d passed" % (len(suites) - failed, len(suites)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

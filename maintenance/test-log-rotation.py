#!/usr/bin/env python3
"""Regression tests for Invoke-LogRotation, the 1 MiB size cap on the two
PowerShell maintenance logs that would otherwise grow without bound:

    maintenance/push-fleet-heartbeat.ps1   -> maintenance/push-fleet-heartbeat.log
    maintenance/stuck-session-watchdog.ps1 -> maintenance/stuck-session-watchdog.log

Why this exists (2026-11-23, Automation Audit R34-8): the audit flagged
push-fleet-heartbeat.log as unbounded with "nothing rotates it". That was wrong.
The rotation has been in both writers since PR #162 (2026-09-06, R21-10), and it
fired on 2026-10-22 (maintenance/_log_archive/push-fleet-heartbeat-20261022-162254.log,
1,053,241B). But no test covered it, and it has been silently lost once already:
R25-3 (2026-09-11) found it merged on main but absent from the live checkout.
These tests make a second loss fail the pre-push gate instead of surfacing two
months later as an audit finding.

Pinned behaviour:
  1. Both writers define Invoke-LogRotation with the 1 MiB default and call it on
     $log at top level, after $log is assigned and before the first Log write.
  2. Below the threshold, nothing moves. At or above it, the log is MOVED (byte
     for byte) to <dir>/_log_archive/<base>-<UTC yyyyMMdd-HHmmss>.log.
  3. Retention (Invariant 6): every earlier archive is kept. Rotation never
     deletes, and _log_archive/ is never pruned.
  4. Fail-open: a held handle without FILE_SHARE_DELETE (the Windows lock that
     blocks a rename) leaves the log in place, and the caller keeps running under
     both ErrorActionPreference=Stop and the scripts' default Continue. A missing
     log is a no-op.

Each writer's own copy of the function is extracted from its .ps1 and executed,
so the tests run the shipped code, not a re-implementation.

Run: python test-log-rotation.py   (exit 0 = all pass; Windows PowerShell required)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WRITERS = {
    "push-fleet-heartbeat": os.path.join(HERE, "push-fleet-heartbeat.ps1"),
    "stuck-session-watchdog": os.path.join(HERE, "stuck-session-watchdog.ps1"),
}
ONE_MIB = 1048576
ARCHIVE_NAME = re.compile(r"^(?P<base>.+)-\d{8}-\d{6}\.log$")
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def extract_function(src, name="Invoke-LogRotation"):
    """Return the full `function <name>(...) { ... }` text, brace-matched."""
    m = re.search(r"^function\s+" + re.escape(name) + r"\b", src, re.M)
    if not m:
        return None
    i = src.index("{", m.end())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start(): j + 1]
    return None


# --------------------------------------------------------------------------- #
# 1. Static wiring: defined, 1 MiB default, called on $log before first write
# --------------------------------------------------------------------------- #
def check_wiring(label, path):
    errs = []
    src = _read(path)
    lines = src.splitlines()
    fn = extract_function(src)
    if fn is None:
        return ["%s: Invoke-LogRotation is not defined (rotation lost again, see R25-3)" % label]
    if not re.search(r"\$maxBytes\s*=\s*1048576\b", fn):
        errs.append("%s: Invoke-LogRotation default threshold is not 1048576 (1 MiB)" % label)
    if "Remove-Item" in fn or "Clear-Content" in fn:
        errs.append("%s: Invoke-LogRotation deletes or truncates; it must only move (Invariant 6)" % label)

    def first(pattern):
        for n, line in enumerate(lines):
            if re.match(pattern, line):
                return n
        return None

    assign = first(r"^\$log\s*=")
    call = first(r"^Invoke-LogRotation\s+\$log\s*$")
    # first top-level or indented *call* of Log (not its definition)
    first_write = None
    for n, line in enumerate(lines):
        if re.match(r"^\s*Log\s+[\"'(\$]", line):
            first_write = n
            break
    if assign is None:
        errs.append("%s: no top-level `$log = ...` assignment found" % label)
    if call is None:
        errs.append("%s: no top-level `Invoke-LogRotation $log` call (defined but not wired)" % label)
    if assign is not None and call is not None and call < assign:
        errs.append("%s: Invoke-LogRotation is called before $log is assigned" % label)
    # Defining Log before the rotation call is harmless; *calling* it first is the bug.
    if call is not None and first_write is not None and first_write < call:
        errs.append("%s: first Log write (line %d) precedes rotation (line %d)"
                    % (label, first_write + 1, call + 1))
    return errs


# --------------------------------------------------------------------------- #
# 2-4. Behaviour: run each writer's extracted function against temp fixtures
# --------------------------------------------------------------------------- #
DRIVER = r"""
param([string]$Root, [string]$Pref)
$ErrorActionPreference = $Pref
%FUNC%
$r = [ordered]@{}
Invoke-LogRotation (Join-Path $Root 'below\x.log') 100
Invoke-LogRotation (Join-Path $Root 'at\x.log') 100
Invoke-LogRotation (Join-Path $Root 'over\x.log') 100
Invoke-LogRotation (Join-Path $Root 'default_below\x.log')
Invoke-LogRotation (Join-Path $Root 'default_at\x.log')
Invoke-LogRotation (Join-Path $Root 'missing\x.log') 100
Invoke-LogRotation (Join-Path $Root 'prior\x.log') 100
$held = [IO.File]::Open((Join-Path $Root 'locked\x.log'), 'Open', 'Read', 'ReadWrite')
try { Invoke-LogRotation (Join-Path $Root 'locked\x.log') 100 } finally { $held.Close() }
$r['continued'] = $true
$r | ConvertTo-Json -Compress
"""

# name -> (initial size or None for absent, pre-existing archive file?)
FIXTURES = {
    "below": (99, False),
    "at": (100, False),
    "over": (5000, False),
    "default_below": (ONE_MIB - 1, False),
    "default_at": (ONE_MIB, False),
    "missing": (None, False),
    "prior": (300, True),
    "locked": (300, True),
}
PRIOR_ARCHIVE = "x-20200101-000000.log"
PRIOR_BYTES = b"older generation - must survive\n"


def _payload(size):
    # deterministic, line-shaped content so a byte-for-byte check is meaningful
    unit = b"2026-11-23T00:00:00Z  publish: heartbeat publish OK\n"
    return (unit * (size // len(unit) + 1))[:size]


def build_fixtures(root):
    for name, (size, prior) in FIXTURES.items():
        d = os.path.join(root, name)
        os.makedirs(d)
        if size is not None:
            with open(os.path.join(d, "x.log"), "wb") as f:
                f.write(_payload(size))
        if prior:
            os.makedirs(os.path.join(d, "_log_archive"))
            with open(os.path.join(d, "_log_archive", PRIOR_ARCHIVE), "wb") as f:
                f.write(PRIOR_BYTES)


def _archives(d):
    a = os.path.join(d, "_log_archive")
    return sorted(os.listdir(a)) if os.path.isdir(a) else []


def check_behaviour(label, path, pref):
    errs = []
    fn = extract_function(_read(path))
    if fn is None:
        return ["%s: cannot run behaviour checks, function missing" % label]
    root = tempfile.mkdtemp(prefix="logrot-")
    try:
        build_fixtures(root)
        driver = os.path.join(root, "driver.ps1")
        with open(driver, "w", encoding="utf-8-sig") as f:
            f.write(DRIVER.replace("%FUNC%", fn))
        proc = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", driver,
             "-Root", root, "-Pref", pref],
            capture_output=True, text=True, timeout=180)
        tag = "%s[%s]" % (label, pref)
        out = proc.stdout.strip().splitlines()
        try:
            result = json.loads(out[-1]) if out else {}
        except ValueError:
            result = {}
        if proc.returncode != 0 or not result.get("continued"):
            return ["%s: caller did not keep running (rc=%s) - rotation is not fail-open\nstdout=%s\nstderr=%s"
                    % (tag, proc.returncode, proc.stdout[-800:], proc.stderr[-800:])]

        def d(n):
            return os.path.join(root, n)

        # below threshold: untouched, no archive dir created
        for n, size in (("below", 99), ("default_below", ONE_MIB - 1)):
            if not os.path.isfile(os.path.join(d(n), "x.log")) or \
                    os.path.getsize(os.path.join(d(n), "x.log")) != size:
                errs.append("%s: %s log was moved or altered below the threshold" % (tag, n))
            if os.path.isdir(os.path.join(d(n), "_log_archive")):
                errs.append("%s: %s created _log_archive without rotating" % (tag, n))

        # at/over threshold: moved byte-for-byte, correctly named
        for n, size in (("at", 100), ("over", 5000), ("default_at", ONE_MIB)):
            if os.path.exists(os.path.join(d(n), "x.log")):
                errs.append("%s: %s log was NOT rotated at/above the threshold" % (tag, n))
            arch = _archives(d(n))
            if len(arch) != 1:
                errs.append("%s: %s expected exactly one archive, found %r" % (tag, n, arch))
                continue
            mm = ARCHIVE_NAME.match(arch[0])
            if not mm or mm.group("base") != "x":
                errs.append("%s: %s archive name %r does not match <base>-yyyyMMdd-HHmmss.log"
                            % (tag, n, arch[0]))
            with open(os.path.join(d(n), "_log_archive", arch[0]), "rb") as f:
                if f.read() != _payload(size):
                    errs.append("%s: %s archive content differs from the rotated log" % (tag, n))

        # missing log: no-op
        if os.listdir(d("missing")):
            errs.append("%s: missing-log case created %r" % (tag, os.listdir(d("missing"))))

        # retention: prior generation kept, new one added
        arch = _archives(d("prior"))
        if PRIOR_ARCHIVE not in arch or len(arch) != 2:
            errs.append("%s: prior archive not retained alongside the new one: %r" % (tag, arch))
        else:
            with open(os.path.join(d("prior"), "_log_archive", PRIOR_ARCHIVE), "rb") as f:
                if f.read() != PRIOR_BYTES:
                    errs.append("%s: prior archive content was overwritten" % tag)
        if os.path.exists(os.path.join(d("prior"), "x.log")):
            errs.append("%s: prior case log was not rotated" % tag)

        # held handle (no FILE_SHARE_DELETE): log stays, nothing lost, prior kept
        lp = os.path.join(d("locked"), "x.log")
        if not os.path.isfile(lp) or os.path.getsize(lp) != 300:
            errs.append("%s: locked log was lost or altered when the move failed" % tag)
        if _archives(d("locked")) != [PRIOR_ARCHIVE]:
            errs.append("%s: locked case archive dir changed: %r" % (tag, _archives(d("locked"))))
        return errs
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    if os.name != "nt" or not POWERSHELL:
        print("SKIP: needs Windows PowerShell (the writers are Windows Task Scheduler scripts)")
        return 0
    errs = []
    for label, path in WRITERS.items():
        errs += check_wiring(label, path)
        for pref in ("Stop", "Continue"):
            errs += check_behaviour(label, path, pref)
    if errs:
        print("FAIL (%d):" % len(errs))
        for e in errs:
            print("  - " + e)
        return 1
    print("PASS: Invoke-LogRotation wired and behaving in %d writers (x2 error preferences)"
          % len(WRITERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

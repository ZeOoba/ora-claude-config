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
     blocks a rename) leaves the log in place, and the caller keeps running. The
     Stop run is the one that proves the try/catch: under the scripts' real
     default (Continue, which neither script overrides) a Move-Item failure is
     non-terminating anyway. A missing log is a no-op.
  5. Archive stamps are the real UTC second, and the move never uses -Force: on
     a name collision the existing archive survives and the log stays for the
     next run (Move-Item -Force deletes the destination before moving).

Wiring (1) is judged on the PowerShell parser's AST, not line regexes, so a
block-commented, if/function-wrapped, early-returned or shadowed (defined twice)
rotation fails. The single definition's own text is then executed against temp
fixtures, so the tests run the shipped code, not a re-implementation.

Run: python test-log-rotation.py   (exit 0 = all pass; prints CANNOT RUN and exits
1 without Windows PowerShell, the gate's ENV-SKIP contract)
"""
import datetime
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


# --------------------------------------------------------------------------- #
# 1. Static wiring, judged on the PowerShell parser's AST (not line regexes), so
#    a block-commented, if-wrapped, function-wrapped or shadowed rotation fails.
#    (REFUTE pass 2026-11-23: the first, regex-based version passed all four.)
# --------------------------------------------------------------------------- #
ANALYZER = r"""
param([string]$Path)
$ErrorActionPreference = 'Stop'
$L = [System.Management.Automation.Language.FunctionDefinitionAst]
$tok = $null; $perr = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tok, [ref]$perr)
function InFunction($n) { $p = $n.Parent; while ($p) { if ($p -is $L) { return $true }; $p = $p.Parent }; $false }
function IsLogVar($n) { $n -is [System.Management.Automation.Language.VariableExpressionAst] -and $n.VariablePath.UserPath -match '^(script:)?log$' }
function IsLogAssign($n) {
    if ($n -isnot [System.Management.Automation.Language.AssignmentStatementAst]) { return $false }
    $l = $n.Left; if ($l -is [System.Management.Automation.Language.ConvertExpressionAst]) { $l = $l.Child }
    IsLogVar $l
}
$defs = @($ast.FindAll({ param($n) $n -is $L -and $n.Name -eq 'Invoke-LogRotation' }, $true))
$top = @($ast.EndBlock.Statements)
$callIdx = -1
for ($i = 0; $i -lt $top.Count; $i++) {
    $s = $top[$i]
    if ($s -is [System.Management.Automation.Language.PipelineAst] -and $s.PipelineElements.Count -eq 1) {
        $c = $s.PipelineElements[0]
        if ($c -is [System.Management.Automation.Language.CommandAst] -and $c.GetCommandName() -eq 'Invoke-LogRotation' `
            -and $c.CommandElements.Count -eq 2 -and (IsLogVar $c.CommandElements[1])) { $callIdx = $i; break }
    }
}
# every assignment to $log outside function bodies, as top-level statement indexes (-1 = nested)
$assigns = @($ast.FindAll({ param($n) (IsLogAssign $n) -and -not (InFunction $n) }, $true) | ForEach-Object {
    $a = $_; $idx = -1; for ($i = 0; $i -lt $top.Count; $i++) { if ([object]::ReferenceEquals($top[$i], $a)) { $idx = $i } }; $idx })
$earlyExit = @(); $earlyWrite = @()
if ($callIdx -ge 0) {
    for ($i = 0; $i -lt $callIdx; $i++) {
        $s = $top[$i]
        if ($s -is $L) { continue }
        foreach ($n in $s.FindAll({ param($n) -not (InFunction $n) }, $true)) {
            if ($n -is [System.Management.Automation.Language.ReturnStatementAst] -or
                $n -is [System.Management.Automation.Language.ExitStatementAst] -or
                $n -is [System.Management.Automation.Language.ThrowStatementAst] -or
                $n -is [System.Management.Automation.Language.BreakStatementAst] -or
                $n -is [System.Management.Automation.Language.ContinueStatementAst]) { $earlyExit += $n.Extent.StartLineNumber }
            if ($n -is [System.Management.Automation.Language.CommandAst]) {
                $nm = $n.GetCommandName()
                # an alias outranks the function; Set-Variable can repoint $log unseen by the assignment scan
                if (@('Set-Alias','New-Alias','Set-Variable','New-Variable','Remove-Variable','Remove-Item') -contains $nm -and
                    @($n.CommandElements | Where-Object { $_.Extent.Text -match '(?i)^[''"]?(Invoke-LogRotation|log|alias:\S*Invoke-LogRotation|function:\S*Invoke-LogRotation|variable:\S*log)[''"]?$' }).Count -gt 0) {
                    $earlyExit += $n.Extent.StartLineNumber }
                if ($nm -eq 'Log' -or (@('Out-File','Add-Content','Set-Content','Tee-Object') -contains $nm -and
                    @($n.CommandElements | Where-Object { IsLogVar $_ }).Count -gt 0)) { $earlyWrite += $n.Extent.StartLineNumber }
            }
            if ($n -is [System.Management.Automation.Language.FileRedirectionAst] -and (IsLogVar $n.Location)) { $earlyWrite += $n.Extent.StartLineNumber }
        }
    }
}
[ordered]@{
    parse_errors = @($perr | ForEach-Object { $_.Message })
    def_count    = $defs.Count
    def_toplevel = ($defs.Count -eq 1 -and [object]::ReferenceEquals($defs[0].Parent, $ast.EndBlock))
    def_text     = $(if ($defs.Count -ge 1) { $defs[0].Extent.Text } else { $null })
    call_line    = $(if ($callIdx -ge 0) { $top[$callIdx].Extent.StartLineNumber } else { $null })
    call_idx     = $callIdx
    assign_idxs  = @($assigns)
    early_exit   = @($earlyExit)
    early_write  = @($earlyWrite)
} | ConvertTo-Json -Compress -Depth 3
"""


def analyze(path, workdir):
    script = os.path.join(workdir, "analyze.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write(ANALYZER)
    proc = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Path", path],
        capture_output=True, text=True, timeout=180)
    out = proc.stdout.strip().splitlines()
    if proc.returncode != 0 or not out:
        raise RuntimeError("AST analyzer failed rc=%s: %s" % (proc.returncode, proc.stderr[-600:]))
    return json.loads(out[-1])


def check_wiring(label, path):
    """Returns (errors, function_text_or_None)."""
    workdir = tempfile.mkdtemp(prefix="logrot-ast-")
    try:
        a = analyze(path, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    errs = []
    if a["parse_errors"]:
        errs.append("%s: script does not parse: %s" % (label, a["parse_errors"][:3]))
    if a["def_count"] == 0:
        return errs + ["%s: Invoke-LogRotation is not defined (rotation lost again, see R25-3)" % label], None
    if a["def_count"] > 1:
        errs.append("%s: Invoke-LogRotation is defined %d times; a later definition would shadow the "
                    "tested one" % (label, a["def_count"]))
    if not a["def_toplevel"]:
        errs.append("%s: Invoke-LogRotation is not a single top-level function definition" % label)
    fn = a["def_text"]
    if not re.search(r"\$maxBytes\s*=\s*1048576\b", fn):
        errs.append("%s: Invoke-LogRotation default threshold is not 1048576 (1 MiB)" % label)
    if re.search(r"Remove-Item|Clear-Content|\]::Delete\(", fn):
        errs.append("%s: Invoke-LogRotation deletes or truncates; it must only move (Invariant 6)" % label)
    if re.search(r"(?im)^\s*Move-Item\b[^\r\n#]*-Force\b", fn):
        errs.append("%s: Move-Item -Force deletes an existing archive before moving onto its name "
                    "(Invariant 6)" % label)
    call = a["call_idx"]
    if call < 0:
        errs.append("%s: no top-level `Invoke-LogRotation $log` statement (defined but not wired, or "
                    "wrapped in a block that may never run)" % label)
        return errs, fn
    assigns = a["assign_idxs"]
    if assigns != [i for i in assigns if 0 <= i < call] or len(assigns) != 1:
        errs.append("%s: $log must be assigned exactly once, at top level, before rotation "
                    "(top-level statement indexes %r, rotation at %d; -1 = nested)" % (label, assigns, call))
    if a["early_exit"]:
        errs.append("%s: return/exit/throw/break/continue, or an alias/variable override of "
                    "Invoke-LogRotation or $log, before rotation (line %s) can skip or misdirect it"
                    % (label, a["early_exit"]))
    if a["early_write"]:
        errs.append("%s: log written (line %s) before rotation (line %s)"
                    % (label, a["early_write"], a["call_line"]))
    return errs, fn


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
# collision: an archive already exists under every stamp this rotation could pick
$cArch = Join-Path $Root 'collide\_log_archive'
$t0 = [DateTime]::UtcNow
for ($s = -2; $s -le 20; $s++) {
    $n = 'x-{0}.log' -f $t0.AddSeconds($s).ToString('yyyyMMdd-HHmmss')
    [IO.File]::WriteAllText((Join-Path $cArch $n), "existing archive $n")
}
Invoke-LogRotation (Join-Path $Root 'collide\x.log') 100
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
    "collide": (300, True),
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


def check_behaviour(label, fn, pref):
    errs = []
    started = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
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
            else:
                # The stamp must be the real UTC second of rotation. A coarser stamp
                # (date-only, fixed) makes -Force overwrite an earlier same-stamp
                # archive, which is a deletion (Invariant 6).
                stamp = datetime.datetime.strptime(arch[0][len("x-"):-len(".log")], "%Y%m%d-%H%M%S")
                finished = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                if not (started - datetime.timedelta(seconds=2) <= stamp <= finished):
                    errs.append("%s: %s archive stamp %s is not the UTC time of rotation (%s..%s)"
                                % (tag, n, stamp, started, finished))
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

        # name collision: the existing archive must survive (no -Force overwrite) and
        # the log must stay put for the next run to rotate under a fresh stamp
        cp = os.path.join(d("collide"), "x.log")
        if not os.path.isfile(cp) or os.path.getsize(cp) != 300:
            errs.append("%s: collide log was lost or altered" % tag)
        ca = os.path.join(d("collide"), "_log_archive")
        for name in _archives(d("collide")):
            with open(os.path.join(ca, name), "rb") as f:
                body = f.read()
            want = PRIOR_BYTES if name == PRIOR_ARCHIVE else ("existing archive " + name).encode()
            if body != want:
                errs.append("%s: existing archive %s was overwritten on a name collision "
                            "(Move-Item -Force; Invariant 6)" % (tag, name))
        if len(_archives(d("collide"))) != 24:
            errs.append("%s: collide archive count changed: %d (expected 24)"
                        % (tag, len(_archives(d("collide")))))
        return errs
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    if os.name != "nt" or not POWERSHELL:
        # Repo ENV-SKIP contract (hooks/git-prepush-hook-tests-gate.py): CANNOT RUN + nonzero.
        print("CANNOT RUN: needs Windows PowerShell (the writers are Windows Task Scheduler scripts)")
        return 1
    errs = []
    for label, path in WRITERS.items():
        werrs, fn = check_wiring(label, path)
        errs += werrs
        if fn is None:
            continue
        for pref in ("Stop", "Continue"):
            errs += check_behaviour(label, fn, pref)
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

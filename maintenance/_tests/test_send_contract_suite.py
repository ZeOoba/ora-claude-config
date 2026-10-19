#!/usr/bin/env python3
"""Puts the R-05 send-contract PowerShell suites under the pre-push hook-tests gate, and pins
three static properties of send-via-outlook.ps1 that no PowerShell case can observe.

WHY: hooks/git-prepush-hook-tests-gate.py runs only `python <file>` tests from hooks/tests,
maintenance and maintenance/_tests, and maintenance/test-powershell-suites.py covers only
maintenance/test-*.ps1. Nothing gated scheduled-tasks/_shared/test-*.ps1. The existing
test-send-via-outlook.ps1 sat at 2 FAIL / 21 on 2026-10-18 and no gate noticed.

Static checks:
  S1  every ORA_SEND_ environment read in send-via-outlook.ps1 (case-insensitive; `$env:` or
      GetEnvironmentVariable) sits on a line guarded by `$WhatIf -and` or `if ($WhatIf)` -- a test
      seam must never be able to alter a real send;
  S2  the script's .NOTES exit table documents codes 0..6;
  S3  ground-truth-run-index.py's send-log parser still reads the new OK-line shape and does
      NOT count SEND-INTENT / DEDUP-SKIP / SEND-STATE-UNKNOWN lines as sends.

Slow part: the two suites take ~100 s on a quiet host and over 200 s on a loaded one, so they run only
when the push touches the send path (S4: git diff origin/main...HEAD; ORA_FORCE_SEND_SUITES=1 forces
them). When they run, they run concurrently (output to temp files, so neither blocks on a full pipe)
under one 200 s deadline, inside the gate's 240 s per-file budget. A deadline overrun is a FAIL with no
ENV-SKIP sentinel: the gate's own rule is that a timeout is never an environment skip, so the
gate reruns the file once and a second overrun blocks. No PowerShell -> `CANNOT RUN:` (the
gate's ENV-SKIP sentinel), but only if the static checks passed; a static failure always blocks.

Run: python maintenance/_tests/test_send_contract_suite.py   (exit 0 = pass)
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.dirname(os.path.dirname(HERE))
SHARED = os.path.join(CLAUDE, "scheduled-tasks", "_shared")
SCRIPT = os.path.join(SHARED, "send-via-outlook.ps1")
SUITES = [os.path.join(SHARED, "test-send-contract-legacy.ps1"),
          os.path.join(SHARED, "test-send-contract-keyed.ps1"),
          os.path.join(SHARED, "test-send-via-outlook.ps1")]
GTRI = os.path.join(CLAUDE, "maintenance", "ground-truth-run-index.py")
DEADLINE_SECONDS = 200
ENV_SKIP_SENTINEL = "CANNOT RUN:"

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + detail))


def kill_tree(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        p.kill()
    except OSError:
        pass


# --- S1 -------------------------------------------------------------------------------------
src = open(SCRIPT, encoding="utf-8").read()
lines = src.splitlines()
SEAM_PAT = r"\$\{?env:ORA_SEND_|\bEnv:\\?ORA_SEND_|GetEnvironmentVariable\(\s*['\"]ORA_SEND_"
SEAM_RE = re.compile(SEAM_PAT, re.I)
GUARD_RE = re.compile(r"\$WhatIf\s+-and\b|\bif\s*\(\s*\$WhatIf\s*\)", re.I)
NEG_GUARD_RE = re.compile(r"(-not|!)\s*\$WhatIf", re.I)
ELSE_SEAM_RE = re.compile(r"\belse\b.*(?:" + SEAM_PAT + ")", re.I)


def code_part(line):
    """The line without a trailing # comment (a seam read must not be 'guarded' by a comment)."""
    return line.split(" #", 1)[0]


def s1_flags(line):
    """True when `line` reads an ORA_SEND_ environment variable without a $WhatIf guard.
    The seam is looked for on the RAW line (a ' #' inside a string must not hide it); the guard
    only counts in the code part. Known limit: the check is lexical and per line."""
    if line.lstrip().startswith("#") or not SEAM_RE.search(line):
        return False
    c = code_part(line)
    return (not GUARD_RE.search(c)) or bool(NEG_GUARD_RE.search(c)) or bool(ELSE_SEAM_RE.search(c))


seams = [(i + 1, l) for i, l in enumerate(lines) if not l.lstrip().startswith("#") and SEAM_RE.search(l)]
check("S1 the script reads its test seams", len(seams) >= 5, "found %d" % len(seams))
unguarded = [n for n, l in seams if s1_flags(l)]
check("S1 every ORA_SEND_ env read sits behind a `$WhatIf -and` / `if ($WhatIf)` guard on its own line",
      not unguarded, "lines %s" % unguarded)
check("S1 self-test: unguarded, inverted, else-branch, comment-guarded, Env: drive-path and string-hidden reads are "
      "flagged; a guarded read is not",
      s1_flags("$x = $env:ORA_SEND_LOG_PATH")
      and s1_flags("if (-not $WhatIf -and $env:ORA_SEND_LOG_PATH) { }")
      and s1_flags("$x = $env:ora_send_simulate  # $WhatIf -and")
      and s1_flags("$x = (Get-Item Env:ORA_SEND_X).Value")
      and s1_flags("$x = (Get-Item env:\\ORA_SEND_X).Value")
      and s1_flags("$x = if ($WhatIf) { '' } else { [string]$env:ORA_SEND_SIMULATE }")
      and s1_flags("$h = \"x #y\"; $p = $env:ORA_SEND_LOG_PATH")
      and s1_flags("$x = [Environment]::GetEnvironmentVariable('ORA_SEND_X')")
      and not s1_flags("$x = if ($WhatIf) { [string]$env:ORA_SEND_SIMULATE } else { '' }"))

# --- S2 -------------------------------------------------------------------------------------
m = re.search(r"\.NOTES(.*?)#>", src, re.S)
notes = m.group(1) if m else ""
for code in range(7):
    check("S2 .NOTES documents exit %d" % code, re.search(r"\b%d = " % code, notes) is not None)

# --- S3 -------------------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location("ground_truth_run_index", GTRI)
gtri = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gtri)
rx = gtri._SEND_LOG_LINE_RE
ok_line = ('2026-10-18T07:55:25-04:00 [OK] Sent to=ggoldberg@oxfordra.net cc=none '
           'subject="[ORA] Ground-Truth Audit -- 2026-10-18" bytes=14030 format=html '
           'shash=0123456789abcdef key=ora-ground-truth-auditor/2026-10-18/0123456789abcdef')
mm = rx.match(ok_line)
check("S3 the new [OK] Sent line still parses with its subject",
      mm is not None and mm.group("subject") == "[ORA] Ground-Truth Audit -- 2026-10-18", ok_line)
for label, other in (
    ("SEND-INTENT", '2026-10-18T07:55:20-04:00 [INFO] SEND-INTENT: key=k/2026-10-18/0123456789abcdef '
                    'subject="[ORA] Ground-Truth Audit -- 2026-10-18" shash=0123456789abcdef'),
    ("DEDUP-SKIP", '2026-10-18T07:56:00-04:00 [OK] DEDUP-SKIP: key=k/2026-10-18/0123456789abcdef already '
                   'sent at 2026-10-18T07:55:25-04:00 -- not re-sending subject="[ORA] Ground-Truth Audit -- '
                   '2026-10-18" shash=0123456789abcdef'),
    ("SEND-STATE-UNKNOWN", '2026-10-18T07:56:00-04:00 [ERROR] SEND-STATE-UNKNOWN: x -- the message MAY '
                           'have been sent. shash=0123456789abcdef'),
):
    check("S3 a %s line is not counted as a send" % label, rx.match(other) is None, other)

# --- S4: when are the slow suites run? ---------------------------------------------------------
# MEASURED 2026-10-19: both suites together take ~100 s on a quiet host and MORE than 200 s on a
# host carrying ~30 other python/PowerShell processes, which is what a push looks like (the gate
# runs 8 workers). Running them on every push would false-block unrelated pushes, so they run
# only when the push touches the send path (diff against origin/main); the static checks above
# always run. If the diff cannot be computed the suites run (fail toward testing).
SEND_PATH_RE = re.compile(
    r"^(scheduled-tasks/_shared/(send-via-outlook|test-send-via-outlook|send-contract-harness|test-send-contract-legacy|"
    r"test-send-contract-keyed)\.ps1|maintenance/_tests/test_send_contract_suite\.py)\Z")


def touches_send_path(names):
    return any(SEND_PATH_RE.match(n.strip().replace("\\", "/")) for n in names)


def push_touches_send_path():
    if os.environ.get("ORA_FORCE_SEND_SUITES") == "1":
        return True
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        r = subprocess.run(["git", "-C", CLAUDE, "diff", "--name-only", "--no-renames", "origin/main...HEAD"],
                           capture_output=True, text=True, timeout=30, env=env)
    except (OSError, subprocess.SubprocessError):
        return True
    if r.returncode != 0:
        return True
    return touches_send_path(r.stdout.splitlines())


check("S4 the matcher selects the send path", touches_send_path(["scheduled-tasks/_shared/send-via-outlook.ps1"])
      and touches_send_path(["scheduled-tasks/_shared/test-send-contract-keyed.ps1"])
      and touches_send_path(["maintenance/_tests/test_send_contract_suite.py"]))
check("S4 the matcher ignores unrelated paths", not touches_send_path(
    ["scheduled-tasks/_shared/send-via-outlook.ps1.bak", "hooks/x.py", "scheduled-tasks/_shared/block-sentinel.py"]))

static_ok = all(results)
if static_ok and not push_touches_send_path():
    print("send-contract bridge: %d/%d static checks passed; suites not run (HEAD vs origin/main shows "
          "no send-path change; ORA_FORCE_SEND_SUITES=1 forces them)" % (len(results), len(results)))
    sys.exit(0)

# --- PowerShell suites ------------------------------------------------------------------------
ps = os.environ.get("ORA_POWERSHELL_EXE") or shutil.which("powershell") or shutil.which("pwsh")
if not ps or not os.path.exists(ps):
    if static_ok:
        print("CANNOT RUN: no PowerShell interpreter found; the R-05 send-contract suites were not executed")
    print("send-contract bridge: static %s, suites not run" % ("ok" if static_ok else "FAILED"))
    sys.exit(1)

deadline = time.monotonic() + DEADLINE_SECONDS
procs = []
for s in SUITES:
    # Output goes to a temp FILE, not a pipe: with two pipes drained one after the other, the
    # second suite blocks on a full pipe buffer (about 4 KB) until the first exits, which
    # serialized the run (adversarial review of Task 5, C8).
    f = tempfile.TemporaryFile()
    p = subprocess.Popen([ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", s], cwd=SHARED,
                         stdout=f, stderr=subprocess.STDOUT)
    procs.append((s, p, f))
for s, p, f in procs:
    name = os.path.basename(s)
    try:
        p.wait(timeout=max(1, deadline - time.monotonic()))
        rc = p.returncode
    except subprocess.TimeoutExpired:
        kill_tree(p)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        rc = "timeout(%ss)" % DEADLINE_SECONDS
    f.seek(0)
    out = f.read().decode("utf-8", errors="replace")
    f.close()
    text = out.replace(ENV_SKIP_SENTINEL, "CANNOT-RUN:")
    fails = [l for l in text.splitlines() if "FAIL" in l][:15]
    check("%s exits 0" % name, rc == 0,
          "exit %s\n    %s" % (rc, "\n    ".join(fails or text.splitlines()[-8:])))
passed = sum(1 for r in results if r)
print("send-contract bridge: %d/%d passed" % (passed, len(results)))
sys.exit(0 if all(results) else 1)

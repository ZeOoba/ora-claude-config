"""Tests for maintenance/test-powershell-suites.py -- the bridge that puts the
PowerShell unit suites (maintenance/test-*.ps1) under the pre-push hook-tests gate,
which only runs `python <file>`. Follow-up from PR #260 (2026-09-23): the dead-man's
60-check PowerShell suite, and five others, were run by no gate at all.

Run: python _tests/test_powershell_suites_runner.py   (exit 0 = pass)
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(os.path.dirname(HERE), "test-powershell-suites.py")

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + detail))


def run(suite_dir, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, RUNNER, "--dir", suite_dir],
                       capture_output=True, text=True, timeout=180, env=env)
    return p.returncode, p.stdout + p.stderr


def write(d, name, body):
    with open(os.path.join(d, name), "w", encoding="ascii") as fh:
        fh.write(body)


with tempfile.TemporaryDirectory() as td:
    write(td, "test-alpha.ps1", "Write-Output 'ALL PASS'; exit 0\n")
    write(td, "test-beta.ps1", "Write-Output 'ALL PASS'; exit 0\n")
    rc, out = run(td)
    check("all suites pass -> exit 0", rc == 0, "rc=%s out=%s" % (rc, out))
    check("each suite is named in the output", "test-alpha.ps1" in out and "test-beta.ps1" in out, out)

    write(td, "test-gamma.ps1", "Write-Output '  FAIL something'; exit 1\n")
    rc, out = run(td)
    check("one failing suite -> non-zero exit", rc != 0, "rc=%s out=%s" % (rc, out))
    check("the failing suite is named", "test-gamma.ps1" in out and "FAIL" in out, out)
    check("a failing suite is NOT reported as an env-skip", "CANNOT RUN:" not in out, out)

    write(td, "not-a-test.ps1", "exit 1\n")
    os.remove(os.path.join(td, "test-gamma.ps1"))
    rc, out = run(td)
    check("only test-*.ps1 files are run", rc == 0 and "not-a-test.ps1" not in out, "rc=%s out=%s" % (rc, out))

    rc, out = run(td, {"ORA_POWERSHELL_EXE": os.path.join(td, "no-such-powershell.exe")})
    check("no PowerShell -> gate ENV-SKIP sentinel, non-zero", rc != 0 and "CANNOT RUN:" in out, "rc=%s out=%s" % (rc, out))

with tempfile.TemporaryDirectory() as td:
    rc, out = run(td)
    check("no suites found -> non-zero (a silent zero would hide a moved directory)", rc != 0 and "CANNOT RUN:" not in out,
          "rc=%s out=%s" % (rc, out))

print("powershell-suites runner tests: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)

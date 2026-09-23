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

# Review of #269 (MED): a suite that hangs past the per-suite timeout must FAIL, never pass.
import time as _time
with tempfile.TemporaryDirectory() as td:
    write(td, "test-hang.ps1", "Start-Sleep -Seconds 60; exit 0\n")
    t0 = _time.time()
    rc, out = run(td, {"ORA_PS_SUITE_TIMEOUT": "3"})
    el = _time.time() - t0
    check("a hanging suite times out as FAIL (non-zero, 'timeout(' named, not an env-skip)",
          rc != 0 and "timeout(" in out and "test-hang.ps1" in out and "CANNOT RUN:" not in out, "rc=%s out=%s" % (rc, out))
    check("the timeout is actually honoured (<30s for a 3s bound)", el < 30, "elapsed=%.1fs" % el)

# Review of #269 (LOW): a suite's own child process must not hold the runner past the bound.
pid_dir = tempfile.mkdtemp()   # outside the suite dir, so an orphan cannot pin its cleanup
pid_file = os.path.join(pid_dir, "child.pid")
with tempfile.TemporaryDirectory() as td:
    # The suite starts a long-lived child, records the child's PID, then waits on it.
    write(td, "test-child-hang.ps1",
          "$c = Start-Process -FilePath ping -ArgumentList '-n','60','127.0.0.1' -NoNewWindow -PassThru\n"
          "Set-Content -Path '%s' -Value $c.Id\n"
          "$c.WaitForExit(); exit 0\n" % pid_file)
    t0 = _time.time()
    rc, out = run(td, {"ORA_PS_SUITE_TIMEOUT": "3"})
    el = _time.time() - t0
    _time.sleep(1)
    child_pid = int(open(pid_file).read().strip()) if os.path.exists(pid_file) else 0
    alive = False
    if child_pid:
        q = subprocess.run(["tasklist", "/FI", "PID eq %d" % child_pid, "/NH"], capture_output=True, text=True)
        alive = str(child_pid) in q.stdout
        if alive:   # never leak it, whatever the verdict
            subprocess.run(["taskkill", "/F", "/PID", str(child_pid)], capture_output=True)
    # Re-review of #269: the old '<30s' check passed with the tree kill removed, because the
    # bounded post-kill read alone kept the runner under 30s. Assert the child is actually gone.
    check("a suite's lingering child is killed with the suite (tree kill; child PID gone)",
          rc != 0 and child_pid > 0 and not alive, "rc=%s pid=%s alive=%s elapsed=%.1fs out=%s" % (rc, child_pid, alive, el, out))
    check("a suite's lingering child cannot stretch the bound (<30s for 3s)", el < 30, "elapsed=%.1fs" % el)
import shutil as _sh
_sh.rmtree(pid_dir, ignore_errors=True)

# Review of #269 (LOW): a FAILING suite that happens to print the gate's ENV-SKIP sentinel must
# not turn the runner's failure into an env-skip -- the runner rewrites the sentinel it echoes.
with tempfile.TemporaryDirectory() as td:
    write(td, "test-sentinel.ps1", "Write-Output 'FAIL check 3: CANNOT RUN: fixture missing'; exit 1\n")
    rc, out = run(td)
    check("an echoed 'CANNOT RUN:' from a failing suite is neutralised", rc != 0 and "CANNOT RUN:" not in out
          and "CANNOT-RUN" in out, "rc=%s out=%s" % (rc, out))

print("powershell-suites runner tests: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)

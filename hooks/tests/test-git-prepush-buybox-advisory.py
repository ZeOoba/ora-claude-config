"""Tests for the buy-box ADVISORY leg of git-prepush-doctrine-gate.py (Gabriel 2026-11-03:
WARN now, BLOCK only after the known stale lines are fixed).

The leg runs the PUSHED commit's own maintenance/buybox-drift-probe.py against the gate's
scratch worktree and prints a [WARN] block. It must NEVER change the gate's exit code and
NEVER raise: every probe outcome (0 clean, 1 drift, 2 probe error, crash, absent script,
hang) is advisory. These tests stub the probe with tiny scripts in a temp "worktree".
Run: python test-git-prepush-buybox-advisory.py  (exit 0 = pass)
"""
import importlib.util
import io
import os
import shutil
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "dg", os.path.join(HOOKS, "git-prepush-doctrine-gate.py"))
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def make_worktree(probe_body):
    """Temp dir shaped like a pushed-commit worktree; probe_body=None means no probe."""
    root = tempfile.mkdtemp(prefix="bbx_adv_")
    if probe_body is not None:
        os.makedirs(os.path.join(root, "maintenance"))
        with open(os.path.join(root, "maintenance", "buybox-drift-probe.py"), "w",
                  encoding="utf-8") as fh:
            fh.write(probe_body)
    return root


def run_leg(probe_body, **kw):
    wt = make_worktree(probe_body)
    old_err = sys.stderr
    buf = io.StringIO()
    sys.stderr = buf
    try:
        ret = dg.run_buybox_advisory(wt, **kw)
        raised = None
    except BaseException as e:  # the leg must never raise
        ret, raised = None, e
    finally:
        sys.stderr = old_err
        shutil.rmtree(wt, ignore_errors=True)
    return ret, raised, buf.getvalue()


ARGV_ECHO = "import sys\nprint(' '.join(sys.argv[1:]))\nsys.exit(%d)\n"

# 1) clean probe -> silent, returns 0
ret, raised, err = run_leg("import sys\nsys.exit(0)\n")
expect("clean: no raise", raised is None, repr(raised))
expect("clean: returns 0", ret == 0, repr(ret))
expect("clean: nothing printed", err.strip() == "", repr(err))

# 2) drift -> WARN block with the findings, returns 1, never raises
drift = ("import sys\nprint('BUY-BOX DRIFT DETECTED (1) -- canon ...')\n"
         "print('  C:/x/CLAUDE.md:10  $10M ceiling ...')\nsys.exit(1)\n")
ret, raised, err = run_leg(drift)
expect("drift: no raise", raised is None, repr(raised))
expect("drift: returns 1", ret == 1, repr(ret))
expect("drift: WARN tag", "[WARN]" in err, err)
expect("drift: finding echoed", "CLAUDE.md:10" in err, err)
expect("drift: says advisory / not blocking", "not blocking" in err.lower(), err)

# 3) probe error -> one-line WARN note, returns 2
ret, raised, err = run_leg("import sys\nsys.stderr.write('canon moved')\nsys.exit(2)\n")
expect("probe-error: returns 2", ret == 2, repr(ret))
expect("probe-error: WARN tag", "[WARN]" in err and "probe error" in err.lower(), err)

# 4) crashing probe (traceback, exit 1 from the interpreter) -> still advisory, no raise
ret, raised, err = run_leg("raise RuntimeError('boom')\n")
expect("crash: no raise", raised is None, repr(raised))

# 5) absent probe (older pushed commit) -> silent skip, returns None
ret, raised, err = run_leg(None)
expect("absent: no raise", raised is None, repr(raised))
expect("absent: returns None", ret is None, repr(ret))
expect("absent: silent", err.strip() == "", repr(err))

# 6) the probe is pointed at the WORKTREE (pushed content), not the live ~/.claude
wt = make_worktree(ARGV_ECHO % 0)
old_out = sys.stdout
cap_err = io.StringIO()
old_err = sys.stderr
sys.stderr = cap_err
try:
    seen = dg._buybox_probe_argv(wt)
finally:
    sys.stderr = old_err
    shutil.rmtree(wt, ignore_errors=True)
expect("argv: --claude-root is the worktree", "--claude-root" in seen and
       seen[seen.index("--claude-root") + 1] == wt, repr(seen))
expect("argv: --quiet", "--quiet" in seen, repr(seen))

# 7) hang -> bounded by the timeout, reported, no raise
ret, raised, err = run_leg("import time\ntime.sleep(30)\n", timeout=1)
expect("hang: no raise", raised is None, repr(raised))
expect("hang: WARN timeout note", "[WARN]" in err and "timed out" in err.lower(), err)

# 7b) REFUTE round 1 (C4): a GRANDCHILD that inherits the output handles must not hold the
#     push past the timeout (pipes + communicate() blocked ~15 s here before the fix)
import time as _time
grandchild = ("import subprocess, sys, time\n"
              "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])\n"
              "time.sleep(30)\n")
_t0 = _time.time()
ret, raised, err = run_leg(grandchild, timeout=1)
_elapsed = _time.time() - _t0
expect("grandchild: no raise", raised is None, repr(raised))
expect("grandchild: bounded (< timeout + 6s)", _elapsed < 7, "elapsed %.1fs" % _elapsed)
expect("grandchild: WARN timeout note", "timed out" in err.lower(), err)

# 8) run_doctrine_probe's verdict is untouched by the advisory leg, even if it explodes
calls = {}
orig = (dg.materialize_pushed_commit, dg.remove_worktree, dg.run_buybox_advisory,
        dg.PROBE_SCRIPT_OVERRIDE)
stub_dir = tempfile.mkdtemp(prefix="bbx_dg_")
stub_probe = os.path.join(stub_dir, "doctrine-stub.py")
with open(stub_probe, "w", encoding="utf-8") as fh:
    fh.write("import sys\nsys.exit(0)\n")


def boom(_wt, **_kw):
    calls["advisory"] = True
    raise RuntimeError("advisory exploded")


try:
    dg.materialize_pushed_commit = lambda repo_root=None: (stub_dir, None)
    dg.remove_worktree = lambda p, repo_root=None: calls.setdefault("removed", p)
    dg.run_buybox_advisory = boom
    dg.PROBE_SCRIPT_OVERRIDE = stub_probe
    old_err = sys.stderr
    sys.stderr = io.StringIO()
    try:
        rc, _out = dg.run_doctrine_probe()
    finally:
        sys.stderr = old_err
    expect("gate: advisory was invoked", calls.get("advisory") is True, repr(calls))
    expect("gate: doctrine verdict still 0 despite advisory raising", rc == 0, repr(rc))
    expect("gate: worktree still removed", calls.get("removed") == stub_dir, repr(calls))
finally:
    (dg.materialize_pushed_commit, dg.remove_worktree, dg.run_buybox_advisory,
     dg.PROBE_SCRIPT_OVERRIDE) = orig
    shutil.rmtree(stub_dir, ignore_errors=True)

failed = [label for ok, label in results if not ok]
print("%d/%d buybox-advisory checks passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)

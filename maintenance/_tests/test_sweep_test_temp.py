"""Tests for maintenance/sweep-test-temp.py (age-gated sweep of leaked test fixtures)."""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sweep", os.path.join(os.path.dirname(HERE), "sweep-test-temp.py"))
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def age(path, days):
    ts = time.time() - days * 86400
    os.utime(path, (ts, ts))


base = tempfile.mkdtemp(prefix="sweep-test-base-")
temp = os.path.join(base, "fake", "Temp")
os.makedirs(temp)


def mk_dir(name, days_old, with_readonly=False):
    d = os.path.join(temp, name)
    os.makedirs(os.path.join(d, "sub"))
    f = os.path.join(d, "sub", "f.txt")
    open(f, "w").write("x")
    if with_readonly:
        os.chmod(f, stat.S_IREAD)
    age(d, days_old)
    return d


old_fix = mk_dir("eos-rg-repo-abc123", 30, with_readonly=True)
old_node = mk_dir("debt-api-test-Ab12Cd", 30)
fresh_fix = mk_dir("cwg-root-fresh01", 1)
generic_old = mk_dir("tmpab12cd34", 60)            # generic mkdtemp name: NEVER swept
foreign_old = mk_dir("claude", 60)                 # Claude Code's own temp dir: NEVER swept
scratch_parent = mk_dir("ora-gate-tmp", 60)        # gate's scratch parent: NEVER swept
old_file = os.path.join(temp, "cdp-zz11-claude.json")
open(old_file, "w").write("{}")
age(old_file, 30)

# --- dry run deletes nothing ---------------------------------------------------------
logs = []
st = sw.run(temp, apply=False, min_age_days=7, log=logs.append, allow_other_temp=True)
expect("dry run: reports 3 sweepable old fixtures (2 dirs + 1 file)", st["fixture_old"] == 3, st)
expect("dry run: reports the fresh fixture as kept", st["fixture_fresh"] == 1, st)
expect("dry run: reports generic/foreign names as unclaimed (3)", st["unclaimed"] == 3, st)
expect("dry run: nothing deleted", all(os.path.exists(p) for p in
       (old_fix, old_node, fresh_fix, generic_old, foreign_old, scratch_parent, old_file)))

# --- apply ---------------------------------------------------------------------------
st = sw.run(temp, apply=True, min_age_days=7, log=logs.append, allow_other_temp=True)
expect("apply: old fixture dir (with a read-only file inside) removed", not os.path.exists(old_fix))
expect("apply: other repo's Node fixture removed", not os.path.exists(old_node))
expect("apply: old fixture FILE removed", not os.path.exists(old_file))
expect("apply: fresh fixture kept (age gate)", os.path.isdir(fresh_fix))
expect("apply: generic tmpXXXXXXXX name kept", os.path.isdir(generic_old))
expect("apply: foreign 'claude' dir kept", os.path.isdir(foreign_old))
expect("apply: gate scratch parent kept", os.path.isdir(scratch_parent))
expect("apply: counts", st["removed"] == 3 and st["skipped_locked"] == 0, st)

# --- a junction INSIDE a fixture is unlinked, its target is never descended into -----
if os.name == "nt":
    target = os.path.join(base, "precious")
    os.makedirs(target)
    keep = os.path.join(target, "keep.txt")
    open(keep, "w").write("do not delete")
    jdir = os.path.join(temp, "oag-junction-xyz789")
    os.makedirs(jdir)
    made = subprocess.run(["cmd", "/c", "mklink", "/J", os.path.join(jdir, "link"), target],
                          capture_output=True, text=True).returncode == 0
    age(jdir, 30)
    if made:
        sw.run(temp, apply=True, min_age_days=7, log=logs.append, allow_other_temp=True)
        expect("junction: fixture dir removed", not os.path.exists(jdir))
        expect("junction: the junction's TARGET content survives", os.path.exists(keep))
    else:
        print("  (mklink /J unavailable; junction case skipped)")

# --- top-level junction is unlinked, not followed ------------------------------------
if os.name == "nt":
    target2 = os.path.join(base, "precious2")
    os.makedirs(target2)
    keep2 = os.path.join(target2, "keep.txt")
    open(keep2, "w").write("do not delete")
    top = os.path.join(temp, "scs-topjunction")
    made2 = subprocess.run(["cmd", "/c", "mklink", "/J", top, target2],
                           capture_output=True, text=True).returncode == 0
    if made2:
        # a junction's own mtime cannot be back-dated on Windows; a negative age gate makes
        # every fixture-named entry 'old', which is all this case needs
        sw.run(temp, apply=True, min_age_days=-1, log=logs.append, allow_other_temp=True)
        expect("top-level junction: the link itself is removed", not os.path.lexists(top))
        expect("top-level junction: target content survives", os.path.exists(keep2))

# --- refuses a shallow path ----------------------------------------------------------
try:
    sw.run(os.path.abspath(os.sep), apply=True, log=logs.append, allow_other_temp=True)
    expect("refuses a root/shallow temp path", False, "no SystemExit")
except SystemExit as e:
    expect("refuses a root/shallow temp path", "too shallow" in str(e), str(e))

# --- refuses any dir that is not the real temp dir (the review's hooks/ scenario) ------
prod = os.path.join(base, "hooks")
os.makedirs(prod)
victim = os.path.join(prod, "eos-plan-gate.py")
open(victim, "w").write("# production guard")
age(victim, 60)
try:
    sw.run(prod, apply=True, log=logs.append)
    expect("refuses a non-temp dir without --allow-other-temp", False, "no SystemExit")
except SystemExit as e:
    expect("refuses a non-temp dir without --allow-other-temp", "not this machine" in str(e), str(e))
expect("non-temp dir: production-shaped file untouched", os.path.exists(victim))
if os.name == "nt":
    try:
        sw.run(chr(92) * 2 + "?" + chr(92) + os.path.expanduser("~"), apply=False, log=logs.append)
        expect("refuses a long-path-prefixed home dir", False, "no SystemExit")
    except SystemExit:
        expect("refuses a long-path-prefixed home dir", True)

# --- prefix matcher ------------------------------------------------------------------
expect("matcher: fixture prefix", sw.is_fixture_name("cpg-repo-9zx8y7"))
expect("matcher: generic mkdtemp name is NOT a fixture", not sw.is_fixture_name("tmpab12cd34"))
expect("matcher: unrelated app dir is NOT a fixture", not sw.is_fixture_name("Microsoft"))

shutil.rmtree(base, ignore_errors=True)
passed = sum(1 for ok, _ in results if ok)
print("sweep-test-temp tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)

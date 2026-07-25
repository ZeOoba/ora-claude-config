"""Standalone test for hooks/fleet-session-hook.py. Drives the script via stdin exactly
as the harness does, plus imports it directly to reproduce the state-file
read-modify-write race deterministically.
"""
import concurrent.futures
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "fleet-session-hook.py")
PY = sys.executable

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def load_module(state_path, out_path, sessions_dir):
    """Import fleet-session-hook.py fresh, pointed at a throwaway environment via its
    own env-var overrides -- NOT the live vault -- so this test never touches real
    session-state.json or the real Obsidian vault."""
    env_backup = {
        k: os.environ.get(k) for k in
        ("ORA_FLEET_STATE", "ORA_OBSIDIAN_OUT", "ORA_OBSIDIAN_SESSIONS")
    }
    os.environ["ORA_FLEET_STATE"] = state_path
    os.environ["ORA_OBSIDIAN_OUT"] = out_path
    os.environ["ORA_OBSIDIAN_SESSIONS"] = sessions_dir
    try:
        spec = importlib.util.spec_from_file_location("fleet_session_hook_under_test", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_hook(payload, state_path, out_path, sessions_dir):
    env = dict(os.environ, ORA_FLEET_STATE=state_path, ORA_OBSIDIAN_OUT=out_path,
               ORA_OBSIDIAN_SESSIONS=sessions_dir)
    p = subprocess.run([PY, SCRIPT], input=json.dumps(payload).encode("utf-8"),
                        capture_output=True, env=env, timeout=30)
    return p.returncode


def fresh_env(prefix):
    root = tempfile.mkdtemp(prefix=prefix)
    state_path = os.path.join(root, "session-state.json")
    out_path = os.path.join(root, "Claude Session Tasks.md")
    sessions_dir = os.path.join(root, "Sessions")
    return root, state_path, out_path, sessions_dir


# ===================================================================================
# THE RACE (2026-07-24). Every hook invocation does a full read-modify-write of the
# SHARED session-state.json: load_state() reads the WHOLE file, mutates only its own
# session_id's entry, then save_state() writes the WHOLE file back (atomic rename
# protects against torn/partial writes, but NOT against two concurrent readers each
# working from a stale snapshot). Two sessions racing: A loads (sees {}), B loads
# (sees {} -- same snapshot, before A's write), A adds session "aaa" and saves, B adds
# session "bbb" and saves -- B's save is a full-file overwrite of a stale snapshot that
# never had "aaa" in it, so A's session is silently dropped. This can happen for real:
# concurrent Claude Code sessions in different worktrees of the same repo all fire this
# same hook, all racing to update the SAME shared state file.
#
# CHARACTERIZATION, not a bug: load_state()/save_state() are deliberately plain I/O --
# state_lock() protects the CALL SITE (main()'s read-modify-write block), not these
# functions themselves, so calling them directly (as this test does, bypassing the
# lock on purpose) still reproduces the raw race. That is intentional and expected --
# it is what proves the lock is doing real work, verified properly below by the
# end-to-end test, which drives real concurrent subprocesses through main() itself.
# ===================================================================================
print("== THE RACE: raw load_state()/save_state(), used directly, still race (expected) ==")
root, state_path, out_path, sessions_dir = fresh_env("race-sim-")
mod = load_module(state_path, out_path, sessions_dir)

# Session A's process: loads state (empty)
state_a = mod.load_state()
state_a["sessions"]["aaa11111"] = {"started": mod.iso(mod.now()), "tasks": [], "activity": [],
                                     "lastAt": mod.iso(mod.now())}

# Session B's process: loads state BEFORE A has saved -- same stale snapshot
state_b = mod.load_state()
state_b["sessions"]["bbb22222"] = {"started": mod.iso(mod.now()), "tasks": [], "activity": [],
                                     "lastAt": mod.iso(mod.now())}

# A saves first. B saves second, from its OWN (stale, pre-A) snapshot -- neither call
# goes through state_lock(), matching the "raw primitives" characterization above.
mod.save_state(state_a)
mod.save_state(state_b)

final = mod.load_state()
check("raw save_state() calls still lose session A's update (expected -- no lock used)",
      "aaa11111" in final["sessions"], False)
check("session B (the later, unlocked save) is present",
      "bbb22222" in final["sessions"], True)

shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# END-TO-END: real concurrent subprocess invocations against the SAME state file,
# each a DIFFERENT session_id's SessionStart event -- the actual failure mode in
# production (many concurrent Claude Code sessions all firing this hook).
# ===================================================================================
print()
print("== END-TO-END: N real concurrent hook subprocess invocations, distinct session_ids ==")
root, state_path, out_path, sessions_dir = fresh_env("race-e2e-")

N = 12
payloads = [
    {"hook_event_name": "SessionStart", "session_id": "sess-%02d" % i,
     "cwd": "C:/fake/repo%d" % i}
    for i in range(N)
]

with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
    futs = [ex.submit(run_hook, p, state_path, out_path, sessions_dir) for p in payloads]
    exit_codes = [f.result() for f in futs]

check("all N concurrent hook invocations exited 0",
      all(c == 0 for c in exit_codes), True)

with open(state_path, "r", encoding="utf-8") as f:
    final_state = json.load(f)

present = set(final_state.get("sessions", {}).keys())
expected = set("sess-%02d" % i for i in range(N))
missing = expected - present
check("all %d concurrently-created sessions present in final state (none lost)" % N,
      missing, set())
if missing:
    print("       missing:", sorted(missing))

shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# FORMAL REVIEW FOLLOW-UP (2026-07-24). The reviewer probed both the stale-lock-clear
# and fail-open paths live before approving, and called the untested failure mode --
# "if stale-clearing ever regresses, every invocation after any crashed holder stalls
# LOCK_TIMEOUT_S forever" -- the single worst thing this design can do. Both are
# deterministic (no real concurrency needed): plant a lock file with a controlled
# mtime, drive ONE hook invocation, and assert on timing + outcome.
# ===================================================================================
print()
print("== STALE-LOCK CLEARING: an abandoned lock (crashed holder) must not jam forever ==")
root, state_path, out_path, sessions_dir = fresh_env("stale-lock-")
lock_path = state_path + ".lock"
with open(lock_path, "w") as f:
    f.write("")
old = time.time() - 3600  # 1 hour old -- far past LOCK_STALE_S (10s)
os.utime(lock_path, (old, old))

t0 = time.time()
exit_code = run_hook({"hook_event_name": "SessionStart", "session_id": "stale-test",
                       "cwd": "C:/fake/repo"}, state_path, out_path, sessions_dir)
elapsed = time.time() - t0

check("exits 0", exit_code, 0)
check("completes fast (< 2s -- does NOT wait out the full timeout for a stale lock)",
      elapsed < 2.0, True)
with open(state_path, "r", encoding="utf-8") as f:
    state = json.load(f)
check("session recorded despite the pre-existing stale lock",
      "stale-test" in state.get("sessions", {}), True)
check("stale lock file was cleared, not left behind",
      os.path.exists(lock_path), False)
shutil.rmtree(root, ignore_errors=True)

print()
print("== FAIL-OPEN: a FRESH foreign lock (genuine live contention) must bound, not hang ==")
root, state_path, out_path, sessions_dir = fresh_env("fresh-lock-")
lock_path = state_path + ".lock"
with open(lock_path, "w") as f:
    f.write("")
# fresh mtime (now) -- looks like a live holder, must NOT be cleared as stale

t0 = time.time()
exit_code = run_hook({"hook_event_name": "SessionStart", "session_id": "failopen-test",
                       "cwd": "C:/fake/repo"}, state_path, out_path, sessions_dir)
elapsed = time.time() - t0

check("exits 0 even when it can never acquire the lock", exit_code, 0)
check("bounded by LOCK_TIMEOUT_S, not indefinite (elapsed within [1s, 15s])",
      1.0 <= elapsed <= 15.0, True)
with open(state_path, "r", encoding="utf-8") as f:
    state = json.load(f)
check("session STILL saved after proceeding lockless (fail-open, not fail-lost)",
      "failopen-test" in state.get("sessions", {}), True)
shutil.rmtree(root, ignore_errors=True)

print()
print("RESULT: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)

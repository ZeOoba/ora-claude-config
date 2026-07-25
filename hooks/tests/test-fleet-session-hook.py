"""Standalone test for hooks/fleet-session-hook.py. Drives the script via stdin exactly
as the harness does, plus imports it directly to check the per-session-file storage
model's internals (each session's own file, aggregation-at-render-time, pruning).
"""
import concurrent.futures
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "fleet-session-hook.py")
PY = sys.executable

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def load_module(sessions_state_dir, out_path, sessions_dir):
    """Import fleet-session-hook.py fresh, pointed at a throwaway environment via its
    own env-var overrides -- NOT the live vault -- so this test never touches real
    session state or the real Obsidian vault."""
    env_backup = {
        k: os.environ.get(k) for k in
        ("ORA_FLEET_SESSIONS_DIR", "ORA_OBSIDIAN_OUT", "ORA_OBSIDIAN_SESSIONS")
    }
    os.environ["ORA_FLEET_SESSIONS_DIR"] = sessions_state_dir
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


def run_hook(payload, sessions_state_dir, out_path, sessions_dir):
    env = dict(os.environ, ORA_FLEET_SESSIONS_DIR=sessions_state_dir,
               ORA_OBSIDIAN_OUT=out_path, ORA_OBSIDIAN_SESSIONS=sessions_dir)
    p = subprocess.run([PY, SCRIPT], input=json.dumps(payload).encode("utf-8"),
                        capture_output=True, env=env, timeout=30)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def fresh_env(prefix):
    root = tempfile.mkdtemp(prefix=prefix)
    sessions_state_dir = os.path.join(root, "session-state.d")
    out_path = os.path.join(root, "Claude Session Tasks.md")
    sessions_dir = os.path.join(root, "Sessions")
    return root, sessions_state_dir, out_path, sessions_dir


# ===================================================================================
# BASIC: a single SessionStart creates that session's OWN file and renders correctly.
# No shared file exists at all in this design -- there is nothing to race over.
# ===================================================================================
print("== BASIC: one SessionStart creates its own file, dashboard renders ==")
root, sdir, out_path, notes_dir = fresh_env("basic-")
code, out, err = run_hook(
    {"hook_event_name": "SessionStart", "session_id": "basic-001", "cwd": "C:/fake/repoA"},
    sdir, out_path, notes_dir)
check("exits 0", code, 0)
check("own session file created", os.path.isfile(os.path.join(sdir, "basic-001.json")), True)
with open(os.path.join(sdir, "basic-001.json"), "r", encoding="utf-8") as f:
    saved = json.load(f)
check("session file has the true session_id embedded", saved.get("_sid"), "basic-001")
check("status recorded as working", saved.get("status"), "working")
with open(out_path, "r", encoding="utf-8") as f:
    dashboard = f.read()
check("dashboard mentions the session's short id", "basic-00" in dashboard, True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# CROSS-SESSION INDEPENDENCE: two different sessions never touch each other's files.
# This is now trivially true by construction (each session has its own path), but
# worth a direct assertion -- and it demonstrates there is no shared file to race on.
# ===================================================================================
print()
print("== CROSS-SESSION INDEPENDENCE: distinct sessions never share a file ==")
root, sdir, out_path, notes_dir = fresh_env("cross-")
run_hook({"hook_event_name": "SessionStart", "session_id": "cross-A", "cwd": "C:/a"},
         sdir, out_path, notes_dir)
run_hook({"hook_event_name": "SessionStart", "session_id": "cross-B", "cwd": "C:/b"},
         sdir, out_path, notes_dir)
check("two separate files on disk",
      sorted(os.listdir(sdir)), ["cross-A.json", "cross-B.json"])
with open(os.path.join(sdir, "cross-A.json"), "r", encoding="utf-8") as f:
    a = json.load(f)
check("A's file only knows about A's own cwd", a.get("cwd"), "C:/a")
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# END-TO-END CONCURRENCY: N real concurrent subprocess invocations, distinct
# session_ids -- the shape that used to lose 10/12 sessions under the old shared-file
# design. With per-session files there is no shared write path left to race over.
# ===================================================================================
print()
print("== END-TO-END: N real concurrent hook subprocess invocations, distinct session_ids ==")
root, sdir, out_path, notes_dir = fresh_env("e2e-")

N = 20
payloads = [
    {"hook_event_name": "SessionStart", "session_id": "sess-%02d" % i,
     "cwd": "C:/fake/repo%d" % i}
    for i in range(N)
]

with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
    futs = [ex.submit(run_hook, p, sdir, out_path, notes_dir) for p in payloads]
    hook_results = [f.result() for f in futs]

check("all N concurrent hook invocations exited 0",
      all(c == 0 for c, _, _ in hook_results), True)

present = set(f[:-5] for f in os.listdir(sdir) if f.endswith(".json"))
expected = set("sess-%02d" % i for i in range(N))
missing = expected - present
check("all %d concurrently-created sessions have their own file (none lost)" % N,
      missing, set())
if missing:
    print("       missing:", sorted(missing))
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# SAME-SESSION CONCURRENCY: N real concurrent hook subprocess invocations sharing ONE
# session_id -- realistic here (e.g. parallel subagent tool completions reporting
# under their parent's session_id). This file is now the only thing left to race on.
# save_session()'s temp filename is PID-suffixed specifically so concurrent writers to
# the SAME session never collide on the SAME temp path (a Windows sharing-violation /
# corruption risk, not just a lost-update risk). What this does NOT (and, per the
# module docstring's documented accepted residual, deliberately does not) guarantee is
# that every concurrent writer's update survives -- last-writer-wins on a load-mutate-
# replace cycle can still silently drop a sibling's update. So this test asserts the
# STRONG guarantee (never corrupts, never crashes) and explicitly does NOT assert the
# weaker property (all N updates present) that a per-session lock would be needed for.
# ===================================================================================
print()
print("== SAME-SESSION CONCURRENCY: N concurrent writers to ONE session never corrupt it ==")
root, sdir, out_path, notes_dir = fresh_env("samesess-")
sid = "shared-sess"
run_hook({"hook_event_name": "SessionStart", "session_id": sid, "cwd": "C:/x"},
         sdir, out_path, notes_dir)

N = 12
payloads = [
    {"hook_event_name": "PostToolUse", "session_id": sid, "cwd": "C:/x",
     "tool_name": "TaskCreate",
     "tool_input": {"id": "task-%02d" % i, "title": "task %d" % i, "status": "pending"},
     "tool_response": {}}
    for i in range(N)
]
with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
    futs = [ex.submit(run_hook, p, sdir, out_path, notes_dir) for p in payloads]
    same_sess_results = [f.result() for f in futs]

check("all N concurrent same-session hook invocations exited 0",
      all(c == 0 for c, _, _ in same_sess_results), True)

no_tmp_leftover = [f for f in os.listdir(sdir) if ".tmp." in f]
check("no leftover .tmp files after concurrent same-session writes",
      no_tmp_leftover, [])

with open(os.path.join(sdir, sid + ".json"), "r", encoding="utf-8") as f:
    same_sess_final = json.load(f)  # must not raise -- proves the file is valid, unmangled JSON
check("session file is still valid JSON with the right shape after concurrent writes",
      isinstance(same_sess_final.get("tasks"), list), True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# RENDER AGGREGATION: the dashboard's "Active sessions" table and the global feed are
# both computed fresh at render time from whatever session files currently exist.
# ===================================================================================
print()
print("== RENDER AGGREGATION: active-sessions table and feed merge across sessions ==")
root, sdir, out_path, notes_dir = fresh_env("aggr-")
mod = load_module(sdir, out_path, notes_dir)

s1 = {"started": mod.iso(mod.now()), "tasks": [], "activity": [], "feed_events": [],
      "status": "working", "cwd": "C:/repo1", "lastAt": mod.iso(mod.now()), "lastTool": "Bash"}
mod.add_feed_local(s1, "session", "session started")
mod.save_session("aggr-1", s1)

s2 = {"started": mod.iso(mod.now()), "tasks": [], "activity": [], "feed_events": [],
      "status": "idle", "cwd": "C:/repo2", "lastAt": mod.iso(mod.now()), "lastTool": "Edit"}
mod.add_feed_local(s2, "task-create", "Do the thing")
mod.save_session("aggr-2", s2)

mod.render()
with open(out_path, "r", encoding="utf-8") as f:
    dashboard = f.read()
check("dashboard lists both sessions in the active table",
      "aggr-1" in dashboard and "aggr-2" in dashboard, True)
check("dashboard's recent-activity feed includes session 1's contribution",
      "session started" in dashboard, True)
check("dashboard's recent-activity feed includes session 2's contribution",
      "Do the thing" in dashboard, True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# FEED ORDERING AND CAP: feed_entries from multiple sessions must be merged by
# timestamp (not grouped by session) and capped at FEED_CAP globally, matching the
# original shared-list semantics even though there is no shared list anymore.
# ===================================================================================
print()
print("== FEED ORDERING: cross-session entries sorted by time, capped globally ==")
root, sdir, out_path, notes_dir = fresh_env("feedorder-")
mod = load_module(sdir, out_path, notes_dir)

import datetime as _dt


def _mk(base_minutes_ago):
    return (mod.now() - _dt.timedelta(minutes=base_minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S")


sA = {"started": mod.iso(mod.now()), "tasks": [], "activity": [], "status": "working",
      "cwd": "C:/a", "lastAt": mod.iso(mod.now()),
      "feed_events": [{"at": _mk(5), "kind": "session", "detail": "A-newer"},
                       {"at": _mk(15), "kind": "session", "detail": "A-older"}]}
mod.save_session("feed-A", sA)

sB = {"started": mod.iso(mod.now()), "tasks": [], "activity": [], "status": "working",
      "cwd": "C:/b", "lastAt": mod.iso(mod.now()),
      "feed_events": [{"at": _mk(1), "kind": "session", "detail": "B-newest"},
                       {"at": _mk(10), "kind": "session", "detail": "B-middle"}]}
mod.save_session("feed-B", sB)

mod.render()
with open(out_path, "r", encoding="utf-8") as f:
    dashboard = f.read()
order = [label for label in ["B-newest", "A-newer", "B-middle", "A-older"]
         if label in dashboard]
check("feed entries interleaved across sessions in time order (not grouped by session)",
      dashboard.index("B-newest") < dashboard.index("A-newer") <
      dashboard.index("B-middle") < dashboard.index("A-older"), True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# SESSION-END: the file is NOT deleted (formal review, 2026-07-24 -- an earlier
# version of this fix deleted it immediately, destroying that session's
# recent-activity feed contribution the instant SessionEnd fired, instead of after
# the same SESSION_PRUNE_H window every other session gets). It's marked
# status="ended" and persists until the normal prune cycle -- but must NEVER show as
# "active" in the dashboard, and session_liveness.py must NEVER report it as open.
# ===================================================================================
print()
print("== SESSION END: file persists (marked ended), writes a final note, never looks active ==")
root, sdir, out_path, notes_dir = fresh_env("sessend-")
run_hook({"hook_event_name": "SessionStart", "session_id": "end-test", "cwd": "C:/x"},
         sdir, out_path, notes_dir)
check("file exists after SessionStart",
      os.path.isfile(os.path.join(sdir, "end-test.json")), True)

code, out, err = run_hook({"hook_event_name": "SessionEnd", "session_id": "end-test",
                            "cwd": "C:/x"}, sdir, out_path, notes_dir)
check("SessionEnd exits 0", code, 0)
check("session file PERSISTS after SessionEnd (not deleted)",
      os.path.isfile(os.path.join(sdir, "end-test.json")), True)
with open(os.path.join(sdir, "end-test.json"), "r", encoding="utf-8") as f:
    ended_state = json.load(f)
check("status recorded as ended", ended_state.get("status"), "ended")
note_files = [f for f in os.listdir(notes_dir)] if os.path.isdir(notes_dir) else []
check("a final per-session note was written", len(note_files) >= 1, True)
with open(out_path, "r", encoding="utf-8") as f:
    dashboard_after_end = f.read()
active_section = dashboard_after_end.split("## Recent activity")[0]
check("ended session does NOT appear in the dashboard's active table",
      "end-test" not in active_section, True)
check("ended session's contribution DOES still appear in the recent-activity feed",
      "end-test" in dashboard_after_end, True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# PRUNING: a session file older than SESSION_PRUNE_H is deleted as a side effect of
# render()'s own directory scan, and does not appear in the active-sessions table.
# ===================================================================================
print()
print("== PRUNING: a stale session file is cleaned up and excluded from the dashboard ==")
root, sdir, out_path, notes_dir = fresh_env("prune-")
mod = load_module(sdir, out_path, notes_dir)

stale_at = (mod.now() - _dt.timedelta(hours=mod.SESSION_PRUNE_H + 1)).strftime("%Y-%m-%dT%H:%M:%S")
stale_s = {"started": stale_at, "tasks": [], "activity": [], "feed_events": [],
           "status": "idle", "cwd": "C:/stale", "lastAt": stale_at}
mod.save_session("prune-stale", stale_s)

fresh_s = {"started": mod.iso(mod.now()), "tasks": [], "activity": [], "feed_events": [],
           "status": "working", "cwd": "C:/fresh", "lastAt": mod.iso(mod.now())}
mod.save_session("prune-fresh", fresh_s)

mod.render()
check("stale session file was deleted by render()'s pruning",
      os.path.isfile(os.path.join(sdir, "prune-stale.json")), False)
check("fresh session file was NOT pruned",
      os.path.isfile(os.path.join(sdir, "prune-fresh.json")), True)
with open(out_path, "r", encoding="utf-8") as f:
    dashboard = f.read()
check("dashboard does not mention the pruned session",
      "prune-st" not in dashboard, True)
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# FULL LIFECYCLE: SessionStart -> PostToolUse (task tracking) -> Stop -> SessionEnd,
# run as real sequential subprocess invocations, verifying end-to-end functional
# correctness (not just the concurrency angle) survived the redesign.
# ===================================================================================
print()
print("== FULL LIFECYCLE: sequential real invocations through the whole event set ==")
root, sdir, out_path, notes_dir = fresh_env("lifecycle-")
sid = "life-001"

run_hook({"hook_event_name": "SessionStart", "session_id": sid, "cwd": "C:/proj"},
         sdir, out_path, notes_dir)
run_hook({"hook_event_name": "PostToolUse", "session_id": sid, "cwd": "C:/proj",
          "tool_name": "TaskCreate",
          "tool_input": {"id": "t1", "title": "Write tests", "status": "pending"},
          "tool_response": {}}, sdir, out_path, notes_dir)
run_hook({"hook_event_name": "PostToolUse", "session_id": sid, "cwd": "C:/proj",
          "tool_name": "TaskUpdate",
          "tool_input": {"id": "t1", "status": "completed"},
          "tool_response": {}}, sdir, out_path, notes_dir)

with open(os.path.join(sdir, sid + ".json"), "r", encoding="utf-8") as f:
    mid_state = json.load(f)
check("task was created and then marked completed",
      mid_state.get("tasks", [{}])[0].get("status"), "completed")

run_hook({"hook_event_name": "Stop", "session_id": sid, "cwd": "C:/proj"},
         sdir, out_path, notes_dir)
with open(os.path.join(sdir, sid + ".json"), "r", encoding="utf-8") as f:
    idle_state = json.load(f)
check("status is idle after Stop", idle_state.get("status"), "idle")

code, out, err = run_hook({"hook_event_name": "SessionEnd", "session_id": sid,
                            "cwd": "C:/proj"}, sdir, out_path, notes_dir)
check("SessionEnd exits 0", code, 0)
with open(os.path.join(sdir, sid + ".json"), "r", encoding="utf-8") as f:
    ended_lifecycle_state = json.load(f)
check("status is ended after SessionEnd (file persists)",
      ended_lifecycle_state.get("status"), "ended")
check("this session's task history survived through to the end",
      ended_lifecycle_state.get("tasks", [{}])[0].get("status"), "completed")
shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# ROBUSTNESS: a malformed session file, or no sessions directory at all, must never
# crash the hook -- same fail-open posture as everywhere else in this file.
# ===================================================================================
print()
print("== ROBUSTNESS: malformed file / missing directory never crash the hook ==")
root, sdir, out_path, notes_dir = fresh_env("robust-")
os.makedirs(sdir, exist_ok=True)
with open(os.path.join(sdir, "corrupt.json"), "w", encoding="utf-8") as f:
    f.write("{not valid json")
code, out, err = run_hook({"hook_event_name": "SessionStart", "session_id": "robust-001",
                            "cwd": "C:/x"}, sdir, out_path, notes_dir)
check("exits 0 even with a corrupt sibling session file", code, 0)
check("the corrupt file's OWN session is unaffected -- new session still recorded",
      os.path.isfile(os.path.join(sdir, "robust-001.json")), True)
shutil.rmtree(root, ignore_errors=True)

root2, sdir2, out_path2, notes_dir2 = fresh_env("nodir-")
shutil.rmtree(root2, ignore_errors=True)  # remove the WHOLE root -- sessions dir never created
code, out, err = run_hook({"hook_event_name": "SessionStart", "session_id": "nodir-001",
                            "cwd": "C:/x"}, sdir2, out_path2, notes_dir2)
check("exits 0 on first-ever run (no sessions directory exists yet)", code, 0)
check("directory is created and the session recorded",
      os.path.isfile(os.path.join(sdir2, "nodir-001.json")), True)
shutil.rmtree(root2, ignore_errors=True)

print()
print("RESULT: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)

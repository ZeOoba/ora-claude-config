#!/usr/bin/env python3
"""ORA fleet pause/resume guard (WO-5, 2026-08-21 repo-architecture-review).

A paused fleet whose one-time resume task never fires -- or fires but doesn't
finish the job -- is indistinguishable from a healthy quiet fleet to every
lastRunAt-based detector. This is exactly the state OI-202 found live
2026-08-21: the resume task fired but only re-enabled 2 of 35 tasks, silently,
with no error and no summary email; nothing caught it until a human happened
to check.

Design (deliberately scoped to avoid a new secret decision the same day
CRON_SECRET was rotated -- see open-items-tracker.md#OI-197's fix (a) commit
message for the same reasoning): this runs as a native Windows Scheduled Task,
NOT a CC/MCP or LAMS fleet task. Native tasks are unaffected by a fleet pause
(only Claude-session-driven fleet tasks stop), so this alone -- no Notion
beacon, no GitHub Actions layer -- already survives the exact failure mode it
exists to catch. The one gap a purely local guard can't cover (the whole
MACHINE off for the entire pause+grace window) is already the existing
dead-man chain's job (ora-cowork-heartbeat -> Notion -> GitHub watchdog), not
this script's.

Alarms when, for either fleet:
  - the fleet's enabled ratio is at or near zero (<= --min-enabled-ratio,
    default 0.10) across ALL its non-one-time tasks, AND
  - EITHER a one-time task whose id contains "-resume-" or "resume-08" (the
    2026-08 naming convention) has a fireAt in the past by more than
    --resume-grace-minutes (default 30) while the ratio is still near-zero,
  - OR no such resume task exists at all while the ratio is near-zero and has
    been low across two consecutive runs (state file) -- an indefinite pause
    with no stated resume, or one whose registration was itself lost.

Never alarms on a single task being legitimately disabled for an unrelated
reason -- only an aggregate near-zero ratio across a whole fleet is a signal.

Also checks the GENERAL case (2026-08-21 follow-on, OI-202): ANY one-time
task, not just a fleet resume, that fired and left a stale/incomplete
task-progress-marker.py marker -- see that script for the write-side
convention. This is the general fix OI-202's fix direction asked for; the
fleet-ratio check above is the narrower, concrete instance that motivated it
and stays as an independent signal (a stalled resume with no marker at all
still trips it).

Also checks RETIRE-PENDING RESURRECTION (2026-08-22, register-scheduled-task
v2.14): a retirement that has been RATIFIED but not yet EXECUTED leaves the
task registered with enabled:false, and enabled:false is not a retirement --
it is a pause. Any fleet-wide resume (the very thing the checks above exist to
chase) flips it back on and silently reverses the decision; on a same-id
cross-fleet pair it also resurrects the duplicate the retirement existed to
remove. maintenance/_state/retire-pending.json is the register of those
in-flight retirements; this alarms when one of its ids is found enabled:true
on its named fleet. Fail-open by construction: an absent, unreadable or
malformed register yields no findings, never a crash and never a false alarm.

Sends ONE Outlook COM alert via the proven standalone path
(send-via-outlook.ps1 -- deploy-mirror.ps1 already uses this successfully
outside any Claude session). Writes a state file so a persisting alarm
doesn't re-email every run; a NEW alarm (fleet flipped from OK to ALARM, or a
newly-stalled marker) always sends immediately.

Usage:
    python pause-resume-guard.py [--json] [--min-enabled-ratio F] [--resume-grace-minutes N] [--marker-grace-minutes N]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fleet_status", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-status.py"))
fleet_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_status)

_spec2 = importlib.util.spec_from_file_location(
    "task_progress_marker", os.path.join(os.path.dirname(os.path.abspath(__file__)), "task-progress-marker.py"))
task_progress_marker = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(task_progress_marker)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "pause-resume-guard-state.json")
RETIRE_PENDING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "retire-pending.json")
SEND_SCRIPT = r"C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
RESUME_ID_RE = re.compile(r"-resume-", re.IGNORECASE)
NOTION_ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
# Same target every other native/scheduled-task alert in this fleet posts status/failure
# notes to (ora-am-brief, ora-cc-snapshot-refresh, ora-doctrine-integrity-guard, ...).
OPERATIONS_HUB_PAGE_ID = "32b6ecd8-9e59-81f2-b329-df3fd0e25062"


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def parse_fire_at(task):
    """fireAt on a live registry entry is epoch-ms (int/float), not an ISO
    string -- confirmed against the live cc/lams registries 2026-08-21. This
    used to call fa.replace(...) directly, which threw on an int and was
    silently swallowed by the except below, so overdue-resume detection could
    never fire (empty resume_tasks the same day, for the same reason -- see
    the taskId->id fix at the call site)."""
    fa = fleet_status.fire_at(task)
    if fa is None:
        return None
    try:
        return datetime.fromtimestamp(fa / 1000, tz=timezone.utc)
    except Exception:
        return None


def load_retire_pending(path=None):
    """Entries from _state/retire-pending.json: retirements RATIFIED but not yet EXECUTED.

    Shape: {"pending": [{"fleet": "cc"|"lams", "id": ..., "ratified": "YYYY-MM-DD",
    "reason": ..., "executeFrom": ...}, ...]}; a bare top-level list is also accepted.

    FAIL-OPEN, deliberately: an absent, unreadable or malformed register returns [] and
    this guard reports nothing. The register is a convenience for making an in-flight
    retirement observable -- it must never be able to crash the guard that also carries
    the fleet-ratio and stalled-marker checks, and a parse error must never masquerade
    as "no retirement is pending" ALARM-side either. Entries missing fleet or id are
    skipped rather than guessed at."""
    try:
        with open(path or RETIRE_PENDING_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    entries = data.get("pending") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    return [e for e in entries
            if isinstance(e, dict) and e.get("id") and e.get("fleet")]


def find_resurrected(tasks_by_fleet, path=None):
    """Retire-pending ids found ENABLED on their named fleet -- i.e. a ratified retirement
    that a resume (or a hand re-enable) has silently reversed while it waited to execute.

    Three outcomes per entry, only one of which is a finding:
      - id present and enabled  -> FINDING (the registration is live again)
      - id present and disabled -> normal: still awaiting execution, exactly as filed
      - id absent from the fleet -> the retirement executed; the register entry is stale
        and should be removed, but a stale entry is not an alarm (removing it is the
        executing session's job, and alarming here would punish a completed retirement).
    """
    out = []
    for e in load_retire_pending(path):
        fleet = str(e["fleet"]).lower()
        for t in tasks_by_fleet.get(fleet, []):
            if t.get("id") != e["id"]:
                continue
            if t.get("enabled"):
                out.append({"fleet": fleet, "id": e["id"],
                            "ratified": e.get("ratified", "unknown"),
                            "reason": e.get("reason", ""),
                            "executeFrom": e.get("executeFrom", "the fleet's own surface")})
            break
    return out


def analyze_fleet(label, tasks):
    recurring = [t for t in tasks if not fleet_status.is_onetime(t.get("cronExpression") or t.get("fireAt", ""))]
    if not recurring:
        return {"fleet": label, "status": "NO_RECURRING_TASKS", "ratio": None}

    enabled = sum(1 for t in recurring if t.get("enabled"))
    ratio = enabled / len(recurring)

    # NOTE (2026-08-21): live registry entries key the id as "id", not
    # "taskId" -- the original taskId lookup always returned "" and this list
    # was silently empty on every run. Same incident as parse_fire_at above.
    resume_tasks = [t for t in tasks if RESUME_ID_RE.search(t.get("id", "")) and fleet_status.fire_at(t) is not None]
    now = datetime.now(timezone.utc)
    overdue_resume = None
    for t in resume_tasks:
        fa = parse_fire_at(t)
        if fa and fa < now:
            overdue_resume = {"taskId": t.get("id"), "fireAt": t.get("fireAt"),
                               "minutesOverdue": (now - fa).total_seconds() / 60}
            break

    return {
        "fleet": label, "status": "OK", "ratio": ratio,
        "enabledCount": enabled, "totalRecurring": len(recurring),
        "overdueResume": overdue_resume,
        # A resume task that EXISTS but isn't due yet (fireAt in the future) also leaves
        # overdue_resume None -- without this, the caller's "no pending/overdue resume task
        # exists for this fleet" branch couldn't tell that apart from a genuinely absent
        # resume, and fired a false alarm on a legitimately scheduled future pause.
        "hasResumeTask": bool(resume_tasks),
    }


def _load_notion_token():
    # Exact key match (mirrors scheduled-tasks/ora-pm-ledger/*_snapshot_diff.py's
    # load_token): a prefix match would happily return NOTION_TOKEN_OLD / _BACKUP and
    # authenticate as the wrong (possibly revoked) integration.
    with open(NOTION_ENV_PATH, encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.partition("=")
            if sep and k.strip() == "NOTION_TOKEN":
                return v.strip().strip('"').strip("'")
    raise RuntimeError(f"NOTION_TOKEN not found in {NOTION_ENV_PATH}")


def _log_send_failure_to_notion(subject, identifier, proc):
    """Best-effort ONLY -- a Notion logging failure must never raise past this call. The
    guard's obligation is to have TRIED to make a silent send failure visible somewhere,
    not to guarantee delivery of the visibility mechanism itself (that would just move the
    single-point-of-failure, not remove it). Appends a paragraph block to the Operations
    Hub page, the same target every other native/scheduled-task alert in this fleet posts
    status/failure notes to."""
    try:
        token = _load_notion_token()
        text = (f"[ALERT SEND FAILED] pause-resume-guard could not deliver: {subject} "
                f"(identifier={identifier!r}, send-via-outlook.ps1 exit={proc.returncode}, "
                f"stderr={proc.stderr.strip()[:300]!r})")
        req = urllib.request.Request(
            f"https://api.notion.com/v1/blocks/{OPERATIONS_HUB_PAGE_ID}/children",
            data=json.dumps({"children": [{
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
            }]}).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            method="PATCH")
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return True
    except Exception:
        return False


def send_alert(subject, body, identifier=None):
    """One retry on a COM failure (2) or timeout (4) -- matches PR Compliance's send-script
    caller contract. Returns whether delivery actually succeeded; callers MUST check this
    (see main()) rather than assume the send happened, and MUST NOT persist alarm-suppression
    state as delivered until this returns True -- a discarded return value here previously let
    a failed send permanently suppress every future retry of a still-active alarm."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(body)
        body_path = f.name
    try:
        args = ["powershell", "-NoProfile", "-File", SEND_SCRIPT, "-To", "ggoldberg@oxfordra.net",
                "-Subject", subject, "-BodyFile", body_path, "-BodyFormat", "text"]
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode in (2, 4):
            proc = subprocess.run(args, capture_output=True, text=True)
        ok = proc.returncode == 0
        if not ok:
            _log_send_failure_to_notion(subject, identifier, proc)
        return ok
    finally:
        try:
            os.unlink(body_path)
        except OSError:
            pass


def capture_pause_windows():
    """Observe both live registries into _state/fleet-pause-windows.json (see
    _shared/pause_windows.py). Module-level so tests can stub it -- main() must not
    write live state from a unit test. Never raises."""
    out = {"held": {}, "errors": []}
    try:
        spec = importlib.util.spec_from_file_location(
            "pause_windows", os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared", "pause_windows.py"))
        pw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pw)
        return pw.capture()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append("%s: %s" % (type(exc).__name__, exc))
        return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-enabled-ratio", type=float, default=0.10)
    parser.add_argument("--resume-grace-minutes", type=float, default=30)
    parser.add_argument("--marker-grace-minutes", type=float, default=20)
    args = parser.parse_args()

    # DURABLE PAUSE RECORD (2026-09-12). Observe both registries on EVERY run and extend
    # per-task "held" intervals (disabled AND named by a pending resume) in
    # _state/fleet-pause-windows.json. This guard is a native Windows task, so it keeps
    # running through a fleet pause -- the one observer guaranteed to see a pause whether or
    # not whoever paused the fleet remembered to write a ledger (the 09-07 pause had none).
    # Observation cadence = this task's cadence, so interval edges under-count by up to one
    # run (detectors alarm early, never late). health-guard-beacon.py and fleet-status.py
    # subtract the intervals from gaps. Fail-open: a capture error is printed, never raised.
    pause_capture = capture_pause_windows()

    registries = fleet_status.discover_registries()
    results = []
    tasks_by_fleet = {}
    for label, path in registries:
        tasks, _ = fleet_status.load(path)
        tasks_by_fleet[str(label).lower()] = tasks
        results.append(analyze_fleet(label, tasks))

    state = load_state()
    now_iso = datetime.now(timezone.utc).isoformat()
    alarms = []

    for r in results:
        if r["status"] != "OK" or r["ratio"] is None:
            continue
        fleet = r["fleet"]
        near_zero = r["ratio"] <= args.min_enabled_ratio
        prev_near_zero = state.get(fleet, {}).get("nearZero", False)

        trip = False
        reason = None
        if near_zero and r["overdueResume"] and r["overdueResume"]["minutesOverdue"] > args.resume_grace_minutes:
            trip = True
            reason = (f"enabled ratio {r['ratio']:.0%} ({r['enabledCount']}/{r['totalRecurring']}), "
                       f"resume task '{r['overdueResume']['taskId']}' fireAt {r['overdueResume']['fireAt']} "
                       f"was {r['overdueResume']['minutesOverdue']:.0f}min ago and never resumed it")
        elif near_zero and not r["overdueResume"] and not r["hasResumeTask"] and prev_near_zero:
            trip = True
            reason = (f"enabled ratio {r['ratio']:.0%} ({r['enabledCount']}/{r['totalRecurring']}) for at least "
                       f"two consecutive checks, and no pending/overdue resume task exists for this fleet")

        state.setdefault(fleet, {})
        state[fleet]["nearZero"] = near_zero
        state[fleet]["lastChecked"] = now_iso

        if trip:
            # NOTE: "alarmed" is deliberately NOT set here. It must only become True once
            # send_alert() actually confirms delivery (below) -- setting it eagerly, before
            # the send is even attempted, is what let a failed Outlook delivery permanently
            # suppress every later retry of a still-active alarm.
            already_alarmed = state[fleet].get("alarmed", False)
            alarms.append({"fleet": fleet, "reason": reason, "alreadyAlarmed": already_alarmed})
        else:
            state[fleet]["alarmed"] = False

    # General case (OI-202 follow-on, 2026-08-21): ANY one-time task with a
    # stale/incomplete task-progress-marker.py marker, not just a fleet
    # resume. Tracked per taskId so a persisting stall doesn't re-email every
    # 6h run, same pattern as the fleet-ratio alarms above.
    marker_state = state.setdefault("_markers", {})
    stalled = task_progress_marker.find_stalled(args.marker_grace_minutes)
    seen_marker_ids = set()
    for s in stalled:
        tid = s["taskId"]
        seen_marker_ids.add(tid)
        already_alarmed = marker_state.get(tid, {}).get("alarmed", False)
        # Same deferred-"alarmed" fix as the fleet-ratio alarms above: only lastChecked is
        # recorded here; "alarmed" is set later, only for markers whose alert actually sent.
        marker_state.setdefault(tid, {})
        marker_state[tid]["lastChecked"] = now_iso
        reason = (f"one-time task '{tid}' ({s['fleet']}) stalled at step {s['step']}/{s['totalSteps']} "
                  f"-- marker last updated {s['staleMinutes']} min ago (note={s['note']!r})")
        alarms.append({"fleet": f"marker:{tid}", "reason": reason, "alreadyAlarmed": already_alarmed})
    # a marker that's no longer stalled (completed, or its task got re-run) clears its own alarm state
    for tid in list(marker_state.keys()):
        if tid not in seen_marker_ids:
            marker_state[tid]["alarmed"] = False

    # Retire-pending resurrection (2026-08-22, register-scheduled-task v2.14). Same
    # per-key alarm bookkeeping as the markers above so a persisting resurrection
    # doesn't re-email every 6h run.
    rp_state = state.setdefault("_retirePending", {})
    resurrected = find_resurrected(tasks_by_fleet)
    seen_rp = set()
    for rp in resurrected:  # not `r` -- `results` reuses that name in the print loop below
        key = f"{rp['fleet']}:{rp['id']}"
        seen_rp.add(key)
        already_alarmed = rp_state.get(key, {}).get("alarmed", False)
        rp_state.setdefault(key, {})["lastChecked"] = now_iso
        reason = (f"retire-pending task '{rp['id']}' ({rp['fleet']}) is ENABLED again -- its retirement "
                  f"was ratified {rp['ratified']} but never executed, so this is a LIVE registration, "
                  f"not a retired one. On file: {rp['reason']!r}. Execute from: {rp['executeFrom']}.")
        alarms.append({"fleet": f"retire-pending:{key}", "reason": reason, "alreadyAlarmed": already_alarmed})
    # an entry that is disabled again (or whose retirement finally executed) clears its own alarm state
    for key in list(rp_state.keys()):
        if key not in seen_rp:
            rp_state[key]["alarmed"] = False

    new_alarms = [a for a in alarms if not a["alreadyAlarmed"]]

    if args.json:
        print(json.dumps({"results": results, "alarms": alarms, "stalledMarkers": stalled,
                          "resurrectedRetirePending": resurrected,
                          "pauseWindowCapture": pause_capture}, indent=2, default=str))
    else:
        for r in results:
            print(f"{r['fleet']:6s} ratio={r.get('ratio')} enabled={r.get('enabledCount')}/{r.get('totalRecurring')} overdueResume={r.get('overdueResume')}")
        print(f"markers: {len(stalled)} stalled" if stalled else "markers: none stalled")
        print(f"retire-pending: {len(resurrected)} resurrected of {len(load_retire_pending())} filed")
        held = pause_capture.get("held") or {}
        print("pause observation: held " + (", ".join(f"{f}={len(v)}" for f, v in sorted(held.items())) or "-")
              + (f"; ERRORS: {pause_capture['errors']}" if pause_capture.get("errors") else ""))
        if alarms:
            print(f"[ACTION] {len(alarms)} tripped: " + "; ".join(f"{a['fleet']}: {a['reason']}" for a in alarms))
        else:
            print("No fleet shows a stuck pause, no stalled progress markers, no retire-pending id re-enabled.")

    if new_alarms:
        subject = "[ORA] Fleet pause/resume guard - ALARM"
        body_lines = ["Fleet pause/resume guard tripped (native, off-fleet check -- OI-202/WO-5).", ""]
        for a in new_alarms:
            body_lines.append(f"Source: {a['fleet']}")
            body_lines.append(f"Reason: {a['reason']}")
            body_lines.append("")
        body_lines.append("This does not auto-resume, auto-restart or auto-disable anything -- verify by hand. For a fleet-ratio alarm: resume the fleet or investigate why an automated resume didn't work. For a stalled-marker alarm: check the task's own instructions/session for where it stopped (see open-items-tracker.md#OI-202 for a real prior instance and register-scheduled-task/SKILL.md's progress-marker convention). For a retire-pending alarm: the id's ratified retirement has been reversed -- re-disable it on the named fleet and finish the retirement from the surface named in the alarm (archive-first-delete-second, ONE pass; see register-scheduled-task v2.14 RULES 3-4).")
        identifier = "; ".join(a["fleet"] for a in new_alarms)
        delivered = send_alert(subject, "\n".join(body_lines), identifier=identifier)
        # Only mark these as "alarmed" (suppressing future retries) once delivery actually
        # succeeded -- see send_alert's docstring and analyze_fleet's "alarmed" comment above.
        if delivered:
            for a in new_alarms:
                key = a["fleet"]
                if key.startswith("marker:"):
                    marker_state.setdefault(key[len("marker:"):], {})["alarmed"] = True
                elif key.startswith("retire-pending:"):
                    # keyed "<fleet>:<id>" under _retirePending -- NOT a top-level fleet key,
                    # which is what the bare else below would have written.
                    rp_state.setdefault(key[len("retire-pending:"):], {})["alarmed"] = True
                else:
                    state.setdefault(key, {})["alarmed"] = True

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())

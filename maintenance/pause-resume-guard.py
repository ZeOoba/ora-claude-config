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

Sends ONE Outlook COM alert via the proven standalone path
(send-via-outlook.ps1 -- deploy-mirror.ps1 already uses this successfully
outside any Claude session). Writes a state file so a persisting alarm
doesn't re-email every run; a NEW alarm (fleet flipped from OK to ALARM)
always sends immediately.

Usage:
    python pause-resume-guard.py [--json] [--min-enabled-ratio F] [--resume-grace-minutes N]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fleet_status", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-status.py"))
fleet_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_status)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "pause-resume-guard-state.json")
SEND_SCRIPT = r"C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
RESUME_ID_RE = re.compile(r"-resume-", re.IGNORECASE)


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
    fa = task.get("fireAt")
    if not fa:
        return None
    try:
        return datetime.fromisoformat(fa.replace("Z", "+00:00"))
    except Exception:
        return None


def analyze_fleet(label, tasks):
    recurring = [t for t in tasks if not fleet_status.is_onetime(t.get("cronExpression") or t.get("fireAt", ""))]
    if not recurring:
        return {"fleet": label, "status": "NO_RECURRING_TASKS", "ratio": None}

    enabled = sum(1 for t in recurring if t.get("enabled"))
    ratio = enabled / len(recurring)

    resume_tasks = [t for t in tasks if RESUME_ID_RE.search(t.get("taskId", "")) and t.get("fireAt")]
    now = datetime.now(timezone.utc)
    overdue_resume = None
    for t in resume_tasks:
        fa = parse_fire_at(t)
        if fa and fa < now:
            overdue_resume = {"taskId": t.get("taskId"), "fireAt": t.get("fireAt"),
                               "minutesOverdue": (now - fa).total_seconds() / 60}
            break

    return {
        "fleet": label, "status": "OK", "ratio": ratio,
        "enabledCount": enabled, "totalRecurring": len(recurring),
        "overdueResume": overdue_resume,
    }


def send_alert(subject, body):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(body)
        body_path = f.name
    try:
        args = ["powershell", "-NoProfile", "-File", SEND_SCRIPT, "-To", "ggoldberg@oxfordra.net",
                "-Subject", subject, "-BodyFile", body_path, "-BodyFormat", "text"]
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode in (2, 4):
            proc = subprocess.run(args, capture_output=True, text=True)
        return proc.returncode == 0
    finally:
        try:
            os.unlink(body_path)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-enabled-ratio", type=float, default=0.10)
    parser.add_argument("--resume-grace-minutes", type=float, default=30)
    args = parser.parse_args()

    registries = fleet_status.discover_registries()
    results = []
    for label, path in registries:
        tasks, _ = fleet_status.load(path)
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
        elif near_zero and not r["overdueResume"] and prev_near_zero:
            trip = True
            reason = (f"enabled ratio {r['ratio']:.0%} ({r['enabledCount']}/{r['totalRecurring']}) for at least "
                       f"two consecutive checks, and no pending/overdue resume task exists for this fleet")

        state.setdefault(fleet, {})
        state[fleet]["nearZero"] = near_zero
        state[fleet]["lastChecked"] = now_iso

        if trip:
            already_alarmed = state[fleet].get("alarmed", False)
            state[fleet]["alarmed"] = True
            alarms.append({"fleet": fleet, "reason": reason, "alreadyAlarmed": already_alarmed})
        else:
            state[fleet]["alarmed"] = False

    save_state(state)

    new_alarms = [a for a in alarms if not a["alreadyAlarmed"]]

    if args.json:
        print(json.dumps({"results": results, "alarms": alarms}, indent=2, default=str))
    else:
        for r in results:
            print(f"{r['fleet']:6s} ratio={r.get('ratio')} enabled={r.get('enabledCount')}/{r.get('totalRecurring')} overdueResume={r.get('overdueResume')}")
        if alarms:
            print(f"[ACTION] {len(alarms)} fleet(s) tripped: " + "; ".join(f"{a['fleet']}: {a['reason']}" for a in alarms))
        else:
            print("No fleet shows a stuck pause.")

    if new_alarms:
        subject = "[ORA] Fleet pause/resume guard - ALARM"
        body_lines = ["Fleet pause/resume guard tripped (native, off-fleet check -- OI-202/WO-5).", ""]
        for a in new_alarms:
            body_lines.append(f"Fleet: {a['fleet']}")
            body_lines.append(f"Reason: {a['reason']}")
            body_lines.append("")
        body_lines.append("This does not auto-resume anything -- verify and resume by hand, or investigate why an automated resume didn't work (see open-items-tracker.md#OI-202 for a real prior instance).")
        send_alert(subject, "\n".join(body_lines))

    return 0


if __name__ == "__main__":
    sys.exit(main())

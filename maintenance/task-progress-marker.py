#!/usr/bin/env python3
"""Per-step progress marker for model-driven one-time scheduled tasks (OI-202, 2026-08-21).

A model-driven one-time task (natural-language steps run by an agent session,
not a deterministic script) that stalls mid-run looks IDENTICAL to a healthy
"still running" task to every lastRunAt-based detector -- lastRunAt is stamped
the moment the scheduler fires it, not when/if it finishes. This is exactly
what happened to `ora-routine-pause-resume-08-21`: it fired, stamped
lastRunAt, then silently stopped after re-enabling 2 of 35 tasks with no
error and no summary email. Nothing distinguished that from "still working
through the list" until a human ran a manual `list_scheduled_tasks` diff.

This script gives a multi-step one-time task's own SKILL.md instructions a
one-line way to record "I finished step N of TOTAL" as it goes, and gives any
monitor (this session's own guard, automation-health-monitor, a future check)
a one-line way to ask "is any fired-but-incomplete task's marker stale?".

It does NOT retrofit every existing one-time task -- only ones written or
edited to call `write` at each step opt in. A task with no marker file is
invisible to `check` (neither alarmed nor cleared) rather than assumed
stalled; false alarms on tasks that never adopted the convention would be
worse than the gap this closes. See register-scheduled-task/SKILL.md's
"Progress markers for multi-step one-time tasks" section for the authoring
convention.

Usage:
    python task-progress-marker.py write --task-id <id> --step N --of TOTAL [--note "text"]
    python task-progress-marker.py check [--grace-minutes 20] [--json]
    python task-progress-marker.py clear --task-id <id>

`check` can also be imported and called as find_stalled(grace_minutes) by a
sibling monitor (see pause-resume-guard.py) instead of shelling out.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fleet_status", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-status.py"))
fleet_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_status)

MARKER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "task-progress")

# task_id becomes a filesystem path component (write/clear open/remove it directly), and
# --task-id is a free-form CLI arg with no upstream validation -- a task_id of "../../../foo"
# or an absolute path (os.path.join silently DISCARDS the MARKER_DIR prefix for an absolute
# second argument, especially on Windows with a drive letter) let write/clear touch any file
# on disk. Every real scheduled-task id in this fleet is alphanumeric plus -._, so that shape
# is enforced up front, and containment is re-checked after path construction as defense in
# depth (belt-and-suspenders: the regex should already make escape impossible, but a path
# that somehow still resolves outside MARKER_DIR is rejected rather than trusted).
_SAFE_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
# fleet is keyed the same way task_id is -- see fleet-status.py's discover_registries()
# docstring: "cc" (claude-code-sessions/MCP) and "lams" (local-agent-mode-sessions/Cowork)
# are the only two live labels, but --fleet is still a free-form CLI arg like --task-id, so
# it gets the same validation rather than being trusted as code-controlled.
_SAFE_FLEET_RE = re.compile(r"^[a-z0-9]+$")


class InvalidTaskId(ValueError):
    pass


def _marker_path(fleet, task_id):
    """Markers are keyed on (fleet, task_id), not task_id alone -- the same one-time task id
    can legitimately exist in both fleets (fleet-status.py's own find_cross_fleet_duplicates
    documents this as a real, supported case), so a bare task_id key let a marker written for
    one fleet's task be read/cleared for the other fleet's same-named task."""
    if not isinstance(fleet, str) or not _SAFE_FLEET_RE.match(fleet):
        raise InvalidTaskId(f"invalid fleet: {fleet!r}")
    if not isinstance(task_id, str) or not _SAFE_TASK_ID_RE.match(task_id):
        raise InvalidTaskId(f"invalid task id: {task_id!r}")
    path = os.path.join(MARKER_DIR, fleet, f"{task_id}.json")
    real_dir = os.path.realpath(MARKER_DIR)
    real_path = os.path.realpath(path)
    if os.path.commonpath([real_dir, real_path]) != real_dir:
        raise InvalidTaskId(f"fleet/task id escapes marker directory: {fleet!r}/{task_id!r}")
    return path


def write_marker(fleet, task_id, step, of, note=None):
    path = _marker_path(fleet, task_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "fleet": fleet,
        "taskId": task_id,
        "step": step,
        "totalSteps": of,
        "note": note,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def load_marker(fleet, task_id):
    try:
        with open(_marker_path(fleet, task_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_marker(fleet, task_id):
    try:
        os.remove(_marker_path(fleet, task_id))
        return True
    except FileNotFoundError:
        return False


def find_stalled(grace_minutes=20):
    """One-time tasks (both fleets) that have fired, carry a progress marker,
    and either haven't reached their final step or haven't updated it recently.

    A task with NO marker file is skipped entirely -- it never opted into the
    convention, so absence is not a signal (see module docstring)."""
    now = datetime.now(timezone.utc)
    stalled = []
    for label, path in fleet_status.discover_registries():
        tasks, _ = fleet_status.load(path)
        for t in tasks:
            if fleet_status.fire_at(t) is None:
                continue  # recurring task, not one-time
            if not t.get("lastRunAt"):
                continue  # hasn't fired yet -- nothing to stall
            task_id = t.get("id")
            marker = load_marker(label, task_id)
            if marker is None:
                continue
            step, total = marker.get("step", 0), marker.get("totalSteps", 0)
            if total and step >= total:
                continue  # completed cleanly
            updated_at = marker.get("updatedAt")
            stale_minutes = None
            try:
                upd = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
                stale_minutes = (now - upd).total_seconds() / 60
            except Exception:
                pass  # unparseable/missing updatedAt -- treat as stale below
            if stale_minutes is None or stale_minutes > grace_minutes:
                stalled.append({
                    "fleet": label, "taskId": task_id, "step": step, "totalSteps": total,
                    "note": marker.get("note"), "updatedAt": updated_at,
                    "staleMinutes": stale_minutes, "lastRunAt": t.get("lastRunAt"),
                })
    return stalled


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_write = sub.add_parser("write", help="Record step N of TOTAL for a one-time task")
    p_write.add_argument("--fleet", required=True, choices=["cc", "lams"])
    p_write.add_argument("--task-id", required=True)
    p_write.add_argument("--step", type=int, required=True)
    p_write.add_argument("--of", type=int, required=True, dest="of_total")
    p_write.add_argument("--note")

    p_check = sub.add_parser("check", help="Report one-time tasks whose marker shows a stall")
    p_check.add_argument("--grace-minutes", type=float, default=20)
    p_check.add_argument("--json", action="store_true")

    p_clear = sub.add_parser("clear", help="Delete a task's marker file")
    p_clear.add_argument("--fleet", required=True, choices=["cc", "lams"])
    p_clear.add_argument("--task-id", required=True)

    args = parser.parse_args()

    if args.cmd == "write":
        try:
            data = write_marker(args.fleet, args.task_id, args.step, args.of_total, args.note)
        except InvalidTaskId as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 2
        print(json.dumps(data, indent=2))
        return 0

    if args.cmd == "clear":
        try:
            removed = clear_marker(args.fleet, args.task_id)
        except InvalidTaskId as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            return 2
        print(f"{'removed' if removed else 'no marker found for'} {args.fleet}/{args.task_id}")
        return 0

    if args.cmd == "check":
        stalled = find_stalled(args.grace_minutes)
        if args.json:
            print(json.dumps(stalled, indent=2, default=str))
        elif stalled:
            for s in stalled:
                print(f"[STALLED] {s['fleet']}/{s['taskId']} step {s['step']}/{s['totalSteps']} "
                      f"(marker last updated {s['staleMinutes']} min ago; note={s['note']!r})")
        else:
            print("No stalled progress markers.")
        return 1 if stalled else 0


if __name__ == "__main__":
    sys.exit(main())

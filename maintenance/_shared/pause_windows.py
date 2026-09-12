#!/usr/bin/env python3
"""Durable record of PAST bounded fleet pauses, and "how much of this gap was a pause?".

Added 2026-09-12 (Gabriel-directed "fix this" on that day's ora-health-guard run).

WHY THIS EXISTS
---------------
`_shared/fleet_pause.py` answers "is this fleet paused RIGHT NOW". The moment a pause's
resume task fires, that answer flips to "no" and the window is gone -- so every detector
that looks BACK across a pause has nothing to read. Live 2026-09-12: the first
ora-health-guard run after the 2026-09-07 -> 09-11 CC pause reported 5 FAILs, and 3 of
them (a 124.8h beacon gap, an 11-task missed-cycle list, the am-brief/rate-snapshot
staleness) were the pause itself. The only past-pause record, a hand-written
`*_FleetPause_RestoreLedger*.json`, existed for 08-17 and was never written for 09-07.

OBSERVED STATE, NOT PARSED TEXT (read before changing the design)
-----------------------------------------------------------------
The first two cuts recognised a pause by parsing the resume task's SKILL.md. Two
adversarial refute passes the same day found ten ways that hid REAL misses: carve-outs
named in prose or in bullets, an efficacy check saying "if disabled, re-enable it", a
cancelled-then-repaused merge, a task re-enabled early by hand, ids in a code block, a
manual re-run stretching the window. Every one reduces to "text is not state".

So `capture()` records what the registry actually says. At each capture, a recurring
task is HELD iff
    (a) it is disabled right now, AND
    (b) an enabled, not-yet-fired one-time task (fireAt no more than
        PENDING_OVERDUE_GRACE_HOURS in the past) names its id in its SKILL.md AND names
        at least MIN_DISABLED_NAMED currently-disabled recurring tasks in total.
A third refute pass added three guards: (b)'s count, so a reminder that happens to
mention one accidentally-disabled task cannot excuse it; a hold longer than
MAX_WINDOW_DAYS is VOIDED entirely, since it is not a bounded pause; and an interval closes
across a blind span > MAX_UNOBSERVED_HOURS or when its task leaves the registry.
Known, accepted limit: a one- or two-task pause is not observed. Its gap alarms as it
always did (a false alarm, the safe direction); hand-record it if that matters.
Consecutive HELD observations extend one interval; any non-held observation, or evidence
the task RAN since the last observation, closes it. Intervals span first-held ->
last-held observation only, so both edges under-count by up to one capture interval --
the detectors then alarm slightly early, never late. Requiring (a) makes wording
irrelevant: a carve-out is not disabled, an efficacy check disables nothing. Requiring
(b) keeps an unrelated long-term disable from ever excusing anything.

Callers: `pause-resume-guard.py` (native Windows task, keeps running through a fleet
pause) captures every run; register-scheduled-task v2.22 captures at pause time.

HAND RECORDS
------------
A pause that predates observation (the 2026-09-07 one) is recorded with `record`,
citing its evidence in `note`. Capped at MAX_WINDOW_DAYS.

FAILURE POLICY
--------------
Never raises into a caller. An unreadable store reads as NO windows and is never
overwritten, which makes every consumer alarm exactly as it did before this module
existed -- a bug here can only ever cost a false alarm, never a suppressed real one.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys

__all__ = ["DEFAULT_STORE", "capture", "record_window", "load_windows", "overlap_hours",
           "paused_at", "discover_registry"]

UTC = datetime.timezone.utc
DEFAULT_STORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "_state", "fleet-pause-windows.json")
STORES = {"cc": "claude-code-sessions", "lams": "local-agent-mode-sessions"}
MAX_WINDOW_DAYS = 21                 # a longer hold is not a bounded pause: VOIDED, excuses nothing
PENDING_OVERDUE_GRACE_HOURS = 24.0   # a resume this far past fireAt and still unfired
                                     # no longer counts: pause-resume-guard alarms on it
MIN_DISABLED_NAMED = 3               # a one-time task is resume-shaped only if it names at
                                     # least this many CURRENTLY DISABLED recurring tasks --
                                     # a reminder mentioning one disabled task is not a pause
MAX_UNOBSERVED_HOURS = 48.0          # a longer blind span between captures closes the interval

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------- time helpers

def _aware(d):
    """Naive datetimes are UTC (fleet-status.py's lastRunAt convention)."""
    if d is None:
        return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)


def _iso(d):
    return _aware(d).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(v):
    if v is None or v == "":
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.datetime.fromtimestamp(float(v) / 1000.0, tz=UTC)
        return _aware(datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00")))
    except Exception:
        return None


# ---------------------------------------------------------------- registry

def discover_registry(fleet):
    """Most-tasks-wins, newest-mtime tie-break. Same rule as fleet-status.py /
    fleet_pause.py -- GUIDs rotate, never hardcode a path. Duplicated rather than
    imported so this module does not depend on an uncommitted sibling."""
    roaming = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    bases = [os.path.join(roaming, "Claude"),
             os.path.join(local, "Packages", "Claude_pzs8sxrjxfjjc", "LocalCache", "Roaming", "Claude")]
    best, best_key = None, None
    for base in bases:
        for p in glob.glob(os.path.join(base, STORES.get(fleet, fleet), "**", "scheduled-tasks.json"),
                           recursive=True):
            try:
                with open(p, encoding="utf-8") as fh:
                    n = len(json.load(fh).get("scheduledTasks") or [])
                key = (n, os.path.getmtime(p))
            except Exception:
                continue
            if best_key is None or key > best_key:
                best, best_key = p, key
    return best


def _held_ids(tasks, now):
    """Recurring ids that are disabled AND named by a pending RESUME-SHAPED one-time task
    (one naming >= MIN_DISABLED_NAMED currently-disabled recurring tasks)."""
    disabled = [t.get("id") for t in tasks
                if t.get("id") and t.get("cronExpression") and not t.get("enabled", True)]
    held = set()
    for t in tasks:
        if t.get("cronExpression") or t.get("fireAt") is None:
            continue
        if not t.get("enabled") or t.get("lastRunAt"):
            continue
        fire = _parse(t.get("fireAt"))
        if fire is None or fire < now - datetime.timedelta(hours=PENDING_OVERDUE_GRACE_HOURS):
            continue
        try:
            with open(t.get("filePath"), encoding="utf-8") as fh:
                text = fh.read()
        except Exception:
            continue
        named = {tid for tid in disabled
                 if re.search(r"(?<![\w-])" + re.escape(tid) + r"(?![\w-])", text)}
        if len(named) >= MIN_DISABLED_NAMED:
            held |= named
    return held


# ---------------------------------------------------------------- store

def _load_store(path):
    """(store dict, error). A missing file is an empty store, not an error."""
    if not os.path.exists(path):
        return {"version": 2, "windows": [], "observed": {}}, None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("store root is not an object")
        data.setdefault("windows", [])
        data.setdefault("observed", {})
        data["version"] = 2
        return data, None
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)


def _save(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data["windows"] = sorted(data.get("windows") or [], key=lambda w: w.get("start_utc", ""))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def load_windows(path=None, with_error=False):
    """Hand-recorded windows. With with_error=True also returns the store read error,
    which consumers use to decide whether ANY subtraction is safe."""
    data, err = _load_store(path or DEFAULT_STORE)
    wins = [w for w in ((data or {}).get("windows") or []) if isinstance(w, dict)]
    return (wins, err) if with_error else wins


def record_window(fleet, start, end, task_ids, key, note=None, path=None):
    """Hand-record (or correct, by key) one window. Refuses > MAX_WINDOW_DAYS."""
    start, end = _aware(start), _aware(end)
    if end <= start:
        raise ValueError("end must be after start")
    if end - start > datetime.timedelta(days=MAX_WINDOW_DAYS):
        raise ValueError("window longer than %d days -- record it in parts with evidence"
                         % MAX_WINDOW_DAYS)
    path = path or DEFAULT_STORE
    data, err = _load_store(path)
    if err:
        raise RuntimeError("refusing to write over unreadable pause-window store (%s)" % err)
    now = _iso(datetime.datetime.now(tz=UTC))
    window = {"key": key, "fleet": fleet, "start_utc": _iso(start), "end_utc": _iso(end),
              "task_ids": list(task_ids), "source": "manual", "note": note, "updated_at": now}
    data["windows"] = [w for w in data["windows"] if w.get("key") != key] + [window]
    _save(path, data)
    return window


def capture(fleets=("cc", "lams"), registries=None, path=None, now=None):
    """Observe each fleet once and extend/close per-task held intervals. Never raises.
    A store that cannot be read is left untouched."""
    path = path or DEFAULT_STORE
    now = _aware(now) or datetime.datetime.now(tz=UTC)
    out = {"held": {}, "errors": []}
    data, err = _load_store(path)
    if err:
        out["errors"].append("store unreadable, not written: %s" % err)
        return out
    changed = False
    for fleet in fleets:
        try:
            reg = (registries or {}).get(fleet) or discover_registry(fleet)
            if not reg:
                raise FileNotFoundError("no live registry found for fleet %r" % fleet)
            with open(reg, encoding="utf-8") as fh:
                tasks = json.load(fh).get("scheduledTasks") or []
            held = _held_ids(tasks, now)
            out["held"][fleet] = sorted(held)
            present = set()
            for t in tasks:
                tid = t.get("id")
                if not tid or not t.get("cronExpression"):
                    continue
                present.add(tid)
                key = "%s:%s" % (fleet, tid)
                ivs = data["observed"].get(key, [])
                last = ivs[-1] if ivs and ivs[-1].get("open") else None
                if last is not None:
                    ran = _parse(t.get("lastRunAt"))
                    last_end = _parse(last["end_utc"])
                    blind = (now - last_end) > datetime.timedelta(hours=MAX_UNOBSERVED_HOURS)
                    if tid not in held or blind or (ran is not None and ran > last_end):
                        last["open"] = False          # not held now, ran meanwhile, or unobserved too long
                        last = None
                        changed = True
                if tid in held:
                    streak_void = bool(ivs) and ivs[-1].get("void") and ivs[-1].get("void_streak_live")
                    if streak_void:
                        pass                          # same over-long hold continues: stays unexcused
                    elif last is not None:
                        if now - _parse(last["start_utc"]) > datetime.timedelta(days=MAX_WINDOW_DAYS):
                            # not a bounded pause after all -- void the WHOLE streak
                            last.update({"open": False, "void": True, "void_streak_live": True})
                        else:
                            last["end_utc"] = _iso(now)
                    else:
                        ivs.append({"start_utc": _iso(now), "end_utc": _iso(now), "open": True})
                        data["observed"][key] = ivs
                    changed = True
                elif ivs and ivs[-1].get("void_streak_live"):
                    ivs[-1]["void_streak_live"] = False   # hold ended; a future pause may count again
                    changed = True
            for key, ivs in data["observed"].items():   # task deleted from the registry
                if key.startswith(fleet + ":") and key.split(":", 1)[1] not in present:
                    if ivs and (ivs[-1].get("open") or ivs[-1].get("void_streak_live")):
                        ivs[-1]["open"] = False
                        ivs[-1]["void_streak_live"] = False
                        changed = True
        except Exception as exc:
            out["errors"].append("%s: %s: %s" % (fleet, type(exc).__name__, exc))
    if changed:
        data["last_capture_utc"] = _iso(now)
        try:
            _save(path, data)
        except Exception as exc:
            out["errors"].append("save failed: %s: %s" % (type(exc).__name__, exc))
    return out


# ---------------------------------------------------------------- answers

def _intervals(fleet, task_id, path):
    data, err = _load_store(path or DEFAULT_STORE)
    if err or data is None:
        return []
    iv = []
    for w in data.get("windows") or []:
        if not isinstance(w, dict) or w.get("fleet") != fleet:
            continue
        ids = w.get("task_ids") or []
        if "*" in ids or task_id in ids:
            iv.append((_parse(w.get("start_utc")), _parse(w.get("end_utc"))))
    for o in (data.get("observed") or {}).get("%s:%s" % (fleet, task_id), []):
        if o.get("void"):
            continue
        iv.append((_parse(o.get("start_utc")), _parse(o.get("end_utc"))))
    return [(s, e) for s, e in iv if s and e and e > s]


def overlap_hours(fleet, task_id, start, end, path=None):
    """Hours of [start, end] during which `task_id` on `fleet` was held by a recorded or
    observed pause. Overlaps are merged, never double-counted. 0.0 on any problem."""
    try:
        start, end = _aware(start), _aware(end)
        if start is None or end is None or end <= start:
            return 0.0
        clipped = sorted((max(s, start), min(e, end))
                         for s, e in _intervals(fleet, task_id, path) if s < end and e > start)
        total, cur_s, cur_e = 0.0, None, None
        for s, e in clipped:
            if cur_e is None or s > cur_e:
                if cur_e is not None:
                    total += (cur_e - cur_s).total_seconds()
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        if cur_e is not None:
            total += (cur_e - cur_s).total_seconds()
        return round(total / 3600.0, 2)
    except Exception:
        return 0.0


def paused_at(fleet, task_id, when, path=None):
    try:
        when = _aware(when)
        return any(s <= when < e for s, e in _intervals(fleet, task_id, path))
    except Exception:
        return False


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", default=DEFAULT_STORE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture", help="observe both registries once (held = disabled AND named by a pending resume)")
    sub.add_parser("list", help="print the store")
    r = sub.add_parser("record", help="hand-record/correct one window (cite evidence in --note)")
    r.add_argument("--fleet", required=True, choices=["cc", "lams"])
    r.add_argument("--start", required=True, help="ISO-8601 with offset, e.g. 2026-09-07T13:07:00-04:00")
    r.add_argument("--end", required=True)
    r.add_argument("--task-ids", required=True, help="comma list, or * for the whole fleet")
    r.add_argument("--key", required=True)
    r.add_argument("--note", required=True, help="the evidence this window rests on")
    o = sub.add_parser("overlap", help="hours of [start,end] a task spent paused")
    o.add_argument("--fleet", required=True)
    o.add_argument("--task-id", required=True)
    o.add_argument("--start", required=True)
    o.add_argument("--end", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "capture":
        res = capture(path=a.store)
        print(json.dumps(res, indent=2))
        return 1 if res["errors"] else 0
    if a.cmd == "list":
        data, err = _load_store(a.store)
        print(json.dumps({"store": a.store, "error": err, "data": data}, indent=2))
        return 2 if err else 0
    if a.cmd == "record":
        s, e = _parse(a.start), _parse(a.end)
        if not s or not e:
            print("start/end unparseable", file=sys.stderr)
            return 2
        ids = ["*"] if a.task_ids.strip() == "*" else [x.strip() for x in a.task_ids.split(",") if x.strip()]
        try:
            print(json.dumps(record_window(a.fleet, s, e, ids, a.key, note=a.note, path=a.store), indent=2))
        except (ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0
    h = overlap_hours(a.fleet, a.task_id, _parse(a.start), _parse(a.end), path=a.store)
    print(json.dumps({"fleet": a.fleet, "task_id": a.task_id, "pause_hours": h}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

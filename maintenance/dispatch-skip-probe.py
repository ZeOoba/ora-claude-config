#!/usr/bin/env python3
"""dispatch-skip-probe.py — dispatcher-throttle + retry-recovery classifier.

REPLACES the main.log grep in automation-health-monitor Step 0.08 items 1/3a.
That grep never had a working extraction path: the Desktop Commander content
search returns no line text for these lines, and PowerShell `Select-String`
across the rotated main*.log set times out at 90s. Step 0.08 had been running
on substitute evidence since 2026-08-09.

TWO WORKING PATHS, both verified 2026-08-13:

  PRIMARY — the registry itself. Both scheduled-tasks.json stores carry a
  `recordedSkips` map: {taskId: [{"at": <epoch ms>, "reason": "global_limit"
  |"per_task_limit"}, ...]}. This is structured, authoritative, needs no log
  parsing, and is already in hand from the same file Step 0 reads. Recovery is
  the task's own `lastRunAt` being LATER than its most recent skip.

  CONFIRMATION — main*.log, read with Python, not Select-String. A full scan of
  all five rotated logs (~45 MB) takes 0.61s. It yields the two unambiguous
  recovery lines the registry cannot give you:
    "Spawning new session for scheduled task <id>"
    "Confirmed task run for: <id>"

WHY BOTH: `lastRunAt` is stamped at DISPATCH and stamped again when the
scheduler garbage-collects a dispatch that never attached (see
ora-task-integrity-guard STEP 1.5 script 4). So registry-derived RECOVERED means
"dispatch confirmed", NOT "the task completed". `Confirmed task run for:` is the
stronger signal. Where the two disagree, the log wins and the finding is routed
to phantom-dispatch-probe.py.

Classifications (Step 0.08 vocabulary):
  THROTTLED-THEN-RECOVERED  a later spawn/confirm/lastRunAt exists  -> informational
  PROVISIONAL               most recent skip is younger than --provisional-secs
                            (default 90) -> Notion only, NEVER an alert
  DISPATCH-THROTTLED        skipped, no recovery, and past the blind spot
                            -> open finding

Exit: 0 = no open DISPATCH-THROTTLED findings   1 = at least one   2 = could not look
"""
import argparse, datetime as dt, json, os, re, sys, time

STORES = os.path.join(os.environ.get("APPDATA", r"C:\Users\Owner\AppData\Roaming"), "Claude")
ORG = r"a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350"
REG = {"cc": os.path.join(STORES, "claude-code-sessions", ORG, "scheduled-tasks.json"),
       "lams": os.path.join(STORES, "local-agent-mode-sessions", ORG, "scheduled-tasks.json")}
LOGDIR = os.path.join(STORES, "logs")

SPAWN = re.compile(r"Spawning new session for scheduled task ([A-Za-z0-9._-]+)")
CONFIRM = re.compile(r"Confirmed task run for: ([A-Za-z0-9._-]+)")
SKIPLINE = re.compile(r"Skipping dispatch for ([A-Za-z0-9._-]+): (global_limit|per_task_limit)")
TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def iso_ms(s):
    if not s:
        return None
    try:
        return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=dt.timezone.utc).timestamp() * 1000
    except Exception:
        return None


def local_ms(s):
    """main*.log stamps are LOCAL time, unlike lastRunAt which is UTC."""
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp() * 1000
    except Exception:
        return None


def fmt(ms):
    return "-" if not ms else dt.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def scan_logs(window_ms):
    """Return (spawn, confirm, skip) dicts of taskId -> newest epoch-ms, plus ok flag.

    Full Python scan of every main*.log. Measured 0.61s over ~45 MB. Do NOT
    reimplement this with PowerShell Select-String — that is what timed out.
    """
    spawn, confirm, skip = {}, {}, {}
    if not os.path.isdir(LOGDIR):
        return spawn, confirm, skip, False
    files = sorted(f for f in os.listdir(LOGDIR)
                   if f.startswith("main") and f.endswith(".log"))
    if not files:
        return spawn, confirm, skip, False
    cutoff = time.time() * 1000 - window_ms
    for f in files:
        try:
            fh = open(os.path.join(LOGDIR, f), encoding="utf-8", errors="replace")
        except Exception:
            continue
        with fh:
            for line in fh:
                if "ScheduledTasks]" not in line:
                    continue
                m = TS.match(line)
                t = local_ms(m.group(1)) if m else None
                if t is None or t < cutoff:
                    continue
                for rx, box in ((SPAWN, spawn), (CONFIRM, confirm)):
                    g = rx.search(line)
                    if g and t > box.get(g.group(1), 0):
                        box[g.group(1)] = t
                g = SKIPLINE.search(line)
                if g and t > skip.get(g.group(1), 0):
                    skip[g.group(1)] = t
    return spawn, confirm, skip, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--provisional-secs", type=int, default=90,
                    help="dispatcher retry interval is ~60s; 90s is the safety margin")
    ap.add_argument("--json-out")
    a = ap.parse_args()

    window_ms = a.window_hours * 3600000
    now = time.time() * 1000
    spawn, confirm, logskip, log_ok = scan_logs(window_ms)

    rows, could_not_look = [], []
    for fleet, path in REG.items():
        try:
            reg = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            could_not_look.append("%s registry unreadable: %s" % (fleet, e))
            continue
        tasks = {t["id"]: t for t in reg.get("scheduledTasks", [])}
        for tid, events in (reg.get("recordedSkips") or {}).items():
            recent = [e for e in events if now - e.get("at", 0) <= window_ms]
            if not recent:
                continue
            last = max(e["at"] for e in recent)
            reasons = sorted({e.get("reason", "?") for e in recent})
            lr = iso_ms((tasks.get(tid) or {}).get("lastRunAt"))
            sp, cf = spawn.get(tid), confirm.get(tid)
            age = (now - last) / 1000.0
            recovered_by = []
            if cf and cf > last:
                recovered_by.append("confirmed_task_run")
            if sp and sp > last:
                recovered_by.append("spawn_line")
            if lr and lr > last:
                recovered_by.append("lastRunAt")

            if recovered_by:
                verdict = "THROTTLED-THEN-RECOVERED"
            elif age < a.provisional_secs:
                verdict = "PROVISIONAL"
            else:
                verdict = "DISPATCH-THROTTLED"

            # lastRunAt alone is dispatch-confirmed, not completion-confirmed.
            weak = (verdict == "THROTTLED-THEN-RECOVERED"
                    and recovered_by == ["lastRunAt"] and log_ok)
            rows.append({
                "fleet": fleet, "taskId": tid, "verdict": verdict,
                "last_skip": fmt(last), "skips_in_window": len(recent),
                "reasons": reasons, "recovered_by": recovered_by,
                "skip_age_secs": round(age, 1),
                "lastRunAt": fmt(lr), "spawn": fmt(sp), "confirmed": fmt(cf),
                "dispatch_confirmed_only": weak,
            })

    rows.sort(key=lambda r: (r["verdict"], r["fleet"], r["taskId"]))
    open_findings = [r for r in rows if r["verdict"] == "DISPATCH-THROTTLED"]
    provisional = [r for r in rows if r["verdict"] == "PROVISIONAL"]

    if not log_ok:
        could_not_look.append("main*.log unreadable — recovery evidence is "
                              "registry-only (dispatch-confirmed, not completion-confirmed)")

    print("DISPATCH-SKIP PROBE  window=%.1fh  provisional_guard=%ds  log_scan=%s"
          % (a.window_hours, a.provisional_secs, "ok" if log_ok else "UNAVAILABLE"))
    for r in rows:
        tag = "[ACTION]" if r["verdict"] == "DISPATCH-THROTTLED" else "[info]"
        print("%s %-24s %-5s %-42s last_skip=%s n=%-3d %s recovered_by=%s%s"
              % (tag, r["verdict"], r["fleet"], r["taskId"], r["last_skip"],
                 r["skips_in_window"], ",".join(r["reasons"]),
                 ",".join(r["recovered_by"]) or "-",
                 "  (dispatch-confirmed only — cross-check phantom-dispatch-probe)"
                 if r["dispatch_confirmed_only"] else ""))
    for c in could_not_look:
        print("[unverifiable] %s" % c)
    print("SUMMARY throttled_ids=%d open=%d provisional=%d unverifiable=%d"
          % (len(rows), len(open_findings), len(provisional), len(could_not_look)))
    if provisional:
        print("NOTE: PROVISIONAL rows are Notion-only. Never include them in an "
              "alert email — the dispatcher retries at ~60s and the retry has "
              "not necessarily fired at read time.")

    if a.json_out:
        try:
            with open(a.json_out, "w", encoding="utf-8") as fh:
                json.dump({"ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                           "log_scan_ok": log_ok, "rows": rows,
                           "unverifiable": could_not_look}, fh, indent=1)
        except Exception as e:
            print("[unverifiable] json_out write failed: %s" % e)
            return 2

    if could_not_look and not rows:
        return 2
    return 1 if open_findings else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[unverifiable] probe raised %s: %s — a zero that might mean "
              "'couldn't look' is a failure, not a clean fleet."
              % (type(e).__name__, e))
        sys.exit(2)

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

FROZEN-LOG GATE (added 2026-08-26 -- Gabriel-directed).
Until today this probe printed `log_scan=ok` whenever the main*.log files
merely EXISTED AND OPENED. That is a readability test wearing a liveness
test's name, and on 2026-08-26 it printed `ok` against a log that had not
been written to since 2026-08-20 20:51 -- 134.5 hours dead, and NOT revived
by a Windows-Update restart at 11:12:09 ET that morning during which the app
came up and dispatched 12+ tasks. phantom-dispatch-probe.py had gained a gate
for exactly this on 2026-08-24; this probe had not, so the same machine
carried one detector that knew and one that did not.

The verdict now comes from `_shared/log_liveness.py`, which both this probe
and ora-health-guard Block A.0d call, so the rule lives in ONE place. Nothing
about the PRIMARY (registry) leg changes -- `recordedSkips` is structured
registry state, wholly independent of the log, and was correct throughout both
incidents. Rows are still computed and printed in full when the log is dead;
what changes is that the run stops calling itself clean, and every recovery
resting on `lastRunAt` alone is marked dispatch-confirmed-only.

Exit: 0 = no open DISPATCH-THROTTLED findings   1 = at least one
      2 = could not look -- INCLUDING a frozen/behind log. Per
          automation-health-monitor Step 0.08 item 5, a 2 is reported as
          [unverifiable] and the audit continues; it never blocks the run and
          is never reported as clean.
"""
import argparse, datetime as dt, json, os, re, sys, time

# Dynamic store resolution (2026-08-15): both registry paths used to hardcode
# the a6ad2c61.../583f08bc... session UUID pair directly, unlike every other
# probe (cc-verifier-probe.py, registry-membership-probe.py, fleet-status.py),
# which already route through the shared discover_store() -- "GUIDs rotate,
# never hardcode" (store_discovery.store_name() docstring). A reinstall or
# session-dir rotation would have silently blinded this probe to both fleets.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: discover_store() returns None -> REG path is None,
                # main()'s existing per-fleet try/except already reports that
                # as "registry unreadable" via could_not_look.
try:
    import log_liveness as _ll
except Exception:
    _ll = None  # fail CLOSED, unlike _sd above: if the liveness module cannot
                # be imported we cannot establish that the log is live, and an
                # unestablished liveness is exactly the thing this gate exists
                # to stop us calling "ok". main() turns this into an
                # [unverifiable] + exit 2, never a silent pass.

STORES = os.path.join(os.environ.get("APPDATA", r"C:\Users\Owner\AppData\Roaming"), "Claude")
REG = {"cc": _sd.discover_store("claude-code-sessions") if _sd else None,
       "lams": _sd.discover_store("local-agent-mode-sessions") if _sd else None}
# DISCOVERED, not hardcoded (2026-08-26). Was os.path.join(STORES, "logs"),
# i.e. %APPDATA%\Claude\logs -- the tree the app abandoned on 2026-08-20 when it
# moved logging to %LOCALAPPDATA%\Claude\Logs. Same "GUIDs rotate, never
# hardcode" rule that already governs the registry paths two lines above; a
# hardcoded absolute path is an unverified assumption either way.
LOGDIR = str(_ll.discover_log_dir()[0]) if _ll else os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Claude", "Logs")

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


def main(argv=None):
    # argv is threaded through (rather than always reading sys.argv) so
    # test-dispatch-skip-probe.py can drive main() end-to-end against synthetic
    # registries and log dirs. Same signature as phantom-dispatch-probe.main.
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--provisional-secs", type=int, default=90,
                    help="dispatcher retry interval is ~60s; 90s is the safety margin")
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)

    window_ms = a.window_hours * 3600000
    now = time.time() * 1000
    spawn, confirm, logskip, log_ok = scan_logs(window_ms)

    rows, could_not_look = [], []
    newest_activity_ms = None  # most recent lastRunAt across BOTH fleets, for
                               # the liveness BEHIND check: a registry dispatch
                               # newer than the newest log byte means the app is
                               # running and not logging.
    for fleet, path in REG.items():
        try:
            with open(path, encoding="utf-8") as _fh:   # was a bare json.load(open(...)),
                reg = json.load(_fh)                     # which leaked a handle per fleet
        except Exception as e:
            could_not_look.append("%s registry unreadable: %s" % (fleet, e))
            continue
        tasks = {t["id"]: t for t in reg.get("scheduledTasks", [])}
        for t in tasks.values():
            ms = iso_ms(t.get("lastRunAt"))
            if ms and (newest_activity_ms is None or ms > newest_activity_ms):
                newest_activity_ms = ms
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
            # The `and log_ok` clause that used to live here was backwards: it
            # DROPPED this caveat precisely when the log could not corroborate,
            # i.e. exactly when the caveat matters most. The weakness is a
            # property of the evidence, not of whether a second source happened
            # to be available to contradict it.
            weak = (verdict == "THROTTLED-THEN-RECOVERED"
                    and recovered_by == ["lastRunAt"])
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

    # ---- LOG-LIVENESS GATE (2026-08-26) ---------------------------------
    # `log_ok` from scan_logs() only ever meant "main*.log exists and opened".
    # Liveness is a different property and gets its own verdict, from the one
    # shared module, so this probe and ora-health-guard A.0d cannot drift.
    if _ll is None:
        live = None
        could_not_look.append(
            "_shared/log_liveness.py could not be imported — log liveness is "
            "UNESTABLISHED this run; treat every log-derived signal below as unverifiable")
        log_scan = "UNESTABLISHED"
    else:
        live = _ll.assess(
            LOGDIR, window_hours=a.window_hours,
            newest_activity=(dt.datetime.fromtimestamp(newest_activity_ms / 1000.0)
                             if newest_activity_ms else None))
        log_scan = live.verdict if not (live.usable and log_ok) else "ok"
        if not live.usable:
            could_not_look.append(
                "desktop log is %s (%s) — the confirmation leg is dead. Recovery "
                "evidence below is registry-only: dispatch-confirmed, NOT "
                "completion-confirmed." % (live.verdict, live.detail))
        elif not log_ok:
            could_not_look.append("main*.log unreadable — recovery evidence is "
                                  "registry-only (dispatch-confirmed, not completion-confirmed)")

    print("DISPATCH-SKIP PROBE  window=%.1fh  provisional_guard=%ds  log_scan=%s"
          % (a.window_hours, a.provisional_secs, log_scan))
    if live is not None and not live.usable:
        print(live.banner())
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
                           "log_scan_ok": log_ok,
                           "log_liveness": live.as_dict() if live else
                                           {"verdict": "UNESTABLISHED", "usable": False},
                           "rows": rows,
                           "unverifiable": could_not_look}, fh, indent=1)
        except Exception as e:
            print("[unverifiable] json_out write failed: %s" % e)
            return 2

    if could_not_look and not rows:
        return 2
    # A dead confirmation leg is "could not look", not "looked and it was
    # clean" -- same contract as phantom-dispatch-probe.py, so one mental model
    # covers both. The registry rows above are still printed in full and remain
    # trustworthy; Step 0.08 item 5 says to report the gap as [unverifiable]
    # and continue, never to block the audit on it.
    if live is None or not live.usable:
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

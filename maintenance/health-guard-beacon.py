#!/usr/bin/env python3
"""ora-health-guard LOCAL durable beacon (Block B.3.5). Write-always, network-free.

WHY THIS EXISTS
---------------
The Block B.3.5 beacon was a Notion page and nothing else. That made the ONE detector
built to survive a lying `lastRunAt` depend on the connector whose outage is among the
most common ways a run degrades -- so "the task never ran" and "the task ran fine but
Notion was down" produced identical evidence.

That is not hypothetical. On 2026-08-04 the run woke 51 minutes late, executed end to
end, and sent all three emails (A.0 late-wake alert 06:09:43, pre-flight mirror
06:20:19, `[ACTION] Health Guard` 06:24:05 -- all exit 0). Every one of its four
notion-fetch calls returned net::ERR_FAILED, so per spec B.3.5 it correctly skipped the
Notion beacon write. Consequences, all false:
  * the 2026-08-05 run measured a 42h Notion gap and reported a FAIL that never happened;
  * the off-machine watchdog opened ZeOoba/ora-cowork-watchdog#10
    ("Health Guard Beacon Stale -- silent for 26.6h") on the same non-event.

This module makes the local write unconditional and dependency-free, so the question
"did ora-health-guard run?" is answerable from disk. The Notion page stays as the
CROSS-FLEET surface (automation-health-monitor and the GitHub Actions watchdog read it);
this file is the on-machine source of truth that B.3.5a reads FIRST.

DESIGN RULES
------------
* Write unconditionally, before/independent of any network call. Never let a connector
  failure skip it -- that is the whole bug.
* Never raise into the caller. A beacon that crashes the daily health guard is worse
  than one that is briefly wrong; write_beacon returns False on failure instead.
* Absent/corrupt store reads as UNKNOWN, never as a silent pass
  (memory: feedback_verified_null_vs_inferred_null -- a zero that could mean
  "couldn't look" is a failure).
* Keep a short ledger, not a single value: distinguishing "Notion has been unwritable
  across the whole gap" from "the task genuinely stopped" needs more than one sample.
"""
import argparse
import json
import os
import sys
import datetime

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
DEFAULT_STORE = os.path.join(HOME, ".claude", "maintenance", "_state",
                             "health-guard-beacon.json")
# Cron is `15 5 * * *` -- daily INCLUDING weekends -- so one missed cycle plus margin.
# Same threshold the Notion beacon and the GitHub Actions watchdog use; keep in step.
STALE_HOURS = 26.0
MAX_ENTRIES = 30          # ~a month of daily runs; bounded so the file cannot grow forever


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _parse(iso):
    """ISO-8601 -> aware datetime, or None. Tolerates a trailing Z and naive input."""
    if not iso:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:                       # naive -> assume machine-local (ET here)
        dt = dt.astimezone()
    return dt


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None                             # missing OR corrupt -> caller reports UNKNOWN
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return None
    return data


def write_beacon(path, status, subject_sent, failed_connectors,
                 notion_written, notion_error=None, now_iso=None):
    """Append one run record. Returns True on success, False on any failure -- never raises.

    Call this EVERY run, pass or fail, before or independent of the Notion write. Its
    whole value is that it cannot be skipped by a connector outage.
    """
    entry = {
        "last_run_et": now_iso or _now_iso(),
        "status": status,
        "subject_sent": subject_sent,
        "failed_connectors": failed_connectors,
        "notion_written": bool(notion_written),
        "notion_error": notion_error,
    }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        data = _load(path) or {"entries": []}
        data["entries"].append(entry)
        data["entries"] = data["entries"][-MAX_ENTRIES:]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)                   # atomic: a torn write cannot orphan the beacon
        return True
    except Exception:
        return False


def read_beacon(path, now_iso=None):
    """Gap verdict from the LOCAL ledger.

    Returns {verdict, gap_hours, last_run_et, last_entry, notion_gap_explained,
             last_notion_write_et}.

      verdict OK       -- ran within STALE_HOURS
      verdict STALE    -- genuinely silent too long (a real missed cycle)
      verdict UNKNOWN  -- no readable store; explicitly NOT a pass

    notion_gap_explained is True when the task HAS been running but could not write
    Notion -- i.e. a Notion-side gap that is accounted for rather than evidence of a
    missed run. That is exactly the 2026-08-04 case.
    """
    now = _parse(now_iso) or datetime.datetime.now().astimezone()
    data = _load(path)
    entries = (data or {}).get("entries") or []
    if not entries:
        return {"verdict": "UNKNOWN", "gap_hours": None, "last_run_et": None,
                "last_entry": None, "notion_gap_explained": False,
                "last_notion_write_et": None}

    last = entries[-1]
    ts = _parse(last.get("last_run_et"))
    if ts is None:
        return {"verdict": "UNKNOWN", "gap_hours": None, "last_run_et": None,
                "last_entry": last, "notion_gap_explained": False,
                "last_notion_write_et": None}

    gap = (now - ts).total_seconds() / 3600.0
    verdict = "OK" if gap <= STALE_HOURS else "STALE"

    last_notion = next((e.get("last_run_et") for e in reversed(entries)
                        if e.get("notion_written")), None)
    # Explained only when the local side is healthy: the task ran recently AND the most
    # recent run could not write Notion. If the task itself has gone quiet, the Notion
    # gap is a real symptom and must not be excused.
    notion_explained = bool(verdict == "OK" and not last.get("notion_written"))

    return {"verdict": verdict, "gap_hours": round(gap, 2),
            "last_run_et": last.get("last_run_et"), "last_entry": last,
            "notion_gap_explained": notion_explained,
            "last_notion_write_et": last_notion}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="append this run's record (call EVERY run)")
    w.add_argument("--status", required=True, choices=["OK", "DEGRADED"])
    w.add_argument("--subject", required=True, help="exact subject line sent in B.3")
    w.add_argument("--failed-connectors", default="none")
    w.add_argument("--notion-written", required=True, choices=["true", "false"])
    w.add_argument("--notion-error", default=None)
    w.add_argument("--store", default=DEFAULT_STORE)

    r = sub.add_parser("read", help="gap verdict from the local ledger (B.3.5a)")
    r.add_argument("--store", default=DEFAULT_STORE)

    a = ap.parse_args()
    if a.cmd == "write":
        ok = write_beacon(a.store, status=a.status, subject_sent=a.subject,
                          failed_connectors=a.failed_connectors,
                          notion_written=(a.notion_written == "true"),
                          notion_error=a.notion_error)
        print(json.dumps({"written": ok, "store": a.store}))
        return 0 if ok else 1                   # non-zero is a real signal: disk write failed

    out = read_beacon(a.store)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

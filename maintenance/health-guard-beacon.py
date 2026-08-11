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

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:
    _ET = None          # tzdata unavailable -- nominal interval falls back to a flat 24h

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
DEFAULT_STORE = os.path.join(HOME, ".claude", "maintenance", "_state",
                             "health-guard-beacon.json")
# Cron is `15 5 * * *` -- daily INCLUDING weekends.
NOMINAL_INTERVAL_HOURS = 24.0
CRON_HOUR, CRON_MINUTE = 5, 15          # ora-health-guard's own cron slot, ET
# CRON-AWARE TOLERANCE (2026-08-11, replaces the old flat STALE_HOURS=26.0):
# a flat wall misfired live on 2026-08-09->08-10 (27.4h) and 2026-08-10->08-11
# (28.9h) -- both runs completed, each just woke late that morning, and the
# two latenesses stacked past 26h with no missed cycle. Tolerance is now the
# nominal 24h interval plus how late THIS read is against the 05:15 ET slot
# (bounded to [0, 24h) by construction -- see _todays_lateness_hours), which
# absorbs a stacked-late-wake gap while a genuine multi-day outage (the real
# 2026-08-05->08-09 99.4h gap) is nowhere near even the widest possible
# tolerance (<48h) and still fires STALE.
# NOTE: the off-machine GitHub Actions watchdog (ZeOoba/ora-cowork-watchdog,
# health-guard-beacon.yml) independently hardcodes a flat 26h check against
# the NOTION mirror of this beacon -- it is a separate repo this session
# cannot reach and now diverges from the local logic below. Flagged as a
# follow-up, not fixed here.
MAX_ENTRIES = 30          # ~a month of daily runs; bounded so the file cannot grow forever


def _todays_lateness_hours(now):
    """Hours since the most recent 05:15 ET boundary at/before `now`. Always
    in [0, 24) by construction -- this measures how late TODAY's wake is
    against the cron slot, not accumulated multi-day drift, so it cannot by
    itself mask a genuine multi-day outage.

    `now` is normalized to ET first (2026-08-11 adversarial-review finding):
    CRON_HOUR/CRON_MINUTE are ET, but read_beacon()'s `now_iso` accepts any
    offset -- including the 'Z'-suffixed UTC form lastRunAt is stored in
    elsewhere in this codebase -- and a bare `.replace(hour=...)` on a
    non-ET-offset `now` silently reinterpreted that wall-clock number in the
    wrong zone, inflating the tolerance by the full UTC-ET offset (verified:
    4h) with no error. Falls back to `now` as-is if tzdata is unavailable or
    `now` is naive, matching the pre-fix behavior in that degraded case."""
    if _ET is not None and now.tzinfo is not None:
        now = now.astimezone(_ET)
    slot = now.replace(hour=CRON_HOUR, minute=CRON_MINUTE, second=0, microsecond=0)
    if now < slot:
        slot -= datetime.timedelta(days=1)
    return (now - slot).total_seconds() / 3600.0


def _nominal_interval_hours(now):
    """Real elapsed hours between today's and yesterday's 05:15 ET cron slot.
    24h on an ordinary day -- but the scheduler fires on LOCAL WALL CLOCK, so
    this is genuinely 23h or 25h across a DST transition, not 24h (regression
    caught by adversarial review 2026-08-11: a fixed 24.0 constant falsely
    read STALE on the Oct31->Nov1 2026 fall-back day even though both runs
    were exactly on time, because the real elapsed interval was 25h). Uses
    zoneinfo to resolve each date's own ET offset rather than shifting `now`'s
    fixed-offset tzinfo by a naive timedelta, which would not observe the
    transition at all. Falls back to the flat NOMINAL_INTERVAL_HOURS if the
    system has no tzdata for America/New_York or `now` is naive."""
    if _ET is None or now.tzinfo is None:
        return NOMINAL_INTERVAL_HOURS
    now_et = now.astimezone(_ET)
    today = now_et.date()
    if now_et.time() < datetime.time(CRON_HOUR, CRON_MINUTE):
        today -= datetime.timedelta(days=1)
    yesterday = today - datetime.timedelta(days=1)
    today_slot = datetime.datetime(today.year, today.month, today.day,
                                   CRON_HOUR, CRON_MINUTE, tzinfo=_ET)
    yesterday_slot = datetime.datetime(yesterday.year, yesterday.month, yesterday.day,
                                       CRON_HOUR, CRON_MINUTE, tzinfo=_ET)
    # Both share the SAME ZoneInfo instance, so a direct subtraction silently
    # takes Python's naive-subtraction fast path and drops the DST
    # adjustment entirely (verified empirically: 24h instead of 25h across
    # the fall-back transition) -- round-trip through a fixed-offset zone
    # (UTC) first so the subtraction is forced through each datetime's own
    # resolved utcoffset().
    utc = datetime.timezone.utc
    return (today_slot.astimezone(utc) - yesterday_slot.astimezone(utc)).total_seconds() / 3600.0


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
    except Exception as exc:                    # noqa: BLE001 -- never raise, but never SILENT
        # Returning a bare False loses WHY. registry-membership-probe.py shipped a
        # silent `except: pass` on its own log append and went quiet for two days
        # (fixed 2026-08-05); the caller sees exit 1 but nobody could say what broke.
        print("beacon write FAILED (%s: %s) -> %s"
              % (exc.__class__.__name__, exc, path), file=sys.stderr)
        return False


def read_beacon(path, now_iso=None):
    """Gap verdict from the LOCAL ledger.

    Returns {verdict, gap_hours, last_run_et, last_entry, notion_gap_explained,
             last_notion_write_et}.

      verdict OK       -- ran within tolerance (NOMINAL_INTERVAL_HOURS + today's
                          own wake-lateness against the 05:15 ET slot)
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
    tolerance = _nominal_interval_hours(now) + _todays_lateness_hours(now)
    verdict = "OK" if gap <= tolerance else "STALE"

    last_notion = next((e.get("last_run_et") for e in reversed(entries)
                        if e.get("notion_written")), None)
    # Explained only when the local side is healthy: the task ran recently AND the most
    # recent run could not write Notion. If the task itself has gone quiet, the Notion
    # gap is a real symptom and must not be excused.
    notion_explained = bool(verdict == "OK" and not last.get("notion_written"))

    return {"verdict": verdict, "gap_hours": round(gap, 2),
            "tolerance_hours": round(tolerance, 2),
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
    w.add_argument("--now-iso", default=None,
                   help="ET timestamp of the run being recorded, e.g. "
                        "2026-08-04T06:05:18-04:00. Omit for a live run. REQUIRED when "
                        "BACKFILLING a past run: without it the entry is stamped with the "
                        "backfill time, which silently claims the run happened now. That "
                        "is exactly how the 2026-08-04 and 08-05 entries came to be stamped "
                        "2026-08-05T11:26:53 -- write_beacon() always took now_iso, but the "
                        "CLI had no way to pass it.")

    r = sub.add_parser("read", help="gap verdict from the local ledger (B.3.5a)")
    r.add_argument("--store", default=DEFAULT_STORE)

    a = ap.parse_args()
    if a.cmd == "write":
        ok = write_beacon(a.store, status=a.status, subject_sent=a.subject,
                          failed_connectors=a.failed_connectors,
                          notion_written=(a.notion_written == "true"),
                          notion_error=a.notion_error, now_iso=a.now_iso)
        print(json.dumps({"written": ok, "store": a.store}))
        return 0 if ok else 1                   # non-zero is a real signal: disk write failed

    out = read_beacon(a.store)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

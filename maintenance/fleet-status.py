#!/usr/bin/env python3
"""ORA fleet-status -- DUAL-FLEET scheduler-store reporter (corrected 2026-06-10).

DUAL-FLEET DOCTRINE (2026-06-10, supersedes the "LAMS orphaned" claim): TWO live
registries, both firing only while the Desktop app is open. (1) CC/MCP fleet --
claude-code-sessions scheduled-tasks.json, written by the scheduled-tasks MCP
(Desktop "Scheduled" sidebar; 14 tasks). (2) LAMS/Cowork fleet --
local-agent-mode-sessions scheduled-tasks.json, written by Cowork sessions
(om-intake-ocr, replacement-cost-refresh, cowork-heartbeat, scheduled-task-
integrity-guard). Cowork-created tasks land in LAMS BY DESIGN. This reporter
reads BOTH and tags each task with its fleet. Cross-check run-liveness with the
[ORA] Health Guard email or the GitHub ora-cowork-watchdog.

Usage:
  python fleet-status.py                 # full table + live fleet health
  python fleet-status.py --summary       # health summary only
  python fleet-status.py --registry PATH # force a single registry (used by tests)
  python fleet-status.py --json          # machine-readable
"""
import os, sys, json, glob, argparse, datetime

for _s in (sys.stdout, sys.stderr):  # UTF-8 safe output on Windows cp1252 pipes
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: fall back to the built-in base list below

def discover_registries():
    """All live scheduler registries: [(fleet_label, path), ...].

    DUAL-FLEET (2026-06-10): cc = claude-code-sessions (MCP fleet), lams =
    local-agent-mode-sessions (Cowork fleet). BOTH live. GUIDs rotate -> never
    hardcode (I4). The MSIX LocalCache path mirrors Roaming via virtualization
    -> one registry per store (biggest, then newest, Roaming preferred by order)."""
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    out = []
    for label, store in (("cc", "claude-code-sessions"),
                         ("lams", "local-agent-mode-sessions")):
        # roots from _shared/scheduler-stores.json (single source 2026-07-09);
        # the built-in list is the fail-open fallback if the helper is unavailable
        bases = _sd.store_bases(store) if _sd else [
            os.path.join(appdata, "Claude", store),
            os.path.join(local, "Packages", "Claude_pzs8sxrjxfjjc", "LocalCache",
                         "Roaming", "Claude", store),
        ]
        cands = []
        for base in bases:
            cands += glob.glob(os.path.join(base, "**", "scheduled-tasks.json"),
                               recursive=True)
        scored = []
        for p in cands:
            try:
                d = json.load(open(p, encoding="utf-8"))
                n = len(d.get("scheduledTasks", []) or [])
                if n > 0:
                    scored.append((n, os.path.getmtime(p), p))
            except Exception:
                continue
        if scored:
            # prefer most tasks, tie-break newest mtime; one registry per store
            scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
            out.append((label, scored[0][2]))
    return out


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    tasks = d.get("scheduledTasks", []) or []
    if isinstance(tasks, dict):
        tasks = list(tasks.values())
    skips = d.get("recordedSkips", {}) or {}
    return tasks, skips


def cron_hm(expr):
    """Return (hour, minute) for a 5-field cron with exactly ONE fixed fire time,
    or None for one-time/epoch/unknown/wildcard/multi-fire expressions. Thin
    wrapper over cron_hms() -- kept for call sites that only make sense for a
    single fire time (a multi-fire cron returns None here, same as before this
    fix, so those call sites are unaffected)."""
    hms = cron_hms(expr)
    if not hms or len(hms) != 1:
        return None
    return hms[0]


def cron_hms(expr):
    """Return a sorted list of every (hour, minute) this 5-field cron fires at on
    a matching day, or None if it isn't a fixed set of times (wildcard hour/minute,
    a step value like '*/15', a one-time epoch, or malformed).

    BUG THIS CLOSES (flagged 2026-07-27c, still open 2026-08-09): the prior
    cron_hm() called int(hr)/int(mn) directly, so a multi-fire hour field like
    "7,13,19" (e.g. ora-lease-snapshot-refresh, ora-aaos-expire-leases) raised
    ValueError and the WHOLE task silently vanished from the AM-pileup count,
    same-time collision detection, AND the missed-cycle detector -- not just
    undercounted, completely invisible to all three. Supports comma lists and
    a-b ranges via the existing _parse_cron_set() (same grammar already used
    for dom/month/dow); a bare '*' hour or minute field is still treated as
    "not a fixed time" (matching cron_hm()'s prior behavior) rather than
    expanding to all 24/60 values, which would swamp collision/pileup output
    with meaningless matches."""
    if not isinstance(expr, str):
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    mn, hr = parts[0], parts[1]
    if mn == "*" or hr == "*":
        return None
    try:
        hours = _parse_cron_set(hr, 0, 23)
        minutes = _parse_cron_set(mn, 0, 59)
    except ValueError:
        return None  # step values ('*/15') or other unparseable forms
    return sorted((h, m) for h in hours for m in minutes)


def _parse_cron_set(field, lo, hi):
    """Parse one non-minute/hour cron field into the set of ints it matches.
    '*' -> the full [lo, hi] range. Supports comma lists and a-b ranges (the
    only forms used across the live fleet)."""
    if field == "*":
        return set(range(lo, hi + 1))
    out = set()
    for part in field.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def _cron_fires_on(dom_field, mon_field, dow_field, dom_val, mon_val, dow_val):
    """NOT standard POSIX cron OR-semantics. The live Claude scheduled-task
    engine's own nextRunAt uses AND (intersection) when BOTH dom and dow are
    restricted -- confirmed 2026-07-28 against ora-entry-market-scan
    ("0 11 1-7 * 2"): its registered nextRunAt was 2026-08-04 (the first
    Tuesday that also falls within days 1-7), skipping Aug 1-3 even though
    those days satisfy the dom-only OR-match. Under POSIX OR semantics
    nextRunAt would have been Aug 1, not Aug 4. This function must mirror the
    live engine, not the textbook, or this script's missed-cycle/collision
    checks silently diverge from what the scheduler actually does (see
    test_fleet_status_missed_cycle.py::
    test_compound_dom_dow_cron_uses_first_match_semantics_not_or, and
    reference_fleet_status_compound_cron_and_semantics.md for the incident).
    If only one of dom/dow is restricted, that one alone governs (unambiguous
    either way); if neither, every day in-month matches."""
    if mon_val not in _parse_cron_set(mon_field, 1, 12):
        return False
    dom_restricted = dom_field != "*"
    dow_restricted = dow_field != "*"
    if dom_restricted and dow_restricted:
        return (dom_val in _parse_cron_set(dom_field, 1, 31)
                and dow_val in _parse_cron_set(dow_field, 0, 6))
    if dom_restricted:
        return dom_val in _parse_cron_set(dom_field, 1, 31)
    if dow_restricted:
        return dow_val in _parse_cron_set(dow_field, 0, 6)
    return True


def crons_share_a_day(expr_a, expr_b):
    """Two 5-field crons already known to share (hour, minute) -- do they also
    share at least one calendar day, i.e. can they ever actually fire at once?
    Walks a full leap year (366 days, covers every dom/month combination) with
    stdlib datetime only. Two tasks at the same clock time on disjoint days
    (e.g. Mon 13:30 vs Wed 13:30) are NOT a real collision -- this is the check
    cron_hm()-only grouping was missing (added 2026-07-20 after fleet-status
    flagged ora-financial-code-integrity-sweep x ora-appsec-sweep, Mon vs Wed,
    as a false-positive same-time collision)."""
    pa, pb = expr_a.split(), expr_b.split()
    if len(pa) != 5 or len(pb) != 5:
        return True  # can't parse -> don't suppress, fail toward flagging
    _, _, dom_a, mon_a, dow_a = pa
    _, _, dom_b, mon_b, dow_b = pb
    d = datetime.date(2024, 1, 1)  # 2024 is a leap year
    for offset in range(366):
        cur = d + datetime.timedelta(days=offset)
        dow_val = (cur.weekday() + 1) % 7  # cron: Sun=0..Sat=6; python: Mon=0..Sun=6
        if (_cron_fires_on(dom_a, mon_a, dow_a, cur.day, cur.month, dow_val)
                and _cron_fires_on(dom_b, mon_b, dow_b, cur.day, cur.month, dow_val)):
            return True
    return False


def is_onetime(expr):
    """Legacy: a one-time task may carry an epoch-ms value in cronExpression."""
    if isinstance(expr, (int, float)):
        return True
    return isinstance(expr, str) and expr.strip().isdigit()


def fire_at(t):
    """Return the one-time fireAt epoch-ms for a task, else None.
    One-time tasks use a top-level `fireAt` field; cronExpression is null."""
    fa = t.get("fireAt")
    if isinstance(fa, (int, float)):
        return int(fa)
    expr = t.get("cronExpression")
    if is_onetime(expr):
        return int(expr)
    return None


def cadence_buffer_days(expr):
    """Heuristic buffer (days) before a never-fired RECURRING task counts as overdue,
    inferred from which cron fields are restricted -- no cron library (stdlib only),
    intentionally approximate. Returns None if the cadence can't be classified (caller
    must then not flag, rather than guess). Only suppresses false positives for
    infrequent cadences; never affects same-time collisions or one-time fire checks.

    Recalibration (2026-07-14): the prior verdict flagged ANY never-ran task
    regardless of cadence, so a quarterly/annual task that simply hadn't reached its
    first fire yet permanently kept the fleet at ATTENTION -- structurally unable to
    ever show OK on a fleet with mixed cadences. See test-fleet-status.py."""
    if not isinstance(expr, str):
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    _mn, _hr, dom, mon, dow = parts
    if mon != "*":       # month restricted -> quarterly/annual-ish
        return 120
    if dom != "*":       # day-of-month restricted, month open -> monthly-ish
        return 40
    if dow != "*":       # day-of-week restricted -> weekly-ish
        return 10
    return 3              # daily/hourly/frequent


# MISSED-SINGLE-CYCLE detector (added 2026-07-27, closes OI-031).
#
# Gap this closes: never_ran_overdue only applies to a RECURRING task that has
# NEVER fired even once; expired_needs_attention only applies to expired
# ONE-TIME tasks; throttle-skip tracking only catches a task that fired and got
# rate-limited. None of the three can detect "this weekly/monthly task has run
# before, is still enabled, but silently missed its most recent scheduled
# cycle" -- exactly the gap that let ora-master-workbook-ingest's 2026-07-20
# Monday fire go unnoticed for a full week despite same-day fleet snapshots
# reporting "0 overdue, 0 missed/stuck". This is additive only -- it does not
# change any existing field's meaning or the pre-existing verdict inputs above.
#
# KNOWN LIMITATION (OI-070, logged 2026-08-04): this is a POINT-IN-TIME check.
# It compares lastRunAt against only the single most-recent expected fire as
# of THIS run -- the registry carries no run history beyond that one scalar.
# If a task misses one or more cycles and then fires again before the next
# fleet-status.py invocation, lastRunAt advances and the earlier gap becomes
# permanently invisible here (confirmed 2026-08-04: ora-health-guard missed
# 07-31/08-01/08-02, resumed 08-03/08-04, and this detector read 0 -- the
# 3-day gap was only recoverable from the scheduler's own run log). A clean
# "0" from this check means "no CURRENTLY open miss", not "nothing was ever
# missed" -- do not report it as a historical census.
MISSED_CYCLE_GRACE_HOURS = 24  # generous: fleet only fires while the Desktop
                               # app is open, so some lateness is normal and
                               # expected, not a fault. Flags only once a task
                               # is more than a full day late to its own cadence.

def _local_utc_offset():
    """Best-effort fixed UTC offset for 'now' on this machine (cron is evaluated
    in local time per doctrine; lastRunAt is stored as UTC ISO8601 'Z')."""
    return datetime.datetime.now().astimezone().utcoffset() or datetime.timedelta(0)


def parse_last_run_utc(s):
    """Parse a lastRunAt ISO8601 string (with or without trailing 'Z') into a
    naive UTC datetime, or None if missing/unparseable."""
    if not isinstance(s, str) or not s:
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def most_recent_expected_fire_utc(expr, now_local, lookback_days=400):
    """For a fixed-time 5-field cron (single- or multi-fire), walk backward from
    now_local to find the most recent local datetime at/before now that the
    cron would have fired (respecting dom/month/dow), converted to naive UTC.
    Returns None if the cron isn't a fixed-time expression (e.g. '*/n', or
    one-time) or no match falls within lookback_days.

    Multi-fire support (2026-08-09, closes the same gap as cron_hms()): a task
    like "40 7,13,19 * * 1-5" fires three times on a matching day, not one --
    each day considered must check all of its fire times, latest first, so the
    single most recent one at/before now_local is returned rather than only
    ever checking one fixed hour/minute."""
    hms = cron_hms(expr)
    if not hms:
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    _mn, _hr, dom, mon, dow = parts
    offset_td = _local_utc_offset()
    cur_date = now_local.date()
    for day_offset in range(lookback_days):
        d = cur_date - datetime.timedelta(days=day_offset)
        dow_val = (d.weekday() + 1) % 7  # cron Sun=0..Sat=6; python Mon=0..Sun=6
        if _cron_fires_on(dom, mon, dow, d.day, d.month, dow_val):
            for hour, minute in sorted(hms, reverse=True):
                candidate_local = datetime.datetime(d.year, d.month, d.day, hour, minute)
                if candidate_local <= now_local:
                    return candidate_local - offset_td
    return None


def find_missed_cycles(tasks, now_local=None, grace_hours=MISSED_CYCLE_GRACE_HOURS):
    """Recurring, enabled tasks that HAVE fired before but whose lastRunAt is
    older than their most recent expected cron fire time by more than
    grace_hours. Silent-single-cycle-miss detector -- see module docstring
    above for the incident this closes (OI-031 / ora-master-workbook-ingest
    2026-07-20)."""
    now_local = now_local or datetime.datetime.now()
    out = []
    for t in tasks:
        if fire_at(t):
            continue  # one-time tasks are covered by expired_needs_attention
        if not t.get("enabled", True):
            continue  # a paused task isn't expected to fire
        last_run_utc = parse_last_run_utc(t.get("lastRunAt"))
        if last_run_utc is None:
            continue  # never-ran is never_ran/never_ran_overdue's job, not this one
        expected_utc = most_recent_expected_fire_utc(t.get("cronExpression"), now_local)
        if expected_utc is None:
            continue  # unparseable/non-fixed cadence -- don't guess
        gap = expected_utc - last_run_utc
        if gap > datetime.timedelta(hours=grace_hours):
            out.append({
                "id": t.get("id"), "fleet": t.get("_fleet"),
                "cron": t.get("cronExpression"),
                "expected_fire_utc": expected_utc.isoformat() + "Z",
                "last_run_utc": last_run_utc.isoformat() + "Z",
                "gap_hours": round(gap.total_seconds() / 3600.0, 1),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.registry:
        regs = [("forced", args.registry)]
    else:
        regs = discover_registries()
    regs = [(lbl, p) for lbl, p in regs if p and os.path.isfile(p)]
    if not regs:
        sys.stderr.write("[ACTION] fleet-status: no live scheduled-task registry found. "
                         "Fleet health is UNKNOWN. Check the claude-code-sessions and "
                         "local-agent-mode-sessions trees.\n")
        sys.exit(3)

    tasks, skips = [], {}
    for lbl, p in regs:
        try:
            t, s = load(p)
        except Exception as e:
            sys.stderr.write("[ACTION] fleet-status: registry %s unreadable: %s\n" % (p, e))
            continue
        for x in t:
            x["_fleet"] = lbl
        tasks += t
        skips.update(s or {})
    if not tasks:
        sys.stderr.write("[ACTION] fleet-status: all discovered registries unreadable/empty.\n")
        sys.exit(3)

    now_ms = datetime.datetime.now().timestamp() * 1000
    enabled = [t for t in tasks if t.get("enabled", True)]
    disabled = [t for t in tasks if not t.get("enabled", True)]
    never_ran = [t for t in tasks if not t.get("lastRunAt")]
    onetime = [t for t in tasks if fire_at(t)]
    expired = [t for t in tasks if fire_at(t) and fire_at(t) < now_ms]

    # RECALIBRATED VERDICT INPUTS (2026-07-14) -- see cadence_buffer_days() docstring.
    # never-ran is only overdue for a RECURRING task (no fireAt -- one-time tasks are
    # handled by expired_needs_attention instead) whose age exceeds its cadence buffer.
    never_ran_overdue = []
    for t in never_ran:
        if fire_at(t):
            continue  # one-time -- not this check's business
        created = t.get("createdAt")
        if not isinstance(created, (int, float)):
            continue  # can't determine age -- don't flag on missing data
        buf = cadence_buffer_days(t.get("cronExpression"))
        if buf is None:
            continue  # can't classify cadence -- don't guess
        if (now_ms - created) / 86400000.0 > buf:
            never_ran_overdue.append(t)

    # expired one-time is only VERDICT-worthy if it never fired (missed) or is still
    # enabled past its fireAt (didn't auto-disable) -- a normal successful one-time
    # completion (lastRunAt set, enabled false) is success, not a fault.
    expired_needs_attention = [
        t for t in expired if not t.get("lastRunAt") or t.get("enabled", True)
    ]

    # skip attribution -- ALL-TIME (unchanged, still shown as context) ...
    skip_counts = {k: len(v) for k, v in skips.items()} if isinstance(skips, dict) else {}
    total_skip_events = sum(skip_counts.values())
    # ... and RECENT (last 24h), which is what actually drives the verdict. recordedSkips
    # is a permanent historical log (grows forever, never reset), so counting all-time
    # events meant one old burst kept the verdict at ATTENTION indefinitely.
    SKIP_WINDOW_MS = 24 * 3600 * 1000
    recent_skip_counts = {}
    for tid, events in (skips.items() if isinstance(skips, dict) else []):
        if not isinstance(events, list):
            continue
        n = sum(1 for e in events if isinstance(e, dict)
                and isinstance(e.get("at"), (int, float))
                and 0 <= (now_ms - e["at"]) <= SKIP_WINDOW_MS)
        if n:
            recent_skip_counts[tid] = n
    recent_skip_total = sum(recent_skip_counts.values())

    # collisions: tasks sharing the same fixed (hour, minute) AND at least one
    # actual calendar day (cron_hm() alone ignores dom/month/dow -- e.g. Mon 13:30
    # vs Wed 13:30 used to false-positive as a collision; see crons_share_a_day()).
    hm = {}
    for t in tasks:
        # cron_hms(), not cron_hm(): a multi-fire task (e.g. "40 7,13,19 * * 1-5")
        # must be grouped into EVERY fire-time bucket it occupies, or it collides
        # invisibly with a task sharing just one of those times (2026-08-09 fix).
        for key in (cron_hms(t.get("cronExpression")) or []):
            hm.setdefault(key, []).append((t.get("id", "?"), t.get("cronExpression")))
    collisions = {}
    for k, group in hm.items():
        if len(group) < 2:
            continue
        real_ids = []
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if crons_share_a_day(group[i][1], group[j][1]):
                    for tid in (group[i][0], group[j][0]):
                        if tid not in real_ids:
                            real_ids.append(tid)
        if real_ids:
            collisions["%02d:%02d" % k] = real_ids

    # AM pileup 05:00-09:30. cron_hms(), not cron_hm(): a multi-fire task only
    # needs ONE of its fire times inside the window to count once (2026-08-09
    # fix -- the prior cron_hm()-only version excluded every multi-fire task
    # from this count entirely, undercounting it; see cron_hms() docstring).
    am_pileup = []
    for t in tasks:
        for key in (cron_hms(t.get("cronExpression")) or []):
            if 5 <= key[0] < 9 or (key[0] == 9 and key[1] <= 30):
                am_pileup.append((("%02d:%02d" % key), t.get("id")))

    missed_cycle = find_missed_cycles(tasks, now_local=datetime.datetime.fromtimestamp(now_ms / 1000))

    verdict_flags = []
    if never_ran_overdue:
        verdict_flags.append("%d never-ran past their expected cadence" % len(never_ran_overdue))
    if expired_needs_attention:
        verdict_flags.append("%d one-time task(s) missed their fire or stayed enabled past fireAt"
                              % len(expired_needs_attention))
    if missed_cycle:
        verdict_flags.append("%d recurring task(s) missed their most recent scheduled cycle"
                              % len(missed_cycle))
    if recent_skip_total > 0:
        verdict_flags.append("%d throttle skip(s) in the last 24h" % recent_skip_total)
    if collisions:
        verdict_flags.append("%d schedule collisions" % len(collisions))
    verdict = "OK" if not verdict_flags else "ATTENTION -- " + "; ".join(verdict_flags)

    if args.json:
        print(json.dumps({
            "registries": {lbl: p for lbl, p in regs},
            "per_fleet_enabled": {lbl: sum(1 for t in enabled if t.get("_fleet") == lbl)
                                  for lbl, _ in regs},
            "disabled_by_fleet": {lbl: sum(1 for t in disabled if t.get("_fleet") == lbl)
                                  for lbl, _ in regs},
            "tasks": [{"id": t.get("id"), "fleet": t.get("_fleet"),
                       "enabled": t.get("enabled", True),
                       "cron": t.get("cronExpression"),
                       "last_run_at": t.get("lastRunAt")} for t in tasks],
            "total": len(tasks), "enabled": len(enabled), "disabled": len(disabled),
            "never_ran": [t.get("id") for t in never_ran],
            "never_ran_overdue": [t.get("id") for t in never_ran_overdue],
            "onetime": [t.get("id") for t in onetime],
            "expired_onetime": [t.get("id") for t in expired],
            "expired_needs_attention": [t.get("id") for t in expired_needs_attention],
            "missed_cycle": missed_cycle,
            "missed_cycle_scope": ("point-in-time only -- lastRunAt vs. the most recent expected "
                                   "fire as of THIS run; a gap that already self-healed (task "
                                   "fired again) before this check is invisible here -- see OI-070 "
                                   "and the scheduler's own run log for a historical census"),
            "total_skip_events": total_skip_events,
            "tasks_with_skips": skip_counts,
            "recent_skip_events_24h": recent_skip_total,
            "recent_tasks_with_skips": recent_skip_counts,
            "collisions": collisions,
            "am_pileup_count": len(am_pileup),
            "verdict": verdict,
        }, indent=2))
        sys.exit(0)

    print("ORA FLEET STATUS  (DUAL-FLEET: cc = claude-code-sessions/MCP · lams = local-agent-mode-sessions/Cowork)")
    for lbl, p in regs:
        print("registry[%s]: %s" % (lbl, p))
    print("=" * 84)
    if not args.summary:
        print("%-42s %-5s %-16s %-4s %-5s %s" % ("TASK", "FLEET", "CRON", "EN", "SKIP", "LAST RUN"))
        print("-" * 84)
        for t in sorted(tasks, key=lambda x: (x.get("_fleet", ""), x.get("id", ""))):
            tid = (t.get("id") or "?")[:42]
            fa = fire_at(t)
            if fa:
                d8 = datetime.datetime.fromtimestamp(fa / 1000).strftime("%Y-%m-%d")
                cron = ("EXPIRED@" if fa < now_ms else "@") + d8
            else:
                cron = str(t.get("cronExpression"))[:16]
            en = "on" if t.get("enabled", True) else "OFF"
            sk = skip_counts.get(t.get("id"), 0)
            last = (t.get("lastRunAt") or "NEVER")[:19]
            print("%-42s %-5s %-16s %-4s %-5s %s" % (tid, t.get("_fleet", "?"), cron, en, sk, last))
        print("-" * 84)

    print("\nHEALTH SUMMARY")
    per_fleet = {lbl: sum(1 for t in enabled if t.get("_fleet") == lbl) for lbl, _ in regs}
    print("  total tasks ........ %d   (enabled %d / disabled %d)  per-fleet enabled: %s"
          % (len(tasks), len(enabled), len(disabled),
             ", ".join("%s=%d" % kv for kv in per_fleet.items())))
    print("  never-ran .......... %d   %s" % (len(never_ran), ", ".join(sorted(t.get("id") for t in never_ran)) or "-"))
    print("      of which overdue  %d   %s" % (len(never_ran_overdue),
          ", ".join(sorted(t.get("id") for t in never_ran_overdue)) or "- (not yet due, by cadence)"))
    print("  one-time fireAt .... %d   %s" % (len(onetime), ", ".join(sorted(t.get("id") for t in onetime)) or "-"))
    print("  EXPIRED one-time ... %d   %s" % (len(expired), ", ".join(sorted(t.get("id") for t in expired)) or "-"))
    print("      of which missed/stuck %d   %s" % (len(expired_needs_attention),
          ", ".join(sorted(t.get("id") for t in expired_needs_attention)) or "- (normal completions)"))
    print("  missed single cycle (currently open) %d   %s" % (len(missed_cycle),
          ", ".join("%s(%.1fh)" % (m["id"], m["gap_hours"]) for m in
                    sorted(missed_cycle, key=lambda m: m["id"])) or "-"))
    print("      NOTE: point-in-time only -- a gap that already self-healed (task fired again "
          "since) is invisible here; see OI-070 and the scheduler's own run log for history.")
    print("  throttle skips ..... %d events across %d tasks (all-time)" % (total_skip_events, len(skip_counts)))
    if skip_counts:
        top = sorted(skip_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print("                       top: %s" % ", ".join("%s=%d" % (k, v) for k, v in top))
    print("      of which last 24h %d   %s" % (recent_skip_total,
          ", ".join("%s=%d" % kv for kv in sorted(recent_skip_counts.items())) or "-"))
    print("  same-time collisions %d   %s" % (len(collisions),
          "; ".join("%s:{%s}" % (k, ",".join(v)) for k, v in sorted(collisions.items())) or "-"))
    print("  AM pileup (05-0930). %d tasks" % len(am_pileup))

    # health verdict (non-fatal; reporting tool). Recalibrated 2026-07-14: the prior
    # verdict flagged ANY never-ran/expired/all-time-skip count, which a mixed-cadence
    # fleet can never clear (a quarterly task is "never-ran" for up to 3 months by
    # design). Now only flags the subsets above that represent an actual anomaly --
    # see cadence_buffer_days() and test-fleet-status.py.
    print("\n  VERDICT: %s" % verdict)
    sys.exit(0)


if __name__ == "__main__":
    main()

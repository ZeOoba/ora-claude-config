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
import os, sys, json, glob, argparse, datetime, re

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


def membership_log_path():
    """Path to registry-membership.log, preferring a checkout-local copy and
    falling back to the canonical live one.

    `_state/` is MACHINE state, not repo content, so it does not exist in a
    worktree -- and this script is routinely run from one. Resolving only
    relative to __file__ silently yielded {} there, which looks identical to
    "no registrations recorded" and would quietly drop the annotation exactly
    where a reviewer is most likely to be reading. Same reasoning as
    discover_registries(), which reads the live AppData stores regardless of
    which checkout is executing."""
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "_state", "registry-membership.log")
    if os.path.exists(local):
        return local
    return os.path.join(os.path.expanduser("~"), ".claude", "maintenance",
                        "_state", "registry-membership.log")
# NOT anchored to end-of-line: the log writes `... adds={...} missing_stores=-`,
# so an `$` anchor here matched nothing and registration_dates() silently
# returned {} -- indistinguishable from "no registrations recorded".
_ADDS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})T\S*\s.*?adds=\{(.+?)\}")
_ADDS_FLEET_RE = re.compile(r"'(cc|lams)'\s*:\s*\[(.*?)\]")
_ADD_ID_RE = re.compile(r"'([a-z0-9][a-z0-9-]*)'")


def registration_dates(path=None):
    """{task_id: 'YYYY-MM-DD'} of when each task FIRST appeared in a registry,
    read from registry-membership.log's `adds={...}` entries.

    WHY THIS EXISTS: a bare `NEVER` in the LAST RUN column reads as "dead", and
    on 2026-08-16 that inference nearly retired the working half of a dual-fleet
    pair -- `ora-passed-deal-tracker`'s CC copy had never fired because it had
    been registered THAT MORNING on a monthly cron, not because it was broken.
    Age-since-registration is the one number that separates "new" from "dead",
    and nothing surfaced it.

    Returns {} on any I/O or parse trouble: this is display sugar, and a probe
    that dies because an advisory log is missing would be a worse defect than
    the ambiguity it fixes."""
    out = {}
    try:
        with open(path or membership_log_path(), encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return out
    for line in lines:
        m = _ADDS_RE.match(line.strip())
        if not m:
            continue
        day = m.group(1)
        # KEYED BY (fleet, id), NOT id alone. The same taskId legitimately exists
        # on BOTH fleets, and collapsing them reports the wrong birthday for the
        # exact case this feature exists for: ora-passed-deal-tracker was first
        # added to LAMS on 2026-07-08, then registered on CC on 2026-08-16 as
        # part of the T3-12 migration. A single key answered "2026-07-08" for the
        # CC copy -- i.e. "6 weeks old and never fired", which is precisely the
        # false 'dead' reading that nearly got the working copy retired.
        for fm in _ADDS_FLEET_RE.finditer(m.group(2)):
            fleet = fm.group(1)
            for tid in _ADD_ID_RE.findall(fm.group(2)):
                # FIRST add per fleet wins -- a no-op re-register is not a birth.
                out.setdefault("%s:%s" % (fleet, tid), day)
    return out


def never_label(task_id, fleet, reg_dates, now_local):
    """'NEVER' annotated with how long ago the task was registered, when known.

    An unknown registration date yields a bare 'NEVER' rather than a guess --
    a fabricated age here would be worse than the missing one, since the whole
    point is to support a keep/retire decision."""
    day = (reg_dates or {}).get("%s:%s" % (fleet, task_id))
    if not day:
        return "NEVER"
    try:
        reg = datetime.datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return "NEVER"
    age = (now_local.date() - reg).days
    if age <= 0:
        return "NEVER (registered today)"
    return "NEVER (registered %dd ago, %s)" % (age, day)


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
MISSED_CYCLE_GRACE_HOURS = 24  # floor: fleet only fires while the Desktop
                               # app is open, so some lateness is normal and
                               # expected, not a fault.
MISSED_CYCLE_INTERVAL_MULTIPLE = 1.5  # CRON-AWARE GUARD (2026-08-11, closes the
                               # 2026-08-10 [CORRECTION]: the raw gap jumps to
                               # ~1x a task's own cadence the instant its cron
                               # time passes unfired -- a healthy weekly task
                               # mid-catch-up reads gap~=168h against a flat
                               # 24h wall and is flagged every week. Escalating
                               # only past 1.5x a task's OWN interval lets one
                               # un-dispatched slot pass silently (normal
                               # catch-up) while >=2 missed slots (>=2x
                               # interval, always > 1.5x) still escalates
                               # unconditionally -- the ora-cc-schematic-refresh
                               # founding case (2x/week, 13 days =~ 3.7
                               # intervals) is the regression this must keep
                               # catching. The 24h floor still applies for
                               # short/frequent cadences so a multi-fire cron
                               # with a small own-interval isn't over-sensitized.

def _local_utc_offset():
    """Best-effort fixed UTC offset for 'now' on this machine (cron is evaluated
    in local time per doctrine; lastRunAt is stored as UTC ISO8601 'Z')."""
    return datetime.datetime.now().astimezone().utcoffset() or datetime.timedelta(0)


def _fmt_offset(td):
    mins = int(abs(td).total_seconds() // 60)
    return "%s%02d:%02d" % ("+" if td >= datetime.timedelta(0) else "-", mins // 60, mins % 60)


def host_clock_status(now_local=None):
    """Host clock vs Eastern AT THIS INSTANT (added 2026-09-03; DST-aware 2026-09-06).

    Cron is evaluated in LOCAL time, so a host whose clock is not on Eastern fires every
    slot shifted in ET terms. The comparison is against America/New_York's offset at the
    same instant (zoneinfo), so -05:00 in July or -04:00 in January is correctly SHIFTED --
    a flat {-04:00, -05:00} allow-set would read both as Eastern. Without tzdata the check
    degrades to that allow-set and says so. Flag only -- never retime
    (memory: reference_machine_clock_utc_plus_2_fleet_shift_2026-09-02)."""
    now_local = now_local or datetime.datetime.now().astimezone()
    host_off = _fmt_offset(now_local.utcoffset() or datetime.timedelta(0))
    try:
        from zoneinfo import ZoneInfo
        eastern = _fmt_offset(now_local.astimezone(ZoneInfo("America/New_York")).utcoffset())
        shifted = host_off != eastern
    except Exception:
        eastern = "-05:00/-04:00 (tzdata unavailable -- season not resolved)"
        shifted = host_off not in ("-04:00", "-05:00")
    return {"host_clock": "%s (UTC%s)" % (now_local.tzname() or "?", host_off),
            "host_clock_offset": host_off, "eastern_offset_now": eastern,
            "host_clock_shifted": shifted}


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


def _local_to_utc(naive_local):
    """Interpret a naive local datetime in the MACHINE's zone using the DST rule
    in force on THAT date (not today's fixed offset) and return naive UTC.

    Cron is evaluated in machine-local time per doctrine -- the Desktop
    scheduler uses whatever zone Windows is on (2026-09-02: Romance Standard
    Time, not Eastern), so this deliberately does NOT hard-code
    America/New_York. Before 2026-09-03 every candidate was shifted by the
    CURRENT offset, so a slot on the far side of a DST transition landed an
    hour off and could move an overdue verdict across the 24h grace boundary
    (PR #157 review). A nonexistent/ambiguous local time (the spring-forward
    gap, the fall-back fold) resolves however the C runtime's mktime resolves
    it -- one hour of slack at most, twice a year, on a 24h grace window."""
    return naive_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _utc_to_local(naive_utc):
    """Inverse of _local_to_utc: naive UTC -> naive machine-local, per-date DST."""
    return (naive_utc.replace(tzinfo=datetime.timezone.utc)
            .astimezone().replace(tzinfo=None))


def first_expected_fire_after_utc(expr, after_utc, lookahead_days=400):
    """The EARLIEST local fire strictly after `after_utc` (naive UTC), as naive
    UTC -- the mirror image of most_recent_expected_fire_utc(). Returns None
    for a cron the walker can't evaluate (same contract: caller falls back).

    Why a separate forward walker (PR #157 review, finding 1): the never-ran
    first-slot rule needs "did the task's FIRST post-registration slot go by
    unfired?", and the most-recent slot is the wrong witness for that. A
    multi-fire or daily cron always has a slot inside the last 24h, so
    comparing the most recent one against the grace window never flags --
    a daily 0 7,13,19 task registered yesterday 06:00 read as not overdue at
    20:00 today despite a 37h-old first miss."""
    hms = cron_hms(expr)
    if not hms:
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    _mn, _hr, dom, mon, dow = parts
    after_local = _utc_to_local(after_utc)
    d0 = after_local.date()
    for day_offset in range(lookahead_days):
        d = d0 + datetime.timedelta(days=day_offset)
        dow_val = (d.weekday() + 1) % 7
        try:
            fires = _cron_fires_on(dom, mon, dow, d.day, d.month, dow_val)
        except ValueError:
            return None
        if fires:
            for hour, minute in sorted(hms):
                candidate_local = datetime.datetime(d.year, d.month, d.day, hour, minute)
                if candidate_local > after_local:
                    return _local_to_utc(candidate_local)
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


def _own_interval_hours(expr, expected_utc, hops=8):
    """This task's own TYPICAL cadence in hours: the SMALLEST gap among the
    last `hops` consecutive fire-to-fire steps ending at expected_utc.

    Walking back just ONE hop is not safe: for a weekday-only or multi-fire
    cron, the single most-recent hop varies with WHEN you sample. Sampled
    right at the day's/week's first fire, that one hop is the weekend/day-
    boundary outlier (e.g. Fri 19:40 -> Mon 07:40 = 60h for a 3x/weekday
    cron, or Fri -> Mon = 72h for a weekday-only daily cron) rather than the
    task's true cadence (6h / 24h) -- which inflates the missed-cycle
    threshold enough to hide several real consecutive misses (found via
    adversarial review 2026-08-11: a 3x/weekday cron missing 5 straight
    fires, gap ~89h, went unflagged because the single-hop interval was 60h
    -> threshold 90h). Taking the MIN across several hops finds the task's
    true tightest cadence regardless of where in its cycle `now_local` lands
    -- for a perfectly uniform cadence (daily, weekly) every hop is equal so
    this returns the same value the single-hop version did.

    Returns None if fewer than 2 fires can be located (falls back to the
    flat grace floor)."""
    offset_td = _local_utc_offset()
    fires_utc = [expected_utc]
    cursor_local = expected_utc + offset_td
    for _ in range(hops):
        cursor_local = cursor_local - datetime.timedelta(minutes=1)
        prior_utc = most_recent_expected_fire_utc(expr, cursor_local)
        if prior_utc is None:
            break
        fires_utc.append(prior_utc)
        cursor_local = prior_utc + offset_td
    if len(fires_utc) < 2:
        return None
    gaps = [(fires_utc[i] - fires_utc[i + 1]).total_seconds() / 3600.0
            for i in range(len(fires_utc) - 1)]
    return min(gaps)


def _load_pause_windows_module():
    try:
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared", "pause_windows.py")
        spec = importlib.util.spec_from_file_location("pause_windows", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def find_missed_cycles(tasks, now_local=None, grace_hours=MISSED_CYCLE_GRACE_HOURS,
                        interval_multiple=MISSED_CYCLE_INTERVAL_MULTIPLE,
                        pause_store=None, explained_out=None):
    """Recurring, enabled tasks that HAVE fired before but whose lastRunAt is
    older than their most recent expected cron fire time by more than the
    CRON-AWARE GUARD threshold: max(grace_hours, interval_multiple x the
    task's own cadence). Silent-single-cycle-miss detector -- see module
    docstring above for the incident this closes (OI-031 /
    ora-master-workbook-ingest 2026-07-20), and MISSED_CYCLE_INTERVAL_MULTIPLE
    above for the 2026-08-10 false-positive incident that made the threshold
    cadence-aware rather than a flat wall.

    PAUSE-AWARE (2026-09-12): when `pause_store` is given, hours the task was held
    by a RECORDED bounded pause (_shared/pause_windows.py) are subtracted from the
    gap before it is judged. An entry whose remaining gap is within threshold is
    appended to `explained_out` (if a list is passed) instead of the returned list --
    reported, never silently dropped. Flagged entries carry pause_hours too. An
    unreadable store means no subtraction: it can cost a false alarm, never hide one.
    Live incident: the first ora-health-guard run after the 2026-09-07 -> 09-11 CC
    pause listed 11 'missed' tasks whose missed slots all fell inside that pause."""
    now_local = now_local or datetime.datetime.now()
    pw = None
    if pause_store:
        pw = _load_pause_windows_module()
        if pw is not None and pw.load_windows(pause_store, with_error=True)[1]:
            pw = None
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
        interval_hours = _own_interval_hours(t.get("cronExpression"), expected_utc)
        threshold_hours = grace_hours
        if interval_hours is not None:
            threshold_hours = max(grace_hours, interval_multiple * interval_hours)
        if gap > datetime.timedelta(hours=threshold_hours):
            entry = {
                "id": t.get("id"), "fleet": t.get("_fleet"),
                "cron": t.get("cronExpression"),
                "expected_fire_utc": expected_utc.isoformat() + "Z",
                "last_run_utc": last_run_utc.isoformat() + "Z",
                "gap_hours": round(gap.total_seconds() / 3600.0, 1),
                "own_interval_hours": (round(interval_hours, 1)
                                       if interval_hours is not None else None),
                "threshold_hours": round(threshold_hours, 1),
            }
            if pw is not None:
                pause_h = pw.overlap_hours(t.get("_fleet"), t.get("id"), last_run_utc,
                                           expected_utc, path=pause_store)
                entry["pause_hours"] = round(pause_h, 1)
                entry["effective_gap_hours"] = round(entry["gap_hours"] - pause_h, 1)
                if pause_h > 0 and entry["effective_gap_hours"] <= threshold_hours:
                    if explained_out is not None:
                        explained_out.append(entry)
                    continue
            out.append(entry)
    return out


def find_cross_fleet_duplicates(tasks):
    """Tasks registered under the SAME id on more than one fleet.

    This is a DIFFERENT condition from a same-time collision and deliberately has
    its own detector, because the two have different -- and differently dangerous
    -- remedies. A collision is fixed by retiming one task: cheap and reversible.
    A cross-fleet duplicate is fixed by retiring one COPY, which is hazardous:
    the Cowork Scheduled-sidebar delete is folder-destructive, the two fleets take
    opposite archive/delete orderings, and a same-id pair can share a SKILL.md
    path, so deleting one can silently destroy the other.

    Detected independently of cron, on purpose: two copies of one task with
    DIFFERENT schedules are still a duplicate, and the old time-bucketed logic
    could not see them at all.

    Root incident (Automation Audit R13-3, 2026-08-16): ora-passed-deal-tracker
    was registered on both fleets mid-migration. The old collision loop deduped
    its member list by task id and dropped the fleet, so it surfaced as a
    same-time "collision" containing a single name -- which reads as nonsense and
    led a reader to recommend retiring the wrong copy.

    Also catches a duplicate REGISTRATION on a single fleet (same id twice in one
    registry -- a documented failure mode, 2026-07-08). That case must not fall
    through: find_collisions() now skips same-id pairs, so if this detector
    required two DISTINCT fleets, a single-fleet duplicate would be invisible to
    both. Such entries are reported with cross_fleet=False, since the remedy is
    different again (drop the redundant registration, no cross-fleet hazard).

    Returns {task_id: {"fleets": [...], "crons": [...], "enabled": [...],
                       "cross_fleet": bool}}.
    """
    seen = {}
    for t in tasks:
        tid = t.get("id")
        if not tid:
            continue
        seen.setdefault(tid, []).append(t)
    dups = {}
    for tid, group in seen.items():
        if len(group) < 2:
            continue
        fleets = []
        for t in group:
            f = t.get("_fleet")
            if f not in fleets:
                fleets.append(f)
        dups[tid] = {
            "fleets": fleets,
            "crons": [t.get("cronExpression") for t in group],
            "enabled": [bool(t.get("enabled")) for t in group],
            "cross_fleet": len(fleets) > 1,
        }
    return dups


def find_collisions(tasks):
    """Genuine same-time collisions: DIFFERENT tasks sharing a fire time and a day.

    Two guards apply, and both exist because of real false positives:
      * crons_share_a_day() -- Mon 13:30 vs Wed 13:30 never actually coincide.
      * same-id pairs are excluded -- those are cross-fleet duplicates, reported
        by find_cross_fleet_duplicates() instead (R13-3, 2026-08-16).

    A duplicate does NOT mask a genuine collision at the same time: if a third,
    distinct task also fires then, that pairing is still reported here.

    CAVEAT -- this compares cron EXPRESSIONS, not actual dispatch times. The
    scheduler applies a small deterministic per-task delay to recurring fires for
    load balancing (observed 2026-08-16: `0 9 * * *` dispatches ~09:07, `40 9 * * *`
    ~09:47). That delay is not present in the registry this script reads, so it
    cannot be modelled here. A reported collision therefore means "same scheduled
    minute", which is the right thing to keep clean, but is not proof two tasks
    truly execute simultaneously.
    """
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
                if group[i][0] == group[j][0]:
                    continue  # same task on two fleets -- a duplicate, not a collision
                if crons_share_a_day(group[i][1], group[j][1]):
                    for tid in (group[i][0], group[j][0]):
                        if tid not in real_ids:
                            real_ids.append(tid)
        if real_ids:
            collisions["%02d:%02d" % k] = real_ids
    return collisions


# STALENESS WARNING (added 2026-08-28, closes a false-alarm class): this report is a
# point-in-time snapshot. Root incident: a fleet-status/setup-self-audit advisory
# forwarded to Gabriel correctly showed `ora-754-flaute-escalation-check` as expired,
# not-yet-fired, still enabled -- true AT GENERATION TIME -- but the task was mid a
# ~1h41m AM-catch-up-burst throttle delay and had already fired and auto-disabled by
# the time the advisory was read and acted on. The snapshot wasn't wrong; it was stale
# by minutes, and nothing in the report itself said so. This note is baked into BOTH
# output modes (not left to a downstream skill's discipline, e.g. fleet-advisory-
# remediation's live-reverify step) because Gabriel routinely pastes/forwards this
# output as-is, and a reader several minutes removed from generation has no way to
# know the snapshot may already be dead -- especially during a catch-up burst, when
# enabled/lastRunAt can flip within minutes.
STALENESS_NOTE = (
    "SNAPSHOT, NOT LIVE STATE: task enabled/lastRunAt can change within minutes, "
    "especially during an AM catch-up burst (throttle-delayed fires + auto-disable "
    "on completion). Re-run this script (or list_scheduled_tasks) immediately before "
    "acting on any flagged item -- do not act on a forwarded/pasted copy of this output."
)


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
    #
    # FIRST-SLOT RULE (2026-09-02, closes Automation Audit R21-2b). The cadence
    # buffer alone measures age-since-createdAt, so a day-of-month cron gets a
    # flat 40-day grace regardless of whether a real slot has already come and
    # gone. That hid a money-moving miss: ora-pm-monthly-billing (10 11 1 * *,
    # registered 2026-08-21) missed its first-ever fire on 2026-09-01 inside a
    # host outage and read "0 overdue" -- and would have kept reading that
    # until ~09-30 -- while find_missed_cycles() explicitly excludes never-ran
    # tasks. A never-ran task whose FIRST post-registration slot has elapsed by
    # more than MISSED_CYCLE_GRACE_HOURS is overdue now, whatever its cadence;
    # the buffer remains the fallback for crons most_recent_expected_fire_utc()
    # can't evaluate. A slot that predates createdAt never counts (a task
    # registered on the 16th for the 15th is simply waiting for next month).
    never_ran_overdue = []
    never_ran_overdue_reason = []
    now_utc_naive = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    grace_td = datetime.timedelta(hours=MISSED_CYCLE_GRACE_HOURS)
    for t in never_ran:
        if fire_at(t):
            continue  # one-time -- not this check's business
        created = t.get("createdAt")
        if not isinstance(created, (int, float)):
            continue  # can't determine age -- don't flag on missing data
        created_utc = datetime.datetime.fromtimestamp(
            created / 1000.0, datetime.timezone.utc).replace(tzinfo=None)
        first_utc = first_expected_fire_after_utc(t.get("cronExpression"), created_utc)
        if first_utc is not None:
            if first_utc <= now_utc_naive and (now_utc_naive - first_utc) > grace_td:
                never_ran_overdue.append(t)
                never_ran_overdue_reason.append({
                    "id": t.get("id"), "fleet": t.get("_fleet"),
                    "reason": "first slot %sZ elapsed >%dh unfired"
                              % (first_utc.strftime("%Y-%m-%dT%H:%M"), MISSED_CYCLE_GRACE_HOURS)})
            # else: first post-registration slot is still ahead, or inside
            # the grace window -- waiting, not overdue. Do NOT fall through to
            # the cadence buffer: a slot walker that CAN evaluate the cron is
            # a stronger witness than an age heuristic.
            continue
        buf = cadence_buffer_days(t.get("cronExpression"))
        if buf is None:
            continue  # can't classify cadence -- don't guess
        if (now_ms - created) / 86400000.0 > buf:
            never_ran_overdue.append(t)
            never_ran_overdue_reason.append({
                "id": t.get("id"), "fleet": t.get("_fleet"),
                "reason": "age exceeds %dd cadence buffer (cron not evaluable by the slot walker)" % buf})

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

    # Two SEPARATE conditions, deliberately not conflated (R13-3, 2026-08-16):
    # genuine same-time collisions between DIFFERENT tasks, and the same task id
    # registered on both fleets. See each function's docstring for why the remedies
    # differ and why merging them once produced a "collision" containing one name.
    collisions = find_collisions(tasks)
    cross_fleet_dups = find_cross_fleet_duplicates(tasks)

    # AM pileup 05:00-09:30. cron_hms(), not cron_hm(): a multi-fire task only
    # needs ONE of its fire times inside the window to count once (2026-08-09
    # fix -- the prior cron_hm()-only version excluded every multi-fire task
    # from this count entirely, undercounting it; see cron_hms() docstring).
    am_pileup = []
    for t in tasks:
        for key in (cron_hms(t.get("cronExpression")) or []):
            if 5 <= key[0] < 9 or (key[0] == 9 and key[1] <= 30):
                am_pileup.append((("%02d:%02d" % key), t.get("id")))

    # Pause-aware (2026-09-12): subtract recorded bounded-pause hours; explained entries
    # are REPORTED on their own line, never dropped. A pause record that cannot be read
    # is surfaced as pause_record_status so a silent fallback can't masquerade as clean.
    pause_explained = []
    _pw = _load_pause_windows_module()
    if _pw is None:
        pause_record_status = "UNAVAILABLE -- _shared/pause_windows.py failed to load; no pause subtraction"
        _pause_store = None
    else:
        _wins, _perr = _pw.load_windows(_pw.DEFAULT_STORE, with_error=True)
        pause_record_status = (("UNREADABLE -- %s; no pause subtraction" % _perr) if _perr
                               else "%d recorded window(s)" % len(_wins))
        _pause_store = None if _perr else _pw.DEFAULT_STORE
    missed_cycle = find_missed_cycles(tasks, now_local=datetime.datetime.fromtimestamp(now_ms / 1000),
                                      pause_store=_pause_store, explained_out=pause_explained)

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
    if cross_fleet_dups:
        verdict_flags.append("%d task(s) registered on BOTH fleets" % len(cross_fleet_dups))
    verdict = "OK" if not verdict_flags else "ATTENTION -- " + "; ".join(verdict_flags)

    generated_at_iso = datetime.datetime.now().isoformat(timespec="seconds")

    # Host clock (added 2026-09-03): the 2026-09-02 shift to UTC+2 went unnoticed by every
    # scheduled pass because nothing printed it. See host_clock_status().
    _hc = host_clock_status()
    host_clock, host_clock_shifted, eastern_offset_now = _hc["host_clock"], _hc["host_clock_shifted"], _hc["eastern_offset_now"]

    if args.json:
        print(json.dumps({
            "generated_at": generated_at_iso,
            "staleness_note": STALENESS_NOTE,
            "host_clock": host_clock,
            "eastern_offset_now": eastern_offset_now,
            "host_clock_shifted_from_eastern": host_clock_shifted,
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
            "never_ran_overdue_reason": never_ran_overdue_reason,
            "onetime": [t.get("id") for t in onetime],
            "expired_onetime": [t.get("id") for t in expired],
            "expired_needs_attention": [t.get("id") for t in expired_needs_attention],
            "missed_cycle": missed_cycle,
            "missed_cycle_pause_explained": pause_explained,
            "pause_record_status": pause_record_status,
            "missed_cycle_scope": ("point-in-time only -- lastRunAt vs. the most recent expected "
                                   "fire as of THIS run; a gap that already self-healed (task "
                                   "fired again) before this check is invisible here -- see OI-070 "
                                   "and the scheduler's own run log for a historical census"),
            "total_skip_events": total_skip_events,
            "tasks_with_skips": skip_counts,
            "recent_skip_events_24h": recent_skip_total,
            "recent_tasks_with_skips": recent_skip_counts,
            "collisions": collisions,
            "cross_fleet_duplicates": cross_fleet_dups,
            "am_pileup_count": len(am_pileup),
            "verdict": verdict,
        }, indent=2))
        sys.exit(0)

    print("ORA FLEET STATUS  (DUAL-FLEET: cc = claude-code-sessions/MCP · lams = local-agent-mode-sessions/Cowork)")
    print("generated_at: %s" % generated_at_iso)
    print("host_clock: %s; Eastern now %s%s" % (host_clock, eastern_offset_now,
          "  !! NOT Eastern -- every cron slot below fires shifted in ET terms; flag, never retime"
          if host_clock_shifted else ""))
    for lbl, p in regs:
        print("registry[%s]: %s" % (lbl, p))
    print("=" * 84)
    print("!! %s" % STALENESS_NOTE)
    print("=" * 84)
    reg_dates = registration_dates()
    now_local = datetime.datetime.now()
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
            # Truncate the two cases SEPARATELY: widening one bound for the
            # annotation also widened it for real timestamps, which previously
            # displayed at 19 chars and would now print sub-second precision and
            # offset -- an unintended display change to every task that HAS run.
            _lr = t.get("lastRunAt")
            last = (_lr[:19] if _lr else
                    never_label(t.get("id"), t.get("_fleet"), reg_dates, now_local)[:44])
            print("%-42s %-5s %-16s %-4s %-5s %s" % (tid, t.get("_fleet", "?"), cron, en, sk, last))
        print("-" * 84)

    print("\nHEALTH SUMMARY")
    per_fleet = {lbl: sum(1 for t in enabled if t.get("_fleet") == lbl) for lbl, _ in regs}
    print("  total tasks ........ %d   (enabled %d / disabled %d)  per-fleet enabled: %s"
          % (len(tasks), len(enabled), len(disabled),
             ", ".join("%s=%d" % kv for kv in per_fleet.items())))
    print("  never-ran .......... %d   %s" % (len(never_ran), ", ".join(sorted(t.get("id") for t in never_ran)) or "-"))
    print("      of which overdue  %d   %s" % (len(never_ran_overdue),
          ", ".join("%s [%s] (%s)" % (r["id"], r["fleet"] or "?", r["reason"])
                    for r in sorted(never_ran_overdue_reason,
                                    key=lambda r: (r["fleet"] or "", r["id"] or "")))
          or "- (not yet due: no post-registration slot elapsed >%dh, none past cadence buffer)"
          % MISSED_CYCLE_GRACE_HOURS))
    print("  one-time fireAt .... %d   %s" % (len(onetime), ", ".join(sorted(t.get("id") for t in onetime)) or "-"))
    print("  EXPIRED one-time ... %d   %s" % (len(expired), ", ".join(sorted(t.get("id") for t in expired)) or "-"))
    print("      of which missed/stuck %d   %s" % (len(expired_needs_attention),
          ", ".join(sorted(t.get("id") for t in expired_needs_attention)) or "- (normal completions)"))
    print("  missed single cycle (currently open) %d   %s" % (len(missed_cycle),
          ", ".join("%s(%.1fh)" % (m["id"], m["gap_hours"]) for m in
                    sorted(missed_cycle, key=lambda m: m["id"])) or "-"))
    print("      NOTE: point-in-time only -- a gap that already self-healed (task fired again "
          "since) is invisible here; see OI-070 and the scheduler's own run log for history.")
    print("  pause-explained (NOT missed) %d   %s" % (len(pause_explained),
          ", ".join("%s(%.1fh, %.1fh paused)" % (m["id"], m["gap_hours"], m["pause_hours"]) for m in
                    sorted(pause_explained, key=lambda m: m["id"])) or "-"))
    print("      pause record: %s  (_state/fleet-pause-windows.json; advisory, never a FAIL)"
          % pause_record_status)
    print("  throttle skips ..... %d events across %d tasks (all-time)" % (total_skip_events, len(skip_counts)))
    if skip_counts:
        top = sorted(skip_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print("                       top: %s" % ", ".join("%s=%d" % (k, v) for k, v in top))
    print("      of which last 24h %d   %s" % (recent_skip_total,
          ", ".join("%s=%d" % kv for kv in sorted(recent_skip_counts.items())) or "-"))
    print("  same-time collisions %d   %s" % (len(collisions),
          "; ".join("%s:{%s}" % (k, ",".join(v)) for k, v in sorted(collisions.items())) or "-"))
    print("  duplicate registrations %d %s" % (len(cross_fleet_dups),
          "; ".join("%s{%s%s}" % (tid, "+".join(str(f) for f in d["fleets"]),
                                  "" if d["cross_fleet"] else " SAME-FLEET x%d" % len(d["crons"]))
                    for tid, d in sorted(cross_fleet_dups.items())) or "-"))
    if cross_fleet_dups:
        print("      NOTE: same task id on BOTH registries -- NOT a collision, and NOT safe to")
        print("      'clean up' casually: the sidebar delete is folder-destructive, the fleets take")
        print("      opposite archive/delete orderings, and a pair can share one SKILL.md path.")
        print("      Check each task's registry description for a deliberate migration first.")
    print("  AM pileup (05-0930). %d tasks" % len(am_pileup))

    # health verdict (non-fatal; reporting tool). Recalibrated 2026-07-14: the prior
    # verdict flagged ANY never-ran/expired/all-time-skip count, which a mixed-cadence
    # fleet can never clear (a quarterly task is "never-ran" for up to 3 months by
    # design). Now only flags the subsets above that represent an actual anomaly --
    # see cadence_buffer_days() and test-fleet-status.py.
    print("\n  VERDICT: %s" % verdict)
    if verdict != "OK":
        print("  !! %s snapshot at %s -- %s" % ("ATTENTION", generated_at_iso, STALENESS_NOTE))
    sys.exit(0)


if __name__ == "__main__":
    main()

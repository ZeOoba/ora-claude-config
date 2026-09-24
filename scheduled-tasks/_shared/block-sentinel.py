#!/usr/bin/env python3
"""block-sentinel.py -- per-block, per-ET-date entry guard for ORA scheduled tasks.

WHY THIS EXISTS
---------------
2026-08-09 (Sunday): the machine was offline overnight. ora-health-guard reported
waking 219 min late and the whole fleet fired in a catch-up burst. `ora-am-brief`
fired TWICE -- a run that published Notion page 3b76ecd8-9e59-8160-bb0f-c6b5c925a278
and sent "ORA Daily Brief - Sunday, August 9 2026" to ggoldberg cc egoldberg at
09:06 ET, then a second fire at 09:11 ET (registry lastRunAt 2026-08-09T13:11:04Z).
The second fire only avoided re-sending the email and clobbering the page because
the session read the artifact first and stood down BY HAND.

Root cause: Block B had no entry guard. Its only dedup was the daily-brief skill's
Patch 3 pre-create check, which (a) dedups the NOTION PAGE ONLY -- the Outlook COM
send is unconditional -- and (b) on "exactly 1 match" issues notion-update-page
replace_content, i.e. it OVERWRITES, because it assumes any match is its own retry
artifact rather than a completed prior run's output.

The catch-up burst itself is documented, intended fleet-wide behavior (both fleets
fire only while the Desktop app is open). The guard therefore belongs at each
task's own entry, NOT in the cron schedule.

SEMANTICS -- claim-then-complete, as step 0 of a block, before any generation work:
  * today's block COMPLETE          -> SKIP_ALREADY_COMPLETE (exit 10). Record it
                                       as a NORMAL skip in the run summary so
                                       ora-health-guard / automation-health-monitor
                                       do not read it as a miss.
  * IN_PROGRESS, claimedAt < TTL    -> STAND_DOWN_IN_PROGRESS (exit 11). Another
                                       fire is live.
  * IN_PROGRESS, claimedAt > TTL    -> crashed run; re-claim and PROCEED (exit 0).
  * no record                       -> claim and PROCEED (exit 0).

The TTL is load-bearing in BOTH directions. A COMPLETE-only sentinel does not stop
two OVERLAPPING fires (fire #2 arrives while fire #1 is still generating). An
IN_PROGRESS sentinel with no expiry permanently wedges the task after any crash.

FAIL-OPEN. Consistent with every other ORA guard: an unreadable/corrupt state file,
a lock we cannot take, or any unexpected internal error yields PROCEED with the
degradation surfaced in `stateFileError`. This guard must never become the reason
the morning brief stops going out.

WHERE THE STATE LIVES
---------------------
Default: <Claude_Workspace>\\_state\\<task>-block-completion.json

`Claude_Workspace\\_state\\` is the ONE location ora-am-brief's NON-MUTATION
GUARANTEE already permits it to write, so this mechanism stays inside that task's
existing envelope. Other tasks pass --state explicitly.

Because `_state` sits on OneDrive, the file can be lost or briefly unavailable to a
sync conflict. That is why email-sending blocks carry an INDEPENDENT second layer
(outlook-sent-probe.ps1, which searches Sent Items for today's subject immediately
before the COM send). Neither layer is sufficient alone.

USAGE
-----
  python block-sentinel.py claim    --task ora-am-brief --block blockB --run-id <id>
                                    [--ttl-min 30] [--state PATH] [--force] [--period day|week|month]
  python block-sentinel.py complete --task ora-am-brief --block blockB --run-id <id>
                                    [--notion-page-id ID] [--email-sent-at ISO] [--period day|week|month]
  python block-sentinel.py fail     --task ora-am-brief --block blockB --run-id <id>
                                    [--error "..."] [--period day|week|month]
  python block-sentinel.py status   --task ora-am-brief --block blockB   (read-only) [--period day|week|month]
  python block-sentinel.py slot     --times 09:35,12:35,15:35            (read-only) -> {"block": "slot-12", ...}
                                    For multi-fire-per-day tasks: resolves the current ET cron slot so
                                    no caller does timezone math in a shell (Git Bash ignores TZ here).

--period (added 2026-09-06, default "day"): which calendar bucket a block's
claim-then-complete record is keyed to. A DAILY task keyed to the ET date is
right for a task meant to fire once a day, but a WEEKLY or MONTHLY task keyed
the same way re-arms every day between fires -- a clock skew, a missed cron
window, or a manual catch-up re-run days later reads as "virgin date, PROCEED"
even though the task already ran this period. --period week keys to the ISO
week (`YYYY-Www`, US/Eastern); --period month keys to the calendar month
(`YYYY-MM`, US/Eastern). Same claim-then-complete semantics apply within
whichever bucket is selected; only the key format and retention window change
(see `prune()`). The caller must pass the SAME --period on claim/complete/fail
that it used to claim, or it addresses a different bucket than intended.

Exit codes:  0 PROCEED/ok  |  10 SKIP_ALREADY_COMPLETE  |  11 STAND_DOWN_IN_PROGRESS
             12 REFUSED (finalize without ownership; nothing written)
             any other (2 argparse, 9009/127 no interpreter) -> treat as PROCEED, fail-open,
             and surface verbatim in the run summary
             EXCEPTION: claim --slot-times / slot exit 2 with no `block` on bad times or a
             missing block. There is no block id to proceed under, so the caller must ALERT
             and stop, never guess one.
JSON is written to stdout in every case so the calling run can log deterministically.

Stdlib only. ASCII-only. Windows (`python`).
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

DEFAULT_TTL_MIN = 30
RETAIN_DAYS = 14
RETAIN_SPAN = {
    "day": timedelta(days=RETAIN_DAYS),
    "week": timedelta(weeks=8),
    "month": timedelta(days=93),   # ~3 months; exact day count doesn't matter, only the order of magnitude
}
LOCK_TIMEOUT_S = 10.0

EXIT_OK = 0
EXIT_ALREADY_COMPLETE = 10
EXIT_STAND_DOWN = 11
EXIT_REFUSED = 12          # finalize refused: not the owner / never claimed. Nothing written.


# ------------------------------------------------------------------ time

def _utc_now():
    """Wall clock, overridable for tests via ORA_SENTINEL_NOW (ISO-8601 UTC).

    Test-only injection point. Without it the ET-vs-UTC contract can only be
    exercised during the few hours a day the two dates actually differ, which
    makes the test that pins it tautological for most of the day.
    """
    override = os.environ.get("ORA_SENTINEL_NOW")
    if override:
        parsed = _parse_iso(override)
        if parsed is not None:
            return parsed
    return datetime.now(timezone.utc)


def _eastern_now(force_fallback=False):
    """Current time in US/Eastern.

    Prefers zoneinfo. Falls back to the statutory US rule (DST from the 2nd Sunday
    in March 02:00 to the 1st Sunday in November 02:00) so a machine without tzdata
    still keys records to the right ET date rather than silently using UTC.

    force_fallback is for tests only (also via ORA_SENTINEL_NO_ZONEINFO=1) -- the
    fallback branch is the most intricate arithmetic here and would otherwise have
    no regression protection on a host where zoneinfo works.
    """
    utc = _utc_now()
    if not (force_fallback or os.environ.get("ORA_SENTINEL_NO_ZONEINFO")):
        try:
            from zoneinfo import ZoneInfo
            return utc.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            pass
    year = utc.year

    def nth_sunday(month, nth):
        d = datetime(year, month, 1, tzinfo=timezone.utc)
        offset = (6 - d.weekday()) % 7  # weekday(): Mon=0 .. Sun=6
        return d + timedelta(days=offset + 7 * (nth - 1))

    dst_start = nth_sunday(3, 2) + timedelta(hours=7)   # 02:00 EST = 07:00 UTC
    dst_end = nth_sunday(11, 1) + timedelta(hours=6)    # 02:00 EDT = 06:00 UTC
    offset = -4 if dst_start <= utc < dst_end else -5
    return utc.astimezone(timezone(timedelta(hours=offset)))


def et_date():
    return _eastern_now().strftime("%Y-%m-%d")


PERIODS = ("day", "week", "month")


def period_key(period, now=None):
    """The state-file bucket key for `period`, US/Eastern.

    day   -> et_date() unchanged ("YYYY-MM-DD")
    week  -> ISO year-week ("YYYY-Www")
    month -> calendar month ("YYYY-MM")

    All three formats sort lexically in chronological order, which `prune()`
    and `_period_key_to_date()` both rely on.

    `now` (an ET datetime) pins the key to a clock reading the caller already
    took -- claim --slot-times uses it so the slot and the date bucket come from
    ONE instant and cannot straddle midnight.
    """
    now = now or _eastern_now()
    if period == "week":
        return now.strftime("%G-W%V")
    if period == "month":
        return now.strftime("%Y-%m")
    return now.strftime("%Y-%m-%d")


def _period_key_to_date(key, period):
    """Best-effort anchor UTC datetime for a period key, for retention only.

    week -> Monday of that ISO week. month -> the 1st of that month.
    Returns None on anything unparseable (dropped as stale by prune())."""
    try:
        if period == "week":
            iso_year, iso_week = str(key).split("-W")
            return datetime.combine(
                datetime.fromisocalendar(int(iso_year), int(iso_week), 1).date(),
                datetime.min.time(), tzinfo=timezone.utc)
        if period == "month":
            y, m = str(key).split("-")
            return datetime(int(y), int(m), 1, tzinfo=timezone.utc)
        return _parse_iso(str(key) + "T00:00:00Z")
    except Exception:
        return None


def utc_iso():
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value):
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or None."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_minutes(claimed_at):
    """Minutes since claimed_at. None if unparseable -- treated as INFINITELY OLD
    by the caller, so a garbled timestamp releases the claim rather than wedging it."""
    dt = _parse_iso(claimed_at)
    if dt is None:
        return None
    return (_utc_now() - dt).total_seconds() / 60.0


# ------------------------------------------------------------------ paths

def default_state_path(task):
    workspace = os.environ.get("ORA_CLAUDE_WORKSPACE") or os.path.join(
        os.path.expanduser("~"), "OneDrive - Oxford Capital Partners", "Claude_Workspace")
    return os.path.join(workspace, "_state", "%s-block-completion.json" % task)


def canon_block(block):
    """Canonical STORAGE KEY for a block id.

    These ids are typed into an LLM-executed spec at four call sites per block, so
    `blockB` / `blockb` / `block-b` / `Block_B` must all address the SAME record.
    An earlier revision normalized only the log token, so `complete --block blockb`
    after `claim --block blockB` silently wrote a second record and left the first
    stuck IN_PROGRESS -- a duplicate once the TTL expired.
    """
    name = str(block).strip().replace("-", "").replace("_", "").lower()
    if name.startswith("block") and len(name) > 5:
        return "block" + name[5:].upper()
    return name


def block_token(block, suffix):
    """blockB -> BLOCK_B_<suffix>; block-b / blockb / main all tolerated."""
    name = canon_block(block)
    if name.startswith("block") and len(name) > 5:
        name = name[5:]
    return "BLOCK_%s_%s" % (name.upper(), suffix)


# ------------------------------------------------------------------ io

def _lock_pid(path):
    """PID recorded in a lock file, or None."""
    try:
        with open(path, "r", encoding="ascii") as fh:
            return int((fh.read().split("|") + [""])[0].strip())
    except Exception:
        return None


def _pid_alive(pid):
    """True if pid is running. Unknown -> True (assume alive: refusing to reap a
    lock we cannot adjudicate is the safe direction; we proceed unlocked and say so)."""
    if not pid:
        return True
    if os.name == "nt":
        try:
            out = os.popen('tasklist /FI "PID eq %d" /NH' % pid).read()
            return str(pid) in out
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return True


class _Lock(object):
    """Best-effort cross-process lock via exclusive file creation.

    Two catch-up-burst fires land minutes apart, but they CAN overlap inside the
    read-modify-write, which is exactly the race this guard exists to arbitrate --
    so serialize it rather than assume the gap. Fails open: if the lock cannot be
    taken within LOCK_TIMEOUT_S we proceed anyway and say so.
    """

    def __init__(self, target):
        self.path = target + ".lock"
        self.held = False
        self.note = None

    def __enter__(self):
        deadline = time.time() + LOCK_TIMEOUT_S
        while time.time() < deadline:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, ("%d|%s" % (os.getpid(), utc_iso())).encode("ascii"))
                os.close(fd)
                self.held = True
                return self
            except FileExistsError:
                # A lock older than the timeout MAY be a crashed holder's residue --
                # but reaping on age alone can hand the lock to a second holder while
                # the first is merely stalled (OneDrive can hold a transient handle on
                # the target; that same stall is why save_state retries). So check the
                # recorded PID is actually dead before reaping.
                try:
                    if time.time() - os.path.getmtime(self.path) > LOCK_TIMEOUT_S:
                        if not _pid_alive(_lock_pid(self.path)):
                            os.remove(self.path)
                            continue
                        self.note = ("lock held by live pid %s for >%.0fs -- proceeded unlocked"
                                     % (_lock_pid(self.path), LOCK_TIMEOUT_S))
                        return self
                except OSError:
                    pass
                time.sleep(0.15)
            except OSError as exc:
                self.note = "lock unavailable: %s" % exc
                return self
        self.note = "lock timeout after %.0fs -- proceeded unlocked" % LOCK_TIMEOUT_S
        return self

    def __exit__(self, *exc):
        if self.held:
            try:
                os.remove(self.path)
            except OSError:
                pass
        return False


def load_state(path):
    """Return (data, error). A missing file is not an error -- it is a virgin date."""
    if not os.path.exists(path):
        return {}, None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
        if not text:
            return {}, None
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}, "state file root is %s, expected object" % type(data).__name__
        return data, None
    except Exception as exc:
        return {}, "unreadable state file (%s) -- failing open" % exc


def save_state(path, data):
    """Atomic-ish write. Returns an error string, or None.

    os.replace is atomic on Windows, but OneDrive can hold a transient handle on the
    target, so retry briefly rather than losing the claim to a sync hiccup.
    """
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            return "cannot create state dir: %s" % exc
    tmp = "%s.tmp%d" % (path, os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        return "cannot write temp state: %s" % exc
    last = None
    for _ in range(6):
        try:
            os.replace(tmp, path)
            return None
        except OSError as exc:
            last = exc
            time.sleep(0.25)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return "cannot commit state file: %s" % last


def prune(data, today, period="day"):
    """Drop keys older than this period's retention span so the file cannot
    grow without bound. Unparseable keys are dropped too -- they cannot be
    today's. `period` generalizes the original day-only cutoff (identical
    behavior when period=="day") to week/month buckets, which need a wider
    span since they accumulate far fewer keys per unit of wall-clock time."""
    anchor = _period_key_to_date(today, period)
    span = RETAIN_SPAN.get(period, RETAIN_SPAN["day"])
    cutoff = (anchor - span) if anchor is not None else None
    for key in list(data.keys()):
        if key == today:
            continue
        parsed = _period_key_to_date(str(key), period)
        if parsed is None or (cutoff is not None and parsed < cutoff):
            del data[key]
    return data


def emit(payload, code):
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return code


# ------------------------------------------------------------------ commands

def cmd_claim(args):
    path = args.state or default_state_path(args.task)
    period = getattr(args, "period", None) or "day"
    slot_times = getattr(args, "slot_times", None)
    if slot_times:
        # Slot and date bucket from ONE clock reading: a separate `slot` call
        # followed by `claim` can straddle midnight (slot-21 resolved at 23:59:40,
        # claimed under the next day) and silently skip that next day's slot.
        now = _eastern_now()
        try:
            args.block, _ = resolve_slot(slot_times, now)
        except ValueError as exc:
            return emit({"task": args.task, "decision": "ERROR",
                         "error": str(exc)}, EXIT_BAD_SLOT_TIMES)
        today = period_key(period, now)
    elif not args.block:
        return emit({"task": args.task, "decision": "ERROR",
                     "error": "claim needs --block or --slot-times"}, EXIT_BAD_SLOT_TIMES)
    else:
        today = period_key(period)
    run_id = args.run_id or "run-%s" % utc_iso()
    ttl = args.ttl_min if args.ttl_min is not None else DEFAULT_TTL_MIN

    with _Lock(path) as lock:
        data, err = load_state(path)
        note = err or lock.note
        rec = (data.get(today) or {}).get(canon_block(args.block))

        base = {"task": args.task, "block": args.block, "etDate": today,
                "period": period, "periodKey": today,
                "runId": run_id, "ttlMin": ttl, "statePath": path,
                "stateFileError": note}

        if rec and not args.force:
            status = str(rec.get("status", "")).upper()
            if status == "COMPLETE":
                # THE 2026-08-09 PATH. Do not touch the prior run's record.
                base.update({
                    "decision": "SKIP_ALREADY_COMPLETE",
                    "logToken": block_token(args.block, "ALREADY_COMPLETE_TODAY"),
                    "skipClass": "NORMAL",
                    "record": rec,
                    "message": ("%s already COMPLETE for %s (runId=%s). Skip this block. "
                                "Record it as a NORMAL skip in the run summary -- it is "
                                "not a miss." % (args.block, today, rec.get("runId"))),
                })
                return emit(base, EXIT_ALREADY_COMPLETE)

            if status == "IN_PROGRESS":
                age = age_minutes(rec.get("claimedAt"))
                if age is not None and age < ttl:
                    base.update({
                        "decision": "STAND_DOWN_IN_PROGRESS",
                        "logToken": block_token(args.block, "IN_PROGRESS_ELSEWHERE"),
                        "skipClass": "NORMAL",
                        "record": rec,
                        "ageMin": round(age, 1),
                        "message": ("%s claimed %.1f min ago by runId=%s (TTL %d min). "
                                    "Another fire is live -- stand down."
                                    % (args.block, age, rec.get("runId"), ttl)),
                    })
                    return emit(base, EXIT_STAND_DOWN)
                reason = "RECLAIMED_STALE_IN_PROGRESS"
            else:
                reason = "RECLAIMED_AFTER_%s" % (status or "UNKNOWN")
        elif rec and args.force:
            reason = "FORCED_OVERRIDE"
        else:
            reason = "CLAIMED"

        new_rec = {"status": "IN_PROGRESS", "runId": run_id, "claimedAt": utc_iso(),
                   "notionPageId": None, "emailSentAt": None}
        if rec:
            new_rec["supersededRunId"] = rec.get("runId")
        data.setdefault(today, {})[canon_block(args.block)] = new_rec
        write_err = save_state(path, prune(data, today, period))

        notes = [n for n in (note, write_err) if n]
        base.update({
            "decision": "PROCEED",
            "logToken": block_token(args.block, reason),
            "record": new_rec,
            "persisted": write_err is None,
            "stateFileError": "; ".join(notes) if notes else None,
            "message": "%s claimed for %s by runId=%s (%s)." % (args.block, today, run_id, reason),
        })
        return emit(base, EXIT_OK)


def _finalize(args, status, extra):
    """Record a terminal status for a block THIS RUN OWNS.

    OWNERSHIP IS ENFORCED. An earlier revision let any invocation write a terminal
    status for any block, which opened the design's only real false-suppression
    path: `complete` on a block that was never claimed fabricated a COMPLETE
    record, and every later fire that ET date was then skipped as a NORMAL skip --
    silently, with no alarm. Suppressing a real brief is worse than a duplicate,
    so a non-owner is refused here rather than trusted.

    `fail` had the mirror hole in the release direction: a stood-down fire calling
    `fail` would clear the LIVE fire's IN_PROGRESS claim and let a third fire run
    concurrently.

    --adopt is the deliberate escape hatch for the one legitimate no-prior-claim
    case: the Sent-Items probe reports ALREADY_SENT after the state file was lost
    (OneDrive rollback), and the run records COMPLETE so Layer 1 re-converges with
    reality. It must be asked for explicitly, never inferred.
    """
    path = args.state or default_state_path(args.task)
    period = getattr(args, "period", None) or "day"
    today = period_key(period)
    key = canon_block(args.block)
    with _Lock(path) as lock:
        data, err = load_state(path)
        rec = (data.get(today) or {}).get(key)

        if rec is None and not getattr(args, "adopt", False):
            return emit({
                "task": args.task, "block": args.block, "etDate": today,
                "period": period, "periodKey": today,
                "decision": "REFUSED_NO_CLAIM",
                "logToken": block_token(args.block, "FINALIZE_WITHOUT_CLAIM"),
                "persisted": False, "record": None, "statePath": path,
                "stateFileError": err or lock.note,
                "message": ("Refusing to record %s for %s: this run never claimed it and "
                            "--adopt was not passed. Nothing was written. If the Sent-Items "
                            "probe reported ALREADY_SENT after state-file loss, re-run with "
                            "--adopt." % (status, args.block)),
            }, EXIT_REFUSED)

        if rec is not None and args.run_id and rec.get("runId") not in (None, args.run_id) \
                and not getattr(args, "adopt", False):
            return emit({
                "task": args.task, "block": args.block, "etDate": today,
                "period": period, "periodKey": today,
                "decision": "REFUSED_NOT_OWNER",
                "logToken": block_token(args.block, "FINALIZE_NOT_OWNER"),
                "persisted": False, "record": rec, "statePath": path,
                "stateFileError": err or lock.note,
                "message": ("Refusing to record %s for %s: the live record belongs to runId=%s, "
                            "not %s. Nothing was written. A stood-down fire must call NOTHING."
                            % (status, args.block, rec.get("runId"), args.run_id)),
            }, EXIT_REFUSED)

        if rec is None:
            rec = {"status": None, "runId": args.run_id, "claimedAt": utc_iso(),
                   "notionPageId": None, "emailSentAt": None, "adopted": True}
        rec.update(extra)
        rec["status"] = status
        if args.run_id:
            rec["runId"] = args.run_id
        rec["%sAt" % status.lower().split("_")[0]] = utc_iso()
        data.setdefault(today, {})[key] = rec
        write_err = save_state(path, prune(data, today, period))

    # Do NOT let an earlier note mask a failed write -- that is the one error this
    # channel most needs to carry, and it was previously short-circuited away.
    notes = [n for n in (err, lock.note, write_err) if n]
    return emit({"task": args.task, "block": args.block, "etDate": today,
                 "period": period, "periodKey": today,
                 "decision": status, "record": rec, "statePath": path,
                 "persisted": write_err is None,
                 "stateFileError": "; ".join(notes) if notes else None}, EXIT_OK)


def cmd_complete(args):
    extra = {}
    if args.notion_page_id:
        extra["notionPageId"] = args.notion_page_id
    if args.email_sent_at:
        extra["emailSentAt"] = args.email_sent_at
    return _finalize(args, "COMPLETE", extra)


def cmd_fail(args):
    """Mark a block FAILED. Deliberately NOT the same as leaving it IN_PROGRESS:
    a FAILED record releases the claim immediately, so a legitimate operator retry
    does not have to wait out the TTL."""
    return _finalize(args, "FAILED", {"error": args.error or "unspecified"})


def cmd_status(args):
    """Read-only. Must not create the state file -- callers use it to inspect."""
    path = args.state or default_state_path(args.task)
    period = getattr(args, "period", None) or "day"
    today = period_key(period)
    data, err = load_state(path)
    rec = (data.get(today) or {}).get(canon_block(args.block))
    age = age_minutes(rec.get("claimedAt")) if rec else None
    return emit({"task": args.task, "block": args.block, "etDate": today,
                 "period": period, "periodKey": today,
                 "record": rec, "ageMin": round(age, 1) if age is not None else None,
                 "statePath": path, "stateFileError": err}, EXIT_OK)


EXIT_BAD_SLOT_TIMES = 2    # same code argparse uses for bad input


def resolve_slot(times_arg, now):
    """Which cron slot a multi-fire-per-day task is in at ET datetime `now`.

    Added 2026-09-24: an ora-pr-land-watch run used Git Bash
    `TZ=America/New_York date`, which this machine silently evaluates as UTC,
    read 12:51 EDT as 16:51 and claimed slot-15 instead of slot-12. Slot math
    now lives next to the ET clock this module already owns.

    `times_arg` is the task's ET fire times, "HH:MM,..." in any order. The slot
    is the latest time at or before now (inclusive, to the minute); before the
    first one it is `slot-pre<HH>`. Labels use the hour only, so the hours must
    be distinct. Returns (block, sorted times); raises ValueError on bad input.
    """
    import re
    times = []
    for raw in str(times_arg).split(","):
        t = raw.strip()
        m = re.match(r"^([01][0-9]|2[0-3]):([0-5][0-9])$", t)
        if not m:
            raise ValueError("invalid slot time %r (need HH:MM, 24h)" % t)
        times.append((int(m.group(1)), int(m.group(2))))
    times = sorted(set(times))
    if len({h for h, _ in times}) != len(times):
        raise ValueError("slot times must have distinct hours (labels are slot-HH)")
    started = [t for t in times if t <= (now.hour, now.minute)]
    block = "slot-%02d" % started[-1][0] if started else "slot-pre%02d" % times[0][0]
    return block, times


def cmd_slot(args):
    """Read-only preview of the block `claim --slot-times` would resolve.

    Unlike claim/complete/fail, bad input does NOT fail open: exit 2 with no
    `block`, because a guessed slot id is exactly the defect this exists to fix.
    """
    now = _eastern_now()
    try:
        block, times = resolve_slot(args.times, now)
    except ValueError as exc:
        return emit({"decision": "ERROR", "error": str(exc)}, EXIT_BAD_SLOT_TIMES)
    return emit({"block": block, "etDate": now.strftime("%Y-%m-%d"),
                 "etTime": now.strftime("%H:%M"),
                 "times": ["%02d:%02d" % t for t in times]}, EXIT_OK)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("claim", "complete", "fail", "status"):
        sp = sub.add_parser(name)
        sp.add_argument("--task", required=True)
        # claim may resolve its block from --slot-times instead (checked in cmd_claim)
        sp.add_argument("--block", required=(name != "claim"))
        sp.add_argument("--state", default=None,
                        help="state file path; defaults to Claude_Workspace/_state/<task>-block-completion.json")
        sp.add_argument("--run-id", default=None)
        sp.add_argument("--period", choices=PERIODS, default="day",
                        help="calendar bucket the claim/complete record is keyed to "
                             "(default day); must match across claim/complete/fail for one run")
        if name == "claim":
            sp.add_argument("--ttl-min", type=int, default=None)
            sp.add_argument("--force", action="store_true",
                            help="override a COMPLETE record (documented manual-rerun escape hatch)")
            sp.add_argument("--slot-times", default=None,
                            help="ET fire times HH:MM,... -- resolve the block (slot-HH) inside the "
                                 "claim from the same clock reading as the date; overrides --block. "
                                 "Reuse the emitted `block` verbatim for complete/fail")
        if name == "complete":
            sp.add_argument("--notion-page-id", default=None)
            sp.add_argument("--email-sent-at", default=None)
        if name == "fail":
            sp.add_argument("--error", default=None)
        if name in ("complete", "fail"):
            sp.add_argument("--adopt", action="store_true",
                            help="record a terminal status with no prior claim (state-file-loss "
                                 "re-convergence only); without it a non-owner is REFUSED exit 12")
    sp = sub.add_parser("slot", help="print the current ET cron-slot block id (read-only)")
    sp.add_argument("--times", required=True,
                    help="comma-separated ET fire times, HH:MM (e.g. 09:35,12:35,15:35)")
    args = parser.parse_args(argv)
    if args.cmd == "slot":
        return cmd_slot(args)
    try:
        return {"claim": cmd_claim, "complete": cmd_complete,
                "fail": cmd_fail, "status": cmd_status}[args.cmd](args)
    except Exception as exc:  # fail open, loudly
        return emit({"task": getattr(args, "task", None), "block": getattr(args, "block", None),
                     "decision": "PROCEED", "logToken": "BLOCK_SENTINEL_INTERNAL_ERROR",
                     "stateFileError": "internal error (%s) -- failing open" % exc}, EXIT_OK)


if __name__ == "__main__":
    sys.exit(main())

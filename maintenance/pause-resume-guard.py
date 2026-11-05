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

Also checks the GENERAL case (2026-08-21 follow-on, OI-202): ANY one-time
task, not just a fleet resume, that fired and left a stale/incomplete
task-progress-marker.py marker -- see that script for the write-side
convention. This is the general fix OI-202's fix direction asked for; the
fleet-ratio check above is the narrower, concrete instance that motivated it
and stays as an independent signal (a stalled resume with no marker at all
still trips it).

Also checks RETIRE-PENDING RESURRECTION (2026-08-22, register-scheduled-task
v2.14): a retirement that has been RATIFIED but not yet EXECUTED leaves the
task registered with enabled:false, and enabled:false is not a retirement --
it is a pause. Any fleet-wide resume (the very thing the checks above exist to
chase) flips it back on and silently reverses the decision; on a same-id
cross-fleet pair it also resurrects the duplicate the retirement existed to
remove. maintenance/_state/retire-pending.json is the register of those
in-flight retirements; this alarms when one of its ids is found enabled:true
on its named fleet. Fail-open by construction: an absent, unreadable or
malformed register yields no findings, never a crash and never a false alarm.
It is read as utf-8-sig (2026-11-05): a PowerShell-written BOM used to make the
whole register read as malformed.

Also checks STRANDED TASKS (2026-11-05). Every check above judges an EVENT -- a
resume inside a 72h window, a fleet-wide ratio at or below 10% -- and none
judges the persistent STATE "a recurring task is disabled and nobody recorded
why". On 2026-09-28 the CC resume ora-routine-pause-resume-09-28 stalled with
35 recurring tasks still disabled, and the incomplete-resume check saw it but
its alarm was never delivered. The same day a cleanup pass archived the
resume's folder, its filePath stopped resolving and the case fell out of every
check, so 24 of those tasks (13 business reports, 5 data producers) stayed
dark 32 days until a human triage on 2026-10-30. find_stranded() flags every
recurring task (the fleet-ratio check's one-time test) whose enabled is falsy
unless (a) it is filed in retire-pending.json, (b) a hold in
maintenance/_state/held-off.json decides it, or (c) capture_pause_windows()
lists it as held AND its fleet has an ENABLED one-time *-resume-* task firing
between 24h ago and 21 days ahead -- a bounded pause in progress. That held
list carries no time bound of its own, so without such a resume it is ignored
and the digest says why. The held-off register records deliberate "keep it
off" rulings:

    {"holds": [{"fleet": "cc"|"lams", "id": "<task id, or * for the whole fleet>",
                "reason": "...", "ruledBy": "...", "ruledOn": "YYYY-MM-DD",
                "reviewBy": "YYYY-MM-DD"}]}

A hold is active through its reviewBy date (UTC); after that its tasks are
stranded again as "hold-expired", so no ruling silently outlives its review.
An exact-id hold, active or expired, decides its task alone; "*" applies only
where no exact-id hold exists. ONE digest alarm (stranded:digest) carries the
whole set and names every newly stranded id, uncapped. It is NEW when any
stranded id lacks an alertedAt from a delivered digest in the last 7 days, or
when lastAlerted is more than 7 days old, in the future or unreadable: a
persisting set re-alerts weekly ("week N"), and an id flapping in and out of an
exclusion re-alerts at most weekly, because its alertedAt outlives its exit
from the set by 7 days. lastAlerted/alertedAt advance only once send_alert()
confirms delivery, and a fleet with no registry this run keeps its record
untouched. The whole check -- judging, bookkeeping, digest text -- runs inside
one try: any failure becomes the stranded:check-error alarm, never a skipped
send or save.

The held-off register is NOT fail-open-silent: its only job is to SUPPRESS
alarms, so an unreadable or malformed file -- or an entry with a missing or
non-string fleet/id/reviewBy, a non-string reason, an unknown fleet or an
unparseable reviewBy (nothing is coerced) -- applies no hold and is named in
the digest. A broken register must surface stranded tasks, never hide them (a
broken retire-pending.json is named the same way). An absent held-off file
simply means no holds.

One DELIBERATE change to the fleet-ratio check (2026-11-05): an ACTIVE "*"
hold also suppresses that fleet's near-zero trip. Gabriel ruled the LAMS fleet
dark on 2026-10-30, and the guard had been trying to send a LAMS near-zero
alarm every run since. The run prints one "held by ruling" line instead; the
marker, retire-pending, incomplete-resume and stranded checks ignore that
hold. Apart from that, the existing checks compute the same alarms and state
as before; when a stranded digest fires in the same run, it shares the single
email and the subject gains "(stranded tasks: K, week N)".

Sends ONE Outlook COM alert via the proven standalone path
(send-via-outlook.ps1 -- deploy-mirror.ps1 already uses this successfully
outside any Claude session). Writes a state file so a persisting alarm
doesn't re-email every run; a NEW alarm (fleet flipped from OK to ALARM, or a
newly-stalled marker) always sends immediately. Since 2026-11-05 every send
attempt is recorded in that state file's _sendLog (the 10 most recent: at, ok,
rc, stderr, stdout, subject, plus exception when subprocess.run itself raised
-- send_alert never raises), the latest is printed in the text summary, and the
file is written atomically (temp file + os.replace) so a killed run cannot
truncate it.

Usage:
    python pause-resume-guard.py [--json] [--min-enabled-ratio F] [--resume-grace-minutes N] [--marker-grace-minutes N]
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fleet_status", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-status.py"))
fleet_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fleet_status)

_spec2 = importlib.util.spec_from_file_location(
    "task_progress_marker", os.path.join(os.path.dirname(os.path.abspath(__file__)), "task-progress-marker.py"))
task_progress_marker = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(task_progress_marker)

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "pause-resume-guard-state.json")
RETIRE_PENDING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "retire-pending.json")
# Deliberate "keep this recurring task disabled" rulings honoured by the STRANDED check (see the
# module docstring). Overridable for tests, like the two paths above.
HELD_OFF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state", "held-off.json")
SEND_SCRIPT = r"C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
RESUME_ID_RE = re.compile(r"-resume-", re.IGNORECASE)
NOTION_ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
# Same target every other native/scheduled-task alert in this fleet posts status/failure
# notes to (ora-am-brief, ora-cc-snapshot-refresh, ora-doctrine-integrity-guard, ...).
OPERATIONS_HUB_PAGE_ID = "32b6ecd8-9e59-81f2-b329-df3fd0e25062"
SEND_LOG_MAX = 10  # C8 (2026-11-05): send attempts kept in the state file's _sendLog


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    """Atomic (2026-11-05): write a temp file beside STATE_PATH, then os.replace() it over the
    old one. Writing in place meant a run killed mid-write (one died at 12 s on 2026-11-05, exit
    0xC000013A) left a truncated file that load_state() reads as {} -- silently forgetting every
    alarmed / firstSeen / alertedAt record. A failed write still raises; the old file survives."""
    d = os.path.dirname(STATE_PATH)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pause-resume-guard-state.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def parse_fire_at(task):
    """fireAt on a live registry entry is epoch-ms (int/float), not an ISO
    string -- confirmed against the live cc/lams registries 2026-08-21. This
    used to call fa.replace(...) directly, which threw on an int and was
    silently swallowed by the except below, so overdue-resume detection could
    never fire (empty resume_tasks the same day, for the same reason -- see
    the taskId->id fix at the call site)."""
    fa = fleet_status.fire_at(task)
    if fa is None:
        return None
    try:
        return datetime.fromtimestamp(fa / 1000, tz=timezone.utc)
    except Exception:
        return None


def load_retire_pending(path=None):
    """Entries from _state/retire-pending.json: retirements RATIFIED but not yet EXECUTED.

    Shape: {"pending": [{"fleet": "cc"|"lams", "id": ..., "ratified": "YYYY-MM-DD",
    "reason": ..., "executeFrom": ...}, ...]}; a bare top-level list is also accepted.

    FAIL-OPEN, deliberately: an absent, unreadable or malformed register returns [] and
    this guard reports nothing. The register is a convenience for making an in-flight
    retirement observable -- it must never be able to crash the guard that also carries
    the fleet-ratio and stalled-marker checks, and a parse error must never masquerade
    as "no retirement is pending" ALARM-side either. Entries missing fleet or id are
    skipped rather than guessed at."""
    return _read_retire_pending(path)[0]


def _read_retire_pending(path=None):
    """(entries, errors): load_retire_pending()'s reader, plus one human-readable string per
    problem. load_retire_pending() drops the errors, so its fail-open contract above is
    unchanged; the STRANDED check reports them instead, because a broken register is exactly
    what would make a retirement-in-flight id read as stranded. An absent file is no error.
    Read as utf-8-sig (D10, 2026-11-05): PowerShell 5.1 writes UTF-8 WITH a BOM, which strict
    utf-8 read as a malformed register -- stranding every retire-pending id and blinding the
    resurrection check."""
    path = path or RETIRE_PENDING_PATH
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [], []
    except Exception as exc:  # noqa: BLE001 -- reported, never raised
        return [], [_ascii_safe(f"retire-pending register {path} unreadable ({type(exc).__name__}: {exc})")]
    entries = data.get("pending") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return [], [_ascii_safe(f'retire-pending register {path} has no "pending" list')]
    good = [e for e in entries
            if isinstance(e, dict) and e.get("id") and e.get("fleet")]
    errors = []
    if len(good) < len(entries):
        errors.append(_ascii_safe(f"retire-pending register {path}: {len(entries) - len(good)} "
                                  f"entry(ies) without fleet/id skipped"))
    return good, errors


def find_resurrected(tasks_by_fleet, path=None):
    """Retire-pending ids found ENABLED on their named fleet -- i.e. a ratified retirement
    that a resume (or a hand re-enable) has silently reversed while it waited to execute.

    Three outcomes per entry, only one of which is a finding:
      - id present and enabled  -> FINDING (the registration is live again)
      - id present and disabled -> normal: still awaiting execution, exactly as filed
      - id absent from the fleet -> the retirement executed; the register entry is stale
        and should be removed, but a stale entry is not an alarm (removing it is the
        executing session's job, and alarming here would punish a completed retirement).
    """
    out = []
    for e in load_retire_pending(path):
        fleet = str(e["fleet"]).lower()
        for t in tasks_by_fleet.get(fleet, []):
            if t.get("id") != e["id"]:
                continue
            if t.get("enabled"):
                out.append({"fleet": fleet, "id": e["id"],
                            "ratified": e.get("ratified", "unknown"),
                            "reason": e.get("reason", ""),
                            "executeFrom": e.get("executeFrom", "the fleet's own surface")})
            break
    return out


def analyze_fleet(label, tasks):
    recurring = [t for t in tasks if not fleet_status.is_onetime(t.get("cronExpression") or t.get("fireAt", ""))]
    if not recurring:
        return {"fleet": label, "status": "NO_RECURRING_TASKS", "ratio": None}

    enabled = sum(1 for t in recurring if t.get("enabled"))
    ratio = enabled / len(recurring)

    # NOTE (2026-08-21): live registry entries key the id as "id", not
    # "taskId" -- the original taskId lookup always returned "" and this list
    # was silently empty on every run. Same incident as parse_fire_at above.
    resume_tasks = [t for t in tasks if RESUME_ID_RE.search(t.get("id", "")) and fleet_status.fire_at(t) is not None]
    now = datetime.now(timezone.utc)
    overdue_resume = None
    for t in resume_tasks:
        fa = parse_fire_at(t)
        if fa and fa < now:
            overdue_resume = {"taskId": t.get("id"), "fireAt": t.get("fireAt"),
                               "minutesOverdue": (now - fa).total_seconds() / 60}
            break

    return {
        "fleet": label, "status": "OK", "ratio": ratio,
        "enabledCount": enabled, "totalRecurring": len(recurring),
        "overdueResume": overdue_resume,
        # A resume task that EXISTS but isn't due yet (fireAt in the future) also leaves
        # overdue_resume None -- without this, the caller's "no pending/overdue resume task
        # exists for this fleet" branch couldn't tell that apart from a genuinely absent
        # resume, and fired a false alarm on a legitimately scheduled future pause.
        "hasResumeTask": bool(resume_tasks),
    }


def _load_notion_token():
    # Exact key match (mirrors scheduled-tasks/ora-pm-ledger/*_snapshot_diff.py's
    # load_token): a prefix match would happily return NOTION_TOKEN_OLD / _BACKUP and
    # authenticate as the wrong (possibly revoked) integration.
    with open(NOTION_ENV_PATH, encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.partition("=")
            if sep and k.strip() == "NOTION_TOKEN":
                return v.strip().strip('"').strip("'")
    raise RuntimeError(f"NOTION_TOKEN not found in {NOTION_ENV_PATH}")


def _log_send_failure_to_notion(subject, identifier, proc):
    """Best-effort ONLY -- a Notion logging failure must never raise past this call. The
    guard's obligation is to have TRIED to make a silent send failure visible somewhere,
    not to guarantee delivery of the visibility mechanism itself (that would just move the
    single-point-of-failure, not remove it). Appends a paragraph block to the Operations
    Hub page, the same target every other native/scheduled-task alert in this fleet posts
    status/failure notes to."""
    try:
        token = _load_notion_token()
        text = (f"[ALERT SEND FAILED] pause-resume-guard could not deliver: {subject} "
                f"(identifier={identifier!r}, send-via-outlook.ps1 exit={proc.returncode}, "
                f"stderr={proc.stderr.strip()[:300]!r})")
        req = urllib.request.Request(
            f"https://api.notion.com/v1/blocks/{OPERATIONS_HUB_PAGE_ID}/children",
            data=json.dumps({"children": [{
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
            }]}).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            method="PATCH")
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        return True
    except Exception:
        return False


class _NoProc:
    """Stands in for a CompletedProcess when subprocess.run itself raised (C8)."""

    def __init__(self, error):
        self.returncode = None
        self.stdout = ""
        self.stderr = error


def _record_send(send_log, subject, proc, error=None):
    """C8: append one send attempt to send_log (main() passes the state's _sendLog), keeping the
    SEND_LOG_MAX most recent: {at, ok, rc, stderr (first 500 chars), stdout (first 200 chars),
    subject} plus exception when subprocess.run itself raised. Never raises."""
    if not isinstance(send_log, list):
        return
    try:
        rc = getattr(proc, "returncode", None)
        entry = {"at": datetime.now(timezone.utc).isoformat(), "ok": error is None and rc == 0, "rc": rc,
                 "stderr": _ascii_safe(str(getattr(proc, "stderr", "") or "")[:500]),
                 "stdout": _ascii_safe(str(getattr(proc, "stdout", "") or "")[:200]),
                 "subject": _ascii_safe(subject)}
        if error is not None:
            entry["exception"] = _ascii_safe(str(error)[:500])
        send_log.append(entry)
        del send_log[:-SEND_LOG_MAX]
    except Exception:  # noqa: BLE001 -- observability must never break delivery
        pass


def _send_attempt(args, subject, send_log):
    """One recorded subprocess attempt. Returns the CompletedProcess, or a _NoProc when
    subprocess.run itself raised (recorded, never raised)."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True)
    except Exception as exc:  # noqa: BLE001
        error = _describe_exc(exc)
        _record_send(send_log, subject, None, error)
        return _NoProc(error)
    _record_send(send_log, subject, proc)
    return proc


def send_alert(subject, body, identifier=None, send_log=None):
    """One retry on a COM failure (2) or timeout (4) -- matches PR Compliance's send-script
    caller contract. Returns whether delivery actually succeeded; callers MUST check this
    (see main()) rather than assume the send happened, and MUST NOT persist alarm-suppression
    state as delivered until this returns True -- a discarded return value here previously let
    a failed send permanently suppress every future retry of a still-active alarm.

    C8 (2026-11-05): the scheduled guard had logged no send since 2026-09-02 while its state
    showed tripped alarms with alarmed:false, so every subprocess attempt is now appended to
    `send_log` (main() passes the state's _sendLog), and nothing here raises: an exception from
    subprocess.run, or from writing the temp body file, is recorded and reported as a failed
    delivery. The send command line itself is unchanged."""
    body_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            body_path = f.name
            f.write(body)
        args = ["powershell", "-NoProfile", "-File", SEND_SCRIPT, "-To", "ggoldberg@oxfordra.net",
                "-Subject", subject, "-BodyFile", body_path, "-BodyFormat", "text"]
        proc = _send_attempt(args, subject, send_log)
        if proc.returncode in (2, 4):
            proc = _send_attempt(args, subject, send_log)
        ok = proc.returncode == 0
        if not ok:
            _log_send_failure_to_notion(subject, identifier, proc)
        return ok
    except Exception as exc:  # noqa: BLE001 -- e.g. the temp body file could not be written
        _record_send(send_log, subject, None, _describe_exc(exc))
        return False
    finally:
        if body_path:
            try:
                os.unlink(body_path)
            except OSError:
                pass


def _describe_send(entry):
    """One line for the text summary's "last send:" (C8). Never raises."""
    if not isinstance(entry, dict):
        return "none recorded"
    try:
        text = f"{entry.get('at')} ok={entry.get('ok')} rc={entry.get('rc')} subject={entry.get('subject')!r}"
        if entry.get("exception"):
            text += f" exception={entry.get('exception')!r}"
        if entry.get("stderr"):
            text += f" stderr={str(entry.get('stderr'))[:300]!r}"
        return _ascii_safe(text)
    except Exception:  # noqa: BLE001
        return "unreadable entry"


INCOMPLETE_RESUME_GRACE_MINUTES = 30
INCOMPLETE_RESUME_LOOKBACK_HOURS = 72
INCOMPLETE_RESUME_MIN_LISTED = 3
_REENABLE_RE = re.compile(r"re-?enable|update_scheduled_task\s*\([^)]*enabled\s*:\s*true", re.IGNORECASE)


def _parse_run_ts(v):
    """lastRunAt -> aware UTC datetime, or None. Accepts ISO with Z/offset, NAIVE ISO
    (treated as UTC -- a naive value used to raise TypeError out of the age subtraction and
    kill main()), and epoch milliseconds (used to be skipped silently). Review 2026-09-12."""
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(float(v) / 1000.0, tz=timezone.utc)
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
    except Exception:
        return None


def find_incomplete_resumes(tasks_by_fleet, retire_pending_path=None, now=None,
                            grace_minutes=INCOMPLETE_RESUME_GRACE_MINUTES,
                            lookback_hours=INCOMPLETE_RESUME_LOOKBACK_HOURS):
    """Fired resume-shaped one-time tasks whose listed recurring ids are STILL disabled.

    OI-273 (2026-09-12): the 2026-09-11 resume re-enabled 6 of 38 ids, then blocked on a
    permission prompt nobody answered (the Desktop scheduled-task runner does not
    auto-approve update_scheduled_task unattended), and list_task_runs reported
    `succeeded`. The fleet-ratio check above cannot see that shape (6/38 = 16% > 10%), and
    the stalled-marker check depends on the task's own marker calls. This compares what the
    resume ASKED for against live `enabled` -- no dependency on session status or markers.

    Resume-shaped = has fired (lastRunAt), carries a re-enable instruction, and names at
    least INCOMPLETE_RESUME_MIN_LISTED of the fleet's recurring ids. Judged only between
    grace_minutes and lookback_hours after firing. Retire-pending ids are excluded (they are
    disabled on purpose). Ids no longer in the registry are ignored (retired). Direction of
    error: a resume-shaped audit naming legitimately-disabled tasks could false-alarm; it
    can never hide a partial resume.
    """
    now = now or datetime.now(timezone.utc)
    pending = {(str(e["fleet"]).lower(), e["id"]) for e in load_retire_pending(retire_pending_path)}
    out = []
    for fleet, tasks in tasks_by_fleet.items():
        recurring = {t.get("id"): t for t in tasks if t.get("id") and t.get("cronExpression")}
        for t in tasks:
            if t.get("cronExpression") or fleet_status.fire_at(t) is None or not t.get("lastRunAt"):
                continue
            fired = _parse_run_ts(t["lastRunAt"])
            if fired is None:
                continue
            age = now - fired
            if age < timedelta(minutes=grace_minutes) or age > timedelta(hours=lookback_hours):
                continue
            try:
                with open(t.get("filePath") or "", encoding="utf-8") as fh:
                    text = fh.read()
            except Exception:
                continue
            if not _REENABLE_RE.search(text):
                continue
            listed = [i for i in recurring
                      if re.search(r"(?<![\w-])" + re.escape(i) + r"(?![\w-])", text)]
            if len(listed) < INCOMPLETE_RESUME_MIN_LISTED:
                continue
            order = {i: text.find(i) for i in listed}
            listed.sort(key=lambda i: order[i])
            disabled = [i for i in listed
                        if not recurring[i].get("enabled") and (fleet, i) not in pending]
            if disabled:
                out.append({"fleet": fleet, "taskId": t.get("id"), "firedAt": t.get("lastRunAt"),
                            "listed": len(listed), "disabled": disabled})
    return out


HOLD_FLEETS = ("cc", "lams")
STRANDED_REALERT_DAYS = 7
STRANDED_DIGEST_MAX_LISTED = 25
_YMD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# D2 (2026-11-05): capture_pause_windows()'s "held" list is honoured only while its fleet has an
# ENABLED one-time *-resume-* task firing inside this window around now.
PAUSE_HOLDER_AHEAD = timedelta(days=21)
PAUSE_HOLDER_OVERDUE = timedelta(hours=24)


def _ascii_safe(text):
    """Register text is hand-written (arrows, curly quotes, dashes). With stdout redirected --
    as under the native task -- Python 3.13 on this machine encodes print() as cp1252, and one
    unencodable character raises out of print() and kills the run before save_state() and
    send_alert(). Backslash-escape anything non-ASCII instead."""
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def load_holds(path=None, today=None):
    """Held-off register (_state/held-off.json) -> (active_holds, expired_holds, errors).

    Shape: {"holds": [{"fleet": "cc"|"lams", "id": "<task id or *>", "reason": ...,
    "ruledBy": ..., "ruledOn": "YYYY-MM-DD", "reviewBy": "YYYY-MM-DD"}, ...]}. id "*" holds
    the whole fleet. A hold is ACTIVE while reviewBy >= today (UTC date), expired after.

    Never raises. A missing file means no holds and no error. An unreadable or malformed
    file, or an entry that is not an object, lacks fleet/id/reviewBy, carries a non-string
    fleet/id/reviewBy/reason (D9), names a fleet other than exactly "cc"/"lams", or a reviewBy
    that is not a real YYYY-MM-DD date, contributes NO hold and one error string. Nothing is
    coerced -- no str(), no case-folding, no trimming: a value that is not exactly right is
    named, never silently repaired. That is the opposite of load_retire_pending()'s silent
    fail-open, on purpose: this register can only SUPPRESS alarms, so a broken one must
    surface stranded tasks, not hide them. Holds are returned exactly as written."""
    path = path or HELD_OFF_PATH
    if today is None:
        today = datetime.now(timezone.utc).date()
    elif isinstance(today, datetime):
        today = (today.astimezone(timezone.utc) if today.tzinfo else today).date()
    active, expired, errors = [], [], []
    try:
        # utf-8-sig: PowerShell 5.1 (this machine's default shell) writes UTF-8 WITH a BOM, and a
        # BOM is not a content error -- strict utf-8 would turn it into a false "unreadable".
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return active, expired, errors
    except Exception as exc:  # noqa: BLE001 -- reported, never raised
        errors.append(_ascii_safe(f"held-off register {path} unreadable ({type(exc).__name__}: {exc}) "
                                  f"-- no hold applied"))
        return active, expired, errors
    entries = data.get("holds") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        errors.append(_ascii_safe(f'held-off register {path} is not {{"holds": [...]}} -- no hold applied'))
        return active, expired, errors
    for n, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            errors.append(f"held-off entry #{n} is not an object -- skipped, no hold applied")
            continue
        problems = []
        for k in ("fleet", "id", "reviewBy"):
            v = e.get(k)
            if v is None or v == "":
                problems.append(f"missing {k}")
            elif not isinstance(v, str):
                problems.append(f"{k} must be a string (got {type(v).__name__})")
            elif v != v.strip():
                problems.append(f"{k} {v!r} has leading/trailing whitespace")
        if "reason" in e and not isinstance(e["reason"], str):
            problems.append(f"reason must be a string (got {type(e['reason']).__name__})")
        fleet, tid, review = e.get("fleet"), e.get("id"), e.get("reviewBy")
        if not problems and fleet not in HOLD_FLEETS:
            problems.append(f"unknown fleet {fleet!r} (expected exactly cc or lams)")
        review_by = None
        if not problems:
            try:
                if not _YMD_RE.fullmatch(review):
                    raise ValueError(review)
                review_by = date.fromisoformat(review)
            except ValueError:
                problems.append(f"reviewBy {review!r} is not a YYYY-MM-DD date")
        if problems:
            label = ":".join(x if isinstance(x, str) and x else "?" for x in (fleet, tid))
            errors.append(_ascii_safe(f"held-off entry #{n} ({label}): {'; '.join(problems)} "
                                      f"-- skipped, no hold applied"))
            continue
        (active if review_by >= today else expired).append(dict(e))
    return active, expired, errors


def _unbounded_pause_reason(tasks, now):
    """D2: None when `tasks` (one fleet) has an ENABLED one-time task whose id matches
    RESUME_ID_RE and whose fireAt lies between now - PAUSE_HOLDER_OVERDUE and
    now + PAUSE_HOLDER_AHEAD -- the only holder whose pause_windows "held" list the stranded
    check honours (that list has no time bound of its own and is not resume-specific).
    Otherwise, a human-readable reason why not."""
    near = []
    for t in tasks:
        if not isinstance(t, dict) or not t.get("enabled") or not isinstance(t.get("id"), str):
            continue
        if not RESUME_ID_RE.search(t["id"]):
            continue
        if not fleet_status.is_onetime(t.get("cronExpression") or t.get("fireAt", "")):
            continue
        fa = parse_fire_at(t)
        if fa is None:
            continue
        if now - PAUSE_HOLDER_OVERDUE <= fa <= now + PAUSE_HOLDER_AHEAD:
            return None
        near.append(f"{t['id']} fires {fa.date().isoformat()}")
    if not near:
        return "the fleet has no enabled one-time *-resume-* task to bound it"
    return ("no enabled *-resume-* task fires between 24h ago and 21 days ahead ("
            + ", ".join(near[:3]) + ")")


def find_stranded(tasks_by_fleet, held_by_pause=None, retire_pending_path=None,
                  holds_path=None, today=None, now=None):
    """Recurring tasks that are disabled with NO recorded intent -> (stranded, errors).

    Candidate = recurring (analyze_fleet's test: not fleet_status.is_onetime(cronExpression
    or fireAt)) AND enabled falsy. A candidate is NOT stranded when (a) its (fleet, id) is
    retire-pending, (b) an ACTIVE hold decides it, or (c) it is in held_by_pause[fleet] --
    capture_pause_windows()'s "held": disabled AND named by a pending, not-yet-fired resume --
    AND that fleet has a bounded resume (_unbounded_pause_reason: D2); without one the fleet's
    held list is ignored and a note says why. Holds (D8): an exact-id hold, active or expired,
    decides its task alone; the fleet's "*" applies only where no exact-id hold exists. A
    candidate decided by an EXPIRED hold IS stranded, as "hold-expired" with that hold's reason
    and reviewBy; every other candidate is "no-recorded-intent".

    stranded: [{fleet, id, reason, holdReason, reviewBy}], sorted by (fleet, id).
    errors: one human-readable string per exclusion NOT applied -- the held-off and
    retire-pending loaders' errors and any ignored pause list. Each excuses nothing, so the
    direction of error is a false alarm, never a hidden stranded task."""
    now = now or datetime.now(timezone.utc)
    active, expired, errors = load_holds(holds_path, today)
    pending, rp_errors = _read_retire_pending(retire_pending_path)
    errors = errors + rp_errors
    fleets = {str(f).lower(): (ts or []) for f, ts in tasks_by_fleet.items()}
    retiring = {(str(e["fleet"]).lower(), e["id"]) for e in pending}
    paused = set()
    for f, ids in (held_by_pause or {}).items():
        fleet = str(f).lower()
        ids = [i for i in (ids or []) if isinstance(i, str)]
        if not ids:
            continue
        why_not = _unbounded_pause_reason(fleets.get(fleet, []), now)
        if why_not is None:
            paused.update((fleet, i) for i in ids)
        else:
            errors.append(_ascii_safe(f"pause exclusion ignored for {fleet} ({len(ids)} held id(s)): {why_not}"))

    def ruling(fleet, tid):
        for wanted in (tid, "*"):  # exact id first; "*" only when no exact-id hold exists
            live = [h for h in active if h["fleet"] == fleet and h["id"] == wanted]
            if live:
                return live[0], True
            lapsed = [h for h in expired if h["fleet"] == fleet and h["id"] == wanted]
            if lapsed:
                return lapsed[0], False
        return None, False

    out, seen = [], set()
    for fleet, tasks in fleets.items():
        for t in tasks:
            tid = t.get("id")
            if not tid or t.get("enabled"):
                continue
            if fleet_status.is_onetime(t.get("cronExpression") or t.get("fireAt", "")):
                continue
            key = (fleet, tid)
            if key in seen or key in retiring or key in paused:
                continue
            hold, is_active = ruling(fleet, tid)
            if is_active:
                continue
            seen.add(key)
            out.append({"fleet": fleet, "id": tid,
                        "reason": "hold-expired" if hold else "no-recorded-intent",
                        "holdReason": hold.get("reason", "") if hold else None,
                        "reviewBy": hold["reviewBy"] if hold else None})
    out.sort(key=lambda s: (s["fleet"], str(s["id"])))
    return out, errors


def _fleet_rulings(path=None, today=None):
    """{fleet: hold} for every ACTIVE "*" hold -- the recorded rulings that also hold that
    fleet's fleet-ratio near-zero alarm (2026-11-05). Never raises; a broken register holds
    nothing, so the alarm stands."""
    try:
        out = {}
        for h in load_holds(path, today)[0]:
            if h.get("id") == "*":
                out.setdefault(h["fleet"], h)
        return out
    except Exception:  # noqa: BLE001
        return {}


def _describe_exc(exc):
    try:
        return f"{type(exc).__name__}: {exc}"
    except Exception:  # noqa: BLE001 -- a broken __str__ must not break the alarm about it
        return type(exc).__name__


def _stranded_record(raw):
    """The stored _stranded value -> a clean {ids, firstSeen, alertedAt, lastAlerted}. Keeps only
    str ids and str keys/values (D9); migrates the pre-D6 alertedIds list to alertedAt (each id
    alerted at lastAlerted). Never mutates `raw`; a checkError marker is not carried over."""
    raw = raw if isinstance(raw, dict) else {}
    ids = [i for i in raw["ids"] if isinstance(i, str)] if isinstance(raw.get("ids"), list) else []
    seen_raw = raw.get("firstSeen") if isinstance(raw.get("firstSeen"), dict) else {}
    first_seen = {k: v for k, v in seen_raw.items() if isinstance(k, str) and isinstance(v, str)}
    last = raw.get("lastAlerted") if isinstance(raw.get("lastAlerted"), str) else None
    if isinstance(raw.get("alertedAt"), dict):
        alerted_at = {k: v for k, v in raw["alertedAt"].items() if isinstance(k, str) and isinstance(v, str)}
    elif isinstance(raw.get("alertedIds"), list) and last is not None:
        alerted_at = {i: last for i in raw["alertedIds"] if isinstance(i, str)}
    else:
        alerted_at = {}
    return {"ids": ids, "firstSeen": first_seen, "alertedAt": alerted_at, "lastAlerted": last}


def _update_stranded(prev, stranded, notes, observed_fleets, now_dt, now_iso):
    """One run's bookkeeping, pure -> (record, digest_alarm_or_None, week_or_None).

    prev is a _stranded_record(). A fleet not in observed_fleets (no registry this run) keeps
    its ids/firstSeen/alertedAt exactly (D5). For observed fleets: firstSeen is kept for ids
    still stranded, set to now for new ones and dropped for the rest; an id's alertedAt
    outlives its exit from the set by STRANDED_REALERT_DAYS (D6), so a flapping exclusion
    re-alerts at most weekly. An id is NEW unless it has a fresh alertedAt; the digest is due
    when any id is new or lastAlerted is not fresh -- null, older than 7 days, in the future
    or unreadable (D7). Once nothing is left to protect, lastAlerted resets to null too.
    Delivery is NOT recorded here: see _mark_stranded_delivered()."""
    window = timedelta(days=STRANDED_REALERT_DAYS)

    def fresh(v):
        d = _parse_run_ts(v) if isinstance(v, str) else None
        return d is not None and d <= now_dt and now_dt - d <= window

    def unobserved(k):
        return k.split(":", 1)[0] not in observed_fleets

    cur = sorted({f"{s['fleet']}:{s['id']}" for s in stranded})
    first_seen = {k: v for k, v in prev["firstSeen"].items() if unobserved(k)}
    for k in cur:
        v = prev["firstSeen"].get(k)
        first_seen[k] = v if _parse_run_ts(v) is not None else now_iso
    alerted_at = {k: v for k, v in prev["alertedAt"].items() if unobserved(k) or k in cur or fresh(v)}
    ids = sorted({k for k in prev["ids"] if unobserved(k)} | set(cur))
    last = prev["lastAlerted"] if (ids or alerted_at) else None
    record = {"ids": ids, "firstSeen": first_seen, "alertedAt": alerted_at, "lastAlerted": last}
    if not cur:
        return record, None, None
    new_ids = [k for k in cur if not fresh(alerted_at.get(k))]
    due = bool(new_ids) or not fresh(last)
    seen = {k: _parse_run_ts(first_seen[k]) for k in cur}
    week = max(1, math.ceil((now_dt - min(seen.values())).total_seconds() / (7 * 86400)))
    digest = {"fleet": "stranded:digest", "alreadyAlarmed": not due,
              "reason": _stranded_digest_reason(stranded, seen, week, notes, new_ids)}
    return record, digest, week


def _mark_stranded_delivered(record, ids, now_iso):
    """After send_alert() CONFIRMED delivery only: stamp lastAlerted and every id the digest
    named. Never raises -- it runs between the send and save_state()."""
    try:
        record["lastAlerted"] = now_iso
        at = record.setdefault("alertedAt", {})
        for k in ids:
            at[k] = now_iso
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: stranded delivery bookkeeping failed ({_describe_exc(exc)})", file=sys.stderr)


def _stranded_digest_reason(stranded, seen, week, notes, new_ids=()):
    """The stranded:digest reason: headline (count, the earliest date this check first saw a
    task stranded, week N); every newly stranded id, UNCAPPED (D3); the no-intent list, oldest
    first, capped at STRANDED_DIGEST_MAX_LISTED then "..."; expired holds listed separately, one
    line per lapsed ruling; exclusions not applied; then the remedy. `seen` maps every
    "fleet:id" in `stranded` to its aware first-seen datetime. ASCII-only (see _ascii_safe):
    hold reasons and register errors are hand-written text."""
    cap = STRANDED_DIGEST_MAX_LISTED

    def key(s):
        return f"{s['fleet']}:{s['id']}"

    lines = [f"{len(stranded)} recurring task(s) disabled with no live recorded intent -- earliest first "
             f"stranded by this check {min(seen.values()).date().isoformat()}, week {week}."]
    if new_ids:
        lines.append(f"Newly stranded ({len(new_ids)}): " + ", ".join(new_ids))
    no_intent = sorted((s for s in stranded if s["reason"] != "hold-expired"),
                       key=lambda s: (seen[key(s)], key(s)))
    if no_intent:
        shown = ", ".join(f"{key(s)} (off since {seen[key(s)].date().isoformat()})" for s in no_intent[:cap])
        lines.append(f"No recorded intent ({len(no_intent)}): {shown}" + (", ..." if len(no_intent) > cap else ""))
    lapsed = {}
    for s in stranded:
        if s["reason"] == "hold-expired":
            lapsed.setdefault((s["fleet"], s["reviewBy"] or "?", s["holdReason"] or ""), []).append(key(s))
    for (fleet, review_by, why), keys in sorted(lapsed.items()):
        lines.append(f"Expired hold ({fleet}, reviewBy {review_by}, reason {why!r}) no longer covers "
                     f"{len(keys)}: " + ", ".join(keys[:cap]) + (", ..." if len(keys) > cap else ""))
    if notes:
        lines.append("Exclusions not applied (these excused nothing): " + "; ".join(notes))
    lines.append("Remedy, per task: record a hold in maintenance/_state/held-off.json "
                 "(fleet, id, reason, ruledBy, ruledOn, reviewBy) or re-enable it through the "
                 "register-scheduled-task skill.")
    return _ascii_safe("\n  ".join(lines))


def capture_pause_windows():
    """Observe both live registries into _state/fleet-pause-windows.json (see
    _shared/pause_windows.py). Module-level so tests can stub it -- main() must not
    write live state from a unit test. Never raises."""
    out = {"held": {}, "errors": []}
    try:
        spec = importlib.util.spec_from_file_location(
            "pause_windows", os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared", "pause_windows.py"))
        pw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pw)
        return pw.capture()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append("%s: %s" % (type(exc).__name__, exc))
        return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-enabled-ratio", type=float, default=0.10)
    parser.add_argument("--resume-grace-minutes", type=float, default=30)
    parser.add_argument("--marker-grace-minutes", type=float, default=20)
    args = parser.parse_args()

    # DURABLE PAUSE RECORD (2026-09-12). Observe both registries on EVERY run and extend
    # per-task "held" intervals (disabled AND named by a pending resume) in
    # _state/fleet-pause-windows.json. This guard is a native Windows task, so it keeps
    # running through a fleet pause -- the one observer guaranteed to see a pause whether or
    # not whoever paused the fleet remembered to write a ledger (the 09-07 pause had none).
    # Observation cadence = this task's cadence, so interval edges under-count by up to one
    # run (detectors alarm early, never late). health-guard-beacon.py and fleet-status.py
    # subtract the intervals from gaps. Fail-open: a capture error is printed, never raised.
    pause_capture = capture_pause_windows()

    registries = fleet_status.discover_registries()
    results = []
    tasks_by_fleet = {}
    for label, path in registries:
        tasks, _ = fleet_status.load(path)
        tasks_by_fleet[str(label).lower()] = tasks
        results.append(analyze_fleet(label, tasks))

    state = load_state()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    alarms = []
    # C8 (2026-11-05): send_alert() appends every attempt here; saved with the rest of the state.
    raw_log = state.get("_sendLog")
    send_log = [e for e in raw_log if isinstance(e, dict)][-SEND_LOG_MAX:] if isinstance(raw_log, list) else []
    state["_sendLog"] = send_log
    # Deliberate change (2026-11-05, see the module docstring): an ACTIVE "*" hold in held-off.json
    # also holds that fleet's fleet-ratio near-zero trip -- and nothing else.
    ratio_rulings = _fleet_rulings()
    ratio_held = []

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
        elif near_zero and not r["overdueResume"] and not r["hasResumeTask"] and prev_near_zero:
            trip = True
            reason = (f"enabled ratio {r['ratio']:.0%} ({r['enabledCount']}/{r['totalRecurring']}) for at least "
                       f"two consecutive checks, and no pending/overdue resume task exists for this fleet")

        ruling = ratio_rulings.get(str(fleet).lower()) if trip else None
        if ruling is not None:
            # held by a recorded fleet-wide ruling: book it as "not tripped", so the alarm re-arms
            # and sends as NEW the day the ruling lapses or is removed
            ratio_held.append({"fleet": fleet, "suppressed": reason, "reviewBy": ruling.get("reviewBy"),
                               "ruling": ruling.get("reason", "")})
            trip = False

        state.setdefault(fleet, {})
        state[fleet]["nearZero"] = near_zero
        state[fleet]["lastChecked"] = now_iso

        if trip:
            # NOTE: "alarmed" is deliberately NOT set here. It must only become True once
            # send_alert() actually confirms delivery (below) -- setting it eagerly, before
            # the send is even attempted, is what let a failed Outlook delivery permanently
            # suppress every later retry of a still-active alarm.
            already_alarmed = state[fleet].get("alarmed", False)
            alarms.append({"fleet": fleet, "reason": reason, "alreadyAlarmed": already_alarmed})
        else:
            state[fleet]["alarmed"] = False

    # General case (OI-202 follow-on, 2026-08-21): ANY one-time task with a
    # stale/incomplete task-progress-marker.py marker, not just a fleet
    # resume. Tracked per taskId so a persisting stall doesn't re-email every
    # 6h run, same pattern as the fleet-ratio alarms above.
    marker_state = state.setdefault("_markers", {})
    stalled = task_progress_marker.find_stalled(args.marker_grace_minutes)
    seen_marker_ids = set()
    for s in stalled:
        tid = s["taskId"]
        seen_marker_ids.add(tid)
        already_alarmed = marker_state.get(tid, {}).get("alarmed", False)
        # Same deferred-"alarmed" fix as the fleet-ratio alarms above: only lastChecked is
        # recorded here; "alarmed" is set later, only for markers whose alert actually sent.
        marker_state.setdefault(tid, {})
        marker_state[tid]["lastChecked"] = now_iso
        reason = (f"one-time task '{tid}' ({s['fleet']}) stalled at step {s['step']}/{s['totalSteps']} "
                  f"-- marker last updated {s['staleMinutes']} min ago (note={s['note']!r})")
        alarms.append({"fleet": f"marker:{tid}", "reason": reason, "alreadyAlarmed": already_alarmed})
    # a marker that's no longer stalled (completed, or its task got re-run) clears its own alarm state
    for tid in list(marker_state.keys()):
        if tid not in seen_marker_ids:
            marker_state[tid]["alarmed"] = False

    # Retire-pending resurrection (2026-08-22, register-scheduled-task v2.14). Same
    # per-key alarm bookkeeping as the markers above so a persisting resurrection
    # doesn't re-email every 6h run.
    rp_state = state.setdefault("_retirePending", {})
    resurrected = find_resurrected(tasks_by_fleet)
    seen_rp = set()
    for rp in resurrected:  # not `r` -- `results` reuses that name in the print loop below
        key = f"{rp['fleet']}:{rp['id']}"
        seen_rp.add(key)
        already_alarmed = rp_state.get(key, {}).get("alarmed", False)
        rp_state.setdefault(key, {})["lastChecked"] = now_iso
        reason = (f"retire-pending task '{rp['id']}' ({rp['fleet']}) is ENABLED again -- its retirement "
                  f"was ratified {rp['ratified']} but never executed, so this is a LIVE registration, "
                  f"not a retired one. On file: {rp['reason']!r}. Execute from: {rp['executeFrom']}.")
        alarms.append({"fleet": f"retire-pending:{key}", "reason": reason, "alreadyAlarmed": already_alarmed})
    # an entry that is disabled again (or whose retirement finally executed) clears its own alarm state
    for key in list(rp_state.keys()):
        if key not in seen_rp:
            rp_state[key]["alarmed"] = False

    # Incomplete resume (OI-273, 2026-09-12). Same per-key bookkeeping as retire-pending.
    ir_state = state.setdefault("_incompleteResume", {})
    seen_ir = set()
    try:
        incomplete = find_incomplete_resumes(tasks_by_fleet)
    except Exception as exc:  # noqa: BLE001 -- fail OPEN: an unanswerable check alarms, never kills the guard
        incomplete = []
        seen_ir.add("check-error")
        alarms.append({"fleet": "incomplete-resume:check-error",
                       "reason": f"incomplete-resume check could not run ({type(exc).__name__}: {exc}); "
                                 f"a partially-completed resume would be invisible this run",
                       "alreadyAlarmed": ir_state.get("check-error", {}).get("alarmed", False)})
        ir_state.setdefault("check-error", {})["lastChecked"] = now_iso
    for ir in incomplete:
        key = f"{ir['fleet']}:{ir['taskId']}"
        seen_ir.add(key)
        already_alarmed = ir_state.get(key, {}).get("alarmed", False)
        ir_state.setdefault(key, {})["lastChecked"] = now_iso
        shown = ", ".join(ir["disabled"][:12]) + (" ..." if len(ir["disabled"]) > 12 else "")
        reason = (f"resume task '{ir['taskId']}' ({ir['fleet']}) fired {ir['firedAt']} but "
                  f"{len(ir['disabled'])} of its {ir['listed']} listed ids are still disabled: {shown}. "
                  f"Its run status may say 'succeeded' -- the Desktop runner blocks unattended "
                  f"update_scheduled_task calls on a permission prompt (OI-273). Finish the resume "
                  f"from an attended session.")
        alarms.append({"fleet": f"incomplete-resume:{key}", "reason": reason, "alreadyAlarmed": already_alarmed})
    for key in list(ir_state.keys()):
        if key not in seen_ir:
            ir_state[key]["alarmed"] = False

    # STRANDED tasks (2026-11-05) -- see the module docstring. EVERYTHING after the registries were
    # read -- judging, record bookkeeping and the digest text -- runs inside this one try (D1):
    # any failure becomes the stranded:check-error alarm and can never skip the send or save.
    raw_st = state.get("_stranded")
    stranded, stranded_errors, stranded_week, stranded_ids, stranded_ok = [], [], None, [], False
    try:
        record = _stranded_record(raw_st)
        found, notes = find_stranded(tasks_by_fleet, held_by_pause=pause_capture.get("held"), now=now_dt)
        record, digest, week = _update_stranded(record, found, notes, set(tasks_by_fleet), now_dt, now_iso)
        ids = sorted({f"{s['fleet']}:{s['id']}" for s in found})
        # commit only after everything above succeeded
        stranded, stranded_errors, stranded_week, stranded_ids = found, notes, week, ids
        state["_stranded"] = record
        if digest is not None:
            alarms.append(digest)
        stranded_ok = True
    except Exception as exc:  # noqa: BLE001 -- fail OPEN: an unanswerable check alarms, never kills the guard
        kept = raw_st if isinstance(raw_st, dict) else {}
        prev_err = kept.get("checkError") if isinstance(kept.get("checkError"), dict) else {}
        alarms.append({"fleet": "stranded:check-error",
                       "reason": _ascii_safe(f"stranded-task check failed ({_describe_exc(exc)}); a recurring "
                                             f"task left disabled with no recorded intent would be invisible "
                                             f"this run"),
                       "alreadyAlarmed": prev_err.get("alarmed") is True})
        # the stranded record itself is left exactly as stored: this run could not judge it
        kept["checkError"] = dict(prev_err, lastChecked=now_iso)
        state["_stranded"] = kept

    new_alarms = [a for a in alarms if not a["alreadyAlarmed"]]

    if not args.json:
        for r in results:
            print(f"{r['fleet']:6s} ratio={r.get('ratio')} enabled={r.get('enabledCount')}/{r.get('totalRecurring')} overdueResume={r.get('overdueResume')}")
        print(f"markers: {len(stalled)} stalled" if stalled else "markers: none stalled")
        print(f"retire-pending: {len(resurrected)} resurrected of {len(load_retire_pending())} filed")
        print((f"stranded: {len(stranded)}" if stranded_ok else "stranded: ? (check error, see [ACTION])")
              + (f"; not applied: {' | '.join(stranded_errors)}" if stranded_errors else ""))
        for h in ratio_held:
            print(_ascii_safe(f"fleet-ratio: {h['fleet']} near-zero alarm held by ruling {str(h['fleet']).lower()}:* "
                              f"(reviewBy {h['reviewBy']}): {h['ruling']}"))
        held = pause_capture.get("held") or {}
        print("pause observation: held " + (", ".join(f"{f}={len(v)}" for f, v in sorted(held.items())) or "-")
              + (f"; ERRORS: {pause_capture['errors']}" if pause_capture.get("errors") else ""))
        if alarms:
            print(f"[ACTION] {len(alarms)} tripped: " + "; ".join(f"{a['fleet']}: {a['reason']}" for a in alarms))
        else:
            print("No fleet shows a stuck pause, no stalled progress markers, no retire-pending id re-enabled.")

    if new_alarms:
        subject = "[ORA] Fleet pause/resume guard - ALARM"
        if any(a["fleet"] == "stranded:digest" for a in new_alarms):
            subject += f" (stranded tasks: {len(stranded)}, week {stranded_week})"
        body_lines = ["Fleet pause/resume guard tripped (native, off-fleet check -- OI-202/WO-5).", ""]
        for a in new_alarms:
            body_lines.append(f"Source: {a['fleet']}")
            body_lines.append(f"Reason: {a['reason']}")
            body_lines.append("")
        body_lines.append("This does not auto-resume, auto-restart or auto-disable anything -- verify by hand. For a fleet-ratio alarm: resume the fleet or investigate why an automated resume didn't work. For a stalled-marker alarm: check the task's own instructions/session for where it stopped (see open-items-tracker.md#OI-202 for a real prior instance and register-scheduled-task/SKILL.md's progress-marker convention). For a retire-pending alarm: the id's ratified retirement has been reversed -- re-disable it on the named fleet and finish the retirement from the surface named in the alarm (archive-first-delete-second, ONE pass; see register-scheduled-task v2.14 RULES 3-4).")
        identifier = "; ".join(a["fleet"] for a in new_alarms)
        delivered = send_alert(subject, "\n".join(body_lines), identifier=identifier, send_log=send_log)
        # Only mark these as "alarmed" (suppressing future retries) once delivery actually
        # succeeded -- see send_alert's docstring and analyze_fleet's "alarmed" comment above.
        if delivered:
            for a in new_alarms:
                key = a["fleet"]
                if key.startswith("marker:"):
                    marker_state.setdefault(key[len("marker:"):], {})["alarmed"] = True
                elif key.startswith("incomplete-resume:"):
                    ir_state.setdefault(key[len("incomplete-resume:"):], {})["alarmed"] = True
                elif key == "stranded:digest":
                    # namespaced under _stranded, never a top-level key (cf. retire-pending below)
                    _mark_stranded_delivered(state["_stranded"], stranded_ids, now_iso)
                elif key == "stranded:check-error":
                    st = state.get("_stranded")
                    if isinstance(st, dict) and isinstance(st.get("checkError"), dict):
                        st["checkError"]["alarmed"] = True
                elif key.startswith("retire-pending:"):
                    # keyed "<fleet>:<id>" under _retirePending -- NOT a top-level fleet key,
                    # which is what the bare else below would have written.
                    rp_state.setdefault(key[len("retire-pending:"):], {})["alarmed"] = True
                else:
                    state.setdefault(key, {})["alarmed"] = True

    # printed AFTER the send so the report carries this run's own attempt in _sendLog (C8)
    if args.json:
        print(json.dumps({"results": results, "alarms": alarms, "stalledMarkers": stalled,
                          "resurrectedRetirePending": resurrected,
                          "stranded": stranded, "strandedErrors": stranded_errors,
                          "fleetRatioHeld": ratio_held, "_sendLog": send_log,
                          "pauseWindowCapture": pause_capture}, indent=2, default=str))
    else:
        print("last send: " + _describe_send(send_log[-1] if send_log else None))

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())

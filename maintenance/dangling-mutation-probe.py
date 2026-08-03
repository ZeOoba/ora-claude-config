#!/usr/bin/env python3
"""Detect scheduled-task work that was LOST without anyone noticing.

Two independent checks, both born from the 2026-08-03 incident in which the
one-time task `ora-appsec-siteexposure-canary-recheck` reached the correct
conclusion, called `update_scheduled_task` to retag `ora-site-exposure-probe`
-- and then died. That tool call was the LAST row of its transcript: the
session ended before any tool_result came back, so the write never landed.
The task then self-disabled on schedule and read as cleanly "completed".
Five days passed with the registry still carrying the stale tag and nothing,
anywhere, flagging it.

The general lesson: A TASK WHOSE FINAL ACT IS A WRITE HAS NO WITNESS THAT THE
WRITE SUCCEEDED. A self-disabling one-time task cannot even be re-run to find
out. Neither the scheduler, the session store, nor any existing probe models
"intended to write" as distinct from "wrote".

CHECK A -- dangling mutation (ALARM).
  A tool_use with no matching tool_result is "dangling". Scoped hard, because
  breadth here is noise: only a MUTATING tool, only when the session died at
  that call (rows_after == 0), only for sessions that are not still running.
  Calibrated against a full scan of 186 scheduled-task transcripts on
  2026-08-03: 8 sessions had some dangling call, but only 1 satisfied all
  three conditions -- the incident itself. Zero historical false positives.
  Sessions that continued PAST a dangling mutation (rows_after > 0) had the
  opportunity to notice and recover, so they are INFO, not alarm.

CHECK B -- uncollected observation (ALARM after a grace period).
  Catches the same failure by its CONSEQUENCE rather than its mechanism, which
  matters because transcripts are pruned (only 186 of 373 scheduled-task
  sessions still had one on 2026-08-03 -- Check A is structurally blind to the
  other half). If a task's MODEL tag is a real id observed BEFORE the current
  model-lineup anchor, and the task has since fired, then fresh observable
  evidence exists and was never collected. Flagged only once that fire is
  older than `grace_days`, so a normal same-week re-canary is never nagged.

NEITHER CHECK EVER WRITES. Report-only, exit non-zero on findings.

Missing transcripts are reported as UNVERIFIABLE, never folded into "clean" --
a zero that could mean "couldn't look" is a failure, not a pass.

Run: python dangling-mutation-probe.py [--lookback-days 14] [--grace-days 7]
Exit 0 = clean, 1 = findings, 2 = probe could not run its own checks.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: discovery returns None, main() reports and exits 2

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STATE_DIR = os.path.join(HERE, "_state")
LOG = os.path.join(STATE_DIR, "dangling-mutation.log")
# Reviewed-and-cleared findings. Same bar as ora-appsec-sweep's suppressions.md:
# entries are added deliberately, with a reason, not to quiet a noisy run.
ACK_FILE = os.path.join(HERE, "_shared", "dangling-mutation-acknowledged.json")
PROJECTS_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")
LINEUP_REF = os.path.join(
    PROJECTS_ROOT, "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
    "memory", "reference_model_release_checklist.md")

# Bare (non-MCP) tool names that mutate. Exact match -- substring matching here
# would catch unrelated MCP tools whose names merely contain "Write"/"Edit".
MUTATING_EXACT = frozenset(("Write", "Edit", "NotebookEdit"))

# Substrings that identify a mutating MCP tool. Each is specific enough not to
# collide with its read-only sibling: "update_scheduled_task" does not appear
# inside "list_scheduled_tasks", and "manage_crm_objects" does not appear
# inside "search_crm_objects". Add here when a new mutating connector lands.
MUTATING_SUBSTRINGS = (
    "update_scheduled_task", "create_scheduled_task", "delete_scheduled_task",
    "archive_session", "set_session_title", "send_message",
    "notion-create", "notion-update", "notion-move", "notion-duplicate",
    "notion-append", "manage_crm_objects", "manage_campaign_objects",
    "manage_landing_page", "form_input", "write_clipboard", "file_upload",
    "upload_image", "write_file", "edit_block", "move_file", "create_directory",
)

# Bash is opaque -- a dangling shell call may be a git commit or an `ls`.
# Classify by command text. Precision matters more than recall: a missed
# mutating shell command costs one undetected finding, whereas treating every
# dangling shell read as a lost write would have produced a false alarm on the
# real ora-am-brief curl call and trained everyone to ignore this probe.
_BASH_MUTATION_RES = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bgit\s+(add|commit|push|rm|mv|reset|checkout|merge|rebase|stash|tag|apply)\b",
    r"send-via-outlook",
    r"append-event-log",
    r"\brm\b", r"\bmv\b", r"\bmkdir\b", r"\btouch\b", r"\btee\b",
    r"\bnpm\s+publish\b", r"\bnetlify\s+deploy\b",
    # A write redirect. Excludes, via the lookbehind/lookahead: `2>&1` (stderr
    # dup), `>=` (comparison), `->` and `=>` (arrows, extremely common inside
    # read-only format strings and comments). `>>` still matches, correctly --
    # appending is a write. A false hit here is not free: it would promote a
    # dangling shell READ into a LOST_WRITE alarm.
    r"(?<![0-9\-=])>(?![=&])",
))


def is_mutating(tool_name, tool_input):
    """True if this tool call could have changed state. Pure."""
    if not tool_name:
        return False
    if tool_name in MUTATING_EXACT:
        return True
    lowered = tool_name.lower()
    if any(s in lowered for s in MUTATING_SUBSTRINGS):
        return True
    if tool_name == "Bash":
        cmd = (tool_input or {}).get("command") or ""
        return any(r.search(cmd) for r in _BASH_MUTATION_RES)
    return False


def find_dangling(rows):
    """Tool calls in a transcript with no matching tool_result.

    Returns [{'id','name','input','idx','rows_after'}] sorted by position.
    `rows_after` is how many transcript rows follow the call -- 0 means the
    session ended right there, which is the signature of a lost write.
    Malformed rows are skipped rather than raised. Pure.
    """
    if not rows:
        return []
    last = len(rows) - 1
    used, got = {}, set()
    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        msg = r.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if r.get("type") == "assistant":
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    used[b.get("id")] = (b.get("name"), b.get("input"), idx)
        elif r.get("type") == "user":
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    got.add(b.get("tool_use_id"))
    out = [{"id": k, "name": n, "input": i, "idx": ix, "rows_after": last - ix}
           for k, (n, i, ix) in used.items() if k not in got]
    return sorted(out, key=lambda d: d["idx"])


def classify_findings(sessions, live_session_ids, acknowledged=None):
    """Split dangling calls into (alarms, infos).

    `sessions`: [{'task_id','session_id','dangling':[{name,input,rows_after}]}].

    A session in `live_session_ids` is skipped entirely -- a running session
    ALWAYS has an unresolved final tool call (the one still executing), so
    without this the probe flags itself, and every concurrently-firing task,
    on every single run. This was not theoretical: the first live run flagged
    a LOST_WRITE against `ora-doctrine-integrity-guard` that was simply a
    session mid-flight.

    A session id in `acknowledged` is downgraded to info: the finding was
    reviewed and the write either landed or was re-applied by hand. Without
    this, a correctly-reported-and-since-fixed incident re-alarms every day
    until it ages out of the lookback window, which is how a good detector
    trains its audience to ignore it. Pure.
    """
    alarms, infos = [], []
    acked = acknowledged or set()
    for s in sessions or []:
        if s.get("session_id") in (live_session_ids or set()):
            continue
        for d in s.get("dangling") or []:
            rec = {"task_id": s.get("task_id"), "session_id": s.get("session_id"),
                   "tool": d.get("name"), "rows_after": d.get("rows_after")}
            mutating = is_mutating(d.get("name"), d.get("input"))
            if mutating and (d.get("rows_after") or 0) == 0:
                if s.get("session_id") in acked:
                    rec["why_not_alarm"] = "acknowledged (reviewed; write verified or re-applied)"
                    infos.append(rec)
                else:
                    alarms.append(rec)
            else:
                rec["why_not_alarm"] = ("session continued past the call"
                                        if mutating else "non-mutating tool")
                infos.append(rec)
    return alarms, infos


def load_acknowledged(path):
    """Set of session ids reviewed and cleared, from a JSON list of
    {'session_id','reason','acknowledged'} records. Missing file -> empty set
    (fail-open: an unreadable ack file must never suppress an alarm)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return set()
    out = set()
    for rec in (data if isinstance(data, list) else []):
        if isinstance(rec, dict) and rec.get("session_id"):
            out.add(rec["session_id"])
    return out


_TAG_RE = re.compile(r"\[MODEL:\s*([^\]]*)\]")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_model_tag(description):
    """(value, date_or_None) from the LAST bracketed MODEL tag, or None.

    LAST, not first: descriptions on this fleet carry long changelogs that can
    legitimately quote an earlier example tag, and a first-match read grades
    the task on prose instead of its real trailing tag (STEP 2.5 hardening,
    2026-07-24). Pure.
    """
    if not description:
        return None
    tags = _TAG_RE.findall(description)
    if not tags:
        return None
    body = tags[-1]
    if "|" in body:
        value, _, right = body.partition("|")
        m = _DATE_RE.search(right)
        return (value.strip(), m.group(1) if m else None)
    return (body.strip(), None)


def _to_datetime(value):
    """Naive UTC datetime from an epoch-ms/epoch-s NUMBER or an ISO-8601
    STRING, else None.

    The two files this probe reads disagree on timestamp encoding, in the
    same tree: session metadata writes createdAt/lastActivityAt as epoch
    MILLISECONDS (integers), while the registry writes lastRunAt as an
    ISO-8601 Z string. (The list_scheduled_tasks / get_session MCP tools
    render both as ISO, which hides the split from anyone who only ever
    reads through the tools.) Handling one encoding and not the other does
    not error -- it silently returns None and disables whichever check
    depended on it. That is exactly what happened on this probe's first live
    run, 2026-08-03: the lookback filter degraded to "scan all history" and
    live-session exclusion never fired once. Pure.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v <= 0:
            return None
        if v > 1e11:          # >1e11 can only be milliseconds for any sane date
            v /= 1000.0
        try:
            return datetime.datetime.fromtimestamp(
                v, datetime.timezone.utc).replace(tzinfo=None)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip().rstrip("Z")
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.datetime.strptime(s[:26], fmt)
            except Exception:
                pass
        try:
            return datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        except Exception:
            return None
    return None


def _as_date(value):
    """Timestamp (either encoding) -> 'YYYY-MM-DD', or None. Pure."""
    dt = _to_datetime(value)
    return dt.date().isoformat() if dt else None


def _days_between(later, earlier):
    a = datetime.datetime.strptime(later, "%Y-%m-%d")
    b = datetime.datetime.strptime(earlier, "%Y-%m-%d")
    return (a - b).days


def uncollected_observations(tasks, anchor_date, today=None, grace_days=7):
    """Enabled recurring tasks whose MODEL observation is older than the
    lineup anchor but which have FIRED since -- i.e. fresh evidence exists and
    nobody collected it. Flagged only once that fire is `grace_days` old.

    Exemptions mirror STEP 2.5's ratified scope filter: one-time and disabled
    tasks are out of scope, and UNVERIFIABLE is its own expected baseline
    bucket, never a re-canary candidate. Pure.
    """
    # UTC, matching the registry's ISO-Z lastRunAt. Local `today` would skew
    # the age arithmetic by the tz offset across a day boundary.
    today = today or datetime.datetime.now(
        datetime.timezone.utc).date().isoformat()
    out = []
    for t in tasks or []:
        if not t.get("enabled"):
            continue
        if not t.get("cronExpression") or t.get("fireAt"):
            continue  # one-time tasks are exempt
        last_run = _as_date(t.get("lastRunAt"))
        if not last_run:
            continue  # never run, or unparseable -- nothing to collect
        tag = parse_model_tag(t.get("description"))
        if not tag:
            continue  # untagged is STEP 2.5's own separate bucket
        value, tag_date = tag
        if "UNVERIFIABLE" in (value or "").upper():
            continue
        if tag_date and tag_date >= anchor_date:
            continue  # already settled against the current lineup
        if last_run <= anchor_date:
            continue  # no post-anchor fire, so no new evidence exists
        if _days_between(today, last_run) < grace_days:
            continue  # inside the grace window
        out.append({"id": t.get("id"), "tag": value, "tag_date": tag_date,
                    "last_run": last_run,
                    "age_days": _days_between(today, last_run)})
    return out


def read_registry_tasks(path):
    """[{'id','description','enabled','cronExpression','fireAt','lastRunAt'}]
    from a scheduled-tasks.json, or None if unreadable. Read-only."""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    return [{"id": t.get("id"), "description": t.get("description") or "",
             "enabled": bool(t.get("enabled")),
             "cronExpression": t.get("cronExpression"),
             "fireAt": t.get("fireAt"), "lastRunAt": t.get("lastRunAt")}
            for t in (d.get("scheduledTasks") or [])]


def read_lineup_anchor(path=LINEUP_REF):
    """The 'Current lineup as of YYYY-MM-DD' date, or None if unreadable."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if "lineup as of" in line.lower():
                    m = _DATE_RE.search(line)
                    if m:
                        return m.group(1)
    except Exception:
        return None
    return None


def _transcript_for(cli_session_id):
    if not cli_session_id:
        return None
    hits = glob.glob(os.path.join(PROJECTS_ROOT, "*", "%s.jsonl" % cli_session_id))
    return hits[0] if hits else None


def collect_sessions(session_dir, lookback_days, live_window_minutes, now=None):
    """(sessions, live_ids, unverifiable) for scheduled-task sessions created
    within the lookback window. `unverifiable` counts sessions whose transcript
    is gone (pruned) -- reported, never silently treated as clean."""
    # UTC throughout: epoch timestamps decode to UTC, so a local `now` would
    # skew every comparison by the tz offset (4h on this machine).
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    cutoff = now - datetime.timedelta(days=lookback_days)
    live_cutoff = now - datetime.timedelta(minutes=live_window_minutes)
    sessions, live_ids, unverifiable = [], set(), []
    examined = 0
    for f in glob.glob(os.path.join(session_dir, "local_*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
        except Exception:
            continue
        task_id = meta.get("scheduledTaskId")
        if not task_id:
            continue
        created = _to_datetime(meta.get("createdAt"))
        # No parseable createdAt => cannot place it in the window. Skip rather
        # than scan, but count it as unverifiable so it is never read as clean.
        if created is None:
            unverifiable.append((task_id, "unparseable-createdAt"))
            continue
        if created < cutoff:
            continue
        examined += 1
        sid = meta.get("sessionId") or os.path.basename(f)[:-5]
        # A session still being written to is "live": its final tool call has
        # simply not returned YET. Treating it as a finding self-flags forever.
        last_act = _to_datetime(meta.get("lastActivityAt"))
        if last_act and last_act >= live_cutoff:
            live_ids.add(sid)
        tpath = _transcript_for(meta.get("cliSessionId"))
        if not tpath:
            unverifiable.append((task_id, sid))
            continue
        try:
            with open(tpath, encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh if l.strip()]
        except Exception:
            unverifiable.append((task_id, sid))
            continue
        dang = find_dangling(rows)
        if dang:
            sessions.append({"task_id": task_id, "session_id": sid, "dangling": dang})
    return sessions, live_ids, unverifiable, examined


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=14)
    ap.add_argument("--grace-days", type=int, default=7)
    # 120 min, not 20. `lastActivityAt` stops advancing while a session is
    # BLOCKED on a single long tool call (a gated push running the full
    # pre-push suite, a long agent dispatch, a big test run), so a short window
    # ages a still-running session out and reports its in-flight call as a lost
    # write. Observed live 2026-08-03: consecutive runs minutes apart disagreed,
    # exit 1 then exit 0, purely from sessions crossing a 20-minute boundary.
    # Detection latency is free here -- the guard runs daily and a genuinely
    # lost write does not heal itself -- whereas a false alarm costs the
    # probe's credibility permanently.
    ap.add_argument("--live-window-minutes", type=int, default=120)
    a = ap.parse_args()

    if _sd is None:
        print("[ERROR] store_discovery unavailable -- cannot locate the CC store.")
        return 2
    # store_name() first: discover_store() takes a STORE NAME
    # ('claude-code-sessions'), not the 'cc' label. Passing the label straight
    # through silently returns None -- the same regression
    # task-folder-registration-probe hit, which is why its test suite pins
    # store_name()'s mapping.
    store = _sd.store_name("cc")
    registry = _sd.discover_store(store) if store else None
    if not registry or not os.path.exists(registry):
        print("[ERROR] CC scheduled-task registry not found -- checks did not run.")
        return 2
    session_dir = os.path.dirname(registry)

    sessions, live_ids, unverifiable, examined = collect_sessions(
        session_dir, a.lookback_days, a.live_window_minutes)
    alarms, infos = classify_findings(sessions, live_ids, load_acknowledged(ACK_FILE))

    tasks = read_registry_tasks(registry)
    anchor = read_lineup_anchor()
    uncollected, anchor_note = [], ""
    if tasks is None:
        anchor_note = "registry unreadable -- CHECK B DID NOT RUN"
    elif not anchor:
        anchor_note = "lineup anchor unreadable -- CHECK B DID NOT RUN"
    else:
        uncollected = uncollected_observations(tasks, anchor, grace_days=a.grace_days)

    print("dangling-mutation-probe  lookback=%dd  in_window=%d  with_dangling=%d  "
          "live_excluded=%d" % (a.lookback_days, examined, len(sessions), len(live_ids)))
    for r in alarms:
        print("[ACTION] LOST_WRITE task=%s session=%s tool=%s -- session ended AT this "
              "call; the write may never have landed. Verify the intended change is "
              "actually present, then re-apply it." % (r["task_id"], r["session_id"], r["tool"]))
    for r in uncollected:
        print("[ACTION] UNCOLLECTED_OBSERVATION task=%s tag=%s (dated %s) fired %s "
              "(%dd ago, past the %dd grace) -- fresh evidence exists and was never "
              "collected." % (r["id"], r["tag"], r["tag_date"] or "UNDATED",
                              r["last_run"], r["age_days"], a.grace_days))
    for r in infos:
        print("  [info] dangling %s in %s (%s; rows_after=%d)"
              % (r["tool"], r["task_id"], r["why_not_alarm"], r["rows_after"]))
    if unverifiable:
        print("  [unverifiable] %d session(s) had no transcript on disk (pruned) -- "
              "Check A could not inspect them; this is NOT a clean result for those."
              % len(unverifiable))
    if anchor_note:
        print("  [unverifiable] %s" % anchor_note)
    if not alarms and not uncollected:
        print("OK -- no lost writes or uncollected observations.")

    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s scanned=%d lost_writes=%d uncollected=%d info=%d "
                     "unverifiable=%d live_excluded=%d%s\n"
                     % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        len(sessions), len(alarms), len(uncollected), len(infos),
                        len(unverifiable), len(live_ids),
                        (" note=" + anchor_note) if anchor_note else ""))
    except Exception as exc:
        print("  [warn] could not append to %s: %s" % (LOG, exc))

    return 1 if (alarms or uncollected) else 0


if __name__ == "__main__":
    sys.exit(main())

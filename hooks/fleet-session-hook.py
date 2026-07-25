#!/usr/bin/env python
"""
fleet-session-hook.py - Mirrors live Claude Code in-session activity into the Obsidian vault.

Wired into settings.json hooks (SessionStart, PostToolUse[Bash|Task|TaskCreate|TaskUpdate], Stop, SessionEnd).
Each invocation:
  - Updates the aggregated "Claude Session Tasks.md" (all active sessions)
  - Creates/updates a per-session note in Sessions/YYYY-MM-DD_<short-id>.md
  - Tracks in-session TaskCreate/TaskUpdate items per session note

Extended 2026-06-11: per-session notes + task tracking.
Always exits 0 — never blocks a tool call.

PER-SESSION-FILE STORAGE (2026-07-24, replaces a shared-file + lock design). Every
invocation used to do a full read-modify-write of ONE shared session-state.json:
load, mutate only THIS session's own entry, write the WHOLE file back. Even with an
atomic rename, that meant every session's hook invocation raced every OTHER session's
invocation over the SAME file -- fixed for one release with a short-timeout mutex
(state_lock()), but a lock is a workaround for a shared-file design, not the actual
fix. The actual fix: each session gets its OWN file
(SESSIONS_STATE_DIR/<sanitized-sid>.json). A hook invocation only ever reads and
writes ITS OWN session's STATE file -- there is no shared STATE file left to race
over CROSS session, which was the actual, measured, production bug (10 of 12
concurrent sessions lost data under the old design; this fix's own test drives 20
concurrent distinct sessions and loses none). render() (the aggregated dashboard)
becomes a READ-ONLY aggregation across all current session files at render time,
computed fresh on every invocation; a partially-written file is never visible thanks
to the same atomic-rename pattern already used elsewhere in this file. Scoped claim,
not absolute: render()'s own OUT file and write_session_note()'s per-session NOTE
file still go through a fixed (not per-invocation-unique) ".tmp" path each -- unlike
the state files above, these are cosmetic OUTPUT artifacts (the dashboard / a
per-session note), not this hook's source of truth, so a torn or dropped write there
self-heals on the very next invocation and was equally possible under the old
locked design (render() ran outside state_lock() there too) -- not a regression, and
deliberately not hardened further here.

KNOWN, ACCEPTED RESIDUAL (formal review, 2026-07-24) -- "there is nothing left to
lock" is true CROSS-session but NOT same-session: two hook invocations for the SAME
session_id (realistic here -- parallel subagent tool completions and a background
Bash task's own events can fire while the parent session's foreground events also
fire, all under one session_id) still do a load-modify-save on that ONE session's
OWN file, and CAN race each other. Live-verified: 11 of 12 concurrent same-session
TaskCreate events lost their own task entry. Deliberately NOT fixed with a
per-session lock (that would partially reopen exactly what this redesign exists to
close, and the blast radius here is strictly smaller and different in kind than the
bug this redesign fixes): consequence is bounded to lost/stale task, activity, or
feed entries in a COSMETIC observability mirror -- `status`/`lastAt`/`cwd` (the
fields hooks/lib/session_liveness.py's two consumers actually depend on) always
reflect at least ONE recent write and self-correct on the very next event; nothing
here is durable data, and neither downstream guard reads task-level detail. Two
concrete correctness risks this DOES carry, beyond the accepted stale-overwrite race,
are closed below (see save_session()): two same-session writers racing on the SAME
"path + '.tmp'" name (which could corrupt a write rather than merely lose one) is
closed via a per-invocation-unique tmp name; and two same-session writers' os.replace()
calls landing on the SAME destination path at nearly the same moment -- empirically
observed as a transient WinError under 12-way same-session concurrency, which without
mitigation silently drops that writer's update AND leaves its tmp file behind as
litter -- is closed via a short bounded retry, with the tmp file removed on the rare
case every retry is exhausted.

SessionEnd does NOT delete its own file (an earlier version of this fix did, which
had two problems found in the same review: it destroyed that session's
recent-activity feed contribution INSTANTLY on every ordinary clean exit rather than
after the same SESSION_PRUNE_H window every other session gets, and closing the file
immediately is also just unnecessary -- the file's "ended" status is already exactly
what a reader needs). Instead it marks status="ended" and lets the SAME
SESSION_PRUNE_H-based cleanup that already runs (as a side effect of render()'s
directory scan) delete it later, same as any other session. Both render()'s own
"Active sessions" table AND hooks/lib/session_liveness.py's reader explicitly
exclude status="ended" sessions -- an ended session's file persisting a while longer
for feed/history purposes must never make it look ACTIVE to the two guards that
depend on file-presence meaning "still open". KNOWN EXCEPTION (same review pass):
a same-session straggler write landing AFTER SessionEnd's -- the accepted
stale-overwrite race two paragraphs up -- can flip status back away from "ended",
making that already-finished session look open again to both consumers until the
next SESSION_PRUNE_H sweep notices its stale lastAt. Same bounded-blast-radius
reasoning as the rest of this residual: commit-provenance-guard.py's hard block has
its own override escape hatch, shared-checkout-guard.py is warn-only, and this
exact resurrection was equally possible under the old locked design (a serialized
straggler event's own load-modify-save would resurrect a just-deleted entry there
too) -- not a regression introduced by this redesign.

Two OTHER hooks (commit-provenance-guard.py, shared-checkout-guard.py) read this
mirror's output via hooks/lib/session_liveness.py's other_active_sessions() -- that
module's PUBLIC function signature and return shape are UNCHANGED by this migration;
only its internal storage format preference changed (prefers this new per-session
directory when present, falls back to the old single-file format otherwise), so
neither guard nor their existing tests needed any changes.
"""
import sys, os, json, datetime, time

SESSIONS_STATE_DIR = os.environ.get("ORA_FLEET_SESSIONS_DIR") or \
    r"C:\Users\Owner\.claude\obsidian-fleet-mirror\session-state.d"
OUT          = os.environ.get("ORA_OBSIDIAN_OUT") or r"C:\Users\Owner\Obsidian\BrainVault\_Claude\Claude Session Tasks.md"
SESSIONS_DIR = os.environ.get("ORA_OBSIDIAN_SESSIONS") or r"C:\Users\Owner\Obsidian\BrainVault\_Claude\Sessions"

FEED_CAP        = 20
SESSION_PRUNE_H = 6
WORKING_MIN     = 5
RECENT_MIN      = 15
ACTIVITY_CAP    = 50
RENAME_RETRIES    = 6
RENAME_RETRY_S    = 0.05


def now():
    return datetime.datetime.now()


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def parse(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def rel(dt):
    if dt is None:
        return "?"
    secs = (now() - dt).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return "%dm ago" % int(secs // 60)
    if secs < 86400:
        return "%dh ago" % int(secs // 3600)
    return "%dd ago" % int(secs // 86400)


def _safe_filename(sid):
    """Filesystem-safe encoding of a session_id for use as a per-session filename.
    Claude Code session_ids are UUID-shaped (already filesystem-safe) -- this is
    defense-in-depth, not a format assumption."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in (sid or "unknown"))
    return safe + ".json"


def session_file_path(sid):
    return os.path.join(SESSIONS_STATE_DIR, _safe_filename(sid))


def load_session(sid):
    """This session's OWN state -- its own file, never touched by any other session's
    hook invocation, so there is nothing to race over. A missing/unreadable file (first
    event of a new session, or any corruption) starts fresh -- same fail-open posture
    as the rest of this hook."""
    try:
        with open(session_file_path(sid), "r", encoding="utf-8") as f:
            s = json.load(f)
        s.setdefault("tasks", [])
        s.setdefault("activity", [])
        s.setdefault("feed_events", [])
        return s
    except Exception:
        return {"started": iso(now()), "tasks": [], "activity": [], "feed_events": []}


def save_session(sid, s):
    """Write THIS session's own file. No shared file, no lock: only processes handling
    THIS session's hook events ever write this specific path -- but that CAN be more
    than one process at once (see the module docstring's KNOWN, ACCEPTED RESIDUAL: a
    parallel subagent's tool completion and the parent's own foreground event, both
    tagged with the same session_id). The tmp filename includes this process's own PID
    so two such concurrent writers never share one tmp path -- a torn/corrupt tmp file
    is no longer possible. os.replace(tmp, path) itself can still hit a transient
    WinError (another same-session writer's own os.replace onto the SAME destination
    path, mid-flight) -- empirically observed under 12-way same-session concurrency, so
    it is retried a few times with a short delay rather than assumed to always succeed
    outright. If every retry is exhausted the tmp file is removed rather than left
    behind as litter, and this writer's update is lost -- the accepted, bounded part of
    the residual (see module docstring); the exception is re-raised so the caller's own
    fail-open `except Exception: pass` remains the single place that decision is made."""
    os.makedirs(SESSIONS_STATE_DIR, exist_ok=True)
    s["_sid"] = sid  # let list_all_sessions() recover the true id even if _safe_filename
                      # ever had to alter it (defense-in-depth, not a format assumption)
    path = session_file_path(sid)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f)
    last_err = None
    for attempt in range(RENAME_RETRIES):
        try:
            os.replace(tmp, path)
            return
        except OSError as e:
            last_err = e
            if attempt < RENAME_RETRIES - 1:
                time.sleep(RENAME_RETRY_S)
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise last_err


def delete_session_file(sid):
    try:
        os.remove(session_file_path(sid))
    except Exception:
        pass


def list_all_sessions():
    """(sid, s) for every session file currently on disk -- a live, read-only
    snapshot. Never raises: a missing directory (no session has ever run) or an
    unreadable/mid-write individual file (skipped, not fatal -- the NEXT render picks
    it up once the writer's atomic rename completes) both degrade gracefully."""
    out = []
    try:
        names = os.listdir(SESSIONS_STATE_DIR)
    except Exception:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_STATE_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                s = json.load(f)
        except Exception:
            continue
        if not isinstance(s, dict):
            continue
        sid = s.get("_sid") or name[:-5]
        out.append((sid, s))
    return out


def short(sid):
    return (sid or "unknown")[:8]


def trunc(s, n=70):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def add_feed_local(s, kind, detail):
    """This session's own contribution to the GLOBAL recent-activity feed, stored
    INSIDE this session's own file (not a separate shared list) -- render() aggregates
    every session's feed_events at render time, so this never touches another
    session's data or a shared file."""
    s.setdefault("feed_events", []).insert(0, {
        "at": iso(now()), "kind": kind, "detail": trunc(detail),
    })
    del s["feed_events"][FEED_CAP:]


def add_activity(s, detail):
    s.setdefault("activity", []).insert(0, {
        "at": iso(now()), "detail": trunc(detail, 80),
    })
    del s["activity"][ACTIVITY_CAP:]


def upsert_task(s, task_id, title=None, status=None):
    tasks = s.setdefault("tasks", [])
    for t in tasks:
        if t.get("id") == task_id:
            if title is not None:
                t["title"] = title
            if status is not None:
                t["status"] = status
            return
    tasks.append({
        "id": task_id,
        "title": title or "(untitled)",
        "status": status or "pending",
        "created": iso(now()),
    })


def get_session_note_path(sid, s):
    started = s.get("started", "")
    started_dt = parse(started)
    date_str = started_dt.strftime("%Y-%m-%d") if started_dt else now().strftime("%Y-%m-%d")
    return os.path.join(SESSIONS_DIR, "%s_%s.md" % (date_str, short(sid)))


def render_session_note(sid, s):
    started = s.get("started", "")
    started_dt = parse(started)
    started_display = started_dt.strftime("%Y-%m-%d %H:%M") if started_dt else "?"
    cwd_val = s.get("cwd", "")
    cwd_short = os.path.basename(cwd_val.rstrip("/\\")) or cwd_val or "-"
    status = s.get("status", "active")
    tasks = s.get("tasks", [])
    # activity is newest-first; render in chronological order
    activity = list(reversed(s.get("activity", [])))

    lines = [
        "---",
        "session_id: %s" % short(sid),
        "started: %s" % started_display,
        "cwd: %s" % cwd_short,
        "status: %s" % status,
        "---",
        "# Session %s — %s" % (short(sid), started_display),
        "",
        "## Tasks",
        "",
    ]

    if tasks:
        for t in tasks:
            st = t.get("status", "pending")
            if st == "completed":
                checkbox = "[x]"
                label = t.get("title", "?")
            elif st == "in_progress":
                checkbox = "[-]"
                label = t.get("title", "?") + " *(in progress)*"
            else:
                checkbox = "[ ]"
                label = t.get("title", "?")
            lines.append("- %s %s" % (checkbox, label))
    else:
        lines.append("*(no tasks created this session)*")

    lines.append("")
    lines.append("## Activity")
    lines.append("")

    if activity:
        for a in activity[-25:]:
            at_dt = parse(a.get("at", ""))
            ts = at_dt.strftime("%H:%M") if at_dt else "?"
            lines.append("- `%s` %s" % (ts, a.get("detail", "")))
    else:
        lines.append("*(session started)*")

    lines.append("")
    lines.append("---")
    lines.append("*Auto-generated by `fleet-session-hook.py`. Do not edit.*")

    return "\n".join(lines) + "\n"


def write_session_note(sid, s):
    try:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        path = get_session_note_path(sid, s)
        content = render_session_note(sid, s)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        pass


def render():
    n = now()
    lines = []
    lines.append("---")
    lines.append("updated: " + n.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("---")
    lines.append("# Claude Sessions — Live Activity")
    lines.append("")

    # Prune stale session FILES as a side effect of this same directory scan (matches
    # the original design's cadence -- once per invocation -- without a second pass).
    cutoff = n - datetime.timedelta(hours=SESSION_PRUNE_H)
    kept = []
    for sid, s in list_all_sessions():
        last = parse(s.get("lastAt", ""))
        if last is None or last < cutoff:
            delete_session_file(sid)
            continue
        kept.append((sid, s, last))

    # A status="ended" session's file persists (not deleted -- see module docstring)
    # so its recent-activity feed survives, but it must NEVER show as "active": that
    # would misrepresent a cleanly-finished session as still open.
    active = []
    for sid, s, last in kept:
        if s.get("status") == "ended":
            continue
        mins = (n - last).total_seconds() / 60.0
        if mins <= RECENT_MIN:
            active.append((sid, s, last, mins))
    active.sort(key=lambda x: x[2], reverse=True)

    if active:
        lines.append("## Active sessions (%d)" % len(active))
        lines.append("")
        lines.append("| Session | State | Folder | Tasks | Last action | When |")
        lines.append("|---------|-------|--------|-------|-------------|------|")
        for sid, s, last, mins in active:
            if s.get("status") == "idle":
                state_lbl = "idle"
            elif mins <= WORKING_MIN:
                state_lbl = "**working**"
            else:
                state_lbl = "recent"
            folder = os.path.basename(str(s.get("cwd", "")).rstrip("\\/")) or "-"
            tasks = s.get("tasks", [])
            done = sum(1 for t in tasks if t.get("status") == "completed")
            task_str = "%d/%d" % (done, len(tasks)) if tasks else "-"
            lines.append("| `%s` | %s | %s | %s | %s | %s |" % (
                short(sid), state_lbl, folder, task_str,
                trunc(s.get("lastTool", "-"), 40), rel(last)))
        lines.append("")
    else:
        lines.append("> No active Claude Code sessions in the last %d minutes." % RECENT_MIN)
        lines.append("")

    # Recent-activity feed: aggregated fresh, every render, from every KEPT (not yet
    # pruned) session's own feed_events -- no shared list to maintain incrementally.
    feed_entries = []
    for sid, s, last in kept:
        for e in s.get("feed_events", []):
            feed_entries.append({
                "at": e.get("at", ""), "sid": short(sid),
                "kind": e.get("kind", ""), "detail": e.get("detail", ""),
            })
    feed_entries.sort(key=lambda e: e.get("at", ""), reverse=True)
    feed = feed_entries[:FEED_CAP]

    if feed:
        lines.append("## Recent activity")
        lines.append("")
        icon = {
            "session": "*", "bg-bash": "[bg]", "subagent": "[agent]",
            "stop": ".", "task-create": "[+]", "task-update": "[~]",
        }
        for e in feed[:12]:
            lines.append("- %s `%s` %s %s - %s" % (
                rel(parse(e.get("at", ""))), e.get("sid", "?"),
                icon.get(e.get("kind"), "-"), e.get("kind", ""), e.get("detail", "")))
        lines.append("")

    lines.append("---")
    lines.append("*Generated by `fleet-session-hook.py` (Claude Code hook). Do not edit.*")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, OUT)


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    event = data.get("hook_event_name", "")
    sid = data.get("session_id", "")
    cwd = data.get("cwd", "")
    note_already_written = False

    if sid:
        s = load_session(sid)
        s["lastAt"] = iso(now())
        if cwd:
            s["cwd"] = cwd

        if event == "SessionStart":
            s.setdefault("started", iso(now()))
            s["status"] = "working"
            s["lastTool"] = "(session start)"
            cwd_label = os.path.basename(cwd.rstrip("/\\")) if cwd else ""
            add_feed_local(s, "session", "session started")
            add_activity(s, "Session started" + (" in %s" % cwd_label if cwd_label else ""))

        elif event == "Stop":
            s["status"] = "idle"
            s["lastTool"] = "(awaiting input)"
            add_activity(s, "Session paused — awaiting input")

        elif event == "SessionEnd":
            s["status"] = "ended"
            add_activity(s, "Session ended")
            write_session_note(sid, s)
            note_already_written = True
            # File is NOT deleted here -- see the module docstring's "SessionEnd does
            # NOT delete its own file" section. It's saved below like any other event
            # (status="ended" persisted) and cleaned up later by the same
            # SESSION_PRUNE_H pruning every other session gets, so its feed_events
            # survive for that window instead of vanishing the instant this event
            # fires. render() and session_liveness.py both explicitly exclude
            # status="ended" sessions from anything that means "still active".

        elif event == "PostToolUse":
            s["status"] = "working"
            tool = data.get("tool_name", "")
            ti = data.get("tool_input", {}) or {}
            tr = data.get("tool_response", {}) or {}
            s["lastTool"] = tool

            if tool == "Bash" and ti.get("run_in_background"):
                cmd = ti.get("command", "")
                add_feed_local(s, "bg-bash", cmd)
                add_activity(s, "[bg] %s" % trunc(cmd, 60))

            elif tool == "Task":
                desc = ti.get("description") or ti.get("subagent_type") or "subagent"
                add_feed_local(s, "subagent", desc)
                add_activity(s, "[agent] %s" % trunc(desc, 60))

            elif tool == "TaskCreate":
                title = (ti.get("title") or ti.get("description") or "(task)")
                # ID may come from the tool response or we generate one from timestamp
                task_id = (tr.get("id") or tr.get("task_id") or
                           ti.get("id") or ("task-%s" % iso(now()).replace(":", "")))
                status_val = ti.get("status", "pending")
                upsert_task(s, task_id, title=title, status=status_val)
                add_feed_local(s, "task-create", title)
                add_activity(s, "[task+] %s" % trunc(title, 60))

            elif tool == "TaskUpdate":
                task_id = (ti.get("id") or ti.get("task_id") or "")
                status_val = ti.get("status")
                title_val = ti.get("title")
                if task_id:
                    upsert_task(s, task_id, title=title_val, status=status_val)
                    existing_title = next(
                        (t.get("title", task_id[:8]) for t in s.get("tasks", [])
                         if t.get("id") == task_id),
                        task_id[:8]
                    )
                    action = status_val or "updated"
                    add_feed_local(s, "task-update", "%s: %s" % (action, existing_title))
                    add_activity(s, "[task~] %s: %s" % (action, trunc(existing_title, 55)))

        try:
            save_session(sid, s)
        except Exception:
            pass

    try:
        render()
    except Exception:
        pass

    if sid and not note_already_written:
        write_session_note(sid, s)

    sys.exit(0)


if __name__ == "__main__":
    main()

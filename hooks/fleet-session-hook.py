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

STATE-FILE RACE (fixed 2026-07-24). Every invocation does a full read-modify-write of
the SHARED session-state.json: load, mutate only THIS session's own entry, write the
WHOLE file back. Atomic rename (temp file + os.replace) protects against a torn/partial
write, but not against two concurrent readers each working from a stale snapshot --
many Claude Code sessions across different worktrees all fire this same hook, and two
racing invocations could each load before the other's save, then the second save
silently overwrites the first session's fresh update with a stale snapshot that never
had it. Live-verified before the fix: 10 of 12 real concurrent hook subprocesses,
each creating a distinct session, lost their own session on save. Closed with
state_lock() -- a short-timeout, stdlib-only mutex around the load-modify-save cycle.
render() and the post-block write_session_note() call sit OUTSIDE it: they only touch
the LOCAL `state` already in hand and are fully derived/self-correcting on the next
event, so a race there is transient staleness, not a permanent lost update. The ONE
write_session_note() call that DOES run inside the lock (SessionEnd's own note, right
before that session is popped from state) is a necessary exception -- it needs the
about-to-be-discarded entry, not a race concern -- and only adds a millisecond-scale
file write to the hold time (2026-07-24 formal review, flagged as a doc-accuracy gap
in an earlier draft of this comment, not a behavioral one; verified: DELIBERATELY on
POSIX the stale-lock-clear below can dual-hold under a specific interleave, defused
here only because Windows CRT `os.remove()` of an fd another process still holds
raises PermissionError (probed live) -- this file is Windows-only by design (see the
hardcoded Windows-path defaults below), so that is a real platform dependency, not a
latent bug.
"""
import sys, os, json, datetime, time, contextlib

STATE        = os.environ.get("ORA_FLEET_STATE") or r"C:\Users\Owner\.claude\obsidian-fleet-mirror\session-state.json"
OUT          = os.environ.get("ORA_OBSIDIAN_OUT") or r"C:\Users\Owner\Obsidian\BrainVault\_Claude\Claude Session Tasks.md"
SESSIONS_DIR = os.environ.get("ORA_OBSIDIAN_SESSIONS") or r"C:\Users\Owner\Obsidian\BrainVault\_Claude\Sessions"

FEED_CAP        = 20
SESSION_PRUNE_H = 6
WORKING_MIN     = 5
RECENT_MIN      = 15
ACTIVITY_CAP    = 50

LOCK_PATH       = STATE + ".lock"
LOCK_TIMEOUT_S  = 8.0    # measured (2026-07-24, concurrent stress tests, see below):
                          # a single hook invocation's OWN Python-interpreter-startup
                          # overhead alone is ~0.75-1.5s under load on this machine --
                          # far more than the JSON-mutation critical section itself, so
                          # a "few ms" estimate for this budget is wrong; it must cover
                          # realistic total per-call latency under contention, not just
                          # the critical section's own work. 0/50 lost at 30-way
                          # concurrency, occasionally 1-2/50 lost at 50-way (confirmed
                          # via ORA_FLEET_LOCK_DEBUG=1 to be genuine lock-acquisition
                          # timeouts, not a logic bug -- the fail-open path is working
                          # exactly as designed). 50 simultaneous SessionStart events
                          # is beyond this environment's realistic worst case (even a
                          # bad "catch-up burst" -- see event_log.md -- fires well under
                          # that many at once); this is a best-effort mirror, not a
                          # security gate, so an occasional single-session miss under
                          # genuinely extreme concurrency is an accepted residual, not
                          # something worth trading further for a longer worst-case
                          # per-tool-call stall.
LOCK_POLL_S     = 0.05
LOCK_STALE_S    = 10.0   # a legitimate hold is milliseconds; older = an abandoned lock
                          # from a killed process, safe to clear rather than jam every
                          # future call for LOCK_TIMEOUT_S forever


@contextlib.contextmanager
def state_lock():
    """Best-effort mutex around the state-file read-modify-write cycle (exclusive-create
    lock file, portable, stdlib-only). NEVER blocks longer than LOCK_TIMEOUT_S -- on
    timeout or any unexpected OS error, proceeds WITHOUT the lock: the same race that
    existed before this fix, never worse, and this hook must always exit fast."""
    fd = None
    deadline = time.time() + LOCK_TIMEOUT_S
    while fd is None and time.time() < deadline:
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(LOCK_PATH) > LOCK_STALE_S:
                    os.remove(LOCK_PATH)  # abandoned lock -- clear and retry immediately
                    continue
            except Exception:
                pass
            time.sleep(LOCK_POLL_S)
        except Exception:
            break  # unexpected OS error -- proceed without the lock
    # Off by default (stderr is not surfaced in normal hook operation); set
    # ORA_FLEET_LOCK_DEBUG=1 to diagnose whether a lost session under contention was a
    # genuine lock-acquisition timeout (this line) vs. some other bug -- this is
    # exactly how the LOCK_TIMEOUT_S calibration above was verified.
    if os.environ.get("ORA_FLEET_LOCK_DEBUG"):
        sys.stderr.write("LOCK_DEBUG acquired=%s\n" % (fd is not None))
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                os.remove(LOCK_PATH)
            except Exception:
                pass


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


def load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("sessions", {})
        d.setdefault("feed", [])
        return d
    except Exception:
        return {"sessions": {}, "feed": []}


def save_state(d):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, STATE)


def short(sid):
    return (sid or "unknown")[:8]


def trunc(s, n=70):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def add_feed(state, sid, kind, detail):
    state["feed"].insert(0, {
        "at": iso(now()), "sid": short(sid), "kind": kind, "detail": trunc(detail),
    })
    del state["feed"][FEED_CAP:]


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


def render(state):
    n = now()
    lines = []
    lines.append("---")
    lines.append("updated: " + n.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("---")
    lines.append("# Claude Sessions — Live Activity")
    lines.append("")

    active = []
    for sid, s in state["sessions"].items():
        last = parse(s.get("lastAt", ""))
        if last is None:
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

    feed = state.get("feed", [])
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

    with state_lock():
        state = load_state()

        # prune stale sessions
        cutoff = now() - datetime.timedelta(hours=SESSION_PRUNE_H)
        for k in list(state["sessions"].keys()):
            last = parse(state["sessions"][k].get("lastAt", ""))
            if last is None or last < cutoff:
                del state["sessions"][k]

        if sid:
            s = state["sessions"].setdefault(sid, {
                "started": iso(now()), "tasks": [], "activity": [],
            })
            s["lastAt"] = iso(now())
            if cwd:
                s["cwd"] = cwd

            if event == "SessionStart":
                s["status"] = "working"
                s["lastTool"] = "(session start)"
                cwd_label = os.path.basename(cwd.rstrip("/\\")) if cwd else ""
                add_feed(state, sid, "session", "session started")
                add_activity(s, "Session started" + (" in %s" % cwd_label if cwd_label else ""))

            elif event == "Stop":
                s["status"] = "idle"
                s["lastTool"] = "(awaiting input)"
                add_activity(s, "Session paused — awaiting input")

            elif event == "SessionEnd":
                s["status"] = "ended"
                add_activity(s, "Session ended")
                write_session_note(sid, s)
                state["sessions"].pop(sid, None)

            elif event == "PostToolUse":
                s["status"] = "working"
                tool = data.get("tool_name", "")
                ti = data.get("tool_input", {}) or {}
                tr = data.get("tool_response", {}) or {}
                s["lastTool"] = tool

                if tool == "Bash" and ti.get("run_in_background"):
                    cmd = ti.get("command", "")
                    add_feed(state, sid, "bg-bash", cmd)
                    add_activity(s, "[bg] %s" % trunc(cmd, 60))

                elif tool == "Task":
                    desc = ti.get("description") or ti.get("subagent_type") or "subagent"
                    add_feed(state, sid, "subagent", desc)
                    add_activity(s, "[agent] %s" % trunc(desc, 60))

                elif tool == "TaskCreate":
                    title = (ti.get("title") or ti.get("description") or "(task)")
                    # ID may come from the tool response or we generate one from timestamp
                    task_id = (tr.get("id") or tr.get("task_id") or
                               ti.get("id") or ("task-%s" % iso(now()).replace(":", "")))
                    status_val = ti.get("status", "pending")
                    upsert_task(s, task_id, title=title, status=status_val)
                    add_feed(state, sid, "task-create", title)
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
                        add_feed(state, sid, "task-update", "%s: %s" % (action, existing_title))
                        add_activity(s, "[task~] %s: %s" % (action, trunc(existing_title, 55)))

        try:
            save_state(state)
        except Exception:
            pass
    try:
        render(state)
    except Exception:
        pass
    # Write per-session note for sessions still active after this event
    if sid and sid in state.get("sessions", {}):
        write_session_note(sid, state["sessions"][sid])

    sys.exit(0)


if __name__ == "__main__":
    main()

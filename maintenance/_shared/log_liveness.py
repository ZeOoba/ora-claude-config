#!/usr/bin/env python3
r"""log_liveness.py — is the desktop log directory actually being WRITTEN TO?

READABILITY AND LIVENESS ARE DIFFERENT PROPERTIES. That sentence is the whole
module. A log directory can be present, readable, well-formed, complete, and
parse without error, while containing nothing newer than a freeze that
happened days ago. Every detector that reads it then draws a confident,
correct-looking conclusion from bytes that cannot support one.

*** 2026-08-26, SAME DAY, SECOND PASS — THE "FREEZE" WAS A DIRECTORY MOVE. ***

Everything below about readability-vs-liveness is still true and still load-
bearing. The diagnosis it produced was not. Claude Desktop MOVED its log
directory on 2026-08-20 20:40-20:51, during an app update, from

    %APPDATA%\Claude\logs        (Roaming)   <- abandoned, last write 08-20 20:51
    %LOCALAPPDATA%\Claude\Logs   (Local, capital L)  <- live, same filenames

Same `main.log` / `mcp.log` / `claude.ai-web.log` family, new home. Proof: the
old tree's last SCHEDULER event is 2026-08-17 14:23:47 and the new tree's first
is 2026-08-21 17:05:49 -- five minutes after the 08-17->08-21 fleet pause
ended -- with 103 spawns / 103 confirms since, including 160 events on 08-26
covering that morning's dispatches.

So the app never stopped logging. Every detector on this machine spent six days
reading an abandoned directory and correctly reporting that nothing was in it.
The 08-24 and 08-26 "FROZEN" verdicts were right that the bytes could not
answer the question, and wrong about why: the recommended remedies (restart the
app; check ACLs; check disk) were all aimed at a writer that was working fine.
Disk had 451 GB free and a live write+delete probe in the old directory
succeeded, which is what finally excluded them and turned up the real answer.

**THE LESSON, AND WHY DISCOVERY LIVES HERE NOW:** a hardcoded absolute path is
itself an unverified assumption, and "the file I expected is stale" has at
least two causes -- the writer stopped, or the writer moved. A detector that
can only express the first will confidently misdiagnose the second. This module
now DISCOVERS the log directory (newest-wins across known candidates) and has a
distinct `STALE-LOCATION` verdict, so the next migration names itself instead
of masquerading as a dead app. Same failure class as
`store_discovery.store_name()`'s "GUIDs rotate, never hardcode".

TWICE-PROVEN, NOT HYPOTHETICAL:

  2026-08-24 — the desktop app stopped writing to that directory at
  2026-08-20 20:51. THREE independent detectors reported success off the
  4-day-stale bytes: phantom-dispatch-probe.py returned exit 0 "OK -- every
  dispatch in the window confirmed" over a window holding >=12 real
  dispatches; host-availability-report.py silently emitted a table ending
  2026-08-17; automation-health-monitor Step 0.08's confirmation leg found no
  Spawning/Confirmed line for any throttled task and recorded 12 rows
  `dispatch_confirmed_only` without asking why. phantom-dispatch-probe gained
  an inline frozen gate that day.

  2026-08-26 — the SAME freeze, still at 2026-08-20 20:51, now 134.5h old and
  NOT cleared by a Windows-Update-triggered restart at 11:12:09 ET that
  morning (the app came up and dispatched 12+ tasks, writing zero log bytes).
  dispatch-skip-probe.py still printed `log_scan=ok` against it, because its
  check was "do main*.log files exist and open" — a readability test wearing a
  liveness test's name. That is what this module exists to stop.

A ZERO THAT MIGHT MEAN "COULD NOT LOOK" IS A FAILURE, NOT A CLEAN RUN
(memory: feedback_verified_null_vs_inferred_null).

FOUR VERDICTS:
  OK      — newest write is inside the window and not behind the registry.
  MISSING — no main*.log could be read at all. Could not look.
  FROZEN  — logs read fine, but the newest write PREDATES the look-back
            window, so they cannot answer a question about that window.
  BEHIND  — logs are not frozen by the window test, yet the registry shows a
            task dispatching MORE RECENTLY than the newest log byte. The app
            is running and not logging. This is strictly sharper than FROZEN:
            it catches a partial freeze hours before the mtime test would, and
            it would have caught 2026-08-20 the same evening.

BEHIND is the reason this is a module and not a copied `if`. The mtime test
alone needs a full window (24-26h) to elapse before it fires. Cross-checking
against registry `lastRunAt` — which every caller already has in hand — turns a
day-scale detector into a minutes-scale one.

Used by: dispatch-skip-probe.py, ora-health-guard Block A.0d (via the CLI
below). phantom-dispatch-probe.py keeps its own inline gate for now;
test-log-liveness.py asserts the two agree on identical inputs, so they cannot
drift apart silently.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

# Same shape as phantom-dispatch-probe: main.log is current, main1..main4 are
# rotations. Include all so a window still resolves across a rotation boundary.
LOG_GLOB_ORDER = ["main.log"] + ["main%d.log" % i for i in range(1, 5)]

# How far the registry may lead the log before we call it BEHIND. A dispatch
# and its log line are same-second in healthy operation; 15 minutes is ~900x
# that and comfortably absorbs clock skew, buffered writes and a slow flush.
DEFAULT_BEHIND_TOLERANCE_MIN = 15.0


def log_dir_candidates():
    """Every place Claude Desktop is known to have kept its logs, newest scheme first.

    ORDER IS DOCUMENTATION, NOT PRECEDENCE -- selection is strictly newest-wins
    (see discover_log_dir). Append to this list when a new location appears;
    never delete an old one, because the ability to SEE the abandoned directory
    is what turns "my log is stale" into "my log moved".
    """
    home = pathlib.Path.home()
    local = os.environ.get("LOCALAPPDATA") or str(home / "AppData/Local")
    roaming = os.environ.get("APPDATA") or str(home / "AppData/Roaming")
    return [
        pathlib.Path(local) / "Claude" / "Logs",    # current, since 2026-08-20
        pathlib.Path(roaming) / "Claude" / "logs",  # pre-2026-08-20, abandoned
    ]


def _newest_main_mtime(d):
    """Newest mtime across main*.log in d, or None if there are none."""
    newest = None
    try:
        names = os.listdir(d)
    except OSError:
        return None
    for name in names:
        if not (name.startswith("main") and name.endswith(".log")):
            continue
        try:
            mt = dt.datetime.fromtimestamp((pathlib.Path(d) / name).stat().st_mtime)
        except OSError:
            continue
        if newest is None or mt > newest:
            newest = mt
    return newest


def discover_log_dir():
    """Return (live_dir, survey) where survey is [(path, newest_mtime), ...].

    NEWEST-WINS. A hardcoded absolute path is an unverified assumption; on
    2026-08-20 the app moved Roaming -> Local and every detector that had one
    baked in spent six days reading an abandoned directory and reporting, with
    complete internal consistency, that nothing was in it.
    """
    candidates = log_dir_candidates()
    survey = [(d, _newest_main_mtime(d)) for d in candidates]
    live = [(d, m) for d, m in survey if m is not None]
    if not live:
        # No candidate holds a main*.log. Return the first known location so
        # callers still get a path to report on, or None if a test has stubbed
        # the candidate list empty -- never IndexError.
        return (candidates[0] if candidates else None), survey
    live.sort(key=lambda x: x[1], reverse=True)
    return live[0][0], survey


def default_log_dir():
    """Backwards-compatible entry point. Now DISCOVERS rather than hardcodes."""
    return discover_log_dir()[0]


class LivenessReport:
    """Verdict plus every fact a caller needs to explain it to a human."""

    __slots__ = ("verdict", "files_read", "problems", "newest_mtime",
                 "age_hours", "window_hours", "newest_activity", "behind_by_min",
                 "detail")

    def __init__(self, verdict, files_read, problems, newest_mtime, age_hours,
                 window_hours, newest_activity, behind_by_min, detail):
        self.verdict = verdict
        self.files_read = files_read
        self.problems = problems
        self.newest_mtime = newest_mtime
        self.age_hours = age_hours
        self.window_hours = window_hours
        self.newest_activity = newest_activity
        self.behind_by_min = behind_by_min
        self.detail = detail

    @property
    def ok(self):
        return self.verdict == "OK"

    @property
    def usable(self):
        """True when log-derived evidence may be trusted for this window."""
        return self.verdict == "OK"

    def as_dict(self):
        def stamp(v):
            return v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, dt.datetime) else None
        return {
            "verdict": self.verdict,
            "usable": self.usable,
            "files_read": list(self.files_read),
            "problems": list(self.problems),
            "newest_write": stamp(self.newest_mtime),
            "age_hours": None if self.age_hours is None else round(self.age_hours, 2),
            "window_hours": self.window_hours,
            "newest_registry_activity": stamp(self.newest_activity),
            "behind_by_minutes": None if self.behind_by_min is None else round(self.behind_by_min, 1),
            "detail": self.detail,
        }

    def banner(self):
        """Multi-line operator-facing explanation. Never a bare verdict."""
        if self.verdict == "OK":
            return "log liveness OK — newest write %s (%.1fh ago)" % (
                self.newest_mtime.strftime("%Y-%m-%d %H:%M:%S"), self.age_hours)
        if self.verdict == "STALE-LOCATION":
            return ("[ACTION] DESKTOP LOG DIRECTORY HAS MOVED — %s\n"
                    "  You are reading an ABANDONED directory. The app is logging normally,\n"
                    "  somewhere else. This is a PATH fix, not an app fix: repoint the reader.\n"
                    "  Do NOT restart Claude Desktop, and do NOT investigate ACLs or disk space —\n"
                    "  all three were chased for six days in 2026-08 against a healthy writer."
                    % self.detail)
        out = ["[ACTION] DESKTOP LOG IS %s — %s" % (self.verdict, self.detail)]
        if self.newest_mtime is not None:
            out.append("  newest write across %s: %s (%.1fh ago)" % (
                ", ".join(self.files_read) or "-",
                self.newest_mtime.strftime("%Y-%m-%d %H:%M:%S"), self.age_hours))
        if self.newest_activity is not None:
            out.append("  newest registry dispatch: %s%s" % (
                self.newest_activity.strftime("%Y-%m-%d %H:%M:%S"),
                "" if self.behind_by_min is None
                else "  (log is %.0f min behind the app)" % self.behind_by_min))
        out.append("  Every log-derived signal on this machine is UNVERIFIABLE until this clears:")
        out.append("  phantom-dispatch-probe, host-availability-report.py, and")
        out.append("  automation-health-monitor Step 0.08's confirmation leg.")
        out.append("  Fall back to registry evidence (recordedSkips, lastRunAt, fleet-status.py),")
        out.append("  which is log-independent. Do NOT report the fleet clean on log silence.")
        return "\n".join(out)


def _read_mtimes(log_dir):
    """Return (files_read, problems, newest_mtime).

    A candidate only counts toward files_read/newest -- the evidence every
    caller's `usable`/OK verdict rests on -- if it is BOTH (a) a regular file,
    not a directory/FIFO/socket/etc, and (b) actually openable for reading.
    stat() succeeding proves neither: a directory named `main.log` stats fine
    and carries a real mtime (Qodo #2), and a permission-denied or ACL-locked
    regular file stats fine too (Qodo #1). Every real consumer of this module
    (dispatch-skip-probe.py, phantom-dispatch-probe.py, host-availability-
    report.py) actually open()s the candidate paths and would fail on either
    case, so "read" here has to mean the same thing it means for them, not
    "stat() didn't raise". We don't load full contents (that's each caller's
    own job and can be tens of MB) -- a 1-byte probe read is enough to prove
    openability without duplicating their scan cost.
    """
    files_read, problems, newest = [], [], None
    log_dir = pathlib.Path(log_dir)
    if not log_dir.is_dir():
        return files_read, ["%s: directory absent" % log_dir], None
    for name in LOG_GLOB_ORDER:
        p = log_dir / name
        if not p.exists():
            problems.append("%s: absent" % name)
            continue
        if not p.is_file():
            problems.append("%s: not a regular file" % name)
            continue
        try:
            with open(p, "rb") as fh:
                fh.read(1)
        except OSError as exc:
            problems.append("%s: %s: %s" % (name, exc.__class__.__name__, exc))
            continue
        try:
            mt = dt.datetime.fromtimestamp(p.stat().st_mtime)
        except OSError as exc:
            problems.append("%s: %s: %s" % (name, exc.__class__.__name__, exc))
            continue
        files_read.append(name)
        if newest is None or mt > newest:
            newest = mt
    return files_read, problems, newest


def assess(log_dir=None, window_hours=24.0, newest_activity=None,
           behind_tolerance_min=DEFAULT_BEHIND_TOLERANCE_MIN, now=None):
    """Classify the desktop log's liveness. Never raises on a bad log.

    log_dir           — None (default) DISCOVERS the live directory newest-wins
                        across log_dir_candidates(). Passing an explicit path
                        additionally enables the STALE-LOCATION check: if some
                        other known candidate has newer writes, the caller is
                        reading an abandoned tree and is told so by name.
    window_hours      — the look-back the CALLER cares about. A log whose newest
                        write predates it is FROZEN *for that caller's question*.
    newest_activity   — datetime (LOCAL, to match log stamps) of the most recent
                        registry dispatch the caller knows about, or None to skip
                        the BEHIND check. Log timestamps carry no zone, so pass a
                        local-time value.
    """
    now = now or dt.datetime.now()
    explicit = log_dir is not None
    live_dir, survey = discover_log_dir()
    log_dir = log_dir or live_dir
    files_read, problems, newest = _read_mtimes(log_dir)

    # ---- STALE-LOCATION GATE (2026-08-26, second pass) -------------------
    # Outranks FROZEN, because it EXPLAINS a frozen-looking directory. If the
    # caller pinned a path and some other known candidate has newer main*.log
    # writes, the caller is reading an abandoned tree -- which is what actually
    # happened for six days after the app moved Roaming -> Local. Saying
    # "FROZEN, the app isn't logging" there is a confident wrong answer; the
    # app is logging, elsewhere, and the fix is a path, not a restart.
    if explicit:
        mine = _newest_main_mtime(log_dir)
        better = [(d, m) for d, m in survey
                  if m is not None and str(d) != str(log_dir)
                  and (mine is None or m > mine + dt.timedelta(minutes=5))]
        if better:
            better.sort(key=lambda x: x[1], reverse=True)
            d, m = better[0]
            age_h = None if mine is None else (now - mine).total_seconds() / 3600.0
            return LivenessReport(
                "STALE-LOCATION", files_read, problems, mine, age_h, window_hours,
                newest_activity, None,
                "this directory is ABANDONED, not dead — %s has newer writes (%s). "
                "The app moved its log location; point readers at the live directory. "
                "Do NOT restart the app or investigate ACLs/disk."
                % (d, m.strftime("%Y-%m-%d %H:%M:%S")))

    if not files_read:
        return LivenessReport("MISSING", files_read, problems, None, None,
                              window_hours, newest_activity, None,
                              "no main*.log could be read: " + ("; ".join(problems) or "unknown"))

    age_h = (now - newest).total_seconds() / 3600.0
    if newest < now - dt.timedelta(hours=window_hours):
        return LivenessReport(
            "FROZEN", files_read, problems, newest, age_h, window_hours,
            newest_activity, None,
            "newest write is %.1fh old but the look-back window is only %gh, "
            "so the log cannot answer a question about that window" % (age_h, window_hours))

    if newest_activity is not None:
        behind = (newest_activity - newest).total_seconds() / 60.0
        if behind > behind_tolerance_min:
            return LivenessReport(
                "BEHIND", files_read, problems, newest, age_h, window_hours,
                newest_activity, behind,
                "the registry shows a dispatch %.0f min NEWER than the newest log byte "
                "(tolerance %g min) — the app is running and not logging"
                % (behind, behind_tolerance_min))
        return LivenessReport("OK", files_read, problems, newest, age_h, window_hours,
                              newest_activity, behind, "log is live and abreast of the registry")

    return LivenessReport("OK", files_read, problems, newest, age_h, window_hours,
                          None, None, "log is live (registry cross-check not requested)")


def newest_registry_dispatch(now=None):
    """Most recent lastRunAt across BOTH fleets, as LOCAL time, or None.

    Returns None when neither store can be resolved or read — the caller must
    treat that as "BEHIND check unavailable", never as "nothing dispatched".
    """
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import store_discovery as sd
    except Exception:
        return None
    newest = None
    for fleet in ("claude-code-sessions", "local-agent-mode-sessions"):
        try:
            path = sd.discover_store(fleet)
            if not path:
                continue
            reg = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for t in reg.get("scheduledTasks", []) or []:
            raw = t.get("lastRunAt")
            if not raw:
                continue
            try:
                # lastRunAt is UTC ISO8601; log stamps are local. Convert.
                utc = dt.datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=dt.timezone.utc)
                local = utc.astimezone().replace(tzinfo=None)
            except Exception:
                continue
            if newest is None or local > newest:
                newest = local
    return newest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Classify desktop-log liveness (OK/MISSING/FROZEN/BEHIND).")
    ap.add_argument("--window-hours", type=float, default=24.0)
    ap.add_argument("--log-dir")
    ap.add_argument("--behind-tolerance-min", type=float, default=DEFAULT_BEHIND_TOLERANCE_MIN)
    ap.add_argument("--no-registry-check", action="store_true",
                    help="skip the BEHIND cross-check against registry lastRunAt")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--json-out")
    a = ap.parse_args(argv)

    activity = None if a.no_registry_check else newest_registry_dispatch()
    rep = assess(a.log_dir, a.window_hours, activity, a.behind_tolerance_min)

    if a.json:
        print(json.dumps(rep.as_dict(), indent=1))
    else:
        live_dir, survey = discover_log_dir()
        print("log dir : %s%s" % (live_dir, "" if a.log_dir else "   (discovered, newest-wins)"))
        for d, m in survey:
            if str(d) == str(live_dir):
                continue
            print("  other  : %s  newest=%s%s" % (
                d, m.strftime("%Y-%m-%d %H:%M:%S") if m else "(no main*.log)",
                "   <-- abandoned" if m else ""))
        print(rep.banner())
        if activity is None and not a.no_registry_check:
            print("  note: registry cross-check UNAVAILABLE (no store readable) — "
                  "BEHIND could not be evaluated this run.")
    if a.json_out:
        try:
            with open(a.json_out, "w", encoding="utf-8") as fh:
                json.dump(rep.as_dict(), fh, indent=1)
        except OSError as exc:
            print("WARN: could not write %s: %s" % (a.json_out, exc), file=sys.stderr)

    if rep.verdict == "OK":
        return 0
    if rep.verdict == "MISSING":
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())

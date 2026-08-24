#!/usr/bin/env python3
"""ORA phantom-dispatch probe -- detects scheduled tasks that NEVER STARTED.

WHY (root-caused 2026-08-03 on ora-health-guard, re-measured 2026-08-05):
the Claude Desktop scheduler stamps `lastRunAt` at DISPATCH, and the
"Cleared stale pending dispatch" garbage-collector stamps it AGAIN -- so a
task whose session never attached is byte-identical, in both registries, to
one that ran to completion. Every registry-based detector is blind to it:
fleet-status.py, lastRunAt read directly, recordedSkips (a phantom is not a
"skip"), and automation-health-monitor's freshness checks.

Measured over main1.log+main.log, 2026-07-31 -> 2026-08-05: 74 confirmed runs
vs 55 phantom dispatches -- 43% of ALL dispatches never started (CC/MCP 47%,
LAMS/Cowork 29%). Casualties included ora-cowork-heartbeat (the dead-man's own
pulse, 4x), ora-task-integrity-guard (4x) and ora-broker-touch-cadence (its
only ever fire). Two same-week incidents were each mis-attributed to a bug in
the task's own SKILL.md before the log was consulted.

THE ONLY RELIABLE EXECUTION PROOF ON THIS MACHINE is the desktop app's own
`Confirmed task run for: <id>` line. This probe pairs it against the preceding
`Spawning new session for scheduled task <id>` and reports every dispatch that
never confirmed. Covers BOTH fleets ([CCDScheduledTasks] = CC/MCP,
[ScheduledTasks] = LAMS/Cowork).

Runs from WINDOWS Task Scheduler via fleet-deadman.ps1, deliberately OUTSIDE
both Claude fleets: a fleet task cannot be trusted to detect its own fleet
failing to start (ora-task-integrity-guard was itself phantom-dispatched on
2026-08-04 AND 2026-08-05, so an in-fleet check would have been silent on
exactly the days it was needed).

Exit 0 = no phantom dispatch in the window, AND at least one dispatch was
         actually examined.
Exit 1 = [ACTION] phantom dispatch(es) found.
Exit 2 = probe could not look. NEVER conflated with exit 0 -- a zero that might
         mean "could not look" is a failure, not a clean run (memory:
         feedback_verified_null_vs_inferred_null). Three ways to get here:
           (a) logs missing/unreadable;
           (b) FROZEN LOG -- logs read fine but the newest write predates the
               look-back window, so they cannot answer the question;
           (c) ZERO DISPATCHES -- log is fresh but carries no dispatch events
               in the window, so the probe verified nothing.

(b) was added 2026-08-24 after this probe reported exit 0 "OK -- every dispatch
in the window confirmed" over a window holding >=12 real dispatches. Nothing
was wrong with the parser: the desktop app had stopped writing to
%APPDATA%\\Claude\\logs entirely at 2026-08-20 20:51, so all five logs were
4 days stale and correctly contained nothing recent. The probe was reading
real bytes and drawing a conclusion the bytes could not support. A log's
READABILITY and its LIVENESS are different properties and this probe now
checks both.

Deliberately NO silent excepts: registry-membership-probe.py shipped an
`except Exception: pass` around its log append and went quiet for two days
before anyone noticed (fixed 2026-08-05).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import sys
from collections import Counter

# A healthy dispatch confirms in ~1-4s (observed max 31s on a loaded machine).
# 180s is ~6x the worst observed, and well inside the app's own ~5-16min
# stale-clear sweep, so a confirm this late always belongs to a LATER dispatch.
CONFIRM_WINDOW_S = 180
# A spawn with neither confirm nor stale-clear this long after it was never
# collected by the app's sweep either -- treat as phantom rather than pending.
ORPHAN_AFTER_S = 900
DEFAULT_HOURS = 26  # one daily cycle + margin, same shape as the beacon watchdog

_LINE = re.compile(
    r"^(?P<ts>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[(?:info|warn)\] "
    r"\[(?P<prefix>CCDScheduledTasks|ScheduledTasks)\] "
    r"(?:"
    r"Spawning new session for scheduled task (?P<spawn>[\w.-]+)"
    r"|Confirmed task run for: (?P<confirm>[\w.-]+)"
    r"|Cleared stale pending dispatch for: (?P<stale>[\w.-]+)"
    r")"
)


class ProbeError(RuntimeError):
    """The probe could not look. Never reported as a clean run."""


class Event:
    __slots__ = ("ts", "kind", "task", "fleet")

    def __init__(self, ts, kind, task, fleet):
        self.ts, self.kind, self.task, self.fleet = ts, kind, task, fleet

    def key(self):
        return (self.ts, self.kind, self.task, self.fleet)

    def __repr__(self):
        return f"Event({self.ts:%Y-%m-%d %H:%M:%S}, {self.kind}, {self.task})"


class Phantom:
    __slots__ = ("ts", "task", "fleet", "reason", "cleared_at")

    def __init__(self, ts, task, fleet, reason, cleared_at=None):
        self.ts, self.task, self.fleet = ts, task, fleet
        self.reason, self.cleared_at = reason, cleared_at

    def line(self):
        when = self.ts.strftime("%Y-%m-%d %H:%M:%S")
        extra = ""
        if self.cleared_at:
            extra = f" (cleared {self.cleared_at:%H:%M:%S}, "
            extra += f"{int((self.cleared_at - self.ts).total_seconds())}s pending)"
        return f"{when}  {self.fleet:<11}  {self.task}  [{self.reason}]{extra}"


def default_log_paths():
    appdata = os.environ.get("APPDATA") or str(pathlib.Path.home() / "AppData/Roaming")
    logs = pathlib.Path(appdata) / "Claude" / "logs"
    # main.log is current; main1..main4 are older rotations. Include all so the
    # window still resolves across a rotation boundary.
    return [logs / "main.log"] + [logs / f"main{i}.log" for i in range(1, 5)]


def load_lines(paths):
    """Read every readable log. Raise ProbeError if NONE could be read.

    Also returns the newest mtime across the logs actually read. A readable
    but FROZEN log is the failure mode this probe was blind to until
    2026-08-24 -- see the freshness gate in main().
    """
    lines, read, problems = [], [], []
    newest_mtime = None
    for p in paths:
        p = pathlib.Path(p)
        if not p.exists():
            problems.append(f"{p.name}: absent")
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                lines.extend(fh.read().splitlines())
            read.append(p.name)
            mt = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            if newest_mtime is None or mt > newest_mtime:
                newest_mtime = mt
        except OSError as exc:
            problems.append(f"{p.name}: {exc.__class__.__name__}: {exc}")
    if not read:
        raise ProbeError("no desktop log was readable -- " + "; ".join(problems))
    return lines, read, problems, newest_mtime


def parse_events(lines):
    """Parse dispatch events, de-duplicating the app's verbatim double-writes."""
    out, seen = [], set()
    for line in lines:
        m = _LINE.match(line)
        if not m:
            continue
        if m.group("spawn"):
            kind, task = "spawn", m.group("spawn")
        elif m.group("confirm"):
            kind, task = "confirm", m.group("confirm")
        else:
            kind, task = "stale", m.group("stale")
        ev = Event(
            datetime.datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S"),
            kind, task,
            "CC/MCP" if m.group("prefix") == "CCDScheduledTasks" else "LAMS/Cowork",
        )
        k = ev.key()
        if k in seen:
            continue
        seen.add(k)
        out.append(ev)
    return out


def find_phantoms(events, now=None, hours=DEFAULT_HOURS):
    """Return dispatches inside the window that never confirmed.

    Log timestamps are LOCAL time with no zone suffix, so `now` is local too.
    """
    if now is None:
        now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=hours)

    # Ordering within a single log second matters: a healthy dispatch very often
    # spawns AND confirms inside the same second, and log lines carry no
    # sub-second precision. Rank spawn FIRST so its own outcome is never sorted
    # behind it (a plain (ts, kind) sort puts "confirm" before "spawn"
    # alphabetically and reports every fast confirm as never-confirmed).
    rank = {"spawn": 0, "confirm": 1, "stale": 2}
    by_task = {}
    for ev in sorted(events, key=lambda e: (e.ts, rank[e.kind])):
        by_task.setdefault(ev.task, []).append(ev)

    phantoms = []
    for task, evs in by_task.items():
        matched_stale = set()
        for i, ev in enumerate(evs):
            if ev.kind != "spawn":
                continue
            confirmed = cleared = None
            for later in evs[i + 1:]:
                if later.kind == "spawn":
                    break  # next dispatch: this one's fate is already decided
                delta = (later.ts - ev.ts).total_seconds()
                if later.kind == "confirm" and delta <= CONFIRM_WINDOW_S:
                    confirmed = later
                    break
                if later.kind == "stale":
                    cleared = later
                    break
            if confirmed:
                continue
            if ev.ts < cutoff:
                continue
            if cleared is not None:
                matched_stale.add(id(cleared))
                phantoms.append(Phantom(ev.ts, task, ev.fleet, "cleared-stale", cleared.ts))
            elif (now - ev.ts).total_seconds() >= ORPHAN_AFTER_S:
                phantoms.append(Phantom(ev.ts, task, ev.fleet, "never-confirmed"))
            # else: still in flight, not yet judged

        # A stale-clear whose Spawning line fell off the end of a rotated log is
        # still hard proof the dispatch never started -- never drop it.
        for ev in evs:
            if ev.kind == "stale" and id(ev) not in matched_stale and ev.ts >= cutoff:
                phantoms.append(Phantom(ev.ts, task, ev.fleet, "cleared-stale"))

    return sorted(phantoms, key=lambda p: (p.ts, p.task))


def count_confirmed(events, now=None, hours=DEFAULT_HOURS):
    if now is None:
        now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=hours)
    return sum(1 for e in events if e.kind == "confirm" and e.ts >= cutoff)


def append_state(state_dir, summary, phantoms):
    """Append the run line + snapshot. Errors are LOUD, never swallowed."""
    state_dir = pathlib.Path(state_dir)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with open(state_dir / "phantom-dispatch.log", "a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {summary}\n")
        with open(state_dir / "phantom-dispatch.json", "w", encoding="utf-8") as fh:
            json.dump({
                "checked_at": stamp,
                "summary": summary,
                "phantoms": [
                    {"at": p.ts.strftime("%Y-%m-%d %H:%M:%S"), "task": p.task,
                     "fleet": p.fleet, "reason": p.reason,
                     "cleared_at": p.cleared_at.strftime("%Y-%m-%d %H:%M:%S") if p.cleared_at else None}
                    for p in phantoms
                ],
            }, fh, indent=2)
    except OSError as exc:
        print(f"WARN: could not write probe state to {state_dir}: "
              f"{exc.__class__.__name__}: {exc}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hours", type=float, default=DEFAULT_HOURS,
                    help=f"look-back window in hours (default {DEFAULT_HOURS})")
    ap.add_argument("--log", action="append", dest="logs",
                    help="explicit log path (repeatable); default = %%APPDATA%%\\Claude\\logs\\main*.log")
    ap.add_argument("--state-dir", default=str(pathlib.Path(__file__).resolve().parent / "_state"))
    ap.add_argument("--quiet", action="store_true", help="summary line only")
    args = ap.parse_args(argv)

    try:
        lines, read, problems, newest_mtime = load_lines(args.logs or default_log_paths())
    except ProbeError as exc:
        print(f"[PROBE ERROR] phantom-dispatch-probe could not look: {exc}", file=sys.stderr)
        print("This is NOT a clean run. Do not report the fleet healthy.", file=sys.stderr)
        return 2

    # ---- FROZEN-LOG GATE (added 2026-08-24) -------------------------------
    # A readable log is not a LIVE log. On 2026-08-24 this probe returned
    # exit 0 / "OK -- every dispatch in the window confirmed" over a window
    # that contained at least 12 real dispatches, because the desktop app had
    # silently stopped writing to %APPDATA%\Claude\logs entirely at
    # 2026-08-20 20:51 -- every file in that directory was 4 days stale. The
    # probe read five logs successfully, parsed them correctly, and found
    # nothing, because there was nothing newer than the freeze to find.
    # Reading stale bytes is "could not look", not "looked and it was clean"
    # (memory: feedback_verified_null_vs_inferred_null).
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(hours=args.hours)
    if newest_mtime is not None and newest_mtime < cutoff:
        age_h = (now - newest_mtime).total_seconds() / 3600.0
        print("[PROBE ERROR] phantom-dispatch-probe could not look: desktop log is FROZEN.",
              file=sys.stderr)
        print(f"  newest write across {', '.join(read)}: "
              f"{newest_mtime:%Y-%m-%d %H:%M:%S} ({age_h:.1f}h ago)", file=sys.stderr)
        print(f"  look-back window is {args.hours:g}h, so the log cannot answer this question.",
              file=sys.stderr)
        print("  The app is dispatching (check the registry) but not logging -- restarting",
              file=sys.stderr)
        print("  Claude Desktop is the usual fix. Until then EVERY log-derived signal on this",
              file=sys.stderr)
        print("  machine is stale: dispatch-skip-probe's confirmation leg, host-availability-",
              file=sys.stderr)
        print("  report.py, and automation-health-monitor Step 0.08's log scan.", file=sys.stderr)
        print("This is NOT a clean run. Do not report the fleet healthy.", file=sys.stderr)
        return 2

    events = parse_events(lines)
    phantoms = find_phantoms(events, hours=args.hours)
    confirmed = count_confirmed(events, hours=args.hours)
    total = confirmed + len(phantoms)
    pct = (len(phantoms) / total * 100) if total else 0.0

    summary = (f"window={args.hours:g}h confirmed={confirmed} phantom={len(phantoms)} "
               f"({pct:.0f}%) logs={','.join(read)}")
    append_state(args.state_dir, summary, phantoms)

    if not args.quiet:
        print("PHANTOM DISPATCH PROBE -- scheduled tasks that never started")
        print(f"  logs read : {', '.join(read)}")
        for p in problems:
            print(f"  skipped   : {p}")
        print(f"  window    : last {args.hours:g}h")
        print(f"  confirmed : {confirmed}")
        print(f"  phantom   : {len(phantoms)} ({pct:.0f}% of {total} dispatches)")

    # ---- ZERO-DISPATCH GATE (added 2026-08-24) ----------------------------
    # Defence in depth behind the frozen-log gate above, for the case where
    # the log is fresh but still carries no dispatch events at all: 0 of 0 is
    # not a clean run, it is an unverified one. This probe's entire contract
    # is "I checked N dispatches and none were phantom" -- with N=0 it checked
    # nothing and must say so. During a ratified bounded fleet pause this
    # exit 2 is the CORRECT answer, and the pause ledger is what explains it.
    if total == 0:
        print(f"\n[PROBE ERROR] no dispatch events at all in the last {args.hours:g}h "
              f"across {', '.join(read)}.", file=sys.stderr)
        print("  0 of 0 dispatches is UNVERIFIED, not clean -- the probe checked nothing.",
              file=sys.stderr)
        print("  Cross-check the registry: if lastRunAt HAS advanced for any task in this",
              file=sys.stderr)
        print("  window, the app is dispatching without logging and the log is unreliable",
              file=sys.stderr)
        print("  even though its mtime looks current. If the fleet was deliberately paused,",
              file=sys.stderr)
        print("  this is expected -- record it against the pause, do not record it as clean.",
              file=sys.stderr)
        return 2

    if phantoms:
        print("\n[ACTION] These dispatches never started -- lastRunAt says otherwise:")
        for p in phantoms:
            print("  " + p.line())
        print("\nBy task:")
        for task, n in Counter(p.task for p in phantoms).most_common():
            print(f"  {n:>3}  {task}")
        print("\nVerify against OUTPUT, never lastRunAt/fleet-status.py -- both are")
        print("advanced by the stale-clear itself. Detail: memory/"
              "reference_scheduler_lastrunat_stamped_at_dispatch.md")
        return 1
    if not args.quiet:
        print("\nOK -- every dispatch in the window confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assert that this environment's own detector OUTPUTS are still being produced.

Added 2026-09-10, ORA Automation Audit R24-1. Closes the structural gap R22-2/R22-3
identified on 2026-09-05 and recommended -- a probe that was never built until now.

THE GAP THIS CLOSES
-------------------
Every check in this environment asserts on what a file SAYS, never on when it last
CHANGED. So a detector that stops producing is invisible: R22-2 found the very probe
built to catch a silent registry drop had itself frozen, while the task that runs it
kept reporting success. R22-3 then found three such writers frozen within ~30h and
noted that "a maintenance writer that stops producing is invisible to every check in
this environment." That remained true for 5 more days.

WHY IT IS PAUSE-AWARE, AND WHY THAT IS THE HARD PART
----------------------------------------------------
A naive staleness check is worse than none here, because a DELIBERATE fleet pause
produces the identical signature. On 2026-09-07 the CC fleet was paused with a resume
queued for 09-11; ~12 `_state/` outputs froze inside one 21-minute window as a direct
consequence. Automation Audit Revision 24 had to separate those two cases by hand.

The rule this probe applies:
    a file that went stale DURING a pause of its producing fleet is expected;
    a file that was ALREADY stale when the pause began is a real finding.
That distinction is the whole value -- it is what makes the probe safe to leave armed
through a pause instead of muting it (muting is how R22-2 happened in the first place).

CONTRACT
--------
Report-only. exit 0 = clean, exit 1 = at least one [STALE] finding, exit 2 = the probe
could not look (which ALARMS -- same "a zero that might mean 'couldn't look' is a
failure, not a pass" reasoning as governor-drift-probe.py).
Never writes to any watched file. Reads the registries read-only via _shared/fleet_pause.
"""
from __future__ import annotations

import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_shared"))

try:
    import fleet_pause
except Exception as exc:  # pragma: no cover
    print("[ERROR] cannot import _shared/fleet_pause: %s: %s" % (type(exc).__name__, exc))
    sys.exit(2)

# One weekly cycle + 24h grace. Since 2026-09-17 every routine except ora-am-brief and
# the dead-man chain runs at most once a week (Gabriel-directed), so a 48h default
# flagged every weekly producer [STALE] on days 3-7 of its cycle. Daily-or-faster
# producers are held tight below in MAX_AGE_OVERRIDES. Enforced by
# _tests/test_state_freshness_thresholds.py.
DEFAULT_MAX_AGE_H = 192.0

# Files that are NOT periodic producers. Each needs a stated reason -- an unexplained
# entry here is how a real detector gets muted, which is the failure this probe exists
# to catch. Matched on basename.
NOT_PERIODIC = {
    "setup-desktop-windows.log":
        "one-off machine-setup transcript, never rewritten after install",
    "retire-pending.json":
        "event-driven queue -- written only when a task retirement is staged; "
        "an empty, old file is the healthy steady state",
    "oi-id-reservations.log":
        "append-only allocation ledger, written only when an OI id is allocated",
    "heartbeat-publish-failed.json":
        "failure marker: written by publish-fleet-heartbeat.py only on a failed publish and "
        "removed on the next success; its absence or age means nothing (merge-gate R7). "
        "A dead publisher is caught by heartbeat-publish-ok.json (48h, pause-independent)",
    "fleet-pause-windows.json":
        "written by pause_windows.capture() only when a hold starts or ends, so it is "
        "untouched for as long as the fleet is live; any age limit false-alarms after "
        "every pause (merge-gate R5, 2026-09-22)",
}

# Per-file overrides where a slower cadence is genuinely by design. Basename -> hours.
#
# Deliberately kept EMPTY-ish: a generous override is indistinguishable from muting a
# detector, which is the failure this probe exists to catch. Pause-awareness below
# already absorbs the common false positive, so the default should do the work and a
# surprise [STALE] is a finding to investigate rather than a threshold to raise.
# Raise one of these only with a stated cadence, never to quiet a result.
#
# Since 2026-09-22 the overrides run the other way too: the weekly default is the
# fleet norm, and the daily-or-faster producers listed here are held TIGHTER than it.
# A dead dead-man/heartbeat must not hide for a week. Each entry names its producer
# and cadence (verified against Windows Task Scheduler 2026-09-22).
MAX_AGE_OVERRIDES = {
    "fleet-deadman.log": 48.0,           # ORA Fleet Dead-Man (Windows, daily)
    "push-fleet-heartbeat.log": 48.0,    # ORA Fleet Heartbeat Push (Windows, daily)
    "heartbeat-publish-ok.json": 48.0,   # ORA Fleet Heartbeat Push (Windows, daily)
    "stuck-session-watchdog.log": 48.0,  # ORA Stuck-Session Watchdog (Windows, 30 min)
    "fleet-heartbeat.json": 48.0,        # emit-fleet-heartbeat.py (sub-daily)
    "phantom-dispatch.log": 48.0,        # phantom-dispatch-probe.py, run daily by ORA Fleet Dead-Man (R6)
    "phantom-dispatch.json": 48.0,       # same
    "ensure-claude-renderer.log": 48.0,  # ORA Claude Desktop Wake-and-Launch (Windows, daily) (R6)
    "pause-resume-guard-state.json": 48.0,  # ORA Fleet Pause-Resume Guard: save_state() on EVERY 6h run (R7;
                                            # was misfiled as NOT_PERIODIC, leaving the guard unwatched)
    # quarterly producers would go here, with the cron that justifies the number
}

# Producers that run OUTSIDE the scheduled-task fleets (Windows Task Scheduler), so a fleet
# pause never explains their staleness. Merge-gate R3 finding, 2026-09-22: once the
# ora-am-brief carve-out in _shared/fleet_pause.py made CC pauses visible, a dead dead-man
# written after the pause began was reported [PAUSED] (rc 0) instead of [STALE] (rc 1)
# for the whole pause, which can last up to 14 days. Enforced by
# _tests/test_state_freshness_thresholds.py.
PAUSE_INDEPENDENT = frozenset({
    "fleet-deadman.log",            # ORA Fleet Dead-Man
    "push-fleet-heartbeat.log",     # ORA Fleet Heartbeat Push
    "heartbeat-publish-ok.json",    # ORA Fleet Heartbeat Push
    "stuck-session-watchdog.log",   # ORA Stuck-Session Watchdog
    "fleet-deadman.start.log",      # ORA Fleet Dead-Man START breadcrumbs (merge-gate R5)
    "push-fleet-heartbeat.start.log",  # ORA Fleet Heartbeat Push START breadcrumbs
    "fleet-heartbeat.json",         # emit-fleet-heartbeat.py, run by ORA Fleet Heartbeat Push
    # Merge-gate R6: the full set, enumerated from the live ORA* Windows tasks and their
    # scripts -- the earlier hand-kept list missed these three producers.
    "phantom-dispatch.log",         # phantom-dispatch-probe.py via ORA Fleet Dead-Man (daily)
    "phantom-dispatch.json",        # same
    "ensure-claude-renderer.log",   # ORA Claude Desktop Wake-and-Launch (daily)
    "ora-nightly-disk.log",         # ORA Nightly Disk Clean (WEEKLY since 2026-09-17: default limit)
    "pause-resume-guard-state.json",  # ORA Fleet Pause-Resume Guard (every 6h) (R7)
    "task-folder-registration.log",  # ORA Headless - stranded-spec (Windows, WEEKLY: default limit) (R8)
})

WATCH_GLOBS = (
    "_state/*.log",
    "_state/*.json",
    "*.log",
)

# A file whose mtime is at/after (pause_start - max(its own limit, PAUSE_GRACE_H)) was still
# within its limit when the pause began, so it went stale because of the pause (merge-gate R7).
PAUSE_GRACE_H = 6.0


def _dated_oneoff(name):
    """2026-08-17_FleetPause_RestoreLedger_v02_CORRECTED.json and friends: a dated
    snapshot is a record of a moment, not a recurring producer."""
    return len(name) > 10 and name[:4].isdigit() and name[4] == "-" and name[7] == "-"


def main():
    now = time.time()

    # Pause state per fleet. An UNKNOWN answer must not silently suppress, so any
    # error here leaves paused=False and is surfaced in the header.
    fleets = {}
    for f in ("cc", "lams"):
        fleets[f] = fleet_pause.pause_state(f)

    cc = fleets["cc"]
    pause_start = cc.get("paused_since") if cc.get("paused") else None
    hdr = []
    for f, st in fleets.items():
        bit = "%s=%s" % (f, "PAUSED" if st["paused"] else "live")
        if st["paused"] and st["resume_epoch"]:
            bit += "(resume %s)" % time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(st["resume_epoch"]))
        if st["error"]:
            bit += "[%s]" % st["error"]
        hdr.append(bit)
    print("state-freshness-probe: fleets %s" % ", ".join(hdr))

    seen, stale, paused_ct, skipped, ok = set(), [], 0, 0, 0

    for pat in WATCH_GLOBS:
        for path in sorted(glob.glob(os.path.join(HERE, pat))):
            rp = os.path.realpath(path)
            if rp in seen:
                continue
            seen.add(rp)
            name = os.path.basename(path)
            rel = os.path.relpath(path, HERE).replace("\\", "/")

            if name in NOT_PERIODIC:
                print("  [SKIP]  %-52s %s" % (rel, NOT_PERIODIC[name]))
                skipped += 1
                continue
            if _dated_oneoff(name):
                print("  [SKIP]  %-52s dated one-off snapshot, not a recurring producer" % rel)
                skipped += 1
                continue

            try:
                mtime = os.path.getmtime(path)
            except OSError as exc:
                print("  [ERROR] %-52s cannot stat: %s" % (rel, exc))
                return 2

            age_h = (now - mtime) / 3600.0
            limit = MAX_AGE_OVERRIDES.get(name, DEFAULT_MAX_AGE_H)
            if age_h <= limit:
                ok += 1
                continue

            # Stale. Was it already stale when the pause began? Only CC-fleet producers can be
            # explained by a CC pause: the Windows Task Scheduler producers keep running through
            # it, so their staleness is never pause-explained (merge-gate R3, 2026-09-22).
            if (pause_start is not None and name not in PAUSE_INDEPENDENT
                    and mtime >= (pause_start - max(limit, PAUSE_GRACE_H) * 3600.0)):
                # Merge-gate R7: "already stale when the pause began" means its age AT the
                # pause start exceeded its own limit, not a flat 6h grace. With the 192h weekly
                # default, the flat grace falsely flagged every weekly producer that a pause
                # longer than the rest of its cycle had frozen.
                print("  [PAUSED] %-51s %.1fh stale, but still within its limit when the pause began "
                      "(%s) -- expected" % (
                          rel, age_h, time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(pause_start))))
                paused_ct += 1
                continue

            why = "limit %.0fh" % limit
            if pause_start is not None:
                if name in PAUSE_INDEPENDENT:
                    # Merge-gate R4: the old wording claimed "already stale before the pause",
                    # which is false for these -- they are never pause-explained at all.
                    why += ("; runs outside the scheduled-task fleets (Windows Task Scheduler), "
                            "so a fleet pause never explains it")
                else:
                    why += "; ALREADY stale before the pause began, so the pause does not explain it"
            print("  [STALE] %-52s %.1fh since last write (%s)" % (rel, age_h, why))
            stale.append(rel)

    print("state-freshness-probe: %d ok, %d stale, %d pause-explained, %d skipped"
          % (ok, len(stale), paused_ct, skipped))
    if stale:
        print("[ACTION] %d detector output(s) stopped producing and a fleet pause does NOT "
              "explain it: %s" % (len(stale), ", ".join(stale)))
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[ERROR] probe failed: %s: %s" % (type(exc).__name__, exc))
        sys.exit(2)

#!/usr/bin/env python3
"""Shared primitive: is a scheduled-task fleet under a DELIBERATE bounded pause?

Added 2026-09-10, ORA Automation Audit R24-1/R24-3.

WHY THIS EXISTS
---------------
On 2026-09-07 the CC/MCP fleet was deliberately paused with a one-time resume task
queued for 2026-09-11T20:01Z. Two separate detectors then misread the consequences:

  * `fleet-deadman.ps1` logged "fleet cc: no task run in 45.6h (threshold 30h)" on
    09-09 with no resolving OK line, and would have re-alarmed every cycle until the
    resume -- an alarm channel crying wolf through a correctly-registered pause.
  * ~12 `_state/` detector outputs froze inside one 21-minute window that afternoon
    (their producing tasks were disabled), reproducing byte-for-byte the signature
    Automation Audit R22-3 called a silent-failure cluster. A full audit pass had to
    reason the difference out by hand, because R22-2/R22-3's freshness probe was
    recommended and never built.

Both need the same question answered, so it is answered once, here.

THE TEST IS STRUCTURAL, NOT NAME-BASED
--------------------------------------
A bounded pause is: *every recurring task disabled* AND *at least one ENABLED
one-time task with a future fireAt*. Deliberately NOT a match on "pause"/"resume" in
a task title -- a title can be renamed and is not state. A merely idle fleet still has
enabled recurring tasks and therefore cannot match. A fleet with everything disabled
and NO resume queued also does not match: that is a real problem and should alarm.

Note the observed asymmetry this correctly captures: during the 2026-09-07 pause the
LAMS fleet kept `automation-health-monitor` and `ora-cowork-heartbeat` enabled, so
LAMS is NOT paused by this test even though 25 of its 29 entries are disabled. That
is the right answer -- its monitors are still firing.

READ-ONLY. Never writes, never touches the registries.
"""
from __future__ import annotations

import glob
import json
import os
import time

__all__ = ["discover_registry", "pause_state", "STORES", "MAX_RESUME_HORIZON_DAYS"]

# A resume must fire within this many days to count (2026-09-12 review finding). Without a
# horizon ANY enabled future one-time task was "the resume": LAMS carries one dated ~2027-08,
# so a real mass-disable fault would have read as a year-long pause and fleet-deadman.ps1
# would have stayed silent for a year. 14 days covers a "for two weeks" pause; a longer
# genuine pause simply alarms (false alarm, the safe direction).
MAX_RESUME_HORIZON_DAYS = 14

# Recurring tasks that stay ENABLED through every pause by standing rule, so their being
# enabled is not evidence the fleet is live (2026-09-22). Without this, a CC pause read
# as "live" because ora-am-brief is never paused (session-context: "the CC copy MUST stay
# enabled"), and every pause-frozen detector output alarmed as [STALE]. Per-fleet and
# deliberately tiny: an entry here stops that task from ever vetoing a pause, so only
# add a task with a ratified never-pause rule. LAMS has none on purpose; see the
# docstring above. Its monitors firing through a pause genuinely means LAMS is not paused.
PAUSE_CARVE_OUTS = {
    "cc": frozenset({"ora-am-brief"}),
    "lams": frozenset(),
}

STORES = {
    "cc": "claude-code-sessions",
    "lams": "local-agent-mode-sessions",
}


def _bases():
    roaming = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
    return [
        os.path.join(roaming, "Claude"),
        os.path.join(local, "Packages", "Claude_pzs8sxrjxfjjc",
                     "LocalCache", "Roaming", "Claude"),
    ]


def discover_registry(store):
    """One live registry per store: most tasks wins, tie-break newest mtime.

    Mirrors fleet-status.py's discover_registries() and fleet-deadman.ps1's
    Find-Registry -- GUIDs rotate, so never hardcode a path.
    """
    best, best_key = None, None
    for base in _bases():
        pat = os.path.join(base, store, "**", "scheduled-tasks.json")
        for p in glob.glob(pat, recursive=True):
            try:
                with open(p, encoding="utf-8") as fh:
                    d = json.load(fh)
                n = len(d.get("scheduledTasks") or [])
                key = (n, os.path.getmtime(p))
            except Exception:
                continue
            if best_key is None or key > best_key:
                best, best_key = p, key
    return best


def pause_state(fleet="cc", registry=None):
    """Return a dict describing this fleet's pause state.

    Keys:
      paused        bool
      resume_epoch  float | None  -- earliest future one-time fireAt, seconds
      paused_since  float | None  -- best estimate of when the pause began
                                     (newest createdAt among the enabled future
                                     one-time tasks), seconds
      recurring     int           -- recurring task count
      enabled_recurring int
      registry      str | None
      error         str | None    -- set when the answer is UNKNOWN, never guessed

    Fail-closed on the *question*, fail-open on the *consequence*: if anything
    cannot be read, `paused` is False and `error` is set, so a caller alarms
    normally rather than silently suppressing on a parse bug.
    """
    out = {"paused": False, "resume_epoch": None, "paused_since": None,
           "recurring": 0, "enabled_recurring": 0, "registry": None, "error": None}
    try:
        reg = registry or discover_registry(STORES.get(fleet, fleet))
        out["registry"] = reg
        if not reg:
            out["error"] = "no live registry found for store %r" % fleet
            return out
        with open(reg, encoding="utf-8") as fh:
            tasks = json.load(fh).get("scheduledTasks") or []
        if not tasks:
            out["error"] = "registry parsed but holds no tasks"
            return out

        carve = PAUSE_CARVE_OUTS.get(fleet, frozenset())
        recurring = [t for t in tasks if t.get("cronExpression")
                     and (t.get("id") or t.get("taskId")) not in carve]
        out["recurring"] = len(recurring)
        enabled_recurring = [t for t in recurring if t.get("enabled")]
        out["enabled_recurring"] = len(enabled_recurring)
        if not recurring or enabled_recurring:
            return out  # not paused

        now_ms = time.time() * 1000.0
        resume_ms, since_ms = None, None
        for t in tasks:
            if not t.get("enabled"):
                continue
            fa = t.get("fireAt")
            if fa is None:
                continue
            try:
                fa = float(fa)
            except (TypeError, ValueError):
                continue
            if fa <= now_ms or fa > now_ms + MAX_RESUME_HORIZON_DAYS * 86400000.0:
                continue
            if resume_ms is None or fa < resume_ms:
                resume_ms = fa
            ca = t.get("createdAt")
            try:
                ca = float(ca)
            except (TypeError, ValueError):
                ca = None
            if ca is not None and (since_ms is None or ca > since_ms):
                since_ms = ca

        if resume_ms is None:
            # Everything disabled with no resume queued -- NOT a bounded pause.
            out["error"] = ("all %d recurring tasks disabled with NO resume queued within %d days "
                            "-- this is not a bounded pause" % (len(recurring), MAX_RESUME_HORIZON_DAYS))
            return out

        out["paused"] = True
        out["resume_epoch"] = resume_ms / 1000.0
        out["paused_since"] = (since_ms / 1000.0) if since_ms else None
        return out
    except Exception as exc:  # never raise into a caller's alarm path
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
        return out


if __name__ == "__main__":
    for f in ("cc", "lams"):
        st = pause_state(f)
        r = st["resume_epoch"]
        s = st["paused_since"]
        print("%-5s paused=%-5s recurring=%d (enabled %d)%s%s%s" % (
            f, st["paused"], st["recurring"], st["enabled_recurring"],
            ("  resume=" + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r))) if r else "",
            ("  since=" + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(s))) if s else "",
            ("  [" + st["error"] + "]") if st["error"] else ""))

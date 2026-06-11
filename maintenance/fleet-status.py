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
import os, sys, json, glob, argparse, datetime

for _s in (sys.stdout, sys.stderr):  # UTF-8 safe output on Windows cp1252 pipes
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
        bases = [
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
    """Return (hour, minute) for a 5-field cron, or None for one-time/epoch/unknown."""
    if not isinstance(expr, str):
        return None
    parts = expr.split()
    if len(parts) != 5:
        return None
    mn, hr = parts[0], parts[1]
    try:
        return (int(hr), int(mn))
    except ValueError:
        return None  # ranges/lists/* -> not a single fixed time


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

    # skip attribution
    skip_counts = {k: len(v) for k, v in skips.items()} if isinstance(skips, dict) else {}
    total_skip_events = sum(skip_counts.values())

    # collisions: tasks sharing the same fixed (hour, minute)
    hm = {}
    for t in tasks:
        key = cron_hm(t.get("cronExpression"))
        if key is not None:
            hm.setdefault(key, []).append(t.get("id", "?"))
    collisions = {("%02d:%02d" % k): v for k, v in hm.items() if len(v) > 1}

    # AM pileup 05:00-09:30
    am_pileup = []
    for t in tasks:
        key = cron_hm(t.get("cronExpression"))
        if key and (5 <= key[0] < 9 or (key[0] == 9 and key[1] <= 30)):
            am_pileup.append((("%02d:%02d" % key), t.get("id")))

    if args.json:
        print(json.dumps({
            "registries": {lbl: p for lbl, p in regs},
            "per_fleet_enabled": {lbl: sum(1 for t in enabled if t.get("_fleet") == lbl)
                                  for lbl, _ in regs},
            "total": len(tasks), "enabled": len(enabled), "disabled": len(disabled),
            "never_ran": [t.get("id") for t in never_ran],
            "onetime": [t.get("id") for t in onetime],
            "expired_onetime": [t.get("id") for t in expired],
            "total_skip_events": total_skip_events,
            "tasks_with_skips": skip_counts,
            "collisions": collisions,
            "am_pileup_count": len(am_pileup),
        }, indent=2))
        sys.exit(0)

    print("ORA FLEET STATUS  (DUAL-FLEET: cc = claude-code-sessions/MCP · lams = local-agent-mode-sessions/Cowork)")
    for lbl, p in regs:
        print("registry[%s]: %s" % (lbl, p))
    print("=" * 84)
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
            last = (t.get("lastRunAt") or "NEVER")[:19]
            print("%-42s %-5s %-16s %-4s %-5s %s" % (tid, t.get("_fleet", "?"), cron, en, sk, last))
        print("-" * 84)

    print("\nHEALTH SUMMARY")
    per_fleet = {lbl: sum(1 for t in enabled if t.get("_fleet") == lbl) for lbl, _ in regs}
    print("  total tasks ........ %d   (enabled %d / disabled %d)  per-fleet enabled: %s"
          % (len(tasks), len(enabled), len(disabled),
             ", ".join("%s=%d" % kv for kv in per_fleet.items())))
    print("  never-ran .......... %d   %s" % (len(never_ran), ", ".join(sorted(t.get("id") for t in never_ran)) or "-"))
    print("  one-time fireAt .... %d   %s" % (len(onetime), ", ".join(sorted(t.get("id") for t in onetime)) or "-"))
    print("  EXPIRED one-time ... %d   %s" % (len(expired), ", ".join(sorted(t.get("id") for t in expired)) or "-"))
    print("  throttle skips ..... %d events across %d tasks" % (total_skip_events, len(skip_counts)))
    if skip_counts:
        top = sorted(skip_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print("                       top: %s" % ", ".join("%s=%d" % (k, v) for k, v in top))
    print("  same-time collisions %d   %s" % (len(collisions),
          "; ".join("%s:{%s}" % (k, ",".join(v)) for k, v in sorted(collisions.items())) or "-"))
    print("  AM pileup (05-0930). %d tasks" % len(am_pileup))

    # health verdict (non-fatal; reporting tool)
    flags = []
    if len(never_ran) > 0: flags.append("%d never-ran" % len(never_ran))
    if len(expired) > 0: flags.append("%d expired one-time" % len(expired))
    if total_skip_events > 0: flags.append("%d throttle skips (over ceiling)" % total_skip_events)
    if collisions: flags.append("%d schedule collisions" % len(collisions))
    print("\n  VERDICT: %s" % ("OK" if not flags else "ATTENTION -- " + "; ".join(flags)))
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""ORA fleet cleanup — STAGE 3 (post-consolidation polish). Phase 3.

RUN WITH THE CLAUDE APP FULLY CLOSED (tray -> Exit). The app owns the scheduler registry
and reloads it on relaunch; live hand-edits get clobbered. This script aborts if claude.exe
is running. Idempotent + backed up + atomic + MSIX-aware registry auto-discovery (no hardcoded GUID, I4).

WHAT THIS DOES (two small, safe polish ops left over from the Stage-2 swap):
  1. RETIME  loopnet-autoreply  0 8,13,17 * * *  ->  0 8,17 * * *   (3x/day -> 2x/day per plan)
  2. PRUNE   recordedSkips      remove every key whose task id is NOT in the live scheduledTasks
             set -- these are stale skip-telemetry entries for tasks deleted in Stage 2
             (ora-inbox-pre-brief, ora-cash-position-snapshot, ora-sharepoint-aging-...,
             ora-artifact-staleness-scan, ora-outbox-qc-sweep, ora-session-pruner,
             ora-claude-workspace-hygiene, ora-treasury-yield-prefetch). Leaves live-task
             skip history intact (loopnet-autoreply, ora-cowork-heartbeat, etc.).

SAFETY: app-closed guard; backup + atomic write (temp -> os.replace); --dry-run preview;
idempotent (cron already-target -> skip; no dead skip-keys -> skip). Touches ONLY the
loopnet cron and dead recordedSkips keys; never adds/deletes a task; never edits any other field.

USAGE:
  python ~/.claude/maintenance/stage3-cleanup.py --dry-run   # preview, writes nothing
  python ~/.claude/maintenance/stage3-cleanup.py             # apply (app must be closed)
After applying: relaunch Claude, then `python ~/.claude/maintenance/fleet-status.py`
(expect throttle-skips to drop to the live-task remainder, loopnet at 2x/day).
"""
import os, sys, json, glob, subprocess, datetime, tempfile, shutil

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")

# --- cleanup spec -----------------------------------------------------------
RETIME = {"loopnet-autoreply": "0 8,17 * * *"}   # 3x/day -> 2x/day

def claude_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "claude.exe" in out
    except Exception:
        return True  # fail safe

def discover_registry():
    r"""GUID-agnostic, works from an external terminal OR in Claude's MSIX container.
    External: %LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\Claude\local-agent-mode-sessions\...
    In-container: %APPDATA%\Claude\... (virtualized). Search both; pick biggest+newest."""
    la = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
    ra = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
    bases = [
        os.path.join(la, "Packages", "Claude*", "LocalCache", "Roaming", "Claude", "local-agent-mode-sessions"),
        os.path.join(ra, "Claude", "local-agent-mode-sessions"),
    ]
    seen, scored = set(), []
    for base in bases:
        for p in glob.glob(os.path.join(base, "**", "scheduled-tasks.json"), recursive=True):
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            try:
                n = len(json.load(open(p, encoding="utf-8")).get("scheduledTasks", []) or [])
                if n > 0:
                    scored.append((n, os.path.getmtime(p), p))
            except Exception:
                continue
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2] if scored else None

def main():
    dry = "--dry-run" in sys.argv
    if not dry and claude_running():
        print("ABORT: claude.exe is running. Fully quit Claude (tray -> Exit) and re-run.")
        print("       (Use --dry-run to preview the plan while the app is open.)")
        sys.exit(1)

    reg = discover_registry()
    if not reg:
        sys.stderr.write("[ACTION] stage3-cleanup: live LAMS registry not found. Nothing changed.\n")
        sys.exit(3)
    print("Registry: %s" % reg)

    d = json.load(open(reg, encoding="utf-8"))
    tasks = d.get("scheduledTasks", [])
    by_id = {t.get("id"): t for t in tasks}
    live_ids = set(by_id)

    # ---- plan RETIME -----------------------------------------------------
    retimes, retime_noop, retime_absent = [], [], []
    for tid, new_cron in RETIME.items():
        t = by_id.get(tid)
        if t is None:
            retime_absent.append(tid)
        elif t.get("cronExpression") == new_cron:
            retime_noop.append(tid)
        else:
            retimes.append((tid, t.get("cronExpression"), new_cron))

    # ---- plan PRUNE recordedSkips ---------------------------------------
    rs = d.get("recordedSkips", {})
    rs_is_dict = isinstance(rs, dict)
    dead_keys, dead_skip_count = [], 0
    if rs_is_dict:
        for k, v in rs.items():
            if k not in live_ids:
                dead_keys.append(k)
                dead_skip_count += (len(v) if isinstance(v, (list, dict)) else 1)
    live_skip_count = 0
    if rs_is_dict:
        for k, v in rs.items():
            if k in live_ids:
                live_skip_count += (len(v) if isinstance(v, (list, dict)) else 1)

    # ---- report ----------------------------------------------------------
    print("\n=== PLAN ===")
    print("RETIME (%d): %s" % (len(retimes), ", ".join("%s %s->%s" % r for r in retimes) or "—"))
    if retime_noop: print("  already at target cron (skip): %s" % ", ".join(retime_noop))
    if retime_absent: print("  not in fleet (skip): %s" % ", ".join(retime_absent))
    if not rs_is_dict:
        print("PRUNE recordedSkips: field is %s, not a dict — skipping prune (no-op)." % type(rs).__name__)
    else:
        print("PRUNE recordedSkips (%d dead keys, %d stale skip events): %s"
              % (len(dead_keys), dead_skip_count, ", ".join(sorted(dead_keys)) or "—"))
        print("  kept (live-task skip history, %d events): %s"
              % (live_skip_count, ", ".join(sorted(k for k in rs if k in live_ids)) or "—"))

    changed = bool(retimes or dead_keys)
    if dry:
        print("\n--dry-run: no changes written.")
        sys.exit(0)
    if not changed:
        print("\nNothing to do — already clean (idempotent no-op).")
        sys.exit(0)

    # ---- backup ----------------------------------------------------------
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bdir = os.path.join(HOME, ".claude", "backups", "fleet-cleanup-stage3-" + stamp)
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(reg, os.path.join(bdir, "LAMS__scheduled-tasks.json"))
    with open(os.path.join(bdir, "MANIFEST.txt"), "w", encoding="utf-8") as m:
        m.write("registry: %s\nbytes: %d\nsaved: %sZ\nretimed: %s\npruned_skip_keys: %s\n" % (
                reg, os.path.getsize(reg), datetime.datetime.utcnow().isoformat(),
                ",".join("%s:%s" % (r[0], r[2]) for r in retimes), ",".join(sorted(dead_keys))))
    print("\nBackup: %s" % bdir)

    # ---- mutate ----------------------------------------------------------
    for tid, _old, new_cron in retimes:
        by_id[tid]["cronExpression"] = new_cron
    if rs_is_dict and dead_keys:
        d["recordedSkips"] = {k: v for k, v in rs.items() if k in live_ids}

    # ---- atomic write ----------------------------------------------------
    dir_ = os.path.dirname(reg)
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        os.replace(tmp, reg)
    except Exception:
        try: os.unlink(tmp)
        except Exception: pass
        raise

    print("APPLIED. loopnet retimed=%d; pruned %d dead skip-keys (%d stale events); %d live skip-events kept."
          % (len(retimes), len(dead_keys), dead_skip_count, live_skip_count))
    print("Relaunch Claude, then run: python ~/.claude/maintenance/fleet-status.py")
    sys.exit(0)

if __name__ == "__main__":
    main()

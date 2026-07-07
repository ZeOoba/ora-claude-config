#!/usr/bin/env python3
r"""ORA fleet consolidation — STAGE 2 (the 6 SKILL.md merges). Phase 3 Stage 2.

RUN WITH THE CLAUDE APP FULLY CLOSED (tray -> Exit). The app owns the scheduler registry
and reloads it on relaunch; live hand-edits get clobbered. This script aborts if claude.exe
is running. Idempotent + backed up + atomic + auto-discovers the registry (no hardcoded GUID, I4).

WHAT THIS DOES (one app-closed run applies the whole Stage-2 swap):
  ADD 5 merged tasks (each authored & verified on disk; perms UNIONed from its sources):
    ora-am-brief            0 6 * * *            (daily; branches AM internally)
    ora-pm-ledger           0 18 * * *           (daily; branches PM internally)
    ora-quarterly-compliance 0 9 1 1,4,7,10 *    (quarterly)
    ora-weekly-hygiene      0 20 * * 0           (Sunday)
    ora-health-guard        15 5 * * *           (daily pre-morning)
  RETIME:
    ora-dashboard-refresh   0 7,13 * * *  ->  0 7 * * *   (kept on ECharts; React retarget deferred to Phase 2/G1)
  DELETE 21 source/dead tasks:
    19 folded sources (only if their replacement merged task will EXIST after this run) +
    ora-dashboard-finish (killed; tombstoned) + ora-connector-recovery-ratification-check (dropped; obsolete).
  KEEP explicitly (NEVER touched here): ora-dormant-thread-revival, ora-automation-health-monitor.

SAFETY INVARIANTS:
  - Aborts if claude.exe is running.
  - REFUSES to ADD a merged task whose SKILL.md is missing on disk.
  - REFUSES to DELETE a folded source unless its replacement merged task is present post-run
    (an explicit kill list — dashboard-finish, recovery-ratification — has no such guard).
  - Idempotent: present merged task -> skip add (no perm clobber); absent source -> skip delete.
  - Backup (LAMS registry) + atomic write (temp -> os.replace). Fully reversible from the backup.

USAGE:
  python ~/.claude/maintenance/apply-fleet-consolidation-stage2.py --dry-run   # preview, writes nothing
  python ~/.claude/maintenance/apply-fleet-consolidation-stage2.py             # apply (app must be closed)
After applying: relaunch Claude, then `python ~/.claude/maintenance/fleet-status.py`.

POST-RUN TODOs (not automated — flagged in the event log):
  - Update ora-automation-health-monitor's producer/expected-fire task names to the merged fleet.
  - Update SoR §1 + session-start active-context: fleet-health email is now '[ORA] Health Guard' (05:15),
    not the cc-implementation-verifier (07:45).
"""
import os, sys, json, glob, subprocess, datetime, time, tempfile

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")
SKILL_ROOT = os.path.join(
    HOME, "OneDrive - Oxford Capital Partners", "Documents", "Claude", "Scheduled")

def skill_path(task_id):
    return os.path.join(SKILL_ROOT, task_id, "SKILL.md")

# --- merge spec -------------------------------------------------------------
# Each ADD: new task id -> {cron, sources:[ids to union perms from + delete]}
ADD = {
    "ora-am-brief": {
        "cron": "0 6 * * *",
        "sources": ["ora-daily-brief-6am", "ora-inbox-pre-brief",
                    "ora-treasury-yield-prefetch", "ora-cash-position-snapshot"],
    },
    "ora-pm-ledger": {
        "cron": "0 18 * * *",
        "sources": ["ora-notion-daily-digest", "ora-outbox-qc-sweep", "ora-eod-action-ledger"],
    },
    "ora-quarterly-compliance": {
        "cron": "0 9 1 1,4,7,10 *",
        "sources": ["ora-lender-covenant-tracker", "ora-insurance-renewal-tracker",
                    "ora-tax-appeal-calendar", "ora-cre-data-mcp-recheck"],
    },
    "ora-weekly-hygiene": {
        "cron": "0 20 * * 0",
        "sources": ["ora-claude-workspace-hygiene", "onedrive-cleanup",
                    "ora-sharepoint-aging-freshness-check", "ora-artifact-staleness-scan",
                    "ora-session-pruner"],
    },
    "ora-health-guard": {
        "cron": "15 5 * * *",
        "sources": ["scheduled-task-integrity-guard", "ora-connector-preflight-guard",
                    "ora-cc-implementation-verifier"],
    },
}

# RETIME: task id -> new cron (idempotent)
RETIME = {"ora-dashboard-refresh": "0 7 * * *"}

# DELETE with NO replacement guard (explicit kills): always safe to remove.
KILL = ["ora-dashboard-finish", "ora-connector-recovery-ratification-check"]

# Tasks that must NEVER be deleted by this script (defense-in-depth assertion).
NEVER_DELETE = {"ora-dormant-thread-revival", "ora-automation-health-monitor",
                "ora-dashboard-refresh"}

def claude_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "claude.exe" in out
    except Exception:
        return True  # fail safe

def discover_registry():
    r"""Find the live LAMS registry, GUID-agnostically, from EITHER an external terminal
    OR inside Claude's app container. Claude is an MSIX/Store-packaged app: from an external
    cmd.exe the live registry lives under %LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\
    Claude\local-agent-mode-sessions\... ; inside the container that same data appears under
    %APPDATA%\Claude\... (virtualized). Search both; pick the biggest+newest. No hardcoded GUID (I4)."""
    la = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
    ra = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
    bases = [
        # MSIX-packaged live path (correct from an EXTERNAL terminal); Claude* keeps it GUID/hash-agnostic
        os.path.join(la, "Packages", "Claude*", "LocalCache", "Roaming", "Claude", "local-agent-mode-sessions"),
        # non-packaged / in-container virtualized view
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

def union_perms(source_tasks):
    """Union approvedPermissions + userSelectedFolders across source tasks, deduped."""
    perms, seen_p = [], set()
    folders, seen_f = [], set()
    for t in source_tasks:
        for p in (t.get("approvedPermissions") or []):
            k = json.dumps(p, sort_keys=True)
            if k not in seen_p:
                seen_p.add(k); perms.append(p)
        for fdr in (t.get("userSelectedFolders") or []):
            k = json.dumps(fdr, sort_keys=True)
            if k not in seen_f:
                seen_f.add(k); folders.append(fdr)
    return perms, folders

def main():
    dry = "--dry-run" in sys.argv
    if not dry and claude_running():
        print("ABORT: claude.exe is running. Fully quit Claude (tray -> Exit) and re-run.")
        print("       (Use --dry-run to preview the plan while the app is open.)")
        sys.exit(1)

    reg = discover_registry()
    if not reg:
        sys.stderr.write("[ACTION] fleet-consolidation-stage2: live LAMS registry not found. Nothing changed.\n")
        sys.exit(3)
    print("Registry: %s" % reg)

    d = json.load(open(reg, encoding="utf-8"))
    tasks = d.get("scheduledTasks", [])
    before = len(tasks)
    by_id = {t.get("id"): t for t in tasks}

    # ---- plan ADD --------------------------------------------------------
    to_add, add_skip_present, add_refuse_missing = [], [], []
    will_exist_merged = set()  # merged ids present after this run
    for mid, spec in ADD.items():
        if mid in by_id:
            add_skip_present.append(mid)
            will_exist_merged.add(mid)         # already there -> present post-run
            continue
        if not os.path.isfile(skill_path(mid)):
            add_refuse_missing.append(mid)     # cannot add without its SKILL.md
            continue
        srcs = [by_id[s] for s in spec["sources"] if s in by_id]
        perms, folders = union_perms(srcs)
        now_ms = int(time.time() * 1000)
        to_add.append({
            "id": mid,
            "cronExpression": spec["cron"],
            "enabled": True,
            "filePath": skill_path(mid),
            "createdAt": now_ms,
            "lastRunAt": None,
            "lastScheduledFor": None,
            "userSelectedFolders": folders,
            "approvedPermissions": perms,
        })
        will_exist_merged.add(mid)

    # ---- plan DELETE -----------------------------------------------------
    # Folded sources: delete ONLY if their replacement merged task exists post-run.
    src_to_merged = {s: mid for mid, spec in ADD.items() for s in spec["sources"]}
    del_ids, del_blocked, del_absent = set(), [], []
    for s, mid in src_to_merged.items():
        if s not in by_id:
            del_absent.append(s)
        elif mid in will_exist_merged:
            del_ids.add(s)
        else:
            del_blocked.append((s, mid))       # replacement not present -> keep source
    # Explicit kills (no replacement guard)
    for k in KILL:
        if k in by_id:
            del_ids.add(k)
        else:
            del_absent.append(k)
    # Defense-in-depth: never delete a protected task
    bad = del_ids & NEVER_DELETE
    if bad:
        sys.stderr.write("ABORT: refusing to delete protected task(s): %s\n" % ", ".join(sorted(bad)))
        sys.exit(2)

    # ---- plan RETIME -----------------------------------------------------
    retimes, retime_noop = [], []
    for tid, new_cron in RETIME.items():
        t = by_id.get(tid)
        if t is None:
            continue
        if t.get("cronExpression") == new_cron:
            retime_noop.append(tid)
        else:
            retimes.append((tid, t.get("cronExpression"), new_cron))

    # ---- report ----------------------------------------------------------
    print("\n=== PLAN ===")
    print("ADD (%d): %s" % (len(to_add), ", ".join(a["id"] for a in to_add) or "—"))
    if add_skip_present: print("  already present (idempotent skip): %s" % ", ".join(add_skip_present))
    if add_refuse_missing: print("  REFUSED (SKILL.md missing on disk): %s" % ", ".join(add_refuse_missing))
    print("RETIME (%d): %s" % (len(retimes),
          ", ".join("%s %s->%s" % r for r in retimes) or "—"))
    if retime_noop: print("  already at target cron (skip): %s" % ", ".join(retime_noop))
    print("DELETE (%d): %s" % (len(del_ids), ", ".join(sorted(del_ids)) or "—"))
    if del_blocked:
        print("  BLOCKED (replacement merged task not present — source KEPT): %s"
              % ", ".join("%s(needs %s)" % b for b in del_blocked))
    if del_absent: print("  already absent (idempotent skip): %s" % ", ".join(sorted(set(del_absent))))
    print("KEEP separate (untouched): ora-dormant-thread-revival, ora-automation-health-monitor")

    if add_refuse_missing:
        sys.stderr.write("\n[ACTION] One or more merged SKILL.md files are missing — fix before applying. Nothing written.\n")
        sys.exit(4)

    after = before + len(to_add) - len(del_ids)
    print("\nTasks: %d -> %d  (+%d add, -%d delete)" % (before, after, len(to_add), len(del_ids)))

    if dry:
        print("\n--dry-run: no changes written.")
        sys.exit(0)

    if not to_add and not del_ids and not retimes:
        print("\nNothing to do — registry already consolidated (idempotent no-op).")
        sys.exit(0)

    # ---- backup ----------------------------------------------------------
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bdir = os.path.join(HOME, ".claude", "backups", "fleet-consolidation-stage2-" + stamp)
    os.makedirs(bdir, exist_ok=True)
    import shutil
    shutil.copy2(reg, os.path.join(bdir, "LAMS__scheduled-tasks.json"))
    with open(os.path.join(bdir, "MANIFEST.txt"), "w", encoding="utf-8") as m:
        m.write("registry: %s\nbytes: %d\nsaved: %sZ\nbefore: %d\nafter: %d\n"
                "added: %s\ndeleted: %s\nretimed: %s\n" % (
                reg, os.path.getsize(reg), datetime.datetime.utcnow().isoformat(),
                before, after, ",".join(a["id"] for a in to_add),
                ",".join(sorted(del_ids)), ",".join("%s:%s" % (r[0], r[2]) for r in retimes)))
    print("Backup: %s" % bdir)

    # ---- mutate ----------------------------------------------------------
    new_tasks = [t for t in tasks if t.get("id") not in del_ids]
    for tid, _old, new_cron in retimes:
        for t in new_tasks:
            if t.get("id") == tid:
                t["cronExpression"] = new_cron
    new_tasks.extend(to_add)
    d["scheduledTasks"] = new_tasks

    # ---- atomic write (temp -> os.replace) ------------------------------
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

    print("\nAPPLIED. Tasks: %d -> %d." % (before, len(new_tasks)))
    print("Relaunch Claude, then run: python ~/.claude/maintenance/fleet-status.py")
    print("POST-RUN TODO: update ora-automation-health-monitor task-name refs + the SoR/active-context "
          "fleet-health-email pointer ([ORA] Health Guard @05:15, not cc-verifier @07:45).")
    sys.exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""ORA CC Implementation Verifier — deterministic probe.

Reads the actual bytes on disk + BOTH live scheduler registries (dual-fleet
doctrine 2026-06-10: claude-code-sessions = CC/MCP fleet, local-agent-mode-sessions
= LAMS/Cowork fleet — both auto-discovered, both LIVE) and prints a PASS/FAIL
table for each optimization end-state. No LLM judgment, no edits.
Exit code 0 = all pass, 1 = one or more FAIL. The scheduled task runs this and
emails the table (subject prefix [ACTION] on any FAIL).
"""
import json, os, subprocess, sys

CLAUDE = r"C:\Users\Owner\.claude"
PROJ   = os.path.join(CLAUDE, r"projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners")
# DUAL-FLEET (2026-06-10): local-agent-mode-sessions (LAMS) is the LIVE Cowork
# fleet registry, NOT orphaned. Discovery consolidated 2026-07-09 into
# maintenance/_shared/store_discovery.py (roots in scheduler-stores.json --
# a store move is a one-file edit there, not here).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: callers treat '' as store-absent

def _discover_store(store):
    """Delegates to _shared/store_discovery; '' when the helper or store is
    unavailable (this probe's callers use '' as the absent sentinel)."""
    return (_sd.discover_store(store) if _sd else None) or ""

LAMS = _discover_store("local-agent-mode-sessions")

def read(p):
    try:
        with open(p, encoding="utf-8") as f: return f.read()
    except Exception:
        return ""

def jload(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

results = []  # (id, ok, detail)
def check(cid, ok, detail):
    results.append((cid, bool(ok), detail))

# V1 keybinding
kb = jload(os.path.join(CLAUDE, "keybindings.json")) or {}
try:
    u = kb["bindings"][0]["bindings"].get("ctrl+shift+u")
except Exception:
    u = None
check("V1 keybinding", u == "skill:acquisition-underwriting", f"ctrl+shift+u={u}")

# Rube scrub — STRICT check only on machine-readable approval lists / registry
# (prose files like reference_tech.md legitimately DOCUMENT Rube as retired).
rube_targets = {
    "settings.json": os.path.join(CLAUDE, "settings.json"),
    "project settings.json": os.path.join(PROJ, "settings.json"),
    "onedrive settings.local": r"C:\Users\Owner\OneDrive - Oxford Capital Partners\.claude\settings.local.json",
    "LAMS registry": LAMS,
}
rube_hits = [n for n, p in rube_targets.items() if ("d6315173" in read(p) or "RUBE_" in read(p))]
check("V4 Rube scrubbed (approvals)", not rube_hits, "no Rube approvals" if not rube_hits else f"RUBE in: {rube_hits}")
# Prose guard: CLAUDE.md must not list Rube as an ACTIVE dedicated MCP / send route.
cm_txt = read(os.path.join(CLAUDE, "CLAUDE.md"))
prose_bad = "Netlify, Rube)" in cm_txt or "prefer Rube" in cm_txt or "Rube scheduler" in cm_txt
check("V4 Rube not active in CLAUDE.md", not prose_bad, "documented-retired only" if not prose_bad else "Rube still listed active")

# Gmail scrubbed (Outlook-only)
gm = "8ac87555" in read(os.path.join(CLAUDE, "settings.json")) or "Gmail (8ac87555)" in read(os.path.join(PROJ, r"memory\tech.md"))
check("Gmail removed (Outlook-only)", not gm, "no Gmail" if not gm else "Gmail still referenced")

# node_modules deny
s = read(os.path.join(CLAUDE, "settings.json"))
check("V9 node_modules Read-deny", "node_modules" in s, "present" if "node_modules" in s else "MISSING")

# V8 read-only Outlook allowlisted (global)
# Outlook READ via the M365 connector (c0ea3c01). The composio-ora OUTLOOK_* perms
# were removed 2026-06-11 with the connector; M365 search tools are the read path now.
check("V8 Outlook read allowlisted", "outlook_email_search" in s and "outlook_calendar_search" in s, "M365 read tools (global scope)")

# Confidentiality guard + SessionStart
guard = os.path.exists(os.path.join(CLAUDE, r"hooks\confidentiality-guard.py"))
sj = jload(os.path.join(CLAUDE, "settings.json")) or {}
hooks = sj.get("hooks", {})
guard_wired = any("confidentiality-guard" in json.dumps(m) for m in hooks.get("PreToolUse", []))
ss = "SessionStart" in hooks and os.path.exists(os.path.join(CLAUDE, "session-context.md"))
check("Confidentiality guard", guard and guard_wired, "script+wired" if guard and guard_wired else "MISSING")
check("SessionStart context hook", ss, "present" if ss else "MISSING")

# Email send path policy — COM-only since 2026-06-11 (Composio fallback retired).
# Verify the SOLE-path doctrine is present and no ACTIVE Composio fallback remains
# (Composio may still appear in negative "do NOT route through Composio (gone)" prose).
ed = read(os.path.join(CLAUDE, r"scheduled-tasks\_shared\EMAIL_DELIVERY.md"))
com_only = bool(ed) and ("SOLE send path" in ed and "send-via-outlook.ps1" in ed
                         and "fall back to Composio" not in ed
                         and "fallback to Composio" not in ed)
check("Email COM-only (Composio fallback retired)", com_only,
      "COM sole path; no active Composio fallback" if com_only else "send-path policy drift")

# OXFORDRA_REPO
pj = jload(os.path.join(PROJ, "settings.json")) or {}
repo = (pj.get("env", {}) or {}).get("OXFORDRA_REPO", "")
repo_ok = repo == "C:/Users/Owner/website-canonical" and os.path.isdir(repo)
remote = ""
if os.path.isdir(os.path.join(repo, ".git")) if repo else False:
    try:
        remote = subprocess.run(["git", "-C", repo, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    except Exception:
        remote = ""
check("V10 OXFORDRA_REPO canonical", repo_ok and "ZeOoba/Website" in remote, f"{repo} -> {remote}")

# ---- Live scheduler fleets (DUAL-FLEET doctrine 2026-06-10) ----
# CC/MCP fleet = claude-code-sessions registry (scheduled-tasks MCP).
# LAMS/Cowork fleet = local-agent-mode-sessions registry (Cowork-created tasks:
# om-intake-ocr, replacement-cost-refresh, cowork-heartbeat, skill-store-drift-check;
# the integrity-guard twin was retired 2026-06-11). Both LIVE; Cowork-created tasks
# land in LAMS by platform design.
def discover_live_store():
    p = _discover_store("claude-code-sessions")
    return (p, jload(p)) if p else (None, None)

# ora-setup-audit RETIRED 2026-06-16 (strategic-audit kill: daily cadence overkill,
# overlaps ora-health-guard's pre-session probe suite); archived 2026-07-07, on the
# event_log ratified-retirements list. Its probes are absorbed by the guard trio
# (ora-health-guard + ora-task-integrity-guard + ora-doctrine-integrity-guard). Dropped here.
# ora-cowork-heartbeat joined 2026-10-30: migrated LAMS -> CC (the dead-man producer must live
# on the fleet that actually fires); the union check below still finds it on either fleet.
EXPECTED_FLEET = {"ora-am-brief", "ora-health-guard",
                  "ora-pm-ledger", "ora-deal-sourcing-scan", "ora-cowork-heartbeat"}
live_path, live = discover_live_store()
live_tasks = (live or {}).get("scheduledTasks", []) or []
live_enabled = {t.get("id") for t in live_tasks if t.get("enabled")}
# EXPECTED_FLEET spans BOTH fleets: ora-am-brief is a Cowork/Daily-Brief task that
# lives in LAMS by design (2026-07-09) — check membership against the union so a
# correctly-placed LAMS task isn't false-flagged as a dark CC task.
_lams_pre = jload(LAMS) or {}
_lams_pre_enabled = {t.get("id") for t in (_lams_pre.get("scheduledTasks", []) or []) if t.get("enabled")}
missing = EXPECTED_FLEET - (live_enabled | _lams_pre_enabled)
check("Live fleet present (dual-fleet)", live_path is not None and not missing,
      (f"{len(live_enabled)} enabled in claude-code-sessions") + (f" MISSING {sorted(missing)}" if missing else ""))
check("Live fleet Rube-free", live is not None and not ("d6315173" in json.dumps(live) or "RUBE_" in json.dumps(live)), "clean")
bad_paths = [t.get("id") for t in live_tasks if not os.path.isfile(t.get("filePath", ""))]
check("Live SKILL files present", live_path is not None and not bad_paths,
      "all filePaths resolve" if not bad_paths else f"missing: {bad_paths}")
lams = jload(LAMS) or {}
lams_tasks = (lams or {}).get("scheduledTasks", []) or []
lams_enabled = {t.get("id") for t in lams_tasks if t.get("enabled")}
# LAMS expected set (2026-06-14): the LAMS integrity twin `scheduled-task-integrity-guard`
# was RETIRED 2026-06-11 — the CC task `ora-task-integrity-guard` is now the SOLE integrity
# runner — so it is dropped here. `ora-skill-store-drift-check` is the live 4th LAMS task.
# ora-cowork-heartbeat left this set 2026-10-30 (migrated to CC; now in EXPECTED_FLEET).
EXPECTED_LAMS = {"ora-om-intake-ocr", "ora-replacement-cost-refresh",
                 "ora-skill-store-drift-check"}
lams_missing = EXPECTED_LAMS - lams_enabled
check("LAMS/Cowork fleet present", bool(LAMS) and not lams_missing,
      (f"{len(lams_enabled)} enabled in local-agent-mode-sessions")
      + (f" MISSING {sorted(lams_missing)}" if lams_missing else ""))
lams_bad = [t.get("id") for t in lams_tasks
            if t.get("enabled") and not os.path.isfile(t.get("filePath", ""))]
check("LAMS SKILL files present", bool(LAMS) and not lams_bad,
      "all filePaths resolve" if not lams_bad else f"missing: {lams_bad}")

# Advisories -- surfaced for the operator, NON-GATING (do not flip the suite to [ACTION]).
notes = []
# Fleet baseline RE-SET 2026-06-09 (Gabriel): 14 live tasks (5 core + 9 ops). The 8 Tier-2
# internal tasks (lease-expiration-dashboard, monthly-close-kickoff, debt-maturity-snapshot,
# tenant-at-risk-monthly, quarterly-compliance, monthly-checklist-formula-audit,
# pm-ar-export-freshness-check, distress-signal-monitor) were RETIRED by decision — archived to
# _archive_2026-06-09_retired in all four stores; do NOT re-register. Regression tripwire: alert
# if the live fleet silently shrinks below the decided floor (a re-orphaning / migration drop).
# Floor RECALIBRATED 14 -> 13 on 2026-07-09: Gabriel ratified the CC->LAMS consolidation
# that moved ora-setup-audit + siblings off the CC fleet. The ratified floors now live in
# _shared/scheduler-stores.json (single source of truth) -- recalibrate THERE, not here;
# the literals below are only the fail-open fallback if the config is unreadable.
RESTORED_FLEET_FLOOR = _sd.fleet_floor("cc", 13) if _sd else 13
if len(live_tasks) < RESTORED_FLEET_FLOOR:
    notes.append(f"CC fleet = {len(live_tasks)}; expected >= {RESTORED_FLEET_FLOOR} per the 2026-07-09 ratified post-consolidation baseline -- a task may have gone dark (check the scheduled-tasks MCP store).")
# LAMS floor (2026-06-10): 4 recurring Cowork tasks. A drop below = a rebuild/
# migration silently removed registry entries (the exact failure that left the
# heartbeat dark 2026-05-31..06-10).
LAMS_FLEET_FLOOR = _sd.fleet_floor("lams", 4) if _sd else 4
lams_recurring = [t for t in lams_tasks if t.get("enabled") and t.get("cronExpression")]
if len(lams_recurring) < LAMS_FLEET_FLOOR:
    notes.append(f"LAMS fleet = {len(lams_recurring)} enabled recurring; expected >= {LAMS_FLEET_FLOOR} (om-intake-ocr, replacement-cost-refresh, cowork-heartbeat, skill-store-drift-check) -- a registry drop may have recurred.")

# ---- output ----
npass = sum(1 for _, ok, _ in results if ok)
print(f"ORA CC Implementation Verifier — {npass}/{len(results)} PASS")
print("-" * 72)
for cid, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {cid:34s} {detail}")
print("-" * 72)
if notes:
    print("ADVISORIES (non-gating):")
    for n in notes:
        print("  - " + n)
    print("-" * 72)
fails = [c for c, ok, _ in results if not ok]
print("ALL PASS" if not fails else "FAIL: " + ", ".join(fails))
sys.exit(0 if not fails else 1)

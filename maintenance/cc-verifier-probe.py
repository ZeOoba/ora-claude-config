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
PROJ   = os.path.join(CLAUDE, r"projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-")
# DUAL-FLEET (2026-06-10): local-agent-mode-sessions (LAMS) is the LIVE Cowork
# fleet registry, NOT orphaned. Both stores are discovered dynamically (I4: GUIDs
# rotate, never hardcode; the MSIX LocalCache path mirrors Roaming -- one per store).
import glob as _glob0

def _discover_store(store):
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    localap = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    bases = [os.path.join(appdata, "Claude", store),
             os.path.join(localap, "Packages", "Claude_pzs8sxrjxfjjc", "LocalCache",
                          "Roaming", "Claude", store)]
    best = None
    for base in bases:
        for p in _glob0.glob(os.path.join(base, "**", "scheduled-tasks.json"), recursive=True):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            n = len(d.get("scheduledTasks", []) or [])
            if n and (best is None or (n, os.path.getmtime(p)) > best[0]):
                best = ((n, os.path.getmtime(p)), p)
    return best[1] if best else ""

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
    "onedrive settings.local": r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\.claude\settings.local.json",
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
# CC/MCP fleet = claude-code-sessions registry (scheduled-tasks MCP, 14 tasks).
# LAMS/Cowork fleet = local-agent-mode-sessions registry (Cowork-created tasks:
# om-intake-ocr, replacement-cost-refresh, cowork-heartbeat, integrity-guard).
# Both LIVE; Cowork-created tasks land in LAMS by platform design.
def discover_live_store():
    p = _discover_store("claude-code-sessions")
    return (p, jload(p)) if p else (None, None)

EXPECTED_FLEET = {"ora-am-brief", "ora-setup-audit", "ora-health-guard",
                  "ora-pm-ledger", "ora-deal-sourcing-scan"}
live_path, live = discover_live_store()
live_tasks = (live or {}).get("scheduledTasks", []) or []
live_enabled = {t.get("id") for t in live_tasks if t.get("enabled")}
missing = EXPECTED_FLEET - live_enabled
check("Live fleet present (MCP store)", live_path is not None and not missing,
      (f"{len(live_enabled)} enabled in claude-code-sessions") + (f" MISSING {sorted(missing)}" if missing else ""))
check("Live fleet Rube-free", live is not None and not ("d6315173" in json.dumps(live) or "RUBE_" in json.dumps(live)), "clean")
bad_paths = [t.get("id") for t in live_tasks if not os.path.isfile(t.get("filePath", ""))]
check("Live SKILL files present", live_path is not None and not bad_paths,
      "all filePaths resolve" if not bad_paths else f"missing: {bad_paths}")
lams = jload(LAMS) or {}
lams_tasks = (lams or {}).get("scheduledTasks", []) or []
lams_enabled = {t.get("id") for t in lams_tasks if t.get("enabled")}
EXPECTED_LAMS = {"ora-om-intake-ocr", "ora-replacement-cost-refresh",
                 "ora-cowork-heartbeat", "scheduled-task-integrity-guard"}
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
RESTORED_FLEET_FLOOR = 14
if len(live_tasks) < RESTORED_FLEET_FLOOR:
    notes.append(f"CC fleet = {len(live_tasks)}; expected >= {RESTORED_FLEET_FLOOR} per the 2026-06-09 decided baseline (8 Tier-2 tasks retired) -- tasks may have gone dark (check the scheduled-tasks MCP store).")
# LAMS floor (2026-06-10): 4 recurring Cowork tasks. A drop below = a rebuild/
# migration silently removed registry entries (the exact failure that left the
# heartbeat dark 2026-05-31..06-10).
LAMS_FLEET_FLOOR = 4
lams_recurring = [t for t in lams_tasks if t.get("enabled") and t.get("cronExpression")]
if len(lams_recurring) < LAMS_FLEET_FLOOR:
    notes.append(f"LAMS fleet = {len(lams_recurring)} enabled recurring; expected >= {LAMS_FLEET_FLOOR} (om-intake-ocr, replacement-cost-refresh, cowork-heartbeat, integrity-guard) -- a registry drop may have recurred.")

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

#!/usr/bin/env python3
r"""ORA fleet send-path normalizer (Phase 3 remediation).

Fixes the fleet-wide bug: ~18 scheduled tasks route email through the dead
`mcp__8a611864-…__COMPOSIO_*` wrapper (not a connected server). Repoints routing to the
canonical path (send-via-outlook.ps1 PRIMARY -> composio-ora fallback) via EXACT-STRING
replacements only (no regex), so prose is never mangled. Touches ONLY an explicit allowlist
of broken files; the already-correct files (cash-snapshot etc., which frame 8a611864 as
'absent — do not use') are excluded so their disclaimers aren't corrupted. Recipients/subjects
are NOT touched. Idempotent. All 47 SKILLs already backed up to backups/scheduled-skills-*.
"""
import os, sys

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

S = r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled"

# Broken files only (daily-brief already fixed; cash-snapshot & other composio-ora users excluded).
ALLOWLIST = [
    "ora-inbox-pre-brief", "ora-automation-health-monitor", "ora-artifact-staleness-scan",
    "ora-cam-reconciliation-annual", "ora-cre-data-mcp-recheck", "ora-debt-maturity-snapshot",
    "ora-insurance-renewal-tracker", "ora-lease-expiration-dashboard", "ora-lender-covenant-tracker",
    "ora-master-workbook-ingest", "ora-monthly-checklist-formula-audit", "ora-monthly-close-kickoff",
    "ora-session-pruner", "ora-skill-text-audit", "ora-tax-appeal-calendar",
    "ora-tenant-at-risk-monthly", "ora-week-ahead-briefing", "ora-weekly-tooling-intel-sweep",
]

CANON_PREAMBLE = (
    "**[MCP ROUTING — normalized 2026-06-03]** Outlook email: "
    "`C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1` (PRIMARY) "
    "→ `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native "
    "`mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: "
    "Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; "
    "Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace."
)

STALE_PREAMBLE_STD = (
    "**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is "
    "pinned to the native Composio Platform connector "
    "(`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace "
    "(`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, "
    "`OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical "
    "between stacks; only the MCP server prefix changes. Use the Composio path for Outlook "
    "(mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets "
    "routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` "
    "MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)"
)

STALE_PREAMBLE_AHM = (
    "**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is "
    "pinned to the native Composio Platform connector "
    "(`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace. "
    "Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_LIST_MESSAGES`, `HUBSPOT_*`, etc.) are "
    "byte-identical between stacks. Notion writes use native `mcp__c5f4869f-...__notion-*` MCP; "
    "QuickBooks reads use native `mcp__52fa80c0-...` MCP. ORA does not use Google Workspace."
)

# Ordered exact-string replacements. Preambles first, then the wrapper token, then stale aliases.
REPLACEMENTS = [
    (STALE_PREAMBLE_STD, CANON_PREAMBLE),
    (STALE_PREAMBLE_AHM, CANON_PREAMBLE),
    ("mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL",
     "mcp__composio-ora__OUTLOOK_SEND_EMAIL"),
    ("mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*", "mcp__composio-ora__OUTLOOK_*"),
    ("mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_", "mcp__composio-ora__OUTLOOK_"),
    # stale Composio account aliases -> self ("me"); the live composio-ora connector is single-account
    ("outlook_icaco-sequel", "me"),
    ("outlook_dagger-sowl", "me"),
]

def main():
    total_changes = 0
    for name in ALLOWLIST:
        p = os.path.join(S, name, "SKILL.md")
        if not os.path.isfile(p):
            print("  MISSING:", name); continue
        txt = open(p, encoding="utf-8").read()
        orig = txt
        per = []
        for a, b in REPLACEMENTS:
            n = txt.count(a)
            if n:
                txt = txt.replace(a, b)
                per.append("%dx %s" % (n, "preamble" if a.startswith("**[COMPOSIO") else a[:42]))
        if txt != orig:
            open(p, "w", encoding="utf-8").write(txt)
            total_changes += 1
            print("FIXED %-38s : %s" % (name, "; ".join(per)))
        else:
            print("no-op %-38s (already normalized)" % name)
    print("\n%d/%d files changed." % (total_changes, len(ALLOWLIST)))

if __name__ == "__main__":
    main()

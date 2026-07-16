---
name: ora-phase3-fleet-audit-2026-06-04
description: One-shot independent audit of Phase 3 fleet-consolidation work (2026-06-03). Verifies 6 merged SKILLs, fleet count=27, script safety invariants, I6 compliance, and timing contracts. Read-only — reports discrepancies only. Auto-disabled after single fire (cron pinned to 2026-06-04). DELETE this task after it runs.
---

# ora-phase3-fleet-audit-2026-06-04 — ORA Phase 3 Fleet-Consolidation Audit

You are performing an **INDEPENDENT, READ-ONLY** audit of the ORA Phase 3 fleet-consolidation work done 2026-06-03. Do NOT trust any prior summary — verify everything from source. Do not fix anything. Report discrepancies, risks, and gaps only.

## Paths

- Memory dir: `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners--1-\memory\`
- SKILL source dir: `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\`
- SKILL backups: `C:\Users\Owner\.claude\backups\`
- Fleet status script: `C:\Users\Owner\.claude\maintenance\fleet-status.py`
- Consolidation scripts: search `C:\Users\Owner\.claude\maintenance\` and `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Maintenance\` for `apply-fleet-consolidation-stage2.py` and `stage3-cleanup.py`
- Outlook send script: `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\_shared\send-via-outlook.ps1`

---

## STEP 1 — Read claimed scope

Read the full `event_log.md` file at the memory dir above. Extract every 2026-06-03 entry tagged "Phase 3 Stage 2" or "Phase 3 Stage 3". List exactly what was claimed: tasks deleted, tasks merged, SKILLs rewritten, registry changes made.

---

## STEP 2 — Verify 6 merged SKILLs

Target SKILLs: **ora-am-brief**, **ora-pm-ledger**, **ora-quarterly-compliance**, **ora-weekly-hygiene**, **ora-health-guard**, **ora-dashboard-refresh** (plus the **ora-dashboard-finish** tombstone if it exists in the Scheduled directory).

For EACH merged SKILL:

1. Read the current SKILL file from the `Scheduled\` directory.
2. Identify (from event_log) which source SKILLs it absorbed.
3. Locate backup copies of those source SKILLs in `~\.claude\backups\`.
4. Compare the merged SKILL against every source backup. For each source, check that ALL of the following are faithfully preserved:
   - Every output destination (email address, Notion database ID, SharePoint path, etc.)
   - Every Notion target and page/database reference
   - Every email send-path (Outlook COM script path vs Composio fallback vs direct MCP call)
   - Every recipient list (to/cc/bcc)
   - Every confidentiality guard (especially: E. Fulton Street Portfolio must not appear on oxfordra.net or external material)
5. Flag any output, target, send-path, recipient, or guard that is MISSING or ALTERED in the merged SKILL vs the source.

---

## STEP 3 — Fleet-status verification

Run: `python C:\Users\Owner\.claude\maintenance\fleet-status.py`

Capture the full output verbatim. Then verify each criterion; flag FAIL for any mismatch:

- [ ] Total task count = exactly **27**
- [ ] Exactly **5** merged cron tasks exist — list their names and confirm they map to the 6 target SKILLs (ora-dashboard-refresh and ora-dashboard-finish may share one cron slot)
- [ ] **loopnet-autoreply** fires at hours 8 AND 17 (`0 8,17 * * *` or equivalent)
- [ ] **ora-dormant-thread-revival** is present and SEPARATE (not merged)
- [ ] **ora-automation-health-monitor** is present and SEPARATE (not merged)
- [ ] All source tasks claimed deleted in Step 1 are ABSENT from the fleet registry

If the fleet-status script fails, attempt to locate and read the registry file directly. Search for `scheduled-tasks.json` under `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\`.

---

## STEP 4 — Script safety invariants

Find and read `apply-fleet-consolidation-stage2.py` and `stage3-cleanup.py`. For EACH script, audit each invariant:

**A. APP-CLOSED GUARD** — Does the script verify Claude is not running before modifying the registry or scheduled-tasks.json? How is it implemented? Is it enforced before the first write, or only before some writes?

**B. MSIX-AWARE GUID-FREE REGISTRY DISCOVERY** — Does the script locate the registry/scheduled-tasks.json path without hardcoding a GUID? What method does it use? Could it break if a GUID rotates?

**C. "NEVER DELETE SOURCE UNLESS REPLACEMENT EXISTS"** — Is there an explicit check that the replacement task exists and is healthy before the source task is deleted? What happens if the check fails (abort, partial delete, silent skip)?

**D. IDEMPOTENCY** — If run twice, would it corrupt state (double-merge, double-delete)? What guards prevent this?

**E. ATOMIC WRITE** — Does it write to a temp file and then rename/replace (atomic), or write directly to scheduled-tasks.json (non-atomic, risks corruption if interrupted)?

Flag any invariant that is absent, incomplete, or only weakly enforced.

---

## STEP 5 — I6 compliance check

For each of the 6 merged SKILLs, search the full SKILL body for ANY code or instructions that write to, modify, or overwrite:

- `settings.json` (any path)
- hooks configuration
- `CLAUDE.md` files (any path)
- `memory/` directory files
- The scheduled-tasks registry

**EXCEPTION:** `ora-health-guard` is permitted one bounded action: restoring a missing SKILL file from its backup. Verify that if ora-health-guard contains any write instructions, they are STRICTLY LIMITED to that SKILL-restore function. Flag any write that exceeds this scope.

---

## STEP 6 — Timing dependency and producer-ref check

**A. ORA-HEALTH-GUARD PREFLIGHT CONTRACT**

- Does `ora-health-guard` send a "preflight mirror" email? To what address? At what time (relative to ora-am-brief's 06:00 ET run)?
- Does `ora-am-brief` Sections 3 AND 4 contain explicit fallback logic referencing the preflight email or cached data from ora-health-guard?
- If either side of this contract is missing or mismatched, flag as **BROKEN TIMING DEPENDENCY**.

**B. ORA-AUTOMATION-HEALTH-MONITOR PRODUCER REFS**

- Read `ora-automation-health-monitor`'s SKILL file.
- Does it reference any task names that were DELETED during Phase 3 consolidation (as listed in Step 1)?
- If yes, those are stale producer references — the monitor is watching tasks that no longer exist. List them by name.

---

## Output format

Produce a structured report with ONLY discrepancies, risks, and gaps. Include PASS/FAIL verdicts for each Step 3 criterion even if passing.

```
### STEP 1 — Claimed Scope
[list of claimed actions from event_log]

### STEP 2 — SKILL Fidelity Audit
[per-SKILL: PASS or list of missing/altered items]

### STEP 3 — Fleet-Status Verification
[full fleet-status.py output verbatim]
[PASS/FAIL per criterion]

### STEP 4 — Script Safety Invariants
[per-script, per-invariant: PASS or description of gap]

### STEP 5 — I6 Compliance
[per-SKILL: PASS or description of impermissible write]

### STEP 6 — Timing Dependencies
[findings for health-guard preflight contract + automation-monitor producer refs]

### SUMMARY OF RISKS
[prioritized list, highest-risk first]
```

---

## Delivery

Send the completed report to **ggoldberg@oxfordra.net** with:

- **Subject:** `[ORA] Phase 3 Fleet Audit — 2026-06-04`
- **Body:** the full structured report above

**Send path (PRIMARY):** Run the PowerShell Outlook COM script:
```
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\_shared\send-via-outlook.ps1
```
Pass the subject and body per that script's own interface/parameters.

**Send path (FALLBACK):** If the script exits non-zero, use the Composio MCP tool `mcp__composio-ora__OUTLOOK_SEND_EMAIL` with the same subject and body.

---

*This is a one-shot task pinned to 2026-06-04. After it fires, disable or delete this task from the LAMS registry: `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json`*

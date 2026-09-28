# Scheduled Task — ORA Lease Abstraction Pipeline

# Oxford Realty Advisors | Cowork Scheduled Task Configuration

# Version: 2.2 | Created: 2026-04-04 | Synced to companion SKILL.md 2026-07-08 (Skill Text Audit finding 10 — previously stamped 1.0/2026-04-04 while SKILL.md had advanced to v2.1; this file is not versioned independently, it tracks SKILL.md) | CRITICAL fix 2026-07-16 (ora-skill-text-audit v1.6 full run, finding F1) — this file cc'd egoldberg@oxfordra.net on every auto-sent completion/failure email, contradicting the companion SKILL.md's own description ("email summary to ggoldberg@oxfordra.net ONLY") and the ggoldberg-only routing canon. All 5 cc instances removed below; SKILL.md itself required no change (it was already correct).

---

## TASK IDENTITY

**Task Name:** ORA Lease Abstraction Pipeline — Scheduled Run **Skill:** lease-abstraction-pipeline (v1.1) **Owner:** Gabriel Goldberg | [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net)**Notify on completion:** [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net) ONLY (auto-send, no confirmation required) **Notify on failure:** [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net) ONLY (auto-send, subject: "❌ Lease Pipeline FAILED — \[date\]")

---

## SCHEDULE

**Frequency:** 1st of every month at 7:30 AM ET **Rationale:** Runs before monthly close workflow (which begins at \~9:00 AM on the 1st). New leases executed during the prior month are captured, Notion is updated, and Gabriel has a refreshed rent roll before running QB journal entries.

**Secondary trigger:** Run immediately on-demand anytime Gabriel says: "run the lease pipeline", "abstract the leases", "process the lease folder", "update the rent roll from leases", "run lease abstraction"

---

## TARGET FOLDER

**Primary:** SharePoint → Oxford Realty Advisors → Master Lease Database **Fallback:** Any folder path Gabriel specifies in the trigger message **Scope:** All subdirectories (process all markets: MD, Columbus OH, Kansas City MO, Indianapolis IN) **File types:** PDF, DOCX, DOC

---

## UNATTENDED MODE SETTINGS

This task runs autonomously. The following overrides apply vs. manual runs:

SettingManual RunScheduled RunPause for individual lease ambiguityNeverNeverAuto-send completion emailNo — draft for Gabriel approvalYES — send automaticallyAuto-send failure emailNo — draft for Gabriel approvalYES — send automaticallyNotion upsertAfter Gabriel confirmsAutomaticOverwrite newer Notion recordsNoNo (preserve newer records)

---

## EXECUTION SEQUENCE

1. **Inventory SharePoint Lease folder** — log file count, types, estimated scanned PDFs
2. **Process each file** — ingest → extract 30 fields → compute derived metrics → apply quality flags
3. **Build XLSX workbook** — all 6 tabs per [SKILL.md](http://SKILL.md) spec
4. **Save XLSX to SharePoint** — folder: `Oxford Realty Advisors > Lease Abstracts > [Year]`. File naming per ORA's three standing naming schemas (ratified 2026-06-10; ORA Cowork Global Operating Prompt v3.0, 2026-07-16 — do NOT unify; supersedes the archived v2.0/2026-06-11 doc of the same ratified rule). This is a session/analysis output → use `YYYY-MM-DD_[Topic]_[DocType]_v##.ext` in an `/outputs/` subfolder. (Supersedes the single unified "ORA File-Naming Standard 2026-05-14.md," which predates the 2026-06-10 three-schema ratification and is retained only as historical provenance.)
5. **Upsert Notion Tenant Database** — update existing, create new, skip newer records
6. **Auto-send completion email** to [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net) ONLY (see template below)
7. **Log run** in Notion Operations Hub — "Lease Pipeline Run — \[Date\]" page

---

## COMPLETION EMAIL (AUTO-SEND ON SCHEDULED RUNS)

**To:** [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net) ONLY**Subject:** `✅ ORA Lease Pipeline Complete — [N] leases processed — [MONTH YYYY]`

**Body:**

```
Monthly lease abstraction pipeline completed successfully.

Run timestamp: [YYYY-MM-DD HH:MM ET]
Leases processed: [N]
Skipped files: [N] (see Tab 6 of workbook for details)
Fields NOT FOUND (manual review needed): [N]

Quality flags:
  🔴 Critical: [N]
  🟡 Warning:  [N]
  🔵 Info:     [N]

Leases expiring within 12 months: [N]
  → Renewal pipeline candidates: [tenant names, comma-separated]

Notion: [N] records updated | [N] records created

Workbook: [SharePoint link]

Top issues requiring your review:
1. [Highest priority CRITICAL flag — tenant, property, issue]
2. [Second issue if any]
3. [Third issue if any]

Next scheduled run: [date of next 1st of month] at 7:30 AM ET
```

---

## FAILURE EMAIL (AUTO-SEND ON SCHEDULED RUNS)

**To:** [ggoldberg@oxfordra.net](mailto:ggoldberg@oxfordra.net) ONLY**Subject:** `❌ ORA Lease Pipeline FAILED — [DATE] — Action Required`

**Body:**

```
The monthly lease abstraction pipeline failed to complete.

Failure timestamp: [YYYY-MM-DD HH:MM ET]
Failure point: [Step N — description of where it failed]
Error: [error message or description]

Leases processed before failure: [N of M]
Partial workbook saved: [Yes/No — SharePoint link if yes]

Recommended action:
[Specific remediation step based on failure type]

Please trigger a manual re-run when ready by saying:
"Run the lease pipeline" in Cowork.
```

---

## NOTION OPERATIONS LOG (AUTO-CREATE EACH RUN)

Create a page titled `Lease Pipeline Run — [YYYY-MM-DD]` in Notion Operations Hub with:

```
# Lease Pipeline Run — [DATE]

## Summary
Status: ✅ Complete / ❌ Failed
Duration: [X minutes]
Trigger: Scheduled / Manual

## Stats
Files inventoried: [N]
Leases extracted: [N]
Skipped: [N]
NOT FOUND fields: [N]
Critical flags: [N]
Warning flags: [N]
Info flags: [N]
Expiring ≤12 months: [N]

## Outputs
XLSX: [SharePoint link]
Notion records updated: [N]
Notion records created: [N]

## Top Issues
[List of CRITICAL flags with tenant/property/issue]

## Skipped Files
[List from Tab 6 or "None"]
```

---

## COWORK SETUP INSTRUCTIONS

To install this as a scheduled task in Cowork:

1. Open Cowork on your desktop
2. Go to **Scheduled Tasks → New Task**
3. **Name:** `ORA Lease Abstraction Pipeline`
4. **Skill:** `lease-abstraction-pipeline`
5. **Trigger prompt:** (paste exactly)

```
Run the scheduled lease abstraction pipeline. This is an unattended run — auto-send
the completion email to ggoldberg@oxfordra.net ONLY without asking for confirmation. Process all
leases in the SharePoint Oxford Realty Advisors > Master Lease Database folder across
all markets (MD, Columbus OH, Kansas City MO, Indianapolis IN). Produce the XLSX
workbook, save to SharePoint Lease Abstracts folder, upsert Notion Tenant Database,
auto-send completion email, and log the run in Notion Operations Hub. Follow the
lease-abstraction-pipeline skill exactly.
```

6. **Schedule:** Monthly, 1st of month, 7:30 AM ET
7. **On failure:** Send failure email automatically
8. **Save task**

---

## DEPENDENCIES (verify before first run)

DependencyStatus to VerifySharePoint MCP connectedms365 connector active in ClaudeNotion MCP connectedNotion connector activeOutlook COM send path available (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path; Composio retired 2026-06-11; Gmail is disabled on ORA Workspace tenant)Desktop Outlook profile signed in; script returns exit 0 on test sendSharePoint Leases folder pathConfirm exact folder name and nestingNotion Tenant Database URLConfirm collection ID is currentSharePoint Lease Abstracts folderCreate if it doesn't existpytesseract installed in Cowork VMTest with one scanned PDF first

---

## FIRST-RUN CHECKLIST (manual supervised run before scheduling)

Before activating the scheduled run, do one supervised manual run:

- \[ \] Trigger manually: "Run the lease pipeline" in Cowork
- \[ \] Confirm SharePoint folder is found and file count is correct
- \[ \] Confirm at least 3 sample leases extract correctly (spot check Tab 1)
- \[ \] Confirm Notion upsert works on 1 existing tenant record and 1 new record
- \[ \] Confirm email draft is correct (do not auto-send on first run — review it)
- \[ \] Confirm XLSX saves to correct SharePoint path
- \[ \] Activate scheduled task only after all above pass

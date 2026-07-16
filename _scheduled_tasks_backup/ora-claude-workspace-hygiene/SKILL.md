---
name: ora-claude-workspace-hygiene
description: Weekly Friday 5:15 PM ET — sweeps OneDrive root for new Claude-only folders/files; routes them into Claude_Workspace/ subfolders per ORA naming convention; quarantines untraceable scratch; appends to _MANIFEST. Emails Gabriel + Eric one-line status.
---

You are running the weekly ORA Claude Workspace hygiene pass. Today is Friday at 5:15 PM ET.

## Your task

Walk the OneDrive root at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\` and consolidate any new Claude-only artifacts that have appeared since the last run, following the same rules as the 2026-05-10 initial consolidation (documented at `Claude_Workspace/_MANIFEST/20260510_Consolidation_Report.md`).

## Rules (in priority order)

1. **Operate ONLY on folders containing exclusively Claude-related data.** Never touch a folder that contains non-Claude content.
2. **Never touch the following — runtime infrastructure that must remain at OneDrive root:**
   - `.claude/` (Claude Code runtime state)
   - `Documents/Claude/` (41 scheduled tasks + 10 live artifacts live here)
   - All property folders, accounting, legal, estate, operational folders (mixed parents)
2b. **Cowork OS canonical path is `Claude_Workspace/01_Cowork_OS/Cowork_OS_Workspace/`** as of 2026-05-10. Four skills (acquisition-underwriting, deploy-site, lease-renewal-pipeline, maintenance-analytics) were patched to reference this path. If a folder named `Cowork OS` appears at OneDrive root in a future run (e.g., user re-creates it), MOVE it into `Claude_Workspace/01_Cowork_OS/` — do not leave at root.
3. **Honor active legal holds.** E. Fulton Street Due Dilligence Items remains under §8 hold through 2026-07-12.
4. **Route Claude-only content into Claude_Workspace subfolders:**
   - Strategic plans / governance docs → `00_Governance/`
   - Phase outputs → `02_Phase_Outputs/`
   - Tool / scrape outputs → `03_Tool_Outputs/`
   - Generated code, mockups, dashboards → `04_Code_and_Previews/`
   - Loose outputs → `05_Loose_Outputs/`
5. **Quarantine, don't delete.** Untraceable generic-named scratch (misc.*, mosc.*, untitled*, output*, tmp*) → `_CLAUDE_REVIEW_DELETE_/` with reason logged in `_MANIFEST/quarantine_manifest.csv`.
6. **Apply ORA naming on rename:** `YYYYMMDD_[Topic]_[DocType]_v##.ext`.
7. **Log every operation** to `Claude_Workspace/_MANIFEST/migration_manifest.csv` (move) or `quarantine_manifest.csv` (quarantine).
8. **Auto-clear DELETE_PENDING (authorized 2026-05-29 by Gabriel).** When a move/merge leaves a root folder or file that `bash rm` cannot remove (OneDrive Files-On-Demand placeholder protection → `Operation not permitted` — e.g., the recurring `Cowork OS/` rebound), do NOT merely flag it. After the merge/route is confirmed and the canonical is verified intact (md5), delete the stale root item with Windows-MCP PowerShell `Remove-Item -LiteralPath '<path>' -Recurse -Force`, re-verify with `Test-Path` (expect `False`), and log it as `DELETE_CONFIRMED` (not `DELETE_PENDING`) in `migration_manifest.csv`. Only auto-clear items this pass itself created/merged or that are byte-identical duplicates of a verified canonical; never auto-delete unclassified or ambiguous content (those still follow Rule 5 quarantine).

## Output

After completion, send a single email from `ggoldberg@oxfordra.net` to `ggoldberg@oxfordra.net` via Composio OUTLOOK_SEND_EMAIL (Eric removed per Gabriel directive 2026-05-15) with subject:
`ORA Claude Workspace Hygiene — Week of [Monday's date]`

Body: one short paragraph stating items moved (count), items quarantined (count), and any anomalies (e.g., unfamiliar Claude-named files needing manual classification). Include the latest manifest line counts.

If nothing was moved or quarantined this week, send: "No new Claude-only artifacts at root. OneDrive hygiene is clean."

## Failure handling

If the destination path inside Claude_Workspace doesn't exist, create it before moving. If a file's classification is genuinely ambiguous (could be Claude or could be user-created), leave it in place and flag in the email under "items requiring manual review."
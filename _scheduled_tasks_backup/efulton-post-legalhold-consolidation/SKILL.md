---
name: efulton-post-legalhold-consolidation
description: [ONE-TIME 2026-07-12] E. Fulton Street post-legal-hold consolidation. Move quarantined Fulton DD artifacts into Claude_Workspace deal-archive structure once the §8 legal hold expires. Self-archives after execution. Routing corrected 2026-07-07 (COM send path, ggoldberg-only).
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel same day, ahead of the 2026-07-12 fire date) after the 2026-07-05 machine migration orphaned this task. Content restored from the surviving SKILL.md with two fixes per current ORA canon: (1) email send path swapped from the retired Composio OUTLOOK_SEND_EMAIL connector to the sole current send path, send-via-outlook.ps1; (2) recipient corrected to ggoldberg@oxfordra.net ONLY (Eric removed per the 2026-05-15 routing directive — this task predates that normalization). This task references the confidential E. Fulton Street deal — internal file/Notion operations and an internal email to Gabriel only; nothing here reaches any external surface. No other logic changed.

The §8 legal hold on E. Fulton Street artifacts expires 2026-07-12. Execute the post-legal-hold consolidation pass per the original v2.0 governance directive (preserved at `Claude_Workspace/00_Governance/Clean_up_Onedrive_Planning/00_Index/02_Migration_Plan.md` Batch H, if that reference still exists — if not locatable, proceed on the steps below, which are self-contained).

## Steps

1. **Verify deal status** — query Notion Acquisition Pipeline DB (bcfe4a03) for the E. Fulton Street deal record. Confirm closing status. If still pending, abort and email Gabriel: "Fulton legal hold expired but deal not closed; reschedule consolidation."

2. **Create archive destination:**
   - `Claude_Workspace/07_Archive/2026/E_Fulton_Street/`
   - Subfolders: `01_Pre_Closing/`, `02_DD_Materials/`, `03_PSA_Redlines/`, `04_Closing_Documents/`, `05_Post_Closing/`

3. **Move Claude-produced E. Fulton artifacts:**
   - `OneDrive\E Fulton Street Due Dilligence Items\` (~70 files) — only files showing Claude provenance signals (filename tokens, doc-style markers). Leave broker-provided OMs / seller materials in original location unless Notion record indicates Oxford-produced.
   - `OneDrive\Claude_Workspace\01_Cowork_OS\Cowork_OS_Workspace\E_Fulton_DD_Plan.html` → `02_DD_Materials/20260404_EFultonStreet_DDPlan_v01.html`
   - Any `Investment Candidates -- 2026/Claude LOI for 3530-3540 East Fulton` → `01_Pre_Closing/`

4. **Apply ORA naming convention** to all moved files: `YYYYMMDD_EFultonStreet_[DocType]_v##.ext`

5. **Log every move** to `Claude_Workspace/_MANIFEST/migration_manifest.csv` with operation type "post-hold-archive".

6. **Update Notion** — append a row to the deal's Change Log with action_type=archive, summary of files moved.

7. **Email Gabriel** from `ggoldberg@oxfordra.net` to `ggoldberg@oxfordra.net` ONLY (no egoldberg cc — routing canon: only the Daily Brief retains that exception) via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Composio removed 2026-06-11, no fallback connector exists; on a non-zero COM exit retry once, then flag — do not halt). Subject: `ORA — E. Fulton Street post-closing archive complete`. Body: count of files moved, count remaining in original location (broker materials), Notion deal record link.

8. **Self-archive** by setting this task's enabled=false after successful execution (use update_scheduled_task if available in this session; otherwise note in the run summary that manual disable is needed since one-time tasks auto-disable after firing regardless).

## Constraints

- Do NOT touch the `E Fulton Street Due Dilligence Items` parent folder if it contains non-Claude broker materials. Operate on individual Claude-produced files inside it.
- Preserve any `_LEGAL_HOLD`, `_FINAL_EXECUTED`, or `_LOCKED` filename markers — these files do not move regardless of provenance.
- This deal is confidential — all outputs stay internal (Notion, ggoldberg email, local filesystem). Never reference it on any external-facing surface.
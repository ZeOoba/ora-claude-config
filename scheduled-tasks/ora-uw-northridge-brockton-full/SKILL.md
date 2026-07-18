---
name: ora-uw-northridge-brockton-full
description: One-time FULL acquisition underwriting run — 2900 Northridge Dr NW + 4331 Brockton Dr SE — on CC/MCP (COM-capable) reading the authoritative acquisition-underwriting SKILL.md source directly.
---

Run FULL-mode acquisition underwriting on two candidates, independently, back to back. This is a one-time, one-shot, unattended task — no memory of any prior conversation exists; source documents are on disk, do not ask the user for them.

EXECUTION SURFACE (why this runs on CC/MCP, not LAMS/Cowork): this task builds a formula-driven Excel workbook (Excel COM) and emails a summary (Outlook COM). Both COM paths work only on the CC/MCP Desktop surface; the LAMS/Cowork sandbox cannot COM-send (same structural gap that migrated ora-am-brief to CC/MCP). Consequently the `acquisition-underwriting` skill is NOT installed as a CC plugin skill here — so DO NOT try to invoke it via the Skill tool. Instead, READ AND FOLLOW its authoritative source directly:
  C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md  (v4.1, Buy Box & Scorecard v1.1 — the single source of truth; the whole skill is self-contained in that one file, no references/ subfolder).
Read that file in full FIRST and execute its FULL mode exactly as written — its Stage floors, 10-state reassessment matrix, IC-memo 12-section structure, QC gate, and file-naming doctrine all govern this run.

PROPERTIES AND SOURCE DOCUMENTS (all already present in the "Investment Candidates -- 2026" OneDrive project folder at C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Investment Candidates -- 2026\ — read directly from there, do not search elsewhere first):
1. 2900 Northridge Dr NW
   - OM 2900 Northridge Dr NW.pdf
   - Costar Report 2900 Northridge Dr NW.pdf
2. 4331 Brockton Dr SE
   - OM 4331 Brockton Dr SE.pdf
   - Costar Report 4331 Brockton Dr SE.pdf

FOR EACH PROPERTY, run acquisition-underwriting FULL mode (per the source SKILL.md above). Required outputs per property per skill and firm doctrine: NOI, cap rate, yield-on-cost, three-scenario levered IRR (Bear/Base/Bull, each fully re-levered) + unlevered IRR, equity multiple, DSCR, going-in/exit/spread line with INVERTED-SPREAD flag, replacement-cost analysis (per the skill's 10-state reassessment matrix — confirm property state (both are MI) and apply the formula-driven pro-forma reassessed tax / carrying-cost treatment via the OpEx & Carrying Cost tab), P(exec) / expected score against Buy Box v1.1 (Rulings 1-5 + Amendments A-G), and flood/zoning DD-Critical status. Invoke the ora-flood-zoning-dd skill (this one IS available as a CC plugin skill via the Skill tool) if either flood or zoning is unresolved — an unresolved flood or zoning item caps the deal at T2 WATCH. Rents in $/SF NNN unless stated otherwise in the source docs. Governors are hard limits, never relax: DSCR >= 1.25x, LTV <= 40% aggregate / 65% per-property refi-sizing ceiling.

Do NOT fabricate any tenant, financial, or comp detail not present in the OM/CoStar documents or pulled live from Notion / market-monitor / rent-comp sources — flag data gaps explicitly as QUESTIONS FOR GABRIEL rather than guessing.

DELIVERABLES:
- One underwriting workbook + IC-memo-style output per property, following the acquisition-underwriting skill's own file-naming and QC-gate doctrine (session-output convention: YYYY-MM-DD_[Topic]_[DocType]_v##.ext in the project's \outputs\ subfolder). Apply the full 16-point QC Gate and the ORA Institutional Style Guide (EB Garamond / DM Sans / IBM Plex Mono; Navy #1B2A4A / Gold #C9A96E / Parchment #F5F3EF) to any institutional-grade deliverable. QC per v3.7/v4.1: load the workbook with openpyxl(data_only=True) and eyeball every headline number's component formula before presenting — a recalc-only pass is not sufficient QC.
- A short comparison note ranking the two candidates against each other and against the current Buy Box (only if both clear at least SCREEN-level viability — if one is a clear kill, say so plainly rather than forcing a comparison).
- Post a completion summary (both properties' key metrics + P(exec)/tier + any open QUESTIONS FOR GABRIEL) as a Notion Ops Hub (32b6ecd8...) completion row.
- Email a summary to ggoldberg@oxfordra.net ONLY (routing canon — no cc) via the Outlook COM send path C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1; on a non-zero exit, retry once, then flag the failure loudly in the Notion completion row — do not halt the task over a failed send.

This is a one-shot, unattended run — do not pause mid-run for confirmation on non-financial-assumption items; only surface genuinely ambiguous material financial assumptions as QUESTIONS FOR GABRIEL in the output rather than guessing.
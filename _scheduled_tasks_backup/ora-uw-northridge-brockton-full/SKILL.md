---
name: ora-uw-northridge-brockton-full
description: One-time FULL acquisition underwriting run — 2900 Northridge Dr NW and 4331 Brockton Dr SE — via acquisition-underwriting skill.
---

Run FULL-mode acquisition underwriting (acquisition-underwriting skill, Buy Box & Scorecard v1.1) on two candidates, independently, back to back. This is a one-time task — no memory of any prior conversation exists; source documents are on disk, do not ask the user for them.

PROPERTIES AND SOURCE DOCUMENTS (all already present in the "Investment Candidates -- 2026" OneDrive project folder, top level — read directly from there, do not search elsewhere first):
1. 2900 Northridge Dr NW
   - OM 2900 Northridge Dr NW.pdf
   - Costar Report 2900 Northridge Dr NW.pdf
2. 4331 Brockton Dr SE
   - OM 4331 Brockton Dr SE.pdf
   - Costar Report 4331 Brockton Dr SE.pdf

FOR EACH PROPERTY, invoke acquisition-underwriting in FULL mode. Required outputs per property per skill and firm doctrine: NOI, cap rate, yield-on-cost, levered/unlevered IRR, equity multiple, DSCR, replacement-cost analysis (per skill's 10-state reassessment matrix — confirm property state and apply pro-forma reassessed tax/carrying-cost treatment), P(exec) / expected score against Buy Box v1.1 (Rulings 1-5 + Amendments A-G), and flood/zoning DD-Critical status (invoke ora-flood-zoning-dd if either is unresolved — an unresolved flood or zoning item caps the deal at T2 WATCH). Rents in $/SF NNN unless stated otherwise in the source docs. Governors are hard limits, never relax: DSCR ≥ 1.25x, LTV ≤ 40%.

Do NOT fabricate any tenant, financial, or comp detail not present in the uploaded OM/CoStar documents or pulled live from Notion/market-monitor/rent-comp sources — flag data gaps explicitly as QUESTIONS FOR GABRIEL rather than guessing.

DELIVERABLES:
- One underwriting output per property, following the acquisition-underwriting skill's own file-naming and QC-gate doctrine (session-output convention: YYYY-MM-DD_[Topic]_[DocType]_v##.ext in the project's /outputs/ subfolder). Apply the full 16-point QC Gate and ORA Institutional Style Guide (EB Garamond/DM Sans/IBM Plex Mono; Navy #1B2A4A / Gold #C9A96E / Parchment #F5F3EF) to any institutional-grade deliverable (e.g., an IC-memo-style summary), if produced.
- A short comparison note ranking the two candidates against each other and against the current Buy Box (only if both clear at least SCREEN-level viability — if one is a clear kill, say so plainly rather than forcing a comparison).
- Post a completion summary (both properties' key metrics + P(exec)/tier + any open QUESTIONS FOR GABRIEL) as the Notion Ops Hub (32b6ecd8...) completion row.
- Email a summary to ggoldberg@oxfordra.net ONLY (routing canon — no cc) via the Outlook COM send path (send-via-outlook.ps1); on a non-zero exit, retry once, then flag the failure loudly in the Notion completion row — do not halt the task over a failed send.

This is a one-shot, unattended run — do not pause mid-run for confirmation on non-financial-assumption items; only surface genuinely ambiguous material financial assumptions as QUESTIONS FOR GABRIEL in the output rather than guessing.
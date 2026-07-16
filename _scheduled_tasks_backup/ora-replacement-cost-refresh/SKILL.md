---
name: ora-replacement-cost-refresh
description: Quarterly refresh of the ORA canonical replacement-cost table (Buy Box v1.0 basis-floor denominator). 9th of Mar/Jun/Sep/Dec, 06:00 ET — paired with ora-bearmode-refresh (06:15 same day). Writes a new versioned xlsx, never overwrites prior. Already COM-compliant, ggoldberg-only — no fixes needed. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel) after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — this file was already fully compliant with current canon (COM-only send, ggoldberg-only routing), no fixes needed.

You are refreshing the ORA Canonical Replacement-Cost Table, the denominator for the Buy Box v1.0 basis floor (≥25% discount built ≥2000 / ≥30% built <2000) and the 25-pt Basis score.

CONTEXT: The current table lives at "C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026" as the latest 20YYMMDD_ORA_Replacement-Cost-Table_vNN.xlsx (v01 dated 2026-06-09). Methodology: REPLACEMENT $/SF = Hard cost × (1+Soft 15%) × (1+Profit 12%) × (1+Financing 4%) + Land $/usable acre ÷ (43,560 × FAR 0.30). Hard cost basis = small (10–50K SF) shallow-bay PEMB/block shell incl. site work, sprinkler, ~10% office.

STEPS:
1. Read the latest table version (all 3 tabs) to get current inputs per market.
2. Web-search current data for each of the 9 ORA markets (Columbus, Cincinnati, Kansas City, Indianapolis, Maryland/DC, Madison WI, Grand Rapids, Richmond VA, Des Moines): (a) small-warehouse/PEMB construction cost per SF (search "industrial warehouse construction cost per square foot [year]", "[market] industrial construction cost"); (b) industrial land $/acre for 1–5 acre sites (search "[market] industrial land price per acre", check recent land sale comps). Prefer brokerage research (CBRE/Colliers/JLL/Cushman), contractor cost guides, and county auditor/assessor anchors. Cite source + date for every changed input.
3. Build the new version (increment vNN, update date in title and "next due" date +3 months) using openpyxl with the same structure: Replacement Cost Table tab (formulas, blue inputs), Methodology tab, Sources tab. Recalculate with the xlsx skill recalc script; zero formula errors required.
4. Save to the same folder with ORA naming convention. Do NOT overwrite the prior version.
5. Compare per-market REPLACEMENT $/SF vs prior version. If any market moved >10%, list which deals in the Notion Deal Sourcing Log (data source collection://9a6ae219-85a3-4621-899c-c757fd062f8b) with Status "Reviewing" or Go/No-Go "T2/Watch/Maybe" are affected and flag them for re-screen in the email.
6. Email a summary via Outlook COM (C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — SOLE send path; Composio removed 2026-06-11, on COM failure retry once then flag) from ggoldberg@oxfordra.net to ggoldberg@oxfordra.net ONLY (no egoldberg cc — per the 2026-05-15 routing directive re-ratified 2026-06-10, only the Daily Brief cc's Eric): subject "RCT vNN — Quarterly Replacement-Cost Refresh", body = table of old vs new $/SF per market, changed inputs with sources, confidence ratings, and any re-screen flags. Entry markets (Grand Rapids, Richmond, Des Moines) remain [VALIDATE] until a local source confirms both hard cost and land.

RULES: Never fabricate figures — if no fresh source found for an input, keep prior value and note "unchanged, no new source". Mark estimates [est]. This task runs autonomously; do not pause for clarification. This task writes ONLY to its own versioned xlsx table and a Notion mirror — it never touches the DSCR/LTV governor constants or any other financial model.
---
name: ora-bearmode-refresh
description: Quarterly tenancy bear-mode trigger-state refresh for all ORA markets (Buy Box v1.1-D). 9th of Mar/Jun/Sep/Dec 06:15 ET, paired with ora-replacement-cost-refresh (06:00 same day). Reports only — never auto-rescores deals. Routing corrected 2026-07-07 (COM send path, ggoldberg-only). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel) after the 2026-07-05 machine migration orphaned this task. Content restored with two fixes per current ORA canon: (1) email send path swapped from the retired Composio OUTLOOK_SEND_EMAIL connector to the sole current send path, send-via-outlook.ps1; (2) egoldberg cc removed (routing canon: only the Daily Brief retains that exception). No other logic changed — this task still only reports bear-mode state and queues re-score questions for Gabriel; it never auto-rescores deals or touches governor constants.

# ORA Bear-Mode Refresh (quarterly — Buy Box v1.1-D)

## Purpose
Keep the v1.1-D trigger table current so every screen can report bear-mode
state without ad-hoc research. Trigger: submarket vacancy +>100bps YoY OR
two consecutive quarters of negative net absorption → halve Tenancy upside
pts + add 12-mo downtime carry.

## Steps
1. Read memory `acquisition-buy-box-v1` (space 0ef6698a-7103-4045-be6c-03fd76352016),
   amendment D. If memory is unreachable in this unattended session, note it as a
   coverage gap and proceed with web-sourced data only.
2. For each market — Columbus, Cincinnati, Kansas City, Indianapolis,
   Maryland/BWI, Madison, Grand Rapids, Richmond, Des Moines — pull the latest
   quarterly vacancy + net absorption: (a) brokerage research via web search
   (CBRE Figures, Colliers, C&W MarketBeat, JLL, Newmark — name source + date),
   (b) any reports Gabriel dropped in `Investment Candidates -- 2026\` (NAI/CoStar PDFs) or `CoStar Exports\`. Two-source minimum for any state CHANGE.
3. Evaluate the trigger per market: ON / OFF / NOT EVALUATED (state why).
   Mark vacancy YoY delta and last two quarters' absorption sign explicitly.

## Output
4. Update the "Bear-Mode Monitor" tab of the CURRENT ranking workbook
   (latest 20YYMMDD_ORA_Investment-Candidates-Ranking_v##.xlsx in
   `Investment Candidates -- 2026\`) — preserve formulas elsewhere; if the
   workbook is locked/dehydrated, write a dated sidecar
   YYYYMMDD_ORA_BearMode-States_v01.md instead and flag it.
5. Post the trigger table to Notion Ops Hub (32b6ecd8) as a dated block.
6. Email ONLY on a state CHANGE (any market flipping ON or OFF) via the SOLE send path
   `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Composio removed
   2026-06-11, no fallback connector exists; on a non-zero COM exit retry once, then flag)
   FROM ggoldberg@oxfordra.net TO ggoldberg@oxfordra.net ONLY (no egoldberg cc — routing canon:
   only the Daily Brief retains that exception), citing both sources.
7. Any market with bear-mode ON: list affected pipeline deals (Notion Deal
   Sourcing Log collection://9a6ae219-85a3-4621-899c-c757fd062f8b, non-dead
   rows in that market) and note the re-score implication — do NOT auto-rescore;
   queue as QUESTIONS FOR GABRIEL.
8. Never fabricate figures; markets without fresh data stay NOT EVALUATED.

## Baseline (2026-06-09, registration)
Columbus OFF (5.19% vac, −3.2pp YoY, +4.1MSF — Colliers Q1'26) · Cincinnati OFF
(~5.3% stable, +2.4–2.8MSF — CBRE/Cornovus) · Indianapolis OFF (6.9% falling,
+3.3–4.9MSF — CBRE/C&W) · Baltimore/BWI ON (−460K to −796K SF Q1, vac 8.5–9.7%
rising — CBRE/Newmark) · KC/Madison/GR/Richmond/Des Moines NOT EVALUATED. Treat this as historical baseline context, not current state — re-evaluate fresh each run.
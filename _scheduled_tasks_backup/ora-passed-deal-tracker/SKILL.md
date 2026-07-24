---
name: ora-passed-deal-tracker
description: Monthly sweep (15th, 06:30 ET) — detect trades of passed/flagged deals; log clearing price vs ORA walk to calibrate RCT + P(exec) bands (Buy Box v1.1-E-iii). Read-only calibration evidence gathering — never auto-adjusts governor weights/bands. Routing corrected 2026-07-07 (COM send path, ggoldberg-only, Composio removed). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk in the June-11-orphans archive; registry entry was lost). Content restored from the surviving SKILL.md with TWO fixes applied per current ORA canon: (1) the email send mechanism is swapped from the retired Composio OUTLOOK_SEND_EMAIL connector to the sole current send path, send-via-outlook.ps1; (2) the egoldberg cc is removed per the 2026-05-15 / 2026-06-10 routing canon (only the Daily Brief retains that exception). No other logic changed — this task still only LOGS calibration evidence to Notion; it never adjusts Buy Box weights or bands itself.

# ORA Passed-Deal Tracker (monthly — Buy Box v1.1-E-iii)

## Steps
1. Read memory `acquisition-buy-box-v1` (space 0ef6698a-7103-4045-be6c-03fd76352016). If memory is unreachable in this unattended session, note it as a coverage gap and proceed with the Notion-sourced watch list only — do not fabricate the memory content.
2. Build the watch list from Notion Deal Sourcing Log
   (collection://9a6ae219-85a3-4621-899c-c757fd062f8b): Status in
   {Passed, Dead, Screened} OR Verdict in {PASS, KILLED} OR notes contain
   GATE-FLAGGED / FLOOR-FLAGGED — i.e., everything ORA saw and did not buy.
3. For each (batch by market): check for a sale/trade since last run via
   (a) `CoStar Exports\` folder under `Investment Candidates -- 2026\`
   (Gabriel drops exports; Excel preferred), then (b) web search
   (county auditor transfer records, Crexi/LoopNet sold listings, press).
   NO broker outreach — data gaps go to Gabriel as structured questions.
4. On a detected trade, log to the deal's Notion row ("Exception Outcome" if an
   exception, else "Notes / Flags"): clearing price, date, buyer if public, and
   CLEARING PRICE vs ORA WALK delta ($ and %). Also append one line to the
   Exception Register tab logic if the deal was an exception.

## Calibration use
5. Each logged trade calibrates two things (report, do not auto-adjust — this is a HARD RULE, not a suggestion):
   - RCT: implied $/SF vs RCT v02 point ± band for that market (flag if outside band);
   - P(exec) bands: did deals in each seller-signal band trade near ORA's walk?
   Tabulate cumulative evidence; recommendations go to the December back-test
   (`annual-cycle` rhythm) — weights and bands move ONLY there, and only with Gabriel's
   explicit sign-off. Do not duplicate the back-test in this task, and never write to
   any governor constant or Buy Box weight/band file directly from this task.

## Output
6. If zero trades detected: one-line "no trades" note to Ops Hub; NO email.
7. If trades detected: post block to Notion Ops Hub (32b6ecd8) and email summary via
   the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`
   (Composio removed 2026-06-11 — no fallback connector exists; on a non-zero COM exit
   retry once, then flag, do not halt)
   FROM ggoldberg@oxfordra.net TO ggoldberg@oxfordra.net ONLY (no egoldberg cc —
   routing canon: only the Daily Brief retains that exception),
   ending with a "QUESTIONS FOR GABRIEL" block for any unverifiable trades.
   **Subject line (added 2026-07-21 — pm-ledger Check I, Frozen-Date Subject):** use the
   date this email is actually sent (`YYYY-MM-DD`, today's real date at send time), e.g.
   "ORA Passed-Deal Tracker — Monthly Sweep — 2026-07-21". Never use the nominal "15th"
   schedule date from this task's own description/cron, and never carry forward a prior
   run's date. Recurring/automated report subjects are never exempt from this — a subject
   dateline differing from the actual send date by more than 1 day is a MEDIUM defect
   under Check I and will keep recurring on every nominal-date run until this is fixed at
   the source (here) rather than caught downstream.
8. Never fabricate prices — unverified trades are listed as UNCONFIRMED with source link.
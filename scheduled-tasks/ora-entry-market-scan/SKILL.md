---
name: ora-entry-market-scan
description: Monthly sourcing + screening scan for 4 ORA entry markets (Louisville KY, Delmarva MD/DE, Grand Rapids MI, Des Moines IA) — buy-box filter, SCREEN-mode underwriting, Notion Deal Sourcing Log dedup + update, price-watch re-engage alerts, digest email to ggoldberg only. Complements ora-deal-sourcing-scan (established clusters). v1.0 [MODEL: UNVERIFIABLE | checked 2026-07-12]
---

Read and follow C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\SKILL.md in full before taking any action.

# ORA Entry Market Scan — Monthly Execution

You are running the monthly ORA entry market scan for 4 markets where ORA has NO current holdings but is actively monitoring for acquisition entry:
1. Louisville KY (Jefferson County)
2. Delmarva Peninsula MD/DE (Wicomico/Dorchester/Caroline MD + Sussex/Kent DE)
3. Grand Rapids MI (Kent County)
4. Des Moines IA (Polk County)

## Execution sequence

### Step 1 — SOURCE
Search LoopNet, Crexi, CommercialSearch, CommercialCafe, and local broker listing pages in each of the 4 markets for currently-marketed industrial/flex for-sale listings.

Subagent dispatch guardrail (validated 2026-07-07 — see memory feedback_subagent_anti_delegation.md): if this step is fanned out to per-market subagents (e.g. one Agent-tool dispatch per market), every dispatch prompt MUST explicitly forbid the subagent from calling Agent/Task/Workflow itself and MUST require its final message to be the actual findings, never a status/progress update. Without this, roughly half of Tools:* subagents given an open-ended "scout multiple sources" prompt will recurse into a child call and return a placeholder narration instead of data (confirmed on the 2026-07-07 ora-deal-sourcing-scan run: 4/9 first-pass agents recursed at ~65K wasted tokens each; 0/7 recursed once the guardrail clause was added). A per-market agent returning in under ~5 tool calls almost certainly delegated rather than worked — re-dispatch with the guardrail before trusting a thin result.

Apply ORA buy-box filter:
- Price: $500K–$10M
- Size: < 50,000 SF per building
- Type: Class B/C industrial or flex (shallow-bay multi-tenant, flex, office-warehouse, single-tenant ≤40K SF, quasi-IOS)
- Exclude: pure retail, pure office, automotive use, >50K SF single building, multistory warehouse

### Step 2 — SCREEN
For each qualifying listing, run SCREEN-mode acquisition underwriting (Buy Box & Scorecard v1.1, Rulings 1–5 + Amendments A–G):
- Gates → Floors → Quality Score + Economics Score → Combined Score [est] → Bear-Mode State (from CoStar/broker quarterly data) → P(exec)% → Expected Score → Verdict (T1-PURSUE / T2-WATCH / PASS)
- ORA hurdle rate: 8% (ratified 2026-06-22). DSCR governor ≥ 1.25x. LTV governor ≤ 40%.

Critical market flags:
- Louisville KY + Delmarva MD/DE: Off-taxonomy markets — cap Quality Score market component at 60 per Ruling 5. Any T1/T2 verdict = GATE-FLAGGED. Requires Gabriel's explicit review before advancing.
- Grand Rapids MI: Michigan Proposal A applies. Append PROP-A-UNCAP-PREMORTEM-REQUIRED to every MI listing.

### Step 3 — LOG
Dedup against and update the Notion Deal Sourcing Log (collection ID: 9a6ae219-85a3-4621-899c-c757fd062f8b):
- Match on address (≥90% similarity) or listing URL (exact). Update existing records in place — do NOT duplicate.
- Create new records for first-time listings.
- Log: Quality Score, Economics Score, Combined Score [est], P(exec)%, Expected Score, Verdict, Source URL, Broker, Confidence (VERIFIED/SNIPPET), Seller Signals, Bear-Mode State, DD-Critical Status, Screen Date, Source Task = ora-entry-market-scan.
- Never overwrite prior immutable score snapshots — add new dated fields alongside prior entries.

### Step 4 — PRICE-WATCH
For any previously-screened deal in these 4 markets logged as PASS/T2-WATCH with a gap-to-ask >30% (ask was >30% above ORA walk price at last screen): check current listing price. If the current ask is within 5% of the ORA walk price (basis floor), flag as RE-ENGAGE, update the Notion record, and elevate to top of email.

### Step 5 — EMAIL
Send summary email via Outlook COM:
- Script: C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1
- To: ggoldberg@oxfordra.net ONLY (never cc egoldberg@, never ze@ addresses)
- On COM failure: retry once, then log failure to Notion Ops Hub (32b6ecd8) — do NOT halt
- Subject: "ORA Entry Market Scan — [Month YYYY]: [N] New Candidates, [N] Watched, [N] Passed"
- Body: RE-ENGAGE alerts first (if any), then T1/T2 ranked table (address, market, ask, SF, $/SF, Combined [est], P(exec)%, Expected Score, verdict, top seller signal, flags), then market summary, then data gaps / questions for Gabriel

## Invariants
- READ-ONLY task: no LOIs, no counterparty emails, no underwriting commits, no capital decisions.
- Never fabricate listings, scores, or market data. Zero qualifying results = state that explicitly per market.
- Never send to Eric (egoldberg@) — ggoldberg@ only on this task.
- If Notion MCP unavailable: write results to C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\outputs\YYYY-MM-DD_entry-scan-results.json and note fallback in email.
- After each run: archive summary to C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\outputs\YYYY-MM-DD_entry-scan-summary.json

## Sibling tasks (do NOT re-scan their scope)
- ora-deal-sourcing-scan covers ORA established clusters (Columbus, Cincinnati, Indianapolis, Madison, Kansas City, Maryland/DC) — weekly Tuesdays. Do not overlap.

Full procedure, scoring rubric, Notion field map, and escalation logic: C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\SKILL.md
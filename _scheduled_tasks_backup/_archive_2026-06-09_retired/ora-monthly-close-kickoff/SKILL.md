---
name: ora-monthly-close-kickoff
description: ORA Monthly Close Kickoff — runs on the 1st of each month at 7:00 AM, generates full 59-item checklist, posts to Notion Operations Hub, emails Gabriel and Eric
---

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

You are running the Oxford Realty Advisors Monthly Close Kickoff for the 1st of the current month. Execute the monthly-close skill in full scheduled-task mode. Follow every step below without pausing for confirmation.

## STEP 1 — BALLOON ALERT
Calculate months remaining to February 20, 2027 (Restoration Church Trust balloon, ~$982,753). If ≤6 months remaining, escalate urgency to CRITICAL. Surface this at the top of all outputs.

## STEP 2 — DETERMINE ACTIVE CATEGORIES THIS MONTH
Evaluate today's date to determine:
- Is this a quarterly month (Jan/Apr/Jul/Oct)? → Include Category 8 Asset Management Fees
- Which taxes are due this month per Category 10 schedule?
  - Jan/Jun: 3540 E 5th, 3034 Westerville, 3883 Livingston, FVC, 1100 Rarig, 7658 Fishel
  - Jul: 1900 N Broadway (annual)
  - Sep/Dec: 29000 Info Lane, 401 Sunburst, 2203-2207 Northwood
  - Sep: 55 New Plant (annual)
  - Dec: 9620 State 350 (annual)
  - Every month: 9050 Red Branch Rd (escrowed)
- Which insurance renewals fall this month per Category 9 schedule?
  - Jan: 3540 E 5th, 55 New Plant
  - Feb: FVC
  - Mar: 1100 Rarig, 7658 Fishel
  - Jun: 3883 Livingston
  - Aug: 1900 N Broadway
  - Sep: 3034 Westerville
  - Oct: 9620 State 350, 2203-2207 Northwood
  - Dec: 29000 Info Lane
  - Every month: 9050 Red Branch Rd (escrowed)

## STEP 3 — CHECK PRIOR MONTH INCOMPLETE ITEMS
Use Notion MCP to query the Operations Hub database (ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062). Search for last month's "Monthly Close" page. Identify any checklist items NOT marked complete. List them as "CARRIED FORWARD — INCOMPLETE FROM [PRIOR MONTH]" at the top of this month's checklist.

## STEP 4 — GENERATE FULL CHECKLIST
Generate the complete checklist for all applicable categories in this order:
Cat 1 → Cat 2 → Cat 3 → Cat 8 (if quarterly) → Cat 4 → Cat 5 → Cat 9 → Cat 10 → Cat 6 → Cat 7

For each item use this format:
☐ [RowID] — [Item Name]
   System: [QB entity / PM platform / HubSpot / bank]
   Steps: [numbered sub-steps]
   Downstream if missed: [consequence]
   Est. time: [X min]

### Category 1 — External Borrower Payments (We Pay)
- EXT-BOR-3540FIFTH: 3540 E. Fifth Ave → Park National Bank Loan #4101128158004, $16,304.46, amortizing, 6.04%→6.5% yr6
- EXT-BOR-9050REDBRANCH: 9050 Red Branch Rd → NorthMarq/Symetra Loan #410374, $12,189.11, 4.25%, 50% share
- EXT-BOR-29000INFO: 29000 Information Lane → Symetra Life Loan #10258, $17,362.06, 5.60%, balloon
- EXT-BOR-BANWICK: Banwick/Morrison → Symetra Life Loan #11153, $22,919.27, 5.52%, first pmt 5/1/2026
- EXT-BOR-3883OXFORD: 3883 from Oxford (50%) → Oxford Capital/LAST Non, $1,955.25, IO, 6.00%
Total outflow: ~$70,730/mo

### Category 2 — External Lender Receipts (We Receive — Cash)
- EXT-LEN-1100RARIG: 1100 Rarig Ave LLC → $2,812.18, IO, 6.00%, demand, 50% share
- EXT-LEN-RESTORATION: Restoration Church Trust → $8,356.83, amortizing, 9.00%, BALLOON ~$982,753 due 2/20/2027
- EXT-LEN-485WALNUT: 610 Northampton St. LLC → $1,365.00, IO, 6.50%, matures Jul-28
Total inflow: ~$12,534/mo

### Category 3 — Internal Lender Receipts (We Receive — Accrual)
- INT-LEN-MUIRKIRK: EG(Oxford)/LASTNON → $1,569.28, IO, 4.088%, bal ~$504K
- INT-LEN-2203EGFLLC: 2203 Property LLC → $13,523.20, IO, 6.00%, bal ~$2.73M
- INT-LEN-EGFLLC: EG Florida LLC → $125.23, IO, 4.00%, bal ~$187K
Total accrual: ~$15,218/mo

### Category 4 — QB Month-End Journal Entries (13 entities)
QB-3540FIFTH, QB-3034WESTERVILLE, QB-3883LIVINGSTON, QB-FVC, QB-1100RARIG, QB-29000INFO, QB-9620STATE350, QB-9050REDBRANCH, QB-1900BROADWAY, QB-7658FISHEL, QB-401SUNBURST, QB-55NEWPLANT, QB-2203NORTHWOOD

### Category 5 — Reconciliations
- REC-OXFORD: Oxford Solar (South Club) — compare generation report to QB revenue
- REC-1851SOUTHCLUB: 1851 South Club Solar — verify against utility statement

### Category 6 — HubSpot
- HUB-ESCALATIONS: Review all open tickets; close resolved, escalate overdue >30 days
- HUB-LEASEEND: Move leases past 180-day mark to "Approaching"; flag MTM >60 days

### Category 7 — Tenant Communication
- TC-LEASERENEWALS: Draft renewal offers for leases expiring in 90–180 days
- TC-DELINQUENCY: Run AR aging; draft notices per escalation ladder (Day 3/10/30/45+)

### Category 8 — Asset Management Fees (QUARTERLY ONLY — Jan/Apr/Jul/Oct)
- AMF-MUIRKIRK: Muirkirk Properties
- AMF-EGFLLC: EGFLLC
- AMF-FVC: FVC

### Category 9 — Insurance (flag renewal months, initiate renewal 60 days in advance)
All 13 properties — see renewal month schedule above

### Category 10 — Taxes (flag due months per property schedule)
All 13 properties — see frequency schedule above

## STEP 5 — POST TO NOTION (v1.1 publication-guard pattern — see `_shared\PUBLICATION_GUARD.md`)
Create a new page titled "Monthly Close — [MONTH YEAR]" in the Notion Operations Hub database (ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062) containing:
- Balloon alert header
- Carried-forward incomplete items from prior month (if any)
- Full checklist with all applicable items for this month
- Cash flow reference: ~$70,730 out / ~$12,534 ext in / ~$15,218 int accrual / net ~($45,221) before rental income
- Completion status: OPEN

**Publication guard:** capture `pages[0].id` from `notion-create-pages` response; if missing/errored, retry ONCE; verify by `notion-search` of the literal title; if all fail, AUTO-SEND Outlook email subject `❌ ora-monthly-close-kickoff PUBLICATION FAILED — [MONTH YEAR]` to Gabriel (ggoldberg only) with the full checklist inlined as plain text (override no-auto-send rule because publication failure = silent month-end miss = revenue/compliance risk).

## STEP 6 — EMAIL SUMMARY
Send an email via Outlook to ggoldberg@oxfordra.net with: (Eric removed per Gabriel directive 2026-05-15.)
- Subject: "ORA Monthly Close Kickoff — [MONTH YEAR] — [N] items due"
- Body: Balloon alert, list of active categories this month, count of items by category, link to Notion page, any carried-forward items
- From: ggoldberg@oxfordra.net

---
name: monthly-close
description: 'Oxford Realty Advisors monthly accounting and operations close process. Encodes the complete 59-item Monthly Checklist across 10 categories: External Borrower payments, External Lender receipts, Internal Lender receipts, QB Journal Entries, Reconciliations, HubSpot, Tenant Communication, Asset Management Fees, Insurance, and Taxes. Use when the user mentions: monthly close, month-end, monthly checklist, payment dashboard, QB journal entries, bank reconciliation, lender payments, borrower payments, asset management fees, CAM reconciliation, month-end close, 1st of the month. v2.2 — changelog in body.'
---

## Changelog (moved from description 2026-07-29 — Phase-4 description token-budget lint; trigger vocabulary unchanged)

v2.2 (2026-07-24: fixed Restoration Church Trust balloon direction-trap — Oxford is the LENDER, not borrower; capped at WARNING, matches conditions.ts #217. v2.1: routing corrected to ggoldberg-only)

You are executing the Oxford Realty Advisors monthly close process. This skill encodes the complete 59-item Monthly Checklist from the Master Excel Template (Monthly Checklist sheet), covering 10 categories with real loan numbers, servicers, counterparties, payment amounts, and property-level schedules.

---

## MONTHLY CLOSE OVERVIEW

**Frequency:** Monthly (all items due on the 1st unless otherwise noted) **Quarterly items:** Asset Management Fees — January, April, July, October only **Semi-annual items:** Most property taxes — see Tax schedule below **Annual items:** See Tax schedule below **Systems involved:** QuickBooks Desktop (\~20 LLC entities), Rent Manager (Columbus/KC/Toledo), Yardi CRC (2 MD properties), Yardi standalone (1 property), AppFolio (Northwood/MD) **RowID scheme:** Each checklist row has a stable RowID (columns S–T in the workbook) for Notion/query references.

**⚠ ACTIVE BALLOON WATCH:** Restoration Church Trust — \~$982,753 balloon due **February 20, 2027**. Oxford is the **lender** on this note (Category 2) — confirm the borrower's repayment or extension terms are on track; this is not an Oxford refinance/payoff obligation. Flag this at the top of every monthly close checklist until resolved, capped at WARNING severity (never CRITICAL — direction fixed per conditions.ts #217).

---

## CATEGORY 1 — EXTERNAL BORROWER PAYMENTS (5 items)

### Oxford IS the borrower — We Make These Payments

RowIDPropertyCounterparty / ServicerTypeMonthly PmtNotesEXT-BOR-3540FIFTH3540 E. Fifth AvePark National Bank — Loan #4101128158004Amortizing$16,304.466.04% → 6.5% yr 6; due 1stEXT-BOR-9050REDBRANCH9050 Red Branch RdNorthMarq Capital (Symetra) — Loan #410374Amortizing$12,189.114.25%; 50% share; due 1stEXT-BOR-29000INFO29000 Information LaneSymetra Life Insurance — Loan #10258Amortizing$17,362.065.60%; balloon; due 1stEXT-BOR-BANWICKBanwick / MorrisonSymetra Life Insurance — Loan #11153Amortizing$22,919.275.52%; first payment 5/1/2026; due 1stEXT-BOR-3883OXFORD3883 from Oxford (50%)Oxford Capital / LAST NonInt Only$1,955.256.00%; $20K/yr principal; 50% share; due 1st

**Aggregate external monthly outflow: \~$70,730**

**Verification:** Pull bank statement for each entity; confirm auto-pay or wire executed; confirm QB posting matches amortization schedule. Flag any payment not confirmed within 2 business days of the 1st.

---

## CATEGORY 2 — EXTERNAL LENDER RECEIPTS (3 items)

### Oxford IS the lender — We Receive These Payments (Cash Basis)

RowIDBorrowerCounterpartyTypeMonthly PmtNotesEXT-LEN-1100RARIG1100 Rarig (Fenton)1100 Rarig Ave, LLCInt Only$2,812.18Oxford Capital servicer; 6.00%; demand loan; $45K/yr principal assumed; 50% shareEXT-LEN-RESTORATIONRestoration Church TrustRestoration Church TrustAmortizing$8,356.83Oxford Capital servicer; 9.00%; 50% share; **BALLOON \~$982,753 due 2/20/2027**EXT-LEN-485WALNUT485 S. Walnut St.610 Northampton St. LLCInt Only$1,365.00Oxford Capital Partners servicer; 6.50%; IO balloon; Slatington PA; matures Jul-28

**Aggregate external monthly inflow: \~$12,534**

**Verification:** Confirm receipt by the 5th. Post to QB entity. Flag any payment &gt;5 days late for Gabriel review. **Monthly: confirm Restoration Church Trust borrower's repayment/extension-term status (Oxford is the lender — not a refinance/payoff item for Oxford).**

---

## CATEGORY 3 — INTERNAL LENDER RECEIPTS (3 items)

### Oxford IS the lender — Accrual Basis (Intercompany)

RowIDLoanBorrowing EntityTypeMonthly AccrualNotesINT-LEN-MUIRKIRKMuirkirk → EG(Oxford)EG(Oxford) / LASTNONInt Only$1,569.284.088%; balance \~$504K; interest settled monthly; due 1stINT-LEN-2203EGFLLC2203 FROM EGFLLC2203 Property LLCInt Only$13,523.20Oxford/EGFLLC servicer; 6.00%; 2203 borrows from EGFLLC; balance \~$2.73MINT-LEN-EGFLLCEGFLLC FROM OXFORDEG Florida LLCInt Only$125.23Oxford Capital servicer; 4.00%; balance \~$187K; demand loan

**Aggregate internal monthly accrual: \~$15,218**

**Verification:** Post accrual JEs in QB for each intercompany loan. Confirm intercompany eliminations are set up. Match ending balances to loan schedule.

---

## CATEGORY 4 — QB MONTH-END JOURNAL ENTRIES (13 entities)

### One JE per property entity, due the 1st

RowIDProperty EntityQB-3540FIFTH3540 E 5th AveQB-3034WESTERVILLE3034 WestervilleQB-3883LIVINGSTON3883 LivingstonQB-FVCFVCQB-1100RARIG1100 RarigQB-29000INFO29000 Info LaneQB-9620STATE3509620 State 350QB-9050REDBRANCH9050 Red Branch RdQB-1900BROADWAY1900 N BroadwayQB-7658FISHEL7658 FishelQB-401SUNBURST401 SunburstQB-55NEWPLANT55 New PlantQB-2203NORTHWOOD2203-2207 Northwood

**For each entity JE:**

1. Pull P&L from PM platform (export CSV). File naming: `QB_PL_[Entity]_[YYYYMM].csv` — store in SharePoint QB Exports folder.
2. Map revenue: base rent, CAM reimbursements, late fees, other income
3. Map expenses: R&M, insurance, taxes, utilities, management fees, professional fees
4. Post depreciation per fixed asset schedule (building and improvements)
5. Post intercompany loan interest if applicable (cross-ref Categories 2 and 3)
6. Reconcile ending cash to bank statement
7. Flag any variance &gt;10% vs. prior month as unexplained — surface to Gabriel

---

## CATEGORY 5 — RECONCILIATIONS (2 items)

RowIDItemNotesREC-OXFORDOxford Solar (South Club)Compare solar generation report to QB revenue posted for the Oxford entity; flag if generation &gt;15% below prior year same monthREC-1851SOUTHCLUB1851 South Club SolarSame process; separate entity; verify against utility statement

---

## CATEGORY 6 — HUBSPOT (2 items)

RowIDItemNotesHUB-ESCALATIONSEscalation queue reviewPull all open HubSpot tickets; close resolved, escalate overdue; flag any ticket open &gt;30 daysHUB-LEASEENDLease end date pipeline updateMove leases past 180-day mark to "Approaching"; verify renewal status; flag any tenant at Month-to-Month &gt;60 days

**Process:** Use HubSpot MCP (`search_crm_objects`) to pull all open deals in the Tenant Renewal Pipeline. Identify tenants with lease expiring within 180 days not yet in pipeline and add them.

---

## CATEGORY 7 — TENANT COMMUNICATION (2 items)

RowIDItemNotesTC-LEASERENEWALSLease RenewalsDraft renewal offers for leases expiring in 90–180 days (use lease-renewal-pipeline or document-assembly skill)TC-DELINQUENCYDelinquency EmailsRun AR aging from each PM platform; cross-reference with HubSpot; draft notices per escalation ladder

**Delinquency Escalation Ladder:**

- Day 3 past due: Friendly reminder (tenant-email or document-assembly skill)
- Day 10 past due: Formal notice with late fee calculation
- Day 30 past due: Demand letter with cure period per lease
- Day 45+ past due: Attorney referral packet (Philip Collins)

---

## CATEGORY 8 — ASSET MANAGEMENT FEES (3 items — QUARTERLY: Jan / Apr / Jul / Oct only)

RowIDEntityNotesAMF-MUIRKIRKMuirkirk PropertiesPer management agreement; post QB JE from Oxford Capital → property entityAMF-EGFLLCEGFLLCPer management agreement; verify intercompany eliminationsAMF-FVCFVCPer management agreement

**Non-quarterly months:** Accrue 1/3 of quarterly fee each month so quarterly close is clean.

---

## CATEGORY 9 — INSURANCE (13 properties)

### Track monthly; flag renewal months for advance renewal action (initiate 60 days prior)

RowIDPropertyRenewal MonthINS-3540FIFTH3540 E 5th AveJanuaryINS-3034WESTERVILLE3034 WestervilleSeptemberINS-3883LIVINGSTON3883 LivingstonJuneINS-FVCFVCFebruaryINS-1100RARIG1100 RarigMarchINS-29000INFO29000 Info LaneDecemberINS-9620STATE3509620 State 350OctoberINS-9050REDBRANCH9050 Red Branch RdMonthly escrow — verify each monthINS-1900BROADWAY1900 N BroadwayAugustINS-7658FISHEL7658 FishelMarchINS-401SUNBURST401 SunburstNo renewal month on record — monitorINS-55NEWPLANT55 New PlantJanuaryINS-2203NORTHWOOD2203-2207 NorthwoodOctober

**Each month:** Confirm coverage is current for all properties. In renewal months, initiate renewal 60 days in advance; confirm binder received before expiration.

---

## CATEGORY 10 — TAXES (13 properties)

RowIDPropertyFrequencyDue MonthsTAX-3540FIFTH3540 E 5th AveSemi-annualJan, JunTAX-3034WESTERVILLE3034 WestervilleSemi-annualJan, JunTAX-3883LIVINGSTON3883 LivingstonSemi-annualJan, JunTAX-FVCFVCSemi-annualJan, JunTAX-1100RARIG1100 RarigSemi-annualJan, JunTAX-29000INFO29000 Info LaneSemi-annualSep, DecTAX-9620STATE3509620 State 350AnnualDecTAX-9050REDBRANCH9050 Red Branch RdMonthly (escrowed)Every monthTAX-1900BROADWAY1900 N BroadwayAnnualJulTAX-7658FISHEL7658 FishelSemi-annualJan, JunTAX-401SUNBURST401 SunburstSemi-annualSep, DecTAX-55NEWPLANT55 New PlantAnnualSepTAX-2203NORTHWOOD2203-2207 NorthwoodSemi-annualSep, Dec

**Each month:** Verify 9050 Red Branch escrow is current. In tax due months, confirm payment processed and post QB expense entry. Flag any outstanding tax bill.

---

## MONTHLY CASH FLOW SUMMARY (Reference)

LineAverage/MonthExternal payments we make (borrower)\~$70,730External interest we receive (lender)\~$10,291Internal interest we receive (accrual)\~$15,218**Net (all receive − all pay)\~($45,221) net outflow before rental income**

*Source: Master Excel Template → Monthly Checklist → Cash Flow Summary (rows 83–86)*

---

## EXECUTION SEQUENCE

When this skill is triggered, execute in this order:

### Step 1 — Determine what's due this month

```
Current month: [MONTH YEAR]
Quarterly month (Jan/Apr/Jul/Oct)?   [YES → include Cat 8 AMF]
Tax RowIDs due this month:           [from Cat 10 schedule]
Insurance renewal RowIDs this month: [from Cat 9 schedule]
Restoration Church Trust balloon:    [months to 2/20/2027; borrower's repayment/extension status]
```

### Step 2 — Generate prioritized checklist
For each item due:
```
☐ [RowID] — [Item Name]
   System: [QB entity / PM platform / HubSpot / bank]
   Steps: [numbered sub-steps]
   Downstream if missed: [consequence]
   Est. time: [X min]
```
Execution order: Cat 1 → Cat 2 → Cat 3 → Cat 8 (if quarterly) → Cat 4 → Cat 5 → Cat 9 → Cat 10 → Cat 6 → Cat 7

### Step 3 — Check Notion for in-progress status
Query Notion Operations Hub (DB: 32b6ecd8) for last month's "Monthly Close" page. Identify any items NOT marked complete. Flag as "CARRIED FORWARD — INCOMPLETE FROM [PRIOR MONTH]" at top of this month's checklist.

### Step 4 — Track completion
As Gabriel confirms items complete, mark ✅ with timestamp. Flag any item incomplete by end of 1st business day.

### Step 5 — Post to Notion Operations Hub
Create **"Monthly Close — [MONTH YEAR]"** page in Notion Operations Hub (DB: 32b6ecd8) with:
- Balloon alert with months remaining to 2/20/2027
- Carried-forward incomplete items from prior month
- Full checklist with all applicable items
- Cash flow reference summary
- Completion status: OPEN

---

## IF INVOKED AS A SCHEDULED TASK (no live registration as of 2026-07-09 — monthly-close-kickoff retired 2026-06-09)

1. Surface Restoration Church Trust balloon watch (months to 2/20/2027; capped at WARNING — Oxford is the lender, confirm the borrower's repayment/extension terms; never escalate to CRITICAL)
2. Determine active categories this month (quarterly, semi-annual, annual gates)
3. Check Notion for prior month's incomplete items; carry forward
4. Generate full applicable checklist per execution sequence
5. Post checklist page to Notion Operations Hub (DB: 32b6ecd8)
6. Email summary to ggoldberg@oxfordra.net ONLY via Outlook (routing canon: no cc — the ora-am-brief Daily Brief is the sole cc-Eric exception and does not extend here)
   - Subject: "ORA Monthly Close Kickoff — [MONTH YEAR] — [N] items due"
   - Include: balloon alert, active category list, item count by category, Notion page link, carried-forward items

---

## OUTPUT FORMATS
- Checklist: Posted to Notion Operations Hub + inline in Cowork chat
- Journal entry workpapers: XLSX (use xlsx skill)
- Tenant notices: DOCX (use tenant-email or document-assembly skill)
- Summary report: Markdown in Cowork chat

---
name: portfolio-reporting
description: "Oxford Realty Advisors portfolio-level reporting and investor-ready output generation. Use this skill whenever the user mentions: portfolio report, quarterly report, annual report, investor report, portfolio summary, portfolio overview, portfolio performance, KPI report, management report, board presentation, portfolio PowerPoint, or any request to produce a summary of portfolio performance across all properties and markets. Also trigger when the user asks for a consolidated view of the entire Oxford portfolio. v1.1 — changelog in body."
---

## Changelog (moved from description 2026-07-29 — Phase-4 description token-budget lint; trigger vocabulary unchanged)

v1.1 (2026-07-15: LOW fix, ora-skill-text-audit — Parchment token corrected #F5F0E8 -> #F5F3EF to match ORA Institutional Style Guide v1.0+)

# Portfolio Reporting — Oxford Realty Advisors

## MODULE 1: REPORT TYPES

### Monthly Operating Report
**Audience:** Internal (Gabriel, Eric)
**Format:** XLSX workbook (use xlsx skill)
**Frequency:** 1st business day of month, covering prior month
**Contents:**
- Per-property NOI summary: GPR → vacancy loss → EGI → OpEx → NOI
- Variance to budget (month and YTD)
- Occupancy changes: move-ins, move-outs, new leases, renewals
- Collections summary: collected % of scheduled rent, AR aging snapshot
- CapEx activity: projects completed, spend vs. budget, projects in progress
- Tenant event log: defaults, renewals, notices received/sent
- Portfolio-level rollup row at bottom of every tab

### Quarterly Portfolio Review
**Audience:** Internal IC review; structured to be LP-ready if needed
**Format:** PPTX presentation (read and use pptx skill)
**Frequency:** January, April, July, October
**Contents:**
- Executive summary: portfolio KPIs vs. prior quarter
- Market-by-market performance table (Columbus, MD, KC, Indy)
- Acquisition pipeline update: deals under LOI, under PSA, closed in quarter
- Debt summary: total outstanding, weighted average rate, upcoming maturities
- CapEx forecast: planned major expenditures next 2 quarters
- Lease expiration calendar: next 12 months
- Key risks and mitigations

### Annual Report
**Audience:** Internal board-level; structured for future capital partner review
**Format:** DOCX report (use docx skill) + abbreviated PPTX deck
**Frequency:** February (covering prior calendar year)
**Contents:**
- Year-in-review narrative: acquisitions, dispositions, major operational events
- Full-year financial summary: revenue, NOI, NOI margin, DSCR
- Year-over-year property comparison table
- Portfolio valuation update (income approach: NOI ÷ market cap rate by submarket)
- Debt portfolio summary: all loans, rates, maturities, LTV
- Strategic outlook: target markets, acquisition criteria, AUM trajectory

### Ad-Hoc Snapshot
**Audience:** Broker meetings, lender conversations, partner discussions
**Format:** Inline markdown or HTML artifact (2 minutes to produce)
**Contents:**
- Total AUM, SF, property count, market count
- Occupancy rate, WALT, collections rate
- Current acquisition pipeline (deal count and aggregate size)
- One-sentence Oxford narrative

---

## MODULE 2: DATA SOURCES

Pull data from these sources in priority order:

| Data Type | Primary Source | Fallback |
|-----------|---------------|---------|
| Property NOI, revenue, expenses | Notion Property Financials DB | Gabriel-provided QB export |
| Occupancy, rent roll, lease terms | Notion Tenant Database | Gabriel-provided rent roll |
| Lease expirations, renewal pipeline | Notion Tenant Database views | Manual input |
| Active deals, pipeline value | Notion Acquisition Pipeline Tracker | Gabriel-provided deal summary |
| Debt balances, rates, maturities | Notion Loan Portfolio Tracker (V2) | Memory context |
| Portfolio AUM, LTV | Memory context + manual input | Gabriel-provided estimate |
| Market cap rates | Memory context + web search (recent comps) | Gabriel-provided estimate |

Before pulling data, check when each source was last updated. If >30 days, flag to Gabriel.

---

## MODULE 3: PORTFOLIO-LEVEL METRICS (always include)

Calculate and present all of the following in every report regardless of type:

| Metric | Definition | Calculation |
|--------|-----------|-------------|
| Total AUM | Estimated market value of entire portfolio | Sum of (property NOI ÷ submarket cap rate) across all properties |
| Total SF | Gross rentable area owned | Sum of all property GRAs |
| Portfolio occupancy | Occupied SF ÷ total SF (by SF, not by unit count) | Occupied SF / Total SF |
| WALT | Weighted average lease term remaining | Σ (remaining term × occupied SF) / total occupied SF |
| Portfolio NOI | Total net operating income | Sum of all property NOIs (trailing 12 months or annualized current) |
| NOI margin | NOI ÷ Effective Gross Income | NOI / EGI |
| Total debt outstanding | Sum of all outstanding loan balances | Pull from Loan Portfolio Tracker |
| Portfolio LTV | Total debt ÷ Total AUM | Total debt / Total AUM |
| Weighted avg cost of debt | Weighted average interest rate across all loans | Σ (balance × rate) / total balance |
| Collections rate | Collected rent ÷ scheduled rent | Collected / Scheduled (trailing 3 months) |
| Revenue per SF | Annualized EGI ÷ total SF | Annualized EGI / Total SF |
| Property count | Number of distinct properties owned | Count of active entities with properties |
| Tenant count | Number of active leases | Count from Tenant Database |
| Market count | Number of distinct metro markets | Count of unique market tags |

---

## MODULE 4: FORMATTING STANDARDS

### XLSX Reports
- One tab per property + one "Portfolio Summary" tab as first sheet
- Oxford Navy (#1B2A4A) header row, Oxford Gold (#C9A96E) subheader rows
- IBM Plex Mono for all numeric cells
- Conditional formatting: green for positive variance, red for negative
- Locked header rows; print area set to A1:[last populated column]

### PPTX Reports
- Read pptx SKILL.md before generating any presentation
- Use Oxford design tokens: Navy #1B2A4A, Gold #C9A96E, Parchment #F5F3EF
- EB Garamond for display headings, DM Sans for body text
- Max 6 bullet points per slide; data-dense charts preferred over text

### DOCX Reports
- Read docx SKILL.md before generating any document
- Institutional-grade formatting: table of contents, section headers, page numbers
- All financial tables formatted consistently with 2 decimal places for $/SF, 1 decimal place for %
- No color gradients; Oxford Navy/Gold/Parchment only

---

## MODULE 5: ANNUAL VALUATION METHODOLOGY

For portfolio valuation updates:

**Income Approach (primary method):**
- Stabilized NOI = In-place NOI adjusted for known lease changes in next 12 months
- Market cap rate by submarket (pull from memory or web search):
  - Columbus OH shallow-bay: [search for current market cap rate]
  - MD/DC industrial: [search for current market cap rate]
  - Kansas City MO: [search for current market cap rate]
  - Indianapolis IN: [search for current market cap rate]
- Property value = Stabilized NOI ÷ Market cap rate
- Portfolio value = Sum of all property values

**Replacement Cost Check (secondary validation):**
- Estimated replacement cost per SF by market: $85–$120/SF depending on market
- If income approach value < replacement cost, flag as below-replacement-cost confirmation

**Discount to Replacement Cost:**
- Calculate: (Replacement cost per SF − Income approach value per SF) ÷ Replacement cost per SF
- Report as "acquisition premium/discount to replacement cost" for each property

---

## TRIGGER PHRASES
Activate this skill when Gabriel says:
"portfolio report", "quarterly review", "annual report", "how is the portfolio performing", "portfolio summary", "portfolio snapshot", "KPI report", "investor report", "how many properties", "what's our AUM", "occupancy rate", "WALT", "portfolio NOI", "portfolio LTV", "management report", "board deck", "portfolio presentation"

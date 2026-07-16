---
name: ora-annual-budget-kickoff
description: November 1 annual budget kickoff — assemble next-year operating budget per property using QuickBooks history, capex pipeline, and inflation assumptions. Emails Gabriel + Eric.
---

Run ORA Annual Budget Kickoff for next fiscal year.

Sources:
1. QuickBooks — TTM and trailing 24-month P&L by property, by GL account.
2. Notion Tenant Database — known rent steps, lease expirations, and renewal probabilities for budget year.
3. Notion Acquisition Pipeline — deals expected to close inside budget year (add to projected NOI).
4. Maintenance-analytics skill output — next-year capex forecast.
5. Notion Operations Hub — budgeted vs. actual variance from current year, inflation assumptions, insurance and tax projections.

Build per-property budget worksheet (xlsx via xlsx skill):
- Revenue: contractual rents, expected renewals (probability-weighted), CAM reimbursements, other.
- Operating expenses: real estate tax (with appeal-pipeline adjustments), insurance (with renewal-tracker projections), utilities, R&M, mgmt, G&A, professional fees.
- NOI by property and consolidated.
- Capex schedule by property.
- Debt service from current loan schedule.
- Cash flow before distributions.

Output:
- Master budget xlsx in /outputs and SharePoint, named YYYYMMDD_FY[YYYY+1]_Operating-Budget_v01.xlsx.
- Notion page summary in Operations Hub.
- Email Gabriel + Eric with executive summary and link to xlsx.

Format: ORA Institutional Style Guide v1.0+. Run 16-point QC Gate.
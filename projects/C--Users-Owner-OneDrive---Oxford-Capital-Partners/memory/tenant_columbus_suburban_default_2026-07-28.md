---
name: tenant-columbus-suburban-default-2026-07-28
description: "Columbus Suburban Construction (Morrison 386+388, ORA-T-105) defaulted and vacated; claim $23,959.24 incl. August rent; deposit-on-expansion miss"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7f165cf0-a02a-4e4f-b5a8-20853ce05faf
  modified: 2026-07-28T18:26:01.627Z
---

Gabriel confirmed 2026-07-28: **Columbus Suburban Construction** (Joel Cooper, Tenant ID ORA-T-105, Morrison units 386+388, 3,600 SF, $3,502/mo) **defaulted and vacated**. The unit has **not been re-leased**. **April, May, June and July 2026 rent are all unpaid** (~$14,008; ~$17,510 if liable through the original 2026-08-31 contract expiry).

This answers the question the `ora-lease-snapshot-refresh` task raised when the lease-end date moved *backwards* from 2026-08-31 to 2026-05-31 — that date is the **vacate date**, not a data-entry slip, and not a repeat of the 2026-07-25 parse corruption. Verified: workbook row 122 matches the snapshot exactly.

**The master workbook handles it correctly** — row 122 is `Vacant: Yes` / `Expired`, so its SF lands in Vacant SF (B154) and its $42,024 is backed out of annualized rent (B161). Occupancy and rent are NOT overstated. Do not "fix" this.

**VERIFIED TOTALS** (Sepich Portfolio Delinquency 7.15.2026, PM = Kohr Royer Griffith, acct 13519):
Rent **$14,008.00** + Other **$6,449.24** = ledger total **$20,457.24** as of 7/15/26. Prior Notion `AR Balance` of $5,670.84 understated this by **$14,786.40** — corrected in Notion.

**Gabriel ruling 2026-07-28 (final):** August rent added to the claim (liable through contract term regardless of vacate date) → **claim total $23,959.24**, net of $1,600 deposit = **$22,359.24** pursued. The Notion `AR Balance` field stays at the $20,457.24 ledger snapshot until KRG's next export posts the August charge — don't conflate the ledger figure with the claim total.

**Security deposit ruling:** the $1,600 deposit (unchanged since 2021 despite the 2024 addendum doubling the space) is a confirmed **one-off mistake** for this tenant — Gabriel confirmed ORA's standing practice is to raise deposits on expansion. Scoped as tenant-specific, not asserted as a portfolio-wide pattern; a spot-check of other expansion addenda is a separate, unconfirmed follow-up.

**Lease terms (verified against source documents 2026-07-28):**
- Prime Lease 2021-08-29; Landlord **Fairground Village Center, LLC** (MD LLC); Tenant **Joel Ryan Cooper AND Columbus Suburban Construction, JOINTLY AND SEVERALLY** — Cooper is a direct co-tenant, personally liable. No separate guaranty needed or expected; the blank `Guarantor Name` field was a red herring.
- Term 2021-09-01 → **2026-08-31**. Addendum 2024-09-03 expanded to 3,600 SF (386+388) at $3,400/mo eff. 2024-10-01, 3% each 09-01 → current $3,502. Addendum reconfirms the 2026-08-31 termination.
- Default Rate **18%/annum**; late fee **10%** after 5 business days; Security Deposit **$1,600** (never raised when the 2024 addendum doubled the space).

**Two dates, both correct — do NOT reconcile one to the other:** contract expiry is **2026-08-31**; the workbook's Lease End of **2026-05-31** is the **vacate** date. The workbook's treatment (`Vacant: Yes` + `Expired`) is what puts the SF into Vacant SF (B154) and backs the $42,024 out of annualized rent (B161). Setting Lease End back to 08-31 would flip status to "Expiring Soon" and **re-inflate occupancy and annualized rent**. Leave it alone.

**Gotcha:** the PM system spells the tenant **"Columbus Suburan Construction"** (missing the `b`). Any AR reconciliation keyed on the correct spelling silently misses this record — that is how a $20K balance stayed invisible. See [[reference-tenant-name-mappings]].

**Collection track:** handled by the **Columbus PM (KRG) collection group** per Gabriel 2026-07-28 — NOT the Philip Collins referral drafted 2026-04-08/04-14, which was never dispatched and is superseded. Do not re-raise Collins for Columbus tenants.

**Corrected:** HubSpot deal 58522276430 was **already closed-lost on 2026-07-25**. The Tenant DB Notes describing it as open at `appointmentscheduled` were themselves stale — verify HubSpot directly rather than trusting that field. See [[feedback-verify-before-repeating-session-claims]].

**How to apply:** use $20,457.24 as this tenant's exposure, not $5,670.84. Related: [[reference-delinquency-report-collection-status-blindspot]], [[project-master-workbook-no-single-writer-2026-07-24]].

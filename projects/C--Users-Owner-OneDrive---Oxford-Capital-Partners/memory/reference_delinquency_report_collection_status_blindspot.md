---
name: reference-delinquency-report-collection-status-blindspot
description: "The delinquency report infers \"no action taken\" from a static 90+ balance, but a balance in legal process is SUPPOSED to freeze — collection activity lives in Outlook PM threads the report cannot see"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 99bbd3a1-ff6c-4785-a3ac-ae6560909a70
  modified: 2026-07-24T15:18:41.881Z
---

**The false signal.** The Delinquency Aging report (monthly, sourced from PM-platform A/R exports —
see [[reference_quickbooks_financials]] and the AR source-of-record chain in `ora-am-brief` §4c) flags
"repeat default-notice candidates whose 90+ tranche is flat or growing since [prior cycle] — none show
evidence of the [prior] recommended attorney referrals having been dispatched."

**That inference does not hold, and on 2026-07-24 it was wrong for at least 4 of 6 flagged tenants.**
A 90+ balance that sits unchanged is exactly what you expect while a matter IS in legal process — the
tenant stops paying, the balance freezes, and the case proceeds. Static balance is evidence of
*nothing*; it is equally consistent with total inaction and with an eviction already filed.

**What the 2026-07-24 audit actually found in Outlook**, against the July report's six "no evidence of
action" tenants:

| Tenant | Report's claim | Actual, from Outlook |
|---|---|---|
| PRO REPAIR LLC | 90+ flat, no action | **Eviction notice issued 2026-04-01** ("Eviction Notice 1100 Rarig Unit M&N Pro Repair"), thread through 04-04 |
| Fully Equipped Cleaning (Malik) | balance growing, no action | PM Paul Trautman (KRG) offered voluntary-vacate then 3-Day notice 05-04; payment plan negotiated; payments $300 (05-01), $350 (05-14), $985 (05-17); Gabriel 05-14: "next time he asks for any deviation from the plan, we are evicting him" |
| Columbus Suburban Construction | 90+ unchanged, confirm attorney queue | Active — 2802 Banwick eviction thread live 07-21→07-23 with KRG |
| New Benevis Smiles (largest, $53.7K) | first $25K breach, needs review | **Active collection via CRC's Heather Applegarth as of 07-23** — check expected, did not arrive, she is chasing Samantha at Benevis |
| — | — | Separately: "Joel Cooper Collection" referral opened 07-20 (Gabriel → Trautman: "can we send this one to collections?") |

**Root cause.** Collection status lives in **Outlook threads with the property managers**
(Paul Trautman / Kohr Royer Griffith for the Columbus assets; Heather Applegarth / Community Realty
for the CRC Maryland assets) — not in the A/R export, not in the Notion Tenant DB. The report has no
field for it, so every cycle it re-derives "no action" from the only thing it can see, the balance.

**Why this matters more than a cosmetic defect.** It is a credibility leak in the direction that
hurts: it cries wolf every month on tenants that *are* being worked, which trains the reader to
discount the section — including the month a genuinely-untouched tenant appears in it.

**Do not repeat the inference.** Before writing "no evidence of action" for any tenant, search Outlook
(inbox + sent) for the tenant name AND the property name over the period in question. Absence of a
balance change is not absence of action.

**Watch for a second trap:** an "Attorney Referral" subject line is NOT necessarily an ORA collection
matter. The 2026-05-26 thread by that exact name was Caroline Van Fleet (Tower Alliance) asking
whether Philip Collins would take on an American Tower landlord as a client — unrelated to
delinquency. Read the body, not the subject.

**The fix is NOT a new field — verified 2026-07-24, and this corrects an earlier draft of this note.**
The Tenant DB (data source `collection://b12f4cfd-a995-4755-8341-6435ae8173b4`) **already carries the
exact schema needed**, and has for some time:

- `Lease Default / Cure Status` — a select whose options are precisely the collection ladder:
  `None` · `Notice Given` · `Cure Period Active` · `Default Declared` · `Legal Proceedings` · `Resolved`
- `Notice Given Date` (date) · `Notice Sent` · `Required Notice Period (Days)`
- `Interaction Log` (relation) · `Last Interaction Date` · `Interaction Count`

**Every one of those fields is empty for every flagged tenant.** Live query, 2026-07-24:
PRO REPAIR, Columbus Suburban, GT Industrial, Masala Bazaar (XPO), New Benevis, TYM Wholesale, and
Fully Equipped all return `cure_status: null` and `notice_date: null`. Only Columbus Suburban has a
single `Interaction Log` entry. So the gap is **populate + read**, not **create** — and adding a
`Collection Status` property (the obvious-looking fix) would have produced a SECOND empty field
sitting beside an already-empty one, making the problem harder to see, not easier.

Two things must change, neither of which is a schema edit:
1. **Something must write it.** The A/R cycle is the natural owner: when reconciling the PM export it
   already touches each tenant row (37 updated in the July cycle), and the PM threads that hold the
   status are the same ones being reconciled.
2. **The report must read it** before ever writing "no evidence of action," and say
   *"collection status not recorded — verify in Outlook before acting"* when it is null, in the same
   spirit as the §4c coverage-gap language. Null must read as *unknown*, never as *no action*.

**Do not back-fill these fields from email inference.** `Lease Default / Cure Status` is a legal-status
field on the system of record; an email subject line reading "Eviction Notice …" evidences that a
notice was *drafted or discussed*, not that it was *served*, and the distinction is exactly what the
field exists to record. Populating it needs the PM's confirmation per tenant (Invariant 7).

**Also noted in the same query:** archived duplicates co-exist with live rows for several of these
tenants (e.g. two `GT Industrial Supply, INC.` rows, one `⛔ ARCHIVED 2026-07-12 —` prefixed, BOTH
carrying `AR Balance 3279.2`). See [[reference_tenant_db_completeness_gap]]. And `AR Balance` here is
the **furthest-aged-tier subtotal, not the tenant total** — PRO REPAIR shows 6322.86 (its 90+ figure),
not its 11886.39 total. That matches Data-Quality Finding 4 in the July report; do not read the two as
inconsistent.

Related: [[reference_warehouse_basis_parsing]], [[reference_tenant_name_mappings]],
[[people]] (PM contacts), [[reference_tenant_db_completeness_gap]].

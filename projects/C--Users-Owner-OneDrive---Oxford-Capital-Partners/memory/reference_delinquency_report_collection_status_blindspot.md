---
name: reference-delinquency-report-collection-status-blindspot
description: "The delinquency report infers \"no action taken\" from a static 90+ balance, but a balance in legal process is SUPPOSED to freeze — collection activity lives in Outlook PM threads the report cannot see"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 99bbd3a1-ff6c-4785-a3ac-ae6560909a70
  modified: 2026-07-24T15:10:00.741Z
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

**Proposed durable fix (NOT built — needs Gabriel's call):** add a `Collection Status` +
`Collection Last Activity` field to the Notion Tenant DB, populated from the PM threads, and have the
delinquency cycle cite it instead of inferring. Until then the report should say "collection status
not visible to this report — verify in Outlook before acting," in the same spirit as the §4c
coverage-gap language.

Related: [[reference_warehouse_basis_parsing]], [[reference_tenant_name_mappings]],
[[people]] (PM contacts), [[reference_tenant_db_completeness_gap]].

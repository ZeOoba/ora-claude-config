---
name: renewal-cohort-rulings-and-lease-basis-2026-09-18
description: "Gabriel's 2026-09-18 rulings on the 11-30/12-31-2026 renewal cohort — who already has an offer out, lease expense basis by property (9050 Red Branch = NNN), GT Industrial bay layout, Fresenius rent schedule, and four tenant-row facts"
metadata:
  type: reference
---

Rulings and facts Gabriel gave in a Code session on 2026-09-18, after the HubSpot renewal reconciliation ([[reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23]]).

**Renewal offers — status as of 2026-09-18 (Gabriel sends these himself; neither HubSpot stage nor Notion `Renewal Offer Date` records it):**
- ALREADY SENT: Hermiston, Corsets and Cogs, Peninsula Pressure, Reddish Fire (all 2207 Northwood), LinerX (9050 Red Branch). A HubSpot NOTE on each deal records this; stages were left at `appointmentscheduled`.
- NOT YET SENT: Curren Solutions (29000 Information Lane 206), GT Industrial Supply (1100 Rarig), J&R Enterprises (9620 State 350 105B). No drafts were requested.
- State of Missouri Dept of Agriculture (9620 State 350, exp 2026-12-31): Gabriel / the PM handle it directly — do not draft. Research caveat on the deal note: counterparty is the State OA/FMDC Real Estate Services, options possibly exhausted [unverified against the lease].
- **How to apply:** a first-stage HubSpot renewal deal is NOT evidence that a renewal is un-worked. Ask, or check Outlook sent mail, before flagging a tenant as "no renewal activity" or proposing a letter.

**Lease expense basis by property (needed before ANY rent comp is read):**
- 9050 Red Branch (Columbia MD): **NNN** — Gabriel, 2026-09-18.
- 2203-2207 Northwood (Salisbury MD): gross + utilities, no NNN pass-throughs — ORA's own listing, corroborated 2026-09-18; recorded as modified gross in event_log 2026-08.
- 29000 Information Lane (Easton MD): modified gross — event_log 2026-08.
- 1100 Rarig (Columbus OH): modified gross, tenant pays utilities + opex increases over base year — Gabriel-confirmed, event_log 2026-08.
- 9620 State 350 (Raytown MO): treated as gross in the 2026-08 market-rent work; the State of Missouri lease is gross-to-landlord per the State's standard form [agent research, unverified against the executed lease].

**GT Industrial (1100 Rarig, "F & I + J", 4,800 SF):** one 3,000 SF bay and one 1,800 SF bay that CAN be separated — so price it as two re-lettable bays, not one block with a full size discount.

**Baltimore Dialysis / Fresenius (1900 N Broadway 103, 9,030 SF) — extended-term rent schedule supplied by Gabriel:** 9/1/2026-8/31/2027 $21.90/SF, $16,479.75/mo, $197,757.00/yr · 2027-28 $22.56, $16,976.40, $203,716.80 · 2028-29 $23.24, $17,488.10, $209,857.20 · 2029-30 $23.94, $18,014.85, $216,178.20 · 2030-31 $24.66, $18,556.65, $222,679.80 (~3.01%/yr, fixed schedule). The workbook still carried $16,555/mo and escalation -0.0001 on 2026-09-18 → WBC-019 filed; Notion corrected.

**Tenant-row facts:** 2207 Northwood A3 = Grails TCG, LLC and A4 = Sky Shield — two tenancies, same contact (Brett Lagana), both through 2029-08-31; the workbook is right and Notion's "Sky Shield on A3" was the error. Evans Gymnastics (A15) is OUT; Impact Home Technology takes A15 from 2026-10-01. American Tower cell-tower easement at 2018 Zettler is TERMINATED/SOLD — not ORA income. Columbus Suburban Construction's Notion row stays LIVE on purpose until its AR is resolved (do not count its SF/rent). Carlton Handy's balance is with the property manager. See also [[reference_2207_northwood_mtm_tenants_not_holdover_2026-09-18]].

**Leasing of vacant suites is handled by THIRD-PARTY PMs / listing brokers, not by Gabriel (ruled 2026-09-18).** So the right vacancy tool is a weekly vacancy-AGING / accountability report (days vacant, asking vs last rent, listing status per suite), NOT a tenant lead engine — do not propose or build lead-gen for ORA's own vacancies. Context: vacancy was the largest dollar item found that day (Granite Tops' 11,160 SF at Zettler vacant since 2026-07-31, asking $8,500/mo; eight rows under notice to vacate), far larger than the ~$10–25K/yr of renewal repricing upside. Report not yet built as of this entry.

**Adjacent-owner outreach (ruled 2026-09-18):** to be a NEW hash-locked T1 variant (`t1-adjacent.txt`, manifest `variant` key, `ring-screen` targeting source) — never the unhashed interest-sentence shortcut. Built as a patch in `Claude_Workspace/03_Code/owner-outreach-adjacent-variant/`; Gabriel applies and re-hashes himself. Standard T1's "roughly 600,000 square feet" becomes "more than 500,000 square feet" (workbook: 512,258 SF) in the same re-ratification. Morrison Rd anchor parcel confirmed: Franklin 010-208204 (FVC LLC). Ring-screen outputs: `02_Outputs/2026-09-18_RingScreen-*`.

**Sizing of "escalation enforcement" and "rent mark-to-market" (2026-09-19, from the 09-18 rent roll) — both smaller than first ranked; do not rebuild as new systems.** (1) Escalation leakage: only 6 of 125 paying leases have a passed escalation date, **$3,075/yr even if every step was missed** — not worth a system. (2) Rent gap: the raw screen (18 leases >10% under their building's recent-lease median) read $141,943/yr, but that proxy is built from small bays; after a 7%-per-doubling size adjustment and a trend guard it is **about $82-101K/yr over 24 months and $13-15K/yr in the next 120 days**. Trend-down buildings flagged: 29000 Information Lane (median $14.80, newest lease $13.60) and Morrison (median $13.30, newest $12.00). Built as an informational column in the weekly `ora-renewal-hubspot-reconcile` UPCOMING table (STEP 6a, v1.2) — not a new task. Data point for the pending J&R letter: the 9620 State 350 recent-lease median is $8.92 (n=4, larger units), so the proposed $9.75 sits ~9% above it and rests on asking comps and a small-unit premium, not on ORA's own executed leases.

**Comps reports (asking-rent evidence, LOW-MODERATE confidence):** `Claude_Workspace/02_Outputs/2026-09-18_RenewalComps-*_Report_v01.md`. Headline: only Peninsula Pressure, Hermiston and J&R showed a real gap; everything else is retention.

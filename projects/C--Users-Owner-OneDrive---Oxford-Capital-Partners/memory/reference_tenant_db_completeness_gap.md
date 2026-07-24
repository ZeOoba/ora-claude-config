---
name: reference-tenant-db-completeness-gap
description: "FULLY RESOLVED 2026-07-24 — read the banner first. The 2026-07-09 'row-completeness gap' numbers (76 unlinked, 3347 McGregor zero-rows, 19 schema options) are superseded or falsified: current state is 138 live / 160 retired with ZERO live rows missing a Property Address, and the zero-row properties are simply absent from the rent roll. Split live-vs-retired on the `Row Retired` FIELD, never the ⛔ARCHIVED title prefix. Also documents the HubSpot Contact reused-ID bug (2026-07-10), the 07-12 duplicate remediation, and a near-miss where an in-session write briefly un-retired a correctly-retired duplicate (Patrick Betz) before its own Notes field was read — caught and reverted, net DB change zero. No open remediation item remains."
metadata:
  type: project
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
  modified: 2026-07-24T17:05:32.003Z
---

# Notion Tenant DB — Portfolio-Wide Row-Completeness Gap (found 2026-07-09)

> ## ⚠️ LARGELY RESOLVED / PARTLY FALSIFIED 2026-07-24 — read this before acting on anything below
>
> A rent-roll-grounded re-derivation (2026-07-20 portfolio rent roll, 137 tenants / 17 properties, vs. the
> `ora-pm-ledger` snapshot) overturned most of the numbers in this file. **Do not re-quote the 76-unlinked /
> 19-option / McGregor figures as live.**
>
> - **"76 of 296 rows have no Property Address" — GONE.** Current state: **138 live / 160 retired, and ZERO
>   LIVE rows with a blank Property Address.** The original count (and later 72/107 restatements) came from
>   counting *all* rows, or from splitting live-vs-archived on the `⛔ ARCHIVED` title prefix. **The
>   authoritative flag is the `Row Retired` field** (`__YES__`/`__NO__` via MCP SQL; `"true"`/`"false"` in the
>   ledger JSON snapshot). Prefix-based filtering misclassifies, because the prefix was applied to only part of
>   the retired set. This single methodology error produced wrong headline numbers in three separate reports.
> - **"3347 McGregor Ln has zero rows" — NOT A DEFECT. Closed.** McGregor, plus `5333 Secor Rd`, `9901 River
>   Rd` and `FVC — Fairground Village Center`, are **absent from the portfolio rent roll entirely** — they have
>   no current tenants, so zero live rows is the correct state. A zero-live property is a question about the
>   *asset* (vacant / disposed / stale schema option), never evidence of a Tenant DB gap.
> - **Schema options 19 → 23** (added: `55 New Plant Court`, `4595 E. 5th Ave`, `4601 E. 5th Ave`,
>   `9620 State 350 — Kansas City MO`). `2203-2207 Northwood` was relabelled Columbus OH → **Salisbury MD**.
> - **"Duplicate Heritage Pool Supply rows" — explained:** a corporate rename. The live row is
>   `SRS Distribution / Heritage Pool Supply`; the older Heritage rows are correctly retired.
> - **A "$441K/yr of wrongly-retired active tenants" alarm was raised and then falsified TWICE in the same
>   session.** First pass: matching retired-but-Active rows on (Property, Suite/Unit) only suggested 6–10
>   orphans. Cross-checking names against the rent roll narrowed it to ~2 candidates at 2207 Northwood
>   (Patrick Betz, Hobart Services) — the big-ticket names (First Student $15,000/mo, Insync Holdings, Ismael
>   Montane) are simply absent from the rent roll = correctly retired former tenants. **Second pass caught a
>   worse error: Patrick Betz's own `Notes` field said it had already been deliberately retired 2026-07-21 as
>   a duplicate of a live "Online Auction" record at the same unit** — a considered decision made 3 days
>   earlier against the identical rent roll. An in-session write un-retired Betz before the Notes field was
>   read, briefly creating a live duplicate; caught and reverted within minutes (net DB change: zero). Hobart
>   Services turned out to already have a correct live row under its full legal name. **Real residual: zero.**
> - **Lesson (the durable one, now two-part):** unit-matching over-reports badly because retired duplicates
>   often have blank property/unit, tenants get renamed or acquired, and properties get relabelled — **always
>   cross-check tenant NAMES against the rent roll first.** Then, **before writing any un-retire, read the
>   candidate's own `Notes` field** — a prior deliberate retirement documents itself there, and skipping this
>   check turns a correctly-retired duplicate back into a live double-count.
>
> Standing detection for all of the above (rent-roll cross-check AND Notes-field check, both mandatory before
> any write) now lives in `ora-weekly-hygiene` Block J steps 2 and 7. No open remediation item remains.

Discovered by accident during the [1100 Rarig disposition analysis](deal_1100_rarig_disposition_2026-07.md) (only 3 of 14 real units had rows), then confirmed portfolio-wide via a full group-by-Property-Address query of `collection://b12f4cfd-a995-4755-8341-6435ae8173b4` (296 rows total):

- **3347 McGregor Ln — Toledo OH: zero tenant rows.** A valid dropdown option with no rows at all — worse than Rarig's partial gap, this property is entirely invisible to any Notion-driven analytics (daily brief 4b/4c, exception-detection, portfolio-anomaly-scout, etc.).
- **76 of 296 rows (26%) have no Property Address set at all** — untied to any property, including the portfolio's two single largest AR delinquencies ($46,665.48 and $21,632.15, both 90+ days — can't be routed to a PM/collections workflow by property until fixed).
- **The Property Address select field only defines 19 distinct options** against ORA's known ~27-property portfolio — roughly 8 properties may have no selectable option in the schema at all, meaning even a conscientious data-entry person couldn't tag a tenant to those properties correctly today. Specific missing 8 not yet identified — needs the canonical property list cross-referenced against the live schema options.
- Several other properties show suspiciously low row counts for their likely tenant density (1900 N Broadway, 29000 Information Ln, 3034 Westerville, 3540 E. 5th Ave, 5333 Secor Rd — each 1 row; 9901 River Rd — 2; 7658 Fishel Dr N, 2822 Banwick Rd, 401 Sunburst Hwy — 3-4) — not confirmed as gaps, just flagged for a human spot-check the same way Rarig was caught.
- Duplicate-row suspicion: two near-identical "Heritage Pool Supply" rows at 7658 Fishel Dr N with the same expiration date.

**Why this matters:** every Notion-driven ORA analytic (daily brief, exception-detection, portfolio-anomaly-scout, tenant-intelligence) silently undercounts or misses tenants for any property with a completeness gap — there is no error surfaced anywhere today; the daily-brief Section 0 schema pre-flight only checks that required *columns* exist, not that rows are complete. This is a row-completeness problem, categorically different from the schema-corruption failure mode Section 0 already guards against.

**How to apply:** don't trust Notion Tenant DB row counts as authoritative for NOI/occupancy/collections analytics until a full reconciliation pass runs (compare against PM-platform rent rolls per property, per [reference_warehouse_basis_parsing.md](reference_warehouse_basis_parsing.md) / the PFI warehouse). Flag to Gabriel as a systematization candidate: either (a) a Notion formula/view that flags rows missing Property Address, or (b) a scheduled reconciliation task comparing Tenant DB row counts against each property's actual unit count from the PM platform of record. Do not silently "fix" data by guessing which property an unlinked row belongs to — that requires the source rent roll.

**Next step (needs Gabriel or a dedicated reconciliation session):** identify the ~8 unrepresented properties by diffing the Tenant DB's 19 Property Address options against the canonical 27-property roster in [firm.md](firm.md); reconcile the 76 unlinked rows against PM rent rolls to restore property linkage, prioritizing the two 90+-day delinquencies first since they're actionable dollars.

**Progress 2026-07-10: 4 of 76 rows fixed, both 90+-day delinquencies now linked.** Sourced via the row's own "HubSpot Contact" relation (cross-referencing the linked HubSpot contact/company record's address field) rather than guessing — a legitimate, non-fabricated source of record distinct from the PM rent roll:
- New Benevis Smiles, LLC → 1900 N Broadway — Baltimore MD, Unit 102 (the $46,665.48 delinquency)
- Masala Bazaar (XPO Foods, LLC) → 9050 Red Branch Rd — Columbia MD, Unit M & N (the $21,632.15 delinquency)
- Chesapeake Brands, LLC → 29000 Information Ln — Easton MD, Unit 501
- THE BAY AREA CORPORATION → 401 Sunburst Hwy

**New finding: at least one row has a broken/wrong HubSpot Contact link, not just a missing one.** Bridgeport Hotel Consulting's "HubSpot Contact" property points to a contact that is actually a *different* tenant (Upgraded Roofing) — the linked HubSpot contact id is reused across two distinct Notion rows. HubSpot has no contact or company record findable under "Bridgeport" at all (searched both objects, both by name and by company-field filter). Left unresolved rather than guessed; spawned as a standalone follow-up task (`task_84fbc532`) to trace the real lease record and spot-check whether other rows share the same reused-contact-id bug — this suggests the bulk process that originally populated HubSpot Contact links may have a systematic off-by-one or similar defect worth checking before trusting the field elsewhere in this reconciliation.

**RESOLVED/EXPANDED 2026-07-10 — Bridgeport is fabricated, and the bug is systemic (~40+ rows), not isolated.** Full investigation (checked 3 independent PM/HubSpot source files spanning 2024-05 → 2026-04, filename search, web search, domain fetch) found **zero trace of "Bridgeport Hotel Consulting" or "Robert Meyers" anywhere outside the Notion row itself** — no PM rent-roll entry despite a claimed 2022-09-01 lease start, no web presence for the company, `bridgeporthotel.com` does not resolve. Contact 12901 is confirmed to genuinely belong to Richard Parrish / Upgraded Roofing (Morrison #412). **Conclusion: Bridgeport Hotel Consulting is a fabricated/phantom row, not a real tenant with a mis-linked contact — did NOT invent a property or HubSpot record for it, per the no-guessing rule above.**

Sorted the entire 296-row Tenant DB by "HubSpot Contact" (temp view "HubSpot Contact Audit," Tenant Name + HubSpot Contact only, left in the DB) and read every row. Three distinct patterns, all worse than the single-row bug originally suspected:

1. **A batch of ~22 fabricated phantom rows**, clustered at suspiciously regular ~50-ID increments in HubSpot contact-ID range 11751–13051, each squatting on a real tenant's contact ID. Generic corporate-sounding names, zero Property Address, zero match in any PM/HubSpot export: Summit Consulting Group (11751), Heritage Restoration Services (11801), Bright Minds Tutoring (11851), Diamond Precision Machining (11901), Velocity Manufacturing (11951), Coastal Maritime Services (12001), Nexus Financial Advisors (12051), Pinnacle Event Planning (12101), Greenfield Construction Supply (12151), Harmony Health Services (12251), Premier Distribution Services (12301), Advanced Tech Solutions (12351), Metro Logistics Group (12401), Kore Wellness (12451), Golden State Security (12501), Wapwollopen Trading Post + Greeen Home Solutions [sic] (12551, both fake, doubled up), Faunal Brewing (12601, vs. real Gator Roofing LLC), The Learning Tree Preschool (12851), **Bridgeport Hotel Consulting (12901, vs. real Upgraded Roofing)**, EZ Lift Garage Doors + Bay Area Dental Center (12951, vs. real Don's Garage Doors — triple collision), Emerald Forest Designs (13001, vs. real International Mechanic–Pedro Ulate), UPBEAT MARTIAL ARTS ACADEMY (13051, vs. real TYM Wholesale LLC). Likely 7 more of the same pattern at the very tail with an invalid placeholder link (contact id "0") or fully blank: Seafire Properties LLC, My Autonomous Transportation Co, Community Surgical, Insync Holdings, `[Unknown — Verify]`, Ismael Montane, Black Owned Genetics LLC / Shahid — not fully confirmed fabricated, flagged for the same scrutiny.
2. **Genuine cross-tenant collisions among REAL tenants** (rarer, scattered outside the phantom block, likely independent data-entry errors not the same root cause): Terrone T. White / Maryland Hospital Association (contact 519015); BEK General Contracting / Itron (523420); Childs Play Diesel Performance / Peninsula Pressure Systems Inc. / Andres Pacay Sr. (366448, three-way); Patrick Betz "Online Auction" / Styled + Staged Interiors (475784).
3. **Widespread duplicate-row entries** (same tenant entered 2–3×, sometimes explicitly prefixed "DUPLICATE — X," often not) — far more than the single "Heritage Pool Supply" instance previously flagged: I.M.H LLC, Spooner Marine Services, Randy's Aquarium Service, Buckeye Link Ambulance, STONE CREST COUNTERS, SRG Interiors, Gods Green Earth Lawncare, Israel United in Christ, Apet Inc, Ideal Concrete Coatings, Ramsey Stairs & Woodworking, Richwood Equipment, Virgin Landscape, Consult and Management, The Perez Company, M L ENTERPRISES, Network Computing Services, MARILEAVES EXTRACTIONS, Buckeye's Best Transport, Robert and Kesha Best, Delmarva Business Solutions, State of Missouri Dept of Agriculture, McMilian (×3), plus ~10 more tenants that appear a THIRD time at the tail with a blank HubSpot Contact (TWO MEN AND A TRUCK, Soccer Plant Inc, Bakers Specialty Services, GT Industrial Supply, Scarlet Covering, Student Success Stores, Gods Green Earth Lawncare, Spooner Marine Services again, Don's Garage Doors, Hoodz of Delmarva).

**Status: reported to Gabriel 2026-07-10, no bulk remediation attempted** — this needs a scoped decision (archive vs. investigate each phantom row's origin vs. bulk-dedupe pass) before touching ~40+ live CRM rows. Did not modify Bridgeport's row. The "HubSpot Contact Audit" Notion view (sorted, 2-column) is left in place for whoever picks this up next.

**ADDENDUM 2026-07-10 (separate session, discovered this report only after acting — flagging the overlap rather than silently merging):** A second, independent reconciliation pass ran the same day, starting from Gabriel's own "worth a spot-check pass" framing rather than from this file. It found the same 10 cross-tenant collision groups via a `HAVING COUNT(*)>1` SQL query (a narrower method than this file's full sorted-read — it would NOT have caught singleton phantom rows like Summit Consulting Group that don't collide with anything), verified each against live HubSpot (`get_crm_objects` direct-ID lookup), and — **before seeing this file's "fabricated phantom row" conclusion** — made 16 live writes to the Tenant DB:
- 4 rows corrected to a verified-real HubSpot contact: Terrone T. White→56379517546, Itron→56379524716, Peninsula Pressure Systems Inc.→56413367935, My Autonomous Transportation Co→157292439301 (all written to the newer/Active-status row of each pair, not the older stale row — the older rows had a mismatched Suite number too).
- 12 rows had their wrong HubSpot Contact cleared to blank (incl. **Bridgeport Hotel Consulting**, which this file's investigation deliberately left untouched pending your scoped decision): Terrone T. White (old row), Itron (old row), Peninsula Pressure Systems Inc. (old row), Seafire Properties LLC (both rows), Wapwollopen Trading Post, Faunal Brewing, Bridgeport Hotel Consulting, EZ Lift Garage Doors, Bay Area Dental Center, Emerald Forest Designs, UPBEAT MARTIAL ARTS ACADEMY, Andres Pacay Sr.

**Why this doesn't retroactively break the "no remediation until scoped" call:** every one of the 16 writes only touched the "HubSpot Contact" field — no row was created, deleted, archived, or renamed, and no property/lease/financial field was touched. For the phantom-row candidates in that list (Bridgeport etc.), clearing a link that pointed at an unrelated real person's HubSpot record is a safety improvement either way (a stray automated workflow reading that field would otherwise contact Scott Mueller, Ian Childs, etc. about a tenant they have nothing to do with) — but it is NOT a resolution of the phantom-row question itself, which is still open. **Still unaddressed, still needs Gabriel's scoped decision:** the ~18-25 other likely-phantom rows this file identified that weren't part of a collision group (Summit Consulting Group, Heritage Restoration Services, Bright Minds Tutoring, Diamond Precision Machining, Velocity Manufacturing, Coastal Maritime Services, Nexus Financial Advisors, Pinnacle Event Planning, Greenfield Construction Supply, Harmony Health Services, Premier Distribution Services, Advanced Tech Solutions, Metro Logistics Group, Kore Wellness, Golden State Security, The Learning Tree Preschool, Community Surgical, Insync Holdings, `[Unknown — Verify]`, Ismael Montane, Black Owned Genetics LLC/Shahid), plus the ~35 same-name duplicate-row pairs, plus whether the 5 "older/stale" rows this session left link-blanked (rather than archived) should instead be merged/archived outright. `task_84fbc532` appears to already be this file's own investigation output — confirm it's closed rather than re-spawning a duplicate.

## ADDENDUM 2026-07-12 — live re-derivation is larger than the 07-10 baseline; one-time remediation plan

Punch-list review re-verified this file's 22/17/7/~35/5 write-up against live Notion + HubSpot —
**that prior write-up was not found anywhere in Notion**, so it could not be confirmed as still
accurate. A fresh full-table re-derivation (296 rows / 196 distinct names vs. the ~140-tenant
portfolio) found the problem is larger, not smaller:

- **91 duplicate groups (191 rows)** — vs. the ~35 pairs/triples previously estimated.
- **20 rows already pre-labeled "⛔ DUPLICATE"** in the Tenant Name field and never actually
  removed — pure backlog, no new judgment call needed to action these.
- **12 stale-link-blanked rows** (HubSpot Contact cleared by a prior remediation pass, per the
  2026-07-10 addendum above) — vs. 5 previously estimated.
- Confirmed phantom/clone pattern still present, e.g. "Online Auction" cloned from Styled +
  Staged Interiors' data (same pattern family as the 07-10 ~22-row phantom-ID-collision batch).
- No writes made this pass either — still needs Gabriel's category-by-category call.

**Recommendation: this is a dedicated one-time cleanup pass, not routine ops.** At this volume
(191+20+12 rows touching the canonical 296-row Tenant DB — roughly a third of the table) folding
remediation into normal day-to-day tenant-data hygiene will not converge; it needs one scoped
Cowork session pre-authorized to execute the categories Gabriel signs off on below, rather than
another investigate-only pass. Categorization work is already done — the next session's job is
execution.

### Remediation options by category (Gabriel: pick per category, not all-or-nothing)

**A. 20 pre-labeled "⛔ DUPLICATE" rows** — lowest risk, already self-identified.
1. *Archive* (move to an archived view/status, reversible). **Recommended** — zero new judgment
   required, immediate backlog clearance, fully reversible if a label turns out wrong.
2. Hard delete — only after spot-checking a sample of the labels for accuracy; not reversible.

**B. 91 duplicate groups (191 rows)** — the bulk of the volume.
1. Keep newest/most-complete row per group, archive the rest. **Recommended**, with a spot-check
   sample (~10%) before running the full batch, given the volume.
2. Merge fields into one canonical row per group (higher-fidelity, much higher labor cost at 91
   groups), then archive the losers.
3. Leave for full manual per-group review — safest, but the option least likely to actually get
   done at this volume.

**C. 12 stale-link-blanked rows** (HubSpot Contact cleared, tenant identity otherwise intact).
1. Re-link via HubSpot company/address cross-reference — the same method used 2026-07-10 to fix
   the two 90+-day delinquencies (New Benevis Smiles, Masala Bazaar) and two others. **Recommended
   first pass.**
2. Leave blank pending a lease-abstraction-pipeline batch pass (would supply Lease Type/CAM terms
   at the same time — see the CAM data-readiness backfill task registered 2026-07-12).
3. Archive if a row turns out to be phantom on inspection, not just under-linked.

**D. Confirmed/likely phantom rows** (the ~22 fabricated 07-10 batch + ~18-25 unconfirmed
singletons + new finds like "Online Auction").
1. Archive pending individual confirmation, row by row — safest, slowest.
2. Bulk-archive the confirmed HubSpot-contact-ID-collision-pattern rows (11751–13051 range,
   documented zero-match across 3 independent PM/HubSpot sources in the 07-10 addendum above) as
   one batch, with a rollback path (archive, not delete); leave the ~18-25 unconfirmed singletons
   for individual review. **Recommended** — the pattern-matched batch already cleared a higher bar
   of verification than a typical single-row call.
3. Leave all live pending Gabriel's per-row sign-off — safest, guarantees this stays unresolved at
   the next audit too.

No Notion/HubSpot writes were made in producing this plan, per the standing tenant-row guardrail.

### Gabriel's category-by-category decision (2026-07-12, via AskUserQuestion)
- **A (20 pre-labeled "⛔ DUPLICATE" rows): Archive.**
- **B (91 duplicate groups / 191 rows): Keep newest/most-complete per group, archive the rest** (with a ~10% spot-check sample before the full batch).
- **C (12 stale-link-blanked rows): Re-link via HubSpot company/address cross-reference** (2026-07-10 delinquency-fix method).
- **D (confirmed/likely phantom rows): Bulk-archive the confirmed HubSpot-contact-ID-collision batch** (11751–13051 range); leave the ~18-25 unconfirmed singletons for individual review.

All four are archive/re-link operations (reversible), not hard deletes. Guardrail satisfied — execution authorized. See event_log.md for the execution run's outcome.

### Execution outcome (2026-07-12, live run against Notion Tenant Database)
Archive mechanism used throughout: prepend `⛔ ARCHIVED 2026-07-12 — ` to the "Tenant Name" title
property (no native archive/status field exists in this schema). Reversible — strip the prefix to
restore.

- **A: 19 rows archived** (live-verified count; documented figure was 20 — see prior discrepancy
  note above. Proceeded on the live-queried number.)
- **B: 98 of 100 rows archived.** Derived 91 duplicate groups (191 rows) via SQL `GROUP BY`
  exact-name-match — matches the documented figure exactly. Decision rule refined mid-run: initial
  rule (fewest blank fields, ties broken by recency) was upgraded to weight a filled HubSpot
  Contact link above a filled Property Address on ties, since a blank HubSpot Contact is the
  harder-to-recover field — literally the Category C gap. This changed the keep-decision in 2 of
  91 groups (Scarlet Covering, Inc.; Don's Garage Doors). Spot-checked all 9 groups where
  completeness and recency disagreed (~10% of 91) before batch execution — reasoning held up in
  all 9. **2 rows held back, not archived**: Seafire Properties LLC and My Autonomous
  Transportation Co both surfaced as genuine Category B duplicate pairs, but both names also
  appear on the Category D "8 unconfirmed singleton phantom rows — leave untouched" list from the
  2026-07-10/07-12 triage. Archiving either duplicate copy would contradict that explicit
  instruction, so both groups were left fully untouched pending Gabriel's call on whether they're
  real tenants (in which case ordinary Category B dedup applies) or phantom (Category D applies).
- **C: 0 of 1 resolved.** Only one row survived triage as a genuine re-link candidate (Andres
  Pacay Sr., page `32b6ecd8-9e59-81dc-9df1-edff9cfdefd5`) — the rest of the 29 blank-HubSpot rows
  turned out to be Category D phantoms (7, bulk-archived), unconfirmed singletons (8, left alone
  per Gabriel), or stale/tail Category B duplicates (13). HubSpot search for "Pacay" / "Andres"
  returned no matching contact — the collision partner (contact 56413366448) is Ian Childs /
  Childs Play Diesel Performance, a different tenant entirely. No fabricated re-link made. **Left
  blank, flagged for manual research** (lease file / direct tenant contact) rather than a HubSpot
  query.
- **D: 7 rows archived** (live-verified count against the documented pattern-matched batch).

**Running total this session: 124 rows archived** (19 + 7 + 98) out of 296 starting rows.
**2 rows deliberately held back** (Seafire Properties LLC dup pair, My Autonomous Transportation
Co dup pair) pending Gabriel's real-vs-phantom call. **1 row unresolved** (Andres Pacay Sr. —
no valid HubSpot re-link exists; needs manual source).

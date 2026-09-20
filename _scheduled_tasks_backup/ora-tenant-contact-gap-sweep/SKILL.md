---
name: ora-tenant-contact-gap-sweep
description: Weekly sweep of Notion Tenant Database for active/M2M tenants missing Primary Contact or Contact Email; cross-checks each gap against HubSpot in batched token queries, and posts a consolidated gap list to Notion Operations Hub so contact backfill is tracked centrally instead of being re-discovered ad hoc in each Lease Expiration Brief. Read-only/report-only — the guarded writes live in ora-hubspot-notion-contact-sync (Thu), which this sweep audits. v1.3 2026-08-28: step 1 gap filter pushed SERVER-SIDE (the prior step demanded "exactly ONE" SQL call then told the run to paginate with LIMIT/OFFSET — self-contradictory against a 135-row population; now ~23 rows, never paginates, with population_count + backfilled_count subqueries); step 8 fallback corrected — view URLs are {{view://uuid}} on the DATABASE fetch, never "?v=" and never on the data-source fetch, an error that hard-stopped the 08-28 sync run; step 3c adopts the sync task's ratified affirmative-signal domain test so the two tasks cannot contradict each other; step 6a now audits via the Contact Source='HubSpot backfill' provenance count rather than only diffing report pages. A suspected truncation bug was investigated and NOT confirmed — the 08-24 Maryland undercount was the narrative-vs-table error already diagnosed in v1.2. v1.2 2026-08-24: SINGLE-QUERY discipline, view-mode fallback, mandatory cross-foot. v1.1 2026-08-17: batched cross-check + match guards. Retimed 2026-07-30 from 8:00 AM to 10:50 AM ET. [MODEL: claude-sonnet-5 | set 2026-07-30]
---

This is an automated run of a scheduled task for Gabriel Goldberg, Oxford Realty Advisors (ORA). The user is not present — execute autonomously, make reasonable choices, note them in the output. This task only posts a report to Notion (no external sends, no tenant/counterparty contact).

CONTEXT: The Notion Tenant Database (data source id b12f4cfd-a995-4755-8341-6435ae8173b4, collection URL collection://b12f4cfd-a995-4755-8341-6435ae8173b4; database wrapper id 8dbbaec0-611a-4617-be07-6a77d0d0307a is not SQL-queryable but IS the only fetch target that exposes view URLs — see step 8) has a chronic data gap: many active tenant records are missing "Primary Contact" and/or "Contact Email". This was discovered during the 2026-07-27 Lease Expiration Brief (10 of 14 tenants expiring within 180 days had no contact on file) and this task exists to track the gap on a standing cadence rather than rediscovering it per-brief.

RELATIONSHIP TO ora-hubspot-notion-contact-sync: As of 2026-08-24 a separate Thursday task performs the guarded HubSpot→Notion backfill writes. THIS task remains read-only and report-only — it never writes contact data. Its role is now twofold: track the residual gap, and act as an independent audit of whether the sync task is actually closing rows. If the gap count is flat or rising week over week while the sync task reports writes, say so explicitly in the report — that divergence is the finding.

STEPS:

1. SINGLE QUERY — issue exactly ONE notion-query-data-sources SQL call, and make that one call sufficient. Do NOT issue a separate COUNT query, a separate GROUP BY query, or LIMIT/OFFSET continuation queries. Every total, percentage, split and per-property tally is computed CLIENT-SIDE from this one result set. (The 2026-08-24 run issued three SQL calls — a COUNT, a filtered SELECT, and a GROUP BY — and the third failed with "Your workspace has reached the usage limit for Query Data Source," stranding the verification step. The SQL quota is shared workspace-wide, so a wasted call here can also break an unrelated task later the same day.)

   Use this query shape — do not simplify it:

   SELECT
     id,
     url,
     "Tenant Name",
     "Property Address",
     "Suite / Unit",
     "date:Lease Expiration:start",
     "Lease Status",
     "Primary Contact",
     "Contact Email",
     "Secondary Contact Name",
     "Secondary Contact Email",
     "Contact Source",
     (SELECT COUNT(*) FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
       WHERE "Lease Status" IN ('Active','Month-to-Month','Notice Given')
         AND "Row Retired" = ?
         AND "Tenant Name" NOT LIKE '%⛔%'
         AND "Tenant Name" NOT LIKE '%DUPLICATE%') AS population_count,
     (SELECT COUNT(*) FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
       WHERE "Lease Status" IN ('Active','Month-to-Month','Notice Given')
         AND "Row Retired" = ?
         AND "Tenant Name" NOT LIKE '%⛔%'
         AND "Tenant Name" NOT LIKE '%DUPLICATE%'
         AND "Contact Source" = 'HubSpot backfill') AS backfilled_count
   FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
   WHERE "Lease Status" IN ('Active','Month-to-Month','Notice Given')
     AND "Row Retired" = ?
     AND "Tenant Name" NOT LIKE '%⛔%'
     AND "Tenant Name" NOT LIKE '%DUPLICATE%'
     AND ("Primary Contact" IS NULL OR TRIM("Primary Contact") = ''
       OR "Contact Email" IS NULL OR TRIM("Contact Email") = '')

   params: ["__NO__", "__NO__", "__NO__"] (the __YES__/__NO__ checkbox literals, not true/false).

   WHY THIS SHAPE:
   (a) The gap filter is pushed SERVER-SIDE. The prior spec selected the whole active population and filtered client-side, which returns ~135 rows, paginates at 100 with has_more:true, and then required LIMIT/OFFSET continuation calls — directly contradicting the "exactly ONE SQL call" rule in the same step. Filtering server-side returns roughly 20-25 rows, so has_more comes back false and one call genuinely suffices. Verify has_more is false; if it is true, report that and process only what you received, saying so explicitly.
   (b) population_count supplies "total active tenants scanned" and the denominator for the % figure without a second call. As of 2026-08-28 the true population is 135.
   (c) backfilled_count is a DIRECT audit signal for step 6a — see that step. As of 2026-08-28 it was 47.
   (d) Secondary contact fields are still selected because step 2 needs them to confirm a row is a genuine primary-contact gap, not merely a missing secondary.
   If the scalar subqueries are rejected by the SQL engine, drop ONLY those columns, re-run once, and report scanned-total and backfilled-count as "not captured this run" — never estimate them.

2. The rows returned by step 1 ARE the gap rows — the WHERE clause already applied the blank test (whitespace-only counts as blank via TRIM), and it deliberately tests only Primary Contact and Contact Email, so a row missing merely a secondary contact is correctly excluded. Do not re-filter. Note per row which specific field(s) are blank.

3. Cross-check HubSpot (search_crm_objects, objectType=CONTACT, current tenants only) by company/tenant name for each gapped row — if a matching HubSpot contact with an email exists there, note it as "available in HubSpot, not yet synced to Notion" rather than "fully missing"; this distinction matters for prioritization.

   3a. BATCH THE LOOKUPS — do not issue one search per gapped tenant. filterGroups are OR'd against each other and capped at 5 groups per call, so pack 5 single-filter groups into ONE call, each `{propertyName:"company", operator:"CONTAINS_TOKEN", value:"<distinctive token>"}`. Pick the most distinctive non-generic token from the tenant name ("Peninsula", not "Systems"; "Quirky", not "Company"). Request properties ["email","company","firstname","lastname"], limit 25. For individual-person tenants whose HubSpot `company` field may be blank, filter on `firstname`/`lastname` instead. On the 2026-08-17 run this collapsed 49 lookups into 9 calls; on 2026-08-24 and 2026-08-28, 23 lookups into 5. Two tenants sharing a token (e.g. Hoodz of Delmarva / HOODZ of Kansas City) resolve in a single group — do not spend a second one.

   3b. GUARD THE MATCHES — a HubSpot hit is a candidate, not an answer. Flag rather than silently accept: (i) an email whose domain belongs to a brokerage or third party rather than the tenant (a `@cresa.com` address on a tenant row is a tenant-rep broker, not the tenant — this fired on New Benevis Smiles, LLC on 2026-08-24 and again on 2026-08-28); (ii) more than one HubSpot contact for the same tenant — prefer the one whose email domain matches the tenant entity, and say so (this fired on DevCor, LLC on 2026-08-24 and again on 2026-08-28: Janet Haddock @devcorllc.com vs Scott Haddock @glasslock.com); (iii) obvious typos in HubSpot name fields, including trailing whitespace. Carry these to a "Data-integrity notes" section in the posted report so they are resolved before anyone backfills them.

   3c. CLASSIFY DOMAINS THE SAME WAY THE SYNC TASK DOES. ora-hubspot-notion-contact-sync ratified an AFFIRMATIVE-SIGNAL TEST on 2026-08-28; this sweep must apply the identical rule or the two reports will contradict each other — this sweep flagging as suspect the very rows the sync task legitimately wrote. The rule: a domain that is neither the tenant's own nor recognizable free mail is suspect ONLY on affirmative third-party signal — it is blocklisted, it is agent-shaped (realty / commercial / properties / law / legal / title / advisors), or it belongs to a named entity that is neither the tenant nor the contact. A domain EPONYMOUS WITH THE CONTACT PERSONALLY (their surname or personal brand) is NOT a third-party hit; note it as a disclosure, not a defect. Worked examples the sync task wrote on 2026-08-28 and this sweep must NOT re-flag as broker addresses: info@belser.co (contact John Belser), patti@spurrycurren.com (contact Patti Curren), tom@mytransportation.ai (contact Tom Johnson). Free-mail domains (gmail, yahoo, outlook, aol, comcast, verizon, protonmail) are normal in this portfolio and are never a defect on their own.

4. Sort the gap list by nearest Lease Expiration first (soonest-expiring tenants with missing contacts are the highest-priority backfill items). Rows with a null expiration sort last, not first.

5. CROSS-FOOT EVERY ROLLUP BEFORE POSTING. Any breakdown you publish — per-property, per-state, per-status, resolvable-vs-not — must sum exactly to the gap total, and you must verify that arithmetic explicitly before the page goes up. State the check in your working. CROSS-FOOT THE NARRATIVE AGAINST THE TABLE, NOT JUST THE TABLE AGAINST ITSELF: on 2026-08-24 the posted per-state rollup said "three Maryland properties carry 19 of 23" — correct but incomplete, because a fourth Maryland property held a 20th gap. The per-property table was right and the prose summarizing it was wrong. Every sentence that states a count must be re-derived from the table immediately before posting, not written from memory of the table.

6. Post the list to the Notion Operations Hub (page id 32b6ecd8-9e59-81f2-b329-df3fd0e25062) as a new page titled "Tenant Contact Gap Sweep — [ISO date]", containing: total active tenants scanned (population_count), count and % missing contact, a split of gaps into "resolvable from HubSpot" vs "no contact anywhere", the sorted table, a per-property concentration count, a per-state rollup, the Data-integrity notes from 3b/3c, the sync-audit block from 6a, and a recommendation whose source is DERIVED FROM THE SPLIT — not assumed. If most gaps resolve from HubSpot, the recommendation is to let ora-hubspot-notion-contact-sync clear them and to name only the residue it cannot; only rows HubSpot cannot resolve warrant pulling a PM platform export (Yardi/AppFolio/Rent Manager, per property) or QuickBooks tenant records. Do not state a PM-platform/QuickBooks pull is required without first showing that HubSpot failed to cover those rows — 2026-08-17 found HubSpot covered 49 of 49, 2026-08-24 found 22 of 23, and 2026-08-28 found 23 of 23.

   6a. SYNC AUDIT — two independent signals, report both.
     - PROVENANCE COUNT (primary, and more reliable than page-diffing): backfilled_count from step 1 is the number of active rows carrying Contact Source = 'HubSpot backfill'. Compare it to the prior sweep's figure. If ora-hubspot-notion-contact-sync ran on the intervening Thursday and reported writes, this number must have RISEN by at least that many rows. If it is flat while the sync task claims writes, the sync is failing silently or its writes are being reverted — that is the headline finding, not a footnote. Baseline: 47 on 2026-08-28 (26 from the 2026-08-17 sweep + 21 from the 2026-08-28 sync run).
     - WEEK-OVER-WEEK GAP DELTA (secondary): search the Ops Hub for the prior "Tenant Contact Gap Sweep" page and report the change in gap count. Baseline: 23 gaps against a 135-row population on 2026-08-28 (17.0%), of which 2 were parked by guards and 21 were written.
     If no prior page is found, say so and skip the delta rather than inventing a baseline. Note that a gap count can legitimately stay flat while backfilled_count rises, if new tenant rows were added — say which is happening rather than asserting failure.

7. Do not email this report (no routing configured for this task); it is a Notion-only tracking artifact. Do not attempt to contact any tenant, and do not write contact data into Notion from this task under any circumstance — writes belong to ora-hubspot-notion-contact-sync. If a field is unknown, leave it blank and list it as a gap.

8. FALLBACK — if the single SQL call in step 1 fails with a "Query Data Source" usage-limit / quota error, do NOT retry it and do NOT abandon the run. Switch to the view-mode path (no SQL quota), verified working on this database 2026-08-28:
     - Call notion-fetch on the DATABASE WRAPPER id 8dbbaec0-611a-4617-be07-6a77d0d0307a — NOT on the collection:// data source. Views are emitted only by the database fetch; the data-source fetch contains none. This distinction is load-bearing.
     - That fetch is ~84K chars and will overflow the tool-result cap and spill to a one-line .txt. Do not try to Read it whole. Run C:\Users\Owner\ora-skills\tools\notion_fetch_digest.py against the spilled file; it prints the collection URLs, every view URL, and the property schema in a few hundred tokens.
     - View URLs are emitted as {{view://<uuid>}}. THEY ARE NOT "?v=" URLs. The prior version of this step asserted the view_url must contain "?v=<view-id>" — that assertion is FALSE and would send a run looking for a pattern that never appears, producing a false "no view available" conclusion and an unnecessary hard stop. That exact false negative occurred in the 2026-08-28 sync run. Search for `view://`.
     - Pass the bare string "view://<uuid>" as view_url. notion-query-data-sources accepts it directly.
     - Call with mode "view", page_size 100, looping next_cursor→start_cursor until has_more is false, then filter and aggregate client-side (notion-quota-fallback bundles scripts/notion_view_query_aggregate.py for this). View mode returns a per-row url.
     - DO NOT invent, guess, or hardcode a view id. If no view URL can be obtained from the database fetch, say so plainly and stop.
     - Note in the posted report that the run used the fallback path, since that is itself a signal the workspace quota is under pressure.

9. If the Notion MCP tools are unavailable on this surface entirely, state that plainly in a fallback text note and stop rather than improvising a substitute data source.

CHANGELOG
- v1.3 (2026-08-28): Four fixes. (1) STEP 1 rewritten — the prior step told the run to issue "exactly ONE" SQL call and then, two paragraphs later, to paginate with LIMIT/OFFSET when has_more came back true, which is self-contradictory and guaranteed 2+ calls against a 135-row population. The gap filter is now pushed server-side so the result is ~23 rows and never paginates, with population_count and backfilled_count scalar subqueries supplying the figures the extra calls were being spent on. (2) STEP 8 FALLBACK CORRECTED — it asserted view_url must contain "?v=<view-id>". That is false: Notion emits {{view://<uuid>}}, and only on the database-wrapper fetch, never the data-source fetch. The old text would have sent a quota-stalled run hunting a pattern that does not exist and stopping unnecessarily; this is exactly what happened to the sync task on 2026-08-28. Added a pointer to tools/notion_fetch_digest.py for reading the oversized fetch. (3) STEP 3c ADDED — the sweep now applies the same affirmative-signal domain test the sync task ratified on 2026-08-28, so the two tasks cannot reach opposite conclusions about the same address; without it this sweep would flag as broker addresses the three contact-eponymous domains the sync task legitimately wrote. (4) STEP 6a UPGRADED — the sync audit now leads with the Contact Source = 'HubSpot backfill' provenance count (a direct measurement of rows the sync actually wrote) rather than relying solely on diffing report pages, which only ever showed what the sync CLAIMED. Step 5 tightened to require every count-bearing sentence be re-derived from the table immediately before posting. NOTE for the record: a suspected 100-row truncation bug in this task was investigated on 2026-08-28 and NOT confirmed — step 1 already instructed pagination, and the 2026-08-24 Maryland undercount was a narrative-vs-table error, correctly diagnosed in v1.2. The pagination instruction was removed for the quota/self-contradiction reasons above, not because it was producing wrong counts.
- v1.2 (2026-08-24): SINGLE-QUERY discipline in step 1 — one SQL call, all aggregates client-side. The 2026-08-24 run issued three (COUNT, filtered SELECT, GROUP BY) and the third hit the shared workspace quota, stranding verification; the quota is workspace-wide, so waste here can break unrelated tasks the same day. Added step 5 (mandatory cross-foot of every rollup, narrative against table — that run published a state rollup that undercounted Maryland by one property while the table beneath it was correct), step 6a (week-over-week delta, with a flat-or-rising count treated as evidence the new sync task is failing silently), and step 8 (notion-quota-fallback view-mode path, with an explicit prohibition on inventing a view id). Step 7 tightened: this task is now formally read-only, since guarded writes moved to ora-hubspot-notion-contact-sync. Step 3b annotated with the live 2026-08-24 guard hits (New Benevis/cresa.com broker domain; DevCor multi-contact) so the guards carry worked examples rather than hypotheticals.
- v1.1 (2026-08-17): Added 3a (batch HubSpot token filters, 5 filterGroups per call — 49 lookups collapsed to 9 on the 2026-08-17 run) and 3b (match guards: third-party/broker email domains, multi-contact tenants, HubSpot name typos). Rewrote Step 5 so the backfill-source recommendation is derived from the HubSpot-coverage split rather than hardcoded to a PM-platform/QuickBooks pull — the original wording asserted a source the first full run disproved (HubSpot covered 49 of 49 gaps). Report now also carries the coverage split, per-property concentration, and Data-integrity notes.
- v1.0 (2026-07-27): Initial. Retimed 2026-07-30 from 8:00 AM to 10:50 AM ET.
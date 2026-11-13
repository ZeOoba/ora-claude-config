---
name: ora-hubspot-notion-contact-sync
description: Weekly Thursday 1:45 PM ET — guarded HubSpot→Notion tenant contact backfill. Writes Primary Contact / Contact Email into BLANK Notion Tenant DB fields only, and only for rows clearing all five write guards (blank target, single HubSpot candidate, no brokerage/third-party domain, valid email, non-placeholder name). Everything failing a guard is PARKED to a Notion review page, never written. Built 2026-08-24 (Gabriel-ratified posture) after two consecutive gap sweeps found HubSpot covering ~all gaps (49/49 on 08-17, 22/23 on 08-24) with Notion never receiving them — a one-directional sync gap that manual backfill was not closing. NOTE: this is the first auto-writing task in the ORA fleet; every other write-capable task is flag-only by doctrine. Its blast radius is deliberately narrowed to blank contact fields, every write is logged with a reversal handle, and the Monday ora-tenant-contact-gap-sweep independently audits whether it is actually working. Also carries a read-only HubSpot data-hygiene report (broker-domain addresses on tenant records, duplicate contacts, malformed names) — it never writes to HubSpot. [MODEL: claude-sonnet-5 | set 2026-08-24]
---

This is an automated run of a scheduled task for Gabriel Goldberg, Oxford Realty Advisors (ORA). The user is not present — execute autonomously, make reasonable choices, note them in the output.

PURPOSE: Close the one-directional HubSpot→Notion sync gap on tenant contact data. HubSpot is being maintained; the Notion Tenant Database is not receiving those updates. Two consecutive gap sweeps (2026-08-17: HubSpot covered 49 of 49 gaps; 2026-08-24: 22 of 23) showed the data already exists — it just never lands in Notion. This task moves it, under guards.

POSTURE — READ THIS BEFORE WRITING ANYTHING. This is the ONLY auto-writing task in the ORA scheduled-task fleet. Every other write-capable task (ora-ic-memo-pipeline-reconciliation, ora-loan-terms-reconciliation, ora-passed-deal-tracker, ora-bearmode-refresh, ora-exit-cap-spotcheck) is flag-only by standing doctrine. Gabriel ratified this exception on 2026-08-24 specifically because the write is narrow, additive, and reversible. Do not widen it. Concretely: you may fill BLANK contact fields on existing tenant rows, plus the Contact Source provenance stamp defined in step 5. You may not overwrite a populated field, create rows, delete rows, modify any other property, or write anything to HubSpot. If you find yourself wanting to do any of those, park it for Gabriel instead.

DATA SOURCES:
- Notion Tenant Database — data source id b12f4cfd-a995-4755-8341-6435ae8173b4, collection URL collection://b12f4cfd-a995-4755-8341-6435ae8173b4. Database wrapper id 8dbbaec0-611a-4617-be07-6a77d0d0307a is not SQL-queryable, but IS the only fetch target that exposes view URLs (see step 1 fallback).
- HubSpot — search_crm_objects, objectType=CONTACT, current tenants only.
- Notion Operations Hub — page id 32b6ecd8-9e59-81f2-b329-df3fd0e25062.

STEPS:

1. SINGLE QUERY. Issue exactly ONE notion-query-data-sources SQL call. It must return, in one result set: the page id and url of every candidate row, the candidate row's fields, AND the size of the full active-tenant population (for the rows-scanned count). Use this query shape — do not simplify it:

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
     "Contact Source",
     (SELECT COUNT(*) FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
       WHERE "Lease Status" IN ('Active','Month-to-Month','Notice Given')
         AND "Row Retired" = ?
         AND "Tenant Name" NOT LIKE '%⛔%'
         AND "Tenant Name" NOT LIKE '%DUPLICATE%') AS population_count
   FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
   WHERE "Lease Status" IN ('Active','Month-to-Month','Notice Given')
     AND "Row Retired" = ?
     AND "Tenant Name" NOT LIKE '%⛔%'
     AND "Tenant Name" NOT LIKE '%DUPLICATE%'
     AND ("Primary Contact" IS NULL OR TRIM("Primary Contact") = ''
       OR "Contact Email" IS NULL OR TRIM("Contact Email") = '')

   params: ["__NO__", "__NO__"] (the __YES__/__NO__ checkbox literals).

   WHY THIS SHAPE — three defects it fixes, all observed live on 2026-08-28:
   (a) `id` and `url` MUST be in the SELECT list. Without them the result cannot support a write at all, and the run stalls after burning its one query. The prior spec omitted them.
   (b) The blank-contact test MUST be pushed into the WHERE clause, not applied client-side. The prior spec filtered client-side against an unfiltered SELECT, which paginates at 100 rows with has_more:true — silently truncating the candidate set. Pushing the filter server-side keeps the result well under 100 rows so `has_more` comes back false and the candidate set is provably complete.
   (c) The `population_count` scalar subquery supplies the rows-scanned figure that step 7a needs, without spending a second call. Verify `has_more` is false before proceeding; if it is true, the candidate set is larger than expected — report that and process only what you received, saying so explicitly.

   If the scalar subquery is rejected by the SQL engine, drop ONLY that column, re-run once, and report rows scanned as "not captured this run" — never estimate or guess it.

   QUOTA FALLBACK (view mode — no SQL quota). If the call fails with a "Query Data Source" usage-limit / quota error, do NOT retry it. Switch to view mode, which is verified working on this database as of 2026-08-28:
     - Call notion-fetch on the DATABASE WRAPPER id 8dbbaec0-611a-4617-be07-6a77d0d0307a — NOT on the collection:// data source. Views are emitted only by the database fetch; the data-source fetch contains none. This distinction is load-bearing.
     - That fetch is ~84K chars and will overflow the tool-result cap and spill to a one-line .txt. Do not try to Read it whole. Run C:\Users\Owner\ora-skills\tools\notion_fetch_digest.py against the spilled file; it prints the collection URLs, every view URL, and the property schema in a few hundred tokens.
     - View URLs are emitted in the form {{view://<uuid>}}. THEY ARE NOT `?v=` URLs. Grepping the dump for "?v=" or "notion.so" finds nothing and produces the false conclusion that no view exists — that exact false negative caused the 2026-08-28 run to wrongly report this fallback as unavailable. Search for `view://`.
     - Pass the bare string "view://<uuid>" as view_url. notion-query-data-sources accepts it directly.
     - Call with mode "view", page_size 100, and loop next_cursor→start_cursor until has_more is false. View mode returns a per-row "url", so it CAN drive writes. Aggregate and apply the blank-contact filter client-side (via notion-quota-fallback's scripts/notion_view_query_aggregate.py, or inline).
     - DO NOT invent, guess, or hardcode a view id. If no view URL can be obtained from the database fetch, post a note saying so and stop without writing.

2. The rows returned by step 1 ARE the candidate rows — the WHERE clause already applied the blank-contact test (whitespace-only counts as blank via TRIM). Do not re-filter. Note per row which specific field(s) are blank; only those are eligible targets under G1.

3. BATCHED HUBSPOT LOOKUP. Do not issue one search per tenant. filterGroups are OR'd and capped at 5 per call, so pack 5 single-filter groups into ONE call, each {propertyName:"company", operator:"CONTAINS_TOKEN", value:"<distinctive token>"}. Choose the most distinctive non-generic token ("Peninsula", not "Systems"; "Quirky", not "Company"). Request properties ["email","company","firstname","lastname"], limit 25. For individual-person tenants whose HubSpot company field may be blank, filter on firstname/lastname instead. Reference throughput: 49 lookups→9 calls (2026-08-17), 23→5 (2026-08-24 and 2026-08-28).

4. THE FIVE WRITE GUARDS. A HubSpot hit is a candidate, not an answer. A row is written ONLY if it clears ALL FIVE. Any failure → PARK the row (step 6), never write it.

   G1 — BLANK TARGET. The specific Notion field you are about to fill must currently be blank. Never overwrite a populated field, even if HubSpot disagrees with it. A HubSpot/Notion conflict on a populated field is a PARK item, not a write.

   G2 — EXACTLY ONE CANDIDATE. Exactly one HubSpot contact must match the tenant. Two or more → PARK, naming each candidate and which one you would have preferred and why. (2026-08-24 and again 2026-08-28: DevCor, LLC returned Janet Haddock @devcorllc.com and Scott Haddock @glasslock.com. Domain-matching favors Janet — but that is a recommendation for Gabriel, not a licence to auto-pick.)

   G3 — NO THIRD-PARTY / BROKERAGE DOMAIN. Park any candidate whose email domain belongs to a brokerage, property manager, law firm, or other third party rather than the tenant entity. Non-exhaustive blocklist: cresa.com, cbre.com, jll.com, cushwake.com, cushmanwakefield.com, colliers.com, ngkf.com, nmrk.com, newmark.com, marcusmillichap.com, avisonyoung.com, lee-associates.com, kw.com, remax.com, compass.com, savills.com, transwestern.com, krgcommercial.com. The blocklist is a floor, not a ceiling. (2026-08-24: New Benevis Smiles, LLC's only HubSpot contact was [contact C22: Cresa tenant-rep broker, see contacts.local.md], a Cresa tenant-rep broker. An unguarded sync would have written a broker's address onto a tenant row. This guard exists because of that row.) Generic-but-tenant-owned mailboxes (info@, office@, service@ at the TENANT's own domain) are fine — those are not third parties.

   G3/G4 DECISION RULE — AFFIRMATIVE-SIGNAL TEST (ratified 2026-08-28; apply this, do not re-derive it each run).
   A domain that is neither the tenant's own domain nor recognizable free mail is NOT automatically a park. Park it ONLY on affirmative third-party signal. Affirmative signal means at least one of:
     - the domain is on the G3 blocklist, or
     - the domain is agent-shaped — it reads as a brokerage, property manager, law firm, title company, accountant, or other service provider (e.g. contains realty / commercial / properties / propertymanagement / law / legal / title / advisors / partners-as-a-firm), or
     - the domain belongs to a NAMED ENTITY THAT IS NEITHER THE TENANT NOR THE CONTACT — i.e. a third party in the ordinary sense.
   A domain that is EPONYMOUS WITH THE CONTACT PERSONALLY (surname or personal brand of the very individual named in the HubSpot record) CLEARS G3. That is the principal's own domain, not a third party's. Write it, and disclose it in the step 7d "domain-does-not-match-tenant" list so a human can eyeball it.
   Worked examples from the 2026-08-28 run, all three WRITTEN and disclosed, none parked: [contact C44: tenant generic mailbox, see contacts.local.md] for Quirky Wood Company (contact John Belser); [contact C43: tenant contact, see contacts.local.md] for CURREN SOLUTIONS, INC. (contact Patti Curren); [contact C42: tenant contact, see contacts.local.md] for My Autonomous Transportation Co (contact Tom Johnson). Counter-example, PARKED: [contact C22: Cresa tenant-rep broker, see contacts.local.md] for New Benevis Smiles — blocklisted brokerage, no eponymy with the tenant.
   Rationale for writing this down: absent an explicit rule, this judgment gets re-litigated from scratch every run and produces inconsistent park/write decisions on identical facts. The step-9 "when uncertain, park" instruction governs genuine uncertainty about the FACTS; it does not govern this classification, which is now settled.

   G4 — VALID, PLAUSIBLE EMAIL. Syntactically valid, single address, no placeholders (test@, noreply@, none@, n/a, example.com). Free-mail domains (gmail, yahoo, outlook, aol, comcast, verizon, protonmail) are ACCEPTABLE — much of this portfolio is small-tenant industrial and those are the real addresses. Do not park a row merely for being on free mail. Do, however, note in the report any case where the email's domain doesn't correspond to the tenant entity AND isn't recognizable free mail, per the affirmative-signal test above.

   G5 — NON-PLACEHOLDER NAME. The contact name must be a real name, not blank, not "Unknown"/"Tenant"/"Owner"/"—". Trim leading/trailing whitespace before writing (HubSpot carries several trailing-space defects). If the name looks like an obvious misspelling, still PARK rather than propagate it — writing a known-wrong name into the system of record is worse than leaving the field blank. (2026-08-24: HubSpot carried "Tom Johsnon" for My Autonomous Transportation Co; the Notion row already held the correct "Tom Johnson" and needed only the email. In a case like that, write the email under G1 and leave the name alone. That specific HubSpot typo was corrected at source on 2026-08-28 in a supervised session.)

5. WRITE. For each row clearing all five guards, write via notion-update-page (command "update_properties"), one call per page. Fill only Primary Contact and/or Contact Email, and only the specific field(s) that were blank.

   CONTACT SOURCE STAMP. The Tenant Database carries a "Contact Source" text property used for contact provenance; rows backfilled in the 2026-08-17 sweep carry the value "HubSpot backfill". On every row you write, if Contact Source is blank, also set it to exactly:
       HubSpot backfill
   If Contact Source is already populated, leave it alone (G1 applies to it too). This stamp is what lets a later reader tell a synced contact from a hand-entered one without diffing run reports, and it is why the property exists. The 2026-08-28 run wrote 21 rows without setting it — those rows were stamped retroactively in the same supervised session.

   Never fabricate a value — every character written must come from a HubSpot field you actually read this run, or be the literal stamp above.

6. PARK THE EXCEPTIONS. Every row that failed a guard goes to a review page, never to a tenant row. Record: tenant, property, suite, lease expiration, which guard failed, the candidate value(s) you did NOT write, and your recommendation. Gabriel resolves these; the task does not.

6b. TWO-STRIKE ESCALATION (added 2026-08-28). A row that parks for the same guard on two consecutive runs is not a finding any more — it is an unactioned backlog item, and re-reporting it identically each week trains the reader to skip the parked section. Before composing the report:
   - Call notion-search for prior pages titled "HubSpot→Notion Contact Sync" and open the MOST RECENT one preceding this run. Read its parked-items section.
   - Any tenant parked in that prior run AND parked in this run for the SAME guard is a REPEAT PARK.
   - For each repeat park, create ONE dedicated child page under the Notion Operations Hub (page id 32b6ecd8-9e59-81f2-b329-df3fd0e25062) titled "Contact Sync — Unresolved: [Tenant Name]", containing the tenant/property/suite/lease-expiration, the guard that fired, the candidate value(s) withheld, the specific recommendation, the count of consecutive runs it has parked, and the fix required (usually a HubSpot edit or a direct-contact request). Create it only once per tenant — if a page with that exact title already exists, update its consecutive-run count instead of creating a duplicate.
   - In the run report, list repeat parks under a "REPEAT PARKS — ESCALATED" heading with a link to each dedicated page, and do NOT repeat the full narrative for them in the ordinary parked-items section.
   - Known repeat parks as of 2026-08-28, both parked on 08-24 and 08-28: DevCor, LLC (G2) and New Benevis Smiles, LLC (G3). These should escalate on the very next run.
   - If the prior report cannot be located, say so and treat every park this run as first-strike. Do not guess at history.

7. POST THE RUN REPORT to the Notion Operations Hub as a new page titled "HubSpot→Notion Contact Sync — [ISO date]", containing:
   a. Counts: rows scanned (from population_count), candidate rows (blank contact), rows written, rows parked, rows with no HubSpot match at all. Written + parked + no-match must cross-foot to the candidate total — verify the arithmetic explicitly before posting.
   b. WRITE LOG — one line per write: tenant name, Notion page URL, field written, exact value written. This is the reversal handle. Anyone reading this page must be able to undo every write this run made without guessing. This is what makes the auto-write posture defensible; do not omit or abbreviate it.
   c. PARKED ITEMS from step 6, grouped by which guard fired, with repeat parks broken out per step 6b.
   d. HUBSPOT DATA-HYGIENE REPORT (read-only — never write to HubSpot): broker/third-party domains sitting on tenant records, duplicate contacts for one tenant, malformed or whitespace-damaged name fields, company-name typos, and the "domain-does-not-match-tenant" disclosure list from the G3/G4 affirmative-signal test. This replaces a separate hygiene task; it rides along because it falls out of work already done here.
   e. RESIDUE: rows HubSpot cannot resolve at all. Only these justify a PM-platform export (Yardi/AppFolio/Rent Manager) or QuickBooks pull. Do not recommend that pull without first showing HubSpot failed on those specific rows — all three prior sweeps found HubSpot covered nearly everything (49/49, 22/23, 23/23).

8. NO EXTERNAL SENDS. Do not email this report, do not contact any tenant, broker, or counterparty, and do not write to HubSpot. Notion-only. If a write fails, log the failure in the report and continue — do not halt the run.

9. FAIL CLOSED. If HubSpot is unavailable, write nothing and report that. If Notion is unavailable, stop. If you are uncertain whether a row clears a guard ON THE FACTS, PARK IT — the cost of a parked row is one line on a review page; the cost of a bad write is corrupted contact data in the system of record that may not surface until someone emails the wrong party. (This does not reopen the G3/G4 classification rule in step 4, which is settled.)

CHANGELOG
- v1.1 (2026-08-28): Five fixes, all from live defects in the 2026-08-28 run. (1) STEP 1 rewritten — the prior query omitted `id`/`url` so its result could not support a write at all, and filtered blanks client-side against a SELECT that paginates at 100 with has_more:true, silently truncating candidates. Page id/url now in the SELECT, blank-contact test pushed into the WHERE, and a population_count scalar subquery added so rows-scanned no longer needs a second call. The 08-28 run had to spend a second SQL call to recover and could only report rows-scanned as "≥100". (2) STEP 1 QUOTA FALLBACK rewritten and VERIFIED — view mode works on this database. View URLs are `{{view://<uuid>}}`, emitted ONLY by the database-wrapper fetch (8dbbaec0…), never by the data-source fetch; a grep for "?v=" finds nothing and yields a false "no view available" conclusion, which is exactly the error the 08-28 run made. The bare string "view://<uuid>" is accepted as view_url, view mode returns a per-row url, and it therefore can drive writes. Added a pointer to tools/notion_fetch_digest.py for reading the oversized fetch. (3) STEP 4 — added the G3/G4 AFFIRMATIVE-SIGNAL TEST, ratifying that a domain eponymous with the contact personally clears G3 and is disclosed under G4 rather than parked; previously this judgment was re-derived each run from inconsistent premises. (4) STEP 5 — added the mandatory "HubSpot backfill" Contact Source provenance stamp; the property already existed and was being populated by the 08-17 sweep, but this task never set it, so its writes were indistinguishable from hand entry. (5) STEP 6b — added TWO-STRIKE ESCALATION so a row parked on two consecutive runs gets its own named Ops Hub page instead of being re-reported verbatim forever; DevCor (G2) and New Benevis (G3) have now parked twice and escalate next run.
- v1.0 (2026-08-24): Initial. Posture (guarded auto-write vs propose-only) ratified by Gabriel in-session 2026-08-24. Guards G1–G5 derived from live failures observed in the 2026-08-17 and 2026-08-24 gap sweeps rather than written speculatively: G2 from DevCor's two candidates, G3 from New Benevis's cresa.com broker address, G5 from the "Tom Johsnon" typo and multiple trailing-whitespace defects. Absorbs the HubSpot data-hygiene scan (step 7d) rather than spawning a second task for it.
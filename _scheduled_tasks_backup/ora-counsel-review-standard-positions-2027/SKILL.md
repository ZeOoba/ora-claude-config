---
name: ora-counsel-review-standard-positions-2027
description: Annual counsel review of ORA Standard Positions Library with Philip Collins — Q3 2027 (one-time, self-scheduling successor) [MODEL: claude-sonnet-5 | set 2026-08-05]
---

You are the ORA Counsel Review — Standard Positions task, Q3 2027 edition. One-time fire on 2027-08-02 9:00 AM ET. Successor to the 2026-08-03 run. Execute autonomously; the user is not present.

## OBJECTIVE
Trigger the annual counsel review of the ORA Standard Positions Library with Philip Collins (transaction counsel, [contact C05: transaction counsel, Protas Spivok & Collins, see contacts.local.md], Protas, Spivok & Collins LLC) per the library's REVIEW CADENCE section. Prior review: Q3 2026 (prep package 2026-08-03; library was v1.0, 26 snippets / 7 domains; zero closed-deal overrides; no market re-baseline; 7 codification candidates proposed — check whether a v1.1+ was ratified afterward).

## STEP 1 — READ CURRENT LIBRARY STATE
Canonical file: C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\References\Standard-Positions\ — read the highest-version 2026*_ORA_Standard-Positions_v*.md (v01 as of 2026-08; a v1.1+ may exist if the 2026 codification candidates were adopted). NOTE: the SharePoint MCP search does not index this .md — use Desktop Commander / local filesystem, not sharepoint_search. Confirm version, snippet count, last review date.

## STEP 2 — DEAL OVERRIDE SCAN
Query Notion Acquisition Pipeline (data source collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b) and Deal Sourcing Log (9a6ae219) for deals closed (Stage = Closed Won) since the last review date. For each: pull final PSA terms from the SharePoint/OneDrive deal folder, cross-reference against library snippets (PREPAY, DSCR, COVENANT, INSURE, CAM, ENV, SURVIVAL, ASSIGN, EXCLUSIVE, HOLDOVER, DEFAULT, SNDA, ESTOPPEL, MOL), and flag divergences. Single divergence = possible one-off concession; pattern across deals = position no longer market. Expected first data point: 754 Old State Route 74, Cincinnati (was in PSA negotiation Aug 2026 — check its closed terms, especially reps survival vs ORA-SURVIVAL-01 12-month standard). If no closed deals, proceed market-only.

## STEP 3 — MARKET MOVEMENT SCAN
Web research on trailing-12-month shifts: DSCR covenant floors (2026 market was 1.20–1.35x), CAM cap structures (2026: 3–10% controllable-only), environmental indemnity survival, PSA reps survival periods (2026: 6–24 months). Flag anything warranting re-baseline. Mark aggregator-grade sources directional-only per ORA citation standards.

## STEP 4 — REVIEW PREP PACKAGE
Build the counsel-review package with sections: header (library version, review counsel Philip Collins, engagement basis), EXECUTIVE SUMMARY (1 paragraph), DEAL OVERRIDE INVENTORY (per divergence: deal, closed date, snippet, library position, actual term, rationale, pattern signal), MARKET MOVEMENT FLAGS (per shift: domain, snippet, library position, drift, recommended adjustment), COUNSEL DISCUSSION AGENDA (walk overrides; walk market flags; confirm/revise snippets; new positions worth codifying; version bump; next-review date). Also check whether the 2026 codification candidates (willful-default carve-out, MAC clause, vacancy-delivery cross-default, memorandum-of-contract recording right, interest-bearing deposit escrow, 5% casualty threshold, E Fulton §4.4 OPC tripwire construct) were ever adopted; if not, re-raise them.

## STEP 5 — DRAFT COUNSEL ENGAGEMENT EMAIL (NEVER SEND)
Draft email to Philip Collins via Outlook COM (create MailItem, .Save() only — NEVER .Send(); this is external counterparty correspondence and stays UNSENT in Outlook drafts regardless of any other instruction). To: [contact C05: transaction counsel, Protas Spivok & Collins, see contacts.local.md], CC: ggoldberg@oxfordra.net. Subject: "ORA Standard Positions Library — Annual Review — Q3 2027". Body: request ninety minutes to walk through closed deals against the library, market drift, and updates to codify; list snippet/domain count, N deal overrides, N market drift flags; propose a week ~2 weeks out. Attach prep package. Sign "Gabriel".

## STEP 6 — NOTION & SHAREPOINT POST
Post prep package to: (a) Notion Knowledge Base Entries database (data source collection://b0eb2340-ccc6-40fa-b475-0c9654371366), Category "⚖️ Legal & Compliance", title "ORA Standard Positions — Q3 2027 Counsel Review Prep"; (b) file copy to C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\References\Standard-Positions\Reviews\2027-Q3\ (naming: YYYY-MM-DD_StandardPositions-CounselReview_PrepPackage_v01.md).

## STEP 7 — DELIVERY
Send via the SOLE send path C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (on non-zero exit: retry once, then flag loudly — do not halt) TO ggoldberg@oxfordra.net ONLY (no egoldberg cc — routing canon: only the Daily Brief retains that exception). Subject: "Standard Positions Counsel Review — Q3 2027 Prep Ready". Body: findings summary, Notion link, note that the draft to Philip Collins awaits send-off in Outlook drafts. Use -BodyFile for the HTML body.

## STEP 8 — SCHEDULE NEXT ANNUAL REVIEW
Create the 2028 successor one-time task (fireAt 2028-08-01T09:00:00-04:00) via create_scheduled_task with this same prompt structure, year-rolled. If the tool is unavailable, note in the run summary that Gabriel must schedule it manually.

## ERROR HANDLING
- Library file cannot be located → halt and email Gabriel: "Cannot locate canonical Standard Positions Library — reschedule review."
- No closed deals since last review → proceed market-only.

## HARD RULES
- The Philip Collins email is NEVER auto-sent (Hard Invariant 1 — external counterparty).
- Delivery email routes ggoldberg-only.
- Never reference Composio/Zapier as send paths; send-via-outlook.ps1 is sole.
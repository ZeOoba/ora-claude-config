---
name: broker-coverage-gap-map-findings-2026-09-19
description: "2026-09-19 broker coverage-gap map: v01's 'missed warm lead' list was REFUTED by the v02 body-level check; the real finding is unsent drafts (incl. two 808 Rhoads chases to James Koon) and an unreachable gap pool (no emails). Read before re-running the map or feeding ora-broker-touch-cadence."
metadata:
  type: reference
---

**Files** (`Claude_Workspace/02_Outputs/`): `2026-09-19_BrokerCoverageGap_Map_v01/v02.xlsx`, `…Summary_v01/v02.md`, `2026-09-19_BrokerPriority_Seed_v01.json`, `2026-09-19_BrokerReopenDrafts_Top4_v01.md` (drafts, NOT sent), `2026-09-19_BrokerDraftsBacklog_Audit_v01.md` (if present).

**What the map is:** 168 brokers/teams found from 310 usable-name rows of the 545-row Deal Sourcing Log (43% of rows never captured a listing agent). v02 verified the 40 most active previously-unverified brokers (96 Outlook searches): ACTIVE 14 · WARM 9 · DORMANT 30 · NONE 54 · UNVERIFIED 61.

**⛔ v01's "10 missed warm inbound leads" were NOT reliable — none survived a body-level re-check.** v01 tested "unanswered" from headers only. Refuted or downgraded on the threads: Oakbrook (Eric replied 'Thanks!' 5 min later; the off-market asset was already declined at $125/SF), Gunnerson (105 N Chestnut was under contract, the underwriting Q&A was about 604 N Scott Ave, ORA PASSED on 105 N Chestnut 2026-05-17, the 09-02 log row is a duplicate OCR re-intake — NOT a re-listing), Abraham (Eric answered 3x on 06-29), Wieringa/Kingma/Menninger/Ludwig (acknowledged, no follow-up), Meeder (the 09-05 'checking back in' was never SENT — it is unsent in Drafts). **Rule for any rerun:** read the last 2-3 message bodies, count a reply from ANY @oxfordra.net sender (Eric included), check Sent Items AND Drafts, never infer a re-listing from a log row without ruling out a duplicate re-intake, and carry a Confidence column.

**Real findings:** (1) three ORA follow-ups sit UNSENT in Outlook Drafts — Meeder 2026-09-05, plus two chases to **James Koon (808 Rhoads listing broker) 2026-08-13 and 08-28**; 808 Rhoads was the deal at 'proceed to LOI pending Gabriel approval' — the stall is internal, not the broker. (2) Tom Fairhurst (JLL Cincinnati) ACTIVE two-way 2026-09-16 on 11560 Rockfield Ct — ORA's only warm Cincinnati institutional line; Ryan McGreevy (NAI Ohio Equities) ACTIVE 2026-09-14. (3) Colliers Cincinnati: 19 buy-box listings vs one dormant contact (Ackerman, Keefer total nulls). (4) Bryan Herr (MacKenzie MD) is ORA's most responsive Maryland broker but appears ZERO times in the Deal Sourcing Log — he reaches ORA directly, so the automated scan is blind to him.

**Structural limits:** the gap pool is ~unreachable — only 3 of 54 NONE brokers have an email on file; the seed has 29 entries and 59 otherwise-eligible brokers were excluded for no email. Listing detail pages hide broker email/phone behind 'Contact Broker' forms; Crexi and LoopNet return 403 on search AND detail; CommercialSearch/CommercialCafe DETAIL pages yield name + firm (5/5 tested). Never guess an email from a firm pattern.

**Notion Broker Relationships DB** (`collection://48e43778-b1f2-4b16-8f3c-0bf18f8642e9`) holds ~9 rows and is not a usable ledger. Its `Markets` multi-select had NO option for Louisville, Madison, Cincinnati, Grand Rapids or Richmond (5 of 10 markets) — **FIXED 2026-09-19 at Gabriel's direction: all 5 added (13 options now), the 8 originals kept their option ids and all 9 rows verified identical before/after**; it still has no `Source`/`First Seen` property (those go in `Notes`). `ora-deal-sourcing-scan` v2.7 (2026-09-19, layered on uncommitted v2.6) now captures name+firm into the log's `Broker / Contact` and links `Broker (Linked)`; first run Tue 2026-09-22.

Related: [[people]] (verified broker rows) · [[reference_mortgage_maturity_signal_not_bulk_accessible_2026-09-18]] · [[reference_renewal_cohort_rulings_and_lease_basis_2026-09-18]].

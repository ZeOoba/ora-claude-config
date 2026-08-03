---
name: reference-catfish-court-broker-correspondence-claim-false
description: "5515 Catfish Court's Notion Broker/Source field wrongly claims zero Outlook correspondence with the M&M team — a real Timothy Sullivan thread exists with an unanswered ORA ask from 2026-07-17."
metadata: 
  node_type: memory
  type: project
  originSessionId: a3a82fa0-28ad-4f86-8e87-44ddc824a30d
  modified: 2026-07-31T13:44:03.220Z
---

The `Broker / Source` field on the **5515 Catfish Court** row in the Notion Acquisition Pipeline Tracker contains a **false correspondence-history claim**, written by `ora-deal-aging-sla` during the Gabriel-directed backfill of 2026-07-28. The field states there is "NO Outlook correspondence with any of these four" Marcus & Millichap contacts and that a re-approach "would be a cold first contact, not a follow-up."

**Ground truth (verified 2026-07-31 by recipient-domain search on `marcusmillichap.com`):** a live thread exists with **Timothy Sullivan** (`Timothy.Sullivan@marcusmillichap.com`), one of the four named contacts, subject `5515 CATFISH COURT WESTPORT, WI 53597`:

- 2026-07-15 22:33 UTC — Sullivan proposes a call.
- 2026-07-16 15:14 UTC — Sullivan: "time is of the essence… ownership is close on decision working through offer."
- 2026-07-16 20:18 UTC — Sullivan sends Westport/County C-2 zoning codes.
- **2026-07-17 17:41 UTC — Eric → Sullivan**, asking drive-in height, office SF, tenant business health, and whether the lease restricts a new landlord. **Never answered.**

**Why it matters:** Gabriel's 2026-07-24 ruling is LEAN PASS / KEEP OPEN with a **2026-08-14 re-check**. That re-check is a **warm follow-up on an unanswered ask**, not a cold first contact — a materially different posture for pricing leverage and for how the outreach should read. The unanswered ORA question set is the natural opening.

**Status:** reported, NOT corrected. The field edit needs Gabriel's instruction (identity-field backfill rule — see [[reference-property-llc-signature-roster]] context and the task's own guardrail that posture/clock fields are never edited while `Broker / Source` may be backfilled from a primary source on instruction, stamped with source and date).

**Root cause:** the 07-28 backfill searched too narrowly and read silence as absence — the exact failure mode of [[feedback_verified_null_vs_inferred_null]], reproduced by the task built to catch it in the tracker. Same run also proves the fix works: 808 Rhoads got the full surname-ladder treatment and its "no correspondence" verdict is a genuine verified null.

Related: [[deal-decision-ledger]] · [[feedback_self_flattering_error_bias]]

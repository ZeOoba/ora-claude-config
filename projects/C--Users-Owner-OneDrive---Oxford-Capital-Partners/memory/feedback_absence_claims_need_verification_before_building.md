---
name: feedback_absence_claims_need_verification_before_building
description: "A memory/report claim that a check or capability does NOT exist is a hypothesis, not a finding -- grep for it before building it; the usual truth is that it exists but is disconnected from the path that needed it."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2c9d524e-0310-4835-a558-f3218f031193
  modified: 2026-08-03T19:04:50.815Z
---

**What happened (2026-08-03, `ora-lease-snapshot-refresh`).** [[reference_parseleases_vacancy_block_phantom_leases_2026-08-03]] stated as a detector gap: *"Nothing ties parsed lease annual rent to the workbook's own Contractual annualized rent (total) at row 160."* I repeated that to Gabriel and recommended building the assertion — scoped as financial-decision code needing TDD plus a REFUTE pass.

It was wrong. The assertion existed **twice**: `server/reconcile-runtime.ts:60-64` (in-process, already unit-tested, comparing against `snapshot.workbookTotals.rent` which `parse.ts:472` already captures) and `scripts/reconcile.ts:71-76` (`npm run reconcile`, which failed on the exact defect the moment I ran it). Neither was called by the two CLI writers. The real defect was **wiring, not absence** — and the fix collapsed from "design a new financial assertion" to "add two call sites to an already-tested function."

**Why this class of error is worth its own rule.** An absence claim is unfalsifiable from the seat that writes it — the session that wrote the note had looked at the *write path*, found nothing, and generalized to "nothing anywhere." That reads identically to a verified global search. It then costs far more than a wrong presence claim: a wrong presence claim gets caught the moment you open the file, whereas a wrong absence claim routes you into building a duplicate, and duplicates of financial-integrity checks are exactly what [[reference_concurrent_session_duplicate_hardening_work]] and the 2026-07-26 anomaly-floor consolidation were fought over. Note the error direction: it flattered the finder by making the gap look bigger and the fix look more heroic — the tell in [[feedback_self_flattering_error_bias]].

**How to apply.** Before acting on any "nothing does X / no such check exists / this is unprotected" claim — in a memory file, a probe report, a subagent finding, or your own earlier turn:
1. Grep the repo for the capability by *concept*, not by the phrasing in the note — the field name, the constant, the tolerance, the message string. Here, one grep for `workbookRentTotal` would have settled it.
2. Check whether the thing exists but is **unreachable from the path in question** — a different caller, a gate that runs in `gate` but not `gate:ci`, a live-server-only code path, a test-only import. That is the common shape.
3. Only then treat it as absent. If it turns out to be disconnected rather than missing, correct the source note in place with the direction of the error stated — a bare fix leaves the next reader to re-run the same investigation.

Companion to [[feedback_recheck_before_reflagging_tooling_gaps]] (don't re-report a gap another session already closed) and [[feedback_verified_null_vs_inferred_null]] (a zero that could mean "couldn't look" is a failure). This one covers the build-side cost: an inferred null that sends you off to construct what is already there.

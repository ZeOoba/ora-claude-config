---
name: feedback_financial_code_upfront_load_derivation
description: "For financial or scaling-sensitive code fixes, do the load/bottleneck derivation and convergence/failure-mode analysis explicitly before writing the first line of code, not iteratively via adversarial review rounds"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6d6043de-39cf-419a-9eaf-ca0ef62a4091
  modified: 2026-08-16T20:04:31.789Z
---

Before implementing a fix to code that scales with a live dataset (per-lease/per-row loops, batch processing, external-API fan-out) or moves real money, do the `/build` skill's own "Small path" load/bottleneck derivation and a real failure-mode brainstorm as a genuine first step — write out the actual arithmetic (fixed cost + per-item cost × batch size vs. the real platform ceiling) and the convergence property any retry/drain loop needs to guarantee — before writing the implementation, not after a reviewer finds the gap.

**Why:** the ora-pm monthly-billing OI-162 fix (2026-08-16) took five adversarial-review rounds to reach a safe state. Each round found something real: round 1 fixed the demonstrated Cloudflare-subrequest-limit crash but relocated the same O(leases) shape into the autopay debit loop; round 2 bulk-fetched debit inputs but left the batch unbounded; round 3 added a drain loop with no consumer and lost its own error diagnostics; round 4 found a genuine deadlock (batch-limiting before computing which leases needed a debit let already-paid leases starve leases that actually owed money — reproduced empirically); round 5 found the same starvation *shape* recurring via deterministically-failing Stripe calls. Every round's fix was locally correct and passed its own tests, but each one only considered the specific failure mode the previous round had surfaced, not the general property ("every batch-selection step must guarantee forward progress regardless of what's in the batch"). That property, stated once, would have caught rounds 2, 4, and arguably 5 in a single pass.

**How to apply:** before implementing (not before shipping) a fix in this class:
1. Write the actual subrequest/query-count arithmetic against the real platform ceiling (verify the ceiling — don't assume a tier), including worst-case retry/failure costs, not just the happy path.
2. State the convergence property explicitly if there's any retry/drain/batch loop: "this must strictly decrease [X] every call, or stop and say so loudly" — then check every code path (including every failure branch) against that property, not just the main flow.
3. Name the failure modes a batch-selection or ordering decision could hide (e.g., "what happens if the same N items always sort into the batch and never leave it") before choosing how to select/limit a batch — starvation is a distinct bug class from the volume problem the fix was originally chasen to solve.
4. This doesn't replace adversarial review (`[[feedback_refute_pass_proactive_default]]`) — it front-loads the parts of it that are derivable by reasoning alone, so the review rounds spend their budget finding what reasoning alone missed, not re-deriving arithmetic that should have been done upfront.

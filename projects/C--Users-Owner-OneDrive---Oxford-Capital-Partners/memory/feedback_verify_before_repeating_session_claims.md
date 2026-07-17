---
name: feedback_verify_before_repeating_session_claims
description: "Standing habit, confirmed twice in one session (2026-07-17): before repeating another session's or source's status claim as fact, independently verify it against ground truth. Caught real staleness both times, not paranoia."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

**Rule:** before repeating a claim about system state that originated from another session, a
memory file's own self-description, or any second-hand source — "OI-007 is done," "the PR merged,"
"the guard is working correctly" — independently verify it against ground truth (git log/fetch,
a live query, reading the actual file) before stating it as fact, especially before summarizing it
to Gabriel. Do this even when the claim looks authoritative (a well-formatted tracker entry, a
confident commit message) and even when it would be faster to just relay it.

**Why:** confirmed twice in the same 2026-07-17 session, not a one-off:
1. Reported OI-007 as "Gabriel-ratified, not tonight's scope, nothing done" based on the tracker
   entry's own wording — then checked `event_log.md` and found the OTHER session had actually
   landed and verified the Gate 1 (email) half already, with the Gate 2a (netlify) half explicitly
   still open. The tracker's own self-description was stale relative to what had actually happened.
2. Minutes later, the tracker had been updated to claim BOTH gates were closed, citing a specific
   merged PR (`#30`, commit `b25a70d`) with specific file line counts. Rather than relay that as
   fact, ran `git fetch`/`git pull` on the actual `website-canonical` repo and confirmed the PR,
   commit, and files were real and substantive — they were, this time. But the verification step
   is what makes that a confirmed fact rather than a repeated claim; skipping it would have been
   right by luck, not by rigor.

**How to apply:** the check should be proportional to the claim's stakes and how easy verification
is — a `git fetch` + `git log` is cheap and was worth doing both times above. This generalizes the
existing narrower siblings below rather than replacing them; check those first if the claim fits
one of their specific shapes:
- [[feedback_verify_probe_findings_before_acting]] — a probe finding specifically (defect could be
  in the probe, not the flagged artifact)
- [[feedback_verify_registry_mutation_claims]] — a logged scheduled-task registry mutation
  specifically (cross-fleet calls can silently no-op)
- [[feedback_verify_subagent_safe_claims]] — a subagent's "safe to proceed" claim specifically
- [[feedback_verify_negative_glob_results]] — a "no files found" result specifically

This one is the general case: ANY status claim from a second-hand source, not just those four
specific shapes. When in doubt whether a claim needs re-verification, it does — the cost of
checking is almost always lower than the cost of confidently repeating something stale to Gabriel.

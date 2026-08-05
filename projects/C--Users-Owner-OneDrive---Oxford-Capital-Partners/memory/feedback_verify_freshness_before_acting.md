---
name: feedback_verify_freshness_before_acting
description: "On a concurrently-written checkout, state verified at DECISION time (a claim held, a HEAD ref, a push status) is not guaranteed current at EXECUTION time. Re-check immediately before the actual state-changing action, not just once when planning it. Confirmed three times in one session, 2026-08-05."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 98d8f05b-4827-4a96-bdc9-3466337e508c
  modified: 2026-08-05T22:10:40.821Z
---

**Rule:** on `~/.claude` or any shared-checkout repo, a fact about repository/claim state you verified
a few tool calls ago — "I hold the claim," "HEAD is X," "this commit is unpushed" — is a snapshot, not
a standing guarantee. Other sessions commit to these checkouts continuously and without warning. Before
any state-changing action (a commit, a claim, a rebase, a push, an `--only` pathspec commit), re-verify
the specific fact the action depends on **immediately before taking it**, even if the same fact was
already confirmed minutes earlier in the same turn.

**Why — three independent instances in one session (2026-08-05), not a one-off:**
1. **Claim collision.** Claimed `open-items-tracker.md`, edited it, released. Re-claimed later for a
   second edit — the tool warned another session (`5ac5b6c1`) held a *live* claim on the exact same file,
   mid-repair on a corrupted table. The claim I'd verified clean minutes earlier was stale by the time I
   acted again. Correctly stopped and re-verified their repair had actually landed before touching the
   file myself, rather than trusting the earlier read.
2. **HEAD moved mid-plan.** Gabriel approved rewording a commit's message on the explicit premise "it's
   unpushed, nothing sits on top of it." By the time the rewrite was attempted, another session's
   unrelated commit had landed on top of it — the target was no longer even HEAD. Re-checking
   `git log -1` immediately before acting caught this instead of an amend silently rewording the wrong
   commit.
3. **Push status changed underneath a decision.** Same turn: Gabriel approved pushing several local-only
   commits. By the time the push was attempted, `git fetch` showed every one of them was already on
   `origin/main` — a different session had pushed in the interval between the approval and the action.
   Attempting the originally-approved plan at that point would have meant force-pushing over history
   another session may have already fetched, a materially different and much riskier operation than the
   one that was actually approved.

**How to apply:** the check is cheap — `git status`, `git log -1`, `claim_work.py list`, `git fetch` +
`merge-base --is-ancestor` — and should run *at the point of action*, not be inferred from a check earlier
in the same turn. Treat "I already checked this" as true only for the instant it was checked. This applies
with the most force to anything a hard invariant or a "never without explicit confirmation" rule gates
(force-push, rebase, destructive git) — a plan approved against one risk profile does not carry forward
automatically once the facts underneath it have changed, even within the same turn, even after the same
user already said yes once.

**Related, different axis — verify-before-*acting* vs. verify-before-*relaying*:**
[[feedback_verify_before_repeating_session_claims]] is the sibling for status *claims* repeated to
Gabriel or written into a report; this file is for state a *state-changing action* is about to depend on.
Both reduce to "don't trust a stale read," applied at different moments.

**The specific git mechanism this bit hardest on today** (a symptom of not re-checking immediately
before the write) is already fully documented — see [[feedback_pathspec_commit_discards_index_splice]]
and [[reference_event_log_partial_commit_splice]]. That gotcha exists precisely because a pathspec-scoped
commit re-reads the working tree at the *moment of the commit*, not at the moment the index was staged —
the same freshness-at-action-time principle, one layer down in git's own plumbing.

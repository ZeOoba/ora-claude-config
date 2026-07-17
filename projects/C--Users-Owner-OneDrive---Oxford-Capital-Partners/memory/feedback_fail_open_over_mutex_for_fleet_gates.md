---
name: feedback-fail-open-over-mutex-for-fleet-gates
description: "Gabriel's ratified stance (2026-07-16, commit-provenance-guard design): reject a hard claim-lock/mutex for cross-session fleet coordination in favor of a fail-open gate needing TWO affirmative signals. Apply this default to any future concurrency-guard proposal."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

When asked to convert `shared-checkout-guard.py` into "a real claim-lock" (the literal initial
ask), I surfaced the tradeoff before building rather than just building it: a true lock needs
atomic claim storage + TTL-based stale-claim recovery + release-on-crash handling, and a crashed
session holding a claim can wedge every other session in the fleet. This repo already has one
fail-closed guard, `confidentiality-guard.py`, that has self-deadlocked the machine once — see
[[feedback_confidentiality_guard_selfdeadlock]]. Given the explicit choice via `AskUserQuestion`
("Fail open + TTL" vs. "Fail closed"), Gabriel chose **fail open + TTL** — an explicit rejection
of the mutex/lock shape for this class of problem, not an assumption on my part.

**How to apply:** the resulting pattern — block only on TWO independent affirmative signals (e.g.
"another session demonstrably touched this file" AND "liveness affirmatively reports that session
open, within a TTL") rather than treating absence-of-information as license to block — is now
built and live: `commit-provenance-guard.py`, see [[reference_commit_provenance_guard]]. Treat
this as the house default for the NEXT cross-session coordination guard proposed in this fleet:
default to fail-open + two-signal, and require an explicit, separately-argued case before
proposing a hard lock/mutex. The fleet runs 8-14+ concurrent sessions where a single wedged claim
is a fleet-wide outage, not a local one.

**Scope — this is not "always fail open."** [[feedback_destructive_git_deny_stays_hard]] is the
opposite-direction precedent: some things (force-push, reset --hard) stay categorically
hard-denied, no exceptions. This preference is specific to coordination/liveness gates between
concurrent sessions, where the failure mode of blocking is worse than the failure mode of an
occasional missed collision.

Related: [[reference_commit_provenance_guard]] · [[feedback_confidentiality_guard_selfdeadlock]] ·
[[feedback_destructive_git_deny_stays_hard]] · [[project_tenant_db_no_sync_rootcause]].

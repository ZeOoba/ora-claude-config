---
name: preexisting-failure-verify-against-push-target
description: "\"Pre-existing\" means present on the branch you are pushing TO, not merely present before your change. Verifying only the latter let a red typecheck be merged onto oxford-command-center's main on 2026-08-24."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2b6b4343-89ec-4a37-a0c3-912a30556587
  modified: 2026-08-24T16:37:16.197Z
---

When a gate step fails on work you did not write, the safe-to-proceed test is **not** "was this already failing before my change?" It is "is this already failing on the branch I am about to push to?"

Those differ exactly when local and remote have diverged — which on a shared checkout with many concurrent sessions is the normal case, not the edge case.

## What went wrong (2026-08-24)

Merging local `main` into `origin/main` in `oxford-command-center`, `npx tsc --noEmit` reported 4 errors in `tests/unit/prepush-confidential-scan.test.ts`. I checked them against the pre-merge local tree, saw them there too, called them "pre-existing on both sides," and pushed.

They were pre-existing on **local** main only. Old `origin/main` was clean — provably so: PR #293's CI gate had passed on that base an hour earlier. The push imported a red typecheck onto `main`, and every branch cut from main inherited it until PR #295 fixed it.

The commits carrying the defect (`ead629d`) had reached local `main` by direct commit, never through PR CI — which is precisely why the divergence hid a failure that upstream had never seen.

**Why:** "pre-existing" is a claim about a *baseline*, and I silently used the wrong baseline. Checking "was it failing before I touched it" answers a question about my own change; it says nothing about what the merge does to the target.

**How to apply:**
- Before pushing a merge, diff the failure against the **push target** explicitly: `git stash && git checkout origin/<target> -- . && <gate step>`, or simply check whether the target's own last CI run was green.
- A green CI run on the target branch is the cheapest possible proof. Look for it before dismissing any failure as inherited.
- State the baseline out loud when claiming pre-existence — "fails identically on `origin/main`" is verifiable; "pre-existing" alone is not.
- This is the same failure class as [[feedback-verified-null-vs-inferred-null]]: a result that could mean "I checked the wrong thing" must not be reported as "I checked."

Related: [[reference-vitest-green-is-not-a-typecheck-mjs-dmts-drift]] (the specific defect this let through) · [[feedback-command-center-gate-vs-gate-ci-divergence]] · [[feedback-verify-before-repeating-session-claims]]

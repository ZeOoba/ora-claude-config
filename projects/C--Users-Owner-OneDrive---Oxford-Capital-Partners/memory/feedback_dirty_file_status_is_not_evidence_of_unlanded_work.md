---
name: feedback_dirty_file_status_is_not_evidence_of_unlanded_work
description: "On a checkout far behind origin/main, a dirty file is often already-merged work, not unlanded WIP -- diff it against origin/main before treating it as risky"
metadata:
  node_type: memory
  type: feedback
---

On a shared checkout that is far behind its canonical branch, `git status` "modified" is **not** evidence that a file holds unlanded work. The working-tree content can already be byte-identical to `origin/main`: the session that wrote it landed the change upstream via a PR, and the file only reads as modified because the local HEAD is behind and still carries the *old* version. The local content matches the future, not the past.

Measured on `~/.claude` (2026-09-10, HEAD 84 commits behind `origin/main`, 23 merge-blocking dirty files):

- **6 of 23** were byte-identical to `origin/main` — already-merged work, safe to discard because the merge restores the same bytes.
- **7 of 23** were untracked files whose exact path `origin/main` now introduces — same situation.
- Only **10 of 23** were genuinely divergent unlanded WIP.

Two of the six were `hooks/eos-review-gate.py` and `hooks/eos-telemetry.py` — which by filename and `owner=None` looked like the most dangerous items in the entire backlog (unattributed edits to the review gate). They were the *safest*.

**Why:** `dirty-tree-triage` classifies by git status and attributes by provenance, and both are blind to this. Status compares the working tree to HEAD; when HEAD is stale, that comparison answers the wrong question. Attribution is also unreliable here — in the same pass, two files this session had edited itself were attributed to two long-dead sessions, because the provenance recorder carried an older touch and never recorded the current one. Attribution is good enough to *exonerate* a file (a live owner with corroborating activity) but not to *convict* one.

**How to apply:** before treating any dirty file as risky WIP, run `git diff --quiet origin/main -- <path>` (and for untracked files, check whether `origin/main` already introduces that path). Split the set into already-upstream (safe, lossless to discard) vs. genuinely divergent (needs a real decision) *before* spending judgment on ownership. It reclassified more than half the backlog here in one command.

Corollary: a merge-forward blocked by files owned by *currently live* sessions cannot be unblocked by any amount of triage — those files are untouchable by doctrine, so the merge is gated on those sessions finishing, not on cleanup effort. Recognize that early and stop pushing.

Related: [[feedback_shared_checkout_guard_session_attribution_unreliable]], [[feedback_verify_wip_settled_via_mtime]], [[feedback_git_index_is_shared_state]].

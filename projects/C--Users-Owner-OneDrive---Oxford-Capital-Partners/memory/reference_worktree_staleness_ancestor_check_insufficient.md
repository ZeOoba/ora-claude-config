---
name: reference-worktree-staleness-ancestor-check-insufficient
description: git merge-base --is-ancestor alone cannot detect a stale worktree/branch when its content landed on main via squash-merge or manual reapply under a new hash — verify via per-file blob-diff + diff direction instead.
metadata: 
  node_type: memory
  type: reference
  originSessionId: e3f980f6-f186-4928-ba79-212963641f99
  modified: 2026-07-25T18:18:26.980Z
---

`git merge-base --is-ancestor <branch-tip> main` reports "not an ancestor" whenever a branch's content reached `main` through anything other than a real fast-forward or merge commit — a squash-merge, a manual copy-and-recommit, or a rebase that re-authors hashes. That result is easy to misread as "this branch still holds unlanded work." It happened twice in one evening (2026-07-24/25), across two different repos, during worktree-cleanup sweeps:

- **`~/.claude` `feat/eos-review-gate`** — not an ancestor of `main`, but all three files it touched were byte-identical to `main`'s current content. `main` had absorbed the fix via a separate commit (`c53c69c`) timestamped one minute after the branch's last commit — a manual reapply, not a merge.
- **`oxford-command-center` `fix/lease-id-integrity`** — same pattern: not an ancestor, 11 of 12 changed files byte-identical to `main`. The one differing file (`scripts/lease-snapshot-drift-check.ts`) needed a DIRECTION check, not just a "differs" flag: the diff showed `main`'s copy was the *larger* one (it retained interfaces the branch's copy lacked) — proof `main` had moved past this branch, not the reverse. Confirmed stale and safe to delete.

**The decisive check has two parts, not one:**
1. Isolate the branch's own changes with a three-dot diff (`git diff main...HEAD --name-only`). A plain two-dot diff (`git diff main..HEAD`) conflates the branch's own edits with everything `main` gained independently since the fork point, and will show unrelated newer work on `main` as spurious "deletions" — misleading if the branch is many commits behind.
2. For each file in that list, blob-compare it directly against `main`'s current tip (`git diff --quiet main:<file> HEAD:<file>`). If every file is identical, the branch is stale regardless of what `is-ancestor` says. If some differ, check **which side is larger/newer** on those specific files — a file where `main`'s content is a superset of the branch's means `main` moved past the branch (stale), not that the branch holds something new.

Applying this same two-part check to a THIRD branch that same evening (`oxford-command-center` `fix/governor-ltv-toloansignal-guard`) gave the opposite, correct answer: 6 of 20 files genuinely differed, and the direction ran the other way — the branch's copy was the larger one, adding a real rate/LTV collision-detection feature `main` didn't have yet. That branch was correctly left alone rather than deleted.

**Rule of thumb:** never treat `is-ancestor: false` alone as proof of real unlanded work, and never treat "some files differ" alone as proof of live work either — a differing file can just as easily mean the *worktree* is behind. Both require the file-by-file blob-diff, and any differing file requires the directional check, before a worktree/branch is safe to delete.

Related: [[reference_stale_merge_head_poisons_graph]] (a sibling git-history-integrity gotcha — a different mechanism, same family of "history doesn't say what actually happened"), [[reference_concurrent_session_duplicate_hardening_work]] (the duplicate-work risk this check exists to catch before deleting the wrong thing).

---
name: project-config-corruption-recurrence-closed-2026-07-25
description: "CLOSED 2026-07-25: root-caused the recurring t <t@t.t> authorship + phantom wt-branch corruption in ~/.claude to a stale worktree missing the 337a7af/be82a87 GIT_DIR-leak fixes; fixed the one remaining vulnerable file (test-doctrine-integrity-probe.py) and pushed. OPEN: another session (worktree wt-branch-collision-fix) was found mid-fix on the same bug class in 3 different files"
metadata: 
  node_type: memory
  type: project
  modified: 2026-07-25T22:37:20.497Z
  originSessionId: 4d316a61-d6cb-4d65-8d29-9364a7647607
---

Gabriel's punch-list of 4 outstanding items (recurring corruption, 8b45f67 needing merge, bad authorship, settings.json guard idea) all traced to ONE root cause: the `amazing-lamarr-c659bb` worktree forked from `main` at `1fe2ae3`, before `337a7af`/`be82a87` (the GIT_DIR/GIT_WORK_TREE env-leak fixes across 8 test files) landed. Building `8b45f67` in that stale worktree re-ran the already-fixed leak, corrupting the worktree's own git identity to `t <t@t.t>` and — via `hooks/tests/test-memory-orphan-link-guard.py`'s worktree-resolution test (`git(rootM, "worktree", "add", "-b", "wt-branch", wt_dir, "HEAD")`) — registering a real `wt-branch` branch/worktree against the live repo. Verified via `git merge-base --is-ancestor` (both fixes: NOT ancestors of that branch). No 9th mystery file needed: `test-config-write-guard.py` (the earlier inconclusive live-catch) doesn't spin up a git repo at all, ruling it out definitively.

Found ONE genuinely still-open instance: `maintenance/test-doctrine-integrity-probe.py` had unguarded `git init`/`git -C <tmp> add` calls, and `8b45f67` was about to wire it into the blocking pre-push gate (17 newly-discovered maintenance/ test files). Reproduced with simulated GIT_DIR/GIT_WORK_TREE contamination (exit 128), fixed with the same 9-line guard as the other 8 files, verified clean both ways, full 50-file `hook-tests-gate` green. Merged + pushed as `c1f5601` (then `9db0d34` for the event-log entry).

`8b45f67` turned out already merged to main via GitHub PR #22 (`5f4c7b0`) by another party before this session got there — item 2 was already done, not by this session. Gabriel ruled: leave `337a7af`/`be82a87`'s `t <t@t.t>` authorship (and `5f4c7b0`'s "ZE OOBA" naming) uncorrected — fixing it needs a force-push, hard-denied in settings.json, on a private solo repo where it's cosmetic; and skip a settings.json guard against `git worktree add -b` — the vulnerable-file class is closed, a blanket rule risks false positives on legitimate worktree creation.

**OPEN — live collision, not yet reconciled:** by the time this session went to delete the phantom `wt-branch` worktree, it was already gone — another session had beaten it there and stood up `C:\Users\Owner\.claude\.claude\worktrees\wt-branch-collision-fix` (branch `worktree-wt-branch-collision-fix`, off `5f4c7b0`) with **uncommitted** in-progress edits to `hooks/tests/test-confidentiality-guard.py`, `test-git-prepush-scan.py`, and `test-memory-orphan-link-guard.py`. This session did not touch those 3 files. See [[reference_concurrent_session_duplicate_hardening_work]] — same failure mode as 2026-07-16 (two sessions building the same fix independently, found only by chance). Next session touching hook-test isolation should read that worktree's diff first — it may already be a better fix than anything documented here, or it may need merging/cleaning up if abandoned.

**Why:** confirms the "check for collisions before ad-hoc hook work" doctrine caught a real concurrent-edit risk this time, not just a hypothetical.

**How to apply:** before touching `hooks/tests/test-confidentiality-guard.py`, `test-git-prepush-scan.py`, or `test-memory-orphan-link-guard.py` again, run `git worktree list` and check whether `wt-branch-collision-fix` still exists / is still uncommitted / has since merged.

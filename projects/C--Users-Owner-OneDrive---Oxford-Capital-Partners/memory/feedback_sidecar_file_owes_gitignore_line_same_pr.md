---
name: feedback_sidecar_file_owes_gitignore_line_same_pr
description: "Any change that makes a script write a new sidecar next to a TRACKED file (lock, tmp, spool, backup) must add its .gitignore line in the same PR — and a rename of a sidecar must re-check the existing ignore pattern still matches"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 576ca272-a9be-4605-98e9-a57e981ec957
  modified: 2026-09-12T22:01:10.296Z
---

A PR that introduces or renames a runtime sidecar next to a git-tracked file (e.g. `event_log.md.lock`, `.tmp-append.<pid>.<ns>`, `.pending/`, `.inplace-backup`) owes the matching `.gitignore` line **in the same PR**. Renames count: an exact-name ignore rule silently stops matching when the sidecar gets a unique suffix.

**Why:** PR #172 (063fa61, 2026-09-07) added `event_log.md.lock` and renamed `.tmp-append` to `.tmp-append.<pid>.<ns>` with no `.gitignore` change. `memory-commit-sweep.py` then committed the lock (9ce0923) — correctly, since nothing ignored it. The three earlier sidecars each got their ignore line at birth; this was the first miss. `~/.claude/.gitignore` default-denies at root but OPTS IN `memory/` wholesale, so anything written inside memory/ is committable by default. Fixed in PR #191 (7bdd5ef).

**How to apply:**
- When writing/reviewing code that does `path + ".<suffix>"`, an f-string/format sibling name, or a spool dir next to a tracked file: grep `.gitignore` for that exact final on-disk name and confirm with `git check-ignore -v --no-index <path>` (a nonexistent path works; for a dir-only rule probe a file INSIDE the dir).
- For `append-event-log.py` this is now enforced: `hooks/tests/test-memory-sidecar-hygiene.py` derives sidecar names from the script's source and fails the pre-push gate on any unignored or tracked one. Other sidecar-writing scripts are NOT covered — extend the test's SCRIPT list or apply the check by hand.
- Fix the ignore rule, not the sweep: a sweep-level exclusion only protects one writer, while `git add -A` from any session bypasses it. Already-tracked files also need `git rm --cached`.

Related: [[reference_worktree_isolation_drops_gitignored_overlay_2026-09-05]] · [[feedback_absence_claims_need_verification_before_building]]

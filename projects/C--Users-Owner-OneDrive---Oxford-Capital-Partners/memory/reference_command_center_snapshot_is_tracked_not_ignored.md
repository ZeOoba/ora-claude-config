---
name: reference_command_center_snapshot_is_tracked_not_ignored
description: "SUPERSEDED 2026-11-12: oxford-command-center's data/snapshots/portfolio.json is now GITIGNORED (PR #565) and never committed; the snapshot-refresh tasks write it in place. It was tracked 2026-07-27 to 2026-11-12."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d935c53e-d25d-4d65-ba47-f27485998667
  modified: 2026-11-12T23:30:00.000Z
---

**Current (since 2026-11-12, oxford-command-center PR #565, squash `0211bb77`):** `C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json` is **gitignored and untracked**, like every other real-data file in `scripts/fixtures/real-data-manifest.json` (all of `data/` is in its `neverTrack` list). The public repo ships synthetic stand-ins under `fixtures/synthetic/`; real files exist only in the live checkout. Verify: `git ls-files --error-unmatch data/snapshots/portfolio.json` exits non-zero and `git check-ignore -q` exits 0.

**Writers now:** `ora-lease-snapshot-refresh` and `ora-cc-snapshot-refresh` v2.0 refresh it **in place** in the live checkout and never commit (pre-run backup in `data/snapshots/_prev/`, guards in `~/.claude/scheduled-tasks/_shared/snapshot-guard.py`, restore on refusal); the Brain Server persists it; `ora-ar-feed-sweep` patches it Mondays. Freshness is probed by age (`cross-repo-wip-scan.py`, stale above 96h), not against `origin/main`.

**How to apply:** never `git add` this file or any copy of it (the pre-push scan and `npm run governance` fail closed on it); a pull or checkout that crosses #565 deletes it from a working tree, so follow `docs/ops/2026-11-11-real-data-untrack-pull-runbook.md`. Any memory or spec that says it is tracked or auto-committed is pre-#565 history.

**History:** tracked from `b53c93c` (2026-07-27) to #565; during that window bad extracts were committed unattended as `Auto-refresh:` commits, which is why guards were layered on (see [[reference_parseleases_vacancy_block_phantom_leases_2026-08-03]]). Related: [[reference-snapshot-tasks-share-one-file-diff-absorption]], [[feedback_git_index_is_shared_state]].

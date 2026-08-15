---
name: reference-oi140-check-open-items-duplicate-ids-cli-fix-2026-08-13
description: OI-140 fixed (maintenance/check-open-items-duplicate-ids.py now rejects unexpected CLI args instead of silently checking the canonical tracker); the *_OVERRIDE-seam hazard does NOT generalize to the other 3 probes that share the pattern
metadata: 
  node_type: memory
  type: reference
  originSessionId: b34ec269-3c65-4bc6-ba23-039298513853
  modified: 2026-08-13T04:32:21.384Z
---

[OI-140](open-items-tracker.md#OI-140) is fixed: `maintenance/check-open-items-duplicate-ids.py` previously accepted-and-silently-discarded any CLI argument (no `argparse`/`sys.argv` handling at all — `main()` always read `TRACKER_PATH_OVERRIDE` or the canonical tracker regardless of what was passed on the command line), so `check-open-items-duplicate-ids.py <any-path>` gave a verdict about the canonical tracker while looking like it checked the named path. Fixed with the tracker's own smallest recommended candidate: `main()` now rejects any `sys.argv[1:]` with exit code 2 and a message pointing at `TRACKER_PATH_OVERRIDE`'s real scope (module-attribute test seam only) and at `open-items-tracker.md#OI-140`.

**Checked whether the hazard generalizes (it doesn't).** Three other files share the same `*_OVERRIDE = None` test-seam pattern: `hooks/git-prepush-hook-tests-gate.py`, `hooks/git-prepush-doctrine-gate.py`, `maintenance/cross-repo-wip-scan.py`. None of them has `argparse` or `sys.argv` at all — they were never designed to take a CLI path argument in the first place (they're pure hook/gate entry points invoked with zero arguments), so there's no "looks like it worked, silently didn't" gap to close. Don't re-open this as a sweep across those three; it was checked and doesn't apply.

**Status as of 2026-08-13:** the fix is applied in the live `~/.claude` checkout's working tree but NOT YET COMMITTED — the checkout had 4 other files staged by a concurrent session (`_assert_no_other_staged_changes`-class contention) at write time, and per [[feedback_polling_claim_loop_default]] this should be committed via `hooks/lib/isolated_commit.py` (or its new `commit_isolated_replacement` wrapper once merged, see [[reference_isolated_commit_repair_wrapper_2026-08-13]]) once that contention clears, not swept up in an unrelated broad commit. Verified working via manual test run (`python maintenance/check-open-items-duplicate-ids.py badarg` → exit 2, correct rejection message) and the file's own test suite (30/31 passing — the one failure is [[reference_check_open_items_duplicate_ids_live_state_gate]]-class live-tracker-data flakiness, unrelated to this change: an `ORPHANED_SECTION` finding on the canonical tracker's current real content, not a regression).

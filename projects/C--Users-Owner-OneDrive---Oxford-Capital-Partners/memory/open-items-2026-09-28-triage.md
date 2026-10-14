---
name: open-items-2026-09-28-triage
description: Eight open items OI-357..OI-364 from the 2026-09-28 PR #284 merge gate and dirty-tree triage, filed in a standalone file because open-items-tracker.md was held by live session 07f5c5ca; NOT yet in the tracker
metadata:
  type: reference
---

# Open items OI-357 to OI-364 (filed 2026-09-28, standalone)

**Not yet in `open-items-tracker.md`.** The tracker was CONTESTED by live session `07f5c5ca` (preflight, 2026-09-28 20:34) so these were filed here instead. To merge: when `python maintenance/preflight-shared-checkout.py --repo C:/Users/Owner/.claude --paths projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md --since <sha>` returns 0, copy each `Row:` line into the tracker table (newest first) and each `### OI-NNN` section after it, then delete this file. Ids were reserved through `maintenance/allocate-oi-id.py` (session 372c45f9), so they will not be reissued. Sources: adversarial-merge-gate on PR #284 (closed; pinned head 9329f26, six reviewers), the independent review of PR #285, and the dirty-tree triage. Every finding was reproduced by a command.

Row: | [OI-357](#OI-357) | 2026-09-28 | PR #284 merge gate, races reviewer (already on `main` a82e043, not a regression of the PR) | **OPEN — HIGH.** `scheduled-tasks/_shared/block-sentinel.py` treats a Windows `PermissionError` (Errno 13) on its lock file or state file as "proceed": a COMPLETE block runs again (duplicate email/side effect) and the write-back erases every other block's record. |

### OI-357
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** adversarial-merge-gate races reviewer on PR #284 (`g2/race3.py`), code on `main` a82e043 lines ~331 and ~359.
**Severity:** HIGH (double-fire guard fails open on the exact platform it runs on; corrupts the shared state file).
**Description:** Mechanism 1: on Windows `os.open(O_CREAT|O_EXCL)` on a lock file mid-deletion raises Errno 13, not "exists"; `_Lock.__enter__` takes the `except OSError` branch ("lock unavailable") and proceeds unlocked instead of retrying. Mechanism 2: `load_state` treats Errno 13 on read (another writer's `os.replace`, or OneDrive holding the file) as an empty state ("failing open"), then the claim writes back only its own record. Reproduction 1: `python race3.py 30 16` (16 distinct-block claims + 4 on one block, concurrent) — trial 27 lost 16 records, another PROCEEDed twice. Reproduction 2 (deterministic): three blocks COMPLETE, a PowerShell handle opened with sharing None for 1.2s, then `claim --block blockA` → PROCEED, state afterward holds only `blockA` IN_PROGRESS; blockB/blockC COMPLETE records erased.
**Candidate fix (NOT applied):** retry on `PermissionError` in `_Lock` the same way it retries "exists"; retry Errno 13 in `load_state` like `save_state` does; never `save_state` after a read error on a file that exists (emit PROCEED unpersisted or STAND_DOWN). Add a test using the handle-hold interleaving.
**Auto-check:** none.
**Related:** PR #285 (sentinel `--slot-times`, which does not touch these lines).

---
Row: | [OI-358](#OI-358) | 2026-09-28 | PR #285 independent review + PR #284 blast-radius mapper | **OPEN — MEDIUM.** The cold-start guard can hold the send script for about 135s; callers with a 120s Bash-tool timeout can be killed mid-wait, and no test exercises the new path (all `-WhatIf`). |

### OI-358
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** independent reviewer note on PR #285 (untested caveat) and blast-radius mapper F1/F2 on PR #284.
**Severity:** MEDIUM.
**Description:** `Ensure-OutlookReady` waits up to 120s (measured overshoot about 12s, so about 135s) before the 15s send. `maintenance/headless/ora_headless_lib.py:199-205` allows 180s per attempt (fits); any task agent calling the script through a Bash tool with the default 120s timeout would be killed during a cold start, where before it got exit 4 at about 15s. `test-send-via-outlook.ps1` covers only `-WhatIf`, which exits at :403 before the new code, so the guard is UNCOVERED. Separate fragility: `test-send-via-outlook.ps1` case "bare empty-string attachment" fails from a long checkout path because PowerShell wraps the error text mid-phrase ("Missing an" / "argument"), so the `*Missing an argument for parameter*Attachment*` match misses (21/21 from a short path, 20/21 from `.claude/.claude/worktrees/slim-landing`). Also `rules.md` §2 and `CLAUDE.md` describe exit 4 as "retry once"; that stays correct only while the script does not retry internally (it does not, after PR #285).
**Candidate fix (NOT applied):** shrink the wait to about 90s (fresh independent review required: send path is blast radius); add a mock-based test for the cold-start branch; make the empty-attachment assertion whitespace-insensitive.
**Auto-check:** none.
**Related:** PR #285.

---
Row: | [OI-359](#OI-359) | 2026-09-28 | PR #284 merge gate (scope, guards) + four pushes this session | **OPEN — HIGH/MEDIUM.** Three defects in the pre-push gate: the confidential/credential scan cannot see inside archives, Office files or UTF-16 text; `test-governor-drift-probe.py` false-positives on positivity guards and blocks every push; the tests-gate reads the shared working tree. |

### OI-359
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** scope reviewer F1, guards reviewer F1, and the blocked pushes of `chore/reattach-primary-checkout-2026-09-28` (four overrides needed).
**Severity:** HIGH (1), MEDIUM (2, 3).
**Description:** (1) `hooks/git-prepush-confidential-scan.py` scans `git log -p` text; binary files appear as one "Binary files differ" line. A 31.6 MB `maintenance/_state/r27-baseline/claude-dirty-snapshot.tgz` holding memory files (people.md, deal-decision-ledger.md, deal_1100_rarig_disposition, event_log.md) reached the remote unscanned; also 16 UTF-16 task XMLs and 3 .docx. Checked against the roster afterward: 0 active terms, 15 hits for the declassified E. Fulton block. (2) `test-governor-drift-probe.py` flags `oxford-command-center/server/warehouse/capital-config.ts:198/201` (`next.ltvCeiling > 0`, `next.dscrFloor > 0`) as "LTV ceiling constant 0 != 0.4" and "inverted floor". They are finiteness guards; the real enforcement is lines 189/192 against `RATIFIED_GOVERNORS` (`src/contracts/governor-constants.ts:15-17`, 1.25 and 0.40). The probe fails twice per push and blocks it. (3) `hook-tests-gate` tests the shared working tree, so another session's uncommitted edit (orphaned OI-354/355 sections) failed `test_check_open_items_duplicate_ids.py` for an unrelated push (same class as OI-328).
**Candidate fix (NOT applied):** (1) expand .gz/.tgz/zip/Office and decode UTF-16 before scanning, or fail closed on binary files under `maintenance/_state` and `maintenance/_archive`; gitignore `maintenance/_state/**/*.tgz`. (2) teach the probe to accept `> 0` / `Number.isFinite` guards when the same function compares against `RATIFIED_GOVERNORS`. (3) run the tests-gate from a clean export of the pushed ref (see OI-328).
**Auto-check:** none.
**Related:** OI-328, PR #284 (closed), PR #285.

---
Row: | [OI-360](#OI-360) | 2026-09-28 | PR #284 merge gate, correctness + guards reviewers | **OPEN — MEDIUM.** `maintenance/audit-log-sweep.py` overwrites an earlier archive of the same session path and archives gzipped session audit logs into a git-tracked, unignored folder the pre-push scanner cannot read. The task and script are still untracked in the live checkout. |

### OI-360
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** correctness F1 and guards F2 on PR #284; held out of PR #285.
**Severity:** MEDIUM.
**Description:** `_archive_one` (lines 86-89) writes `archive_root/<rel>.gz` with `gzip.open(dest,"wb")`; a second archive of the same path destroys the first, then deletes the second original (`FIRST-GENERATION` lost in the repro, zero errors reported; breaks invariant 6). `ARCHIVE_ROOT` is `maintenance/_archive/session-audit-logs/` inside `~/.claude`, `git check-ignore` says NOT IGNORED, so the next land-the-dirty-tree pass commits about 102 MB of per-session tool-call trails, and a sandbox commit containing a fake `ghp_` token in the gzip passed `scan_diff` with `[]` (plaintext control was flagged). `--since-days 0` or negative makes a seconds-old file eligible, bypassing the only liveness gate.
**Candidate fix (NOT applied):** unique suffix (mtime) or open mode `"xb"` with a collision error; move `ARCHIVE_ROOT` outside the repo or gitignore it; argparse minimum 1 for `--since-days`. Then land `scheduled-tasks/ora-audit-log-sweep/` and the script with the run-guard entry (currently removed from the backlog list because the spec is untracked-and-held).
**Auto-check:** none.
**Related:** OI-359.

---
Row: | [OI-361](#OI-361) | 2026-09-28 | PR #284 merge gate, correctness reviewer | **OPEN — MEDIUM/LOW.** `parcel-screen-fanout.js` accepts a string `neverCallNames` and screens nothing; `loan_balance_check.py` exits 1 where exit 2 is documented and has no zero floor on expected balance; the .mjs and .py guard evidence differ by timestamp rounding. All landed in PR #285 as-is. |

### OI-361
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** correctness reviewer F2-F4 on PR #284.
**Severity:** MEDIUM (fanout guard), LOW (rest).
**Description:** (1) `skills/county-parcel-screen/workflows/parcel-screen-fanout.js:84-94,230`: the fail-loud guard checks only `.length` (and `.every` when length <= 2), so `neverCallNames:'ACME'` passes, line 230 spreads it into single characters, line 118 requires `norm(n).length >= 3`, so no counterparty ever matches (repro: array form hits "counterparty", string form hits null). The header usage (lines 14-18) still describes forms that now always throw. (2) `maintenance/loan_balance_check.py:92,105,170`: non-numeric Notion balance raises `TypeError` and appraisal value 0 raises `ZeroDivisionError`, exit 1 where SKILL.md Step 2 handles exit 2; `anchor_amortizing` has no floor (principal 1000, payment 300, rate 0 → -1,400.00 expected). (3) `test-pipeline-match.mjs:38-43` claims byte-for-byte parity with `institutional_owners.guard_evidence()`; Node's `mtime` rounds to ms while Python truncates (mtimeNs ...898828900 → .899Z vs .898Z), and a relative `ORA_PIPELINE_GUARD` path prints raw vs abspath.
**Candidate fix (NOT applied):** (1) throw unless `Array.isArray(cfg.neverCallNames) && every(typeof n==='string' && norm(n).length>=3)`; (2) catch `TypeError`/`ZeroDivisionError` (or validate) and clamp expected balance at 0; (3) `statSync(f,{bigint:true}).mtimeNs / 1000000n` and `path.resolve(GUARD_FILE)`.
**Auto-check:** none.
**Related:** OI-362 (test gaps on the same scripts).

---
Row: | [OI-362](#OI-362) | 2026-09-28 | PR #284 merge gate, test-validity reviewer | **OPEN — MEDIUM.** Tests that pass under deliberate mutation: the run-guard hand-verified ordering entry is membership-only, one sentinel midnight test cannot catch the bug it is named for, the slot-times cycle test depends on the wall clock, and the loan-balance tests read a gitignored live fixture and let two mutants survive. |

### OI-362
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** test-validity reviewer F1-F6 on PR #284 (mutations on copies, `g3/`).
**Severity:** MEDIUM.
**Description:** (1) `maintenance/_tests/test_scheduled_task_run_guard.py` (`ORDERING_VERIFIED_BY_HAND`, check at :486-490) is only a membership test: moving the claim line after the send line in a copy of `ora-loan-balance-check/SKILL.md` still exits 0 (evidence string is never compared to the file). (2) Slot-times path (:569-606) runs real-clock claims; a boundary (09:35/12:35/15:35/18:35/21:35 ET) or midnight between the two fires makes fire #2 PROCEED (repro with a pinned-clock shim → FAIL). (3) `scheduled-tasks/_shared/test-block-sentinel.py:645-660` (`test_claim_slot_times_single_instant_near_midnight`): mutant B5 (`period_key(period)` reads the clock twice) survives; with an advancing clock the mutant returns etDate 2026-09-25 vs original 2026-09-24. (4) `maintenance/_tests/test_loan_balance_check.py:11` loads gitignored `~/.claude/data/loan-terms.json` (fails with an empty USERPROFILE). (5) Surviving mutants L3 (tolerance `> 0`), L4 (`hit - full` not ORA share), L6 (maturity mismatch check off), L7 (`MATURITY_HORIZON_DAYS = 0`), L10 (unmodeled-records note removed).
**Candidate fix (NOT applied):** (1) also assert `min(claim_lines) < first_side_effect(lines)` (holds for 10 of 11 listed tasks; `ora-passed-deal-tracker` needs an explicit exemption); (2) capture one `ORA_SENTINEL_NOW` for all calls; (3) patch `_utc_now` with an advancing iterator; (4) commit a frozen fixture under `maintenance/_tests/fixtures/`; (5) add a +$3 (must not flag) and +$6 (must flag) diff, and a Red Branch row with a Notion balance equal to its ORA share.
**Auto-check:** none.
**Related:** OI-361.

---
Row: | [OI-363](#OI-363) | 2026-09-28 | PR #285 (run-guard backlog) + PR #284 guards reviewer | **OPEN — MEDIUM.** Eight side-effecting scheduled tasks are on the run-guard backlog with no double-fire guard, and the LoopNet sync's "never merge / never push to main" rule (Invariant 2 territory) is enforced only by its own spec text. |

### OI-363
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** PR #285 `UNGUARDED_BACKLOG` additions; guards reviewer notes on PR #284.
**Severity:** MEDIUM.
**Description:** Backlogged 2026-09-28 (waiver, not a fix): `ora-hubspot-renewal-closeout-tasks` (HubSpot task creation; known search-then-create race; nearest peers `ora-renewal-hubspot-reconcile` and `ora-tenant-hubspot-reconciliation` carry a block-sentinel claim), `ora-incentive-registry-refresh` (email; also rewrites `incentive-registry.json` after long web research while supervised sessions edit it — unreported as a race, no executed proof), `ora-jackson-boe-prep-reminder`, `ora-loopnet-listings-sync` (git push), `ora-noi-opportunity-digest`, `ora-recovery-billing-monthly`, `ora-recovery-structure-audit-annual`, `ora-wicomico-reassessment-reminder`. With the eight entries removed, the ratchet reports 8 failures (6 email tasks, 1 HubSpot write, 1 git push); a ninth, `ora-audit-log-sweep` (email), belongs to OI-360. No PreToolUse hook covers `manage_crm_objects`. `check_bash` in `ora-autonomy-gate.py` returns ALLOW for `git push origin HEAD:main` run from inside website-canonical and for `gh pr merge 12 --repo ZeOoba/Website --squash`; `destructive-git-guard.classify("push", …)` returns None; the settings deny list holds only `git push --force*`. Whether a push to Website `main` triggers a Netlify production build was not verified (config outside the pinned worktree).
**Candidate fix (NOT applied):** adopt the block-sentinel claim per task (README-DOUBLE-FIRE-GUARD.md; adoption is proven per task, not en masse), removing each name from `UNGUARDED_BACKLOG` in the same change (ratchet); add a hook rule blocking pushes to `main` and `gh pr merge` from the LoopNet task's context, or verify the Netlify auto-publish setting.
**Auto-check:** `python maintenance/_tests/test_scheduled_task_run_guard.py` (passes only while the waiver stands).
**Related:** PR #285, OI-360.

---
Row: | [OI-364](#OI-364) | 2026-09-28 | Dirty-tree triage close-out | **OPEN — LOW-MEDIUM (Gabriel action).** The closed PR #284's hidden ref still holds a 31.6 MB tarball with memory files; per-run `_state` files and other runtime paths are not gitignored (they would pin the merge-forward corrector if ever tracked); the primary `~/.claude` checkout is still on `chore/reattach-primary-checkout-2026-09-28`. |

### OI-364
**Status:** OPEN
**Opened:** 2026-09-28 · **Source:** 2026-09-28 dirty-tree triage close-out.
**Severity:** LOW-MEDIUM.
**Description:** (1) Deleting the `chore/reattach-primary-checkout-2026-09-28` remote branch and closing PR #284 does not purge `refs/pull/284/head`; commit baf9ea8 (`maintenance/_state/r27-baseline/claude-dirty-snapshot.tgz`, 61 memory/pending-task entries incl. 43 files naming the declassified E. Fulton deal) stays reachable in the private `ora-claude-config` repo until a GitHub support purge. (2) Untracked in the live checkout and deliberately NOT landed: `skills/synced/` (417 files, a platform-sync cache; `README.md:96` on main says synced skills are not tracked), per-run `_state` files (`checkout-merge-forward-last-run.json`, `audit-log-sweep-history.jsonl`, `headless-findings/`, `ground-truth/`, `fleet-pause-windows.json`, `hubspot-closeout-log.jsonl`, `handoffs/`, `task-xml-backup-*`). Reproduced: a tracked `checkout-merge-forward-last-run.json` makes every corrector run return `BLOCKED_DIRTY_OVERLAP` on its own state file (streak alarm each run). Unmerged branch `chore/ignore-closeout-runtime-log` already ignores most of these. (3) RESOLVED 2026-09-28 (Gabriel-directed): the primary checkout was moved off the recovery branch with `git reset --mixed origin/main` (working tree untouched; 478 branch-only files hash-verified identical) and the branch renamed `live/primary-checkout`, tracking `origin/main`. `main` itself stays pinned to the `main-checkout` worktree (daily `deadman: fleet-heartbeat` commits, ahead of origin). No ref or worktree HEAD reaches the tarball commit `baf9ea8` any more; it survives only in the local reflog (old tip `dc3fecf`). Side effect to expect: once PR #285 merges, its 38 files overlap untracked copies in this checkout and the merge-forward corrector returns `BLOCKED_DIRTY_OVERLAP` until they are moved aside (`maintenance/merge-forward-unblock.py`).
**Candidate fix (NOT applied):** open a GitHub support ticket for the purge (or ask if the residual risk is acceptable for a private repo with no active confidential terms); land or coordinate `chore/ignore-closeout-runtime-log`; decide the primary checkout's steady-state branch and delete the recovery branch.
**Auto-check:** none.
**Related:** OI-359, PR #284 (closed).

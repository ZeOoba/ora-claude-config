---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-07-25T00:59:46.598Z
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-07-26 — CLAUDE.md Autonomy doctrine amended: taxonomy tags + task-hygiene pass on close-out

Evaluated a generic `/wrap-up` skill prompt against ORA's actual setup. Most of it (auto-commit/push to main, auto-deploy, auto-file-move in OneDrive folders, auto-apply-and-commit findings) was rejected as violating Invariant 2/5/6 and the standing never-auto-commit-unless-asked rule. Two reporting-only pieces were kept and merged into CLAUDE.md's Autonomy section (line 61): the end-of-session ≤5-bullet workflow-optimization close-out now tags each finding as skill gap · friction · knowledge · automation, and is followed by a reporting-only task-hygiene pass (mark resolved open items done, flag orphaned/stale ones — no auto-apply). Gabriel confirmed the edit in-turn; landed via the `allow-config-write` override token (config-write-guard), since CLAUDE.md itself was clean (not part of the concurrent-session dirty set in the shared `.claude` checkout at edit time).

## Stale-worktree exposure check after wt-branch-collision-fix merge (2026-07-25)

After merging/pushing the wt-branch collision fix (`f0bf1b2`, merging `1172cec`), checked all
active session worktrees for whether they still carry the old vulnerable copies of
test-memory-orphan-link-guard.py / test-confidentiality-guard.py / test-git-prepush-scan.py.

**All 5 active worktrees + fix/telemetry-rollup-cohort-segmentation are stale and still
vulnerable**: `amazing-lamarr-c659bb` and `blissful-nash-783df1` (8 commits behind main, have
the sibling `c1f5601` test-doctrine-integrity-probe.py fix but not this one); `goofy-hopper-44e430`
(7 behind), `gracious-pascal-8cbe91` (15 behind), `relaxed-goldberg-98b9d3` (10 behind) -- these
three predate BOTH fixes (`337a7af`/`be82a87` GIT_DIR-leak AND `c1f5601`), so they're exposed to
the original leak too, not just the branch-naming issue. `amazing-lamarr-c659bb` is the exact
worktree already implicated in re-triggering this corruption once (see the prior entry above).

Did not touch any of these worktrees (single-writer caution, [[reference_concurrent_session_duplicate_hardening_work]]).

**Why:** a stale worktree running its own pre-push hook chain can still corrupt the real repo's
git state even though main is now fully patched -- the fix only protects code that has actually
been pulled into the worktree running it.

**How to apply:** before starting hooks/tests/ work in any of these 5 worktrees (or any other
worktree older than `f0bf1b2`), rebase/merge main first. If one of them pushes without doing so
and the hook-tests-gate runs test-memory-orphan-link-guard.py's worktree-resolution case, treat
any resulting `wt-branch` collision or stray ref in ~/.claude's .git as this same root cause, not
a new bug.

## Corruption-recurrence root cause closed; concurrent-session collision found mid-fix (2026-07-25)

Root-caused the "corruption still recurring" report (t <t@t.t> authorship + phantom `wt-branch` worktree): `amazing-lamarr-c659bb` forked from main at `1fe2ae3`, before `337a7af`/`be82a87` (the GIT_DIR/GIT_WORK_TREE env-leak fixes) landed — so its copies of those 8 test files never got the guard. Building `8b45f67` in that stale worktree re-triggered the already-fixed leak, corrupting the worktree's own git identity and, via `test-memory-orphan-link-guard.py`'s worktree-resolution case, registering a real `wt-branch` branch/worktree against the live repo. No new/undiscovered vulnerable file was needed to explain it — confirmed `test-config-write-guard.py` (an earlier inconclusive catch) doesn't spin up a real git repo at all, ruling it out.

Found one genuinely still-open instance of the same class: `maintenance/test-doctrine-integrity-probe.py`'s `git init`/`git -C <tmp> add` calls had no env-clearing guard, and `8b45f67` was about to wire it into the blocking pre-push gate. Reproduced (contaminated GIT_DIR/GIT_WORK_TREE -> exit 128), fixed with the same guard pattern as the other 8 files, verified clean under both conditions, full 50-file hook-tests-gate green. Merged to main and pushed: `c1f5601`.

`8b45f67` itself turned out already merged to main via PR #22 (`5f4c7b0`, author "ZE OOBA <ggoldberg@oxfordra.net>") by the time this session checked — not by this session. Per Gabriel's ruling, left the `t <t@t.t>` authorship on `337a7af`/`be82a87` (and the "ZE OOBA" naming on `5f4c7b0`) uncorrected: fixing it needs a force-push, which is hard-denied in settings.json, on a private solo backup repo where it's cosmetic-only. Also per Gabriel's ruling, skipped adding a settings.json guard against `git worktree add -b` — the vulnerable-file class is now closed, and a blanket rule risks false-positives on legitimate worktree creation.

**Collision found while cleaning up:** by the time the phantom `wt-branch` worktree/branch needed removing, ANOTHER session had already deleted it and stood up its own worktree `C:\Users\Owner\.claude\.claude\worktrees\wt-branch-collision-fix` (branch `worktree-wt-branch-collision-fix`, off `5f4c7b0`) with **uncommitted** edits in progress to `hooks/tests/test-confidentiality-guard.py`, `test-git-prepush-scan.py`, and `test-memory-orphan-link-guard.py` — the same bug class, likely hardening the worktree-add fixture pattern itself. This session did NOT touch those 3 files (only `test-doctrine-integrity-probe.py`, untouched by the other session). Per [[reference_concurrent_session_duplicate_hardening_work]], flagging here rather than guessing at or duplicating that in-progress work — whoever picks this up next should read that worktree's diff before touching the same 3 files.

**Why:** recurring "corruption" reports without a session-collision check risk chasing a phantom 9th bug or duplicating a fix another session is already mid-way through.

**How to apply:** if `test-confidentiality-guard.py`/`test-git-prepush-scan.py`/`test-memory-orphan-link-guard.py` need the same env-leak/isolation treatment again, check `wt-branch-collision-fix`'s worktree diff and whether it merged before starting fresh.

## 2026-07-25 â€” Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `ef02eb35-61f8-4ac2-beb4-f2aa0c774bc6` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel confirmed in-turn ("open the pr now") after two rounds of diagnosis showing all failures are pre-existing hooks/tests/ files unrelated to this diff, root-caused to a GIT_DIR/GIT_WORK_TREE env-leak in run_test_file() (subprocess.run has no env= override) that only manifests under a real git pre-push hook invocation, not under standalone runs. Not caused by or related to the two files this diff touches.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-07-25 17:03:27 local.

## 2026-07-25 — Shared-checkout investigation: wrong-file edit found and corrected, orphaned skill-mirror tree discovered (OI-025)
Investigating the dirty-`~/.claude`-checkout flag raised at the end of the prior turn surfaced a real defect: this session's earlier HubSpot-idle-flag and tracker-output changes to `ora-tenant-hubspot-reconciliation` had been applied to `Claude_Workspace\00_Governance\Scheduled\ora-tenant-hubspot-reconciliation\SKILL.md`, which `list_scheduled_tasks` confirms is NOT the registered path (`~\.claude\scheduled-tasks\ora-tenant-hubspot-reconciliation\SKILL.md` is canonical) — the edit had no effect. Also found a separate, already-live, uncommitted edit on the canonical file (from an earlier session that day, ~11:19 AM) adding a DATE-MISMATCH check (HubSpot closedate vs. `oxford-command-center`'s `portfolio.json` leaseEnd) for the Stone Crest/Chesapeake/J&R lease-date drift, and a third session's ~2:10 PM edit to `open-items-tracker.md` OI-021 that had already triaged the original "~49 stuck HubSpot deals" down to 8 real items (7 resolved) and flagged the remaining ~37 as a policy gap — the same finding this session's punch-list had surfaced independently.
Re-verified no further changes to the canonical file/tracker since discovery, then merged the IDLE category (re-lettered to 3e to avoid colliding with the other session's 3d) and the tracker-output redirect into the canonical file on top of the other session's DATE-MISMATCH work, preserving it. Archived the orphaned Claude_Workspace mirror folder to `_archive_2026-07-25_orphans\` in place (moved, not deleted).
Discovered in passing: `Claude_Workspace\00_Governance\Scheduled\` holds 100+ scheduled-task folders of unverified live/dead status, including apparent name-collisions with live CC tasks. Logged as `open-items-tracker.md#OI-025` rather than audited in full — out of scope for this pass.
No git commit made — the `~/.claude` checkout still has multiple sessions' uncommitted work; left for reconciliation rather than a blanket commit.

## 2026-07-25 — Systematization punch-list actioned (4 items)
Gabriel ruled on the session's "worth systematizing (≤5)" list via AskUserQuestion:
1. **Master workbook single-writer protocol** — RATIFIED as the recommended package (new `_active_sessions` sheet claim marker, documented-convention enforcement, scoped to the 4 highest-blast-radius sheets: Rent Roll, External Loans Summary, Property NOI, Portfolio Summary). Canonical text moved from the proposal file into `tech.md` §3d; proposal file marked RATIFIED and cross-links there. See `project_master_workbook_single_writer_proposal_2026-07-25.md`.
2. **HubSpot renewal-deal idle-stage flag** — Gabriel set flag-only, 6-month lease-expiration / 30-day-idle threshold. Added as category (d) IDLE to `ora-tenant-hubspot-reconciliation` SKILL.md (Claude_Workspace/00_Governance/Scheduled), output folded into item 3 below.
3. **ora-tenant-hubspot-reconciliation output relocation** — step 6 changed from a standalone Notion Ops Hub child page to direct `open-items-tracker.md` rows (own `OI-NNN` per finding), closing the discoverability gap that nearly caused a redundant hand-redo.
4. **Unsigned-draft-to-signature nudge** — Gabriel set 5-business-day threshold, housed inside the existing `ora-weekly-hygiene` cadence rather than a new cron entry. Added as Block M (report-only, output also routed to `open-items-tracker.md`), catalyzed by the Kareem/Cricket DC LLC amendment sitting unsigned 07-17→07-25 undetected.

Files touched: `tech.md`, `MEMORY.md`, `project_master_workbook_single_writer_proposal_2026-07-25.md`, `~/.claude/scheduled-tasks/ora-weekly-hygiene/SKILL.md`, `Claude_Workspace/00_Governance/Scheduled/ora-tenant-hubspot-reconciliation/SKILL.md`. No workbook, HubSpot, or Notion data touched — documentation/skill-spec changes only, nothing executed live this session.

## 2026-07-24 — Governor-LTV false-clearance remediation shipped (PR #233)

 The weekly ora-financial-code-integrity-sweep found 7 defects (2 HIGH: negative-balance aggregate deflation + empty-snapshot book wipe, both false clearances of the Hard-Invariant-4 40% ceiling). Gabriel ordered fixes; 4 rounds of independent adversarial review then found 4 MORE real defects in the fixes themselves (id-overlap shrinkage guard froze refis; collision-padding masked a total wipe; preserved-id double-count over-triggered; shared-schema LTV bound failed whole-snapshot parse). Final state: net-shrinkage guard on writeDebtSnapshot with allowEmptySupersede confirmation, emptyCohort null-verdict, Zod-validated POST /snapshot, persisted-column updated_at gates on both acq sync writers ('archived' now no-clobber-locked), inclusive-ceiling float epsilon, and a round-7 ltv==rate collision defense (aggregate function only). Commit 50ffdec, branch fix/governor-ltv-false-clearance, Refute-Reviewed trailer. 3062/3062 tests. OPEN residuals: (1) debt-scoring.ts per-property signals still consume raw ltv unguarded — spawned task task_fe4b5d56; (2) refusedEmptySupersede is surfaced in POST /snapshot response + backfill CLI but the automated server/index.ts reload path only console.warns a refusal — a frozen book still looks healthy downstream; (3) pre-existing lease-count reconcile mismatch (exp 137 got 138) on origin/main, unrelated, unfixed. Process lesson: two guards built same-day each needed outside adversarial review to catch a real defect — refute passes on financial code are load-bearing, not ceremony.

## 2026-07-24 — ora-pm-ledger: Block B retro-sweep mode built; snapshot-diff cross-day defect fixed; alerts-engine "wrong dates" misdiagnosis corrected

Evening `ora-pm-ledger` run delivered A/B/C on time (18:17/18:19/18:23 ET, all exit 0). Three durable changes came out of it, plus one correction to a claim this session itself had made hours earlier.

**Block B retro-sweep mode — NEW (`outbox_qc_window.py`).** Block B swept only `[today 00:00 → run time]`, which left two permanent holes. (1) **Missed days**: a day the task didn't fire was never audited and nothing retried it — confirmed twice in one week from the send-log, **2026-07-17 and 2026-07-23** have no Outbox QC send or Ops Hub page. (2) **Evening tails**: the old B.2 asserted mail sent after the ~18:00 fire "land[s] in next day's window" — it does NOT, because the next day's window is `[D+1 00:00 → D+1 18:00]` and a message sent 18:30 on day D carries `sentDateTime` on day D, so it fell in no window ever. **Every day silently lost its ~18:00→24:00 tail.** Measured across 07-20/21/22/24 tails plus all of 07-23: **~46.6 hours of unaudited outbound mail in five days.** Both are one bug — coverage was modelled as "did we run today?" instead of "which spans have been swept?" Now tracks covered **intervals** in `state/outbox-qc-coverage.json`; 7-day lookback; `--commit` is a deliberately separate **fail-closed** step so a gap whose page/email failed to deliver stays open and retries (committing at plan time would silently swallow a day whose report never reached Gabriel — the exact class being killed); `dropped_beyond_lookback` is reported, never silently truncated; weekend gaps are surfaced and flagged so the Monday run finally audits Friday-evening-onward mail (Block B is Mon–Fri, so Sat/Sun was otherwise permanently unaudited). Retro results fold into ONE email and only mint a Notion page when the gap actually contains messages — most evening tails are empty and blank pages would bury the real ones. `--selftest` = 20 assertions (interval algebra, missed-day, evening-tail, today-capped-at-now, idempotent re-commit, lookback clamp + drop reporting, `tracking_since` floor, out-of-order/overlapping merges, weekend flagging, sub-minute sliver suppression), all passing. State seeded from real send-log times (07-20 18:20:59 · 07-21 18:21:45 · 07-22 18:25:37 · 07-24 18:15:00, `tracking_since` 2026-07-20). SKILL.md B.2/B.4/B.5/B.7/B.8 rewritten + amendment note.

**`tenant_db_snapshot_diff.py` — cross-day false positives FIXED.** First genuine cross-day run reported **267 of 298 rows changed when only 5 were real** (a Property Address correction, `9620 State 350 — Columbus OH` → `Kansas City MO`). It was fingerprinting five date-derived formula fields that recompute from the calendar. The "verified end-to-end 2026-07-20" sign-off written into this task's own SKILL.md was **wrong** — that verification was a *same-day second pull*, so it never crossed a date boundary. Fixed by excluding those fields **by name** (not by type — a formula over static inputs is still a real signal), comparing *filtered* fields on both sides rather than the stored hash (without which the first post-fix run would have reported all 298 rows changed), and adding a **bulk-field guard** that warns when any non-excluded field moves on >50% of rows. That guard immediately earned its keep: it caught `Months to Expiry`, a fifth derived field that would have burst on all 298 rows monthly rather than daily. Re-verified on real archived snapshots: 07-22→07-24 **5** (was 267) · 07-21→07-22 **20** (was 298) · 07-20→07-21 **164** — all substantive, no spurious warnings.

**CORRECTION — the Command Center "wrong lease dates" defect is NOT in `conditions.ts`.** This session's own EOD Ledger (T3-2) reported the alerts engine as emitting wrong expiration dates and named `conditions.ts` / `critical-dates.ts`. That attribution was **wrong**, and was inferred from bad output without reading the code. Executing the real `evaluateConditions` against the on-disk snapshot at `referenceDate 2026-07-24` produces entirely correct results — Granite Tops → `Renewal lapsed / holdover — lease end passed May 31, 2026`, J&R → `expires Jul 31, 2026 (7d)`, Carlton L. Handy → correctly silent. The rules were never broken. **Actual root cause: lease IDs embed a worksheet ROW INDEX and are unstable** — `data/alert-state.json` vs the live snapshot shows `zettler-2000-2002-`**135**→**131**, `2207-northwood-a4-`**22**→**21**, `29000-information-lane-101-`**53**→**50**. When row order shifts, a tenant's identity pairs with another row's dates AND the dedupe state silently invalidates (which is how J&R's genuine 7-day expiry vanished from the 07-24 alert set after firing on 07-23). **Already being fixed elsewhere — did NOT write a competing fix**: branch `fix/lease-id-integrity` (worktree `.claude/worktrees/lease-id-integrity-fix`), 10 commits + 3 REFUTE rounds, ~+1,359 lines with tests, commit `a9f0bf0` "stable lease ids independent of worksheet row position". Open follow-up for whoever lands it: `data/alert-state.json` still holds the OLD row-index ids and will keep mis-deduping until reconciled or reset. Detail: [[reference_lease_date_detector_defects_2026-07-24]].

**`.gitignore` allow-list extended.** `outbox_qc_window.py` landed gitignored (`scheduled-tasks/*/*` is deny-by-default with a per-file allow-list, same reason `tenant_db_snapshot_diff.py` needed `af3e615`). Left alone it would never reach the `ora-claude-config` backup — the same loss class that destroyed the original ora-pm-ledger spec in July. Added following the file's documented "name each durable file individually" convention; `state/` stays untracked deliberately (per-run data that churns daily; losing it degrades safely to the old today-only window).

**Two lessons worth carrying.** (1) A same-day rerun is not a valid test for any date-sensitive diff, fixture, or detector — "advance the clock" must be a required case. (2) Don't infer a code fault from bad output; execute the function against the real input first. Both defects this session looked identical from the outside (wrong dates in a report) and had completely different causes — one was a real fingerprinting bug, the other was upstream data identity.

**Landed (Gabriel-directed, later the same evening).** `d9f6462` = the four files above (`SKILL.md`, `tenant_db_snapshot_diff.py`, `outbox_qc_window.py` new, `.gitignore`); `262f371` = follow-up hardening. Both blocked first by `eos-review-gate`, which is now ENFORCING (an earlier entry today recorded it failing open — its missing `git_commit_parse.py` dependency has since landed). No override token was written: Gabriel had approved *committing*, not landing *unreviewed*, and those are not the same authorization.

**Three independent Fable-pinned review cycles followed, and the gate earned its keep on the first one.** Cycle 1 = CHANGES-REQUIRED, 10 defects; the top finding was mine and material: `run()` computed the new bulk-field guard's `warnings` and never emitted them, so **the guard was dead in production** and had only ever fired via my own verification probe — i.e. a claim I had already reported as working was false in the nightly path. Cycle 2 = APPROVED-WITH-NITS after fixing 7 defects (atomic tmp+fsync+replace writes; corrupt state degrading to a warning instead of raising and wedging every future 18:00 run; a row-count-collapse guard so a revoked Notion scope returning 200-with-0-rows cannot destroy the baseline; prune against injected `now` not the wall clock; inverted-span rejection; `>=` bulk threshold; exact-match `load_token`; bounded 429/5xx retry). It also exposed a genuine aliasing bug in my own code — a module-level `EMPTY_STATE` dict shallow-copied and then mutated by callers, cross-contaminating state within a process — now an `empty_state()` factory. Cycle 3 = APPROVED, clearing the four residual nits (null-cursor pagination break + page backstop + injectable fetch seam; archive fallback when `LATEST` is corrupt, plus a blanket refusal to persist any 0-row pull; sanitising stored non-increasing spans; and **fixing a self-fulfilling test of mine** that committed *today's* date so it passed even with the fix reverted). Cycle 3 verified every new assertion by REVERSION EXPERIMENT — reverting each fix on a copy and confirming the matching test then fails; all five discriminate. Final: selftests 32/32 (outbox) and 21/21 (tenant), real-data diffs unchanged.

**Accepted, not fixed** (reviewer: non-blocking, no further cycle): a null cursor arriving mid-pagination truncates a pull silently if the short result still clears the 50% collapse floor; and `run()`'s persist-refusal logic has no injection seam, so it is covered only by monkeypatched probes, not `--selftest`.

**Lesson worth keeping:** an independent reviewer caught, in one pass, a dead-in-production code path that I had already described to Gabriel as working. Re-reading your own diff does not substitute for it — and neither does a passing test suite, since two of the tests certifying this work were themselves non-discriminating until an outside pass reverted the fixes to check.

This entry was committed on its own via the isolated-hunk technique in [[reference_event_log_uncommitted_backlog]] (stage via `git apply --cached`, then a BARE `git commit` with no pathspec — a pathspec silently re-adds the whole working-tree file). The other ~5 sessions' entries in this file were deliberately left uncommitted for their owners ([[reference_event_log_partial_commit_splice]] · [[feedback_pathspec_commit_discards_index_splice]]).

## 2026-07-24 — Open-sessions board: ora-am-brief LAMS retirement dispatch found already-completed, MEMORY.md index corrected

Gabriel's decision on the board item (local_db4523d0-7199-4a86-bc84-36fac1bd7963): dispatch the Cowork session's copy-paste prompt to Code. On execution, found the entire 5-step prompt was redundant: oxford-cc-repo-health.md §2026-07-16 entry and the fleet-disposition-ledger's §9 (Claude_Workspace/00_Governance/outputs/2026-06-10_fleet-disposition-ledger.md) show a CC-surface session already closed every residual on 2026-07-16 — verified CC copy healthy (enabled:true, cron 0 6 * * *), verified fleet-wide single appearance (cc only) via fleet-status.py, fixed a companion registry-membership-probe.py ratification bug, and updated both the ledger and session-context.md's do-not-re-register note. Re-ran the same verification steps today (list_scheduled_tasks, fleet-status.py, registry-membership-probe.py) as a fresh confirmation only — all clean, no drift, nothing to change. Did not duplicate the ledger entry. Root cause of the redundant dispatch: MEMORY.md's index still listed this under OPEN/BLOCKED 8 days after project_ora_am_brief_lams_retirement_blocked.md itself was marked RETIRED + VERIFIED — corrected the index line (moved to a new CLOSED note, and used the same pass to also correct the adjacent FRED-key-exposure OPEN/BLOCKED line, which this same board session had already remediated).

## 2026-07-24 — Open-sessions board: "Memory index orphan links" logged as corroborating sighting, not a new incident

Gabriel's decision on the board item (local_6c1b4083-1332-4019-97bc-83a7d07ecdc7): log it. That session's eos-review-gate.py hook-missing/self-healed observation is the SAME 2026-07-24 machine-wide Bash-outage incident already logged in event_log.md and [[reference_concurrent_session_duplicate_hardening_work]]'s "RECURRED 2026-07-24" entry (a different session witnessing the same collision independently) — did not duplicate it as a new memory. Appended one genuinely new tactical detail to that existing reference file instead: Desktop Commander's process tool bypasses the broken Bash-matcher PreToolUse hook, so it stayed usable for read/inspect work throughout the outage when Bash itself was hard down.

## 2026-07-24 — correction to the eos-review-gate Bash-outage entry above: root cause was git clean -fd, not incremental worktree landing

The earlier entry today ("machine-wide Bash outage from mid-flight eos-review-gate landing") inferred its root cause purely from git evidence gathered as an outside/concurrent session (no `MERGE_HEAD`, file observed missing then present) and concluded the file was being landed incrementally, file-by-file, from the worktree. The shipping session's own first-person record — [[project_eos_review_gate_shipped_2026-07-24]] — shows the actual mechanism was more specific and in two parts: (1) an earlier `git merge --no-commit --no-ff` got its `MERGE_HEAD` silently absorbed by a *different* concurrent session's unrelated commit, poisoning the merge-base ([[reference_stale_merge_head_poisons_graph]]) — recovered via `git checkout <branch> -- <paths>` + a plain single-parent commit, which is why no real merge was ever in progress when checked; (2) separately, the shipping session's own `git clean -fd` in the live checkout deleted the already-placed untracked `hooks/eos-review-gate.py`, breaking every Bash call in-session until Gabriel explicitly confirmed a restore via an `allow-config-write` override token. That second event is almost certainly what this session observed from the outside as "file missing, then present" — not an incremental multi-file landing still in flight. The decision to stand down and not intervene was still correct (it was someone else's active, Gabriel-approved recovery either way), but the causal narrative in the earlier entry should be read as superseded by [[project_eos_review_gate_shipped_2026-07-24]]'s authoritative account. Lesson: when reconstructing another session's actions purely from git-state snapshots, flag the reconstruction as inferred, not established — and re-check against that session's own memory entry once it exists, rather than letting an inference stand as fact.

## 2026-07-24 — Open-sessions board: FRED key cleanup decided (restart + scrub)

Gabriel's decision on the "Compact MEMORY.md below 17.1KB" board item (local_5c4e6dec-2337-4ded-8adb-a652ab96114b): restart Claude Desktop tonight, scrub the dead-key file copies. Executed the scrub in-session: content-scanned all 21-file-class candidates by fingerprint (never printing the raw key); the 5 `backups/.claude.json.backup.*` files had already self-cleaned via the normal rolling-backup cycle (now hold only the live/new key fingerprint `3cfc85efb07f`) — nothing to touch there. Redacted the dead key (fingerprint `0f63fcc0868f`) from the 3 remaining OneDrive archived `ora-debt-maturity-snapshot/SKILL.md` copies (Claude_Workspace + Documents/Claude x2), 3 occurrences each, 9 total, verified clean post-write. Transcripts (9) and LAMS `audit.jsonl` (3) intentionally left untouched — append-only, age out per doctrine. Restart of Claude Desktop itself is a manual/physical step Gabriel must do — not executable from within a running Code session; flagged back to him, due before tomorrow's 05:15 ora-health-guard / 06:00 ora-am-brief fires.

## 2026-07-24 — Deal-stage sync: 1150 Newark Road Industrial — Zanesville, OH — Candidate → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-24 — machine-wide Bash outage from mid-flight eos-review-gate landing; self-healed via guarded-import fail-open design

**Symptom.** Every Bash tool call in every concurrent session started failing with `PreToolUse:Bash hook error: ... can't open file '...\hooks\eos-review-gate.py': [Errno 2] No such file or directory`. `settings.json:371-379` (uncommitted working-tree change, `M settings.json`) registered a `Bash`-matcher `PreToolUse` hook pointing at `hooks/eos-review-gate.py`, which did not yet exist on disk in the main `~/.claude` checkout.

**Root cause.** `feat/eos-review-gate` (commits `d7008a6` → `97a64a8` → `83dd7dc`, "blocking independent-review gate for blast-radius/financial-decision commits") is checked out in its own worktree at `.claude/worktrees/eos-review-gate`, never merged to `main`. A concurrent session was manually landing that branch's files into the shared main checkout file-by-file rather than via a real `git merge` (no `MERGE_HEAD` was ever present). `settings.json`'s hook registration landed before `hooks/eos-review-gate.py` itself did, opening a window where every Bash call in every session — not just this one — hit the missing-file error. Mid-investigation, `hooks/eos-review-gate.py` itself appeared on disk (confirmed by a `git cat-file -e HEAD:...` check flipping from "does not exist" to "exists on disk, but not in HEAD" between two checks seconds apart) while its dependency `hooks/lib/git_commit_parse.py` still had not landed.

**Why it self-healed instead of needing a revert.** `eos-review-gate.py`'s own commit history anticipated exactly this: the `git_commit_parse` import is wrapped in `try/except Exception: PARSE_CONTRACT_LOADED = False`, with the comment "an unguarded import crashes at MODULE LOAD ... it would traceback on EVERY Bash call in EVERY session -- not just commits." `main()` opens with `if not PARSE_CONTRACT_LOADED: return  # no information -> allow`. So the moment the `.py` file itself existed, Bash calls stopped crashing — the gate just fails open (does not yet enforce the independent-review requirement) until `hooks/lib/git_commit_parse.py` also lands from the worktree.

**Action taken: none, deliberately.** `git worktree list` showed `feat/eos-review-gate` live and mid-commit (`83dd7dc`), and files visibly landing in the shared checkout in real time — this was an active landing, not an abandoned one, so reverting `settings.json` or hand-copying `hooks/lib/git_commit_parse.py` myself would have fought/duplicated the owning session's work (the exact collision class in [[reference_concurrent_session_duplicate_hardening_work]]). Stood down once Bash was confirmed working again; did not touch `settings.json`, `hooks/eos-review-gate.py`, or `hooks/lib/`.

**Residual, not yet re-checked:** the review-gate is present but non-enforcing (fails open) until `hooks/lib/git_commit_parse.py` lands from the worktree too — blast-radius/financial-decision commits are currently NOT getting the independent-review gate. Re-verify `PARSE_CONTRACT_LOADED` once the worktree's landing finishes.

Related: [[reference_concurrent_session_duplicate_hardening_work]] (the collision-avoidance pattern this followed), [[feedback_fail_open_over_mutex_for_fleet_gates]] (same fail-open design philosophy elsewhere in the guard stack).

## 2026-07-24 — guard.ps1 content-equality gate (false-alarm class closed, 10/10 fixture test); ora-appsec-sweep canary refined to opus-only; dispatch "miss" resolved as a non-defect

**guard.ps1 mtime-churn false alarm — FIXED.** `restored[]` non-empty is a STEP-3 EMAIL alarm, and the engine decided purely on mtime. The governance mirror lives in OneDrive, whose sync bumps mtimes after the guard copies canonical -> mirror; on the next run newest-wins therefore points AT the mirror and copies back. Observed live: the same 6 ids in `backed_up[]` at 12:12 and `restored[]` at 12:33 with canonical/gov/local byte-identical throughout (md5-verified on 4 of 6). Ordinary OneDrive sync could page Gabriel about a restore that moved zero bytes. Fix: SHA256 content comparison gates BOTH the canonical restore and the mirror refresh; a newer mtime with identical content is now reported in a new `churn_suppressed[]` field rather than acted on. Suppression is reported, never silently swallowed — an invisible suppressor would just be a new blind spot of the kind this guard exists to catch. Fail-safe preserved: an unreadable/unhashable file falls back to the old mtime-only behaviour rather than skipping a restore it cannot prove unnecessary.

*Verification (not a live poke — 8 sessions were concurrently active):* built an isolated fixture harness that runs the REAL guard.ps1 logic against a synthetic registry + canon/gov/local trees, with the 4 root literals rewritten to temp paths. 5 cases, 10 assertions, **10/10 pass**: churn case not restored / reported as churn / content untouched; genuine divergence still restored with correct content applied; missing canonical still restored; absent-everywhere still flagged; clean task neither restored nor needlessly copied; `checked` count correct. Harness: `scratchpad/test_guard.py`. One assertion was corrected mid-run — `t-clean` (canonical newest, mirrors older, all identical) legitimately lands in `churn_suppressed` because the old logic WOULD have copied and counted it; the expectation was wrong, not the code. Live run after the fix: `restored:[]`, `churn_suppressed:[]`, and a real `backed_up` for the two SKILL.mds actually edited today. Full dry-run: VERDICT CLEAN, real `.cc.json` byte-identical (md5 `40cfc098…`). SKILL.md STEP 2 documents the new field as never-an-alarm; the dry-run wrapper surfaces it as INFO only.

**ora-appsec-sweep canary — REFINED, and my earlier report was imprecise.** The "claude-opus-4-8 + claude-sonnet-5" reading aggregated the whole of session `4b66d74c`. Cutting the transcript at the first human-authored turn shows the **scheduled** portion is `claude-opus-4-8` and nothing else — all 163 assistant messages from 17:38:32Z — while the 86 `claude-sonnet-5` messages follow Gabriel running `/model` at 19:54:12Z and are a deliberate human switch, not fleet behaviour. Tag narrowed to `[MODEL: claude-opus-4-8 …]`. **Method rule added to the reference memory: always cut a canary transcript at the first human turn — a scheduled session can continue as an interactive one.** The core conclusion is unchanged and if anything cleaner: frontmatter `model:` is inert on CC/MCP.

**"security-auditor dispatch may not have executed" — RESOLVED, no defect.** The 07-22 run made zero Agent/Task calls, but v1.1 (which *introduced* the dispatch) was authored DURING that same session — its own Edit calls to `ora-appsec-sweep\SKILL.md` are in the transcript. The fire ran the v1.0 inline-CHECKS spec, which had no dispatch to make. Consequence that still stands: **the dispatch has never actually executed; its first live test is the next scheduled fire (2026-07-29)** — verify a subagent transcript is produced then, do not assume the path works.

**Pattern to watch (2 data points, not a rule):** both CC/MCP tasks canaried so far (`ora-site-exposure-probe`, `ora-appsec-sweep`) fired on `claude-opus-4-8` despite `settings.json`'s `claude-sonnet-5` default — consistent with a fleet-wide opus server-pin rather than per-task randomness. A third canary settles it.

**STILL OPEN — Gabriel's call, unchanged:** `ora-appsec-sweep` reviews security-gate and payment-facing code while firing on opus-4-8, below CLAUDE.md's never-below-Fable floor, with no in-registry fix. Options: accept and document; migrate to LAMS where the pin is enforceable; or rely on the (still-unexercised) Fable-pinned subagent dispatch.

## 2026-07-24 — ora-task-integrity-guard per_task_limit skip loop: first confirmed "lone task" pattern; disable→enable remedy TESTED AND FAILED

**How it surfaced.** Follow-up to the 07:00 collision fix. The residual throttle-skips had been reported as the documented benign catch-up burst; running that reference's OWN prescribed check (do the skips cluster with other tasks, or is one task alone?) showed they were not.

**Finding — genuinely a different pattern.** `ora-task-integrity-guard` skipping once per 60s, ALONE, no neighbouring tasks in the same instant, reason `per_task_limit` (same-task double-fire guard) rather than `global_limit`. Onset 12:21:22 ET. The same-day 10:34–10:43 events WERE the benign burst (3 tasks within one millisecond) — the two are distinguishable and were conflated in the prior report. All three historical `per_task_limit` cases cleared in 1–3 min (check-dirty-files-session-pr 3.0, ora-lease-expiration-brief 1.0, ora-pm-ledger 1.0); this one ran 20+ min.

**Confound ruled out.** A concurrent session (`fdaf1f4e`) was dry-running this exact task via `dry-run-task-integrity-guard.ps1` — a plausible alternative cause of a double-fire rejection. Eliminated on timestamps: its first dry-run touch was 12:32:14, **11 minutes after** the 12:21:22 onset.

**Remedy tested and FAILED (Gabriel-directed).** disable→enable re-arm. Disable demonstrably suppressed it — a clean 12:38:23 → 12:42:23 gap against an otherwise unbroken 60s cadence. Re-enable brought it straight back: 12:42:23, 12:43:23, 12:44:23 at 1/min. So stale re-arm state is NOT the mechanism; re-arming reproduces it. Recorded rather than retried.

**Root cause NOT asserted.** Onset was ~60s after this session's `update_scheduled_task` retime (07:00→07:05), making the retime the obvious suspect. But the workstation had **36 claude.exe processes / ~13 live sessions** at the time — heavy saturation of the same concurrency ceiling this throttle protects. A reading that fits every observation equally well: the retime merely made the task *due*, and it joined a retry queue against a ceiling that stayed saturated for 20+ min from concurrent session load. The scheduler's arbitration is closed-source; the timestamps do not separate "retime-triggered" from "saturation-sustained." Per the standing reference, the documented lever is machine load, not per-task config. Captured in `reference_fleet_throttle_skip_catchup_burst.md` so this is not re-derived from scratch.

**State left behind.** Task is ENABLED (verified) — it must stay so: it is the SOLE fleet-integrity runner (LAMS twin retired), and disabling it to silence the metric would blind the exact check that catches registry loss. `nextRunAt` remained correct (2026-07-25 07:14 ET) throughout, so scheduled execution was never at risk; only the skip metric is polluted, and those events age out of the 24h window.

**Method correction carried in.** The prior turn judged a co-written file "settled" via mtime quiet. `feedback_positive_attribution_over_mtime.md` (written same day) rules that out — attribution was redone via `hooks/sessions/<sid>/touched-files.txt`, which corrected the file's owner from `53f57fbe` to `fdaf1f4e` and showed 4 further writes by them AFTER this session's edits. This session's three `output_contract` cron strings were re-verified intact afterward; the commit is left to that file's owner.

## 2026-07-24 — dry-run wrapper no longer forges the guard's liveness beacon; ora-appsec-sweep is NOT running on Fable (transcript canary)

Follow-up actioning the three items left open by the v1.7 guard fix earlier today.

**Item 1 — `dry-run-task-integrity-guard.ps1` was forging a liveness beacon (FIXED).** It wrote the REAL `_state-history\<date>.cc.json`, self-described as "harmlessly overwritable." It was not. That filename is declared in `ora-task-integrity-guard`'s `output_contract` as `is_primary_health_signal: true` / `on_missing_severity: alarm` and is consumed by `automation-health-monitor` Step 0.56 — it is the ONLY evidence that a guard which is silent-by-design on a clean run actually fired. **A dry-run could therefore make a DARK guard look alive**, masking the precise failure class the chain exists to catch (secondary issue: without `-SnapshotJsonPath` it falls back to the on-disk registry, so it also downgraded fidelity). Now writes `<date>.cc.dryrun.json`, a suffix matched by neither the output_contract pattern nor `membership-guard.ps1`'s `.lams.json` filter. Verified: real `.cc.json` byte-identical across a full dry-run (md5 `40cfc098…`, MCP source string intact). Second defect fixed in the same script: its STEP 0.5 comment and its WOULD-ALARM reason both claimed the write had to precede `membership-guard.ps1` because that engine reads the snapshot — **it does not, and has not since the 2026-07-15 filename split** (`membership-guard.ps1:78-79` filters `20*-*.lams.json`; its line 63 explicitly excludes `.cc.json`). A failed dry-run snapshot write no longer poisons the verdict. Stale `12:45 ET` references updated to the retimed slot.

**Item 2 — `ora-appsec-sweep` MODEL tag: the premise was wrong, and the correction is material.** The claim carried in `reference_scheduled_task_model_standard.md` (and repeated by me) that this task is "deliberately Fable-pinned, correct as-is" conflated three distinct things: the SKILL.md frontmatter `model: fable` (declared INTENT), the in-task `security-auditor` Agent dispatch passing `model: 'fable'` (a real, honored mechanism), and the model the scheduled task itself actually fires on — only the last of which a `[MODEL:]` tag asserts. Transcript canary on its own 2026-07-22 17:38Z run (session `4b66d74c-b948-49c1-8f8d-883d821e7aa3`, first timestamp within 2s of registry `lastRunAt`): main loop ran **`claude-opus-4-8` x163 + `claude-sonnet-5` x86, ZERO `claude-fable-5`**. This is the first direct evidence that **frontmatter `model:` is inert on the CC/MCP fleet**, settling the question `ora-appsec-sweep` v1.1 left hedged. Tagged MODEL-OBSERVED (not UNTAGGED, not an intentional-exception pass); task bumped to v1.2 with the MODEL PIN note rewritten; reference memory corrected. **OPEN, needs Gabriel: this security-gate task is running BELOW CLAUDE.md's never-below-Fable floor and there is no in-registry fix (no settable model field on this fleet).** Also observed: that run wrote ZERO subagent transcripts, so the `security-auditor` dispatch may not have executed at all — unverified, flagged, not chased.

**Item 3 — closed, no action.** The `0 7 -> 5 7` cron move was the Gabriel-directed retiming already logged under "07:00 fleet collision cleared." Confirmed, nothing to do.

**NEW finding (reported, NOT fixed — needs Gabriel, touches the authoritative engine):** `guard.ps1` can email a false STEP-3 alarm on pure mtime churn. A dry-run at 12:33 returned `restored[]` = 6 tasks (`ora-pm-ledger`, `ora-deal-aging-sla`, `automation-health-monitor`, `ora-health-guard`, `ora-sofr-direct-prefetch`, `ora-command-center-mirror-drift-check`) — but canonical, governance-mirror and local-mirror copies are byte-identical (md5 verified on 4 of 6), so nothing was actually restored. The same ids appeared in `backed_up[]` at 12:12 and in `restored[]` at 12:33: OneDrive sync bumps the governance-mirror mtime after the guard copies canonical->mirror, so newest-wins flips direction and copies back. Content-neutral, but `restored[] non-empty` is a STEP-3 EMAIL alarm condition — this will page on ordinary OneDrive sync activity, which is alarm-fatigue on a guard whose entire value is silence-unless-broken. Suggested fix (not applied): compare content hash, not mtime, before counting a restore.

**Mechanism confirmed:** `list_scheduled_tasks` reads each task's `description` LIVE from its SKILL.md frontmatter — the registry JSON's stored `description` is stale and is not the source of truth (neither the v1.7 guard text nor the v1.6 retiming text appears in the registry file, yet both are returned by the tool). Editing SKILL.md frontmatter is therefore the correct and sufficient way to retag; no `update_scheduled_task` registry write is needed. Consistent with `reference_cc_scheduler_filepath_mechanism`.

Files left uncommitted — the shared `.claude` checkout had 29 uncommitted changes across ~7 concurrent sessions.

## 2026-07-24 — ora-task-integrity-guard v1.7: model-currency classifier corrected + every Bash command literal in the file un-broken

Two defects, both surfaced by that morning's own 07:00 ET run of this guard.

**(a) STEP 2.5 model-currency classifier was the LAMS test mis-applied to CC/MCP.** It graded `ora-site-exposure-probe`'s transcript-verified `claude-opus-4-8` observation as MODEL-STALE — implying a disable/recreate cycle that doctrine says cannot exist on a server-pinned fleet — while 21 content-free UNVERIFIABLE tags passed clean. `reference_scheduled_task_model_standard.md`'s "NOT settable, but IS observable" section defines the CC/MCP check as **tag-presence + observation-freshness**, NOT match-the-standard; the guard contradicted it. MODEL-CURRENT/MODEL-STALE retired, replaced with MODEL-OBSERVED / MODEL-OBSERVATION-STALE / MODEL-UNVERIFIABLE / MODEL-UNTAGGED, freshness anchored to `reference_model_release_checklist.md`'s "Current lineup as of" date. The same spec ambiguity explains the 07-22 (STALE=0) vs 07-24 (STALE=1) swing on an unchanged tag — one tag, two classifications, no actual drift. `automation-health-monitor` Step 0.07 was checked and is CORRECT (LAMS-scoped, explicitly excludes CC/MCP) — unchanged. `model-currency-cc.md` got an appended revised key + corrected 07-24 line; prior dated lines left byte-intact per append-only.

**(b) EVERY Bash command literal in the file was unsafe — not just the one that errored.** Git Bash collapses unquoted backslashes, so STEP 1.5 scripts 1-2 (shipped 07-16) had failed on first invocation every run since, silently hand-corrected by each run's agent and therefore never surfaced. The first fix asserted the PowerShell lines were safe because their `-File` arg was quoted; testing that claim showed the **interpreter path is its own command word** and collapses too (`C:WindowsSystem32WindowsPowerShellv1.0powershell.exe: command not found`) — STEP 1, STEP 1.5 script 3, and the DRY-RUN line were broken identically. All literals rewritten forward-slashed/quoted, plus an explicit PATH-QUOTING RULE. New memory: `feedback_bash_unquoted_windows_paths_collapse`.

**Verified:** all five scripts run verbatim exit 0; dry-run wrapper reports CLEAN; `guard.ps1` propagated the edit to both mirrors (`backed_up:["ora-task-integrity-guard"]`). Files left uncommitted — the shared `.claude` checkout had 19 uncommitted changes from concurrent sessions.

**Open, not actioned (needs Gabriel):**
1. `dry-run-task-integrity-guard.ps1` OVERWRITES the day's canonical `_state-history/<date>.cc.json` with lower-fidelity on-disk-fallback data, despite documenting itself "read-mostly and safe to run anytime" — it silently downgrades the output_contract's own primary health signal. Today's snapshot was restored from a fresh `list_scheduled_tasks` call.
2. `ora-appsec-sweep` is MODEL-UNTAGGED but is a confirmed intentional Fable pin (CLAUDE.md security floor) — tag it, do not flip to Sonnet.
3. Cron `0 7 → 5 7` observed mid-session is NOT drift — it is the Gabriel-directed retiming already logged in this file's "07:00 fleet collision cleared" entry; the `output_contract.expected_on` fields followed it. No action.

## 2026-07-24 — commit-provenance-guard compound-command blind spot: root cause CONFIRMED (was SPECULATIVE) and fixed

CLOSES the open question in `44efc61`'s durable-record entry (this same file, earlier
today): *"LEADING HYPOTHESIS [SPECULATIVE -- the janitor's literal command was not
recoverable]... the compound form is the blind spot."* That janitor was this session
(`53f57fbe`). The literal commands ARE recoverable from this session's own history:
all four backlog-landing commits (`44efc61`, `5b347d2`, `281b159`, and a fourth) used
the exact shape `git add <paths> && git commit -q -F -`. Root cause is now CONFIRMED,
not speculative, and matches the other session's hypothesis precisely:
`candidate_paths()` derived candidates only from `git diff --cached --name-only`;
PreToolUse fires BEFORE the command executes, so at hook-fire time the index is still
empty of whatever the `git add` half of the compound is about to stage;
`candidate_paths()` returned `set()`; `main()`'s `if not cands: return` allowed the
commit before `foreign_hits()` (the actual liveness/TTL check) was ever consulted --
despite every OTHER precondition for a block being met.

FIXED, TDD + isolated worktree (`fix-provenance-guard-compound-add`, merged `485a62d`,
commit `f6de17d`): new `pending_add_paths(repo, cmd)` resolves what a preceding `git
add` in the same compound command is about to stage, WITHOUT ever running `git add`,
by querying the pre-add working-tree state the pending add is about to consume.

TWO ROUNDS of the mandatory adversarial REFUTE pass (security-auditor agent, required
for `hooks/**` override/auth-logic per Engineering OS) — this is worth recording
because both rounds found REAL, non-cosmetic gaps in what looked like a complete fix:

- Round 1 [HIGH]: the first version of the fix only recognized `&&`/`;`/`||`/`|`-
  joined, `git`-token-FIRST segments. Two ordinary (not adversarial) shapes bypassed
  it entirely and reproduced the exact incident: newline-separated statements (no
  operator between the add and the commit -- `shlex.split()` treats a bare newline as
  whitespace) and env-var-prefixed invocations (`FOO=bar git add x`). Both empirically
  verified as false-allows against the round-1 code before being closed in round 2.
- Round 1 also surfaced (mid-fix, not a numbered finding) that "stop collecting adds
  at the FIRST commit segment" silently drops an add sandwiched between two commits
  in one command (`commit1; add; commit2`) even though it's genuinely staged for the
  second one -- corrected to "collect any add segment with at least one commit
  segment somewhere after it."
- Round 2 (verifying round 1's fixes) found one NEW gap the fix itself introduced:
  per-line tokenization loses quote context, so a multi-line heredoc commit-message
  BODY whose prose happens to start a line with the literal words "git add ..." can
  be mistaken for a real segment. Verified this fails SAFE ONLY (adds a spurious
  candidate, never hides a real one) and requires an unrealistic shape (2+ chained
  `git commit` invocations in one Bash call) this fleet doesn't use -- accepted and
  documented inline rather than fixed, same threat-model framing as the pre-existing
  git-alias-blindness gap.

38 tests (23 pre-existing regression + 9 round-1 + 5 round-2), including full
end-to-end reproductions of all 3 real audit PoCs and a locked-in safe-direction
guarantee for the accepted heredoc gap. Full detail in the merge commit `485a62d`.

WHY THIS MATTERS BEYOND THIS ONE BUG: `git add X && git commit` is the idiomatic,
default way to write a commit -- not a special janitor-only pattern. This guard was
therefore likely blind to a large fraction of ordinary Claude-authored commits, not
just sweeping backlogs, whenever a foreign hit existed. The guard now covers that
shape (plus the two round-1 variants); it remains fail-open by construction on
missing/stale/unreadable data, per its own documented safety invariant -- unaffected
by this change.

Related: [[reference_commit_provenance_guard]] · [[reference_event_log_partial_commit_splice]].

## 2026-07-24 — 07:00 fleet collision cleared: ora-task-integrity-guard retimed 07:00 → 07:05 ET (Gabriel-directed)

**Trigger.** Follow-up investigation into the 09:20 collision flagged by the 2026-07-20 schematic refresh. That one was already found, root-caused and fixed on 07-20 (ora-deal-aging-sla → 09:25, commit `b35a916`); re-verified live this session — no overlap remains. The investigation instead surfaced a *new* collision.

**Finding.** `fleet-status.py` flagged `07:00:{ora-task-integrity-guard, ora-cam-reconciliation-annual}`. Verified NOT a false positive of the `cron_hm()` day-blind class fixed in `25088f7` — `crons_share_a_day()` is present (fleet-status.py:131, used :296) and the two genuinely share Jan 15 (guard daily `0 7 * * *`; CAM annual `0 7 15 1 *`).

**Cause.** `ora-task-integrity-guard` was retimed 12:45 → 07:00 ET earlier the same day (v1.6, Gabriel-directed via automation-health-monitor's audit, commit `7c7117b`) to sit inside the 05:15–07:00 AM-cluster window. That move landed it on the annual CAM task's slot.

**Severity assessment.** Real but near-inert — one overlap per year (next 2027-01-15). The material cost was that it pinned the fleet verdict at ATTENTION on *every* run, masking future genuine collisions. Risk asymmetry noted: the CAM task fires once a year, so losing a `global_limit` race costs it a full year; the daily guard shrugs off a single skip.

**Ruling + fix (Gabriel, interactive).** Shift the guard 07:00 → **07:05 ET** — CC-side (writable from Code; the CAM task is LAMS and needs a Cowork-surface write), preserves the AM-cluster intent exactly, and protects the annual task's single fire. Applied via `update_scheduled_task` after a clean registry single-writer pre-flight (`registry-membership.log` latest 2026-07-24T12:13:15, no adds/drops, no concurrent writer).

**Self-reference sweep (lesson carried from the 09:20 fix).** That fix had to correct two hardcoded cron self-references inside the task's own SKILL.md that would otherwise have silently disagreed with the live schedule. Same defect class found here: **three** `expected_on.cron: "0 7 * * *"` entries in the `output_contract` (blocks block-cc-snapshot / block-registry-membership-log / block-fleet-heartbeat-json, lines 13/23/33) plus one prose reference. All four corrected to 07:05.

**Verified.** `same-time collisions 0`. Verdict remains ATTENTION but now driven *solely* by throttle skips (11/24h), which match the documented benign catch-up-burst pattern in `reference_fleet_throttle_skip_catchup_burst.md`.

**NOT committed.** `scheduled-tasks/ora-task-integrity-guard/SKILL.md` carries another session's uncommitted v1.7 work (STEP 2.5 classifier retirement + Git Bash path-quoting fix); the shared-checkout hook flagged 16 uncommitted changes across 5 sessions in the .claude main checkout. My edits are surgical exact-string replacements that touch none of their hunks, but the commit is left to the v1.7 owner to avoid sweeping their work (commit-provenance-guard class).

## 2026-07-24 — acquisition-underwriting v4.4 installed (STAGE 2.8 — FORG v1.0, Save-skill click confirmed)

Adds Functional Obsolescence & Durability Grade (proposed/pilot; BDS-5 ratified at 10 pts by Gabriel 2026-07-23). Source: ora-skills commit `4a29470` (local main; not yet pushed to origin as of this entry — origin/main still at `979b12d`). Packaged via Entry Point A on Code (repo-direct, after two failed Entry Point B chat-attachment handoffs — root cause: the Cowork session had real-filesystem Desktop Commander access and never needed a chat "attachment," just the real path); installed via Entry Point B on Cowork reading the `.skill` directly off disk once redirected. Post-install verified from Code: runtime cache (`skills-plugin\...\acquisition-underwriting\`) SHA256-identical to repo on both `SKILL.md` and `target-markets.json`, H1 reads v4.4, `STAGE 2.8` present, BDS-5 ratification line present, cache mtime 2026-07-24 11:31.

## 2026-07-24 — ora-deal-aging-sla v1.1 (dashed-UUID fix + STEP 3b posture doctrine); landed via a foreign janitor commit with commit-provenance-guard silent

CHANGE (Gabriel-directed, from the 09:25 ora-deal-aging-sla run): SKILL.md -> v1.1, two fixes.

1. STEP 1's Acquisition Pipeline Tracker data source was the UNDASHED `collection://bcfe4a03…4fa138b`. `notion-query-data-sources` rejects that form with `validation_error`/`sql_invalid` reading *"table … was not exposed for this request"* — which reads like a permissions/sharing problem and sends you debugging the wrong layer. The dashed `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b` works. The undashed id had been there since authoring, so EVERY run from 2026-07-18 to 2026-07-24 failed its first query and recovered by hand. Fixed, with an inline "do not tidy the dashes out" warning + the `notion-fetch` recovery path. Sweep (two independent methods — Grep and a Python walk, since rg has false-negatived rooted at scheduled-tasks) confirms it was the ONLY undashed `collection://` literal across `~/.claude/scheduled-tasks/`, `ora-skills`, and the LAMS `Documents/Claude/Scheduled` tree. Memory: reference_notion_query_requires_dashed_uuid.md.

2. New STEP 3b makes Notion-vs-Outlook posture mismatch a first-class output row. Deeper than the reporting refinement it started as: STEP 2 classified deals off the tracker's own `Next Action` text, which is exactly what goes stale when work happens off-Notion. 754 Old State Route 74 was an internal-gate EXCLUSION on 07-24 (field stamped 07-21 PM: "NOT sent to Patterson — awaiting Gabriel's review/sign-off"), yet Eric had sent the PSA with modifications to `kmklaw.com` on 07-23. Only searching Outlook anyway reclassified it to a live counsel ask (1 business day, inside the 7bd threshold). So 3b(b) now REQUIRES falsifying any internal-gate exclusion whose text makes an Outlook-falsifiable claim ("not sent", "awaiting sign-off", "staged for review") against the live thread before the exclusion sticks. GUARD CONDITION amended so a zero-qualifying-ask run cannot skip 3b(b); STEP 7 gets a titled mismatch section that leads the summary when breaches are zero; two guardrails added (mismatches are reported never reconciled — correcting the field would destroy the divergence evidence and reset the clock; tracker posture never outranks the live thread). STEP 2's "already resolved against ORA" branch also gained its first worked example (511 Industrial Mile: LOI outstanding since 5/15, most breach-looking row in the pipeline on age alone, correctly NOT flagged because the broker confirmed 07-17 the property went to a competing buyer — the test is whether an answer is still owed, not whether the status field still reads "Submitted").

PROVENANCE ANOMALY: this v1.1 diff (+32/-8) was NOT committed by its authoring session. It was swept into `44efc61 chore(scheduled-tasks): land canonical SKILL.md backlog from prior sessions` — a genuine 13-file janitor sweep (8 other SKILL.mds + 5 memory files) — 73 seconds after the last edit (last touch 10:49:50, commit ct=1784904663 = 10:51:03), while the authoring session was mid-turn and `status=working`. The memory files went the same way in `281b159`. Content verified byte-identical to intent (marker-by-marker + empty `git diff HEAD`); nothing lost. But the commit message misdescribes a substantive doctrine change as a prior-session backlog `chore`, so `git log --oneline` archaeology will find no reasoning for why STEP 3b exists. THIS ENTRY is the durable record of that reasoning.

commit-provenance-guard.py DID NOT FIRE, and its documented preconditions were all met:
- Recorder healthy — all 9 SKILL.md touches + both memory touches present in the authoring session's touched-files.txt with timestamps.
- Liveness healthy — the authoring session was present in obsidian-fleet-mirror/session-state.json as `status=working`, so `other_active_sessions()` would have reported it.
- NO `allow-foreign-commit` sentinel exists anywhere under hooks/sessions/ — the sanctioned backlog-landing bypass (guard line 353) was NOT used.
- TTL: touch was 73s old. `already_committed_since()` would return False (last commit touching that path long predated the touch). => a hit, i.e. a BLOCK, was the correct outcome.
- Wiring intact: settings.json PreToolUse matcher `Bash` -> commit-provenance-guard.py.

LEADING HYPOTHESIS [SPECULATIVE — the janitor's literal command was not recoverable]: `candidate_paths()` derives candidates from `git diff --cached --name-only`, but PreToolUse fires BEFORE the command executes. For a compound one-liner `git add -A && git commit -m "..."` the index is still empty of those paths at hook time, so candidates come back empty and line 344's `if not cands: return` allows it — the files are staged and committed microseconds later, unguarded. `_has_all_flag()` covers `-a/--all` on the commit itself but NOT a preceding `git add` in the same command. A separate `git add` in an earlier Bash call would be caught (index already populated); the compound form is the blind spot, and it is the most natural way to write a sweeping janitor commit. Alternatives not excluded: an internal exception hitting the deliberate fail-open `except Exception: pass` (silent by construction), or a commit made outside a hooked Bash call.

NOT FIXED — hooks/** is blast radius and security-gate code (mandatory REFUTE pass + Gabriel's explicit approval, and config-write-guard blocks the edit pending an `allow-config-write` token). Proposed fix if approved: teach `candidate_paths()` to union in what a preceding `git add` in the same command would stage.

COLLATERAL FINDING: shared-checkout-guard repeatedly attributed the 38-41 uncommitted changes to open session `99aea6a4`. That session was `idle` since 10:35:01 and has NO provenance dir under hooks/sessions/ at all, so it did not make the 10:51 commits. Consistent with the existing feedback_shared_checkout_guard_session_attribution_unreliable.md — the named ID is a hint, never evidence. Also of note: 11 sessions were concurrently registered in the liveness mirror.

CROSS-REFERENCE: a different session independently documented the same incident from the janitor's side (`1ebdbb0`, appended to reference_commit_provenance_guard.md). Its "SKILL.md v1.1" is its OWN ora-command-center-mirror-drift-check/SKILL.md — verified, not a misattribution of this work; two sessions coincidentally held an uncommitted v1.1. Its stated mechanism ("does not protect a live session's UNSTAGED work") is likely incomplete: staged-vs-unstaged is not the exemption, since `-a` and a prior `git add` are both covered — the pre-execution empty index is the more probable gap.

OPEN (deal-side, not systems): 754's Notion `Next Action` still asserts the PSA was not sent. The task is read-only on that field by design, so it needs Gabriel's hand; until then the weekly ora-deal-command-board reads the stale posture.

## 2026-07-24 — Rate Snapshot staleness root-caused: catch-up-burst ordering, not an orphaned producer; ora-sofr-direct-prefetch v1.1 guard added

SYMPTOM: During the 2026-07-24 ora-sofr-direct-prefetch run, the Rate Snapshot page (35e6ecd8) header read `fetched_at: 2026-07-22 13:25 ET` with §1/§3/§4 at 07-21/07-22 vintage, suggesting ora-am-brief Block A had not refreshed on 07-23 or 07-24.

TRACE (orphaned-task-forensics Workflow A):
- NOT an orphaning. ora-am-brief is enabled and live on CC/MCP (`0 6 * * *`, filePath resolves). Ran 07-17, 07-21, 07-22, 07-24.
- 07-24 observation was a RACE, not a failure: am-brief started 14:35:28Z; the prefetch task read the page at 14:36:26Z (58s later) and saw pre-run state; am-brief finished writing at ~10:40 ET. Self-resolved.
- 07-23 gap is REAL, confirmed three ways: (1) no run transcript (`scheduled-task name="ora-am-brief"` present in transcripts dated 07-17/07-21/07-22/07-24, absent 07-23); (2) no throttle-skip entry for 07-23 (its only skips 07-21 09:46, 07-22 09:20, 07-24 10:34 ET, all `global_limit`); (3) no "ORA Daily Brief" email 07-23. Page fetched_at jumped 07-22 13:25 ET -> 07-24 10:40 ET, ~45h stale.

ROOT CAUSE (independently corroborated by ora-health-guard 2026-07-24 Block A.0): the Desktop app is offline overnight, so 05:00-06:00 ET slots depend on catch-up backfill. Health guard counts 5 late-wake bursts since 07-14 (07-14, 07-20, 07-21, 07-22, 07-24) and a 16-task pileup in the 05:00-09:30 window. On 07-24 the 06:00 slot was backfilled 4h35m late; on 07-23 it was not backfilled at all. Exact backfill cutoff UNRESOLVED [SPECULATIVE] — n=2, and the registry keeps only a single `lastRunAt`.

SECOND FINDING: the catch-up burst does not preserve intra-cluster ordering (health guard's own wording). ora-sofr-direct-prefetch (10:10 ET) is built assuming ora-am-brief (06:00 ET) already ran; in a burst they fire seconds apart, inverting it. On 07-24 that produced a redundant SOFR patch that am-brief superseded ~4 min later with identical values at full precision (am-brief's §2 note records it cross-validated against the prefetch pull). Benign, but exposed a latent false-alarm path: a Block A write landing between STEP 2's read and STEP 3c's write would fail `old_str` and post a false failure to the Ops Hub.

RESOLUTION (Gabriel approved option B, 2026-07-24): ora-sofr-direct-prefetch SKILL.md -> v1.1. STEP 2 now also reads Block A's `fetched_at` and sets `am_brief_pending`; STEP 3c treats an `old_str` mismatch that re-resolves to already-fresh as SUCCESS (no Ops Hub post) and retries once only if still stale; STEP 4 treats a supersede-by-am-brief as PASS with no re-patch; STEP 5 silent-success list extended. Fallback role preserved — a genuinely missed Block A day still gets patched. Also corrected a stale fact in the same file: it attributed ora-am-brief Block A to the LAMS/Cowork fleet, retired there 2026-07-16 and now CC/MCP.

DEFERRED (Gabriel's call, not taken): option A — moving the 05:00-09:30 AM cluster later to match actual machine uptime. Root cause is machine uptime, not cron placement; rescheduling trades away the point of a 6am brief.

OPEN: (1) exact catch-up backfill window rule unknown; (2) ora-health-guard's setup-self-audit reports "all 57 SKILL.md parse cleanly" but this file's frontmatter fails strict YAML at the pre-existing `[MODEL: UNVERIFIABLE` token — same failure in HEAD, so the audit uses a lenient parser or a different corpus; the assurance claim is weaker than it reads. (3) SKILL.md edit left UNCOMMITTED — .claude main checkout had ~39 uncommitted changes from live session 99aea6a4 at the time.

## 2026-07-24 — ora-command-center-mirror-drift-check v1.1: baseline list replaced with ff-only abort tests
**Trigger:** the 10:40 ET scheduled run posted HEALTHY (drift 0, `LastTaskResult` 0, `LastRunTime` 10:00:01, no merge markers) but had to make a judgment call: the working tree held one entry outside the SKILL.md known-benign baseline — untracked `docs/superpowers/plans/2026-07-22-brain-overlay-staleness-fix-plan.md`. The baseline was **stale in both directions**: none of its four documented entries (`.claude/launch.json.example`, `package.json`, `.wrangler/`, `scripts/dev-watchdog.cjs`) were present anymore, and 07-22's CRLF-dirty `.claude/workflows/refute-financial-change.js` was also resolved. Gabriel directed the fix in-turn.

**Change (v1.0 → v1.1, `~/.claude/scheduled-tasks/ora-command-center-mirror-drift-check/SKILL.md`):**
- **Step 3** no longer enumerates benign files. It now classifies each `git status --short` entry by running a test that answers the only question that matters — *can this entry abort `git pull --ff-only`?*: untracked with no counterpart on `origin/main` (`git ls-tree origin/main -- <path>` empty) → BENIGN · untracked that DOES exist on `origin/main` → FLAG (the case that genuinely aborts ff-only) · modified but EOL/whitespace-only (`git diff --ignore-all-space --ignore-cr-at-eol` empty) → BENIGN · modified with substantive content or any staged/conflicted status → FLAG · any merge/rebase marker → FLAG. Historic filenames are retained as illustrative context with an explicit "context, NOT an exemption — run the test" caveat.
- **Step 5** ALARM condition reworded to key off those tests rather than "beyond the known-benign baseline"; BENIGN entries must be recorded in the Notion row **with their verification output**, never silently skipped.
- **Step 6** corrected: the Ops Hub was described as a *database ID*; it is a **page**, and completion rows are child pages of `32b6ecd8-9e59-81f2-b329-df3fd0e25062` (parent type `page_id`, not `data_source_id`). Full dashed ID, parent type, and title convention now written into the file.

**Verification:** new tests replayed against the live tree reproduce the run's verdict (plan doc → BENIGN); FLAG branch counterfactually confirmed against `package.json` / `README.md` (`ls-tree` non-empty → would FLAG).

**Not committed** — the shared `~/.claude` checkout held ~41 uncommitted changes belonging to open session `99aea6a4`; committing would have swept their work in. SKILL.md on disk is authoritative for the CC/MCP scheduler (registry stores `filePath` only), so v1.1 is live regardless.

**Generalizable lesson:** a monitoring check whose "known-benign" definition is a hardcoded file list rots in both directions and trains the reader to discount its own alarms. Prefer a test that names the failure mode.

**Ops note (no action):** no Ops Hub rows of any producer exist for 2026-07-23 — Claude Desktop was closed Thursday. Expected per this task's KNOWN LIMITATION; the native Windows task was unaffected (`NumberOfMissedRuns` = 0).

## 2026-07-24 — AR/delinquency invented-pointer defect closed (ora-am-brief §4c + ora-pm-ledger)

**Defect.** The 2026-07-22 Command Center Daily Brief §4c told the reader to "refer to the latest **ora-pm-ledger** AR run (nightly 18:00 ET) for current balances." No such run exists — `ora-pm-ledger` has no AR-computation module and never has. The pointer was **model-generated at run time**, not a hardcoded string (confirmed: the phrase appears nowhere under `~/.claude`), so this was a fabrication in the same class as the 2026-07-16 date defect — it sent Gabriel to a nonexistent artifact for a financial figure. Surfaced by the 2026-07-22 ora-pm-ledger Block C run.

**Design decision — did NOT build an AR module.** Investigated `ora-ar-export-freshness-nudge` (LAMS) first. Per the 2026-04-28 QuickBooks-Scrub Master Change Set (Notion `3506ecd8-9e59-815b-b6a8-cff24fa5b926`): AR's canonical source is the PM platforms (Rent Manager/Yardi/AppFolio) **manually** exported to SharePoint `Cowork OS / QB Exports / AR Aging`; QuickBooks Desktop AR is explicitly NOT primary; **no live connector exists** for QB Desktop or any PM platform; and the only importer (`scripts/ar-import.ts`, oxford-command-center PR #81) is **interactive-CLI-only by design** because a human must confirm ambiguous tenant matches. A nightly AR job would therefore have to auto-write fuzzy-matched arrears to a financial overlay unconfirmed. Rejected on data-integrity grounds; corrected the pointer instead.

**Fix (2 files, content-only, no registry change).**
- `~/.claude/scheduled-tasks/ora-am-brief/SKILL.md` — added **"4c — AR / DELINQUENCY SOURCE OF RECORD"** clause inside the 2026-07-16 critical-dates OVERRIDE block, between list items 4 and 5. Documents the real chain, and requires §4c to record a COVERAGE GAP naming that chain (or "current AR exposure not verifiable — awaiting export") and to never invent/promise an automated AR run. Deliberately inserted WITHOUT renumbering — "step 5" is cross-referenced in surrounding prose.
- `~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md` — added **"AR / DELINQUENCY — THIS TASK DOES NOT PRODUCE IT"** to §C.2, closing the reverse confusion (a future ledger run "helpfully" building the module the Brief implied).

**Verified.** Both clauses present; am-brief items 4/5 intact and ordered with the clause between them; `step 5` cross-ref resolves; frontmatter intact in both. Registry `path` for ora-am-brief confirmed = the edited file (`list_scheduled_tasks`), so the scheduler reads it; file-is-authoritative means no commit needed to take effect. Self-heal direction checked (`guard.ps1` = newest-wins, restores only if canonical is missing/stale) — the edit propagates to mirrors rather than being reverted at the next 12:45 guard fire.

**NOT committed.** `.claude` main checkout had 37 uncommitted changes belonging to another live session (`99aea6a4`); per shared-checkout single-writer rule the commit was left to that session's owner.

## 2026-07-23 — ora-cc-schematic-refresh (2026-07-23a): producer-clobber resync + memory-integrity EXIT 1

Scheduled 2×/week schematic refresh (Thu 14:15 ET slot), first FULL probe-suite re-run since the durable source diverged from the published artifact.

- **Producer-clobber caught & resolved.** Durable source `~/.claude/artifacts/claude-code-schematic.html` was at REV 2026-07-20a while the *published* artifact had advanced to REV 2026-07-21b via three ad-hoc fleet-only rechecks (07-20b / 07-21a / 07-21b) that never synced back to the source file. Per the refresh SKILL's pre-edit check, pulled the artifact's authoritative content into the source BEFORE applying this run's edits (would otherwise have wiped 3 revisions). No data lost.
- **memory-integrity-probe.py flipped exit 0 → EXIT 1** (was clean at the prior full pass). 132/132 files present on disk (working-tree reconcile 1:1), but MEMORY.md at git HEAD links 5 files not committed to HEAD's tree: project_config_write_guard_boundary_fix_2026-07-21.md, project_tenant_db_renewal_watch_view_2026-07-22.md, reference_config_write_guard_quote_split_gap.md, reference_notion_view_dsl_formula_filter_bug.md, reference_workflow_scriptpath_crlf_rejection.md. Commit-hygiene gap (a fresh clone would get 5 broken index pointers), not lost data — the owning session should commit the 5 files. Left untouched (not this session's WIP).
- Other 4 probes green: governor-drift exit 0 (638 files, DSCR 1.25x / LTV 40%), doctrine-integrity exit 0 (8/8 guards, CLAUDE.md 1694 words), confidentiality-guard 131/131.
- Fleet VERDICT ATTENTION — 52 tracked / 49 enabled (27 CC/MCP + 22 LAMS) / 3 disabled; 13 throttle skips/24h all ora-pm-ledger (documented catch-up-burst, expected); 0 collisions/overdue/missed.
- Repos clean: oxford-command-center main==origin/main @e6aba59; ora-pm clean @1b304e8. enabledPlugins unchanged (14 keys / 12 true).

## 2026-07-22 — OI-023 (snapshot provenance asOf) closed: PR #231 opened on oxford-command-center

The Command Center snapshot's provenance labels (`meta.asOf`/`cash.asOf`/`assumptions.asOf`) no longer pin to the June `WORKBOOK_AS_OF` constant — `parse.ts` now reads each sheet's own cached "As of ..." dateline (rent roll 2026-07-17, cash 2026-07-10 live-verified; missing dateline falls back with a DataQualityFlag warn, never silently). `parseTasks` monthCol deliberately stays on `WORKBOOK_AS_OF` (test-locked). Day-count `?? s.meta.asOf` fallback audit: all production alerting paths pass explicit run dates; last omitting caller (`brain.setTenantNote`) wired to `referenceDate()`. TDD (9 new tests), full gate green (2,964 tests, typecheck 0, lint 0), adversarial REFUTE pass run (caught one real break: brain.test.ts partial config mock). PR: https://github.com/ZeOoba/oxford-command-center/pull/231 (merge = Gabriel). Tracker row moved to Closed. NOTE: this OI-023 (opened 07-21, snapshot asOf) is distinct from the 07-20 event-log entries' "OI-023" (IWNS LLC rent-roll gap, closed same day) — apparent ID recycle during the 07-20 tracker worktree/HEAD divergence incident (see project_open_items_tracker_worktree_head_divergence.md).

## 2026-07-22 — Doctrine-guard WARN fixed; pathspec-commit-discards-splice gotcha found and documented

Triggered by the scheduled `ora-doctrine-integrity-guard` run (12:55 ET): clean overall (doctrine exit 0, governor exit 0, telemetry exit 0), but the doctrine probe flagged a fail-open WARN — a `MEMORY.md` index entry (skill description-version-extraction gotcha, line 61) exceeded the 150-char hook-description cap by one character. Gabriel asked for it fixed, then to commit just that file.

**First commit attempt correctly blocked.** `commit-provenance-guard.py` blocked the initial commit: session `40a4b051` (oxfordra.net SEO-audit work, same OneDrive cwd) had touched `MEMORY.md` within the 6h TTL and was still live (`session-state.json` showed status flipping idle→working in real time). Verified this was a genuine collision, not a false positive, before waiting: confirmed the session's presence, its touch recency (3.1h, inside TTL), and that the content hadn't already landed (`git log -1` on the file predated the touch). Re-checked periodically; once `40a4b051` was no longer present in `session-state.json` (ended/pruned), re-attempted.

**Surgical splice landed, but the closing commit re-swept foreign content anyway.** Re-staged just the one-line fix via `hash-object` + `update-index --cacheinfo` (the [[reference-event-log-partial-commit-splice]] technique), verified `git diff --cached` showed only the intended line, then closed with `git commit -m "..." -- MEMORY.md` — the guard's own suggested remediation form ("commit only your own files with an explicit pathspec"). That pathspec form ignores the index for a splice and re-reads the working tree instead, silently discarding the surgical stage. Result: four unrelated hunks from `40a4b051`'s SEO-audit work (two new project entries, an SEO-audit-line refresh, two new reference entries) landed under the fix's commit message (`61facf4`). Caught on a post-commit diff review, not before. Reviewed the swept-in content — complete, finished work, not a mid-edit fragment — and amended the message to accurately attribute it rather than reverting, which would have destroyed real work (`62e5a35`).

**Root-caused and fixed at the source, not just patched around.** The gotcha: `git commit -- <path>` always re-reads the working tree for that path regardless of what the index holds — a splice only survives a **bare** `git commit -m "..."` with no pathspec at all. Fixed in three places so the next session (or the next guard block) doesn't hit this blind: `reference_event_log_partial_commit_splice.md` step 6 now states the bare-commit requirement explicitly with the incident as evidence; `commit-provenance-guard.py`'s block-time remediation text carries the same caveat inline, plus a full writeup added to its docstring fix-history log (edited under an explicit `allow-config-write` override token, per Gabriel's in-turn confirmation); and a new standalone memory entry, [[feedback-pathspec-commit-discards-index-splice]], captures the lesson on its own so it surfaces independently of either doc.

**Closing commit applied the lesson it documents.** `dad9746` (the guard/doc/memory-entry commit itself) was staged with exact pathspecs — not `-A` — against a MEMORY.md diff re-verified clean beforehand, and closed with a bare `git commit -m "..."` with no pathspec, per the fix just written. Landed cleanly: 4 files, 45 insertions, nothing from the ~20 other files dirty across the fleet's concurrent sessions at that moment pulled in.

**Pushed.** `git fetch` confirmed 0 behind / 2 ahead of `origin/main` before pushing (the second ahead commit, `2c02865`, was another live session's unrelated work that landed on local HEAD in between — verified as a clean fast-forward, not a merge, before pushing both). `git push origin main` succeeded (`0731e65..2c02865`), pre-push doctrine gate clean. Re-ran the doctrine probe as part of the push hook: MEMORY.md over-150-char count now reads 0, confirming the original WARN is durably closed.

Commits: `61facf4` (superseded) → `62e5a35` (amended, accurate) → `dad9746` (guard/doc/memory fixes, pushed).

## 2026-07-22 — connector-drift fixed: chrome-devtools + Apify marked retired in tech.md

`ora-health-guard` (late catch-up run, fired 09:47 ET vs 05:15 scheduled) Block C `connector-drift-probe` FAILed with 2 drifts: `chrome-devtools` and `Apify` documented `state=active` in `tech.md`'s machine-readable connector roster but not live. Verified the finding against ground truth before editing (probe findings are a hypothesis, not a verdict): neither `mcp__` allow-prefix is present in `settings.json permissions.allow` — chrome-devtools survives only as plugin skill toggles (`chrome-devtools-mcp:*` set off/user-invocable), Apify entirely absent — and `.claude.json` carries no `mcpServers` key for either. Both are documented-alive-but-dead, same class as the Grain/Windows-MCP case.

Fixed in [[tech]]: roster block flipped both to `state=retired`; the human-readable **Active:** prose list dropped both; a dated line added to the "Not usable / retired" prose recording the removal + verification method. Re-ran the probe: OK — 21 roster entries consistent with live state (exit 0). Today's health-guard FAIL resolved.

Committed `2c02865` (`memory(tech): mark chrome-devtools + Apify connectors retired`, 4 ins / 4 del). tech.md was co-mingled with session `84d0d1b4`'s in-flight Property Register "14 rows" correction — committed only my 2 connector hunks via a filtered `git apply --cached` + plain `git commit` (not `git commit -- <path>`, which would have swept their working-tree hunk in), leaving their WIP + the frontmatter `modified:` stamp intact and uncommitted. Splice discipline per [[reference_event_log_partial_commit_splice]] / [[shared-checkout-cofile-patch-hazard]].

## 2026-07-21 — "Artifact updates and setup optimization" session logged (retroactive, spanning 07-17 through 07-21)

Long-running session (`local_5282a851`, title "Artifact updates and setup optimization") never got a consolidated event_log entry despite substantial multi-day work; logged retroactively at Gabriel's request after reviewing its transcript. Summary of the substantive threads, newest-relevant-first:

**Real scheduling collision found and fixed.** A fleet-status re-check (2026-07-20) flipped verdict OK→ATTENTION: `ora-site-exposure-probe` (Wed 09:20 ET, live since 07-10) and newly-registered `ora-deal-aging-sla` (weekdays 09:20 ET, ratified 07-18) both fired at the same clock minute every Wednesday. Investigated and confirmed a REAL shared-resource conflict, not a coincidental overlap: both post a completion child page to the same Notion Ops Hub parent (`32b6ecd8`) and both touch the Outlook COM automation surface concurrently — a previously-observed failure class in this fleet. Root cause: `ora-deal-aging-sla` was registered without checking existing Wednesday slots, the exact check the registration QC gate exists for. Fixed by retiming `ora-deal-aging-sla` to 09:25 ET (effective ~09:32 with dispatch delay) via `update_scheduled_task`, plus correcting two hardcoded cron self-references inside its own `SKILL.md` `output_contract` that would otherwise have quietly disagreed with the live schedule. Committed `b35a916`, pushed.

**False-positive collision bug found and fixed in `fleet-status.py` itself.** A follow-up re-check surfaced a new apparent collision: `ora-financial-code-integrity-sweep` and `ora-appsec-sweep` both at 13:30. Investigated and found it was NOT real — the two tasks run on different days (Monday `30 13 * * 1` vs. Wednesday `30 13 * * 3`), matching `ora-appsec-sweep`'s own SKILL.md stated design intent (deliberately offset from the Monday sweep to avoid RAM contention). Root cause: `fleet-status.py`'s `cron_hm()` collision detector only compared hour:minute, ignoring day-of-week/month entirely — the mirror-image bug of the real Wednesday collision above. Fixed by adding `crons_share_a_day()` (proper cron OR-semantics, full year walk) before flagging a collision; added 3 new tests (disjoint weekdays don't collide, overlapping ranges still do, existing same-day case unaffected) — 16/16 passing. Committed and pushed `25088f7`.

**Throttle-skip catch-up-burst mechanism diagnosed and documented (new standing reference, then corroborated twice).** `ora-deal-aging-sla` kept showing residual throttle-skip events even after its collision fix. Traced to the Desktop scheduler's own `global_limit` concurrency ceiling — multiple tasks piling up and hitting the ceiling in a dead heat when the app reopens after sitting closed past several tasks' scheduled slots (a catch-up-burst signature), not a per-task config defect. Documented in new memory file `reference_fleet_throttle_skip_catchup_burst.md` so the metric isn't re-investigated from scratch. A second, independent occurrence 3 days later (`ora-am-brief`/`ora-deal-aging-sla`/`check-dirty-files-session-pr` piling up at 09:46:48 ET, throttle-skips jumping 10→18/24h) matched the documented pattern exactly and was added to the same file as corroborating evidence rather than treated as a new investigation. Both pushed (`37c8577`, `e569244`).

**OI-009 Notion Tenant DB gap swept DB-wide.** Investigated uncommitted WIP found sitting in the shared `~/.claude` checkout (`event_log.md` + `open-items-tracker.md`) via a dispatched read-only background agent rather than guessing at authorship or discarding it — identified as a legitimate, already-finished DB-wide sweep closing OI-009 (Tenant DB rows title-archived but never had `Row Retired` actually set): 73 additional stale rows found beyond the earlier 42-row Northwood-only pass, 115 total firm-wide, verified via a fresh COUNT query returning 0. Confirmed healthy (no duplicate OI-### IDs, cross-references consistent, self-correction annotations followed the never-delete convention) before committing it on Gabriel's instruction (`b64921e`), isolated from other unrelated WIP in the same checkout.

**Housekeeping fix:** `ora-uw-northridge-brockton-full` had been re-registered live by another session (reversing an earlier same-day retirement — a deliberate decision, left alone) but its `SKILL.md` wasn't git-tracked, unlike all 82 sibling task files. Brought under version control, byte-identical content (`6c3388c`).

**Memory consolidation pass** (3-phase: take stock / consolidate / tidy index) — 5 files touched: two stale project-status corrections, one extension of `reference_concurrent_session_duplicate_hardening_work.md` with a same-day recurrence (the shared-tracker OI-### ID collision class hit twice, confirming that file's own prediction), and a new `feedback_verify_wip_settled_via_mtime.md` capturing the mtime-comparison technique used to judge whether uncommitted WIP was still live. `MEMORY.md` index tidied (2 stale entries corrected, 2 new pointers, all under the 150-char line limit). Committed `e01eefd`, pushed.

**Artifact (schematic) maintained across 5 revisions this arc** (`rev 2026-07-17c` stability confirmation → `20a` collision found → `20b` collision fixed → `21a` false-positive + throttle-skip diagnosis → `21b` second throttle-skip occurrence), each scoped honestly — sections not re-verified in a given pass were explicitly flagged stale-and-unconfirmed rather than silently restated. One incidental slip: a publish call minted a stray duplicate artifact, caught immediately, and removed via Chrome browser automation (claude.ai's artifacts UI has no API delete) — confirmed removed before continuing.

Every commit in this arc was staged by explicit path, never `-A`/`.`, consistently isolating the session's own edits from other sessions' concurrent WIP in the same shared `~/.claude` checkout — the same discipline this thread's own splice technique ([[reference_event_log_partial_commit_splice]]) formalizes for the specific case of `event_log.md` itself.

No files modified by this logging session beyond this entry — purely a retroactive record of another session's already-completed and already-pushed work.

## 2026-07-21 — acquisition-underwriting re-click + ora-operations-extensions plugin reinstall confirmed (Gabriel)

Follow-up to the same-day acquisition-underwriting/deal-retirement description-token disambiguation commits (`f2e452f`, `d701493`), which reintroduced pending-reimport status for both after the earlier 15-skill batch install. Packaged and staged both from a Code-surface session: `acquisition-underwriting.skill` (repackaged, standalone Save-skill path — multi-file, bundles `target-markets.json`) and `ora-operations-extensions.plugin` (rebuilt v0.1.4→v0.1.5 via `tools/build_plugin.py`, since `deal-retirement` is plugin-bundled and needs a plugin reinstall, not a standalone click).

**Gabriel confirmed running the install** ("I ran this," 2026-07-21, in response to a direct question). Independently verified before this entry, not logged on trust alone:
- `acquisition-underwriting`: cache SKILL.md SHA256-matches repo commit `f2e452f`.
- `deal-retirement`: content SHA256-matches repo commit `d701493` at the actual **plugin cache mirror** (`...\rpm\plugin_01Sq7t7TEQEoa4G1asrLe8ms\skills\deal-retirement\`, not the standalone skills-plugin cache — confirmed the distinction matters, per the 2026-07-17 precedent of checking the wrong location).
- Cache mtime on both: **18:06:40**, after staging (~17:01-17:02) — a fresh install, not stale pre-existing content.
- `pending_reimport.py list` → "none pending" immediately after, consistent with a completed install triggering the ledger clear.

Also committed the `plugin-build.json` 0.1.4→0.1.5 version bump that `build_plugin.py --bump patch` had left uncommitted in the repo (`3ce7631`) — repo now matches what's actually live.

No files modified by this session beyond the event_log entry itself; the install action was Gabriel's own click, confirmed directly rather than inferred.

## 2026-07-21 (18:08 ET) — acquisition-underwriting + deal-retirement (ora-operations-extensions) CONFIRMED INSTALLED — Cowork session, package-and-stage-skill Entry point B

Two pre-packaged, pre-verified artifacts staged from an earlier Code-surface session (`C:\Users\Owner\ora-skills\_staging\2026-07-21_index-unregistered-batch\`) — the only two entries `pending_reimport.py list` carried at session start — installed via distinct paths per Step 0's plugin-membership routing gate.

**acquisition-underwriting.skill** (standalone; `plugin_of()` → `None`): 4-item integrity pre-check run before surfacing — exists · 2 zip entries, forward-slash, expected set (SKILL.md + injected `target-markets.json`) · SKILL.md raw SHA256 byte-identical to repo commit `f2e452f` (`77e9763a...`), shared-root-dep `target-markets.json` byte-identical to repo-root copy (`28dba293...`) · staged to session outputs. No repackaging. **Gabriel confirmed the Save-skill click.** Post-install verify: runtime cache (`...\skills-plugin\...\skills\acquisition-underwriting\`) description now reads "schema rev 1.1" (was "v1.1") — the f2e452f fix is live; both files present. `pending_reimport.py clear acquisition-underwriting` run. This closes the item logged eight entries below today ("acquisition-underwriting skill staging — Not sure, recheck") as still needing a fresh click against f2e452f.

**ora-operations-extensions.plugin v0.1.5** (deal-retirement is plugin-member-only; `plugin_of('deal-retirement')` → `ora-operations-extensions` — routed as plugin reinstall, NOT a standalone Save-skill, per Step 0). Verified before surfacing: 9 zip entries (`.claude-plugin/plugin.json` + README + 7 member SKILL.md files, matching the "seven institutional skills" manifest description) · `skills/deal-retirement/SKILL.md` raw SHA256 byte-identical to the repo's canonical top-level `deal-retirement/SKILL.md` (commit `d701493`, not the `plugins/.../skills/...` path — that resolves to a non-existent file per the 2026-07-17 false-mismatch precedent). **Gabriel confirmed the plugin install.** Post-install verify at the PLUGIN cache mirror specifically (`...\rpm\plugin_01Sq7t7TEQEoa4G1asrLe8ms\`, not the standalone skills-plugin cache): `.claude-plugin\plugin.json` version `0.1.5` ; `skills\deal-retirement\SKILL.md` description now reads "Prior rev 1.1 (...)" / "v1.2" (the d701493 disambiguation is live, was previously the stacked/ambiguous v1.1+v1.2 wording); all 7 member skill dirs present. `pending_reimport.py clear deal-retirement` run; ledger now reports "none pending (cache in sync with repo)".

**Flagged, not actioned:** `plugins/ora-operations-extensions/plugin-build.json` carries an uncommitted working-tree change (`"version": "0.1.4"` → `"0.1.5"`) — the installed plugin content matches this uncommitted state, so the install is sound, but the repo will read as one version behind the shipped plugin until Gabriel commits the bump. Left for Gabriel rather than committed unprompted.

Did not touch the unrelated staged `_event_entry.md` found in the same staging folder (a draft entry for a separate, already-completed 15-skill standalone Save-skill batch from an earlier session today — out of scope for this task, not logged here to avoid misattributing that batch's work to this session).

No deploys, no scheduled-task changes, no email.

## 2026-07-21 — Open-sessions board dispatched; 6 items decided

ora-open-sessions-board 2026-07-21 17:00 ET run: probed 364 unarchived sessions, 6 actionable items reached the board (4 NEEDS-ANSWER, 1 STALLED, 1 INTERRUPTED; 27 excluded as fleet runs / already-decided-and-unchanged / sub-30-min). Notion deal-stage reconciliation ran clean (5 transitions logged — see separate 2026-07-21 deal-stage-sync entries — 3 with disposition PASS appended to deal-decision-ledger.md; flagged 1333 Research Road Passed → Candidate for Gabriel's awareness, not in the active-deal-pipeline table). Gabriel's decisions:

- **Loans External covenant analysis / Red Branch Road register** (local_47ae43e6) — Add line item. Executed: added the Muirkirk Properties, LLC intercompany promissory note ($1,778,552.34 orig., $1,380,000 o/s 12/31/2025) as its own entry in `loans-external-register.html`, tagged as related-party/not-external-debt, JS syntax validated via node.
- **ora-cowork-heartbeat beacon gap, thread A** (local_2674549c) — Check inbox now. Checked: no GitHub watchdog alert has landed today (2026-07-21) despite the 16-hr stale threshold having passed hours ago; last watchdog email was yesterday's Issue #6 thread (2026-07-20, still open). The external monitor appears not to have re-fired today — worth a look independent of the heartbeat task itself.
- **ora-cowork-heartbeat beacon gap, thread B** (local_a67aca7d) — Spin off Cowork session. Cannot execute directly — confirmed via ccd_session_mgmt tooling that this Code-surface session has no cross-surface session-creation capability into Cowork/LAMS. Handoff prompt for the delete+recreate drafted and returned to Gabriel to paste into a Cowork session himself.
- **acquisition-underwriting skill import** (local_8d6215b6) — Already done, drop.
- **acquisition-underwriting skill staging** (local_0e4c2618) — Not sure, recheck. Checked `tools/pending_reimport.py list`: acquisition-underwriting is STILL pending reimport as of 2026-07-21T20:44Z, now against a newer commit (`f2e452f`, description-token disambiguation) than the v4.3/`34c0094` package this session staged. Whether that earlier Save-skill click took is now moot — a fresh Save-skill + ledger clear is needed regardless.
- **Add confidential-deal egress guard to om-extract.ts** (local_41d96432) — Drop.

## 2026-07-21 — Deal-stage sync: 2900 Northridge Dr NW — Walker, MI (Kent County) — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 2196 Port Sheldon Street — Jenison, MI — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 1150 Newark Road Industrial — Zanesville, OH — (none) → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 4331 Brockton Dr SE — Kentwood, MI (Airport Industrial Center) — (none) → Passed (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Deal-stage sync: 1333 Research Road — Passed → Candidate (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry existed. Tripwire only — see Notion for the actual decision context.

## 2026-07-21 — Repo-wide sweep for the acquisition-underwriting version-token gotcha: one more instance found and fixed (deal-retirement)

Follow-up Code-surface session to the same-day `acquisition-underwriting` description fix (commit `f2e452f`) and its companion memory file `reference_skill_description_version_extraction_gotcha.md`. Swept all 53 `SKILL.md` files in `ora-skills` for the same class of bug: a bare `vX.Y(` token in the frontmatter description that a naive version-extraction regex could misread as the skill's file version.

**22 skills carry a `vX.Y(` description token; 21 are clean** — each is a single, self-referential note matching its own changelog's latest entry (or the file's only version reference). `register-scheduled-task`'s H1 also states its version (`v2.7`), consistent with the description.

**1 flagged and fixed: `deal-retirement`.** A different variant of the same risk — not a sub-component/schema version colliding with the file version (the acquisition-underwriting pattern), but two genuine file-version notes stacked back-to-back in the description (`v1.1 (2026-07-16: ...)`. `v1.2 (2026-07-18: ...)`) with no body changelog section to disambiguate. A naive first-match regex would have logged the superseded v1.1 instead of the true current v1.2 (visible only via inline `[v1.2]` tags in the Standard Workflows steps). Fixed the same way: reworded the superseded entry to `Prior rev 1.1 (...)` so it no longer matches a bare `vX.Y(` token, leaving v1.2 as the sole marker. Packager-validated (925/1024 chars, `python tools/package_skills.py` exit 0). Committed as `d701493`.

Repo-first check (`git log -1` / `git status`) was clean before editing — HEAD was `f2e452f`, only untracked `_staging/` present (the expected `PENDING_REIMPORT.md` side effect from the acquisition-underwriting fix). No ruling, scorecard weight, governor constant, or substantive skill logic changed by either fix — description wording only.

This closes the "was not exhaustively swept" gap the acquisition-underwriting memory entry flagged the same day — a future session does not need to re-run this audit from scratch unless new skills are added or existing descriptions are re-edited.

## 2026-07-21 — Correction: archiving 01_Workspace/outputs/ stale copies broke doctrine-integrity-probe.py; refreshed in place instead of allowlisting

Follow-up to the same-day archive of 12 stale `01_Workspace/outputs/<skill>/SKILL.md` copies to `_archive/2026-07-21_stale-outputs-skills/`. That move removed the only Code/Cowork-surface resolution path `doctrine-integrity-probe.py`'s `collect_skill_dirs()` had for all 12 — re-ran the probe's own resolver post-archive and confirmed all 12 flipped to unresolvable.

**First fix attempt was wrong.** Added all 12 to `PLUGIN_SKILL_ALLOWLIST` (mirroring the existing `re-operations` entry). `test-doctrine-integrity-probe.py`'s `test_real_doctrine_skills_resolve()` caught it: a deliberate regression guard, dated to the 2026-06-06 review, asserts `communication-intelligence` and `deal-comparison` must resolve via a REAL directory, explicitly NOT via the allowlist — because allowlist-masking a skill that's actually missing/stale is the exact failure mode that guard exists to prevent. Reverted the allowlist change back to `{"re-operations"}` only, restored the original comment.

**Correct fix:** refreshed all 12 `outputs/<skill>/SKILL.md` files in place with byte-exact current content copied from the authoritative `ora-skills` repo (SHA256-verified match, all 12). This satisfies the probe's structural resolution AND eliminates the stale/governor-relevant content the original audit flagged (deal-comparison's pre-RCT-v03 scoring bands, exception-detection's retired-Rube reference) — the stale versions remain preserved in `_archive/2026-07-21_stale-outputs-skills/` as the historical record, not touched further.

Re-ran the full test suite (`test-doctrine-integrity-probe.py`) after the refresh: all 39 tests pass, exit 0, including `test_real_doctrine_skills_resolve`.

No commits made to `~/.claude` (shared-checkout hazard flagged again by the PreToolUse hook — session `a0d59799` has 36 unrelated uncommitted changes in that checkout; committing now would co-mingle their WIP with this fix). The `doctrine-integrity-probe.py` edit and the `01_Workspace/outputs/` refresh are both saved to disk and verified working, but `git add`/`commit` on `~/.claude/maintenance/doctrine-integrity-probe.py` is left for whoever reconciles that session's WIP.

## 2026-07-21 — 15-skill Save-skill batch confirmed installed (Entry point B pre-packaged install)

Companion to the same-day "21 index-unregistered skills" backfill entry above: the 14 re-staged skills plus the 1 held skill (acquisition-underwriting) — 15 total — were packaged today via `tools/package_skills.py` in an earlier Code-surface session, hash-verified against the repo at package time, and handed off to this Cowork session for install via `package-and-stage-skill` Entry point B (pre-packaged install, steps 5-8 only).

**Step 0 (plugin-membership gate):** `plugin_of()` returned `None` for all 15 — none are shadowed by a plugin bundle; standalone Save-skill path confirmed correct for every package.

**Integrity pre-check (per package, before surfacing):** exists · zip entries forward-slash, expected file set matches repo dir · SKILL.md byte-identical to repo · `SHARED_ROOT_DEPS` `target-markets.json` byte-identical to repo root for the 3 consumers in this batch (acquisition-underwriting, deal-comparison, rent-comp). No package rejected back to Entry point A.

**Gabriel confirmed the Save-skill click on all 15.** Post-install verification: every packaged file present and content-identical in the runtime cache mirror (`...\skills-plugin\...\skills\<skill>\`) for all 15 — no missing files, no stale content. Runtime-cache `SKILL.md` mtimes cluster 2026-07-21 16:31:14-16:33:43, consistent with sequential clicks landing this session (not stale pre-existing cache), including acquisition-underwriting (16:31:14) — closing the gap the 2026-07-18 doctrine review had logged as still awaiting this click, independent of content freshness (content was already byte-identical pre-click, per that entry).

**Confirmed installs (skill v version):**
- acquisition-underwriting v4.3
- census-acs-extract v1.0
- communication-intelligence v1.2
- conversation-archival v2.0
- deal-comparison v1.0
- document-assembly v1.3
- file-reconciliation v1.0
- fleet-advisory-remediation v1.1
- graph-app-registration v1.0
- legal-intelligence v1.1
- orphaned-task-forensics v1.1
- portfolio-growth v1.0
- portfolio-reporting v1.1
- rent-comp v1.1
- tenant-intelligence v1.0

`pending_reimport.py clear <skill>` run for all 15 post-verification. The 6 skills backfill-confirmed earlier today (exception-detection, deal-execution, loi-generation, owner-outreach, disposition-analysis, market-monitor) were untouched, per instruction — no click needed for those.

## 2026-07-21 — 21 index-unregistered skills: evidence-proportionate backfill (6 confirmed, 14 re-staged, 1 held for Gabriel)

Gabriel-directed follow-up to the 2026-07-21 16:04:58 UTC drift-check correction's 24-item (later 21, after lease-renewal-pipeline/personal-portfolio/website-perfection closed same day) index-unregistered list. Rather than treat every skill as an individual incident, researched actual usage evidence per skill (event_log.md + memory dir) and split by evidence strength — matching the drift-check's own 2026-07-20 recommendation to treat this as a backfill exercise where evidence supports it.

**Backfill-confirmed (6), no re-staging, no new click required — content already hash-clean in cache, and dated usage evidence corroborates the CURRENT version is what's actually running:**
- **exception-detection** v1.2 (`b723118`) — same-day (2026-07-21) log directly confirms `Skill({skill:"exception-detection"})` served v1.2 content matching current commit, with v1.2-specific features (3 new Category 2 rows) verified present. Strongest evidence in the set.
- **deal-execution** v1.2 (`643dd9f`) — `open-items-tracker.md` OI-012: Gabriel explicitly confirmed "all 3 imported (all done)" at commit `643dd9f`, exact match to current repo HEAD, dated 2026-07-17.
- **loi-generation** v1.4 (`643dd9f`) — same OI-012 confirmed-import event, exact commit match.
- **owner-outreach** v1.0 (`5dda2cd`) — 2026-07-21 log entry: real scheduled-run failure/fix touching the pipeline scripts and the skill's own SKILL.md, postdating the commit; OI-012 also confirms repo↔runtime matching at this exact version.
- **disposition-analysis** v1.0 (`e2764e0`) — `deal_1100_rarig_disposition_2026-07.md`: "Ran as a standing portfolio-health check... via the disposition-analysis skill," dated 2026-07-09, postdating the only-ever commit.
- **market-monitor** v1.1 (`35cdbca`) — `markets.md`: Des Moines market-data row sourced "via market-monitor skill v1.1," version token matches current — moderate confidence only, since that entry predates the 07-16 commit by 5 days and can't confirm every feature in that commit was exercised.

**Re-staged (14) — no usage evidence found either way; packaged via `tools/package_skills.py` into session outputs (`.../scratchpad/restage-2026-07-21/`), frontmatter-validated, SHA256-verified against repo, awaiting Gabriel's Save-skill click:** census-acs-extract, conversation-archival, document-assembly, file-reconciliation, fleet-advisory-remediation, graph-app-registration, orphaned-task-forensics, portfolio-growth, portfolio-reporting, rent-comp, communication-intelligence, deal-comparison, legal-intelligence, tenant-intelligence.

The last 4 were initially held pending a surface-architecture question (`reference_skill_surfaces.md` claimed they load via a distinct Code-CLI `anthropic-skills` plugin bundle with "no local SKILL.md," not the individual Cowork Save-skill cache). Resolved same session: this session's own available-skills listing shows the identical `anthropic-skills:` prefix on personal-portfolio/website-perfection/lease-renewal-pipeline — skills already confirmed individually Save-skill-installed earlier today — proving the prefix is a generic Code/CLI namespace label, not evidence of a separate bundle mechanism. Combined with all 4 already being present and byte-matching in the Store B runtime cache, the "no local SKILL.md" claim in `reference_skill_surfaces.md` is stale — it describes the defunct Cowork-workspace-folder sync that document's own 2026-07-21 correction says was superseded by the runtime-cache mechanism. Folded into the standard re-stage batch accordingly. `reference_skill_surfaces.md` should be corrected in a follow-up pass (not done here — read-only investigation only).

**Held (1) — genuinely confirmed open gap, not just a missing log line:**
- **acquisition-underwriting** v4.3 (`34c0094`) — `project_acquisition_underwriting_doctrine_review_2026-07-18.md` explicitly logged this version as "awaiting Gabriel's manual Save-skill click" as of its 2026-07-18 close. Content is already byte-identical in cache (confirmed in this session's full 43-skill sweep) — no repackaging needed, only the click itself, which registers the install event independent of content freshness (same rationale as step 2g / the psa-reconciliation raw-sync precedent). Not yet actioned this session — flagged for Gabriel alongside the 14-skill batch above.

No files modified in ora-skills beyond what package_skills.py wrote to session outputs (untracked, outside the repo). No Save-skill clicks performed by this session — registration remains Gabriel's action per doctrine.

## 2026-07-21 — rent-roll-reconciliation captured into ora-skills repo (PR #22, not yet merged)

Captured from the runtime cache into `C:\Users\Owner\ora-skills\rent-roll-reconciliation\` (SKILL.md + scripts/parse_rent_roll.py + scripts/diff_tenants.py) — the 2026-07-21 ad hoc `ora-skill-store-drift-check` run had flagged this skill CACHE-ONLY with no repo counterpart. Byte-exact copy per the CACHE→REPO RECOVERY PROCEDURE (parcel-data-recovery precedent, PR #20, 2026-07-16): SHA256-verified pre/post-copy (SKILL.md `d684328a...`, parse_rent_roll.py `101969cb...`, diff_tenants.py `86496da9...`). Committed `0b3db80` on branch `capture/rent-roll-reconciliation`, pushed, PR [#22](https://github.com/ZeOoba/ora-skills/pull/22) opened — not merged (Gabriel's review pending, never merging unreviewed per doctrine).

**Pending-reimport ledger false-positive, cleared.** `tools/hooks/post-commit` fired on this commit (as it does for any commit touching a skill's packaged content) and recorded rent-roll-reconciliation in `_staging/PENDING_REIMPORT.md` as "repo ahead of cache, needs reimport." That's incorrect in this specific case: the repo content was sourced byte-for-byte FROM the runtime cache, so cache and repo are already identical — no platform-side change occurred, no Save-skill click is needed. Cleared via `python tools/pending_reimport.py clear rent-roll-reconciliation` rather than leaving a stale pending-reimport signal for a future drift-check or package-and-stage-skill session to act on unnecessarily (the exact class of stale-finding problem root-caused earlier today re: lease-renewal-pipeline/personal-portfolio/website-perfection). The hook's blanket "any skill-content commit → flag for reimport" logic doesn't distinguish a genuine new repo edit from a verbatim cache backfill — worth hardening later, not done here.

**Content note, unresolved:** `scripts/diff_tenants.py`'s docstring cites "the Bay Area Corporation / Bay Area Exteriors case in SKILL.md history," but the captured SKILL.md has no history/changelog section documenting it — flagged in the PR description, not resolved.

## 2026-07-21 — Skill reimport "stale content" traced to async SkillsPlugin sync lag, not a broken cache

Investigated why `Skill({skill: "exception-detection"})` served old v1.1 content in two fresh sessions/agent spawns even though the on-disk SKILL.md (grepped directly) already showed v1.2 and `PENDING_REIMPORT.md` had been cleared after "Save skill." Root cause found in `AppData\Roaming\Claude\logs\main.log`, not in `ora-skills` or any Code-side mechanism: the served base directory (`local-agent-mode-sessions\skills-plugin\<profile>\<id>\skills\`) is a single shared store across all sessions from this app instance, not a per-session copy — confirmed by repeated `[CCD] Using skills plugin at: <same path>` lines across separate session starts. Content only updates there via a periodic `[SkillsPlugin] Starting skills sync` → `Delta: N to download` → `Sync complete` cycle, observed running roughly every 2-10 minutes. "Save skill" registers the update to a remote skill store immediately, but the local file on disk (and therefore what the Skill tool serves) doesn't update until the next sync tick actually downloads it — up to ~10 min later. Confirmed: sync at 13:08:51 showed `Delta: 0` (update not yet visible remotely); sync at 13:11:46 showed `Delta: 1 to download` and completed at 13:11:47, matching the SKILL.md file's CreationTime/LastWriteTime exactly. Any session/agent that reads the Skill tool before that sync tick sees stale content regardless of how "fresh" the session is — this is a race, not a stale in-memory cache that ignores disk changes. Re-tested `Skill({skill: "exception-detection"})` after 13:18:05 (next sync, `Delta: 0`, confirming stable) — now correctly serves v1.2 (3 new Category 2 rows + disambiguated Category 4 row present).

**Systemic implication:** `PENDING_REIMPORT.md` clearing on "Save skill" click is not proof the update is live — it only confirms the registration step, not the sync-to-disk step. Any skill update tested within ~10 min of "Save skill" risks a false "it didn't take" reading. Detail + verification procedure: `memory/reference_skill_reimport_sync_lag.md`.

## 2026-07-21 - package-and-stage-skill workflow-optimization follow-ups: post-commit hook, append-event-log.py, and event_log.md.pending all root-caused
Gabriel asked to "fix all workflow optimizations" flagged at the close of the lease-renewal-pipeline/personal-portfolio/website-perfection install session. Three findings:
1. **Post-commit hook miss for commit 40e5a4d.** Root-cause hunt: tools/hooks/post-commit and pre-commit are both mode 100644 in C:\Users\Owner\ora-skills, but pre-commit still fires reliably (proven live: blocked a malformed test commit). Ruled out the executable-bit theory. Directly ran python tools/pending_reimport.py record 40e5a4d -- it correctly recorded all three skills, proving the record logic itself is sound. Then proved the live post-commit hook DOES fire correctly on this clone today: committed and cleaned up a throwaway _hook-test-scratch skill (2 test commits, fd243a1/eb29889, both tagged "test:"), and the hook fired and recorded on the first passing commit. Conclusion: this clone's hook is healthy; the miss on 40e5a4d most likely traces to a different, since-removed environment (a linked worktree, e.g. the "strange-sutherland" one referenced in this machine's session-memory index, no longer in git worktree list) where core.hooksPath or the shell's python resolution differed. Not independently confirmable post-hoc since that worktree is gone. No code change made -- none was warranted once the mode-bit theory was falsified.
2. **append-event-log.py "undiscoverable."** Wrong-location miss, not a retirement: it lives at ~/.claude/maintenance/append-event-log.py (actively maintained, last touched 2026-07-18, with a live test-append-event-log.py suite), not under ~/.claude/projects/.../memory/ (which only holds session transcripts + the memory *data* files, not the maintenance *code*). Root-caused via reference_memory_scope_fragmentation.md, which names the canonical path directly.
3. **event_log.md.pending directory.** Confirmed active, not cruft: it's the literal spool directory (spool_dir_for() = log + ".pending") append-event-log.py uses when os.replace is blocked by a file-handle lock (see reference_event_log_app_handle_lock.md). Empty = healthy (nothing currently parked), not abandoned.
**Self-correction, same session:** the original install closeout entry was appended via raw .NET AppendAllText (append-event-log.py hadn't been located yet), landing at the tail of the file -- after the 2026-07-18 rollover footer, violating the newest-first convention documented in this file's own frontmatter. A separate, correctly-placed entry describing the same install (titled "Version tokens installed: ...") had since landed properly at the top via another session's proper use of the canonical tool. Removed the misplaced tail duplicate (exact-substring match, verified before and after) rather than leaving two entries for one event. This entry itself is being appended via the canonical append-event-log.py --entry-file path, not manual editing.

## 2026-07-21 — Version tokens installed: lease-renewal-pipeline, personal-portfolio, website-perfection (v1.0 each)

Closed the ora-skill-store-drift-check doctrine gap where these three SKILL.md files had no version token, breaking version-based drift comparison. Repo edit + commit `40e5a4d` (Code session); packaged via `tools/package_skills.py` (single-file skills, no plugin membership). **Gabriel confirmed the Save-skill install click** via Cowork. Runtime cache re-sync verified (EOL-normalized SHA256 match, repo vs `…\local-agent-mode-sessions\skills-plugin\583f08bc…\a6ad2c61…\skills\<skill>\`, post-install mtimes ~12:19 ET, all matching repo content). All three cleared from the post-commit PENDING-REIMPORT ledger (`_staging/PENDING_REIMPORT.md`, now empty/removed). A future `ora-skill-store-drift-check` run should read IN-SYNC for these three.

## 2026-07-21 — ora-owner-outreach-queue-refresh: recurring path defect root-caused and closed across all 3 hosts; staleness heuristic de-coupled from frozen filename vintage

Scheduled run halted at Step 1 with `[FATAL] queue script failed` → `can't open file '...owner_outreach_queue.py'`. Root cause: the 2026-07-05 machine migration nested `Investment Candidates -- 2026` one level deeper under a new `Business\` folder; the 2026-07-11 fix (documented inline in both scripts) addressed a *different* defect — a stray OneDrive `"(1)"` duplicate-folder suffix — and never caught the `Business\` nesting. Patched (with Gabriel's in-turn sign-off) in all three places the path was hardcoded:
- `owner_outreach_weekly.py` — `FOLDER` constant
- `owner_outreach_queue.py` — `_MASTER_FOLDER` constant
- the scheduled task's own `SKILL.md` (Steps 1 and 3's literal `python "..."` invocation) — this is the one that would have kept failing next Monday even with the two scripts fixed, since the harness invokes this path literally.

Swept the rest of the folder's `*.py` (`build_t1_letterpack.py`, `_check_addr_fields_20260712.py`) for the same broken-path string — clean, no other instances.

**This is a recurrence, not a first occurrence.** `send-log.txt` shows an identical ALERT on 2026-07-12 13:16, a "corrected" successful send 8 minutes later, and a broader Cowork Automation Alert at 13:57 flagging 4 tasks including this one. It ran clean on 07-13, then broke again by today with the *identical* defect — meaning the 07-12 correction was very likely a manual override/workaround that session (e.g. an explicit master-path arg), not a persisted edit to the `FOLDER`/`_MASTER_FOLDER` constants: both scripts' content going into today's session still had the bug, and no event_log entry existed documenting a 07-12 fix. Logging this now specifically so the defect can't recur a third time without a paper trail.

**Second, related finding while investigating "no refresh since 06-10":** the master workbook *has* been refreshed — `_v01` through `_v06` all sit in the correct folder, `v02`–`v06` all written 2026-07-12 (archive copies tagged `PREEDIT-cincy10-20260712` indicate a Hamilton/Cincinnati-area SF recovery pass, consistent with parcel-data-recovery's Iron rule 6: new version per pass, never overwrite). But `owner_outreach_queue.py`'s `stale` flag was computed as `(vintage_age > STALE_DAYS) OR (mtime_age > STALE_DAYS)`, where `vintage_age` derives from the filename's frozen `20260610` date prefix — a date recovery passes never rebump. That clause alone pins `stale=True` forever regardless of how fresh the data actually is (confirmed: a same-day-fresh master already read 41d "stale" by vintage). Fixed by gating `stale` on `mtime_age` alone; `vintage`/`vintage_age` still computed and printed (provenance, STANDING RATIFICATIONS matching) but no longer gate the flag. Verified against a disposable fresh-mtime copy of the real master (never touched the pinned master itself) — `STALE=no` with vintage still showing `2026-06-10 (41d)`, confirming the fix behaves as intended.

Doctrine change made: `owner_outreach_queue.py`'s freshness-gating logic (mtime-only). No change to `STALE_DAYS=7` itself, the STANDING RATIFICATIONS mechanism, or the master/ledger data — none of those were in scope or at fault.

## 2026-07-20 — IWNS LLC primary lease verified: escalation date corrected, cannabis-use risk flagged

Gabriel asked to verify the primary lease document for IWNS LLC DBA Jasis Laboratory once available. Located "Lease Suite A1-2 Steven Utieyin Johnson Jr. and IWNS LLC DBA Jasis Laboratory #2 6.17.2026 -- 2203-2207.pdf" (Adobe Sign, Status Signed, Agreement completed 2026-06-22, Gabriel signed for Landlord). Confirms SF 2,400, Suite A1-2, Lease 2026-07-01 through 2031-06-30, Monthly Rent $3,000, Security Deposit $6,000, 3%/year escalation -- all already-written fields matched. **Corrected** Next Escalation Date from 2027-07-01 (a rent-roll-derived estimate) to **2026-10-01** (the lease's actual stated date). **Caveat noted, not resolved**: the Adobe Sign audit trail lists only Gabriel Goldberg as recipient/signer -- Tenant's own signature blocks appear blank in the extracted text, so Tenant-side execution isn't independently confirmed from this document alone. **Material risk surfaced**: this is a cannabis-processing tenant: Sections 5-6 grant Landlord sole-discretion termination rights if Tenant hasn't secured all required cannabis zoning/licensing approvals by September 1, 2026 -- the lease's own text notes current Salisbury zoning restricts this use and may or may not be amended in time. Written via notion-update-page, verified via fresh fetch. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — OI-023 closed: IWNS LLC DBA Jasis Laboratory added to Notion

Gabriel confirmed adding the tenant found missing during the rent-roll reconciliation. Created via `notion-create-pages`: Tenant Name "IWNS LLC DBA Jasis Laboratory", Tenant Legal Entity Name "IWNS LLC", Property Address 2203-2207 Northwood Dr -- Salisbury MD, Suite A1+A2, 2,400 SF, $3,000/mo, Lease Status Active, Primary Contact Steven Johnson, Lease Start 2026-07-01, Lease Expiration 2031-06-30, Next Escalation Date 2027-07-01, Escalation Percent 3%. All fields sourced directly from the rent roll (no primary lease document read yet). Assigned Tenant ID ORA-T-299, verified via fresh fetch. Closes OI-023. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — Rent roll reconciliation residual spun off as OI-023

Gabriel asked to check open-items-tracker.md for any lingering rent-roll gaps after the reconciliation. No tracker entry existed for the reconciliation's residuals yet. Investigated the one genuinely unmatched rent-roll row: IWNS LLC DBA Jasis Laboratory ($3,000/mo, 2203-2207 Northwood Suite A1+A2) -- confirmed via `notion-search` (no result) that it has zero Notion Tenant DB record, unlike the 4 tenants restored earlier this session which existed but were mistakenly retired. Lease Start of 2026-07-01 suggests a genuinely new, not-yet-onboarded tenant. Not written -- opened as OI-023 pending Gabriel's go-ahead. Also confirmed the other unmatched rent-roll rows (Hobart Services, Masala Bazaar/XPO Foods, Green Home Solutions) are naming variants only, not real gaps -- rent already matches Notion exactly. Detail: `open-items-tracker.md` OI-023.

## 2026-07-20 — Portfolio-wide rent roll reconciliation: 4 tenants restored, systemic escalation-drift fixed (60 rows)

Gabriel asked to check the 7/20/2026 Rent Roll for discrepancies against the Notion Tenant Database, then to update Notion to match. Reconciled all 137 rent-roll rows against 160 non-retired Notion rows (SQL query mode hit the same free-plan quota wall documented in reference_tenant_db_completeness_gap.md mid-pull; page IDs for the write pass were gathered via `notion-search` instead, which was unaffected). Findings and actions:

- **4 real, currently-paying tenants had zero live Notion record**: Bay Area Exteriors LLC (29000 Info Ln #502+503, $3,700/mo), Eastern Shore Karate & Fitness LLC (#306, $1,802.50/mo), Palmer's Plumbing LLC (#301+302, $3,069.76/mo), and Scarlet Covering Inc. (1900 N Broadway #100, $10,790.41/mo) -- all four were retired 2026-07-17 (OI-009) as duplicates of an "already-correctly-resolved" counterpart that, on inspection, either never existed or was itself archived/retired. Restored all 4: un-retired, corrected Property Address/Suite/Unit to match the rent roll, updated Palmer's Plumbing's stale rent. Combined ~$19,363/mo (~$232K/yr) of real rent now visible again in the active roster.
- **Systemic Escalation Percent corruption, 9 rows**: values like 11.66, 130.05, 36.06, 164.7975 (should be 0.03-0.06 range) -- a recurring data bug, not isolated typos (same class as Childs Play Diesel Performance, fixed earlier this session). Corrected 8 to the rent roll's sane value; Baltimore Dialysis/Fresenius's rent-roll value was itself nonsensical (-0.0001) so that field was cleared to null rather than filled with garbage.
- **Systemic stale post-escalation rent, ~40 rows**: Notion's Monthly Rent and Next Escalation Date were exactly one escalation cycle behind the rent roll for a large share of the portfolio -- the same root cause as the I Dig Ditches correction earlier this session, just never rolled forward in Notion when escalations actually fired. Bulk-corrected via `notion-update-page`.
- **Exceptions NOT applied mechanically**: Maryland Hospital Association's rent-roll lease-end (2027-05-31) was left alone -- conflicts with the fully-executed PDF Gabriel supplied and confirmed this session (2027-06-30), and a signed document outranks a rent-roll spreadsheet. Upgraded Roofing's SF/Lease Start/Lease Expiration were left alone -- conflict with an executed lease + estoppel verified earlier this session; only its rent-drift figure (already primary-doc-consistent) was left as-is since no diff existed there. Gator Roofing's SF/Lease Start/Lease Expiration were excluded for the same reason, but its Monthly Rent/Next Escalation Date were corrected (consistent with the well-understood drift pattern). Granite Tops' Monthly Rent was corrected to the rent roll ($7,496, resolving a previously "unexplained" figure) but its Lease Expiration/Next Escalation Date were NOT reverted to the rent roll's stale values -- those fields carry Gabriel's explicit 2026-07-31 vacate-date confirmation from earlier this session.
- 60 total `notion-update-page` writes (4 restorations + 56 corrections). Spot-verified via fresh fetch: both restorations, the nulled Baltimore Dialysis field, and the Granite Tops exclusion all confirmed correct.

## 2026-07-20 — I Dig Ditches (Gyurcsik Construction) rent corrected for uncounted escalation (OI-009 sub-item)

Gabriel corrected the Monthly Rent written earlier this session: current base rent is $1,147.36, not the $1,113.94 taken directly from the executed addendum. The addendum's $1,113.94 figure was only effective as of 4/1/2025 (Lease Year 3); the 3%/year escalation clause meant one more step-up was already due by 4/1/2026 (Lease Year 4, which we are now past) -- $1,113.94 x 1.03 = $1,147.36, reconciling exactly with Gabriel's figure. Corrected `Monthly Rent` to $1,147.36, set `Last Rent Increase Date` 2026-04-01 and `Next Escalation Date` 2027-04-01 via `notion-update-page`, verified via fresh fetch. Detail: `open-items-tracker.md` OI-009.

## 2026-07-20 — Childs Play Diesel Performance escalation fixed, I Dig Ditches identity/dates added (OI-009 sub-item)

Gabriel supplied two executed documents directly. **Childs Play Diesel Performance**: the full executed lease (DocuSign, term 4/1/2026-3/31/2029) shows a fixed 3-tier dollar rent schedule (Yr1 $2,100/mo, Yr2 $2,350/mo, Yr3 $2,600/mo), not a flat annual escalation -- the prior `Escalation Percent` of 23.5 was ~(2600-2100)/2100=23.8%, the cumulative 3-year growth mistakenly entered as an annual rate. Corrected to 11.90% (the Yr1->Yr2 rate); `Next Escalation Date` corrected from 2026-04-01 (commencement date, not an escalation) to 2027-04-01; `Tenant Legal Entity Name` added (Ian Blake Childs DBA Childs Play Diesel Performance); full schedule documented in Notes. Monthly Rent ($2,100) confirmed already correct -- still Year 1. **I Dig Ditches**: Gabriel identified the tenant as Gyurcsik Construction; a fully-executed addendum (Adobe Sign, 2025-01-23) confirmed Christopher J. Gyurcsik trades as I Dig Ditches. Wrote `Tenant Legal Entity Name` (Gyurcsik Construction), `Lease Start` (2023-04-01, Prime Lease date), `Lease Expiration` (2027-03-31), and `Escalation Percent` (3%/year from Lease Year 2) -- this row previously had neither date set. Monthly Rent ($1,113.94) already matched, no change. Both written via `notion-update-page`, verified via fresh fetch. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — Granite Tops: AR collection flag added ahead of move-out (OI-009 sub-item)

Gabriel asked to check the AR balance on Granite Tops given the confirmed 2026-07-31 vacate date: $180.19, aged 90+ days (per the 2026-07-15 AR data pull). Added a collection flag to the row's `Notes` via `notion-update-page` — the balance becomes materially harder to collect once the tenant is out and the lease relationship ends; recommended the PM collect or apply against the security deposit at or before move-out. Verified via fresh fetch. No tracker change (informational addition to an already-closed OI-009 sub-item).

## 2026-07-20 — ora-cc-schematic-refresh (Rev 2026-07-20a): fleet verdict flipped OK→ATTENTION

Scheduled Mon-cadence refresh of the Claude Code System Schematic artifact. Material changes vs rev 2026-07-18d:
- **Fleet VERDICT ATTENTION** (was OK): 13 throttle-skip events in the last 24h (ora-deal-aging-sla=5, automation-health-monitor=3, check-github-support-ticket-4584520=3, ora-deal-command-board=1, ora-sofr-direct-prefetch=1) + **1 new same-time collision at 09:20** (ora-site-exposure-probe ∥ ora-deal-aging-sla, both cc weekday-morning). 0 overdue, 0 missed/stuck. Candidate fix if the 09:20 overlap recurs: shift one task by 5–10 min.
- Fleet enabled 43→44 (cc 22→23, lams steady 21); 3 disabled = spent EXPIRED one-time entries.
- **ora-pm repo dirty→clean** (rev-d WIP committed/cleared by its owning session), HEAD 1b304e8; oxford-command-center clean @1cb8f1a.
- memory-integrity now shows 2 present-but-unlisted files (project_plan2_effect_verification_design_2026-07-18.md, project_setup_improvement_top5_plan_2026-07-18.md) — non-fatal, index pointers owed by the authoring session.
Probes otherwise green: governor-drift exit 0 (774 files), doctrine-integrity exit 0, confidentiality-guard 131/131. enabledPlugins unchanged (12 true).

## 2026-07-19 — OI-015 closed as verified-clean (no history purge needed); real residual found and spun off as OI-022

Gabriel asked to close out the ora-appsec-sweep's OI-015 finding (real E. Fulton deal terms allegedly "still in git history on the remote" for ora-pm) and investigate the theoretical residual further, implementing whatever solution followed.

**OI-015 closed, not fixed by a purge — the original finding was wrong.** A completely fresh clone directly from github.com/ZeOoba/ora-pm (bypassing any local object cache) shows commit `c4c69a8` already contains only placeholders, and `git log -p --all` across every reachable commit/branch in that fresh clone returns zero matches for any real E. Fulton term variant. The reachable, clonable, browsable history is genuinely clean — no rewrite or force-push was needed or performed. The original sweep finding (and fix-commit `866480f`'s own note) were based on a stale signal: a local dangling/unreachable blob mistaken for "still in history."

**Real residual found and confirmed, spun off as OI-022:** that same blob (`39b02f4585cc6357876423d04d5c3fcee65793b0`) IS still directly retrievable via GitHub's Git Data API — confirmed via `gh api repos/ZeOoba/ora-pm/git/blobs/<sha>`, which returned the actual content. Root cause: `refs/pull/2/head` (a GitHub-internal ref for the closed/merged PR #2 that originally carried the sensitive commit) keeps the object alive server-side, independent of what happens to `main`'s history. These refs cannot be deleted by the repo owner via git push, the API, or repo settings — no self-service mechanism exists. The only documented fix is a GitHub Support request. Drafted the full request text (repo confirmed private, 0 forks via API) at the scratchpad path recorded in OI-022; submitting it is Gabriel's action (outbound third-party request), not something this session executes.

Not a live-credential emergency (E. Fulton declassified 2026-07-09), but a real, low-probability residual exposure path worth closing via the support request when Gabriel has a moment.

## 2026-07-19 — PR #222 (Debt & Maturity Module v1) merged — both Invariant-4 blockers resolved via direct workbook read + Gabriel ratification

Closes out the last open item from the 2026-07-18/19 next5-improvements round (N3).

- **Workbook column mapping resolved by direct read, not guessed** (commit `53c8ea3`): opened the live Master Workbook's Loan Index + External Loans Summary sheets. LTV confirmed per-loan balance/collateral-value (Loan Index's `ltv` cell is literally `='External Loans Summary'!O_`, that column's own header reads "LTV (Balance/Value)") — validates the module's existing single-active-loan aggregation as correct, not a guess. Rate-type/next-rate-reset confirmed **absent from the workbook entirely** — full header scan of both sheets found exactly one rate field anywhere ("Annual Rate"); migration 023's two columns stay NULL because there is nothing to map, not because of an unresolved question.
- **Refi-window thresholds (12/24-month) ratified by Gabriel, "approve as-is"** (commit `4bbb2d4`) — constants unchanged, doc comments now record the ratification so a future reader doesn't re-flag them `[SPECULATIVE]`.
- **Merged:** squash commit `1cb8f1a` on `oxford-command-center@main`, branch deleted (remote + local). Independent Fable review (APPROVE-WITH-NOTES) stands as the pre-merge record; 233 files/2865 tests green throughout, re-verified after each of the two follow-up commits (31/31 debt-maturity suite + tsc clean post-ratification).
- **Residual, not blocking:** the 65% per-property refi ceiling still isn't DB-backed/ratifiable like the other two governors (`ALERT_THRESHOLDS.ltvCeiling` in `conditions.ts`, self-labeled "non-governor thresholds") — flagged for a future governor-consolidation pass, not this module's scope.
- **v2 follow-ups on record** (not built): wire `/timeline` + `/refi-windows` into `ora-am-brief`/`ora-monthly-portfolio-briefing`; rate-type/reset ingestion if Gabriel ever adds the workbook column or an alternate source; true multi-loan combined-LTV (needs per-loan implied-value reconciliation, not a blocker for v1's conservative single-loan-only approach).

## 2026-07-19 — Next-5 improvements round: 2 crashed agents recovered mid-flight, all 5 completed (chip next5-improvements-2026-07-18, Code/02323ec2)

Same F-id-dossier-adjacent discipline as the architecture-refresh (independently verify before trusting, resume don't rewrite when real partial work exists). Two of five subagents (N2 sourcing-data, N3 debt module) were cut off mid-implementation with no final report — investigated for orphaned work before re-running rather than blindly restarting, per `feedback_verify_subagent_safe_claims`.

- **N1 — deal-unblock drafts (3 requested):** 2040 S Hamilton OM request and 275 Old County Line diligence list drafted to Outlook Drafts + deal folders, grounded on live deal-folder/Notion state, nothing sent. **754 Old State Route 74 PSA-revision memo was built on a stale premise** (the original setup-review's "counsel non-responsive since 6/11" framing) that a 2026-07-17 Gabriel correction in `projects.md` had already overturned (Eric negotiating PSA directly). Caught by cross-checking memory before presenting the deliverable; both the memo file and the Outlook draft were discarded (soft-deleted, recoverable) on Gabriel's explicit choice.
- **N2 — sourcing-data upgrades:** first attempt crashed with zero trace in its target dirs; second attempt discovered a genuine orphaned worktree (`ora-skills/.claude/worktrees/next5-sourcing-data`, real partial SKILL.md edits) that my own initial "is it lost" check had missed (checked file mtimes, not `git worktree list`) — resumed and completed rather than restarted, avoiding a collision the resuming agent itself correctly detected and halted on first. Built `county-parcel-screen/references/county-endpoints.v1.json`, a live-verified ArcGIS parcel/CAMA registry across all 22 documented counties (19 VERIFIED, 2 VERIFIED-PARTIAL, 2 honest NOT-FOUND); caught 2 real endpoint drifts (Dane Co WI service rename, Kent Co MI now token-gated) and one accuracy issue (MD registry is point geometry, not polygon — insufficient for the pad/yard split; fixed the flood-zoning-dd cross-link text to say so). Real drive-time routing (OpenRouteService keyed → keyless OSRM public server, live-verified → straight-line last resort) added to submarket-spatial-analysis, each tier honestly labeled. Pushed: `ora-skills#next5-sourcing-data` (b5ad834) and `ora-claude-config@main` (b982a47, county-parcel-screen registry only). Still needs: package-and-stage-skill + Gabriel's Save-skill click before either ora-skills change reaches the Cowork cache.
- **N3 — debt & maturity warehouse module v1:** first attempt left real, high-quality partial code uncommitted in `oxford-command-center/.claude/worktrees/next5-debt-module` (based on ef9e73e, before main advanced 7 commits). Resumed rather than discarded — independently re-reviewed every existing line rather than trusting the draft. Its own adversarial refute pass caught a real NaN-comparator determinism bug in the timeline sort (two same-key events, e.g. two demand-callable loans, produced `Infinity - Infinity = NaN`); fixed and proven load-bearing. Merged cleanly with main's 7 intervening commits. Full suite 233 files/2865 tests, typecheck, lint all green. **Independent Fable-tier review (financial-decision code, reviewer ≥ implementer per house doctrine): APPROVE-WITH-NOTES** — reproduced every number from scratch, ran 9 of its own adversarial edge cases, confirmed governor-read discipline (DSCR 1.25/LTV 0.40/0.65 read-only, never redefined), confirmed the multi-loan-property guard genuinely excludes rather than silently picking a value. One architectural note surfaced (the 65% per-property refi ceiling isn't DB-backed/ratifiable like the other two governors — pre-existing gap, not introduced here, worth a future consolidation pass). Pushed `oxford-command-center#next5-debt-module` (b09995e); opened **draft PR #222, titled DO NOT MERGE**, listing every blocking confirm (workbook column mapping ×2, ratify the [SPECULATIVE] 12/24-month refi-window thresholds) — awaits Gabriel per Hard Invariant 4.
- **N4 — oxfordra.net site fixes:** async-CSS pattern fixed on 5 pages (not the originally-briefed ~10 — verified live), LinkedIn Insight placeholder stripped from 16 files (not 62 — that count had drifted), dead `snap.licdn.com` CSP entry flagged but not touched (blast-radius). Isolated worktree branch `website-canonical#next5-site-fixes` (2451873), build/JSON-LD/local-render all verified. **Committed, deliberately NOT pushed** (Hard Invariant 2 — oxfordra.net always needs explicit per-deploy confirmation; a push risks triggering Netlify).
- **N5 — financial-skill cache verification:** read-only. monthly-close repo↔Cowork-cache byte-identical (Restoration Church Trust ~$983K balloon alert, due 2027-02-20, confirmed intact in both). Surfaced two real gaps, neither actioned this pass: `cash-position-monitor` is entirely absent from the Cowork cache (repo-only, never synced); the drift-check scheduled task's last registry-recorded firing (07-13) has no matching Notion output — only the 07-16 manual run posted results, meaning the automated cadence may be silently under-reporting even when it fires.

**Coordination:** ran alongside the concurrent `setup-improvement-top5-2026-07-18` session (5 different plans, completed same evening — flywheel merged, appsec sweep landed dependency-security fixes now visible on oxford-command-center main) without collision; every write this round was pathspec-scoped and verified against `git status`/`worktree list` first, catching one real foreign-staged-file risk (`commit-provenance-guard.py` blocked a bare `git commit` that would have swept another live session's staged `open-items-tracker.md` edit).

**Not yet actioned, Gabriel's call:** PR #222 merge (debt module) · PR (unopened) for `next5-sourcing-data` Save-skill reimport · website-canonical branch push/preview-deploy · cash-position-monitor Cowork resync · drift-check cadence-reporting gap.

## 2026-07-19 — Restoration Church Trust note: Notion tracker mislabels corrected; borrower repayment/extension terms remain unconfirmed; HubSpot renewal pipeline stall root-caused

Investigated Gabriel's Restoration Church Trust flag (read-only research agent, then direct Notion corrections). Confirmed via Loan Portfolio Tracker + Covenant Watch history + the 2026-07-18 EOD Action Ledger: Oxford Capital Partners is the LENDER, Restoration Church Trust the borrower, on an originally-~$2.0M IO note at 9.00%, balloon maturity 2027-02-20 (confirmed matches Gabriel's own figure; a mid-session relay of this date as "2026" in an internal sub-agent prompt was this session's own transcription slip, not a data error — corrected before reaching any output). Current balance per the freshest source (Jul-18 EOD Ledger): $979,772, matching Gabriel's figure exactly.

Found and fixed the mislabel in 4 live Notion tracker rows (NOT the dated historical snapshot pages like "Covenant Watch — April 2026" or "Debt Snapshot," which were left untouched as point-in-time records): Loan Portfolio Tracker's "Restoration Church Trust Balloon" row, and 3 rows in the Critical Deadlines Tracker. All previously read "Begin refi/payoff planning" (borrower-side framing, wrong direction) — corrected to lender-side framing matching the already-fixed conditions.ts language (confirm the borrower's repayment/extension intent, not an Oxford-side refinance action). Also found and fixed an independent, unrelated data bug on all 3 Critical Deadlines Tracker rows: the "Counterparty" field said "Oxford Capital Partners" (i.e., Oxford itself) instead of "Restoration Church Trust" (the actual counterparty) -- corrected on all 3.

**Confirmed still unresolved, needs Gabriel's own action:** no record anywhere (Notion, event_log.md, deal-decision-ledger.md) of any borrower-side conversation about repayment intent or extension terms. The April 2026 Covenant Watch report called for "lender conversations by June 2026" -- that deadline passed over a month ago with nothing logged since. Recourse and prepayment-penalty fields are also blank in the Loan Portfolio Tracker. This needs Gabriel's direct outreach or explicit instruction to draft one (outbound counterparty communication -- Hard Invariant 1, not something to initiate unprompted).

**HubSpot renewal-pipeline stall, root-caused (read-only, not fixed):** 50 deals sit in the Lease Renewals pipeline's `appointmentscheduled` stage. 49 of 50 were created in the same ~3-minute window on 2026-03-27 (the 50th, 2026-04-29) -- strong evidence of a one-time bulk import with no downstream stage-advancement automation ever wired up, not an active process that stalled. ~38 of 50 show zero activity since creation. Nearly all share one hubspot_owner_id. One of the 50 is "Lease Renewal — Restoration Church Trust" ($16,714) -- the same mis-entered-loan-counterparty error already corrected in the Notion Tenant DB (OI-009, 2026-07-17) appears to have been carried into HubSpot too; flagged for a retirement decision, not retired here (a live CRM record, Gabriel's call). No property/market/PM-platform field exists on the HubSpot Deal object, so the stall can't be broken down further from CRM data alone -- needs the lease-renewal-pipeline skill's own batch pass once Gabriel sets terms, per his original note.

Detail: OI-021 (open-items-tracker.md).

## 2026-07-19 — ora-cowork-heartbeat write-auth: root cause confirmed, fix requires Gabriel's own manual UI approval (not reachable from any automated session)

Investigated Gabriel's "Cowork heartbeat write-auth is the highest-priority infra fix" flag (read-only, general-purpose agent). Root cause: the LAMS registry entry for ora-cowork-heartbeat has no approvedPermissions grant, unlike sibling tasks that write Notion successfully (e.g. automation-health-monitor carries 8 grants including a Notion page-create grant). This has been documented 3x already (07-16/17/18) and remains unresolved. The task's own SKILL.md claims "tool-grant re-approved 2026-07-17," but a manual "Run Now" UI approval does not persist the same grant that live cron-time approval does -- so the claimed fix did not actually hold.

Current live status is NOT currently blind: the heartbeat's Notion page shows an update as of 2026-07-19T15:54:52Z (~20 min old at investigation time), matching the registry's lastRunAt. But that fire time (11:54 ET) doesn't align with either scheduled slot (05:50/17:50 ET) -- almost certainly another ad-hoc "Run Now," not proof the unattended cron path is fixed. The next genuine unattended fire remains at risk of the same silent-write failure (dispatch succeeds, lastRunAt advances, the actual write never lands -- the exact failure mode documented in [[reference_scheduled_task_approved_permissions.md]]). The GitHub watchdog issue tracking this ("silent for 22.8h") is still OPEN off a stale read and needs manual closure once the fix genuinely holds, not before.

**Structural finding, stronger than the general CC/LAMS write asymmetry:** no MCP tool on EITHER surface (Code/CC or Cowork/LAMS) can write an approvedPermissions grant -- this is UI-approval-only. The only fix is Gabriel personally clicking through the Notion-tool approval prompt in Cowork's own Scheduled Tasks UI during a live unattended fire (a manual "Run Now" does not exercise the same approval path). No automated session, on any surface, can do this. Flagged in OI-020 (open-items-tracker.md).

## 2026-07-19 — conditions.ts balloon-alert direction bug: already fixed 2026-07-16 (PR #217), no code action needed

Gabriel flagged "conditions.ts / Master Workbook balloon-alert direction bug (fires refi/payoff on lender notes)" as an open item. Checked the live code first rather than assuming the report was current: src/analytics/conditions.ts already splits on `l.direction` (borrower vs. lender vs. internal) -- `direction === 'lender'` produces a distinct `note-maturity-*` alert ("Oxford is the lender — confirm the borrower's repayment or extension terms"), capped at severity 'warning' (never critical, since inbound capital isn't an emergency), while `direction === 'borrower'` keeps the original refi/payoff copy. This shipped in commit dd424c2 (PR #217, "fix(analytics): stop telling Gabriel to refinance a note Oxford holds"), merged to main 2026-07-16 -- 3 days before this session. Confirmed server/brief/run.ts (the email Daily Brief generator) imports and calls this same evaluateConditions() -- no separate/duplicated alert-text path -- and confirmed ora-am-brief's own SKILL.md sources its critical-dates section from this exact oxford-command-center alerts-engine output (portfolio.json / Command Center Daily Brief), not an independent computation. So both the in-app Command Center and the emailed Daily Brief already carry the corrected lender-framing text.

**What remains, NOT code:** the Master Workbook's own balloon-alert row (an Excel cell/note inside the live SharePoint source-of-record document) still carries the old borrower-framed "Prepare refinance or payoff strategy" label. No code in this repo reads that label through verbatim -- conditions.ts generates its own alert text independently -- so there is no pass-through bug to fix here. This is a data-content correction inside the live financial source-of-record workbook, which needs Gabriel's own edit (or his explicit go-ahead + the exact sheet/cell location) rather than an unprompted assistant write to that document.

**Lesson (ties to [[feedback_verify_before_repeating_session_claims]]):** a second instance in the same session of a punch-list item being stale relative to the actual code/branch state -- check `git log -- <file>` before treating a described bug as still-open.

## 2026-07-19 — HubSpot Acquisitions-pipeline visibility gap: PR #221 shipped, corrects 2026-07-18's "no code changes needed" call

Re-investigated the 2026-07-18T18:29 finding (HubSpot -> acq_candidates sync gap) from Gabriel's in-turn "fix this" request. That prior session's conclusion -- "No code changes needed once the token is set; the sync is already tested and ready" -- was half right: syncHubSpotPipeline()/POST /acq/sync/hubspot (PR #203) is indeed fully built and tested. But it checked only the token; it never diffed the frontend. AcquisitionsModule.tsx has always had a "Sync from Notion" button (handleNotionSync, wired since PR #153) -- PR #203 shipped the backend HubSpot route but never added its counterpart button. With no UI trigger and no scheduled caller anywhere in the repo or the scheduled-task fleet, the route was structurally unreachable even once a token exists.

Fixed via TDD in worktree fix-acq-hubspot-sync-button (confirmed red against pre-fix code, 5/5 failing; implemented handleHubSpotSync() + "Sync from HubSpot" button mirroring the Notion pattern exactly; local code-reviewer pass found one test-quality gap, fixed). Full gate green: typecheck 0, lint 0, 232/232 test files (2834 tests). PR #221 opened (not merged -- Gabriel's call).

Re-confirmed live via HubSpot MCP: same 4 real deals as 2026-07-18 (6150 Avery Road, 1333 Research Road, 2146 Enterprise Pkwy Twinsburg OH -- still untracked anywhere in projects.md/deal-decision-ledger.md/event_log -- Pendleton Trade Center), plus the 5th legacy/terminated deal at a stale HubSpot stage (unchanged, not touched, this repo's own confidentiality guard blocks naming it here).

**Lesson for [[feedback_verify_before_repeating_session_claims]]:** a prior session's "no code changes needed" is a claim about what THAT session checked, not a verified absence of gaps -- it hadn't diffed the frontend against the backend PR. Re-verify the actual diff/git history, not just re-read the conclusion, before treating a "nothing to fix" finding as closed.

## 2026-07-18 — oxford-command-center: NOI/value/rent reconciliation now live, not CI-only

Closed a real gap flagged in ora-intelligence-platform-master-plan.md: reconcile-runtime.ts (the always-on brain.refresh() check feeding the Health module's Reconciliation card) only verified snapshot-internal invariants -- the cross-check against the workbook's own declared "Portfolio Total" row (NOI/value/rent) lived only in scripts/reconcile.ts, the CI-only gate that does a second independent workbook read. reconcile-runtime.ts's own doc comment explicitly named this as the intentional scope split.

Extended parse.ts to capture that row's NOI/Value (Property NOI cols 13/10) and Annualized Rent (Master Tenant Rent Roll col 14) during the SAME single read that already skips it from the per-entity lists -- zero extra I/O. Added snapshot.workbookTotals (nullable per-field, defaults to null for legacy payloads/workbooks with no such row). reconcile-runtime.ts now cross-checks derived sums against these, plus a cash-history-latest-vs-current check that needed no plumbing at all. TDD (tests added to parse-workbook.test.ts + reconcile-runtime.test.ts), full gate:ci green (typecheck/lint/2819 tests/build/bundle-budget), and separately re-verified npm run reconcile against the REAL production Master Workbook (all values match).

Mandatory adversarial REFUTE pass (financial-adjacent code) found one genuine defect before commit: the portfolio-total-row capture had no first-match-only guard, creating last-match-wins semantics inconsistent with reconcile.ts's own find() helper (which returns on first match) -- dormant today but a real latent fragility if a second matching row ever appeared. Fixed (first-match-wins in both parseProperties and parseLeases) with a regression test (two matching rows, asserts the first is kept), re-verified full gate green + real-workbook reconcile clean again.

Committed 33c9aa6, pushed, GitHub Actions CI green (gate job; refute-required correctly skipped -- PR-only trigger, doesn't fire on a direct main push, and the REFUTE pass was performed manually per this org's doctrine regardless).

## 2026-07-18 — HubSpot Acquisitions-pipeline visibility gap: verified live, precisely scoped, reported to Gabriel

Verified directly against live HubSpot data (Notion/HubSpot MCP connectors came online mid-session): oxford-command-center's HubSpot -> acq_candidates sync (PR #203, commit de23c8f, tested) is fully built and gracefully handles a missing HUBSPOT_TOKEN (400, not a crash) -- but the token was never set in .env, so acq_candidates has 0 rows. Queried HubSpot directly: 4 real deals sit in the Acquisitions pipeline (885606973) -- 6150 Avery Road (Sourced), 1333 Research Road (Screened), 2146 Enterprise Pkwy Twinsburg OH (Screened), Pendleton Trade Center (Screened) -- plus E Fulton Street (Due Diligence stage, but that's the already-declassified/terminated deal; HubSpot's stage just hasn't been updated to reflect that, a separate lower-priority item).

**Real finding: 2146 Enterprise Pkwy, Twinsburg OH does not appear anywhere in projects.md, deal-decision-ledger.md, or recent event_log entries** -- sitting in HubSpot's Screened stage since 2026-03-22, touched 2026-07-17, with zero corresponding awareness in the memory system. Flagged prominently to Gabriel rather than silently noted.

Sent a report to ggoldberg@oxfordra.net only (send-log confirms OK, 2026-07-18T18:29:06-04:00) with the precise deal table and the exact unblock step (add HUBSPOT_TOKEN to oxford-command-center/.env -- a credential, not something to be entered by an assistant). No code changes needed once the token is set; the sync is already tested and ready.

## 2026-07-18 — systematization-candidates branch PARKED (Gabriel-directed), not merged

Investigated for a possible merge to unblock Plan 2 of the setup-improvement effort. Of its 3 substantive changes: (1) `hooks/ora-autonomy-gate.py`'s OVERRIDE_DIR test-seam fix is **obsolete** — main's 2026-07-17 refactor deleted the bare `OVERRIDE_DIR` constant entirely in favor of the shared `hooks/lib/override_tokens.py` module (`Tier`/`token_grants`/`token_path`); merging the branch's version would partially revert that adversarially-reviewed hardening. (2) its `.gitignore` addition for `maintenance/_state/doctrine-status.json` is **redundant** — main already ignores that path (line 105, landed via a different commit). (3) `agents/deal-recon.md` is already identical on main. Only `maintenance/model-currency-probe.py` (+ test) is genuinely new and non-conflicting, but not merged this pass per Gabriel's explicit choice to park rather than cherry-pick.

**Decision: parked, not merged.** Branch/worktree left as-is at `.claude/worktrees/systematization-candidates` (430bf19) — do not re-attempt a wholesale merge without re-checking `hooks/ora-autonomy-gate.py` against whatever the current override-token architecture is by then, since it may drift further. If `model-currency-probe.py` is wanted later, cherry-pick that one file only.

Plan 2 (effect-verification layer) was NOT actually blocked by this branch's unmerged state in practice — main's `.gitignore`/`_state` untracking convention already independently satisfies the compatibility concern that motivated waiting on it.

## 2026-07-18 — Open-sessions board dispatched; 10 items decided

ora-open-sessions-board 2026-07-18 17:00 ET run: probed 292 unarchived sessions, 10 actionable items reached the board (7 NEEDS-ANSWER, 3 INTERRUPTED; 18 excluded as fleet runs / already-decided-and-unchanged / sub-30-min). Notion deal-stage reconciliation ran clean (0 transitions). Gabriel's decisions:

- **Punch-list tracker "finish this" ask** (local_d0909d82) — Drop, nothing to finish.
- **Northwood tenant-row fix commit** (local_ba9fbd75) — Leave the hunk uncommitted for the consolidation pass rather than isolating and committing now.
- **Midwest expansion (Dayton/Fort Wayne/Omaha) target-markets.json draft** (local_54410484) — Not yet.
- **package-and-stage-skill branch push/PR** (local_46a56789) — Wait; branch stays local, unpushed.
- **Cowork EOD verification monitor midday check** (local_1f5d6000) — Drop; no second checkpoint added.
- **acquisition-underwriting v4.0 upgrade prompt** (local_4eedbc94) — Drop; prompt stays in outputs/, not run in Code.
- **Newsletter archive link-list save folder** (local_c7eb8de7) — Confirmed: Investment Candidates 2026 (its current location; no move needed).
- **Cornerstone Tours SEO audit DOCX formatting QC** (local_95a563f2) — Drop; deliverable stands as-is, no further formatting pass.
- **MEMORY.md lines 84-85 over-length trim** (local_b5d10619) — Drop; left over the 150-char policy cap, non-blocking.
- **Catfish Court, WI (5515 Catfish Court) IC decision** (local_71295051) — Wait; LOI at $2,742,267 vs. Pass not decided. Notion Stage stays "Candidate" — no ledger row (not a terminal disposition).

All ten sessionIds upserted into answered.json. No outbound counterparty communication triggered by any of these decisions.

## 2026-07-18 — Architecture-refresh: 3 standing artifacts refreshed + G-batch executed (chip architecture-refresh-2026-07-18, Code/02323ec2)

Fable-planned, Gabriel-ruled (interactive batch, all recommendations accepted), executed same session under the chip claim. Evidence dossier: `00_Governance/outputs/2026-07-18_Architecture-Refresh_FactsDossier_v01.md` (F-01..F-29); plan: `2026-07-18_Architecture-Refresh_ImplementationPlan_v01.md`.

- **Artifacts republished same-URL after a Fable cross-artifact refute pass (PASS-with-edits, 10 defects fixed pre-publish):** schematic → REV 2026-07-18d (probe suite green: governor-drift exit 0/682 files, doctrine-integrity 8/8, memory-integrity 112/112, confidentiality-guard 131/131; fleet VERDICT OK 43 enabled = 22 CC + 21 LAMS) · review-v02 (closeout matrix evidence-upgraded: 0.C and 4.1 → Closed; 12/34 closed) · setup-audit (new "Observations for the 2026-09-15 audit" section — documented, deliberately NOT executed per the frozen cadence).
- **Producer-clobber repaired:** the schematic's durable source (`~/.claude/artifacts/claude-code-schematic.html`) had silently diverged from the published artifact by two revisions (source rev 07-16 vs artifact rev 07-17c) — Monday's ora-cc-schematic-refresh fire would have wiped revs b+c. Source synced to rev-d; WebFetch post-verify confirmed all 3 URLs serving new content.
- **Roster-undercount root-caused:** registry-membership-probe.py omits enabled future-fireAt one-time tasks → session-context showed LAMS 19 vs live 21 (ora-cam-data-backfill @08-15, ora-counsel-review-standard-positions @08-03). Documented for the 09-15 audit; probe not modified.
- **G-A router fix LANDED (L2: fixtures-first, tests green):** engineering-router.py no longer suggests L7 on research/plan/"do not code" prompts and no longer scans system-notification text for the confidential-cloud-review DOCTRINE BLOCK (3 live misfires 07-18 were the fixtures). Root causes: substring "ship/deploy" match + L7-first sort; unconditional prompt-field scan. hooks/tests/test-engineering-router.py extended (7 assertions incl. 2 regressions); ALL PASS, re-verified independently by the orchestrator.
- **G-E retire flow:** 4 spent one-time tasks (heartbeat-beacon-recovery-check, heartbeat-check-backup-verify, ora-setup-review-closeout-recheck, ora-uw-northridge-brockton-full) deleted via supervised delete_scheduled_task, registry re-verified at exactly 22 entries/0 spent, folders archived to `scheduled-tasks/_archive_2026-07-18_retired/`. Northridge-brockton had FIRED clean 14:16:29Z before retirement; run-outcome verification delegated to session local_47ad0cef.
- **G-B:** dead RAM-guard chain (ram-watchdog.sh + ram-guard.ps1, never wired in settings.json) archived to `_archive/2026-07-18_ram-guard-retired/`; tech.md updated.
- **G-C:** roi-brief-ws1-ws4-ws7 worktree removed (0 unmerged commits, branch preserved); gate-matcher-hardening (1) and systematization-candidates (3) KEPT — intentional unmerged anti-revert patches.
- **§7b completion:** EFULTON-counsel-questions staging file archived to `_archive/2026-07-18_efulton-declassification/` (missed at 07-09 declassification).
- **setup-review-closeout chip DONE-closed** on Gabriel's explicit interactive sign-off (the 07-17 TERMINAL entry required a human close).
- **event_log rolled over** (1,137 → 607 live; archive `_archive/event_log_2026-07-18.md`).
- **New standing rule:** all Gabriel decisions via interactive multiple-choice with researched recommendation (`feedback_interactive_decision_questions.md`).
- **Coordination:** ownership conflict with session a67aca7d (origin of the 5-phase tree) resolved by Gabriel ruling + stand-down message; that session pivoted to planning `setup-improvement-top5-2026-07-18` (5 plans incl. Plan-5 hooks hardening — its executor MUST rebase on today's engineering-router.py change). Session 47ad0cef ran parallel deal-side verification, no overlap. Concurrent-session duplicate-work check performed at every write.

## 2026-07-18 — LOI Throughput line added to ora-friday-closeout (v2.1)

Added the Gabriel-carried-forward LOI Throughput block to `ora-friday-closeout`'s SKILL.md (`OneDrive...\Documents\Claude\Scheduled\ora-friday-closeout\SKILL.md`, single-writer check clean — mtime predated this session) as a new Part A step: LOIs generated/sent this week (source: `loi-generation` skill outputs + deal-decision-ledger.md), Notion Acquisition Pipeline stage conversions, and a week-over-week trend line. Report-only, no new send path, reuses the task's existing ggoldberg-only email leg. Bumped to v2.1 with a changelog line; RUN SUMMARY format updated to include the LOI count/delta.

Dry-ran the filesystem-sourced portion against live data: 0 LOI files generated this week (2026-07-11 through 07-18) and 0 new deal-decision-ledger rows — confirmed via direct search, not assumed. Could NOT dry-run the Notion Acquisition Pipeline stage-conversion portion from this Code session (no Notion connector available here) — the SKILL.md's own graceful-degradation line ("LOI pipeline-stage data unavailable this run") will catch that same gap on the real Friday fire if CC/MCP still lacks Notion access then; worth a Cowork-surface check before 2026-07-24 if that matters before the real fire.

## 2026-07-18 — ora-uw-northridge-brockton-full closeout: QC'd, verdict-drift found, summary sent (Notion row + registry cleanup still pending)

Closed the loop on the 2026-07-18T14:16:29Z `ora-uw-northridge-brockton-full` run whose summary email never sent. Dispatched two independent underwriting-checker passes (re-derived cell formulas directly, not a recalc-trust pass) against both 07-18 workbooks/memos, then diffed against the 07-16 manual baseline (`ORA_ICMemo_{2900-Northridge-Dr-NW,4331-Brockton-Dr-SE}_v1.0.*`, `ORA_Underwriting_{...}_v1.0.xlsx`).

- **2900 Northridge:** DSCR 1.45x PASS, LTV 65% at ceiling, aggregate 40% correctly left unverified, basis floor FLOOR-FLAGGED (59.9% vs 61.5% required), INVERTED-SPREAD flagged, MI reassessment tab confirmed formula-driven (v4.0-compliant). Real gap found: single-tenant rollover (Nov 2031 lease expiry, Year 5 of a 10-yr hold) is not stress-tested even in Bear — no re-lease TI/LC/downtime priced at that point.
- **4331 Brockton:** same governor picture (DSCR 1.45x PASS, LTV 65%, both Stage-1 floors breached — Basis 57.43%/Yield 6.67% vs 65%/8% required, INVERTED-SPREAD). Verdict unchanged from 07-16 (kill on floors). **Verdict-drift finding:** Base levered 10-yr IRR swung from -0.26% (07-16) to +6.60% (07-18) with Bear/Bull moving similarly, driven entirely by model structure (an all-cash-close + Yr2 65%-LTV cash-out refi, full lease-up credit) not by any change in source facts — and the 07-18 IC memo never discloses or reconciles the swing. Secondary discrepancies noted (lease-up carry likely understated vs the workbook's own reassessed-tax figure; missing standing 5% LC/2mo free-rent; vacant-share opex not deducted; MI uncap mechanic mis-stated conservatively; inverted-spread magnitude understated; CoStar rent comp unverifiable this session).
- Sent a closeout summary (governor status, both findings, bottom line) to ggoldberg@oxfordra.net only via send-via-outlook.ps1 — confirmed OK in send-log.
- **Not done (Gabriel-decision, not auto-executed):** closing the TERMINAL setup-review-closeout chip; retiring 5 spent one-time registry entries; a Notion Ops Hub (32b6ecd8) completion row — no Notion connector available in this Code session, needs a Cowork-surface pass.

## 2026-07-18 — 511/275 re-screens confirmed complete (were already done, not missing); monthly-close verified current

Verified the 2026-07-17 Gabriel-authorized `verified-deal-recon` re-screens for 511 Industrial Mile Rd and 275 Old County Line Rd, which the 07-18 artifact-content plan flagged as "launched but never confirmed." Found they DID complete — session `local_380f407b-4255-4be9-ac5e-44b051c5cc2e` (07-17 22:49 ET) surfaced the results as another session's then-uncommitted `projects.md` diff; that diff has since landed and is now the current record (memory/projects.md lines 24-26). No re-run was needed.

- **511 Industrial Mile Rd — verdict PASS.** The "below-replacement bargain" thesis broke on a closer comp (1945 Jackson Rd prices below the subject despite having a dock) and lower-than-assumed achievable rent. CRITICAL unresolved fact: the live Crexi listing + Auditor land-use code ("HEALTH SPA") suggest this may currently be an operating indoor sports center, not a vacant industrial shell. The recon's own recommendation is do NOT re-engage broker Noah Kahkonen on the prior bargain framing — so no outbound broker contact is actually being proposed right now; if Gabriel wants to revisit at all, the recon says confirm actual current use with the broker first.
- **275 Old County Line Rd — verdict PURSUE, contingent.** Building resized to a corroborated 30,200 SF (vs. the prior 18-25K SF estimate), pushing the basis discount to 40-53%, past the 25% floor; ~7 active tenant suites suggest substantially occupied. Roof/HVAC totally unverified; a departed gunsmithing tenant (hot bluing/parkerizing/Cerakote) needs explicit Phase I REC scoping. Next step is Auditor/rent-roll confirmation (internal research), not outbound contact.
- **Bonus (same batch, not in original scope):** 2040 S Hamilton Rd also re-screened same day — verdict PURSUE on basis alone; next step (calling listing broker NAI Ohio Equities to confirm occupancy/rent) IS outbound counterparty contact and would need Gabriel's confirmation if pursued.
- **Residual gap:** the recon notes explicitly say these supersede the Notion Acquisition Pipeline tracker, which is "now stale" relative to this — Notion has not been updated to match. That's a Cowork-surface follow-up (no Notion connector in this Code session).

**monthly-close currency check:** compared `C:\Users\Owner\ora-skills\monthly-close\SKILL.md` (canonical, v2.1, HEAD, clean tree) against the live Cowork runtime cache (`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\...\skills\monthly-close\SKILL.md`) — byte-identical, no drift. No packaging/staging or Save-skill action needed; current for the 2026-08-01 close cycle.

## 2026-07-18 — ora-cowork-heartbeat: re-confirmed still broken, blocked on Gabriel/Cowork-surface action

Re-checked the LAMS registry directly (`scheduled-tasks.json`): `ora-cowork-heartbeat` still has NO `approvedPermissions` array (lastRunAt 2026-07-18T10:42:05Z, the 05:50 ET slot firing late as an app-open catch-up), unchanged since the 2026-07-17 root-cause finding and both ACTION-REQUIRED alerts (07-17 18:49 ET, 07-18 10:16 ET). No new diagnosis needed — this session's Code surface confirms the already-documented root cause (missing Notion-write tool grant; manual "Run Now" approval does not persist to the registry the way live cron-time approval does for sibling tasks) is still the live blocker. Per standing doctrine, hand-editing `scheduled-tasks.json` remains prohibited and no MCP tool exposes `approvedPermissions` for writing — this cannot be fixed from Code. Needs either Gabriel doing a supervised "Run Now" in Cowork's Scheduled Tasks UI (explicitly granting/re-approving the Notion write tool at the prompt if one appears) or a Cowork-surface session performing a supervised `update_scheduled_task` write. No further automated action taken this session; flagging to Gabriel per [[open-items-tracker]].

## 2026-07-18 — ora-pm PortalDashboard divide-by-100 bug fixed; discovered CI has silently blocked all deploys for 2 days

Fixed the 07-16 audit's finding #3 (PortalDashboard.tsx divided plain-dollar total_balance/amount fields by 100, showing tenants 1/100th of their true balance) — deleted the local fmt/fmtDate, switched to canonical formatCurrency/formatDate, added a format-contract regression test plus a source-level guard against reintroduction. Full local gate green (tsc 0 errors, 169/169 tests), adversarial REFUTE pass confirmed the fix correct on all axes and flagged the one real gap (test doesn't render the component) — closed with the source-guard test. Committed `43f0b76`, pushed.

**Bigger finding surfaced while confirming deploy:** CI (`npm run typecheck`) had been failing on every push to main since commit `0367ec0` (2026-07-16) — a Windows-vs-Linux TypeScript resolution difference meant `node:fs`/`node:path`/`__dirname` in `tests/db/ar-ledger.test.ts` typechecked locally but not in CI's clean Linux install, and the single CI job runs typecheck -> test -> build -> deploy sequentially, so the failure silently blocked deploy too. `wrangler pages deployment list` confirmed production was still serving commit `866480f` — the commit immediately BEFORE the two 2026-07-16 critical DB fixes (`0367ec0` ar_ledger cartesian-fan-out, `b7321f6` property_name). Those fixes had been merged and believed-shipped for 2 days but never actually reached ora-pm.pages.dev. Root-caused and fixed by pinning `@types/node` as a devDependency (matching CI's Node 20) and adding explicit `/// <reference types="node" />` to the two affected test files rather than widening the global tsconfig `types` array (which is deliberately restricted to avoid a DOM/@cloudflare/workers-types conflict). Committed `f196337`, pushed. CI ran fully green (typecheck/test/build/deploy all ✓) and `wrangler pages deployment list` confirms production is now on `f196337` — the ar_ledger fix, property_name fix, and this divide-by-100 fix are all finally live.

**Concurrent-writer note:** mid-verification, detected a second, legitimate concurrent session actively fixing the related Charge/Lease schema-drift bug (audit finding #7) in the same shared checkout, citing "Gabriel's 2026-07-18 ruling" in its own code comment. Left `src/portal/lib/portal-api.ts`, `PortalMyLease.tsx`, `PortalPayNow.tsx`, and its two new test files untouched per single-writer doctrine; verified no file overlap with my own committed diffs before pushing.

**Not fixed here (flagged separately):** a real crash risk found during the REFUTE pass — `PortalPayNow.tsx:139` falls back to a `charge_type` field that doesn't exist on the schema, throwing on any charge with no description. Spawned as its own task (`task_6a25b41e`) rather than folded into this fix.

## 2026-07-18 — 3 most-recent artifacts remediated: schematic-working, review-v02-working.md, Setup Audit 2026-07-09

Gabriel requested a deep review + fix plan for his 3 most recently updated Claude.ai artifacts (all touched 2026-07-18), then had it re-evaluated via Fable and executed via a subagent-driven remediation pipeline (fact-verification → 3 parallel draft writers → cross-artifact refute pass → 2 targeted fix passes → publish). All 3 republished in place, same URLs.

**Most consequential finding:** review-v02's closeout claim that `ora-uw-northridge-brockton-full` "was retired rather than fired" was factually wrong per live `list_scheduled_tasks` + event_log evidence — the task's deadline was re-armed/slipped from 2026-07-17 16:01 ET to 2026-07-18 10:00 AM ET and it DID fire today (`lastRunAt` 2026-07-18T14:16:29Z), then auto-disabled per normal one-time-task lifecycle. Corrected in the artifact. **Open follow-up, not yet resolved:** whether the fired run's actual output (6-tab Excel workbook, summary email) completed successfully has not been confirmed by any artifact or memory entry — flagging for Gabriel or a follow-up session to verify directly.

**10 facts verified against ground truth** (skill version, task KEEP/retired state, 754 Old State Route 74 pipeline stage, B3 migration closure, Apify/chrome-devtools disposition, confidentiality-guard test count, live fleet counts, live agent roster count, underwriting-defaults table fill-state, dropped-connector dispositions) — dossier at session scratchpad, not persisted. Several original review-pass "findings" (754 dual-classification, KEEP-ruling "reversal") turned out to be false positives on closer reading, not real contradictions — resolved via re-reading rather than a documentation fix.

**Process gap identified and closed:** all 3 artifacts shared one root-cause defect — Resolved/Closed claims asserted without a citation. New standing memory: [[feedback_artifact_citation_requirement]]. No registry writes were needed or attempted; no `BLOCKED-NEEDS-COWORK` items surfaced.

## 2026-07-17 — OI-009: Granite Tops vacating, unsigned lease-extension addendum now moot (OI-009 sub-item)

Gabriel confirmed Granite Tops & More is vacating end of month (2026-07-31), mooting the unsigned 5/28/2026 addendum that had proposed extending the lease to 2029-05-31 — the tenant isn't renewing, they're leaving. Wrote via `notion-update-page`: `Lease Status` → Notice Given, `Lease Expiration` → 2026-07-31 (vacate date). `Monthly Rent` ($16,713.65, still unexplained by any source found) left as-is — now a move-out reconciliation question rather than a lease-terms one. Verified via fresh fetch. This closes the last blocking item on OI-009's 4 named stragglers list — only Chesapeake Communications (already retired) and the untouched rest of the 93-row universe remain. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Maryland Hospital Association tenant-rename question decided (OI-009 sub-item)

Gabriel decided the LogicQual Research Institute reassignment flagged in the prior entry: keep `Tenant Name` as Maryland Hospital Association, no rename. Updated the row's `Notes` to record the decision. Closes the last open thread on this tenant. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Maryland Hospital Association resolved from Gabriel-supplied executed PDF (OI-009 sub-item)

The Third Addendum found earlier this session was an unexecuted draft, superseded by the actual final version. Gabriel supplied the fully-executed PDF directly (`Lease Suite B2-3 MHA Third Addendum Fully Executed 05.2026 -- 2203-2207 Northwood.pdf`) and stated the terms (Termination 6/30/2027, Rent $2,332/mo) before I finished extracting it. Standard PDF text extraction (`pdftotext`, `pdfminer`) failed on broken font encoding — pages were rendered to images via `pypdfium2` and read visually instead, which confirmed Gabriel's figures exactly and the Adobe Sign audit trail (signed by Gabriel Goldberg for Landlord, 2026-05-06, "Agreement completed"). Wrote `Monthly Rent` 1483.39→2332 and `Lease Expiration` null→2027-06-30 via `notion-update-page`, verified via fresh fetch. Separately surfaced (not acted on): the same addendum reassigns the Tenant under the Prime Lease from Maryland Hospital Association to "LogicQual Research Institute, Inc." (an MHA affiliate), releasing MHA from all obligations — flagged in the row's `Notes`, left under the existing Tenant Name pending Gabriel's decision on renaming. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009: Harold Palmer resolved, Maryland Hospital / Granite Tops re-checked (OI-009 sub-item)

Re-checked the 4 named 93-row-universe stragglers left open from earlier OI-009 passes. **Harold Palmer**: located the addendum's source `.docx` (prior pass only found the DocuSign completion-certificate page) plus its own DocuSign audit trail confirming full execution (signed by Eric Goldberg, 2025-03-26). Wrote `Monthly Rent` 1157→1166 and `Lease Expiration` null→2027-04-30 via `notion-update-page`, verified via fresh fetch. **Maryland Hospital Association**: found a newer Third Addendum resolving the earlier entity-name ambiguity (confirms "The Maryland Hospital Association, Incorporated" as the tenant's proper name) and giving Termination 5/31/2027 + Rent $2,332/mo effective 6/1/2026 — but no executed/signed copy located despite two targeted searches, so left unwritten pending confirmation. **Granite Tops**: re-confirmed still unresolved, same blank-signature addenda as before plus one previously undocumented smaller-footprint draft. **Chesapeake Communications**: already retired per Gabriel's prior decision, fresh search found nothing new. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — ora-uw-northridge-brockton-full RE-ARMED (Gabriel-directed) — on CC/MCP, not LAMS

- **Gabriel directed a clean scheduled re-arm** of the one-time northridge/brockton FULL underwriting that this morning's setup-review-closeout recheck found deleted from the registry (see prior entry — item (c) never fired). Registered via supervised `create_scheduled_task` (MCP, no JSON splice) with QC verified against `list_scheduled_tasks`: `enabled:true`, one-time `fireAt 2026-07-18T14:00:00Z` (10:00 ET), path `~\.claude\scheduled-tasks\ora-uw-northridge-brockton-full\SKILL.md`, id unique across both fleets.
- **Deliberately homed on CC/MCP, not the original LAMS/Cowork fleet.** The task must build a 6-tab Excel workbook (Excel COM) and email a summary (Outlook COM) — both COM paths work only on CC/MCP; the LAMS/Cowork sandbox cannot COM-send. This is the same doctrine that migrated `ora-am-brief` LAMS→CC/MCP on 2026-07-16. The original LAMS design's email leg would have failed structurally.
- **One adaptation vs. the backup SKILL.md:** because `acquisition-underwriting` is a Cowork-surface skill (NOT a CC plugin — confirmed absent from the CC Skill-tool list and per `reference_skill_surfaces.md`), the CC prompt instructs the run to READ AND FOLLOW its authoritative source at `C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md` (v4.1, repo HEAD `5dda2cd`, clean; whole skill self-contained in that one file, no references/ subfolder) rather than invoke it via the Skill tool. `ora-flood-zoning-dd` remains a native CC plugin-skill invocation. All else preserved verbatim: both properties + source PDFs in `Business\Investment Candidates -- 2026\`, FULL-mode deliverables, `/outputs/` file-naming + 16-pt QC gate, Notion Ops Hub `32b6ecd8` completion row, ggoldberg-only email via `send-via-outlook.ps1`, DSCR≥1.25 / LTV≤40 aggregate governors, no-fabricate + QUESTIONS-FOR-GABRIEL escalation.
- **OPEN CAVEAT — tool pre-approval for a truly unattended clean run:** the run will use Bash/PowerShell (send script, openpyxl/Excel COM), the `ora-flood-zoning-dd` Skill, Notion MCP writes, and file writes. Per `reference_scheduled_task_approved_permissions.md`, a scheduled task missing a tool grant can pause on a prompt or silently fail the write while `lastRunAt` still advances. To de-risk, Gabriel should click **Run now** once (pre-approves the tool set onto the task) OR accept that the 10:00 ET fire may need a prompt. Flagged to Gabriel this session.
- **Chip status unchanged:** setup-review-closeout stays ABORTED/open from this morning's recheck; re-arming does not retroactively satisfy that DONE-gate (the recheck task is spent). This re-arm is a fresh forward action, not a chip closure.

## 2026-07-17 — Title-archived Row Retired gap swept DB-wide (OI-009 sub-item)

Gabriel asked to check the same title-archive/Row-Retired gap (rows named "⛔ ARCHIVED 2026-07-12 — ..." that never had the Row Retired checkbox actually set) across the whole Tenant Database, not just the 42 already fixed at Northwood. Queried DB-wide with no property filter: 73 additional rows found, spanning 9620 State 350, Zettler, Red Branch, Morrison, FVC/Fairground Village Center, 1100 Rarig, 1900 N Broadway, 29000 Information Ln, and many with a null Property Address. Set Row Retired=__YES__ on all 73 via notion-update-page, verified clean via a fresh DB-wide COUNT query returning 0. Combined with the 42 Northwood rows, 115 total stale archived rows are now correctly flagged across the entire Tenant Database — this gap is fully closed everywhere, not just Northwood. Detail: open-items-tracker.md OI-009.

## 2026-07-17 — Northwood title-archived Row Retired gap closed (OI-009 sub-item)

Gabriel asked to close out the 42 Northwood-tagged rows (re-counted precisely from the earlier "~45" estimate) that were archived by title prefix (`⛔ ARCHIVED 2026-07-12 — ...`) in a 2026-07-12 remediation but never had the `Row Retired` checkbox actually set (the same gap OI-004 closed for other rows, never swept DB-wide). Set `Row Retired=__YES__` on all 42 via `notion-update-page`, verified clean via a fresh COUNT query returning 0 remaining. Scoped to the Northwood cluster only — the same gap is unverified across the rest of the Tenant Database. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — Northwood bulk address fix closed (OI-009 sub-item)

Retried the Notion `query_data_sources` SQL tool after it hit an `entitlement_required` quota wall earlier (all of today's parallel OI-009 research agents had exhausted the free query allowance). Quota reset after ~1h; query returned 76 rows still on the wrong `2203-2207 Northwood — Columbus OH` address option, 45 of which are pre-existing archived-by-title duplicates (flagged as a residual, not touched — out of scope). Corrected all 31 genuinely active rows to `2203-2207 Northwood Dr — Salisbury MD` via `notion-update-page`, including 2 rows (Bay-Care Heating & Air LLC, Childs Play Diesel Performance) that earlier same-day cluster passes had written to the old wrong option before the address bug was known. Verified clean via a fresh query: 0 active rows remain on the wrong address; 38 rows now on the correct option (31 + 5 from the original pass + 2 from Zettler), reconciling exactly. Address-only fix — Harold Palmer and Maryland Hospital Association's rent/date fields were deliberately left untouched per Gabriel's earlier instruction. Separately noted: `task_6719632a` (the spawned follow-up session) ran on a Code surface without Notion access and correctly declined to guess at the bulk fix, only handling the Restoration Church Trust retirement (redundant with, and consistent with, the earlier retirement — verified no corruption). Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — OI-009 bulk lease-abstraction pass (5 parallel clusters + Gabriel-gated writes)

Gabriel authorized starting the OI-009 bulk pass (previously deferred as low-priority). Ran 5 parallel research agents against the Notion Tenant Database, each independently verifying against primary lease documents before writing: Red Branch stragglers (4/5 resolved), Zettler (7/8 + 1 partial), Northwood (5/7 checked — cluster turned out to be ~80 rows, not 7; follow-up chip spawned for the remainder), Sunburst (3/3), and 6 no-address-but-Active tenants (6/6). 26 of 29 originally-targeted tenants resolved this pass. Real bugs found: a new landlord-name-in-Tenant-Name variant (Seafire Properties LLC), every Northwood row carrying the wrong city/state (Salisbury MD tagged as Columbus OH — new select option added), and a $2M loan counterparty ("Restoration Church Trust") mistakenly entered as a tenant.

6 decisions surfaced needing Gabriel's judgment, all resolved via AskUserQuestion and executed same session: Eurosort's address added as a new schema option (55 New Plant Court — Owings Mills MD); InSite Build updated in place to its $50/mo signage-license terms; Restoration Church Trust retired from the Tenant DB; Chesapeake Communications LLC retired as untraceable bad data; Granite Tops & More and the two remaining Northwood tenants (Harold Palmer, Maryland Hospital Association) left open pending further documents, per Gabriel's explicit choice not to guess. OI-009 remains OPEN — real residual scope (~35 Northwood stragglers) tracked via task chip `task_6719632a`. Detail: `open-items-tracker.md` OI-009.

## 2026-07-17 — setup-review-closeout chip: proper 16:10 ET recheck run — ABORTED (TERMINAL); item (c) task deleted, never fired

- **`ora-setup-review-closeout-recheck` fired on schedule** this run (registry `lastRunAt 2026-07-17T22:47:21Z` = 18:47 ET, after its 20:10Z/16:10 ET `fireAt`; task now `enabled:false`, auto-disabled — this was the proper run the 13:54 ET early-fire abort deferred to). STEP 0 concurrent-writer check clean: the only "setup review closeout recheck" session (local_87aaebe8) is not running; no live session overlaps the chip / "northridge" / "closeout" title.
- **DONE-gate re-verified against LIVE state — NOT 6/6; ABORTED:**
  - **(a) `ora-task-integrity-guard` — fired, but alarmed.** `lastRunAt 2026-07-17T16:55:18Z` (12:55 ET, after 12:45 target); STEP-1.5 emitters all ran clean (see item d). **Caveat / not-clean:** the 12:55 run's registry-membership-probe logged a LAMS drop `ora-skills-reimport-watch` (`membership.log 2026-07-17T13:00:35 drops={'lams':['ora-skills-reimport-watch']}`, re-synced to `drops=-` by 13:01:45). Under the guard's v1.5 doctrine a registry drop is a STEP-3 alarm. Almost certainly benign — a live "Reimport 3 pending ora-skills into Cowork cache" session is active and that one-time watch legitimately left the registry — but not independently confirmed as intended, so treated as an alarm, not clean.
  - **(b) `automation-health-monitor` v1.8 — fired clean.** LAMS registry `lastRunAt 2026-07-17T15:08:57Z` (11:08 ET, after 11:05 target); LAMS `_state` clean, no drop attributable to it.
  - **(c) `ora-uw-northridge-brockton-full` — DID NOT FIRE (decisive, terminal blocker).** Absent from BOTH registries: not in CC/MCP `list_scheduled_tasks`, and a full read of the LAMS registry (`scheduledTasks` len=23) contains no such task. It is NOT present even as a consumed one-time entry — compare `ora-heartbeat-fix-verify` / `psa-reconciliation-fix-monitor`, which fired today and remain as `enabled:false` with a `lastRunAt`; a fired one-time task is retained, a **deleted** one vanishes. Zero run artifacts dated 2026-07-17 in `Business/Investment Candidates -- 2026/` or its `outputs/`. The task was removed from the LAMS registry before its 16:01 ET fire window and will never fire (this recheck is the last automated check — it just auto-disabled).
  - **(d) State timestamps — all advanced past the 2026-07-16 baseline:** `registry-membership.log 2026-07-17T14:43:35` (was 07-16T13:50:00); `fleet-heartbeat.json ts 2026-07-17T17:02:20Z` (was 07-16T17:50:00Z); `push-fleet-heartbeat.log 2026-07-17T17:02:24Z OK` (was 07-16T17:50:02Z).
- **Substantive purpose already satisfied (context for the human decision, NOT grounds to auto-close):** the northridge/brockton FULL underwriting was completed MANUALLY via a Cowork run on 2026-07-16 — deliverables `ORA_ICMemo_2900-Northridge-Dr-NW_v1.0.docx/.pdf`, `ORA_ICMemo_4331-Brockton-Dr-SE_v1.0.*`, `ORA_Underwriting_{2900-Northridge,4331-Brockton}_v1.0.xlsx`, all dated 2026-07-16 10:06–10:10 ET — the same run that drove the acquisition-underwriting v3.9→v4.0 amendment. Per the 07-16 T5 finding, the skill caches were already current (acquisition-underwriting v4.1, ora-flood-zoning-dd v1.1), so the scheduled re-run would have added no fresh signal.
- **Outcome — chip left OPEN; ABORTED (terminal).** Appended `ABORTED` to chip-claims.log (Code/f7ebd0e5). The chip CANNOT self-close now: the recheck task auto-disables after this run and item (c)'s task is deleted, so no future automated run will re-verify. **Needs a human call (Gabriel / a future session):** either accept the 07-16 manual underwriting as satisfying the chip's substantive intent and close it, or re-arm `ora-uw-northridge-brockton-full` if a genuine against-current-skills scheduled re-run is still wanted. No email — internal bookkeeping; any real watch alarm has its own notify path (item (a)'s guard alarm, if real, already emailed ggoldberg).

## 2026-07-17 — OneDrive Business/Personal physical split executed; machine migration B3 closed

**OneDrive split:** Gabriel authorized the full coordinated execution of the 2026-07-09 proposal (`2026-07-09_OneDrive-Business-Personal-Split_Proposal_v01.md`). All Business-bucket and Personal-bucket items physically moved into new `Business\`/`Personal\` folders at the OneDrive root; Ambiguous-bucket items (incl. `eric spreadsheets\`, `eric documents\`) and the "not filed either way" housekeeping items were left at root, unresolved, per the proposal's own fallback. 4 hardcoded automation paths updated in the same pass (`ora-am-brief`, `ora-master-workbook-ingest`, `ora-pm-ledger` ×2, `ora-deal-sourcing-scan`), all verified reachable post-move via `Test-Path`. **Near-miss caught and fixed same session:** an initial pass mistakenly also redirected the Master Workbook path (`eric spreadsheets\`) under `Business\` even though that folder was correctly left un-moved in the Ambiguous bucket — caught via verification before any automation next ran, reverted. One real omission from the original proposal (`Toledo Sale`, named in the proposal's own Business list) was initially missed in the move, caught via a post-move root-listing diff, and moved. Several items not covered by the 2026-07-09 proposal at all were discovered at root during this pass (`Loans External/`, `GFU/`, `Muirkirk 2013 Refinancing/`, and assorted loose files/scripts) — left unclassified for a future pass rather than guessed at. Detail: `reference_onedrive_business_scope.md`.

**Machine migration B3 (48h burn-in) — CLOSED.** All 10 checklist boxes verified with command-output evidence in one session, including a one-time COM test send to ggoldberg@oxfordra.net (Gabriel's explicit in-session confirmation), confirmed via `send-log.txt`. Detail: `project_claude-setup-audit-2026-07-09.md`.

## 2026-07-17 — bash-guard.mjs (oxford-command-center): OI-011 read/write + cp source-dest false positives closed

- **Closed by a concurrent session the same night**, working in its own git worktree
  (`fix/bash-guard-read-write-oi011`) off this session's OI-010 commit — landed on
  `oxford-command-center` `main`, commit `8006a15`, on top of `60c45ed`. Fixes the 2 pre-existing
  false positives flagged (not fixed) during OI-010's adversarial review: `git config --get
  core.hooksPath` (a pure read) was denied identically to an actual write; `cp` reading FROM a
  guardrail file (e.g. a benign backup) was denied identically to overwriting it.
- Check (d) now distinguishes mutation from read: a trailing token after `core.hooksPath` counts as
  a value being set unless the command carries an explicit `--get`/`--get-all`/`--get-regexp`/
  `--get-urlmatch` flag; `--unset`/`--add`/`--replace-all` and inline `-c core.hooksPath=` still
  always deny. Check (g)'s `mv`/`cp` guard now treats them differently: `mv` still denies the guard
  path in either argument position (source-position `mv` removes/neutralizes the file, same
  severity as `rm` — no pure-read form exists for `mv`), while a new `cpGuardWrite()` helper denies
  `cp` only on its destination argument, covering the plain form plus all 3 `-t`/`--target-directory`
  shapes.
- **3 rounds of adversarial review** (mandatory per CLAUDE.md for `hooks/**` security-gate code)
  found and fixed 3 real bypasses before landing: a dash-prefixed `core.hooksPath` value defeating
  the initial read/write classifier; `--target-dir=` (GNU abbreviation) and `--target-directory`
  (space-separated) both missed by earlier destination-detection passes. 68 tests in
  `bash-guard.test.ts` (was 64), full project suite 231 files/2792 tests green, typecheck 0, lint 0.
  Landed via isolated worktree, fast-forward merge (matching the OI-010 convention), verified zero
  collateral impact.
- Full detail in `open-items-tracker.md#OI-011` (closed) and `project_bash_guard_indirection_gap.md`.

## 2026-07-17 — registry-membership-probe: retired_drops added + hardened (plain-prose retirement reconciliation, completion-only)

- **Trigger:** the 2026-07-17 `ora-task-integrity-guard` run had to hand-reconcile a false `[ACTION]`/exit-1 from `registry-membership-probe.py`. `ora-skills-reimport-watch` was retired earlier that day (twice-logged: paused+archived, then registry entry deleted — see the two `2026-07-17:` lines under the `## 2026-07-16` plugin-reimport entry), yet the probe still alarmed on the drop.
- **Root cause:** the probe's only auto-reconciliation path (`ratified_drops`) required the ceremonial uppercase token `RATIFIED` inside the drop's `## ` section. ORA documents most scheduled-task retirements in plain prose ("... retirement ...", "registry entry deleted"), never that token — so a fully-ratified, event-logged retirement still raised a one-time false alarm.
- **Fix 1 — feature (commit a9fb77e):** added `retired_drops()` — reconciles a drop when a recent (≤14d) event_log LINE names the task id alongside a retirement signal, with per-line date resolution (inline `YYYY-MM-DD` prefix wins, else nearest `## ` header). `main()` now reconciles via `ratified_drops | retired_drops`. Also repaired a pre-existing RED test: the fixture still used `### ` headers and had silently stopped matching after the 2026-07-16 `### `→`## ` split fix (suite was 24/25; the failing assertion was never caught because nothing re-ran it).
- **Fix 2 — hardening (commit 8b2acbd):** closed a residual risk in Fix 1 — matching any `retire*`/`decommission*` verb meant a forward-looking "we should retire ora-X next quarter" or a negated "do not retire ora-X" would have reconciled (silenced) a genuine drop of ora-X. Replaced the verb match with `_retirement_completed()`: reconcile only on accomplished-fact wording — `retired`/`decommissioned`/`deregistered` (past participles, so the infinitives no longer match), `retirement`+`completed`, or `registry`+`deleted`/`removed` (past-tense forms that exclude `deletion`/`deleting`/`pending deletion`). Bonus: a two-part retirement now reconciles only on its part-2 completion line, never the part-1 "entry still exists, pending deletion" line. Completion-only wording makes fragile tense/negation parsing unnecessary.
- **Verification:** suite 41/41 (was 24/25). Verified against the real event_log — `ora-skills-reimport-watch` reconciles via its completion line; planted "should retire … next quarter" and "do NOT retire" lines both → ∅; a planted genuine completion → reconciles. Live probe runs exit 0, no regression.
- **Shipped:** both commits pushed to `ZeOoba/ora-claude-config` `main` (HEAD 8b2acbd); pre-push doctrine gate clean. Two files only: `maintenance/registry-membership-probe.py` + `maintenance/test-registry-membership-probe.py`; no other session's WIP swept.
- **Residual (documented, not fixed):** if a future planning note ever uses accomplished-fact phrasing about a not-yet-removed task, it could reconcile prematurely — vanishingly unlikely given the completion-only gate; guard remains defense-in-depth (task-folder-registration-probe + membership-guard.ps1 + integrity-guard cross-checks).

## 2026-07-17 — Weekly punch-list review: 754 corrected, reference-library governance ratified, deal re-screens launched

Gabriel reviewed the week's open items (open-items-tracker + deal pipeline + reference-library governance + machine migration) via interactive multiple-choice questions:
- **754 Old State Route 74:** corrected projects.md — deal is NOT stalled; LOI agreed, ORA sole purchaser, Eric negotiating PSA directly (live email thread 2026-07-16 re: parking easement not previously logged here).
- **Reference-library governance — all 3 open decisions ratified:** (1) subject-first naming schema (Style Guide §3.1) is canonical over date-first; (2) DocType controlled vocabulary locked to exactly ICMemo/LOI/PSA/RentRoll/Deck; (3) Naming Standard v1.1 ratified provisionally pending Eric's formal sign-off.
- **511 Industrial Mile Rd** and **275 Old County Line Rd:** Gabriel authorized fresh `verified-deal-recon` re-screens from scratch (511: re-screen before re-engaging broker Noah Kahkonen; 275: full redo, treating the 6/12 WAIT-FOR-DILIGENCE plan's diligence as never having happened given 27 days of zero Notion movement). Both launched as background Workflows same session.
- **2040 S Hamilton Rd:** parked — Gabriel will supply the OM/rent-roll/financials location later.
- **Machine migration B3 burn-in:** Gabriel asked for the checklist to actually be run this session (separate from this entry — see its own result once complete).
- **OneDrive Business/Personal split:** Gabriel authorized executing the physical folder move (previously only a non-destructive classification reference existed) — see separate entry once complete.

## 2026-07-17 — setup-review-closeout chip: recheck fired ~2h20m early, ABORTED (not DONE); item (c) northridge not yet fired

- **`ora-setup-review-closeout-recheck` executed prematurely** at ~13:50 ET (17:50Z) while its own
  registry `fireAt` is 20:10Z (16:10 ET) — the entry still shows `enabled:true`, `nextRunAt 20:10Z`,
  no `lastRunAt`, so the proper run is still pending. Because it ran early, item (c) — the one-time
  `ora-uw-northridge-brockton-full` acquisition-underwriting re-run scheduled for **16:01 ET** — had
  not yet fired. Verified: task absent from the live CC/MCP registry; backup folder
  `_scheduled_tasks_backup/ora-uw-northridge-brockton-full/` holds only its SKILL.md (Jul 15) with
  **no `outputs/` and zero run artifacts**. Blocker for the DONE-gate.
- **DONE-gate now 3 clear / 1 blocked / 2 unconfirmed — NOT 6/6:**
  - (a) `ora-task-integrity-guard` — **fired** 12:55 ET (`lastRunAt 2026-07-17T16:55:18Z`, after its
    12:45 target); STEP-1.5 emitters confirmed to have run (see item d). Caveat: membership-probe
    logged one LAMS drop today (`ora-skills-reimport-watch`); its STEP-3 alarm status was NOT
    independently confirmed from the guard's Notion post — treated as unconfirmed, not clean.
  - (b) `automation-health-monitor` v1.8 beacon — **not verifiable from the CC/MCP surface** (LAMS
    task; not in this fleet's `list_scheduled_tasks`). Left unconfirmed.
  - (c) `ora-uw-northridge-brockton-full` (16:01 ET) — **NOT fired** (decisive blocker, above).
  - (d) State timestamps — **all advanced past the 2026-07-16 baseline**:
    registry-membership.log `2026-07-17T13:01:45` (was 07-16T13:50:00); fleet-heartbeat.json `ts
    2026-07-17T17:02:20Z` (was 07-16T17:50:00Z); push-fleet-heartbeat.log `2026-07-17T17:02:24Z OK`
    (was 07-16T17:50:02Z).
- **STEP 0 concurrent-writer check:** clean — no running session with an overlapping
  chip/"northridge"/"closeout" title; chip-claims.log CLAIMED (Code/c3a1e79e 2026-07-16) still open,
  no prior DONE/ABORTED.
- **Outcome:** chip left OPEN. Appended `ABORTED` to chip-claims.log (Code/30222b1d) citing the early
  fire + unfired item (c). The recheck's proper 16:10 ET run (still pending in the registry) should
  re-verify after northridge's 16:01 ET fire and can legitimately close the chip DONE then. No email
  (internal bookkeeping; any real watch alarm has its own notify path).

## 2026-07-17 — bash-guard.mjs (oxford-command-center): git-alias/wrapper-script indirection closed, OI-010

- **Audited then closed a real, confirmed gap in oxford-command-center's `bash-guard.mjs`** (its
  Bash PreToolUse guard), following up on an unconfirmed hypothesis raised while checking that repo
  for anything resembling the same-night `ora-autonomy-gate.py` OI-007 indirection work. Confirmed:
  a two-step disk-persisted indirection (a git alias, or a wrapper script deferring its verb/path to
  a positional or shell variable) defeated all 7 blocked command classes, with neither step's own
  text containing the trigger pattern. Proved end-to-end (not just at the hook-logic level): a git
  alias genuinely staged a file via `add -A` in a disposable repo; a wrapper script genuinely
  deleted a `data/warehouse` test directory.
- **Fixed and landed** on `oxford-command-center` `main`, commit `60c45ed`, via isolated worktree +
  TDD + fast-forward merge. Resolves both indirection layers into one expanded text every existing
  check scans: git aliases via `git config --get` (plus inline `-c alias.X=value` one-shot
  overrides), and script content read through a widened set of invocation forms (sh/bash/zsh/dash/
  ksh, source/dot, stdin redirection, direct execution) with best-effort positional-parameter and
  simple-variable substitution.
- **Three rounds of independent adversarial review (3 parallel agents) found and fixed 4 real bugs**
  before landing, most severe first: (1) git global options (`-c`/`-C`/`--git-dir=`/`-p`/
  `--no-pager`) before the alias name broke candidate detection entirely; (2) a DoS-class
  exponential subprocess-spawn blowup from a plausible chained-alias config (4-8s+ stalls on every
  Bash call, fixed via a shared 16-lookup budget); (3) a DoS-class backtracking regex costing ~10s
  on a crafted payload (fixed via a length bound, applied consistently to 3 similarly-shaped
  regexes); (4) a quote-handling bug hiding a substituted value from the downstream commit-message
  quote-blanking logic. 59 new/updated tests including timing guards on both DoS fixes; full project
  suite 231 files/2783 tests green, typecheck 0, lint 0.
- **Accepted, documented limits (same architectural ceiling as OI-007)**: arbitrary shell constructs
  beyond simple literal variable assignment (command substitution, arithmetic, exported variables,
  control flow, >3-level nested wrappers, >64KB scripts) are not resolved — closing those for real
  needs the same shift OI-007 used (verify the actual outbound action/state), not another regex.
- **2 unrelated, pre-existing false positives found during review, deliberately not fixed here** to
  keep scope tight — tracked separately as `open-items-tracker.md#OI-011`.
- Full detail in `project_bash_guard_indirection_gap.md` and `open-items-tracker.md#OI-010` (closed).

## 2026-07-17 — ora-autonomy-gate.py hardening: override tokens, 8 matcher bypasses, OI-007 (indirection ceiling) fully closed

- **Override-token mechanism hardened.** The flat, mtime-only `hooks/overrides/<name>`
  sentinel was content-blind, session-blind, and git-trackable — a plain `git clone` of
  `~/.claude` could self-grant a live production-deploy window with no human involved
  (proven empirically: fresh clone → exit 0 for `netlify deploy --prod`, vs. an empty-dir
  control at exit 2). Replaced with session-scoped, severity-split, content-bound tokens
  under `hooks/sessions/<id>/overrides/` (gitignored, so structurally uncommittable).
  Landed on `ora-autonomy-gate.py`; a concurrent session independently reached the same
  root-cause conclusion and hardened `git-prepush-doctrine-gate.py` the same night — the
  two were later unified onto one shared `hooks/lib/override_tokens.py` contract to stop
  them drifting apart.
- **Adversarial review (3 rounds) found and fixed 8 real detection-matcher bypasses** in
  `ora-autonomy-gate.py`, independent of the token work above: dotless-domain email
  recipients, PowerShell `-T` prefix-binding, `cmd /c`/`powershell -Command` netlify
  indirection, Unicode homoglyphs and invisible characters (zero-width space, RTL
  override) defeating word-boundary matches, the mail script's Windows 8.3 short-name
  alias, `check_mcp`'s allow-by-default logic, and a foundational `sys.stdin` UTF-8
  decoding bug (the platform codepage was silently mojibaking non-ASCII payloads,
  undermining the Unicode fixes for any real, non-Python-escaped invocation). Test suite
  grew 44 → 65.
- **OI-007 (the value-indirection ceiling these matcher fixes couldn't close) fully
  closed**, in three parts:
  1. **Email side**: an outbound-action check inside `send-via-outlook.ps1` itself
     (gitignored, not git-tracked — see the 2026-07-17 entry above this one for detail).
     3 real bugs found and fixed by adversarial review before landing.
  2. **Netlify side, repo-local**: `website-canonical` PR #30, merged by Gabriel —
     `scripts/netlify-guard.js` + a `postinstall` shim patcher routing the netlify CLI
     through an authorization check. 2 real bugs found and fixed pre-merge (an
     exact-array-element flag-detection bypass letting `--prod=true`/`--prod-if-unlocked`
     through unauthorized; a postinstall patcher that silently exited 0 even when it
     patched nothing).
  3. **Netlify side, machine-wide follow-up**: `npx netlify` / a bare `netlify` command
     invoked from OUTSIDE `website-canonical` resolved an unguarded copy via npm's
     global/registry fallback (npx doesn't consult PATH the way a bare command does, so a
     simple PATH-shadowing wrapper wouldn't have closed this). Closed by deliberately
     installing netlify-cli globally (pinned to the repo's own 26.2.0) and patching its
     shims too — `hooks/bin/netlify-guard-global.js` + `maintenance/patch-global-netlify-shim.js`,
     landed on `~/.claude` main. Verified empirically that a local guarded install always
     wins over the global one in npx's own resolution order, so there is zero
     double-check / double-token-consumption risk between the two layers. Accepted limit
     (Gabriel-ratified): global npm installs have no postinstall-equivalent hook, so the
     patch needs a manual re-run after any future global reinstall/update — documented,
     not automated, given the underlying gap was already flagged low-priority.
- Full detail in `reference_autonomy_gate_override_mechanism.md`,
  `project_autonomy_gate_indirection_ceiling_followup.md`, and `open-items-tracker.md#OI-007`
  (now closed).

## 2026-07-17 — Session close-out: OI-006/008 completed, canonical tracker fully closed

Continuation of the Tenant DB remediation session. Closed the remainder of the OI-003–008 arc:

- **OI-006** completed: read all 5 primary executed lease documents via SharePoint for the 4
  turnovers + Soldier Trucking property conflict. Soldier Trucking confirmed via a Gabriel-signed
  Second Addendum (1100 Rarig Ave Unit G&H, not Zettler Rd 301 as Notion had it). Wrote and
  verified 6 Notion corrections.
- Ran down the 7 remaining WORKBOOK-NEWER rows + Masala Bazaar/Azad Shah dedup at Gabriel's
  follow-up request: 5 of 6 date corrections confirmed against primary lease/addendum documents;
  Pedro Ulate corrected on pattern-inference only (no lease document locatable — flagged as the
  one weaker-evidence write). Surfaced a second, distinct systematic bug: several Notion rows had
  the workbook's Escalation Date miscopied into Lease Expiration at the original March import.
- **OI-008 opened and closed same-day**: swept the full 79-pair Notion↔workbook reconciliable
  overlap for the Escalation-Date bug. Zero new instances found beyond the ones already fixed —
  confirms the defect was fully contained to the 7 originally-flagged rows.
- **OI-007** (owned by a concurrent session, not this one): independently verified rather than
  taken on faith — confirmed via `git fetch`/`pull` on `website-canonical` that PR #30 (netlify
  deploy guard) is genuinely merged at `b25a70d`, with real 113+149-line guard files, not a
  placeholder claim. Both Gate 1 (email) and Gate 2a (netlify) are closed.
- **Canonical tracker (`open-items-tracker.md`) now has zero open items** — OI-001 through
  OI-008 all CLOSED with evidence.
- Two shared-checkout commits landed this session using the `commit-provenance-guard` override
  after independently verifying (via `git diff --cached`) that the flagged co-edit was a
  recency-heuristic false positive, not real foreign content — the guard behaved as designed.
- Git state at close: `main` in sync with `origin/main`, nothing of this session's uncommitted or
  unpushed. Concurrent session `3fc20af9` remained active throughout with its own WIP, not
  touched.

**Workflow/systematization candidates surfaced, not yet actioned:**
- The commit-provenance-guard's recency-heuristic false-positive rate on `open-items-tracker.md`
  was 3-for-3 this session (every co-edit flag was already safely in `HEAD`). Worth checking
  whether the guard's TTL window is longer than it needs to be, or whether it should re-diff
  against `HEAD` before flagging instead of relying purely on a recency timestamp.
- OI-008's residual scope note (93 Notion Tenant DB rows with no workbook counterpart, never
  independently verified against primary leases) is real but was explicitly out of scope tonight
  — worth a deliberate decision on whether it's worth pursuing, not a silent drop.

## 2026-07-17 - psa-reconciliation reimported (Save-skill click confirmed)

Standalone MULTI-FILE reimport via Entry Point A. plugin_of => None. Repo commit 7e6d14d (frontmatter description trim 1274->956 for the 1024 import limit, ora-skill-text-audit follow-up). Only SKILL.md had drifted from cache; packaged clean (description 956/1024, 16-point QC OK, 5 forward-slash entries). Routed to the Cowork Save-skill button (multi-file: SKILL.md + INSTALLATION.md + 3 references/ - the desktop Settings path drops subfolder files). Gabriel confirmed the click. Post-install verify: all 5 cache files present, raw+normalized byte-match the repo. Ledger cleared; pending-reimport queue now empty.

## 2026-07-17 — OI-007 email-side fix: outbound-action check in send-via-outlook.ps1 (gitignored file, record here)

- Landed the email side of OI-007 ([open-items-tracker.md#OI-007](open-items-tracker.md#OI-007)):
  ora-autonomy-gate.py's Gate 1 detects an external recipient by parsing Bash command TEXT,
  which adversarial review proved is structurally blind to value indirection (a recipient
  built from a PowerShell variable/concatenation/file-read never appears as a literal
  substring, so Gate 1 never fires). Fix: an outbound-action check inside
  `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` itself, at the point
  where PowerShell has already resolved `$To`/`$Cc` to concrete values.
- **This file is gitignored (`scheduled-tasks/*/*`) — this log entry is the only durable
  record of the change.** No worktree, no commit, no diff history exists for it.
- New git-tracked pieces (landed via normal worktree process): `hooks/lib/email_send_tier.py`
  (shared `EXTERNAL_SEND` tier + recipient-binding, imported by BOTH Gate 1 and this new
  check so they cannot diverge), `hooks/lib/check_external_send.py` (the CLI the PowerShell
  script shells out to, validating against the same session-scoped, content-bound,
  single-use token contract). `ora-autonomy-gate.py` refactored to import from the shared
  module instead of its own inline copy.
- Added `-WhatIf` to send-via-outlook.ps1: performs every check but stops short of the real
  Outlook COM call, so the gating logic can be tested end-to-end without ever sending a
  real email. Exit code 5 = external recipient(s) not authorized (new).
- **Two real bugs found by adversarial review and fixed before this reached production:**
  1. A suffix-only regex (`-notmatch '@oxfordra\.net$'`) misclassified
     `attacker@evilhost.com@oxfordra.net` as internal — a complete bypass. Fixed: require
     exactly one `@` and an EXACT domain match, not a suffix match.
  2. Recipients were passed to `check_external_send.py` via a `--recipients` CLI argument;
     PowerShell's native-argument marshaling silently stripped an embedded double-quote
     before python ever saw it, so the checked value could differ from the actual send
     value. Fixed: recipients now travel one-per-line on stdin, never argument-parsed.
  3. (Found along the way, affects ALL token tiers not just this one) `override_tokens.py`
     opened token files as plain `utf-8`; PowerShell's default `Out-File`/`Set-Content`/`>`
     writes a UTF-8 BOM, corrupting the leading `scope` key and silently failing closed on
     a genuinely Gabriel-approved token. Fixed: `utf-8-sig`.
- Verified via 6+ `-WhatIf` scenarios against the LIVE file (internal-only, external+no-token,
  external+valid-token+consumed, no-session-id fail-closed, Cc-field checked, the Daily-Brief
  internal-To+Cc pattern with zero regression) plus the two bypass reproductions above,
  re-confirmed fixed post-patch.
- **Still open (deferred separately, not this entry's scope):** the netlify/Gate 2a side of
  OI-007 — postinstall-hook wrapper in website-canonical, Gabriel-ratified direction, not yet
  built (Invariant 2 gates any change to that repo's build tooling).

## 2026-07-17 - package-and-stage-skill v1.10 reimported (Save-skill click confirmed)

Standalone single-file reimport via Entry Point A. plugin_of => None (correctly standalone). Repo committed+pushed at fc93248 (plus release_plugin.py wrapper). Packaged clean (description 1019/1024, 1 forward-slash entry, exit 0); cache was stale (pre-v1.10) so real drift, packaged and staged. Gabriel confirmed the Save-skill click. Post-install verify: skills-plugin cache SKILL.md now v1.10, single file, raw+normalized byte-match the repo. Ledger entry cleared. Content: Step 0 plugin-member repo-path clarification (top-level dir, not plugins/<plugin>/skills/). Companion .claude fix pushed same pass: append-event-log.py BOM tolerance (620612d/ea0f9f1).

## 2026-07-17 - package-and-stage-skill v1.10 reimported (Save-skill click confirmed)

Standalone single-file reimport via Entry Point A. plugin_of => None (correctly standalone). Repo committed+pushed at fc93248 (plus release_plugin.py wrapper). Packaged clean (description 1019/1024, 1 forward-slash entry, exit 0); cache was stale (pre-v1.10) so real drift, packaged and staged. Gabriel confirmed the Save-skill click. Post-install verify: skills-plugin cache SKILL.md now v1.10, single file, raw+normalized byte-match the repo. Ledger entry cleared. Content: Step 0 plugin-member repo-path clarification (top-level dir, not plugins/<plugin>/skills/). Companion .claude fix pushed same pass: append-event-log.py BOM tolerance (620612d/ea0f9f1).

## 2026-07-17 — ora-cowork-heartbeat beacon recovery check

STILL STUCK. The Notion beacon page (`35c6ecd8-9e59-81d5-8d2c-d08002458b78`) still reads `Last heartbeat: 2026-07-15T21:57:21Z · Next expected: 2026-07-16T09:57:21Z` — identical to the known-stale baseline `2026-07-15T21:57:21Z`, and Notion's own as-of stamp on the fetch (`2026-07-15T21:57:30Z`) confirms the page has not been edited since. The LAMS registry confirms the task DID fire: `ora-cowork-heartbeat` shows `lastRunAt` `2026-07-17T10:46:53.712Z` with `lastScheduledFor` `2026-07-17T09:50:00.000Z` (the 05:50 ET slot, executed as an app-open catch-up), so this is "task fired but the Notion write still failed," not "task never ran" — the beacon is now ~37 hours stale against a 12-hour cadence and 16-hour watchdog threshold. The registry entry still carries no `approvedPermissions` array, consistent with the 2026-07-16 diagnosis; the alert email sent that day (~18:32 ET) recommended Gabriel check/re-approve the task's Notion permission grant in Cowork's Scheduled Tasks UI, and that grant does not appear to have been made.

## 2026-07-17 - ora-operations-extensions plugin reinstalled (README 7-skill correction)

Rebuilt ora-operations-extensions.plugin v0.1.2 from plugins/ora-operations-extensions/plugin-build.json via tools/build_plugin.py (9 entries OK, forward-slash paths, repo clean at HEAD a6a2677); no version bump - README-only fix. Gabriel confirmed the Save-skill click. Post-install verify against plugin cache rpm/plugin_01Sq7t7TEQEoa4G1asrLe8ms: README.md now reads "Seven institutional skills..." (was "Eight new skills..." pre-debt-management-exclusion); deal-retirement and submarket-spatial-analysis SKILL.md byte-match their canonical top-level repo copies (raw SHA256, no EOL-normalization needed) - both confirmed live via the plugin cache mirror, NOT the standalone skills-plugin shadow-copy path this fix exists to avoid. package-and-stage-skill Entry Point A (plugin-rebuild remedy).

## 2026-07-16 — Shipped commit-provenance guard; Tenant DB open items canonicalized (session close-out)

Two new hooks landed and pushed (`0b81232`, roster added to CLAUDE.md's Guards: line in
`de63351`): `commit-provenance-guard.py` + `commit-provenance-recorder.py` block a `git commit`
that would sweep another live session's uncommitted work into it. Fail-open, requires TWO
affirmative signals (foreign touched-set hit + live session within TTL), no lock ever held.
Gabriel explicitly rejected a hard claim-lock/mutex in favor of this shape — see
`feedback_fail_open_over_mutex_for_fleet_gates.md`, now the house default for future cross-session
coordination guards. Motivating incident: 4 concurrency collisions in one hour in this same
checkout, the worst being a staged MEMORY.md edit swept into another session's commit inside a
~30s window. Spec: `docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md`. Quick
reference for hitting the block: `reference_commit_provenance_guard.md`.

Separately, the Notion Tenant DB no-sync root-cause investigation's 4 residual action items moved
into `open-items-tracker.md` as OI-003 through OI-006 (build the workbook mirror from
`EXPORT_RentRoll`, add a real `Archived` property to the Tenant DB schema, dedup 2 stale Heritage
Pool Supply rows, confirm 4 tenant turnovers + the Soldier Trucking property conflict against
executed leases) — canonical descriptions live there now, `project_tenant_db_no_sync_rootcause.md`
carries only pointers. Also closed a stale claim in that file: `ora-master-workbook-ingest`'s
"should be 34 tabs" assertion was corrected to 49 earlier this session (`d5a1006`) and the memory
file had not caught up.

## 2026-07-16 — ora-skills: staged-frontmatter-validator review-fix shipped (5d33b99 -> ac51978)

Post-hoc gate + review of 3 commits the other concurrent session had already pushed to `ZeOoba/ora-skills` main (f46cfa8, 233349d, merge 5d33b99 — extracts `validate_skill_frontmatter` into a shared gate used by both packaging and a new `tools/hooks/pre-commit` staged-content check, closing the gap where a raw runtime-cache sync could skip frontmatter validation entirely). Gate green (19+32 tests, compile, hook syntax). Independent review (superpowers:requesting-code-review, isolated worktree at 5d33b99) returned "With fixes" — 2 Important, no Critical: (1) `validate_skill_frontmatter`'s per-file loop only exception-guarded the SKILL.md read, so an unreadable secondary staged file (e.g. merge-conflicted, no stage-0 index entry) propagated as a raw traceback instead of a clean finding; (2) `_staged_content()` omitted explicit `encoding='utf-8'` on its `subprocess.run` call, unlike every disk-based reader in the file, risking cp1252-locale mis-decode/crash on multi-byte UTF-8 staged content on Windows. Both fail-closed (no false-pass risk) — polish, not a safety gap.

Fixed both in an isolated worktree (`ora-skills-frontmatter-fix`, branch `fix-staged-frontmatter-review-followup` off 5d33b99) per the now-standard pattern: the shared checkout had live, unrelated concurrent WIP again (staged changes to build_plugin.py/pending_reimport.py on branch `plugin-reimport-routing`). Added exception handling around the loop's `_read(rel)` calls and explicit `encoding='utf-8', errors='replace'` to `_staged_content()`. 3 new tests (2 unit tests reproducing the unreadable-secondary-file case via the existing `read_text` injection point, 1 live-git-index test staging multi-byte UTF-8 content and confirming exact round-trip). 22/22 package_skills tests green, pending_reimport's 32 unaffected. Pushed via `git push origin fix-staged-frontmatter-review-followup:main` (clean fast-forward, re-verified immediately before push since state had moved), confirmed `origin/main` = ac51978, worktree + branch removed.

## 2026-07-17 — Built canonical open-items tracker (`open-items-tracker.md`), closing the dead-pointer incident that motivated it

Motivating incident: `oxford-cc-repo-health.md`'s "residual open items" line pointed at `session-context.md` as carrying "the live list" of two unresolved items (purge 2 dangling disabled LAMS entries; `ora-cam-reconciliation-annual` year-round-vs-seasonal timing). One sibling item (automation-health-monitor canonicalization) got a RESOLVED update logged inline in the same file same-day (2026-07-09); these two never did, and by 2026-07-16/17 `session-context.md` no longer mentioned either — the pointer had gone dead with nobody closing the loop. Both turned out to already be resolved (verified live, not assumed): `fleet-status.py` shows zero disabled LAMS entries fleet-wide; `ora-cam-reconciliation-annual`'s live cron `0 7 15 1 *` confirms the seasonal decision. Confirming that required a from-scratch investigation because the item text lived in two places (the source file's prose and the target file it pointed to) and only needed to rot in one for the trail to go cold.

Built `memory/open-items-tracker.md` as the single canonical home for open/residual/TODO items system-wide: one `### OI-NNN` row per item, OPEN/CLOSED status, opened/closed dates, evidence on closure, and an optional bounded `Auto-check` field (`registry_disabled_count` / `registry_field_equals`) that `memory-integrity-probe.py` can evaluate against live `fleet-status.py --json` output — no arbitrary code execution, just a closed vocabulary of registry comparisons. Migrated both closed items in as `OI-001`/`OI-002` with their closure evidence. `oxford-cc-repo-health.md`'s dead pointer now targets the tracker instead of `session-context.md`.

Extended `memory-integrity-probe.py` (report-only, wired into the existing daily `ora-health-guard` and twice-weekly `ora-cc-schematic-refresh` runs — no new scheduled task registered) with two checks: (a) any `open-items-tracker.md#OI-NNN` reference elsewhere in `memory/*.md` that doesn't resolve to a row in the tracker fails hard, same severity as an existing orphan-index-link finding; (b) any OPEN item whose `Auto-check` now matches gets a WARN nudging closure, without auto-closing anything. Extended `fleet-status.py --json` additively with `tasks` (per-task id/fleet/enabled/cron) and `disabled_by_fleet`, reused by the new checks rather than re-implementing registry discovery — kept the "GUIDs rotate, never hardcode, one source of truth" discipline intact.

Ratified pattern going forward: any file that wants to reference an open item points at `open-items-tracker.md#OI-NNN` and states nothing else about it — no paraphrase, no restated status. `ops_decision_log.md` stays a separate, narrower log (already-decided yes/no operational questions, not items with a mutable open→closed lifecycle) — checked its scope before deciding not to fold this into it.

## 2026-07-16 — ora-skills: shared-dep direction-aware reconciliation shipped (10f042f + follow-up)

Shipped 3 commits to `ZeOoba/ora-skills` main (`35cdbca..15f5497`): 7e6d14d (psa-reconciliation description trim), 10f042f (pending_reimport.py `shared-deps` subcommand + `candidates` advisory — direction-aware reconciliation of shared repo-root deps against the runtime cache: REPO-AHEAD/CACHE-AHEAD/DIVERGENT/UNKNOWN, closing the 2026-07-16 target-markets.json no-direction gap), and a same-day review-fix commit 15f5497.

Gate: 21+6 tests, compile clean, `shared-deps` sanity check all 5 target-markets.json consumers in sync. Independent local review (superpowers:requesting-code-review) returned "Ready to merge: With fixes" — 2 Important issues, no Critical/security/correctness bugs: (1) package-and-stage-skill step 2 didn't consult the new direction advisory before treating a shared-dep hash mismatch as reimport-needed, so a session could still reimport a CACHE-AHEAD dep and reproduce the incident the commit was meant to prevent; (2) the git-integration layer (shared_dep_report/_git_text/_git_blob_bytes/_file_history_hashes) had zero regression coverage, only the pure classifier did. Gabriel elected to fix both before push rather than ship with a known gap.

Mid-fix, discovered a second session (01a43b3e) actively editing the same two target files (package-and-stage-skill/SKILL.md, tools/pending_reimport.py, tools/test_pending_reimport.py) in the shared ora-skills checkout — a live build_plugin.py/plugin-packaging feature, unrelated to this fix. Isolated the review-fix work into a fresh git worktree off commit 10f042f (`git worktree add ../ora-skills-shipfix -b shipfix-review-followup 10f042f`) rather than risk clobbering their uncommitted WIP, since a worktree only pulls from committed history. Added package-and-stage-skill v1.8 (step 2 now requires checking `shared-deps` direction before repackaging a mismatched shared dep; CACHE-AHEAD/DIVERGENT stop for manual reconciliation) and 11 new SharedDepGitIntegration tests (real git repos, not just the pure classifier) to tools/test_pending_reimport.py (21->32 total). Pushed via `git push origin shipfix-review-followup:main` (clean fast-forward), verified `origin/main` = 15f5497, then removed the worktree and force-deleted the local branch (content already confirmed on origin).

Left the shared checkout's local `main` ref 1 commit behind origin deliberately — a `git pull`/merge there would touch the same 2 files the other session has uncommitted edits on, silently rewriting their working tree. That reconciliation is the other session's to do when it commits its own work.

No scheduled-task or Notion changes; tools/pending_reimport.py and package-and-stage-skill/SKILL.md are live on disk immediately (no Save-skill reimport needed for tooling).

## 2026-07-16 — membership-guard.ps1 sticky-fold-in bug fixed (code change, not just a state-file workaround)

Implemented the actual fix for the bug found earlier tonight (see the prior "ora-task-integrity-guard next-run-clean confirmed by live dry-run" entry this same day): `scheduled-tasks/ora-task-integrity-guard/membership-guard.ps1`'s once-daily `.lams.json` snapshot fold-in unconditionally trusted a stale `true` over the live direct registry scan, which had already correctly determined an id was gone.

**Change:** added `$liveLamsOk` tracking — set `true` when the live direct scan successfully parses at least one store this run. The snapshot fold-in's mutation of `$current` is now gated on `-not $liveLamsOk`: when the live scan succeeded, it is treated as closed-world for this run and the once-daily snapshot is skipped entirely for mutation purposes (still contributes to `$stores`/staleness reporting). Added a `snapshot_suppressed` boolean to the output JSON so this is directly observable per-run, matching a field name that had already appeared in the script's own docstring before I started (a second session was independently working the same fix — see reconciliation note below).

**Verified:** ran the patched script three times live. First run: `snapshot_suppressed:true`, confirming the live scan now wins; also surfaced a related latent issue — the snapshot fold-in's loop never had the direct-scan loop's one-time-task (`fireAt`) skip, so two one-time tasks (`ora-cam-data-backfill`, `ora-counsel-review-standard-positions`) had been wrongly baked into the persisted baseline as tracked recurring entries by earlier (pre-fix) runs; suppressing the fold-in surfaced them as a one-time false "disappeared" in that run's output (no real alarm fired — this was a manual diagnostic run, not the scheduled task). Second and third runs: fully clean (`disappeared`/`disabled`/`added` all empty, `snapshot_suppressed:true`, `enabled_total:20`) — baseline is self-consistent and stable going forward.

**Reconciliation note:** this file is edited concurrently by another active session that had already started the same fix (evidenced mid-edit by an unexplained `snapshot_suppressed` mention appearing in the docstring before I wrote it). Continued per explicit instruction rather than backing off. `membership-guard.ps1` (and its sibling `guard.ps1`) are gitignored (`.gitignore:57: /scheduled-tasks/*/*` opts in only each task's `SKILL.md`, not its engine scripts) — this code fix cannot be committed to `ora-claude-config` regardless of who authored it; only this log entry is.

## 2026-07-17 — psa-reconciliation description fix + skill-store hardening (Task 1-3)

- **What:** Trimmed psa-reconciliation's frontmatter description 1274→956 chars (all trigger classes preserved), committed `7e6d14d`. Extracted `package_skills.py`'s frontmatter checks into a shared `validate_skill_frontmatter(skill_dir) -> list[str]`, wired it into the existing (previously target-markets.json-only) `tools/hooks/pre-commit` via a new `--check-staged` CLI mode, TDD (9 new tests, 5 pre-existing green), committed `f46cfa8` on worktree branch `psa-skill-hardening`. Codified the raw-sync-is-provisional doctrine: `ora-skill-store-drift-check` (OneDrive `Documents\Claude\Scheduled\ora-skill-store-drift-check\SKILL.md` — NOT in the ora-skills git repo, a Cowork/LAMS scheduled-task home) bumped v1.9→v1.10, new step 2g cross-checks `event_log.md` for a confirmed Save-skill install before calling a hash-matched skill IN-SYNC; no match → REIMPORT-PENDING (index-unregistered). Mirrored the one-liner into `rules.md` §15 (dateless per policy).
- **Why:** psa-reconciliation's SKILL.md had been synced straight into the AppData runtime cache by an earlier Code-surface session, bypassing `tools/package_skills.py`'s frontmatter validation entirely — the cache read hash-IN-SYNC even though its description (1274 chars) would have been REJECTED by the sanctioned packager. Nothing at commit time caught the defect either, since `package_skills.py` only validates at package time.
- **Root-cause note:** the task brief assumed `ora-skill-store-drift-check`'s SKILL.md lived in the ora-skills git repo (framed as a pure Code-surface job); it doesn't — confirmed via Glob (negative) + filesystem cross-check per `reference_memory_scope_fragmentation.md`-adjacent doctrine (never trust a negative Glob alone). Edited the real Cowork/LAMS home directly (editing a scheduled task's SKILL.md is authoritative, per `reference_cc_scheduler_filepath_mechanism.md`), not the repo.
- **Concurrent-writer note:** session `01a43b3e` was live on the ora-skills MAIN checkout with uncommitted WIP in `tools/pending_reimport.py`/`tools/test_pending_reimport.py` (a hash-normalization refactor) for the full duration of this work. Per rules.md §14, isolated Tasks 2-3's ora-skills-repo work into worktree branch `psa-skill-hardening` (`.claude/worktrees/psa-skill-hardening`) rather than building on the shared checkout; Task 1's single-file commit was staged with an explicit path (never `git add -A`) directly on main since it touched no file the other session had modified. Worktree not yet merged back to main — pending local code review.

## 2026-07-16 — ora-task-integrity-guard next-run-clean confirmed by live dry-run; membership-guard.ps1 sticky-fold-in bug found + baseline corrected

To confirm tomorrow's (2026-07-17 12:54 ET) scheduled `ora-task-integrity-guard` run reports clean re: the ora-am-brief LAMS retirement, ran all of its STEP-3 alarm-surface engines live rather than asserting confidence: `guard.ps1`, `membership-guard.ps1`, `registry-membership-probe.py`, `emit-fleet-heartbeat.py`, and Step 2.75's `task-folder-registration-probe.py` (skipped script 3, `push-fleet-heartbeat.ps1` — a failure there is a STEP-4 note only per the guard's own doc, not an alarm condition, so not needed to confirm "clean").

**Findings, in order:**
1. `guard.ps1` first run: `restored:["ora-skill-text-audit"]` (unrelated to ora-am-brief — its LAMS-side SKILL.md was stale/missing and got repaired from a mirror, newest-wins, no data loss). Re-run immediately after: fully clean (`restored:[]`) — confirms it was a one-time, idempotent repair, not a recurring alarm source.
2. STEP 0.5 (today's CC/MCP fleet snapshot) had not actually been written today despite the guard's own `lastRunAt` showing a 17:00 UTC run — wrote `_state-history/2026-07-16.cc.json` by hand (fresh `list_scheduled_tasks` capture) to unblock `membership-guard.ps1`'s diff. Not deeply root-caused; flagged for awareness only.
3. **Real bug found:** `membership-guard.ps1`'s `.lams.json` fold-in (lines ~64-83) merges any snapshot-listed task into `$current` whenever the snapshot says `true`, even when a more authoritative/live source already says otherwise (`if (-not $current.ContainsKey($id) -or $en) { $current[$id] = $en }` — a "sticky-true" merge with no freshness check). Today's `2026-07-16.lams.json` was captured at 15:15 UTC by `automation-health-monitor`, **before** the evening's LAMS ora-am-brief retirement, so every manual run this session kept resurrecting `ora-am-brief: true` into `$current` and thus into the persisted `_state-history/membership-state.json` baseline — which would have caused a **false "disappeared" alarm** on tomorrow's real scheduled run once `automation-health-monitor`'s fresh 2026-07-17 snapshot correctly excludes it (diffing a correct absence against a wrongly-`true` prior baseline). Corrected `membership-state.json`'s `ora-am-brief` entry to `false` by hand (the disappeared/disabled checks only fire `if ($prev[$k])` was `true`, so `false` permanently and correctly excludes it from future alarm consideration — matching the ratified-retirement intent). Did not fix the underlying merge-logic defect in the script itself (out of scope for this confirmation pass) — flagged separately.
4. Final live-run tally, all STEP-3 alarm conditions clear: `guard.ps1` restored/backed_up/missing_everywhere empty; `membership-guard.ps1` disappeared/disabled/added/parse_miss empty; `registry-membership-probe.py` exit 0, no `[ACTION]`; `emit-fleet-heartbeat.py` exit 0; `task-folder-registration-probe.py` exit 0 on both fleets.

**Conclusion:** tomorrow's scheduled `ora-task-integrity-guard` run (2026-07-17, ~12:54 ET) is expected to output `GUARD OK cc=21 lams=20 | MODEL: ...` and send no alarm email, contingent on no new drift between now and then.

**Deferred:** the sticky-true merge bug in `membership-guard.ps1`'s `.lams.json` fold-in is a latent defect independent of this incident — any same-day retirement landing after `automation-health-monitor`'s daily ~11:05 ET snapshot capture and before the next day's refresh could reproduce this exact false-alarm setup. Worth a proper freshness-aware merge fix later.

## 2026-07-16 — oxfordra.net deploy: GA4/analytics wiring, image/CSS/focus optimization, 404 mobile-nav fix

Pushed and deployed 5 commits on `website-canonical` `main` to production (`https://oxfordra.net`): `670ef4d` (deno.lock build exclusion), `df2bc2a` (real GA4 Measurement ID wired into all 16 analytics snippets), `f45a735` (image recompression/responsive srcset/deferred CSS/focus management), `ad44f6d` (GA4/LinkedIn tracking added to remaining pages), `fe1e271` (404.html mobile-nav fix — restored keyboard/SR-reachable links via horizontal-scroll strip, replacing a broken `display:none` under 960px). The 5th commit was authored mid-session by a concurrent Claude Code session (co-authored by Claude Sonnet 5) — surfaced to Gabriel before push since it wasn't part of the original push request; Gabriel confirmed include-and-deploy-all-5.

`site-qc-reviewer` gate: APPROVE (zero confidential-term matches against the live `confidential-terms.json` roster, no broken links/assets, CSP preload-onload pattern confirmed non-breaking under current headers, 404 nav strip verified keyboard/SR-reachable). Deploy via `netlify deploy --build --prod` (MCP deploy-services-updater tool was permission-denied, used the documented CLI fallback); prod deploy only re-uploaded 2 changed files, confirming the concurrent session had already CLI-deployed most of this content live minutes earlier — the git push brought origin/main in sync with what was already running in production, closing the no-remote-backup gap flagged at session start. Post-verify: curl 200 on `/` and `/404.html`; page content confirmed live.

Non-blocking follow-ups flagged, not yet actioned: (1) convert the 5 pages using the preload-onload CSS pattern (index, about, contact, tenant-application, markets/index) to the safer `media="print"` swap already used elsewhere on the site; (2) LinkedIn Insight partner ID is still the placeholder `XXXXXXX` across all 16 analytics snippets.

## 2026-07-16 — CC/MCP residuals closed for LAMS ora-am-brief retirement; registry-membership-probe.py ratification bug fixed

Closed out the CC/MCP-surface residuals from the same-day LAMS ora-am-brief retirement (see prior entry "RATIFIED: LAMS ora-am-brief retired" and `memory/project_ora_am_brief_lams_retirement_blocked.md`, now RETIRED + VERIFIED). Concurrent-writer check clear (registry-membership.log latest entry complete, not mid-edit; `~/.claude` git tree clean at `242fd6f`).

1. **CC/MCP copy verified healthy** — `list_scheduled_tasks` on this CC surface: `ora-am-brief` `enabled:true`, cron `0 6 * * *`, path `~\.claude\scheduled-tasks\ora-am-brief\SKILL.md`.
2. **LAMS drop confirmed live (not just Cowork-view)** — `fleet-status.py` (reads both registries regardless of surface): `ora-am-brief` appears exactly once, cc-only, `on`; absent from lams.
3. **Roster refresh** — re-ran `registry-membership-probe.py`. It raised a false `[ACTION]` on the LAMS drop instead of auto-ratifying, despite this file's RATIFIED token being present and within the 14-day window. Root cause: `ratified_drops()` split event_log text on the literal `"\n### "` (three `#`), but `append-event-log.py` enforces and every real entry uses `"## "` (two `#`) headers — auto-ratification had never matched a real entry against this file's actual format. Fixed the split token to `"\n## "` (`~/.claude/maintenance/registry-membership-probe.py`); re-ran and directly unit-tested `ratified_drops()` against the live file — now correctly resolves `ora-am-brief` as ratified. Re-ran the probe again: `OK -- no actionable drift`, roster regenerated (cc 21 / lams 20 enabled recurring, session-context.md fleet block current).
4. **Ledgers updated** — `Claude_Workspace/00_Governance/outputs/2026-06-10_fleet-disposition-ledger.md` and `memory/oxford-cc-repo-health.md` both got a dated entry recording the retirement + this fix.
5. **Integrity guard check** — confirmed `ora-task-integrity-guard`'s STEP 1.5 runs this same probe daily; with the fix in place its next run will report the LAMS drop as an auto-ratified INFO (already consumed as this run's snapshot baseline), not a false alarm.

No registry-JSON edits. No re-registration of the LAMS copy (per do-NOT-re-register note). `~/.claude` is git-tracked to private `ZeOoba/ora-claude-config` — the probe fix is a plain code change, no deal terms touched.

## 2026-07-16 — event_log.md rolled over (3083 → 604 lines) via new rollover-event-log.py script

Live log had grown to 3083 lines (~3x the ~1000-line soft cap) with no dedicated rollover tool — the 2026-07-09 rollover was done by hand. Built `~/.claude/maintenance/rollover-event-log.py`, mirroring `append-event-log.py`'s mtime-guard + atomic-replace + pre-write backup + post-write verify pattern, since this is a structural single-writer edit on a file multiple concurrent sessions were actively appending to today. Dry-run first (`--dry-run`), confirmed the cut landed cleanly on a `## ` entry boundary, then ran for real.

Cut at "2026-07-16 — cc-audit-army generalized to repo-generic audits (Gabriel-directed)" — entries at and before that point (2483 lines) moved to `_archive/event_log_2026-07-16.md`; live log now 604 lines with a pointer at the bottom. No content altered — straight cut, consistent with the 2026-07-09 precedent. `memory-policy.md`'s rollover note updated to point at the new script. Known pre-existing defect not fixed in this pass (out of scope for a mechanical rollover): a single 2026-07-12 entry sits out of newest-first order just after the 2026-07-09 archive pointer (now inside the new archive file) — flagged, not reordered.

## 2026-07-16 — Master Workbook corrected: Heritage Pool Supply lease end → 2031-09-30 (DSOR was wrong)

Gabriel confirmed Heritage Pool Supply (7658 Fishel, Kristen Morgan, $8,540/mo) **exercised their
option to renew 5 years through 2031-09-30**. The live Master Workbook still carried
`2026-09-30 / "Expiring Soon"`. Notion's `SRS Distribution / Heritage Pool Supply` row already had
2031-09-30 — **Notion was right, the DSOR was wrong.** Authorized in-turn (Invariants 4 + 5).

- **Change:** `Master Tenant Rent Roll!I81` 2026-09-30 → 2031-09-30. One cell. Written via **Excel
  COM**, not openpyxl (openpyxl warns "Conditional Formatting extension is not supported and will
  be removed" on save — a lossy round-trip on Eric's model; `data_only=True`+save would flatten
  every formula across all 49 tabs).
- **Verified downstream:** `L81` Status Expiring Soon → Active · `L143` portfolio counters
  127A|7S|3E → **128A|6S|3E** · `I144` **portfolio WALT 2.36 → 2.45 yrs** (the understatement this
  fixes) · `EXPORT_RentRoll` I77/L77 propagated. Cell-level diff vs backup across all 49 tabs:
  **exactly 1 formula/literal change**; all other deltas are `TODAY()`-volatile recalcs.
- **Backup:** `Documents\Claude\_backups\Master Excel Template Company Wide -- Oxford_pre-HeritagePool-leaseend-fix_20260716.xlsx` (sha-verified identical pre-write).
- **⚠ Gotcha recorded:** the workbook is OneDrive-hosted → Excel **AutoSave persisted the cell
  before the error path could `Close($false)`**; the COM call then threw `RPC_E_CALL_REJECTED`
  *after* the write already landed. A COM error on this workbook does NOT imply rollback — always
  back up and diff to establish ground truth.
- **Doctrine:** DSOR ≠ infallible. This is the confirmed counterexample that forces the planned
  Tenant-DB mirror to be reconcile-and-escalate, never blind-overwrite — a naive workbook→Notion
  sync would have destroyed the correct 2031 date. See
  `memory/project_tenant_db_no_sync_rootcause.md` + spec
  `Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`.
- **Still open:** dedup the two stale Notion Heritage Pool rows (2026-09-30) vs the correct SRS
  row — Notion untouched this session.

## 2026-07-16 — RATIFIED: LAMS ora-am-brief retired (migrated to CC/MCP)

RATIFIED drop — task id `ora-am-brief` (LAMS/Cowork fleet). Auto-ratify token present for registry-membership-probe.py.

Retired the LAMS/Cowork copy of `ora-am-brief` permanently, archive-first per register-scheduled-task v2.7 RETIRE doctrine. Reason: the Cowork sandbox has no local COM access, so the Outlook email leg (`send-via-outlook.ps1`) structurally could not send — confirmed by the 2026-07-16 edition never sending despite 7/13–7/15 sending fine. Gabriel-approved migration to CC/MCP on 2026-07-16; a CC/MCP registration (same content, same cron `0 6 * * *`, three surface adaptations in its own frontmatter) is live and independently confirmed at `~/.claude/scheduled-tasks/ora-am-brief/SKILL.md`. Both fleets had been double-firing daily at 06:00 ET; this retirement removes the LAMS duplicate.

Actions (in order): (1) concurrent-writer check clear (no live sibling session; registry-membership.log latest entry not mid-edit); (2) disabled LAMS entry via `update_scheduled_task enabled:false`; (3) moved folder to `Documents\Claude\Scheduled\_archive_2026-07-16_retired-to-ccmcp\ora-am-brief\` — verified SKILL.md present at new path, ENOENT at old path; (4) deleted LAMS registry entry via `delete_scheduled_task` (9 run sessions archived). CC/MCP copy untouched (SKILL.md intact, 217 lines). No registry-JSON edits anywhere. Producer-script check clear — `open_sessions_probe.py` (Block C.5.6) co-owned by `ora-open-sessions-board` and the CC `ora-am-brief` copy, so no orphaning. `session-context.md` do-NOT-re-register roster updated with the LAMS-copy retirement note (CC/MCP copy explicitly excluded — must stay enabled).

## 2026-07-16 — Leaked Netlify MCP proxy token found in oxford-site git repair, purged, rotated — CLOSED

Follow-on from repairing `Claude_Workspace/01_Workspace/oxford-site`'s corrupted `.git` (missing
`refs/` entirely). During the mandated "second look" pass before retiring the checkout, found a
live-looking Netlify MCP proxy token (JWE-encrypted, tied to production site `95ac0a0f-a84d-4400-
b919-b8d7a8526646`) hardcoded in plaintext in `run-deploy.bat`, already sitting in the recovery-
baseline commit. Never pushed anywhere (no remote configured on this checkout), so exposure was
local-only throughout.

Remediation, in two passes:
1. Redacted the working file; rewrote history to drop the token from the root commit (`c886245`),
   using a transport-level `git clone --no-local` after discovering in-place `git gc`/`repack -ad`
   left the blob recoverable in the pack — verified zero matches across every object afterward.
2. A secondary sweep of the preserved forensic archive (`.git-corrupted-20260716/`, ~26,800 objects,
   scanned for a full secret-pattern set) caught that the archive itself — kept "for forensics" —
   was still tracked in the live repo's history, meaning the first purge wasn't actually complete
   (same token blob, still technically recoverable). Untracked it from git (kept on disk, gitignored;
   also independently preserved in a non-OneDrive backup), repeated the clean-clone purge (pack
   268,746 KB → 9,917 KB), reverified zero hits. Also found 2 false positives (dotenv npm package's
   own README placeholder key text, bundled in an old committed `node_modules` snapshot) — confirmed
   not real. Final state: `main` @ `8c97652`, no remote, no reflog, no dangling objects.

**Token rotated same day (Gabriel):** revoked "Netlify MCP" under Authorized Applications
(app.netlify.com → User settings → OAuth), reconnected the Netlify MCP connector
(`a66aaa4a-ffcd-4066-b2af-79c4ce807809`). Verified live post-reconnect via the connector itself
(`get-user` → ggoldberg@oxfordra.net; `get-project` on `95ac0a0f…` → deploy state `current`/`ready`).
No other on-disk reference to the old token found (searched `~/.claude` JSON configs). Thread closed.

## 2026-07-16 — Correction: Monthly Checklist location (Gabriel-supplied)

Gabriel corrected the last open item from the EOD Ledger remediation: the Monthly Checklist is not a separate/unreachable file — it's a sheet (`Monthly Checklist`, plus an `EXPORT_MonthlyChecklist` mirror tab) inside the same Master Workbook already confirmed locally reachable at `...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`. Verified directly: both tabs exist (`get_workbook_metadata`), and `Monthly Checklist` has real, current content (a WE PAY / WE RECEIVE loan-payment matrix by property/counterparty, not a stale placeholder). Updated `ora-pm-ledger` SKILL.md's DSOR-reachability note (previously wrong, written earlier today) to reflect this — future runs should read the sheet directly rather than declaring a COVERAGE GAP or citing the stale standalone "Monthly Checklist Accounting+Operations.xlsx" at the OneDrive root.

Follow-on not yet done (flagging, not building unasked): `ora-master-workbook-ingest`'s source-of-truth tab list doesn't currently include `Monthly Checklist` — since ora-pm-ledger reads it live daily anyway, this is a nice-to-have for the weekly mirror/dashboard, not a blocking gap.

All 3 EOD Ledger decision items plus both DSOR/Monthly-Checklist coverage-gap items are now closed. Only the LAMS ora-am-brief retirement handoff remains open (user started task_98448323 in a separate session).

## 2026-07-16 (evening) — Full re-verification of all 15 original drift-check findings: negative result, nothing open

Prompted by a direct request to check whether the "other 7" (no-action/CRLF-FP group) tied back to anything still open, after the daily-brief saga showed "closed" can hide an unpushed commit or un-clicked install. Re-checked all 15, not just 7.

- **Push check:** all 9 relevant commits (batch1 x4: `e605d40`/`1474349`/`fd030b6`/register-scheduled-task's `d5ca189`; batch2 x4 installs: `a66612a`/`e207b7f`/`9aa26d4`/`d0c0cb1`; parcel-data-recovery merge `943f16c`; register-scheduled-task v2.7 `98c52d2`) confirmed via `git merge-base --is-ancestor <hash> origin/main` — all on origin/main, no unpushed-commit gaps.
- **Repo↔cache hash check (EOL-normalized), all 15:** 14/15 clean on first pass. `oxford-cc-strategic-audit` initially read DRIFTED — investigated rather than reported as a new finding: cache carries 228 trailing NUL bytes (the documented platform-upload padding artifact, ora-skill-store-drift-check step 2b), which the first-pass check didn't strip. Re-hashed after stripping `\r` and `\000` from both sides — exact match (`6737ba37...`). Not real drift; a gap in this session's own check, not the skill store's.

Nothing from the original 2026-07-16 15-finding drift-check (Notion comment `39f6ecd8-9e59-814b-83d3-001d8db86fff`) ties back to anything still open.

## 2026-07-16 — EOD Ledger decision items executed (Gabriel's picks: all three "Recommended" options)

Following up the earlier remediation pass, Gabriel chose all three recommended options and asked for them to be built.

**1. ora-am-brief moved to CC/MCP fleet.** Registered `ora-am-brief` on CC/MCP (`0 6 * * *`, taskId `ora-am-brief`, file `C:\Users\Owner\.claude\scheduled-tasks\ora-am-brief\SKILL.md`) — content carried over from the LAMS spec verbatim except: (a) Block B now cites the Command Center alerts engine for critical dates instead of independently re-deriving from Notion (implements decision #2 below); (b) Block D drops the Cowork-only `mcp__cowork__update_artifact` step and reads the Master Workbook at its confirmed local path (`...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`, same path `ora-master-workbook-ingest` already uses) instead of an assumed mount; (c) NON-MUTATION GUARANTEE's output list drops the Cowork artifact reference. `fleet-status.py` confirms CC/MCP 21->22. Retiring the superseded LAMS registration was handed off via `spawn_task` (task_98448323, "Retire LAMS ora-am-brief scheduled task") since this session can register on CC/MCP but can't write to the LAMS registry — needs a Cowork-side session to archive-first retire it and re-verify via its own `list_scheduled_tasks`.

**2. Command Center ruled authoritative for critical dates.** Implemented directly in the new CC/MCP `ora-am-brief`'s Block B as an explicit OVERRIDE to the shared `daily-brief` skill's Section 4b/4c: read the Command Center Daily Brief / `portfolio.json` (DSOR-lineage) rather than independently deriving lease/debt dates from a live Notion read; record a COVERAGE GAP rather than falling back to independent computation if Command Center's data is unavailable that morning.

**3. HubSpot renewal-signal fix.** Edited the shared `daily-brief` SKILL.md Section 4b directly (now v2.7) — replaced the "no HubSpot renewal activity" check (root cause: all ~50-56 renewal deals permanently parked at HubSpot's default stage 1, so the signal was inert for every tenant) with a Notion-native check: renewal activity now = `Renewal Option Terms` non-empty OR `Lease Extension / Amendment Log` has an entry OR `Next Renewal Action Date`/`Renewal Offer Date` is set. This is the actual producer of the "no renewal signal" defect the EOD Ledger flagged — HubSpot's dealstage itself was never touched (that's a separate, not-yet-authorized fix if Gabriel later wants HubSpot's own pipeline made meaningful).

**Bonus finding while investigating #1 (Block D adaptation):** the ORA Master Workbook IS present as a local file on this machine (`...\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`, OneDrive-synced, `lastModifiedDateTime` 2026-07-15) — the same path `ora-master-workbook-ingest` already reads directly via Desktop Commander. The original EOD Ledger's "DSOR not locally resolvable" claim was a miss, not a structural gap: neither the local path nor `sharepoint_search` (both confirmed reachable) were tried before declaring the gap. Added a DSOR-reachability check to `ora-pm-ledger` SKILL.md's C.2 mandated-source discipline documenting both paths, so future runs try them before recording the gap. The **Monthly Checklist** (31/59-item workbook) genuinely remains unreachable — confirmed absent from both the local `eric spreadsheets` folder and SharePoint search by name/category; only a stale (2026-04-17) copy exists at the OneDrive root. That specific gap stands; recommend asking Gabriel directly where the live version lives.

Net: 2 of 3 decision items fully closed this session (CC/MCP registration live, daily-brief HubSpot fix live); LAMS-side retirement is the one open handoff (chip pending, not yet actioned).

## 2026-07-16 (evening) — daily-brief v2.7 INSTALLED — Gabriel's Save-skill click confirmed, ledger cleared

Post-install verify: cache `SKILL.md` raw SHA256 exact match to repo (`129c50d5...`, no EOL divergence this import), cache `target-markets.json` raw SHA256 exact match to repo root (`f06e71e9...`), v2.7 version marker present in cache, cache mtime 2026-07-16 18:51 (consistent with the click). `python tools/pending_reimport.py clear daily-brief` run — ledger entry cleared, `_staging/PENDING_REIMPORT.md` deleted (documented behavior: file is removed once empty, not an error despite the script's exit 1). Runtime and repo both at v2.7 (commit `936f9f4`, on origin/main).

No deploys, no scheduled-task changes, no email.

## 2026-07-16 (evening) — daily-brief v2.7 packaged + staged for reimport (Entry point A)

Repo commit `936f9f4` (Notion-vs-Workbook lease-expiration cross-check, Patch 10) pushed to origin/main this session. Packaged via `tools/package_skills.py _staging/2026-07-16_daily-brief-v2.7 daily-brief` — 2 entries OK (SKILL.md + injected target-markets.json), description 378/1024 chars. Shared-dep pre-check: packaged `target-markets.json` SHA256 `f06e71e9...` matches repo-root source exactly — no drift. Multi-file skill → routed to Cowork **Save skill** button per multi-file doctrine (desktop Settings→Capabilities silently drops bundled files). Runtime cache stays at pre-v2.7 until Gabriel's click; `_staging/PENDING_REIMPORT.md` entry for daily-brief (commit `936f9f4`) stays open until then — clear only after a confirmed post-install hash-verify.

No deploys, no scheduled-task changes, no email.

## 2026-07-16 — ora-am-brief follow-ups (4) + doctrine-probe gains a LAMS-fleet regression guard

Closed the four items flagged after the Block A callout fix earlier today.

**#1 — callout hardened from prohibition to literal template.** A prohibition ("must NOT narrate SOFR freshness") is weaker under generative pressure than a fixed skeleton. A.3 now carries a CALLOUT TEMPLATE: the callout is assembled by concatenating only the true clauses from an enumerated menu (UST-derived / BBB-stale / FedWatch / 30Y-FRM / overnight-SOFR-unobtainable). There is deliberately NO menu clause for the SOFR 30/90/180-day averages or Index, so the model has no slot to narrate them. The earlier hard rule remains as backstop.

**#2 — §7 Sources line patched (live Notion, ephemeral).** Removed the stale "carried forward from 2026-07-15 patch" phrasing; now states overnight SOFR eff. 07-15, averages/Index eff. 07-16 via the local direct pull. Self-regenerates tomorrow under the new rule; this was a same-day cosmetic cleanup.

**#3 — version pin REMOVED, not bumped.** ora-am-brief cited "daily-brief skill v2.5" in two places (frontmatter desc + Block B instruction); installed is v2.7. Bumping just resets the rot clock (feedback_prompt_current_state_prose.md). The pin isn't load-bearing — the skill resolves by name — so both references now say "the installed daily-brief skill" with no version. Stops the rot permanently.

**#4 — NEW doctrine-probe Check 12 (regression guard) + a fleet-coverage finding.** FINDING: doctrine-integrity-probe.py's scheduled-task scanning uses `CLAUDE_DIR/scheduled-tasks` — the CC/MCP fleet ONLY. The entire LAMS/Cowork fleet (OneDrive\Documents\Claude\Scheduled\, 20 tasks incl. ora-am-brief) is invisible to every check in the probe. So the casually-proposed "grep the scheduled SKILL.mds for cross-task narration" would have scanned the wrong fleet and never seen the file it was meant to guard. Gabriel chose (via AskUserQuestion) the narrow regression guard over a general LAMS-wide heuristic (no machine-readable field-ownership map → the general version is keyword-noisy). Check 12: reads ora-am-brief's known OneDrive path (fail-open, WARN-only, live_mode only) and asserts 3 fix sentinels are present (CALLOUT TEMPLATE header, the "deliberately NO clause" guarantee, CALLOUT SCOPE hard rule). It is a fix-PRESENCE check, not an anti-pattern grep — the hard rule legitimately QUOTES the forbidden phrases, so a co-occurrence scan would flag the fix itself. TDD: 6-assertion unit test (red→green), py_compile clean, full probe run exit 0, my check prints "intact (3/3)", the one WARN is the pre-existing benign confidential-term self-check. NOT committed (steady-state uncommitted drift in ~/.claude; user did not ask to commit).

**Open (not built, by decision):** general cross-task-narration detection across the LAMS fleet — deferred; would need a LAMS scan root (cloud/fail-open) + a field-ownership map to avoid false WARNs across 20 tasks. Check 12 can be generalized into it later if warranted.


## 2026-07-13 — ora-lease-expiration-brief: re-hit the confirmed DC PowerShell $var-stripping bug; closing note corrected

During the ORA Lease Expiration Brief scheduled-task run, the Outlook COM send (`send-via-outlook.ps1`) was first attempted with an inline `start_process` command of the form `$body = Get-Content ...; & send-via-outlook.ps1 ... -Body $body -Html` — this is exactly the failure mode already logged in [reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md) (confirmed engine-wide 2026-07-12): `$body` was silently stripped from the `-Command` string, producing a `The term '=' is not recognized` parse error immediately followed by a real (malformed, ~5-byte) send to ggoldberg@oxfordra.net. A second attempt wrote a `.ps1` file but hit the sibling nested-encoding issue from an em dash in an inline literal (`reference_desktop_commander_nested_quote_mangling.md`'s "quoting layer" family). Root-caused and fixed on the third attempt by writing the body to a file directly (`write_file`) and invoking `send-via-outlook.ps1 -BodyFile ... -BodyFormat html` from a `.ps1` script file (no inline `$var` in the `-Command` string) — this matches both the already-documented DC workaround and the pre-existing, actively-maintained doctrine in `_shared/README-SEND-PATTERN.md` (updated 2026-06-15) and `_shared/EMAIL_DELIVERY.md`, which already mandate exactly this file-based `-BodyFile` pattern fleet-wide.

**Correction to my own initial framing:** the session's closing note characterized "prefer `-BodyFile` over inline `-Body $var`" as a new workflow-optimization recommendation. That was wrong — it's not a gap to fix, it's an existing, correctly-designed doctrine I failed to follow on the first two attempts. The actual miss was process discipline: not checking `reference_desktop_commander_powershell_variable_stripping.md` / `_shared/README-SEND-PATTERN.md` before building the send command, despite this bug being confirmed engine-wide the day before (2026-07-12). Logging here per Calibrate convention so the next scheduled-task-authoring or ad-hoc-send session checks the existing reference first rather than rediscovering it a fourth time.

No doctrine change made (none needed) — this is a "read the existing reference first" miss, not a doctrine gap.

---

*Entries at and before “2026-07-16 — ora-am-brief follow-ups (4) + doctrine-probe gains a LAMS-fleet regression guard” rolled over 2026-07-18 to [_archive/event_log_2026-07-18.md](_archive/event_log_2026-07-18.md) per memory-policy.md's rollover rule.*


## 2026-07-22 (cont.) — automation-health-monitor workflow-optimization follow-through (Gabriel-directed, in-session)

Two of the 2026-07-22 Automation Health report's workflow-optimization candidates were implemented same-day, in the same session, on Gabriel's explicit instruction:

1. **`ora-health-guard` v1.1 — Block A.0 wake-lateness immediate alert.** New first step: on every fire, compare actual start time to the 05:15 ET cron target; if >45min late, immediately send a standalone `🌙 Overnight machine-offline detected` email (ggoldberg-only) rather than waiting for `automation-health-monitor`'s ~11:05 ET run to discover the same catch-up burst 3-6h later. **Known limitation, stated explicitly to Gabriel:** this is NOT a true pre-9am external ping — no on-machine scheduled task (any fleet) can fire before the machine itself wakes, so this only front-runs the *previous* 11:05 detection, it doesn't beat the wake event itself. A true independent-of-machine watchdog would require extending the existing GitHub Actions/Power Automate dead-man's-switch pattern (same one already watching `ora-cowork-heartbeat`'s 16h threshold) — out of reach from this Cowork session (no GitHub/Power Automate connector available here). Flagged as a follow-up requiring a session with that access; external dead-man issue `ora-claude-config#11` (referenced in the A2 beacon note) is the likely home for it.

2. **`ora-health-guard` v1.1 — Block B.3.5 cross-fleet beacon.** New Notion page `3a56ecd8-9e59-8152-83b6-c61cec736f2b` ("🔌 Connector Pre-Flight — Status", under Ops Hub `32b6ecd8`), written every Block B run (pass or fail) with `status`/`last_run_et`/`failed_connectors`/`subject_sent`. Closes a real gap found during the 2026-07-22 audit: `automation-health-monitor`'s only prior check for this block was an Outlook Sent Items subject search, which came up empty that day despite the block having actually fired — forcing an unnecessary ℹ️ informational downgrade. `automation-health-monitor` v1.14 Step 0.55 table repoints this row to the new beacon as PRIMARY, keeping the Sent Items search as secondary/backup.

Both changes are additive-only to both SKILL.mds — no prior logic, table rows, or rules were removed or reordered. `automation-health-monitor`'s frontmatter description and end-of-file changelog were bumped to v1.14 with matching notes.

**SELF-CORRECTION, same session:** the first attempt to log this entry used Desktop Commander `write_file` without `mode: 'append'`, which defaults to `mode: 'rewrite'` — this overwrote the entire file (990→11 lines, ~183KB of history destroyed) before the append-vs-rewrite default was caught. Recovered via `git restore -- memory/event_log.md` (this file is tracked in the `.claude/projects/...` git repo, last commit `afc1334`, working tree was otherwise only CRLF/LF-different from HEAD — confirmed via `git diff --stat` before restoring, so nothing beyond the errant write itself was lost). Logging per Calibrate convention: **`write_file` calls against any file under `memory/` (or any tracked/historical file) must always pass `mode: 'append'` explicitly when the intent is to append — never rely on the tool's default.**


## 2026-07-24 — acquisition-underwriting v4.4 (STAGE 2.8 / FORG v1.0) installed via package-and-stage-skill Entry Point B

- Built on the Code surface via Entry Point A from `ora-skills` local `main` @ `4a29470e0f2e5370e4cc1bd4ebb0cd2f108d2f2d` ("ratify BDS-5 at 10 pts (Gabriel ruling 2026-07-23)"). NOT yet pushed to origin (`origin/main` = `979b12d480495f84e60b11cf110e74ad940ed02c`, which itself already carries STAGE 2.8/FORG — only the final BDS-5 10-pt ratification commit is ahead of origin).
- Handoff to Cowork took three attempts. First two failed silently: the referenced chat attachment never landed (`uploads/`, `uploads-tmp/`, and a full recursive filesystem sweep for the filename all came back empty, both times). Third attempt corrected course to a direct Desktop Commander real-filesystem path (`ora-skills\_staging\2026-07-24_acq-uw-v4.4-entrypointA\acquisition-underwriting.skill`), which succeeded.
- Entry Point B integrity pre-check: exists (62,148 bytes) confirmed · SHA256 `E77F37A8A12C4B9D312473B5BC8F05EE6EABDE4E91EEA6361451A4C97736199B` matched the handoff-supplied hash exactly · zip entries = `acquisition-underwriting/SKILL.md` + `acquisition-underwriting/target-markets.json` only, forward-slash paths · freshness: both files byte-identical (raw SHA256) to repo `acquisition-underwriting/SKILL.md` and repo-root `target-markets.json` at HEAD — no drift found.
- Staged to session outputs, `present_files`'d, Gabriel confirmed the **Save-skill click** (Cowork button, not desktop Settings→Capabilities — multi-file package).
- Post-install verification: runtime cache mirror (`...\skills-plugin\583f08bc-0123-4111-8158-8fe3d927e350\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\skills\acquisition-underwriting\`) contains both files, byte-identical (SHA256 match) to the packaged copy. SKILL.md header now reads **v4.4 — Buy Box & Scorecard v1.1**; STAGE 2.8 — Functional Obsolescence & Durability Grade (FORG v1.0, PROPOSED) confirmed present in the installed copy. Remaining "v4.3" hits are changelog history only, not the current header — expected, not drift.
- `python tools\pending_reimport.py clear acquisition-underwriting` → `not pending (nothing to clear)`; `_staging/PENDING_REIMPORT.md` does not exist on disk. No open ledger entry existed to close for this skill.
- Governance note: FORG v1.0 / STAGE 2.8 remains tagged PROPOSED/pilot in the installed SKILL.md (recommended, not yet mandatory outside FULL mode) — only BDS-5's 10-pt value is ratified, not the stage's mandatory status.


## 2026-07-24 (cont.) — register-scheduled-task v2.8 already in sync, no reimport needed (package-and-stage-skill short-circuit)

Invoked to close the register-scheduled-task v2.8 (commit 609164f, "require dated [MODEL:] tag at registration + PAUSE re-enable precondition") gap in `_staging/PENDING_REIMPORT.md` (pending since 2026-07-24T18:25Z) ahead of Monday's `ora-skill-store-drift-check` run.

**Step 0 (plugin-membership gate):** `plugin_of('register-scheduled-task')` -> `None` — standalone skill, not a plugin member.

**Step 1 (source confirm):** `git status --short -- register-scheduled-task/` clean; HEAD for the path = `609164f` (matches the ledger commit exactly).

**Step 2 (runtime-cache pre-check, single file — SKILL.md only, no subfolders):** repo `ora-skills\register-scheduled-task\SKILL.md` vs runtime cache `...\skills-plugin\583f08bc-0123-4111-8158-8fe3d927e350\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\skills\register-scheduled-task\SKILL.md` — file count 1=1, zero RAW SHA256 mismatch, zero missing-in-cache. Both copies read v2.8 header and identical body text (spot-checked, then confirmed by whole-file hash match — no EOL-normalization pass was needed since raw already matched). **Conclusion: the runtime cache is already at v2.8. A Save-skill install evidently already occurred for this commit; it was never logged and the ledger entry was never cleared** — the same unlogged-click pattern the skill's own v1.5 changelog (2026-07-15 near-miss) exists to catch.

**Per Step 2's short-circuit rule: STOPPED before packaging — no `.skill` was built, no Save-skill click was requested of Gabriel.** `python tools\pending_reimport.py clear register-scheduled-task` run to close the now-stale ledger line (cache re-sync is the qualifying event per the ledger's own clear-condition, regardless of which session's click produced it). `monthly-close` and `ora-flood-zoning-dd` ledger lines left untouched (out of scope this pass).

**Flag for Gabriel:** the install that produced this sync was not captured in this log by whichever session performed it — worth a quick check of other recent Cowork/Code session transcripts if attribution matters, but the cache content itself is unambiguous and correct at v2.8.

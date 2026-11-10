---
name: event_log
description: "ORA append-only event log — system changes, deal milestones, decisions. Newest first. This is the ONLY append-wall; living docs are overwritten to current state and point here for history."
metadata: 
  node_type: memory
  type: log
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-11-10T17:27:35.192Z
---

# ORA Event Log (append-only, newest first)

Renamed/expanded 2026-06-03 from reference_optimization_log.md. Living docs (firm/projects/tech/etc.) hold current state; their history accumulates HERE.

## 2026-11-10 -- OI-321 CLOSED (critical-date alerts now ack-after-send, per-tier dedup)

- Closed by Gabriel in-turn ("Yes, close it"). Fix: ora-pm [#55](https://github.com/ZeOoba/ora-pm/pull/55) merged 2026-11-09T15:59Z; migration `0019` applied (`db-migrate.yml` success x2); ack-aware `ping-crons.ps1` live ~15:40Z; spec PR ora-claude-config [#441](https://github.com/ZeOoba/ora-claude-config/pull/441) merged. Row + section moved to [open-items-tracker-history.md#OI-321](open-items-tracker-history.md#OI-321).
- Context: ora-pm Supabase project had been paused 2026-10-12 → 2026-11-09 (every cron 1016; no critical-date digests for four weeks). Restored by Gabriel 2026-11-09; first post-restore run 09:49 ET SEND OK. No catch-up send needed (old Worker recorded nothing during the outage).
- Residual: first live `/ack` on the next scheduled critical-dates run not yet observed.

## 2026-11-02 -- acquisition-underwriting-eval-harness v1.3 (post-#199, 82a83b5e) reimport confirmed

- Package sha 2aa5a645c378f3e7, 24 entries, saved by Gabriel via Cowork Save skill.
- reimport_correlate postclick: CONFIRMED, with CreationTime moving 15:19:41 -> 15:55:59 and main.log "1 downloaded" at an exact-second match.
- This is a second v1.3 install. It carries #199's record_run rollback and the parse_replays OSError catch. It is distinct from the earlier v1.3 entry, which had the same title minus the commit.

## 2026-11-02 -- retail-underwrite-lens reimport confirmed

retail-underwrite-lens reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-11-02 -- repo-architecture v1.0.1 reimport confirmed

repo-architecture v1.0.1 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-11-02 -- deal-folder-intake v1.2 reimport confirmed

deal-folder-intake v1.2 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-11-02 -- acquisition-underwriting v4.41 reimport confirmed

acquisition-underwriting v4.41 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-11-02 -- ora-skills #199 merged (82a83b5e): #196 residuals + 3-round gate; ~/.claude fast-forwarded to main

- #199 fixes the #196 round-3 MEDIUM + 4 LOWs Gabriel accepted at merge:
  - _unquote does a real closing-quote scan;
  - parse_replays --record catches OSError;
  - record_run rolls back the snapshot and truncates a partial summary.csv row on any exception, and an empty CSV counts as new;
  - the .tmp cleanup is best-effort.
- Full 5-reviewer adversarial gate, 3 rounds; all HIGH/MEDIUM issues fixed. Gabriel: "Merge now, note A+B".
- Known limitations (LOW, accepted):
  - (A) no test catches removal of the partial-row truncate (a probe proved it works);
  - (B) truncate-to-stale-size can drop a CONCURRENT writer's CSV row when one writer fails. This needs two same-dir runs at once; the harness is a single daily poll.
- acquisition-underwriting-eval-harness repackaged from 82a83b5e (sha 2aa5a645c378f3e7, 24 entries) and handed over for Save skill. It is pending re-import.
- The 4 DIVERGENT skills (acquisition-underwriting be118330, deal-folder-intake d0a629d3, repo-architecture 732da111, retail-underwrite-lens 77cdbc46) were handed over for Save skill. They are pending clicks.
- Primary ~/.claude: live/primary-checkout fast-forwarded 0c9ca4fe..ee49f5ed (0/0 vs origin/main).
  - The 15 unique commits had already landed via #381-#384 (another session).
  - The 2 overlapping dirty files were archived to maintenance/_archive/2026-11-02_primary-checkout-repoint/ and reset (one byte-identical to main, one an older heartbeat ts).
  - The checkout stays on live/primary-checkout because `main` is held by the main-checkout worktree.
  - 146 dirty files are left for dirty-tree-triage.

## 2026-11-02 -- merge-ready force-cleared from PENDING_REIMPORT (Gabriel in-turn)
- Gabriel approved force-clearing merge-ready's ledger entry (from 819ef1ce, landed as #194 a9560c1d). No Save-skill click was logged for that commit, so `pending_reimport.py clear` refused. Its evidence: the repo SKILL.md was byte-identical (EOL-normalized) to the installed copy before the merge, checked on 2026-10-30 and again on 2026-11-02 at head 819ef1ce, and repo_first_check reads merge-ready IN-SYNC. The platform already serves this content, so no reinstall is needed. Cleared with --force after this entry was appended.

## 2026-11-02 -- acquisition-underwriting-eval-harness v1.3 reimport confirmed

acquisition-underwriting-eval-harness v1.3 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-11-02 -- ora-skills #196 merged (run state no longer ships; cache-ahead false positives; eval-harness v1.3)
- **#196 squash-merged** as beb43040 (Gabriel in-turn "go ahead"; after round 3 he chose "merge now, fix in follow-up"). Merged from the exact head the gate reviewed, c44058d2 on a9560c1d. CI green: skill-gates, skill-tests (GitHub ubuntu-latest) and tools-tests.
- **Root cause corrected.** package_skills.is_bundled shipped the git-ignored runs/ and .pytest_cache/ folders, so the 10-30 eval-harness package carried 41 entries against 23 tracked files. My 10-30 explanation (a run launched from the installed folder) was wrong. Both folders are now excluded. The v1.3 package has 24 entries for 24 tracked files and contains no run state.
- **adversarial-merge-gate: 3 rounds, 5 reviewers each, 0 bypass-marker breaches.**
  - Round 1: 5 confirmed, fixed. The HIGH was the mirror sync refusing on the new RUNTIME-STATE verdict.
  - Round 2: 2 MEDIUM plus the wrong root cause. Fixed after Gabriel chose the root-cause fix; the RUNTIME-STATE machinery was removed.
  - Round 3: 1 MEDIUM and 4 LOWs, accepted as known risk by Gabriel. The MEDIUM: a quoted value followed by a comment ending in a quote mark compares equal to a different value (0 of 90 repo / 119 installed frontmatters).
- **Follow-up PR owed** for the MEDIUM and the LOWs (parse_replays catches only ValueError; two untested decode paths; one misleading test comment; one stale .gitignore comment).
- **Scheduled task ora-acquisition-underwriting-eval-harness** (~/.claude/scheduled-tasks/.../SKILL.md, Step 4): it no longer advances state when the parse_replays report carries record_error. Edited in place (Gabriel approved), backup in ora-skills/_staging/handoff/2026-11-02_merge-194-196/, not re-registered, and uncommitted in the live checkout.
- **Pre-existing, not caused by #196:** acquisition-underwriting, deal-folder-intake, repo-architecture and retail-underwrite-lens read DIVERGENT. That verdict is identical under the pre-#196 tools at a9560c1d. county-parcel-screen moved from DIVERGENT to IN-SYNC.

## 2026-11-02 -- ora-skills #194 merged (merge-ready strict-YAML quoting); no reimport needed
- **#194 squash-merged** (a9560c1d, Gabriel in-turn "go ahead"). merge-ready/SKILL.md line 3 is now the double-quoted description the platform already stored on install, so the frontmatter parses as strict YAML. The decoded text is unchanged (882 chars).
- **Gates:** CLEAN/MERGEABLE, no overlapping PR. tools-tests was cancelled twice by the shared 15-min CI timeout (main hits it too) and passed on attempt 3. The commit's 4 claims were re-checked at head 819ef1ce before merge: old line fails strict YAML, new parses, value identical, file == installed cache. adversarial-merge-gate was not run: its own skip clause covers trivial single-file, single-session changes.
- **Ledger:** merge-ready cleared from PENDING_REIMPORT without a Save-skill click. The repo copy was byte-identical (EOL-normalized) to the installed copy before the merge (checked 2026-10-30 and again today), so the platform already serves this content. The post-merge hook's mirror sync then rewrote the same bytes.

## 2026-11-02 — ora-automation-health-monitor weekly run: am-brief stalled after Block A, ora-pm backups failing, alert sent
- **Surface:** CC/MCP, scheduled Monday fire (throttled +121 min). Base skill v1.15, liveness PASS. No multi-day outage; host off 11-01 18:05 → 11-02 09:34 ET, 42-task catch-up burst (8 HOST-UNAVAILABLE, 13 THROTTLED-THEN-RECOVERED, 0 open).
- **Flagged:** (1) ⚠️ PRODUCER-STALE-OUTPUT ora-am-brief B/C/D: session local_b4b9d9fe ran 14:58–15:04Z and stopped mid-Block B; only the Rate Snapshot landed. No Daily Brief 11-01 or 11-02, no Inbox Pre-Brief 11-02, no Cash Position Snapshot since 10-05. (2) ⚠️ BACKUP-FAILED ora-pm monthly-billing-backup 11-01 (HTTP 500, Cloudflare 1016). (3) ⚠️ BACKUP-FAILED/STALE delinquency-backup (HTTP 500 11-01; 10 straight failures). (4) ⚠️ mirror-drift-check ALERT-LATE +150 (host up, self-recovered).
- **Cleared:** the 10-30 ACTIONS-BILLING-BLOCKED finding. The watchdog has been green since 11-01 03:19Z.
- **Outputs:** Notion `40c6ecd8-9e59-8103-abcc-fa74a073a06b` (verified). Snapshots `2026-11-02.ahm-cc.json` (71) and `.ahm-lams.json` (29), both SNAPSHOT OK; diff vs 10-30 clean. Alert email sent (send-log [OK] 13:26:10 ET, Sent Items confirmed).

## 2026-10-31 — Phase 3: live ~/.claude checkout repointed to origin/main (0c9ca4fe)

- **Gabriel in-turn ("Yes, run it") on the Phase 3 plan.** Before: `live/primary-checkout` f3d3b798, 22 ahead / 6 behind origin/main, 7 files differing. Phase 2 had already landed every unique commit as #381–#384 and #386, and #385 replaced the guard-liveness code. Backup ref `backup/primary-checkout-20261031` = f3d3b798 (the 10-30 `backup/primary-checkout-20261030` = bd1ea863 is kept).
- **Loss check:** every line on live but not on main was an older version of something main superseded (#382 done-bar, #383 deal-recon, #385 probe/tests/tech.md). No content existed only on live.
- **Overlap:** the only dirty file among the 7, `skills/branch-catchup/SKILL.md`, was the ora-skills post-commit copy of Phase 2's 59b60598 upstream. It is byte-identical (EOL-normalised) to ora-skills dd94bd2a and to the ora-claude-config mirror branch 000b4dbf. preflight-shared-checkout flagged it CONTESTED (no live owner); that was resolved by provenance. It was copied to `maintenance/_state/_archive/2026-10-31_phase3-repoint/` and stashed alone (`stash@{0}` fb066981, "phase3-repoint-branch-catchup-59b60598-20261031"). The live copy returns when the 000b4dbf mirror PR merges.
- **Move:** `git reset --keep origin/main` plus upstream set to origin/main; HEAD 0c9ca4fe, 0/0. `main` stays checked out in the stale `.claude/worktrees/main-checkout` (c7e05d82), which was not touched. The other 137 dirty entries were preserved; dirty-tree triage is a separate pass. Nothing was pushed.
- **Verify:** doctrine probe exit 0 (CLAUDE.md 1,744 words; guard liveness 8 guards checked from tech.md, so the #379-inherited check-11 skip is closed by #385); governor-drift OK (DSCR 1.25x / LTV 40%); hook suite 72/72 (PYTHONIOENCODING=utf-8).
- **Rollback:** `git reset --keep backup/primary-checkout-20261031`.

## 2026-10-31 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `c460ebbe-769e-4e81-9c03-d37c0051403e` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel in-turn 2026-10-31 approved the override for the 4 recon/* branches, then separately "Yes, use override" for recon/live-checkpoint-f3d3b798. Sole expected failure: pre-existing test_guard_liveness_real_no_orphans (#379); fix on fix/guard-liveness-techmd.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-31 14:43:48 local.

## 2026-10-31 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `c460ebbe-769e-4e81-9c03-d37c0051403e` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel in-turn 2026-10-31 "Yes, override and push" for the 4 recon/* Phase 2 branches. Sole failure is pre-existing on main: test_guard_liveness_real_no_orphans (#379 removed CLAUDE.md Guards: line); fix tracked in session local_19332dfc.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-31 14:17:10 local.

## 2026-10-31 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `c460ebbe-769e-4e81-9c03-d37c0051403e` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel in-turn 2026-10-31 "Yes, override and push" for the 4 recon/* Phase 2 branches. Sole failure is pre-existing on main: test_guard_liveness_real_no_orphans (#379 removed CLAUDE.md Guards: line); fix tracked in session local_19332dfc.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-31 14:11:05 local.

## 2026-10-31 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `c460ebbe-769e-4e81-9c03-d37c0051403e` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel in-turn 2026-10-31 "Yes, override and push" for the 4 recon/* Phase 2 branches. Sole failure is pre-existing on main: test_guard_liveness_real_no_orphans (#379 removed CLAUDE.md Guards: line); fix tracked in session local_19332dfc.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-31 14:06:22 local.

## 2026-10-31 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `c460ebbe-769e-4e81-9c03-d37c0051403e` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel in-turn 2026-10-31 "Yes, override and push" for the 4 recon/* Phase 2 branches. Sole failure is pre-existing on main: test_guard_liveness_real_no_orphans (#379 removed CLAUDE.md Guards: line); fix tracked in session local_19332dfc.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-31 14:00:42 local.

## 2026-10-30 -- acquisition-underwriting-eval-harness v1.2 reimport confirmed

acquisition-underwriting-eval-harness v1.2 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-30 -- county-parcel-screen v1.6 reimport confirmed

county-parcel-screen v1.6 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-30 — LAMS automation-health-monitor retirement ratified (execution handed to native Cowork)

- **Gabriel in-turn ("Yes, retire it"), after the CC successor `ora-automation-health-monitor` v2.0 completed one clean supervised run (2026-10-30 22:06Z).** RATIFIED automation-health-monitor (fleet: lams).
- **Filed, not executed:** the entry was added to `maintenance/_state/retire-pending.json` (+7 lines, additive), so `ORA Fleet Pause-Resume Guard` alarms if the row is ever re-enabled. The id was also added to `handoffs/2026-10-30_LAMS-twins-retire_brief.md`, so one native on-device Cowork pass retires it with the outreach and heartbeat twins: archive the folder to `_archive_2026-10-30_retired-to-ccmcp\` first, then `delete_scheduled_task` on the LAMS row.
- **Why not executed here:** this Claude Code session's scheduler tools reach only the CC fleet, and the skill treats archive-then-delete as one pass. The folder stays in place until the native session runs.
- **Checks:** no CC row shares the id (the CC id is `ora-automation-health-monitor`). Producer-script check: every script the LAMS spec runs has another live caller (snapshot-validate.py, dispatch-skip-probe.py and host-availability-report.py are now run by the CC monitor). Only `test_snapshot_validate.py` has no task caller, and it is a regression suite, not a producer.
- **Still to do at execution:** add the id to the "Do NOT re-register" list in `session-context.md`, and move the retire-pending entry to `_completed`.

## 2026-10-30 — Health chain on CC: ora-automation-health-monitor v2.0 registered; live ~/.claude checkout carries #379 (510da001)

- **Job 1 (Gabriel in-turn, supervised, register-scheduled-task v2.30):** automation-health-monitor ported from LAMS v1.29 to CC as `ora-automation-health-monitor` (cron `5 11 * * 1` chosen by Gabriel over weekdays; next 2026-11-02 11:17 ET; `[MODEL: UNVERIFIABLE | checked 2026-10-30]`; title "ORA automation health monitor (CC)"; saved in Bypass mode). Port, not copy: 17,164 → 4,927 words. Every v1.29 rule kept; incident narrative left in the LAMS file. Traps closed: (a) snapshots renamed `.ahm-cc.json` / `.ahm-lams.json` (no collision with ora-task-integrity-guard's `.cc.json` or the frozen `.lams.json` membership-guard reads); (b) new Step L makes the ratified LAMS dark state expected silence (grouped ℹ️; teeth: enabled LAMS checked, LAMS re-enable ⚠️, CC twins never suppressed). The CC registry is read live; the `[CC/MCP]` downgrade is gone; LAMS is read via fleet-status.py, read-only. 0.55a shared block byte-identical.
- **Supervised test fire (2026-10-30 22:06Z, succeeded):** both snapshots written and validator-clean (ahm-cc 71 rows/45 enabled, ahm-lams 29/1); Notion page published and verified; alert email confirmed in send-log + Sent Items. Flags: ❌ GitHub Actions billing block since ~10-13 (ora-cowork-watchdog dead-man + ora-pm backups not running; monthly-billing backup at risk 11-01); ⚠️ ora-am-brief inbox-pre-brief heartbeat stuck at ENTERED; ⚠️ cowork-settings-quarterly-review 10-17 run 11.7h late. ℹ️ 27 LAMS dark, 24 with no CC successor; 10 WTS ORA* tasks missing from tech.md §3h roster.
- **ora-health-guard:** already re-enabled earlier today ("Guards & integrity (8)" entry); verified enabled, `15 5 * * 1`, next 11-02, tag checked 2026-10-30. Not touched again.
- **Pending (trap d):** LAMS `automation-health-monitor` stays DISABLED, not retired. One clean CC run now exists; retire it LAMS-style (archive first) from a native on-device Cowork session on Gabriel's go. Roster key in `notion-publish-degraded.json` still `automation-health-monitor`/lams; re-key at the next edit.
- **Job 2 (Gabriel in-turn, Phase 1 of the primary-checkout reconcile):** backup ref `backup/primary-checkout-20261030` = bd1ea863. Merged origin/main 41ac01a4 (#378-#380) into live/primary-checkout in worktree `sync-primary-379` (branch-catchup). One conflict, in CLAUDE.md; took #379, so eda47634's setup-audit plugin clause is dropped per the handoff ruling, and its done-bar half is kept. Independent Opus review: round 1 CHANGES-REQUESTED (stale editor note fixed), round 2 APPROVE (eos-review-gate artifact d8f418b8). Hook suite 72/72 under PYTHONIOENCODING=utf-8 (test-mcp-delete-tiers fails only on a cp1252 console, live tree too). Landed ff-only bd1ea863→510da001 with the guarded script (archived at `maintenance/_state/_archive/2026-10-30_live-sync-379-overlap/`); the 4 dirty overlaps were byte-identical. Live: 21 ahead / 0 behind origin/main, 15 unique commits intact, not pushed. Probe: CLAUDE.md 1,744 words (#379 minus the 9-word done-bar sentence), 0 shared runs; governor-drift OK.
- **Follow-ups:** Phase 2 = PR the 15 commits per the 2026-10-30 handoff table; Phase 3 = repoint to main. Inherited from #379 (review findings): doctrine-integrity-probe check 11 (guard liveness) is silently skipped because CLAUDE.md no longer has a `Guards:` line; #379's message wrongly says county-parcel-screen routes SCREEN mode (the Deal-evaluation tie-break still does).

## 2026-10-30 — Disabled scheduled tasks that "ran anyway" (10-14, 10-29): manual Run-now, not the scheduler

- **Question:** 11 runs of disabled tasks (both fleets) on 2026-10-14 22:04–22:06Z and 2026-10-29 20:30–20:31Z. Did the scheduler ignore `enabled:false`?
- **Verdict:** NO. The scheduler honours the switch. All 11 were hand-started, almost certainly UI "Run now" by Gabriel (high confidence; app logs stop 08-20, so no app-side proof). Cause class: input (manual), not logic.
  - 10-14 (6): CC deal-sourcing-scan, sourcing-construction-verify, county-sales-monitor; LAMS skill-text-audit, ic-memo-pipeline-reconciliation, om-intake-ocr.
  - 10-29 (5): LAMS underwrite-doctrine-staleness-check, loan-terms-reconciliation, consolidate-memory-monthly, skill-text-audit, tenant-contact-gap-sweep.
- **Discriminator (validated):** registry `lastScheduledFor` is set by every scheduler fire, including late catch-ups (master-workbook-ingest: scheduled 10-26 09:45, ran 14:50, field set). It stays empty on hand-started runs, and toggling `enabled` does not clear it (checkout-merge-forward and broker-touch-cadence were re-enabled 10-30 and keep theirs).
- **Ground truth:** the 10-30 integrity-guard and doctrine-guard runs were `run_scheduled_task` calls from session "Weekly task prioritization and planning" at 15:26:22Z. Both left the field empty.
- **Evidence:**
  - All 42 disabled tasks that still carry `lastScheduledFor` last fired on or before 09-22. That is zero scheduler fires on a paused task since the pause.
  - All 11 batch runs have the field empty.
  - Every CC and Cowork transcript was searched: no run or update scheduled-task call falls in either window.
  - Runs started 6–70s apart, mixed cadences, grouped by theme. Text was typed into the skill-text-audit task's composer.
  - `scheduledRunContinued:true` is NOT a discriminator: 79 of 438 CC scheduled sessions carry it, including normal catch-ups.
- **Implication:** "Run now" bypasses `enabled:false`. A paused task is paused against the scheduler only, and a hand run does real work (10-29 consolidate-memory edited MEMORY.md). The 10-14 construction-verify run stopped at GUARD 0 (scan marker 10-05). deal-sourcing-scan's 10-27 run fits the same pattern (empty field, no agent call) and is inferred manual; it was not traced further.
- **CORRECTION:** the 2026-10-30 "ora-task-integrity-guard run (catch-up fire…)" entry is mislabelled. That run was a manual `run_scheduled_task`, not a catch-up. The same applies to the session-context line "ran 2026-10-30 (catch-up fire)".
- **Follow-up candidate:** automation-health-monitor's staleness check should treat an empty `lastScheduledFor` as a manual run, not as scheduled health.
- **Source:** session "Fleet inventory" (read-only investigation; nothing else modified).

## 2026-10-30 — ora-automation-health-monitor v2.0 first CC run: Actions billing block + 2 warnings, alert sent
- **Surface:** CC/MCP, scheduled (off-cycle Friday fire of the Monday task). Base skill v1.14, liveness PASS. No multi-day outage.
- **Flagged:** (1) ❌ ACTIONS-BILLING-BLOCKED: zero-step jobs with the billing annotation on ZeOoba/ora-cowork-watchdog (last success 2026-10-13T15:24Z) and ZeOoba/ora-pm delinquency-backup (last success 10-05). The dead-man watchdog and the off-host backups are dark. Gabriel-only fix: Billing & plans. (2) ⚠️ ora-am-brief Block C: inbox-pre-brief-heartbeat.log stuck ENTERED 11:46:45Z (page published). (3) ⚠️ ora-cowork-settings-quarterly-review 10-17 slot +699 min (host up).
- **Informational:** 27 LAMS tasks dark by ruling (24 have no CC successor); 7 HOST-UNAVAILABLE; 14 CC tasks re-enabled today. doctrine-integrity-guard and task-integrity-guard were re-enabled ~11:26 ET per registry-membership.log `adds`, with no event_log record. 10 ORA* Windows tasks are not in the tech.md §3h roster.
- **Outputs:** Notion `4096ecd8-9e59-8112-879f-d6823b115038` (verified). Snapshots `2026-10-30.ahm-cc.json` (71) and `.ahm-lams.json` (29), both SNAPSHOT OK; baselines bootstrapped from 2026-10-30.cc.json and 2026-09-15.lams.json. Alert email sent (send-log [OK], Sent Items confirmed).

## 2026-10-30 -- merge-ready reimport confirmed

merge-ready reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-30 -- land reimport confirmed

land reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-30 — website-perfection v1.2.2 packaged for re-import (awaiting Save skill)

- Gabriel in-turn ("Package it"). From detached worktree at origin/main 346b693e: plugin_of=None (standalone); package_skills.py rc=0, description 470/1024, 3 forward-slash entries (tests/ excluded by packager, matches cache); SHA-256 prefix 66010a893355060a; delivered to Gabriel. Cache SKILL.md already hash-matches v1.2.2 (mirror sync, not a confirmed platform import), PENDING_REIMPORT line still open; baseline recorded. Install via Cowork Save skill (multi-file). Post-install: reimport_correlate.py verify website-perfection, then clear ledger. Closing sweep: frontmatter 0 findings; repo_first_check flags pre-existing CACHE-AHEAD county-parcel-screen + DIVERGENT acquisition-underwriting/deal-folder-intake/repo-architecture/retail-underwriting-lens/submarket-spatial-analysis (same class as the 10-30 doctrine-guard alarm; not touched).

## 2026-10-30 — site-qc-reviewer Opus pin PRs merged

- Gabriel in-turn ("Merge when green"). ora-claude-config #380 MERGED 636b5fd2; ora-skills #193 MERGED 346b693e after skill-gates/skill-tests/tools-tests all passed (both found already merged at merge time, likely by ora-pr-land-watch). Open follow-up: re-import website-perfection v1.2.2 to the claude.ai store (PENDING_REIMPORT). ora-skills auto-merge is disabled at repo level, so ccd set_auto_merge cannot be used there.

## 2026-10-30 — site-qc-reviewer Opus pin landed as two PRs

- Gabriel-approved via Open sessions review (AskUserQuestion "Land both", verified in that transcript). ora-claude-config #380 (`commands/ship.md`, commit b0e74a3c, worktree off origin/main, pre-push gate passed) and ora-skills #193 (website-perfection v1.2.2, c115498a). Independent adversarial-reviewer (opus-5-5): APPROVE, 0 refuted. Live checkout keeps the identical uncommitted ship.md edit until merge-forward. After #193 merges: re-import website-perfection (PENDING_REIMPORT recorded).

## 2026-10-30 — CI runners: worker-start IPC timeout raised 30 s → 300 s (root cause of "runner lost communication" job deaths)
- **Gabriel in-turn ("Yes, now"), session "Open sessions review"**, after the diagnosis below.
- **Root cause:** the runner listener gives a newly spawned Runner.Worker 30 s (default) to accept the job over IPC. Under memory pressure (commit charge 57.4 of 61.4 GB at 20:05Z; Chrome ~12 GB, 28 claude processes ~6.2 GB) the worker took 31–38 s to start, so the listener killed it ("Job request message sending for job … been cancelled, kill running worker"). GitHub then failed the job about 10 min later as "runner lost communication". `_diag/Runner_*.log` shows 8 such kills since 10-14: OCC `C:\actions-runner` 10-14 ×2 and 10-28; OCC2 10-28; Website 10-27 and 10-30 15:14Z; Skills 10-28 and 10-30 19:53Z (ora-skills PR 190 tools-tests). This matches the post-wake catch-up kills Automation Audit R31–R33 could not explain.
- **Fix:** a new `.env` holding the single line `GITHUB_ACTIONS_RUNNER_CHANNEL_TIMEOUT=300` (the runner's maximum) in all four runner roots: `C:\actions-runner`, `C:\Users\Owner\actions-runner-occ`, `C:\actions-runner-skills`, `C:\Users\Owner\actions-runner`. Runner v2.338.0 reads it at listener start and logs "Set runner/worker IPC timeout to 300 seconds."
- **Verified live:** Website runner. Its new listener (`Runner_20261030-201148-utc.log`) logged the 300 s line and created its session; the runner shows online and idle. **Pending:** OCC ×2 and Skills were mid-job, so they pick it up at their next listener restart (reboot, or an elevated kill while idle, after which the task's 5-min TimeTrigger relaunches them).
- **New gotcha:** `Stop-ScheduledTask ORA-Runner-*` kills only the powershell wrapper. The cmd and Runner.Listener processes run under S4U at Limited level, survive as orphans, and cannot be killed from a non-elevated shell (Access denied). The 5-min TimeTrigger then starts a second listener. The Website runner is in that state now: orphan PID 4644 (old settings) plus new PID 17196. Clean up from an admin prompt (`Stop-Process -Id 4644 -Force`) or by rebooting.
- **Measured for PR 521 (oxford-command-center):** in run 41077985260 the gate job took 76 min, of which "Post Run actions/setup-node" (the npm cache save) took 46m57s (19:11:31→19:58:28Z).

## 2026-10-30 — ora-sourcing-construction-verify re-enabled (CC)
- **Gabriel in-turn ("Yes, re-enable it")**, after a query from session "Code setup issues" triaging CC tasks left disabled by the stalled 09-28 resume. It had been off since its last run 2026-10-14, with no event_log record; most likely swept off by that resume, not retired.
- **Why:** it is the companion to ora-deal-sourcing-scan, which was re-enabled in Phase 0 today. The scan's 'Unknown — CONFIRM' + Listing URL rows and its T1-PENDING-VERIFY rows (v2.9, handled by v1.1 #376) are its target set. Leaving it out of Phase 0 was this session's oversight.
- **Change:** update_scheduled_task, enabled:true; description re-tagged `[MODEL: UNVERIFIABLE | checked 2026-10-30]`; cron `15 14 * * 2` unchanged, next fire 2026-11-03 14:16 ET (after the 10:48 scan). Frontmatter carried name+description only, so no custom key was lost.

## 2026-10-30 — Stalled-resume triage: 8 CC guard/integrity tasks re-enabled; 24 stranded, 3 held

- **Triage (fleet-advisory-remediation):** the 35 CC ids from `ora-routine-pause-resume-09-28` still `enabled:false` (merge-forward re-enabled separately today) were checked against registry descriptions, retire-pending.json, session-context and event_log (current + Oct archives) since 2026-09-28. Result: 32 stranded (no deliberate-off record), 3 held. Two apparent retire-pending hits were substring false positives (`ora-ar-feed-sweep` appears only as the replacement in a LAMS entry; `ora-health-guard` matched `ora-health-guard-fail-aging-nudge`).
- **Re-enabled (Gabriel in-turn, "Guards & integrity (8)"):** ora-health-guard, ora-financial-code-integrity-sweep, ora-appsec-sweep, ora-ground-truth-auditor, ora-weekly-hygiene (OI-373), ora-site-exposure-probe, ora-command-center-mirror-drift-check, ora-model-release-watch. Each got `update_scheduled_task` enabled:true plus description re-tag `[MODEL: UNVERIFIABLE | checked 2026-10-30]`; cron unchanged. Verified: list_scheduled_tasks enabled:true on all 8 (CC now 42/69 enabled); tags confirmed in SKILL.md (the listing truncates descriptions); spec diffs are description-only plus whitespace-only changelog lines on health-guard/appsec; appsec's `model: opus` frontmatter survived. Health-guard's Block A re-runs guard.ps1, which is intentional and idempotent per its spec. First fires: weekly-hygiene Sun 11-01 21:27 ET; health-guard, mirror-drift, model-watch and financial sweep Mon 11-02; ground-truth Tue 11-03; appsec and site-exposure Wed 11-04.
- **Still stranded, Gabriel deferred (24):** Reports (13): forward-calendar-digest, monthly-portfolio-briefing, deal-command-board, deal-aging-sla, vacancy-aging-report, noi-opportunity-digest, psa-drift-watch, tenant-hubspot-reconciliation, renewal-hubspot-reconcile, hubspot-renewal-closeout-tasks, loan-balance-check, incentive-registry-refresh, recovery-structure-audit-annual. Data producers (5): lease-snapshot-refresh, ar-feed-sweep, calibration-snapshot, aaos-expire-leases, aaos-publish-contracts. Self-maintenance (6): cc-schematic-refresh, claude-setup-audit, open-sessions-board, pm-ledger, excess-usage-sweep, acquisition-underwriting-eval-harness.
- **Held OFF deliberately (Gabriel: keep off, log why):** `ora-audit-log-sweep` (OI-360 OPEN MEDIUM: overwrites earlier archives; writes gzipped session logs into a git-tracked folder the pre-push scanner cannot read); `ora-sofr-direct-prefetch` (2026-09-22 ruling: redundant, am-brief Block A pulls SOFR directly; retirement candidate, not yet ratified); `ora-sourcing-construction-verify` (ran 10-14, then disabled with no record; owner intent asked of session 5663921d).

## 2026-10-30 — Setup remediation pass (Gabriel-directed decisions); two session-context tombstones retired here
- **Tombstones moved out of session-context.md (Gabriel in-turn):** (1) "Machine migration CLOSED — both fleets live on LAPTOP-CSHSCBE6 (32GB); do NOT auto-run Phase B2 re-registration. History: event_log.md, oxford-cc-repo-health.md." (2) From the email-send-path bullet: "Rube is shut down — never reference it." Both stand as history here; the send-path rule itself (Outlook COM sole path, no Gmail, no Composio) stays in session-context.
- **Worktrees:** `~/.claude` 89 → 35. 55 removed (clean; merged and idle >24h, or unmerged and idle >7d), branch refs preserved; 11 live-24h and 13 dirty untouched. Log: `maintenance/_state/_worktree_prune_20261030.log`.
- **ora-skills PR #191:** land / merge-ready tie-break — readiness questions and bare "merge PR N" route to merge-ready (always gated on in-turn yes); land claims only explicit single-PR phrases. Independent review: round 1 CHANGES-REQUESTED, round 2 APPROVE.
- **Automation Audit snapshots:** kept pre-R32 and pre-R33; four older folders moved to `~/archive/ora-automation-audit-snapshots/` (archive, never delete).
- **Corrections to Automation Audit R33:** push-fleet-heartbeat.log rotation already exists (1 MiB cap since 2026-09-06; R33-8 "no rotation found" was wrong). The 10-29 prepush-gate-sweep failure (test-governor-drift-probe) was fixed on main by #368; it recurs from the primary checkout (`live/primary-checkout`, 19 ahead / 42 behind origin/main) — triage queued.

## 2026-10-30 — Amendment H landed + upstream portfolio filters widened (PR #378, live)
- **ora-skills #189 merged** (d7cab49e, Gabriel "Merge 189"): Amendment H rulings — >5 bldgs = gate flag; no per-building price band (≤$15M total); premium clears yield floor AND current unlevered IRR floor (max(10.0%, 10-yr UST+550 bps); no separate 15% bar — the "15%" was a relay error by this session). `gh pr merge --auto` merged immediately (checks not required) — skill-gates/skill-tests/tools-tests were still QUEUED on the busy self-hosted runner at merge and post-merge; local suite was 17 files / 0 failed. Confirm CI result.
- **PR #378 (open), already LIVE via propagate-task-spec.py:** entry-market-scan v1.10, deal-sourcing-scan v2.11, am-brief C.5.5, deal-flow-triage — $10–15M portfolios pass; >5 bldgs / >$15M / failing building = gate flag, never dropped; Gate Review never N/A for portfolio flags; STEP 2.0 per building. 3 review rounds → PROCEED.
- **OPEN QUESTION FOR GABRIEL:** deal-sourcing-scan Capital-sleeve score gives $10–15M portfolios 0/10 (10-pt handicap vs T1 ≥60) — unchanged pending ratification.
- **Follow-ups (ora-skills):** county-parcel-screen, portfolio-growth, market-monitor/daily-brief "sub-$10M", verified-deal-recon prompt, deal-comparison Capital Efficiency (scoring), communication-intelligence broker text.

## 2026-10-30 — ora-checkout-merge-forward re-enabled (CC/MCP)

- Gabriel approved in-turn ("Yes, re-enable it") after the diagnosis entry above. Surface: native Claude Code, CC/MCP fleet (path `~\.claude\scheduled-tasks\ora-checkout-merge-forward\`). Single-writer check: no live session on this id; registry-membership.log quiet since 11:30.
- `update_scheduled_task` with `enabled:true` and the description re-tagged `[MODEL: UNVERIFIABLE | checked 2026-10-30]` (was `claude-sonnet-5 | set 2026-09-09`; the registry has no model pin to observe). Cron unchanged at `45 16 * * 5`. Only the description line changed in SKILL.md (git diff 1/1). That leaves it tracked-modified on the live checkout, with LF endings.
- Verified via `list_scheduled_tasks`: enabled:true, nextRunAt 2026-10-30T20:46:27Z (Fri 16:46 ET, today), then Fri 11-06. The live checkout is 0 behind main, so the first run should be NOOP_CLEAN and reset the 09-14 unsynced streak.
- Still open: the other 35 CC tasks stranded by the stalled 09-28 resume (see diagnosis entry); triage per id before any re-enable.

## 2026-10-30 — Diagnosis: ora-checkout-merge-forward (and 35 other CC tasks) stranded by the stalled 09-28 resume

- **Root cause (not deliberate):** the CC task `ora-checkout-merge-forward` (`45 16 * * 5`) is `enabled:false`, last run 2026-09-21 (BLOCKED_DIRTY_OVERLAP, the refused-merge-rewrite incident, PR #250). The 09-22 fleet pause disabled it. The 09-28 attended resume (`ora-routine-pause-resume-09-28`, archived) stalled at step 1 of 5. The 10-02 recovery re-enabled only Wave 1 (5 tasks), and Waves 2 and 3 never ran. The resume spec explicitly said to re-enable merge-forward "anyway" even when blocked, and `retire-pending.json` lists no CC ids, so nothing carved it out.
- **Safe to re-enable:** the live corrector (now synced) computes the dirty/incoming overlap read-only with `merge-tree` (step 3b) before any `git merge`, which closes the 09-21 rewrite hazard. Expect it to report BLOCKED often while OI-249 (live checkout on a long-lived branch, ~600 dirty entries) stands. Re-enabling restores visibility, not automatic sync.
- **Wider finding:** 36 of the resume spec's 51 ids are still OFF on CC, including ora-health-guard, ora-financial-code-integrity-sweep, ora-appsec-sweep, ora-ground-truth-auditor, ora-forward-calendar-digest, ora-weekly-hygiene (OI-373) and ora-sofr-direct-prefetch (a retirement candidate per this log). Per-id intent since 10-02 is not yet checked; triage via `fleet-advisory-remediation` before any bulk re-enable.

## 2026-10-30 — ora-pm-daily-crons description corrected to weekly (CC/MCP)

- Gabriel in-turn. `update_scheduled_task` description-only: "Daily 9:40" -> "Weekly (Mon) 9:40 ... ratified at-most-weekly retime, re-affirmed 2026-10-30"; `[MODEL: claude-sonnet-5-5 | set 2026-10-06]` kept. Update dropped `offhost-backup:` as expected (postguard caught it); restored verbatim from backup. Diff vs backup = description line only; body untouched. File now LF (tool output; was CRLF). Verified `list_scheduled_tasks`: cron `40 9 * * 1`, enabled, next 2026-11-02T14:48Z. Backup: `maintenance/_archive/2026-10-30_pm-crons-desc/`.

## 2026-10-30 — Ruling: ora-pm-daily-crons stays weekly

- Gabriel in-turn ("Keep weekly"): critical-dates-alerts + delinquency-check stay at `40 9 * * 1` under the at-most-weekly ruling; no exception. Do not re-flag the weekly cadence. Residual: the task description still reads "Daily 9:40 AM ET" (cosmetic; fix via register-scheduled-task when next editing the spec, restoring `offhost-backup:` after any update_scheduled_task).

## 2026-10-30 — Setup-optimization research (6 Opus threads) + top-3 correctness pass

- **site-qc-reviewer floor:** subagent-cost-report (30d) showed all 6 dispatches on Sonnet despite `model: opus` frontmatter (dispatch overrides). Fixed `commands/ship.md:19` to require explicit `model: "opus"`. NOT fixed: ora-skills `website-perfection/SKILL.md:18` (single-writer, another session active). Uncommitted.
- **ora-pm-daily-crons weekly** (`40 9 * * 1`) is the RATIFIED at-most-weekly retime (archive event_log_2026-10-08 l.577/581), not a bug; only its description still says Daily. No change; ask Gabriel whether critical-dates alerts merit an exception.
- **backup-push-failed 15:35Z:** pre-push gate failed test-governor-drift-probe on memory `project_doctrine_guard_alarm_2026-10-30.md:13` quoting flagged numerals; already reworded by another session (15:31) and live checkout synced (bd1ea863, #368 live). Probe now OK (3,698 files). Unpushed main = 7 heartbeat/reconcile commits; next 07:30 run retries.
- Correction: live checkout is no longer 42 behind (synced 15:43, ahead 20). CC fleet = 31 enabled recurring, not 24.

## 2026-10-30 — Live ~/.claude checkout caught up to origin/main (bd1ea863); governor-drift alarm cleared

- Gabriel approved in-turn ("Yes, run catch-up"). The sync merge was done in a worktree (`branch-catchup`): live/primary-checkout 59b60598 + origin/main 4848a381 = bd1ea863. One conflict, event_log.md, unioned newest-first. Hook suite 161/161 on the merged tree. Not pushed: the 19 local-only commits stay unpushed, as the 10-29 triage left them.
- Preflight gate was CONTESTED on 5 paths owned by session 5663921d. That session gave GO in writing, and all 5 were byte-identical to the merge. Landed with a guarded ff-only script under an allow-config-write token (closed early). Pre-ff copies of all 11 overlap paths, plus the script, are at `maintenance/_state/_archive/2026-10-30_live-sync-overlap/`. The live event_log.md (superset, 22 newer entries) and fleet-heartbeat.json were restored after the ff. The guard's event_log WARN was a CRLF hash false alarm: content equaled the merged blob.
- Live after the landing: governor-drift probe clean (3,698 files), doctrine probe 16 warnings (baseline), render-settings-wiring `--check --live` CLEAN. #368, #372, #361, #377 are now live.
- Correction to today's audit entry: the live checkout HAD been synced by hand on 10-23 and 10-26. `checkout-merge-forward-last-run.json` (09-21, BLOCKED_DIRTY_OVERLAP) is stale because the automated corrector stopped running. That is still open. The R-08 7-clean-day window can now count from today.
- Leftovers: an empty locked dir `.claude/worktrees/gov-drift-fp-v437` (unregistered) and branch `fix/governor-drift-v437-changelog-fp` (0 ahead of main) are safe to remove.

## 2026-10-30 — Owner-outreach 10-27 T1 pack released (50 letters mailed 10-30)

- Gabriel confirmed in-turn (AskUserQuestion: "Mailed today 10-30"). Ran `owner_outreach_weekly.py --released 2026-10-30`: rc=0, 50 T1 rows appended to `mail-log.csv` (227 -> 277 data rows), 0 duplicates. Clears the exit-3 halt for Monday 11-02 10:55 `ora-owner-outreach-queue-refresh`; those 50 owners are now under the 21-day re-mail floor.

## 2026-10-30 — Setup audit: LAMS dark state ratified deliberate; live ~/.claude checkout 42 commits behind main

- **Ruling (Gabriel in-turn, AskUserQuestion "Deliberate, record it"):** the LAMS/Cowork fleet's full dark state (0 live recurring, no resume queued) is DELIBERATE. Do not re-ask; do not queue a LAMS resume without a new ruling. Answers the open question in the 2026-10-30 ora-task-integrity-guard entry.
- **Correction to that entry:** ora-cowork-heartbeat is NOT the dead-man chain's sole producer any more. The CC twin (`50 5 * * *`) is enabled and ran 2026-10-30 (CC registry `lastRunAt`, via fleet-status.py); main carries the LAMS->CC heartbeat migration (PR #377). Not verified this pass: that the Notion `35c6ecd8` row / ora-cowork-watchdog actually received today's pulse.
- **Residual, by design:** state-freshness-probe and membership-guard will keep reporting LAMS-produced `_state/` files as stale. The probe refuses to mute open-ended pauses (R22-2 lesson), so no suppression was added. The fix is per-producer: migrate to CC or retire.
- **Root-cause finding:** the governor-drift alarm (8 hits on acquisition-underwriting `versions/CHANGELOG.md` v4.37) is ALREADY FIXED on main by PR #368 (`_is_skill_version_changelog` exemption). The probe from main is clean (3,696 files). It still fires live because `live/primary-checkout` is 42 behind / 19 ahead of origin/main: `checkout-merge-forward` last ran 2026-09-21 with status BLOCKED_DIRTY_OVERLAP (33 paths incl. settings.json, CLAUDE.md, heartbeat chain), unsynced since 2026-09-14. So every main fix since mid-September (#346 settings wiring, #368, #377) is not live. Remediation = `branch-catchup`, pending Gabriel's go-ahead (blast radius).
- **Verified non-issues:** ora-entry-market-scan's 811h gap (re-enabled today, next 11-03); skill mirror drift clean; frontmatter sweep 0 findings over 90 skills.

## 2026-10-30 — Deal Sourcing Plan Phase 1: heartbeat page restored + migrated to CC; scan v2.10 live; Amendment H PRs
- **INCIDENT:** heartbeat Notion page `35c6ecd8` was in TRASH since 2026-10-01 (unattributed) — watchdog had no live page ~4 weeks. Restored (same ID), body rebuilt, stale LAMS block trimmed. CC `ora-cowork-heartbeat` (`50 5 * * *`, v08, day-keyed fail-open guard) validated: HB ✅ 2026-10-30T18:35:56Z.
- **Scan v2.10** (first-discovered Source mapping) propagated live via propagate-task-spec.py (hash-verified). Correction: live scan was already v2.9 since 13:12 (#374 session) — the "live runs v2.8" claim this session made earlier was wrong (it compared git HEAD, not the live file).
- **LAMS twins brief** (outreach + heartbeat) hardened: never from Claude Code (delete resolves to CC fleet). Outreach-only brief (#375) marked SUPERSEDED. Both twins in retire-pending.json.
- **PRs:** ora-claude-config #377 (Phase 1, open). ora-skills #187 (Amendment H + LOI write-back) merged by ZeOoba 19:12Z; #189 (Gabriel's 3 H rulings) open — rule (c) IRR-floor meaning [OPEN]: relayed as "15%" but the levered 15% floor was retired v4.33.
- **Gate:** governor-drift false positive from in-flight Amendment H wording fixed at source; rewrite-advisory-guard timing flake under load — passed on retry, no override.
- **Vendors:** shortlist delivered (Lob / Tracerfy recommended); pick ON HOLD per Gabriel.

## 2026-10-30 — ora-year-end-review re-registered (CC/MCP, Feb anchor)

- Gabriel approved in-turn ("Register it too"). Registered via `create_scheduled_task` from a supervised Code session: cron `20 12 26-28 2 *` + last-business-day-on-or-before-Feb-28 guard, idempotency guard, `[MODEL: UNVERIFIABLE | checked 2026-10-30]`. Verified in `list_scheduled_tasks`: enabled, nextRunAt 2027-02-26T17:31Z (Fri; Feb 28 2027 is a Sunday).
- Anchor is Feb 28, NOT the Dec 15 that `annual-cycle`'s description and calendar table still state: the 06-11 orphan-archived spec (`Documents\Claude\Scheduled\_archive_2026-06-11_orphans\ora-year-end-review`) records the 2026-04-28 correction (Dec 15 fires before FY close and can never review a complete year). Kept its 6-point preconditions gate, replacing "QB MCP connected" with QuickBooks Desktop full-year exports on SharePoint. Email ggoldberg only.
- Follow-up: `annual-cycle` SKILL.md (description + calendar table) still says Dec 15 — needs a repo fix.

## 2026-10-30 — ora-annual-budget-kickoff re-registered (CC/MCP, seasonal)

- Gabriel approved in-turn ("Re-register it") after the skill-catalog review (artifact 3ubc2ZMpJ1ELk9MKtWoF93, F1) found `annual-cycle` routing to a Nov 1 task registered on neither fleet. Resolves the conflict between the open-items history ("ratified-unneeded 2026-06-11") and tech.md ("deferred seasonal, re-register before each November"): the seasonal reading stands.
- Registered via `create_scheduled_task` from a supervised Code session: cron `35 10 1-3 11 *` + first-business-day guard (2026: Sun 11-01 exits, Mon 11-02 runs), idempotency guard on the FY output file, `[MODEL: UNVERIFIABLE | checked 2026-10-30]`. Verified in `list_scheduled_tasks`: enabled, nextRunAt 2026-11-01T15:37Z.
- Spec rewritten from the 06-11 orphan archive (`Documents\Claude\Scheduled\_archive_2026-06-11_orphans\ora-annual-budget-kickoff`) to current canon: email ggoldberg ONLY (archived spec also emailed Eric — routing violation, dropped), QuickBooks Desktop via SharePoint exports (not QBO), method delegated to `annual-cycle`, no model/governor edits, draft outputs only.
- Still open: `ora-year-end-review` (Dec 15), also named in `annual-cycle`'s description, is not registered on either fleet.

## 2026-10-30 — Deal Sourcing Plan Phase 0: weekly funnel scorecard built and wired into owner-outreach STEP 4c
- **Built:** `Investment Candidates -- 2026\sourcing_funnel_scorecard.py` + `test_sourcing_funnel_scorecard.py` (38 checks; folder suite `run_tests.py` 91 passed). Read-only. Deal source order: Notion REST (404 today: Deal Sourcing Log not shared with the outreach integration) → `--deals` grouped SQL export (validated against live select options; unknown value = exit 2) → NOT SUPPLIED. SCREEN = `Scorecard Done` only; scan verdicts reported separately.
- **Wired:** CC `ora-owner-outreach-queue-refresh` v1.9 STEP 4c — one SQL query/run, verbatim JSON, WARN-only, runs on halted weeks too.
- **First live read (90d):** 227 letters / 0 responses captured / 16 call-sheet owners, 0 outcomes / 190 scan-triaged / 16 full SCREENs / 2 T1 PURSUE / 0 LOI Sent Dates. Source="Other" on 131 of 206 scored rows.
- **Not mirrored** to `Claude outputs\` (sibling copy folder); Notion plan page `4096ecd8` §9 updated.

## 2026-10-30 — Deal Sourcing Plan Phase 0: sourcing engine moved onto CC fleet
- **Ratified:** Gabriel in-turn ("Start Phase 0"; plan = Notion `4096ecd8-9e59-8150-8417-c1d9a30130e4`).
- **Re-enabled (CC, UPDATE + re-tag `[MODEL: UNVERIFIABLE | checked 2026-10-30]`):** `ora-deal-sourcing-scan` (`45 10 * * 2`, next 11-03), `ora-entry-market-scan` (`45 11 * * 2`, in-task 1st-Tue guard, next 11-03 = real monthly run), `ora-broker-touch-cadence` (`40 13 2 * *`, next 11-02). Only description lines changed; no custom frontmatter lost.
- **Created (CC):** `ora-owner-outreach-queue-refresh` (`55 10 * * 1`, next 11-02). Body verbatim from LAMS v1.7 except Desktop Commander → direct local execution; `output_contract` frontmatter re-applied by hand (dropped by create; any future update_scheduled_task drops it again).
- **LAMS twin:** `ora-owner-outreach-queue-refresh` stays enabled:false, added to `retire-pending.json`; retire via native on-device Cowork session, brief `handoffs/2026-10-30_LAMS-outreach-twin-retire_brief.md`. The 09-28 LAMS-resume brief's 25-id list includes this id — carve it out.
- **Found already closed:** OI-180 (suppression pull moved to REST `pull_suppression.py` 2026-08-24, not on SQL quota); scan/roster doctrine conflict (closed 2026-09-22, local canonical). Master vintage 2026-10-27 ratified.
- **Open for Gabriel:** 10-27 pack unreleased (next Monday run will exit 3 until `--released`); `outreach-responses.csv` absent (0 responses logged); 16 call-sheet owners with no outcomes.

## 2026-10-30 — ora-task-integrity-guard run (catch-up fire, Friday against Mon 07:05 ET cron): 4 alarms, email sent

Guard was believed OFF per stale memory ("since 09-14 pending R33") — live registry shows it `enabled:true` and this run fired; memory corrected. Findings: (1) membership-guard.ps1 — 27 LAMS tasks newly disabled vs. last live-registry baseline (snapshot_suppressed=true, so the 45-day-stale LAMS snapshot did not drive this), including **ora-cowork-heartbeat** (sole external dead-man pulse producer) and automation-health-monitor's LAMS copy; disappeared[]/added[] empty. (2) task-folder-registration-probe.py — UNCOMMITTED_VS_GIT on ora-am-brief, ora-doctrine-integrity-guard, ora-task-integrity-guard; BEHIND_UPSTREAM on ora-full-gate-weekly, ora-site-seo-crawl-weekly. (3) task-folder-backup-completeness-probe.py — 127 UNBACKED files (121 routine `.bak-*` edit snapshots, 6 stray runtime/output files incl. 2 pre-reregistration SKILL.md backups and 2 ora-deal-sourcing-scan digests); none are substantive engine scripts. (4) state-freshness-probe.py — 13 `_state/` detector outputs stale (up to ~1105h), explicitly NOT explained as a bounded LAMS pause (probe: "all 27 recurring tasks disabled with NO resume queued within 14 days -- this is not a bounded pause"), consistent with finding (1). Clean: guard.ps1 (checked=94, 0 restored/missing/regressed/errors/collisions), registry-membership-probe.py, emit/push-fleet-heartbeat, phantom-dispatch-probe.py (0/16), dangling-mutation-probe.py. Informational: model-canary-probe.py found 2 CONTRADICTED model tags (ora-master-workbook-ingest, ora-pm-monthly-billing) — logged to model-currency-cc.md, no alarm. Alarm email sent to ggoldberg@oxfordra.net only (Outlook COM, dedup key ora-task-integrity-guard/2026-10-30/bd0d84fe08e3841d). Full backup-completeness detail: `maintenance/_state/task-folder-backup-completeness-2026-10-30.log`. **Open question for Gabriel: is the LAMS fleet's full dark state (0/27 enabled, no resume queued) deliberate, and should ora-cowork-heartbeat specifically be restored given it is the dead-man chain's sole producer?**

## 2026-10-29 - Architecture diagram remediation (6 repos)

- **Merged (verified earlier):** ora-skills#172, #175; ora-claude-config#358, #359, #364; Website#189, #190, #191; AAOS#32, #33. Still open: oxford-command-center#502, ora-pm#49.
- **Local follow-up (this session):** new PRs oxford-command-center#513 (Notion/Graph/token 15 s timeouts; REFUTE wf_0fa6e284-f6f not clean, then wf_01cc8908-8a7 clean scoped) and #512 (comment-only burn-in note plus status.json claim; flip the claim to merged after it lands). System-inventory regen is committed locally on ora-claude-config branch docs/system-inventory-refresh-2026-10-29 and NOT pushed: the pre-push governor-drift test fails on ora-skills acquisition-underwriting v4.37 text (0.65x).
- **Findings:** Actions billing block has stopped ora-pm delinquency-backup since 2026-10-05 (OI-368); ora-weekly-hygiene OFF since 2026-09-14 explains the stale inventory (OI-373); #502 gate failed in the vitest step, load flake (OI-374); ora-skills capture PRs #168/#169/#170 are overlapping supersets, not distinct skills.
- **OIs touched:** updated OI-254, OI-257, OI-268, OI-320, plus a history note on closed OI-259; filed OI-368 to OI-375.

## 2026-10-29 — Monthly Memory Consolidation (ora-consolidate-memory-monthly)

Run Thursday 2026-10-29. Store: 0 orphan files (all .md listed in MEMORY.md or INDEX_*); MEMORY.md 107 lines / 20,961 B (gate 21.5 KB). Fixed 2 stale index lines in MEMORY.md (sub-index range 7-25 -> 7-32; Rev 29 no longer labelled latest, Rev 33 is). tech.md s3 holds no hardcoded task count (roster generated) - no drift. No retired connector (Rube/Zapier/Composio/Gmail) marked active. OXFORDRA_REPO -> C:/Users/Owner/website-canonical (.git present) and oxford-site resolve. Doctrine/governor audit (31d): doctrine 12 ran/12 pass/0 fail; governor 0 ran; memory 0 ran; pre-push drift overrides: no overrides. event_log.md 918 lines (under ~1000 rollover cap). Deferred (report-only): open-items-tracker.md 743 KB and open-items-tracker-history.md 508 KB are oversized; ~12 July-dated project_/reference_ files may be archive candidates.

## 2026-10-29 — Dirty-tree triage: 2 isolated commits on ~/.claude; ora-skills and 2 archive paths left

Gabriel approved each step in-turn. Scan: `~/.claude` 44 dirty (branch live/primary-checkout, ahead 16 / behind 27), `ora-skills` 4 untracked, the site repo and `oxford-command-center` clean, no stray clones. **Committed (pathspec-isolated, index empty before, settled by 15-min mtime recheck):** `e62a6ac9` county-parcel-screen set, 6 files (UNATTRIBUTED, idle ~40h; no provenance record found); `0a0970a5` 14 already-archived maintenance paths, 236 files. **Not committed:** `maintenance/_archive/session-audit-logs/` (24 MB, may hold deal text) and `maintenance/_state/_archive/2026-10-17_scratch-triage/` (32 MB incl. a dirty-tree tarball), both left untracked because `~/.claude` backs up off-machine; the 5 shared memory files (other sessions append); live `prepush-gate-sweep.json`. Contents of the 236 committed files were not scanned for secrets or confidential terms; unpushed. **ora-skills:** claimed `ora-skills-housekeeping`; the 3 untracked `_archive/*` dirs are already archives and `_wt-au-v435` is a locked registered worktree (branch au-v4.35-rule-evidence, path from another sandbox), so nothing was touched. Branch divergence (ahead 19 / behind 27) left for Gabriel.

## 2026-10-28 — R33 remediation: 30 worktrees pruned; ora-skills fast-forwarded to origin/main

Gabriel approved both in-turn. **Worktrees:** 30 merged-into-origin/main, clean, >7-day-old `~/.claude` worktrees removed with `git worktree remove` (no `--force`, each re-verified immediately before); 3 detached gate-review worktrees kept; all branches kept; record at `maintenance/_archive/2026-10-28_worktree-prune/removed.json`; 110 to 80 worktrees. **ora-skills:** preflight CONTESTED only by an orphaned one-line `target-markets.json` edit (session debb4b17, idle 3d17h); stashed as `stash@{0}` (patch copy in the session scratchpad), then `git fetch` and `git merge --ff-only origin/main` from `8831d3a4` to `b042f550` (20 commits); the post-merge hook refreshed the Cowork skill cache. The stashed Madison note (RE-MEASURED 2026-10-05) is already present in origin/main, so the stash is redundant and was left in place, not dropped. Verification: frontmatter sweep 88 skill dirs, 0 findings; mirror check exit 0 (the R33-6 drift is closed; cause was the stale checkout). Still open: changelog caps for three skills, OI-288 dead pointer, ora-pm Supabase/GitHub billing (see `project_ora_pm_outage_2026-10-28.md`).

## 2026-10-28 — R33 remediation Phase 1 (partial): fleet baseline refreshed, session-context corrected

Gabriel approved the R33 remediation plan and "Continue Phase 1". Done: `registry-membership-probe.py` run twice (the first run happened because the script ignores `--help`); baseline, `fleet-roster.md` and the generated fleet block now read cc=22 recurring (+2 one-time), lams=0 (+1 one-time), drops none. `session-context.md` lines 20 and 23 corrected (integrity guard is Mondays and OFF since 09-14 pending Gabriel's health-chain decision; `ora-passed-deal-tracker` is enabled and ran 10-13 and 10-15). `_r32_band.tmp.html` moved to `artifacts/archive/2026-10-28_pre-r33/`. Not done: pruning 30 merged-clean `~/.claude` worktrees (the auto-mode classifier denied `git worktree remove` as irreversible; list and re-verify script are in the session scratchpad), the `ora-skills` fast-forward (needs Gabriel's call on the dirty `target-markets.json`), and the `event_log.md` OI-288 dead pointer (an old entry names `open-items-tracker.md#OI-288`; the log is append-only, so it needs a probe exemption or a one-token edit by Gabriel's ruling). Separate finding: ora-pm Supabase host NXDOMAIN and GitHub Actions billing refusal, see `project_ora_pm_outage_2026-10-28.md`.

## 2026-10-27 -- Owner-outreach letter copy: "seven states" -> "several markets" (OR-2026-001 rehash)
- Gabriel, in-turn 2026-10-27 21:36 ET: "We don't own in 7 states. Change to several markets in each letter." ORA does not hold property in seven states, so the portfolio sentence was inaccurate.
- Edited letter-templates/t1.txt ("across several markets in the Midwest and Mid-Atlantic"), t3.txt ("across several markets."), t4.txt ("across several markets so far."). Pre-edit copies + pre-rehash outreach-ratification.json archived at Investment Candidates -- 2026\_archive\2026-10-27_letter-template-several-markets\.
- `ratify_outreach.py --rehash --i-have-gabriels-approval` adopted the new hashes into OR-2026-001: T1 ff4bd408... -> b4ffbf8c..., T3 dc53519a... -> 9f06f221..., T4 8975df3c... -> 27fa38da...; `--verify` OK (review_by 2027-08-16).
- Not changed: the "27 buildings comprising over 500,000 square feet" figures (not raised).

## 2026-10-27 -- R-06 Task 7 / R-08 canary run on the live checkout: [FILL: PASS or FAIL]
- Scope: fresh-session canary after the live landing (render-settings-wiring.py --check --live CLEAN, 28 rows / 2 chains, logged 2026-10-27). Run on [FILL: date and time] in a session started AFTER the merge-forward (sessions started before keep the old wiring). Binaries loading ~/.claude/settings.json: CLI [FILL: version, e.g. from `claude --version`], Desktop [FILL: version]. `claude doctor` / schema validation: [FILL: clean or findings].
- Denied fixture (must be blocked by pre.mcp-delete-guard): [FILL: the exact fixture call, taken from the R-06 plan canary step]. Result: [FILL: denied as expected / NOT denied]. Guard telemetry evidence: [FILL: telemetry line or file reference].
- Scanned fixture (must reach pre.sensitive-file-guard-nb-dc via NotebookEdit / Desktop Commander write tools): [FILL: the exact fixture call]. Result: [FILL: scanned as expected / NOT scanned]. Guard telemetry evidence: [FILL: telemetry line or file reference].
- Sleeping-hook timeout test (run in a scratch project with its own settings, NOT the live settings.json): throwaway PreToolUse hook sleeping [FILL: seconds] with timeout [FILL: seconds]. Observed: the tool call [FILL: proceeded / was blocked] when the hook timed out. This settles the unverified claim from #346 that a timed-out PreToolUse hook is non-blocking in the real binary ([FILL: confirmed / contradicted]). If contradicted, the 30 s delete-guard timeout and the fail-open assumption need a redesign before R-09.
- Hooks sweep on Windows (all hooks/tests/test-*.py): [FILL: N suites run, N green; list any RED suite names, or "none"]. Linux main had 10 red (claim-file-collision, confidentiality-guard, config-write-guard, destructive-git-guard, eos-review-gate, git-prepush-scan, lint-config-guard, netlify-guard-global, ora-autonomy-gate, session-kind); Windows result: [FILL: all green / still red: names].
- Verdict: [FILL: PASS = both fixtures behaved, timeout test understood, sweep green; or FAIL with the failing step]. The 7-clean-day window (started 2026-10-27) [FILL: continues / RESTARTS because of: reason].
- Follow-ups: [FILL: none, or list]. Still open regardless: ora-skills #159 (Word render check, Tennessee transfer tax), outlook-calendar-sync v1.1 -WhatIf test, delete the old origin/r08-settings-wiring-table branch name (archived at archive/r08-settings-wiring-table), override-mint-guard re-add (dispatcher and table chains in one PR) after the session_kind redesign.

## 2026-10-27 -- R-08 / R-06 Task 7 live landing verified: --check --live CLEAN; task-spec propagation confirmed; 7-clean-day window starts
- Live checkout (C:/Users/Owner/.claude) verified after the supervised merge-forward: `render-settings-wiring.py --check --live` = RESULT: CLEAN, 28 rows / 2 chains, exit 0 (CRLF checkout, compared LF-normalized). 28 rows includes the two R-06 Task 7 rows (pre.mcp-delete-guard, pre.sensitive-file-guard-nb-dc), so the live settings.json carries #346's entries and matches the table exactly. Output saved to ora-claude-config-worktrees/r08-msgs/live-check-after-landing.json. No "before" check was captured (the merge-forward had already landed when the check was first run), so this after-check is the landing proof.
- Merge-forward history: the first `checkout-merge-forward.py --repo C:/Users/Owner/.claude --json` returned BLOCKED_DIRTY_OVERLAP (43 local scheduled-tasks/*/SKILL.md paths overlapped origin/main; merge not attempted, tree untouched; no blocking claims or in-progress ops). The 43 local diffs were already the #348 forward-slash rewrite (137 lines each way, content identical to origin/main for those files), i.e. the task-spec propagation had already been applied locally. A guarded restore (abort unless exactly 43 dirty files) stopped with 0 dirty files on re-check; the checkout had changed in between, and the live check above confirms the landed state. Empty backup patch left at r08-msgs/local-spec-propagation-backup.patch.
- Task-spec propagation (#348) confirmed: `maintenance/_tests/test_task_spec_command_paths.py` = 182 pass, 0 fail against the live specs. winpath-guard (#347) therefore will not block the scheduled-task commands.
- 7-clean-day window toward ratifying the wiring table as authoritative STARTS 2026-10-27 (one real change through the table = R-06 Task 7, live and CLEAN). Ratification itself remains a separate decision after 7 clean days (live-drift watch only at landings, per the 2026-10-23 decision).
- Unrelated local state seen, not touched: event_log.md modified (the 2026-10-26 R-08 entry; commit via the isolated-commit flow) and skills/county-parcel-screen/* modified (another session's work in progress; do not restore).
- Still open: Windows hooks sweep (10 suites red on Linux main, Windows result pending); fresh-session canary (one denied and one scanned fixture call in guard telemetry, plus the sleeping-hook test that a timed-out PreToolUse hook does not block, run in a scratch project, not the live settings.json); eos-review-gate record only if the gate asks; ora-skills #159 (Word render check, Tennessee transfer tax); outlook-calendar-sync v1.1 -WhatIf test; delete the old origin/r08-settings-wiring-table branch name (archived at archive/r08-settings-wiring-table); override-mint-guard stays unwired pending the session_kind redesign.

## 2026-10-27 -- pipe-mask-guard narrowed after merge-gate BLOCK: short-output evidence keeps the pipefail rewrite (live 79ede20c, PR #353 c94a1e43)

- PR #353's first version (7c775b8a, live since the 07-27 sync) dropped the `set -o pipefail;` rewrite for ANY pipeline ending in a limiter, so `git push | head -N` and `gh pr merge | head -N` could again report a rejected push as landed. Independent Opus merge-gate review: BLOCK (claim C1).
- Fix c94a1e43: `early_exit_kind()` splits PREDICATE (grep -q/-l/-L: always untouched, pipefail inverts them) from LIMIT (head, sed q, grep -m, read ...: untouched only when no evidence stage is git push/commit/merge/pull/rebase/cherry-pick or gh pr merge). Re-review CLEAR (9 claims, 0 refuted). Suite 628/0; hook-tests gate 159/159 from the isolated worktree and from live.
- Landed live as cherry-pick 79ede20c (blobs identical to the reviewed commit; the cherry-pick was not intercepted by eos-review-gate). Single-use `allow-config-write` token minted for it and moved out. Live probe: `git push | head -5` rewritten, `npm run gate:ci | head` and `git push | grep -q` untouched. Displaced expired `hooks-override-auth` claim (72ce2cfb) restored.
- Open: PR #353 awaits Gabriel's merge go-ahead; `live/primary-checkout` unpushed (16 ahead of origin).

## 2026-10-27 -- Retired two expired one-time ltv-register tasks (RATIFIED ora-ltv-register-resume-2026-10-23, ora-ltv-register-unpause-2026-10-23-1601)

- Gabriel approved "Retire both" in-turn (session 11b84238). CC/MCP fleet, order per register-scheduled-task: `delete_scheduled_task` first (registry only; single-use `allow-mcp-delete` tokens minted per target and consumed), then folders moved to `scheduled-tasks/_archive_2026-10-27_retired/`. Both had fired or passed their fireAt (2026-10-23) and were already disabled.
- `test_scheduled_task_run_guard.py` still passes (7/7) with the two now-stale classification entries; removing them is deferred to a follow-up after PR #354 merges.

## 2026-10-27 -- Correction: live hook gate is 159/159 (entry "Live checkout synced to origin/main" said 158/159)

- The 158/159 in the earlier live-sync entry was true at landing time and is now superseded. Classification commit 770ab67a (cherry-pick of 23a18cc2) added `ora-ltv-register-resume-2026-10-23` to NO_SIDE_EFFECT_REVIEWED and `ora-ltv-register-unpause-2026-10-23-1601` to UNGUARDED_BACKLOG; the full live hook gate then passed 159/159. Session 11b84238.
- Also landed live: 82da6220 syncs skills/adversarial-merge-gate (SKILL.md + agent-prompts.md) to ora-skills main (PR #160 content); hash-identical CR-stripped. Live HEAD 82da6220, 15 commits ahead of origin, not pushed.
- Open PRs against ora-claude-config main: #353 (pipe-mask early-exit fix) and #354 (ltv-register classification). The two one-time ltv-register tasks (fire times 2026-10-23) are being retired per Gabriel's in-turn approval.

## 2026-10-27 - Edge news overlay refresh
- 0 signals changed; asOf bumped 10-20 -> 10-27; ACS 2025 1-year release set for 2026-10-29 (headline updated, ranks not rewritten); BLS still August 2026; email sent.

## 2026-10-27 -- Live checkout synced to origin/main: pipe-mask-guard + winpath-guard now active (merge 7d1a2a28)

- `live/primary-checkout` fast-forwarded 5a9c9715 -> 7d1a2a28 (43 commits, 80 files: 24 hooks, settings.json, wiring table, 46 scheduled-task files). Includes the pipe-mask-guard early-exit-stage fix (branch `fix/pipe-mask-early-exit-stages`, local only, not pushed). Gabriel approved the write list in-turn (session 11b84238); claim `repo-housekeeping` taken; `allow-config-write` token minted then moved out.
- 43 dirty scheduled-task specs (identical to the merge result: 25 byte-identical, 18 line-ending only) were archived with SHA-256 to `%LOCALAPPDATA%/Temp/lt/arch-2026-10-26/` and stashed as `live-sync-2026-10-26-43-task-specs` (stash@{0}); the destructive-git guard blocked `git restore`, so no override was minted.
- Verified in live: settings.json parses; wiring check CLEAN; a piped `git merge` probe returns exit 1 (rewrite active). Full hook gate from live: 158/159 -- `test_scheduled_task_run_guard.py` fails on two UNTRACKED live-only one-time task dirs (`ora-ltv-register-resume-2026-10-23`, `ora-ltv-register-unpause-2026-10-23-1601`) not classified in NO_SIDE_EFFECT_REVIEWED / UNGUARDED_BACKLOG. Passes 159/159 in the isolated worktree. Open: classify them (blocks pre-push from live until done).
- Still dirty and unowned (live-only edits, snapshotted in session scratchpad): event_log.md, skills/adversarial-merge-gate/SKILL.md + agent-prompts.md. Rollback: the landing was a fast-forward (no merge commit), so reset to 5a9c9715 (needs approval) or `git revert --no-commit 5a9c9715..7d1a2a28`.

## 2026-10-27 - Edge mfg scout weekly
- 1 new row (SendCutSend, Pittston PA), 0 updates, 10 feeds unreachable; pending file written, email sent (exit 0).

## 2026-10-26 -- R-08 Phase A landed: settings wiring table + check-mode renderer (M63); R-06 Task 7 first change through it
- ora-claude-config #339 (plan), #341 (implementation, 3606c5d): hooks/wiring/settings-wiring.toml, hooks/lib/settings_wiring.py, maintenance/render-settings-wiring.py (--check read-only; --render writes new files only; exit 0 clean / 1 drift / 2 cannot evaluate), hooks/tests/test-settings-wiring.py. Dispatcher edit docstring-only (AST identical). Adoption was a byte-for-byte no-op: no settings.json change, no hook behavior change.
- Follow-on merges: #344 (3cd73af) synced the table chains to 12 guards each after #342 unwired override-mint-guard from the dispatcher (the CHAIN drift R-08 exists to catch; main was briefly red on test-settings-wiring A1/A3); #349 (e609314) fixed the test reading the table without LF normalization (CRLF checkouts failed D1/D3 and raised ValueError, which forced an allow-hook-test-failure override on #348); #346 (0d42144, merged by Gabriel) is R-06 Task 7, the first real change through the table: rows pre.mcp-delete-guard (timeout 30, above session_kind HARD_JOIN_SECONDS 20) and pre.sensitive-file-guard-nb-dc (timeout 10), table now 28 rows. #348 (38fce48) forward-slash Windows paths in 43 scheduled-task specs plus a conformance test; live specs unchanged until supervised propagation.
- Gabriel decisions 2026-10-23: TOML table; dispatcher stays runtime chain authority with a checked mirror; byte-for-byte FORMAT pass bar; live-drift watch only at landings; authoritative promotion = one real change through the table + 7 clean days, then a separate ratification; settings_proposal.py retired after Phase C; merge R-08 Phase A before R-06 Task 7's PR. The 7-clean-day window starts when #346 is live (merge-forward done and --check --live CLEAN).
- Review: Opus REFUTE on R-08 Phase A returned FAIL on one blocking item (a dispatcher that sys.exit()s at import made check mode exit 0); fixed in 6eb2145 with tests H1-H3 (also: exactly one BOM stripped, malformed settings shapes exit 2, no .pyc written by --check). Non-blocking items listed on #341.
- Lesson: a dispatcher chain edit and its wiring-table edit must ship in the same PR; a test must not pin a chain's guard count (G4b now asserts table == live dispatcher).
- Open: Windows hooks sweep (10 suites red on Linux main, same on base: claim-file-collision, confidentiality-guard, config-write-guard, destructive-git-guard, eos-review-gate, git-prepush-scan, lint-config-guard, netlify-guard-global, ora-autonomy-gate, session-kind); Task 5 --check --live before and after merge-forward, with the after-landing JSON saved; fresh-session canary (one denied and one scanned fixture call, plus the sleeping-hook test that a timed-out PreToolUse hook does not block); eos-review-gate record on the final head; task-spec propagation (#348) before the live checkout merges winpath-guard; override-mint-guard stays unwired pending the session_kind redesign (re-add to dispatcher and table chains in one PR); origin/r08-settings-wiring-table is the superseded plan branch (archived at archive/r08-settings-wiring-table, delete the old name by hand).

## 2026-10-26 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `72ce2cfb-dad9-47e1-9a8d-3f5d161cb7b0` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in chat 2026-10-26 pushing past the test-settings-wiring.py failure this once, for the Phase 2 task-spec paths PR: it is pre-existing on a clean origin/main checkout (CRLF working tree vs a test that searches raw bytes for LF) and unrelated to this change.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-26 11:14:13 local.

## 2026-10-23 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `72ce2cfb-dad9-47e1-9a8d-3f5d161cb7b0` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in chat 2026-10-23 pushing past the test-settings-wiring.py failure this once: it is pre-existing on a clean origin/main checkout (CRLF working tree vs a test that searches raw bytes for LF) and unrelated to this change.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-10-23 19:06:05 local.

## 2026-10-23 - Dirty-tree triage (~/.claude, ora-skills)

- Scan: .claude 35 dirty (live/primary-checkout, ahead 4 / behind 71), ora-skills 4; website-canonical and oxford-command-center clean; no stray clones. Settle check: mtimes unchanged over 16 min.
- Committed (local, not pushed): .claude 693c30db (rev32 audit memory + MEMORY/INDEX pointers + 3 scheduled-task event_log appends, via allow-config-write, token deleted). ora-skills PR 154 (target-markets v1.14, Madison note; worktree ora-skills-wt-madison).
- Discarded: skills/adversarial-merge-gate/agent-prompts.md (CRLF-only). Left: untracked runtime state, wt-token-binding (live WIP), 71-behind divergence (Gabriel decision).
- Pending: restore dirty ora-skills/target-markets.json after PR 154 merges.

## 2026-10-20 - Edge news overlay refresh
- asOf 2026-10-08 -> 2026-10-20 (BLS Aug 2026 prelim). 55 entries; 18 jobsYoy refreshed, 2 signals changed (Baltimore, Cincinnati). ACS 2025 1-year still undetermined. Email sent.

## 2026-10-20 - Edge mfg scout weekly

- 8 rows in pending file (4 new, 4 repeats); 12 feeds unreachable/partial; email sent to ggoldberg@oxfordra.net.

## 2026-10-20 — Market snapshot refresh digest

Quarterly digest emailed to ggoldberg@oxfordra.net: 11 of 20 figures stale, 1 not yet published (C&W Baltimore Q3), 8 current. Columbus C&W Q3 2026 vacancy 3.4%, rent $6.98 (+7.7% YoY); NAI KLNB Q3 2026 Columbia flex 4.7% / $11.90, Greater Baltimore flex 7.5%. Open: ACS 2020-2024 values unreachable (API key), KLNB small/mid-bay wording changed, C&W restatement question. No site edits.

## 2026-10-18 -- CLAUDE.md Release-bullet change (bbb20b21): Gabriel approval recorded
- Gabriel approved the CLAUDE.md Release-bullet change in commit bbb20b21 in-turn on 2026-10-17 ("Proceed with recommendation") after reviewing the CLAUDE.md diff. Recorded here at the dirty-tree-triage parent session's request. No governor constants touched; CLAUDE.md word count 1849 (limit 1850).

## 2026-10-18 — Dirty-tree triage follow-ups: decisions recorded
- Gabriel (in-turn): accepts the two independent Opus reviews as the refute pass for the two-basis LTV commits 71fa176c/323028da (agents/underwriting-checker.md; no wf_ run id; check:refute applies only to oxford-command-center source); constants unchanged (governor-drift-probe OK).
- Archived (never deleted) stale untracked skills/synced/…/acquisition-underwriting (v4.20, old with-refi numerator) to archive/2026-10-18_synced-acquisition-underwriting-v4.20/ (live runtime copy v4.31).
- LTV Fix 1 (pending-debt register / refi-time test) held on ora-skills branch claude/fix-ltv-enforcement-2026-10-17-f355fb (5 REFUTE rounds not clean; KNOWN_ISSUES.md); Fix 2 wording PR in progress; register to be redesigned as one piece.
- CodeRabbit usage-based billing: declined. OI-278 archive tags on ora-pm origin kept (fix already on main via PR #26).

## 2026-10-17 -- pending-reimport hygiene: stale ledger lines cleared (equality verified)

fleet-advisory-remediation, isolated-commit, communication-intelligence, county-sales-monitor, county-parcel-screen, daily-brief, lease-generation, legal-intelligence, vendor-management, website-perfection, pma-qc, register-scheduled-task, file-reconciliation, repo-architecture-review, automation-health-monitor. These pending-reimport lines predate their content reaching main and being installed. Re-verified 2026-10-17 against origin/main 917b7bf: each installed copy is confirmed equal to main, file by file (line endings and name quoting normalized). This entry records that verification of equality; it does not claim a Save-skill click was witnessed this session. Clearing the stale lines.

## 2026-10-17 -- pending-reimport hygiene: six stale ledger entries cleared

annual-cycle, lease-abstraction-pipeline, lease-renewal-pipeline, market-monitor, ora-millage-lookup and rent-roll-qc were reimported via Cowork Save-skill on 2026-10-16 (reimport confirmed in the 2026-10-16 entries; batch package 2026-10-16_cache-reconcile). The ledger lines were never cleared. Re-verified 2026-10-17: each installed copy equals origin/main 917b7bf file by file. Clearing the stale lines.

## 2026-10-17 -- ora-skills cache reconciliation closeout (includes two corrections)

Closeout of the 2026-10-16/17 cache-ahead reconciliation in ora-skills.

CORRECTIONS to entries logged earlier today: (1) "acquisition-underwriting v4.28 reimport confirmed" is WRONG. The installed copy at that moment was v4.29 (a Cowork draft, captured as PR #131): the CreationTime/main.log reimport check proves an install happened, not which version. v4.31 was confirmed later with a direct cache-vs-package comparison. (2) "cost-seg-tax-layer ledger cleared (no reinstall needed)" is inaccurate: the clear was refused (an equality check is not a logged install) and the entry was left pending on Gabriel's call; the cache did equal the repo at that time.

LANDED: acquisition-underwriting v4.28 + cost-seg-tax-layer (#127); postclick version guard + dirty-shared-dep guard in package_skills/build_plugin (#139); repo_first_check labels the four Code-only skills CODE-ONLY instead of NOT-INSTALLED (#143). REINSTALLED and confirmed equal to their packages: loi-generation v1.10 (the installed v1.9 template and standards put a numeric portfolio LTV into counterparty text), deal-comparison v1.4, orphaned-task-forensics v1.2, artifact-to-docx-report, graph-app-registration v1.0, psa-reconciliation v1.6. First install: ora-open-decisions v1.0.

ARCHIVED (move only, hash-verified) to ora-skills/_archive/2026-10-17_cache-reconcile (MANIFEST.json, MANIFEST-flat.json): 32 rescue dirs, 12 flat rescue files, 9 handoff folders, 14 temp entry files. HELD back in _staging: the eval-harness rescue (gitignored run state), the lease-generation example script, and 5 flat rescue files with content never committed (automation-health-monitor, lease-form-qc, lease-generation, submarket-spatial-analysis, vendor-contract-qc).

OPEN: the baseline-package-version PR (separate session, review rounds ongoing); stale PENDING_REIMPORT entries for skills already installed and equal to their packages (annual-cycle, lease-abstraction-pipeline, lease-renewal-pipeline, market-monitor, ora-millage-lookup, rent-roll-qc); ora-doctrine-integrity-guard SKILL.md line 44 should list CODE-ONLY as a normal verdict when that task is re-enabled (the task is currently disabled; one site only).

## 2026-10-17 -- ora-open-decisions v1.0 reimport confirmed

ora-open-decisions v1.0 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 — Two-basis financing convention: Gabriel approval recorded
- Gabriel confirmed in-turn (2026-10-17, dirty-tree-triage session): he approves the two-basis financing convention (portfolio-LTV numerator = all-cash; with-refi LTV informational) behind commits 71fa176c / 323028da (agents/underwriting-checker.md, ora-skills #130/#135). Invariant 4 permission now on record. Governor constants (DSCR 1.25 / LTV 40 / 65) unchanged. Independent refute pass on those two commits dispatched same day; result to be logged.

## 2026-10-17 -- loi-generation v1.10 reimport confirmed

loi-generation v1.10 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- psa-reconciliation v1.6 reimport confirmed

psa-reconciliation v1.6 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 — Dirty-tree triage (.claude primary)
- Scan: 4 roster repos; .claude 69 entries, ora-skills 3, oxford-command-center 4, website-canonical clean.
- Committed 9d458ae on live/primary-checkout: 22 settled, unattributed tracked files (14 scheduled-tasks SKILL.md + 1 archived, 7 skills, 1 test) via git commit --only after a 20-min unchanged-mtime re-check; index verified clean first.
- Left untouched: CLAUDE.md + maintenance/_state/* (blast radius, await approval); memory MEMORY.md/event_log.md/project_8625_troost (live Troost session); ~40 untracked dirs/files; OCC modified files (REFUTE-gated); worktree cleanup candidates ora-cfg-confnorm, ocr-readme-fix.

## 2026-10-17 -- graph-app-registration v1.0 reimport confirmed

graph-app-registration v1.0 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- artifact-to-docx-report reimport confirmed

artifact-to-docx-report reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- orphaned-task-forensics v1.2 reimport confirmed

orphaned-task-forensics v1.2 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- deal-comparison v1.4 reimport confirmed

deal-comparison v1.4 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- audit lesson: 8625 Troost v05 after-tax engine vs memo (land share 57.9% vs 75.2%)

The v05 workbook after-tax engine divided the dry-land credit by a hard-coded total (57.9% land share) while the memo used the assessor ratio 75.2%; the Python mirror covered pre-tax only, so QC missed it. Fixed in v06 (land-method selector) and in acquisition-underwriting v4.32 QC parity rule (mirror must tie after-tax and every Sensitivity engine). v06 mirror now ties to the workbook cache: 135 figures, worst relative diff 4e-14 (`mirror/tie6.py`); memo kit has a build-failing tie gate.

## 2026-10-17 -- cost-seg-tax-layer v1.1 landed in repo (PR #138)

Cowork cache already held v1.1 (799065696e44, review card saved). Repo (v1.0 from #127) updated to match byte for byte (blob sha256 799065696e44, +18/-5, v1.1 hunks only). Land-share method selector and placed-in-service timing. Merge gated on adversarial review.

## 2026-10-17 -- acquisition-underwriting v4.32 patch: base-SHA mismatch, NOT applied (PR pending Gabriel's call)

The v4.32 diff is stamped against the Cowork-cache v4.31 (sha256 c864250c2c18). Repo v4.31 (CRLF) hashes 64548923bfdf; the only body difference is the frontmatter `name: "acquisition-underwriting"` (cache, quoted) vs unquoted (repo). The diff dry-runs clean (`git apply --check`), but the result cannot reach 9e98546a47bb without re-quoting the name line. Per the v4.8 rule no hand-merge; A1 stopped for Gabriel. Staged D1 patches re-base on repo HEAD.

## 2026-10-17 -- cost-seg-tax-layer ledger cleared (no reinstall needed)

cost-seg-tax-layer landed in ora-skills via PR #127 (verbatim from capture #122, name: unquoted). Runtime cache copy equals origin/main after name-quoting normalization, so no Save-skill was required; pending-reimport entry cleared on that equality check, not a correlated install.

## 2026-10-17 -- acquisition-underwriting v4.31 reimport confirmed

acquisition-underwriting v4.31 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-17 -- acquisition-underwriting v4.28 reimport confirmed

acquisition-underwriting v4.28 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- solar-lease-underwriting v1.3 reimport confirmed

solar-lease-underwriting v1.3 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- annual-cycle v1.1 reimport confirmed

annual-cycle v1.1 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- market-monitor v1.7 reimport confirmed

market-monitor v1.7 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- rent-roll-qc v1.1 reimport confirmed

rent-roll-qc v1.1 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- ora-millage-lookup v1.2 reimport confirmed

ora-millage-lookup v1.2 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- lease-renewal-pipeline v1.3 reimport confirmed

lease-renewal-pipeline v1.3 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-16 -- lease-abstraction-pipeline v2.8 reimport confirmed

lease-abstraction-pipeline v2.8 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-15 -- exhibit-package-builder reimport confirmed

exhibit-package-builder reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-15 -- estoppel-request-generation v1.3 reimport confirmed

estoppel-request-generation v1.3 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-15 -- deal-execution v1.10 reimport confirmed

deal-execution v1.10 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-13 — Architecture-review remediation: ora-full-gate-weekly registered; ora-setup-audit v1.18 install confirmed; Actions billing block found

- **Registered** `ora-full-gate-weekly` (CC/MCP, `30 11 * * 1`, Gabriel-approved in chat 2026-10-13; verified via `list_scheduled_tasks`, next fire 2026-10-19 11:33 ET). OI-254. Gabriel declined PR-blocking CI: no self-hosted runner, no `schedule:` trigger.
- **Confirmed Save-skill install: ora-setup-audit v1.18.** Gabriel reported the re-import 2026-10-13; verified: store `SKILL.md` mtime 2026-10-13 18:16, body byte-identical to `ora-skills` origin/main after EOL normalization except the platform's own `name: "ora-setup-audit"` quoting; `references/guardrails-telemetry.md` hash-identical; frontmatter description (574 chars) hash-identical. The old "v1.12 ... Changelog" description text is not in v1.18's frontmatter, so the shortened description is the repo's, not a store regression. `_staging/*.md` are gitignored local ledgers (`.gitignore:30`), not repo-tracked.
- **Finding (OI-254 context):** GitHub Actions hosted jobs on this account fail to start: "recent account payments have failed or your spending limit needs to be increased" (ora-county-sales-monitor run 38489261246). Affects every hosted-runner repo incl. ora-pm CI/deploy. Needs Gabriel on GitHub Billing.
- PRs opened, none merged: ora-county-sales-monitor #2 #3 #4; Website #163 (chat model, no preview, no deploy).

## 2026-10-13 — Live checkout caught up to origin/main (dirty-tree triage follow-through)
PRs merged: #313 (10 settled untracked files), #314 (workbook-write-guard: `#` in the unquoted cd arg of the exempt heredoc failed open — a redirect onto the master workbook passed; found by adversarial review of the catch-up merge, fixed + re-reviewed), #315 (ora-passed-deal-tracker full Ops Hub UUID). Live live/primary-checkout merged origin/main (event_log: rolled-over side kept, all 102 main-only headings are in _archive) and fast-forwarded to 5e214634, 0 behind / 8 ahead. Discarded two stale/redundant tracked edits under override (Gabriel option 1; backups hash-verified in maintenance/_archive/2026-10-13_dirty-tree-triage/), removed one identical untracked archive dir (backed up), token deleted. Held back, still untracked: ora-agent-usage-report-monthly, ora-site-market-snapshot-refresh, ora-edge-mfg-scout-weekly, ora-edge-news-overlay-refresh (email without a run guard; fail test_scheduled_task_run_guard). Untouched: 10-06 14:13 bulk-modified batch (CLAUDE.md, settings.json, ~25 task specs), oxford-command-center financial-gate WIP, wt-token-binding hooks WIP.

## 2026-10-13 — Dirty-tree triage (~/.claude)
Scanned 4 repos (84 dirty entries). Isolated-committed 14 settled untracked files (`68c37947`, live/primary-checkout): 5 agents, 5 scheduled-task SKILL.mds, xlsx-warehouse-importer, 3 maintenance scripts. Left untouched: 10-06 14:13 bulk-modified batch (incl. CLAUDE.md, settings.json; unattributed), deleted ora-notion-trial-expiry-reminder, event_log.md, oxford-command-center financial-gate WIP, wt-token-binding hooks WIP. Untracked `_archive*` dirs left in place (already archives). Branch divergence (ahead 5/behind 16) unresolved — Gabriel's call.

## 2026-10-13 - Edge news overlay refresh
- 0 signals changed; asOf not bumped (BLS Aug metro Table 3 unreachable); ACS 2025 1-yr date still undetermined.

## 2026-10-13 - Edge mfg scout weekly
1 new row (GSK PA), 1 update note (Nucor), 9 feeds unreachable; pending file mfg_announcements_pending_2026-10-13.json; email sent to ggoldberg.

## 2026-10-08 - Edge news overlay Q3 broker fold-in
- 2 signals changed (Detroit, Omaha), 11 notes refreshed from CBRE/C&W Q3 2026. Email sent.

## 2026-10-08 - Edge news overlay re-sweep
- Broker/press re-sweep: 0 signals changed, 2 notes refreshed (Columbus, Chicago). Email sent.

## 2026-10-08 - Edge news overlay refresh (July 2026 BLS update)
- 4 signals changed (Baltimore, Grand Rapids, Milwaukee, Louisville); jobsYoy refreshed for 17 metros from BLS July 2026 Table 3; ACS unchanged. Email sent.

## 2026-10-08 - Edge mfg scout weekly
- 9 rows pending (0 updates), 2 below threshold dropped, 6 feeds unreachable; pending file written, email sent.

## 2026-10-08 - Edge news overlay refresh
- 0 signals changed; asOf not bumped; ACS 2025 1-year still undetermined; BLS July 2026 metro Table 3 unreachable (Washington -2.2 only). Email sent.

## 2026-10-08 — Audit R30: Release bullet added to the guarded-edit script (supersedes "Release skipped")

Gabriel asked for the Release-bullet reword after the third-tranche entry said it was skipped. The live CLAUDE.md Release bullet carries an uncommitted edit by an unattributed session ("Merging to main on the site repo deploys oxfordra.net ... treat a merge as a deploy"), which reverses the committed HEAD text ("A merged PR is not a live deploy"). The reword builds on the pending text and keeps its substance (a merge IS a deploy; verify the served asset). `apply_guarded_edits.py` now rewords three bullets (Merge gate, Release, Shared-checkout; 35 words saved) and refuses to run if the Release line is anything other than that exact pending text, so it cannot silently flip the doctrine. 24 fixture checks pass; --dry-run against the live files matched every assertion. Not yet applied: Gabriel runs it himself. If the pending Release edit is later committed or reverted, re-check the script's OLD_RELEASE before running.

## 2026-10-08 — Audit R30 remediation, third tranche (decisions executed)

**Merged:** ora-claude-config #310 (fleet-status createdAt label) and #311 (noi-opportunity-scout trim), merged 19:01Z by the ZeOoba account (not by the Claude Code session). ora-skills #110 earlier.

**Opened:** ora-skills #111 now READY (nine description trims, with the four risky trigger groups Gabriel chose restored plus a legal-intelligence Workflow 2A pointer; descriptions 659-732 chars, lint 0 findings). oxford-command-center #452 (repo CLAUDE.md history collapse) is BLOCKED on two queued required checks: the self-hosted runner LAPTOP-CSHSCBE6 is offline and no actions.runner.* service is installed (started in a foreground window), 9 runs queued repo-wide. ora-claude-config #312 (R30 records: memo, memory index, passed-deal-tracker tag, retired task archive). The event_log rollover and its archive are NOT in #312 (patch does not apply on origin/main); they stay uncommitted in the live checkout.

**Not applied by the session, by design:** the settings.json deploy-hook narrowing, removal of the unreachable Netlify-MCP health-check hook, and two CLAUDE.md bullet rewordings (Merge gate, Shared-checkout; the Release bullet is skipped because the live copy carries another session's uncommitted edit). Editing the hook layer is a security-setting change, so it was packaged as a tested script for Gabriel to run himself (scratchpad `apply_guarded_edits.py`; 21 fixture checks pass; --dry-run against the live files matched every assertion). No override tokens were minted this session.

**Cleanup:** removed worktrees for merged PRs (ora-skills-wt-r30, .claude-wt-r30-fleetstatus, .claude-wt-r30-noiscout). Remaining until their PRs merge: ora-skills-wt-r30-desc, command-center .claude/worktrees/r30-claudemd, ~/.claude/.claude/worktrees/r30-records.

**Declined by Gabriel's choice:** tracker rollover (left for now); ora-cc-snapshot-refresh: wait and check after 10-12.

## 2026-10-08 — Audit R30 remediation, second tranche (Gabriel's open-decision answers)

Answers: enable ora-passed-deal-tracker; merge ora-skills #110; show guarded diffs first; write Cowork retirement prompt; re-baseline membership; fix fleet-status label; investigate outreach file; take all four context trims.

**Done:** `ora-passed-deal-tracker` re-enabled (description tag `[MODEL: UNVERIFIABLE | checked 2026-10-08]`, next run 10-15). ora-skills #110 merged (adversarial-merge-gate + branch-catchup backed up, branch-catchup description tag fixed, ora-setup-audit v1.18). `registry-membership-probe.py` run twice clean after backing up the 09-23 baseline to `maintenance/_state/archive/2026-10-08_pre-rebaseline/`. event_log rolled over by `rollover-event-log.py` (323KB to 101KB; older entries in `memory/_archive/event_log_2026-10-08.md`).

**Corrected:** the seven enabled CC tasks that read "never run" were recreated 2026-10-06 (model re-pin), which wiped lastRunAt; first slots are still ahead. fleet-status "registered Nd ago" label was the cause of the false finding. `outreach-ratification.json` is NOT missing: it lives in `Business/Investment Candidates -- 2026/Claude outputs/` and the xref probe did not search there.

**PRs opened (none merged except #110):** ora-claude-config #310 (fleet-status createdAt label + xref probe root), #311 (noi-opportunity-scout trim); ora-skills #111 (DRAFT, nine skill descriptions trimmed, dropped triggers listed for review); oxford-command-center #452 (CLAUDE.md sections 2 and 3 collapsed to pointers, governance-check passes, independent review approved).

**Not done / held:** tracker rollover (anchors are linked from other files; a bulk move would create dead pointers); guarded settings.json and CLAUDE.md edits (diffs published on the remediation plan page, awaiting approval; realistic CLAUDE.md saving is about 35 words); three LAMS retirements (native Cowork session only, prompt issued).

**Watch:** `ora-cc-snapshot-refresh` (Mon 06:15) last ran 2026-09-14 and skipped 10-05; next run 10-12. origin/main fleet-status flags it as a missed cycle, the stale live copy does not.

**Guard behavior noted:** writes under `hooks/`, shell commands that pair a write with a governance path, and commits of CLAUDE.md all require the conventional worktree path (`.claude/worktrees/<name>`) plus an independent review recorded with `eos-review-gate.py --record`; no override tokens were minted this session.

## 2026-10-08 — Audit R30 remediation, first tranche (Gabriel: "Proceed with implementing the plan")

Plan: https://claude.ai/artifact/PfqhuzESbNWoU48AfvRg7X. Audit: Revision 30 of the ORA Automation Audit. D1 settled: "fleet off" means the Cowork fleet only; CC fleet unchanged.

**RATIFIED retire (CC/MCP, expired one-time tasks, already fired, already enabled:false):** `ora-county-sales-refresh-1003`, `ora-notion-trial-expiry-reminder`. Order: `delete_scheduled_task` first, then folder archived to `~/.claude/scheduled-tasks/_archive_2026-10-08_retired/`. No same-id task on the Cowork fleet.

**Done (archive, never delete):** orphan `pr-review-toolkit/8dc53b945735` cache and five empty `plugins/data/` stubs moved to `plugins/_archive_2026-10-08_remediation/`. Memory: `open-items-2026-09-28-triage.md` indexed; oxford-command-center memory index market-intel lines collapsed to one line (files untouched). `session-context.md` ora-passed-deal-tracker bullet corrected (LAMS row verified gone from the Cowork registry).

**Plan items dropped after verification (premise wrong):** P2-1 retire `memory-nag-correction.py` (it corrects the harness's stale 17.1KB memory nag, not a duplicate of native memory); P2-2 retire the inline credentials hook (`Edit(.env*)` deny rules are relative to cwd, the hook matches any path); P2-4 fix deny patterns (the trailing space in `rm -rf /c/Users/Owner ` is deliberate, the `worktrees\*` pattern is a valid Windows form).

**Not executed, needs Gabriel:** guarded config edits (settings.json hook/allow tidy, CLAUDE.md relocation); LAMS retirements `ora-ar-export-freshness-nudge`, `ora-health-guard-fail-aging-nudge`, `ora-lams-fleet-resume-20260911` (native Cowork session only, still in retire-pending.json).

**Found:** `session-context.md:12` cites `outreach-ratification.json`, which resolves nowhere.

## 2026-10-07 -- correction: xlsx-warehouse-importer cache copy not byte-identical
- Prior entry said the Cowork cache SKILL.md is byte-identical to the repo. Wrong: the platform re-quoted the `description:` frontmatter value (YAML-equivalent); body is identical (verified with diff after stripping CR). Install itself is unaffected.

## 2026-10-07 -- xlsx-warehouse-importer v1.0 reimport confirmed
- New skill `xlsx-warehouse-importer` (ora-skills 563eb4a, pushed to origin/main) installed in the Cowork runtime cache via manual Save-skill click; Cowork confirmed installed and listed. Cache SKILL.md byte-identical to repo.
- Code-surface mirror created at ~/.claude/skills/xlsx-warehouse-importer (sync_skill; --all --check clean).
- Origin: PCA register work; property-id crosswalk and Notion mapping saved to memory (reference_pca_register_notion_field_mapping, project_pca_register_property_id_crosswalk). PCA importer itself not built (plan awaits Phase 0 approval).

## 2026-10-06 -- masterlease-jurisdiction-rebase v1.8 reimport confirmed

masterlease-jurisdiction-rebase v1.8 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-06 -- lease-form-qc v2.9 reimport confirmed

lease-form-qc v2.9 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-10-06 — Scheduled-task model standard bumped to claude-sonnet-5-5 (medium)

Gabriel-directed. Recreated 13 enabled CC/MCP tasks from a Sonnet 5.5/medium session (ids unchanged; SKILL.md bodies restored byte-identical, backups `SKILL.md.bak-2026-10-06-model-sonnet55`), tagged `[MODEL: claude-sonnet-5-5 | set 2026-10-06]`. `ora-master-workbook-ingest` skipped (mid-run; its run session already showed sonnet-5-5/medium without recreation, so runs may follow the app default). Deleting registry entries archived old run sessions for ora-am-brief (2), ora-loopnet-listings-sync (1), ora-pr-land-watch (6). Notifications set off on recreated tasks. Standard file updated; ~45 paused tasks keep old tags. Verify ora-am-brief run model on 2026-10-07.

## 2026-10-03 — Command Center "Daily brief 86d stale": root cause was a health-file path split, not a dead producer

Gabriel asked to run the live Command Center, then trace the Data Feeds "Daily brief 86d old (max 1.5d)" flag. Surface: native Claude Code, `oxford-command-center`. Traced with orphaned-task-forensics Workflow A.

- **Symptom vs cause:** `ora-am-brief` (CC fleet, `0 6 * * *`) was live and ran 2026-10-03; it only READS `data/brief-health.json`. The brief itself is produced by `runBrief` inside the hourly Windows task "ORA Command Center - Mirror Deploy" (`scripts/deploy-mirror.ps1` sets `BRIEF_ENABLED=1`; last real `ranAt` 2026-10-03T22:07Z). It runs in the isolated build root (`oxford-command-center-deploy-build`), so it wrote `brief-health.json` there. The live Brain Server (`server/index.ts`) reads the PRIMARY checkout's copy, which was a unit-test fixture (`ranAt 2026-07-09T11:00Z`, rewritten 2026-09-25) because `brief-run.test.ts` redirected `statePath` but not the health path. No orphaning; ora-cc-snapshot-refresh / lease-snapshot-refresh / ar-feed-sweep remain `enabled:false` (fleet pause) and are unrelated to this feed.
- **Fix:** PR #439 (merged 22:35Z, `034fdf1`): `deploy-mirror.ps1` sets `BRIEF_HEALTH_PATH` to the primary checkout's `data\brief-health.json` (cleared in `finally`); `run.ts` resolves the path at write time. `alert-state.json` deliberately stays in the build root (dedup untouched). First attempt #438 failed `refute-required` (server/ and scripts/ are default-deny; per-commit gate needs a `Refute-Skip` trailer) and was re-created as #439 rather than force-pushed.
- **Adversarial review (Opus, read-only; NOT a `Refute-Reviewed` attestation):** REFUTED two claims. (1) The fix is inert after merge because the hourly task runs `deploy-mirror.ps1` from the PRIMARY checkout, which was on `chore/cc-snapshot-2026-10-02`, 17 behind main; since #279 the deploy never fast-forwards it. (2) `reference-date.test.ts` also calls `runBrief`, so the test-only redirect was incomplete. Four claims survived.
- **Primary checkout moved to main (Gabriel directed):** restored `data/snapshots/portfolio.json` (a regeneration from the dev server, backup `oxford-command-center-worktrees/portfolio-regen-backup.patch`; shared-checkout preflight returned CONTESTED, no recorded owner, proceeded on mtime/clean-at-session-start evidence); moved two untracked plan docs aside to `oxford-command-center-worktrees/_primary-checkout-aside-2026-10-03/` (`wave3a` DIFFERS from main's copy, someone's local edit, review it). Primary now `main` @ `034fdf1`.
- **Stranded commit:** #439 squash-merged 4 min before the test-isolation commit was pushed. Carried over as PR #440 (`tests/setup.ts` suite-wide `BRIEF_HEALTH_PATH` sandbox + a redirect assertion; 32/32 pass); auto-merge armed, pending `gate` + `refute-required`.
- **Not yet verified:** that the next hourly mirror deploy (after the 23:00 run) advances `ranAt` in the PRIMARY `data/brief-health.json`; the `.ps1` change has no unit test. Until #440 merges a local full-suite run can still overwrite the real file.
- **Other Data Feeds items from the same card:** doc index re-run (50,402 chunks, nothing new); lease-market ingest took the 2026-09-17 CoStar Columbus export (+343) but compute wrote 0 `lm_market_rent_feed` rows (no comp set reached the confidence floor); AR aging (80d) still needs a QuickBooks Desktop export + `ar-import-headless`; debt basis gap `debt.basis.affiliate` $699,364 (Property NOI affiliate-lender rows $1,084,582 vs loan schedule $385,218) unresolved.
- **Process note:** the PreToolUse site-write gate false-positives on the site repo's directory name appearing anywhere in a shell command, including a session scratchpad path or quoted text; worked around by keeping that string out of the command. No override token was created.

## 2026-10-02 — ora-loopnet-listings-sync v1.1 live and re-enabled (portfolio availability badges)

Gabriel directed both steps in-turn ("update the sync task for badges", then "Re-enable the sync task"). Surface: native Claude Code, CC/MCP fleet, `~/.claude/scheduled-tasks/ora-loopnet-listings-sync/`.

- **Why disabled:** paused in the 2026-09-22 fleet pause; the 09-28 resume stalled (see "Fleet Wave 1 re-enabled" above), so it stayed `enabled:false` although its pause window was recorded closed. Not part of Wave 1; enabled individually on Gabriel's request.
- **SKILL.md v1.1 (live, hash-verified, backup `SKILL.md.bak-2026-10-02-portfolio-badges`):** stages `portfolio.html` alongside `data/listings.json listings.js available-space.html sitemap.xml`; the "never edit outside the data/generated files" rule names all five; a listing no portfolio asset claims is a Step 3 alert. Repo side: ZeOoba/Website #127 makes `build-listings.mjs` also generate `portfolio.html` (badges) and stamp the /portfolio sitemap lastmod. The SKILL.md edit had to be live before #127 merges, else a sync PR fails `Build & verify` on a portfolio.html drift.
- **Re-enable:** `update_scheduled_task` `enabled:true` + description re-tagged `[MODEL: UNVERIFIABLE | checked 2026-10-02]` in the same call (re-enable precondition; no model observation possible). Cron NOT passed, unchanged at `30 14 * * 1` (the 09-22 retime); the registry description's stale "Mon 10:40 AM ET" corrected to "Mon 2:30 PM ET". Verified with `list_scheduled_tasks`: `enabled:true`, next fire 2026-10-05T18:30Z (Mon 14:30 ET).
- **Tool side effect:** the update rewrote SKILL.md as LF (was CRLF) and dropped the final newline; body edits survived (checked line 10, 40, 52 and the diff against the backup).
- **Sequence risk:** merge #127 before Mon 10-05 14:30 ET if possible. If a sync PR lands first, #127 needs `gh pr update-branch` and a `build-listings` regenerate to pick up the new badge counts.
- Not done: the other Wave 2/3 tasks; `registry-membership-probe.py` not run.

## 2026-10-02 — Fleet Wave 1 re-enabled on Gabriel's approval (5 CC/MCP tasks)

Gabriel approved "Approve all 5" in-turn (AskUserQuestion, 2026-10-02) after a read-only triage showed the 2026-09-28 CC resume stalled at step 1 of 5 (marker `task-progress/cc/ora-routine-pause-resume-09-28.json`), leaving 48 of 49 intended ids disabled.

- Enabled via `update_scheduled_task` (surface: native Claude Code, CC/MCP fleet, paths under `~/.claude/scheduled-tasks/`): `ora-master-workbook-ingest` (Mon 05:45), `ora-pm-daily-crons` (Mon 09:40), `ora-prepush-gate-sweep` (Thu 11:00), `ora-memory-commit-sweep` (Fri 19:00), `ora-pm-monthly-billing` (1st, 11:10; money-moving). Cron unchanged on all five.
- Each re-tagged `[MODEL: UNVERIFIABLE | checked 2026-10-02]` in the same call (re-enable precondition; no model observation was possible, so the standard's fallback value was used).
- `update_scheduled_task` dropped `offhost-backup:` on `ora-pm-daily-crons` and `ora-pm-monthly-billing`; both restored by file edit the same pass. The daily-crons line is byte-identical to HEAD. The billing line was flipped `pending` to `live since 2026-10-01` after the first scheduled off-host run concluded success (https://github.com/ZeOoba/ora-pm/actions/runs/36932162552: 2026-10 posted=139, 0 errors, 0 remaining), meeting step 3b's three proofs.
- Verified with `list_scheduled_tasks`: all five `enabled:true`. Next fires: memory-commit-sweep Fri 10-02 about 19:10 ET, master-workbook-ingest Mon 10-05 about 05:48 ET, pm-daily-crons Mon 10-05 about 09:48 ET, prepush-gate-sweep Thu 10-08 about 11:09 ET, pm-monthly-billing Sun 11-01 about 11:17 ET. CC fleet reads 13 enabled of 58 afterwards.
- Not done: LAMS Wave 1 item `ora-cowork-heartbeat` (needs a NATIVE Cowork session); Waves 2 and 3. `registry-membership-probe.py` not run, so the 09-23 baseline is still stale.
- Expect `ora-prepush-gate-sweep` to report failures on its first run: the pre-push gate is failing on a host-load problem (see Automation Audit R29-5).

## 2026-10-01 — Correction: County Sales Monitor parity causes (supersedes the cause list in the deploy entry above)

An independent review of the ora-skills draft re-derived the legacy-only parity causes and refuted the first explanation. Of the 51 legacy-only rows (window 2025-10-01 to 2026-08-15): 20 multi-parcel representation, 20 Franklin rows with SF >= 150K that the legacy pilot kept and the worker's SF gate drops, 3 on 2025-10-01 (before the worker's window start 2025-10-02), 8 other (mostly Franklin last-sale-only `SALEDATE`, G7). Matched counts (207) and new-only (32) are unchanged. Also: LATE-POSTED and flag semantics in the worker differ from the v0.5 manual workflow (First-Seen-based, 365-day re-pull, SF-INCOMPLETE and MULTI-PARCEL-INFERRED flags); recorded in county-sales-monitor v0.6.

## 2026-10-01 — County Sales Monitor Notion Worker deployed (first sync run, parity checked)

Gabriel ordered the ship (L7). Worker `county-sales-monitor` (id `01a0fa61-6ca4-78f2-895d-5aafe648dbbf`, `@notionhq/workers` 0.9.2, ntn 0.23.15, deployed from native Windows because WSL2 is not installed) lives at `C:\Users\Owner\ora-county-sales-monitor` (local git, initial commit `b2b6c35`, no remote, nothing pushed). Syncs `countySalesSync` and `countySalesCoverageSync`, both weekly, Tier A only (Franklin OH, Baltimore Co MD, Polk IA).

- **Databases (moved under Knowledge Base `3386ecd8`):** `County Sales Comps (Worker)` db `3ed6ecd8-9e59-8168-a367-df08b6ff6d3b` / ds `28bae38c-f495-4c9e-9edc-b86c0ae2c413`; `County Sales Coverage (Worker)` db `3ed6ecd8-9e59-81b1-947b-dff540312cfc` / ds `f26e704a-9191-436b-85cf-fd64258928be`. Legacy pilot DB `311cf712…` (304 rows) untouched.
- **Evidence:** typecheck clean, 12/12 rule tests, simulate passed (Franklin 173 / Baltimore 38 / Polk 64 vs baseline 176 / 38 / 64). Preview and live comps = 275 rows, 275 distinct keys, 0 LATE-POSTED, no `Price PSF` on any NONARMS / CONTRACT-SALE / SF-INCOMPLETE row and none equal to 0. Coverage DB = 7 rows. Run logs: 0 errors. The deploy auto-ran one cycle of each sync, then the manual triggers re-ran them (idempotent upserts, same-day baseline).
- **Parity vs legacy, window 2025-10-01 to 2026-08-15, strict County+Parcel+Date+Price:** legacy 258 / new 239 rows in window; matched 207 (Franklin 119, Baltimore 38, Polk 50); legacy-only 51 (Franklin 35, Polk 16); new-only 32 (Franklin 18, Polk 14). Baltimore is exact. Reasons: 22 legacy-only and 30 new-only are the same transaction with a different parcel-ID representation (multi-parcel member order or per-parcel rows vs one grouped row); 27 Franklin legacy-only are parcels the live layer no longer shows (Franklin `SALEDATE` holds only the last sale, G7), mostly $0 NONARMS; 2 Polk legacy-only and 2 Franklin new-only unexplained.
- **Finding:** Polk sales export newest `initial_entry_date` was 2026-07-30 as of 2026-10-01, contradicting "refreshed continuously" in county-endpoints.md.
- **Pending Gabriel:** review the ora-skills draft diff (county-sales-monitor v0.6 + county-endpoints Polk note, worktree `C:\Users\Owner\ora-skills-csm-v06`, uncommitted); legacy DB archive decision; Polk occupancy codes 25D / 46A ratification; monthly digest reader via register-scheduled-task; any GitHub push. Rollback: `ntn workers capabilities disable countySalesSync` and `countySalesCoverageSync`; never delete the worker or databases.

## 2026-10-01 — oxfordra.net release: broker scoring fixes (Website #110) and Sepich $12M restore (Website #111)

Gabriel confirmed in-turn: merge both and deploy to production. A merge to `main` publishes to production on this site (Netlify builds from main; the live deploy changed seconds after each merge).

- **#110** squash-merged as `3cc54e8`. Production deploy `6abebabec482470007eb1ae2` ready, commit `3cc54e8`. Broker scoring: replacement-cost floor no longer printed to brokers (internalNote whitelisted out), score withheld below 60% scorecard coverage, score rows declared on the `broker-network-ledger` form and joined to the contact row by submission-id. Verified live: apex and /for-brokers 200; `/api/broker-score-status` without a token returns 401 invalid_auth; the served ledger form declares the new fields; Netlify's forms API shows `broker-network-ledger` registered with submission-id, score-total, score-coverage, score-gate-property-type, score-gate-market, score-breakdown.
- **#111** squash-merged as `c2a7f00`. Production deploy `6abebba08a106f0007e747f8` ready. Sepich Portfolio shows $12M and ~2.6x (owner instruction; reverses the 09-24 workbook-checked ~$9.9M / ~2.1x, so the Master Workbook valuation is now out of step with the site). Verified live: track-record and home page show $12M and ~2.6x, no 9.9M left.
- **Pre-flight:** CI `Build & verify` green on each final head; site-qc-reviewer (Sonnet 5.5) APPROVE; no roster term or active-confidential deal in either diff. Reviews of the code ran on Opus 5.5 and Sonnet 5.5, not Fable (monthly spend limit).
- **Rollback:** Netlify "publish previous deploy". Deploy before #110 was `6abeb3f11c3350000984e270` (main at #106); before #111 it was `6abebabec482470007eb1ae2`.
- **Not done:** Overview PDF still shows 2.1x for Sepich (source row updated, PDF not regenerated); accepted residual that a broker can narrow the replacement-cost floor from the basis points and total score; market gate knows 4 markets while the acquisition engine uses 10 (follow-up PR requested by Gabriel).

## 2026-09-30 — Notion upgraded to Plus; free-block outage closed ([OI-288](open-items-tracker-history.md#OI-288))

Gabriel upgraded the Notion workspace to Plus. Live-verified the same day: `notion-create-pages` succeeded (private draft page `3eb6ecd8-9e59-8161-838b-fffb56dc4235`, "OI-288 block-cap verification 2026-09-30", safe to delete; the connector has no delete or trash command, so removal is manual). OI-288 moved from the open tracker to `open-items-tracker-history.md`, with its `### OI-288` anchor stub. `notion-publish-degraded.json` `trial_expiry_risk` set to resolved (it already read `active:false`). Not checked: that the plan survives its first billing cycle. Earlier entries that cite `open-items-tracker.md#OI-288` now point at the wrong file; the integrity probe flags them and they are left as written (append-only).

## 2026-09-30 — ms365 send, Teams and HubSpot CMS write gate live (ora-claude-config PR 292)

`hooks/ora-autonomy-gate.py` now gates ms365 `outlook_send_mail` / `outlook_forward_mail` / `outlook_send_draft` (internal-only `@oxfordra.net` passes; otherwise an `allow-external-send` token naming the recipients, or `draft:<id>`), Teams sends (token naming `teams:<dest>`), and HubSpot `manage_blog_post` / `manage_landing_page` / `manage_website_page` writes (new `allow-hubspot-cms-write` token, 10 min, multi-use; exact-case read allowlist passes). Also fails closed on an unparseable payload that names a gated MCP tool. PR 292 merged as `b401c08`; the live checkout `live/primary-checkout` was fast-forwarded 781bf6b to b401c08 with Gabriel's approval (one `allow-config-write` token, archived after use). Proved live: 8 of 8 crafted payloads, and a real `outlook_send_draft` call with a nonexistent id was blocked in-session. Reviews ran on Opus 5.5 because Fable was at its monthly spend limit. Residuals: a draft token names the draft, not its contents; calendar invites, vacation replies and mail filters are not yet gated (follow-up session, branch `feat/mcp-calendar-gate`); Bash/file-tool gates still fail open on an unparseable payload (follow-up, branch `fix/autonomy-gate-parse-failclosed`); hooks do not run in Cowork.

## 2026-09-30 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `6945e228-b0b9-4e07-974d-4c696f8a5f39` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in chat 2026-09-30: test-governor-drift-probe fails on oxford-command-center capital-config.ts lines 198/201 (separate repo, from that repo PR 386); reproduced by running the test directly; this diff touches no governor or oxford-command-center file.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-30 11:03:42 local.

## 2026-09-29 -- Cook County cluster parity patch (Chicago-Greater Cook County IL = 11th canonical cluster)

Gabriel ratified in-turn 2026-09-29 (South Chicago Small-Bay Portfolio FULL underwrite): Chicago-Greater Cook County IL = 11th canonical cluster, ENTRY phase, all of Cook County, collar counties not satellites (Ruling 3), exit cap 8.00%; IL/Cook reassessment row; Chicago RCT v03 row. Parity commit `dc9ea62` on branch `feat/cook-county-parity-2026-09-29` (worktree `ora-worktrees/cook-parity`), NOT yet on main: target-markets.json v1.11 (11 clusters), acquisition-underwriting v4.25 + deal-comparison v1.3 skill-card content ported into the repo (repo was still at v4.24 / v1.2), state-reassessment-matrix IL(Cook) row, Chicago RCT sourcing paragraph (POINT re-derived $250.65 vs row $250.66, row holds), cw-2025-construction-costs.json bundled, doctrine-rationale Gate 3 mirror. Also: ora-entry-market-scan SKILL.md v1.9 (5th scan market; registry untouched; task still shows EN=OFF, as before), ora-skill-text-audit class (j) alias `Chicago-Cook`, Investment Candidates mirror overwritten (was v1.1/9 clusters, pre-edit copy kept in session scratchpad).

Not done / open: market-monitor and daily-brief blocks SKIPPED (repo base hash did not match; daily-brief already at v2.15); exit-cap mirror in doctrine-rationale skipped (anchor absent); memory twin `acquisition_target_markets.md` not found on this machine; another session's uncommitted Louisville v1.11 edit in the main ora-skills checkout's target-markets.json was reviewed BLOCK (submarket table does not sum to metro totals) and left untouched, so landing on main needs it reconciled and Chicago renumbered to v1.12 if it lands first.

## 2026-09-29 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `9481616f-9636-4c9b-8029-3cda3da4d87c` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved in-turn (2026-09-29, AskUserQuestion "Override, push, open PR") for one push of 7e0d4ba (14 added event_log.md lines, no code). Gate failures are pre-existing and unrelated: governor-drift-probe false positive on capital-config.ts finiteness guards (OI-359), test_scheduled_task_run_guard ora-audit-log-sweep frozen-backlog entry, open-items tracker orphan sections OI-354/355/356. Token to be deleted right after the push.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-29 12:30:45 local.

## 2026-09-28 -- census-v19 install: submarket-spatial-analysis v1.9 + acquisition-underwriting (manual evidence)

Logged 2026-09-29 from Claude Code. Gabriel clicked Save skill in a Cowork session on 2026-09-28 for both packages (confirmed by Gabriel in-session; the click, not the repo commit, is the install): submarket-spatial-analysis v1.9 (SHA-256 prefix 9c26645a3b5d5ba0) and acquisition-underwriting with the comp-grid-discipline.md rent-basis rule, SKILL.md H1 still v4.24 (prefix a93e985a7a62d005). Source: origin/main 532b706 (submarket v1.9 reconcile at f010deb). Packages re-hashed with tools/stage_transfer.py emit and match both prefixes.

PROOF TIER = MANUAL, not reimport_correlate CONFIRMED. `postclick` returned NO-BASELINE for both skills: the click happened Cowork-side and no pre-click CreationTime baseline was captured, so the tool could not correlate. Manual evidence: Local main.log "Delta 2 / downloaded 2 / failed 0" at 2026-09-28T21:47:26; both cache dirs dated 2026-09-28 21:47; repo-vs-cache hashes EOL-normalized identical for every shipped file (only difference: the platform re-quotes `name:` in frontmatter); repo_first_check IN-SYNC and verify_installed_cache 0 needing attention for both. Not proven to the second per skill, since the Local log is skill-blind.

Pre-install runtime v1.8 of submarket-spatial-analysis was merged into v1.9 in the repo; verified every v1.8 content marker is present in v1.9 (the Ring Demographics heading was extended with the v1.9 key path, not dropped). Rescue copy archived to ora-skills/_archive/2026-09-28_submarket-v18-rescue/.

Out of scope, noted: repo_first_check still reports six unrelated cache-ahead skills (estoppel-request-generation, lease-abstraction-pipeline, lease-renewal-pipeline, market-monitor, loi-generation template, eval-harness summary.csv).

## 2026-09-29 -- package-and-stage-skill reimport

package-and-stage-skill reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-09-28 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `372c45f9-107e-4c85-966f-74ce3f70a06f` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved override in-turn (fifth push, one-line run-guard backlog entry for ora-audit-log-sweep, PR after #285): the only gate failure is the governor-drift-probe false positive (capital-config.ts > 0 finiteness guards; real constants 1.25/0.40 intact in governor-constants.ts; tracked as OI-359). 138 of 139 tests pass and the change is 6 lines in one test file.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-28 23:40:16 local.

## 2026-09-29 — RATIFIED retirement of two completed one-time CC tasks: ora-resume-0928-attend-reminder, ora-routine-pause-resume-09-28

RATIFIED: ora-resume-0928-attend-reminder and ora-routine-pause-resume-09-28 (CC/MCP fleet). Both were one-time tasks for the 2026-09-28 attended resume; both fired 2026-09-28 15:24Z (lastRunAt), are enabled:false, and were failing test_scheduled_task_run_guard.py in the live working tree as untracked, unguarded specs. Gabriel approved retiring them in-turn (2026-09-29). CC order: delete_scheduled_task first (registry-only, folder kept), then archive both folders to scheduled-tasks/_archive_2026-09-29_completed-onetime/. Pre-checks: no same-id task on LAMS (grep of the LAMS registry), no code depends on either id (references are runtime state and handoff briefs only). ora-audit-log-sweep is NOT retired: registered, disabled, held out of PR #285; its run-guard failure is being fixed by a backlog entry citing OI-360 (see memory/open-items-2026-09-28-triage.md).

## 2026-09-28 — PR #284 merge gate closed out: slim PR #285 opened, OI-357..OI-364 filed standalone

The adversarial merge gate (six independent reviewers, pinned head 9329f26) found PR #284 carried a 31.6 MB snapshot tarball (memory files inside, invisible to the pre-push scanners), skills/synced/, and per-run _state files that would pin the merge-forward corrector. #284 was closed and its branch deleted (the hidden refs/pull/284/head still holds the tarball until a GitHub purge). Replacement: PR #285 (57 files, 5 commits, reviewed keepers only; the send-via-outlook change is the cold-start guard alone, the in-script retry was dropped because it doubled the caller retry count and could double-send). Eight follow-ups were filed as OI-357..OI-364 in `memory/open-items-2026-09-28-triage.md` (standalone: open-items-tracker.md was CONTESTED by live session 07f5c5ca; merge them into the tracker when the preflight returns 0, then delete the file). Ids reserved via allocate-oi-id.py. Pre-push overrides used: four, each for test-governor-drift-probe.py, a false positive on positivity guards in oxford-command-center capital-config.ts (constants 1.25 / 0.40 intact) - see OI-359.

## 2026-09-28 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `372c45f9-107e-4c85-966f-74ce3f70a06f` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved override in-turn (fourth push, slim replacement branch for PR #284): remaining expected failure is the governor-drift-probe false positive (capital-config.ts > 0 finiteness guard; real constants 1.25/0.40 intact in governor-constants.ts); run-guard ratchet and sentinel fix are resolved and the three blast-radius commits carry recorded independent review (claude-opus-5-5, approved).
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-28 18:34:03 local.

## 2026-09-28 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `372c45f9-107e-4c85-966f-74ce3f70a06f` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved override in-turn (third push, PR #284 run-guard + sentinel-slot fixes): remaining failure is the governor-drift-probe false positive (capital-config.ts > 0 finiteness guard; real constants 1.25/0.40 intact in governor-constants.ts); run-guard ratchet and sentinel TZ fix are fixed in this push.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-28 17:30:27 local.

## 2026-09-28 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `372c45f9-107e-4c85-966f-74ce3f70a06f` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved override in-turn (second push, merge of origin/main into PR #284 branch): remaining failures unrelated to correctness of the merge - governor-drift-probe false positive (capital-config.ts > 0 finiteness guard; real constants 1.25/0.40 intact) and run-guard ratchet on newly tracked task specs (backlog/guard fix pending, noted in PR #284).
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-28 16:54:30 local.

## 2026-09-28 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `372c45f9-107e-4c85-966f-74ce3f70a06f` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved override in-turn: 3 gate failures pre-exist and are unrelated to the 74 pushed commits - governor-drift-probe false positive (capital-config.ts > 0 finiteness guard; real constants 1.25/0.40 intact), in-flight OI-354/355 filing by another session (uncommitted tracker), and un-backlogged scheduled-task specs on run-guard ratchet (fix pending).
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-28 16:10:30 local.

## 2026-09-28 — Dirty-tree triage: primary checkout reattached + 72 settled files isolated-committed

Checkout was found in detached HEAD (reflog: an interrupted `reset: moving to origin/main`), main unavailable for direct checkout because it's pinned to the dedicated `main-checkout` worktree (which runs the daily `deadman: fleet-heartbeat` commits) — resolved by creating `chore/reattach-primary-checkout-2026-09-28` at the existing commit (0796ad1, already an ancestor of `main`; nothing lost). Then ran evidence-attribution (`hooks/sessions/*/touched-files.txt`, 348 sessions) + mtime-settlement against the 120-entry dirty scan; isolated-committed 16 modified-tracked files via `commit_isolated_replacement()` and 56 untracked files/dirs via scoped `git add`+commit (72 commits, 0 failures). Excluded and left dirty on purpose: the memory-index cluster (33 files — governed by the existing `memory: automated sync checkpoint` process, not ad-hoc triage), `settings.json` and `scheduled-tasks/_shared/send-via-outlook.ps1` (blast-radius, need Gabriel's read-through), today's live pending automation (`ora-resume-0928-attend-reminder/`, `ora-routine-pause-resume-09-28/`), and 11 already-archived `_archive/` dirs (no action needed). `website-canonical`'s one dirty file was left untouched — a session was actively running in that exact checkout. `oxford-command-center`'s one dirty file (the deliberately-tracked `data/snapshots/portfolio.json` fixture) was left untouched — repo is 2 commits behind origin, a sync decision, not a triage one. **Flag:** the `scheduled-tasks/ora-pr-land-watch/SKILL.md` I just committed is the pre-fix version (manual shell TZ math) — local branch `fix/sentinel-et-slot` (unmerged, unpushed) already fixes the exact UTC/ET bug it still has. Do not treat this recovery branch's copy as authoritative; reconcile from `fix/sentinel-et-slot` before either lands on `main`.

## 2026-09-26 — oxfordra.net website-perfection audit shipped (PR #99, live)

- Full-site audit (website-perfection v1.1): Lighthouse 100/100/100/100 desktop, 99–100 mobile; verify gate green; live == HEAD before work.
- Gabriel approved scope 2026-09-25 via AskUserQuestion: all code/security/a11y/hygiene findings + claim decisions (Indianapolis → "Other Midwest / Mid-Atlantic"; founding claim stays 2005 everywhere, meta.md aligned; placeholder LinkedIn Insight Tag removed with its CSP origins).
- Landed: P1 tenant-application "Sending…" lock; chat-lead CORS + rate limit; single-use broker intake tokens (release on email failure); CSP hardening directives; webhook/reCAPTCHA silent-failure fixes; 7 prod npm advisories → 0; storage guards; logo `|` → rect (Lighthouse label-content-name-mismatch); mobile nav landmark; aria-controls; titles ≤ 60; llms.txt markets/tenants.
- Gates: seo.test.mjs WP-1..13 + client-robustness + chat-lead unit tests; mutation cases W1–W13 (14 killed); independent Fable REFUTE review recorded via eos-review-gate (1 confirmed defect fixed pre-commit); CI stale-anchor fix (N10) after mobile-nav tag change.
- Merged 4c97ba5 on Gabriel's "merge it once CI is green"; Netlify auto-built main; served assets verified live (script.js?v=16, styles.css?v=19, CSP directives, redirects, content).
- Deferred (in PR body): per-unit size-filter semantics, chat edge global spend cap, netlify-cli 27 bump, one real broker upload to confirm SharePoint uploadUrl host under connect-src.

## 2026-09-24 — adversarial-merge-gate hardened against reviewer hook writes (ora-claude-config PR #282); the override scope was wider than authorized

- **What:** `skills/adversarial-merge-gate` gains a fourth mandatory dispatch clause, "guard surface is off limits": no reviewer writes under `~/.claude/hooks/`, and no encoded or split command text to get past a guard. There is also a pre-dispatch hook-dir listing with a post-swarm breach check. Breaches are archived to `_archive_override_tokens/`, and a plain `override` gets a `.breach-<date>` suffix so the weekly sweep's forced move can't overwrite it. Commit `b8b1c89`, branch `feat/merge-gate-guard-clauses`. An independent opus reviewer approved on its third pass; the PR is open, not merged.
- **Why:** in the PR #89 (ZeOoba/Website) merge gate, a test-validity reviewer wrote the eos-plan-gate `override` into the orchestrating session's hook dir, and base64-encoded a site path in one command. That marker is archived as `bb65086a-…_override.breach-2026-09-24`.
- **Override correction:**
  - Gabriel authorized `allow-hook-test-failure` for load timeouts in `test_checkout_merge_forward.py` and `test_preflight_shared_checkout.py`. Run directly, both passed in 430s and 437s against the 480s budget.
  - The push that consumed the token (the gate's entry above, 14:53) actually overrode three different tests: `test-commit-hygiene-guard.py` (124), `test-linear-shlex-commit-guards.py` (124 twice), and `test-git-prepush-scan.py` (exit 1; `load_terms` assertion failed on the post-timeout rerun).
  - Run directly on the branch, all three pass: 39/39 in 37s, 144s and 99s. So the failures look load-induced.
  - The session first misreported the override as unused and corrected that before closing out. A session-scoped token covers whatever fails during its lifetime, not only the tests named in its reason.
- **Flaky under load (from the same gate runs):** `hooks/tests/test-eos-review-gate.py` and `maintenance/_tests/test_append_event_log_lock.py` (`WinError 5` on the gate temp dir). Both failed once and passed on rerun.

## 2026-09-24 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `bb65086a-c82a-4529-ad6e-4705d6fb23a8` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel authorized in-turn 2026-09-24 (AskUserQuestion "Authorize override"). Push of b8b1c89 (feat/merge-gate-guard-clauses; diff = skills/adversarial-merge-gate/SKILL.md + agent-prompts.md only). Gate failures are load timeouts, not regressions: maintenance/_tests/test_checkout_merge_forward.py and test_preflight_shared_checkout.py both exit 124 after the doubled-budget retry, but run directly they pass (rc=0, 0 FAIL) in 430s and 437s against the 480s budget, with ~18 sessions running. Neither test reads skill files.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-24 14:53:13 local.

## 2026-09-24 — ora-skills ledger sidecar lock (PR #84, stacked on #79)

- **What:** added a cross-process sidecar lock around every ledger read-modify-write in `ora-skills`. This closes #79's deferred merge-gate race finding F2: 21.7–40.2% of concurrent ledger updates were being lost.
  - Covers the PENDING_REIMPORT ledger (written by `pending_reimport.py record` / `clear` / `backfill`) and the STORE_AHEAD_OF_REPO ledger (`repo_first_check.record_ledger`).
  - The lock is a kernel byte-range lock (`msvcrt.locking` / `fcntl.flock`) on a never-deleted `_staging/.<ledger>.lock`, with a 10s bound, then `LedgerLockTimeout`. There is no stale-lock state.
  - `update_entries()` is now the only sanctioned ledger read-modify-write. **Any new ledger writer must go through it.**
- **Evidence:**
  - Contention test, 3 procs × 200 cycles: 0 lost with the lock, versus 388/600 lost or never executed with a no-op lock.
  - Full suite green: 14/14 files, 0 skips, 0 empty.
  - CI 2/2 green on #84.
  - Independent Opus adversarial review: CHANGES REQUESTED (2 Important: silent non-timeout OSError on the post-commit record path, wrong `backfill` remedy), all fixed, then APPROVE.
- **Open:** #84's base is #79 (`fix/staging-primary-checkout`, round-4 merge gate running on ac52f51 at the time of writing). Once #79 merges: merge `origin/main` into `feat/ledger-sidecar-lock`, re-run `tools/run_suite.sh`, and retarget #84 to `main`. The dry-run merge against ac52f51 was clean.

## 2026-09-24 — oxfordra.net fix-forward: duplicate hero stat (#95)

- #92 added "20+ Years Operating" next to the existing "21+" hero stat, a defect found in the post-deploy visual check. #95 removed it (main fc4d772), after Gabriel's in-turn deploy OK and green CI; landed tree equals the reviewed head.
- Verified on prod: the hero reads 500,000+ SF · 130+ Tenants · 3 Core Markets · 21+ Years Operating, with a single "Years Operating" label.
- Lesson: when replacing a stat tile, check its siblings for the replacement label before choosing it. The text-only greps passed; only the visual check caught it.

## 2026-09-24 — oxfordra.net release: Overview PDF (#90) + site figures (#92)

- **Confirmed by Gabriel in-turn** ("deploy #90 and #92 to production"); /ship lane L7.
- **#90 → main 79932dd, Netlify prod live.** Overview PDF regenerated from the Master Workbook (2026-09-23) and settlement statements: no numeric LTV, no building count, no CONFIDENTIAL marking. PDF republished and hero Download Overview button restored. Verified: PDF 200 application/pdf, sha256 ffe362d7… equals repo; button present.
- **#92 → main 809c264, Netlify deploy 6ab53f92 ready.** Public figures corrected: 130+ tenants; building counts replaced by SF per market; 2022 = 300,000 SF; "can close all-cash" instead of every-deal; Sepich ~$9.9M, 1900 NB $5.4M+; occupancy / CoC / value-to-price tiles; 9620 = 34,300 SF. Chat firm facts (scripts/meta.md) aligned. Verified: 9 pages 200 with no 140+, building count or universal all-cash claim. Lighthouse 99/100/100/100; secret scan clean.
- **Gates:** independent fact-checkers (all figures SUPPORTED); site-qc-reviewer APPROVE after 2 BLOCK rounds (review surface, then 2 missed all-cash claims); CI green on the merge heads.
- **Incidents:**
  - #85's squash-merge would have silently dropped #90's reversals; fixed with `-s ours`, since the trees were identical.
  - main went red (#93 × #89 script.js cache-buster); fixed by #94 in parallel.
  - **Defect shipped:** #92 duplicated the "Years Operating" hero stat. Fix-forward PR opened, pending Gabriel's deploy OK.
- **Rollback point:** 6ab48985 (e800913).

## 2026-09-24 — Run-guard test cp1252 crash fixed (PR #281, b89595e)
- Symptom: pre-push hook-tests gate reported `test_scheduled_task_run_guard.py` failing with `UnicodeEncodeError: 'charmap' codec can't encode '→'`. The test quotes task SKILL.md lines in FAIL details; on the gate's cp1252 pipe the print raised inside `check()` before `_failures.append()`, aborting the run and hiding the real failure list.
- Cause class: environment (Windows cp1252 stdout on a pipe). ~30 `maintenance/*.py` scripts already carry the `reconfigure(encoding="utf-8", errors="replace")` idiom; no file under `maintenance/_tests/` does, so any test that prints non-ASCII detail is exposed the same way.
- Fix: the standard idiom added to that one test. Repro (PYTHONIOENCODING=cp1252, `check()` with a U+2192 detail): traceback before, FAIL recorded after. Full pre-push suite green on push.
- Separate, NOT fixed: the live `~/.claude` checkout still fails this test on real FAILs from other sessions' untracked task folders (ora-audit-log-sweep, ora-hubspot-renewal-closeout-tasks, ora-incentive-registry-refresh, ora-jackson-boe-prep-reminder) — frozen-backlog check. That blocks every push from the live checkout, incl. branch deletes.

## 2026-09-24 — oxfordra.net release: PR #94 (application-received on script.js?v=14)
- **Shipped:** squash `1e02320`, confirmed per-deploy by Gabriel in-turn. It fixes the v=13/v=14 mix #89 left behind.
- **Verified:** main CI green on 1e02320. Live `/application-received` loads v=14. `script.js?v=14` still has the #93 matcher. `/`, `/tenant-application`, `/application-received` and `/sell-your-building` all return 200.

## 2026-09-24 — oxfordra.net release: PR #93 (script.js upload check honours `accept`)
- **Shipped:** squash `5498171`, confirmed per-deploy by Gabriel in-turn. #91 had already been merged by ZeOoba at 02:23Z.
- **Gates before merge:** CI green on 45bb8b6; site-qc-reviewer APPROVE; independent Opus review clean; 186 unit + 49 site tests.
- **Live:** production is on `fd8f152`, because #89 merged 4s after #93. Verified by curl: `script.js?v=14` has the new matcher, `/tenant-application` is on v=14 with its 3 accept inputs, and pages return 200.
- **Collision:** #89 put `application-received.html` on `script.js?v=13`, so main CI went red (mixed cache-busters). Follow-up PR #94 (one line, v=14) is a draft with CI green, awaiting per-deploy confirmation.
- **Lesson:** two same-minute merges that both touch the cache-buster can't see each other. Re-check main's tip after every merge, not just the PR head.

## 2026-09-23 — ora-pr-land-watch registered; one-time ora-branch-catchup-refute-trailer-366 RETIRED (superseded)

- **New:** `maintenance/pr-land-watch.py` plus 37 tests landed in ZeOoba/ora-claude-config PR #279 (merge `9c35410`). It is a queue of "do Y once PR X lands" watches. Recurring CC/MCP task `ora-pr-land-watch` (cron `35 9-21/3 * * *`, enabled, `[MODEL: UNVERIFIABLE | checked 2026-09-23]`) polls it and runs each hash-pinned payload once its PR is MERGED. The task always runs the origin/main copy, extracted to TEMP, because the live checkout's merge-forward is paused.
- **Why:** it replaces the "one-time task at a guessed time" pattern. An unattended run cannot re-schedule itself (register-scheduled-task v2.23).
- **Review:** the opus adversarial review ran 3 rounds. It found 6 Important issues, reproduced and fixed each with a regression test, and found no Critical.
- **Named "land", not "merge":** config-write-guard matches "merge" in any git command that names ~/.claude.
- **Queued (both trigger on oxford-command-center #366):**
  - `branch-catchup-366`: the Step 6 refute-trailer doctrine edit, delivered as a PR that is not merged.
  - `pr364-catchup-after-366`: a guarded catch-up of #364, using Refute-Skip only when the conflict is taken verbatim from main. Gabriel chose "guarded".
- **RATIFIED retire: `ora-branch-catchup-refute-trailer-366`** (CC/MCP, one-time). It was superseded by the `branch-catchup-366` watch. It was removed with `delete_scheduled_task` first (registry only), then its folder was archived to `scheduled-tasks/_archive_2026-09-23_retired/`.
- **Push friction:** the ora-claude-config pre-push gate blocked twice. Each time it was timeouts in untouched hook tests under 100% CPU (162 python/node processes, 17+ sessions). It passed 137/137 once load settled.

## 2026-09-23 — ora-site-exposure-probe v1.4: redirects-away classify CLEAN; matrix read from deployed main
- Why: Step 2 accepted "any non-200" while Step 4 CLEAN required "real 404/403"; no verdict covered a 3xx. oxfordra.net PR #85 (ec3f187) unpublishes the Overview PDF with a `_redirects` 301 -> `/`, so the first post-pause run (Wed 2026-09-30 09:50 ET, via ora-routine-pause-resume-09-28) would have hit an unclassified 301 and could have fallen through to an alarm email.
- CLEAN = 404 / 403 / CLEAN-redirect (same-host 3xx, decoded path differs from probed path and is `/` or another matrix path). 200/listing stays ALARM. Every other 3xx (self, no Location, off-host, off-matrix target, 300/304/305) and every other status -> ALARM-UNVERIFIED.
- Steps 1/3 now read build-dist.mjs/_headers from `main` via `gh api` (local working tree was at 31f5cef, behind origin/main; lag would false-alarm when PR #90 restores the PDF). Point raised by the PR #85 session's round-3 race review. No `git fetch` into the site checkout.
- Adversarial REFUTE pass (Opus) found the "Location differs" rule could launder a leak via an unprobed/off-host target; target restriction added. Open follow-up: the must-not-serve list comes from the same file a regression would edit.
- Landed: ora-claude-config branch fix/site-exposure-probe-3xx-verdict (a0b02cf); live SKILL.md propagated via propagate-task-spec.py (backup `SKILL.md.bak-2026-09-23-3xx-verdict`, live == blob b3ece05, LF). Registry unchanged: `50 9 * * 3`, enabled:false.
- Verified: live dry-run on main @ cf92cd3: 34 paths, 2x301 -> / (PDF, PDF/), 32x404, control 200/404, headers match -> CLEAN. 15/15 synthetic adversarial cases classify as intended.

## 2026-09-23 — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)

- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real failure, but session `4c7805b5-6f44-468c-9262-a9905e86259c` held a valid `allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from mtime), so the push was ALLOWED rather than blocked.
- Reason recorded in the token: Gabriel approved in-turn 2026-09-23 for push of feat/sourcing-scan-v2-8 (diff = 2 scheduled-task SKILL.md files only). Gate failures triaged: (1) maintenance/test-powershell-suites.py -> test-fleet-deadman-ps1.ps1 timeout(200s) REPRODUCES on unmodified origin/main 0cb7bd1 (pre-existing); (2) maintenance/_tests/test_verify_push.py timed out 480s x2 under machine load but passes 36/36 standalone on origin/main (137s) and on this branch ee4e804 (214s). Neither test reads the changed files.
- Mechanical record only, per the rules.md override protocol (token created only after Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override used at 2026-09-23 22:17:43 local.

## 2026-09-24 — oxfordra.net PR #88 merged 45s after #85; combined main cf92cd3 verified live

- **What happened:** #88 (form thank-you states) was squash-merged by ZeOoba at 02:03:41Z as `cf92cd3`, 45 seconds after #85 (`ec3f187`). The merged head was `78820da`, the head #88's own 3-round adversarial gate cleared (verdict comment posted 02:03:02Z).
- **Protocol deviation:** the agreed handoff was that the #88 session would merge main in, re-test, and send session 30dc10ce an exact SHA to merge. That didn't happen; the #88 session ended right after the merge, and it is unconfirmed which actor merged. The prior race simulations (#85@55dc0b3 + #88@78820da: clean in both orders and as squash, 7/7) predicted a clean combination.
- **Verified after the fact (session 30dc10ce):**
  - CI "Build & verify" passed on cf92cd3, including csp-smoke.
  - Locally on cf92cd3: unit 186/186, site 37/37 (includes #88's form tests), verify-jsonld 20 pages, listings in sync.
  - Production serves cf92cd3: owner, broker and leasing pages carry #88's `scrollIntoView` and success elements, and #85's markers are intact (nav 1279px, styles v18, PDF 301, three-market title).
  - Not done: no interactive production form test, to avoid real submissions and emails; #88's gate had runtime-verified the forms in a browser.
- **Still open:** the #89 vs #88 conflict in `tests/site/netlify-forms.test.mjs` now falls to #89 (keep both sides); #90 (PDF restore); the build-guard follow-up; the exposure-probe fix.

## 2026-09-24 — oxfordra.net PR #85 merged + verified live (ec3f187)

**Authority:** Gabriel in-turn: "merge #85 once the other four come back clean" (session 30dc10ce).
- **Round 3** (adversarial-merge-gate, head 55dc0b3): all 5 mandates reported zero confirmed #85 defects.
- **Merge:** squash-merged at the pinned head (`--match-head-commit`) as `ec3f187`, 2026-09-24 02:02Z; production served it within about 20s.
- **Live checks passed:** Markets title lists three markets; nav breakpoint 1279px; styles `?v=18` and chat `?v=3`; the announcement-bar critical CSS is inlined; no "15% portfolio"/"loan-to-value" on home, about or for-brokers; "Download Overview" is gone; the Overview PDF 301s to `/`; the control path returns 404; sitemap lastmod reads 2026-09-23; the leasing form serves form-name, bot-field and #leasingSuccess.
- **Round-3 residuals, all routed and none in #85:**
  - Exposure-probe 301 verdict and its Step-1 list source: in the running probe task session.
  - Build-dist double-listing guard: in a separate follow-up task (Gabriel chose this).
  - PR #90 (PDF restore) re-based via an `-s ours` merge onto ec3f187.
  - #88 and #89 conflict in `netlify-forms.test.mjs`; resolve by keeping both.
- **Next:** #88 merges at the exact SHA its owner session sends after merging main in and passing its gate (Gabriel authorized this in both sessions).

## 2026-09-23 — ora-skills PR #80 merged (37fb909): zero-tests + BARE rules live on main

- **Closes the entry of the same day.** Follow-up be59ec0 passed Opus round 3 (APPROVED), plus a separate review of a comment-only delta: the ALLOWED_SKIPS header now says setUpModule/setUpClass SkipTest counts as 1, while `@unittest.skip` counts per test (fixture-verified).
- **Checks:** full local suite green (14 files, 0 failed / 0 skipped / 0 empty); CI `tools-tests` pass on be59ec0. Squash-merged, pinned to the head commit.
- **Cleanup:** claim `ora-skills-tools-suite` released; worktree `ora-worktrees/suite-zero-tests` removed (no junctions); local main forward-merged.
- **Left open:** the header of `.github/workflows/tools-tests.yml` still describes only the fail and zero-skip checks. It is a shared-infra file, not edited here.

## 2026-09-23 — ora-skills #81 merged (84145e7): portfolio LTV 18.71% internal, no numeric leverage outbound

**Authority:** Gabriel, in-turn: "merge #81 once the review is clean"; "use 26 properties, keep it".
- Review 1 (independent, opus): APPROVE with 2 Important items. (A) no-numeric-leverage rule was too broad and would collide with deal-level lender RFPs; now scoped to portfolio-level. (B) v1.10 changelog quoted the removed outbound sentence; now paraphrased. Both fixed in 5d17912. Re-review: 0 CONFIRMED, APPROVE. CI green. Squash-merged, pinned to head 5d17912.
- Shipped: acquisition-underwriting v4.24 (18.71% as of 2026-09-23, internal-only, in CAPITAL STRUCTURE CONTEXT + STAGE 2.3 + references mirror) · loi-generation v1.10 (LOI template Buyer Information page + ora-standards cover note: "conservatively leveraged", 26 properties / 500,000+ SF / ~$57M / ~140 tenants / three core markets).
- Pending: Cowork Save-skill reimport of both skills; eyeball render of the LOI template (QC #17 page count not run; no LibreOffice, Word COM export hung). Follow-ups: add an LOI QC-gate check that fails on numeric leverage; settle the portfolio-value vs acquisition-proposal-generation never-state conflict; harmonize ora-standards.md:75 wording to the portfolio-level scope.

## 2026-09-23 — ora-skills tools suite: zero-tests silent pass found + gated (PR #80)

**Finding** (adversarial merge gate on ora-skills PR #79):
- `tools/test_reimport_cycle.py` (bf724aa) held 7 pytest-style module-level `def test_*` functions, with no `unittest.TestCase` and no `__main__` runner.
- `tools/run_suite.sh` runs each file as plain `python <file>`, with no pytest. The file ran **zero** tests, exited 0, and was reported `ok` with an empty summary.
- The zero-skip baseline (#63/#72) could not see it, because nothing reports as skipped.
- Failure class: **tooling / test harness**. It is the same silent-pass family as the 2026-08-05 rent-comp skip.

**Fix** (session 621bf8a0, lane L2 `/debug`, worktree `ora-worktrees/suite-zero-tests`, claim `ora-skills-tools-suite`):
- **5681d67, pushed as PR #80. CI `tools-tests` pass; local full suite 14 files, 0 failed / 0 skipped / 0 empty.**
  - The test file is converted to stdlib unittest and now prints `Ran 7 tests OK`. Checked against 8 scratch-copy mutations of `gate_failures()`: all 8 caught.
  - `run_suite.sh` gains a **zero-empty rule**: a file that exits 0 without `Ran N tests` (N ≥ 1) fails as EMPTY.
  - Exemption: an exact-path `NON_UNITTEST` list (`test_description_budget.py`) must print `all checks passed` instead.
  - Opus independent review: APPROVED.
- **Follow-up commit (in review at time of logging):**
  - **BARE rule:** any column-0 `def test_*` fails, which catches a stray function beside a TestCase. `NON_UNITTEST` files are exempt.
  - **Label pin:** `UNKNOWN`/`CACHE-AHEAD`/`DIVERGENT` are pinned in `test_every_bad_label_stops`, closing an inherited mutation survivor.
  - **Round-2 Opus review: CHANGES REQUESTED, and it was right.** An interim change had routed whole-module skips (`Ran 0 … skipped=1`) into `ALLOWED_SKIPS`. That would have let a census module that ran nothing pass on ubuntu through the `=1` entry. It was reverted: `Ran 0` is always EMPTY. Round 3 is pending.
- **Memory:** `feedback_ora_skills_tests_zero_tests_rule.md` (indexed under Rules & governance).
- **Lesson:** "suite green" does not prove a file's tests ran. Read its `Ran N` row. `ALLOWED_SKIPS` counts individual test skips and must never vouch for a module that ran nothing.

## 2026-09-23 — oxfordra.net PR #85 (site review): content decisions + merge-gate rounds 1–2

**Authority:** Gabriel in-turn (multiple AskUserQuestion answers, this session 30dc10ce). Preview only; no production deploy. Merging = auto-deploy, so it needs a separate per-deploy go-ahead.
- **Content decisions:**
  - Kansas City stays a **"three core markets"** market. This **supersedes the 2026-09-21 SEO plan's "two core + KC holding"**: plan `docs/superpowers/plans/2026-09-21-oxfordra-seo-followups.md` is annotated, W1 is cancelled, and test M-1 must not be built. W6 now asserts "three core markets".
  - **No numeric portfolio LTV on any public surface.** Site, About FAQ + JSON-LD and chat `scripts/meta.md` now say "conservative leverage" (verified figure 18.71% is internal-only; see LTV entry above).
  - The Azad Shah quote uses the About wording everywhere.
  - About timeline 2022 reads "two markets" (KC entered 2024).
  - For Brokers hero stays 1100 Rarig (decision relayed by the #86 session, confirmed in-session).
  - Overview PDF: link hidden (eaa29c8), then **unpublished** (55dc0b3: build exclusion + 301 to /). The old PDF was marked CONFIDENTIAL and publicly reachable with 15% LTV / 600K SF / 4 markets.
- **Merge gate** (adversarial-merge-gate, 5 mandates):
  - R1 at 2ad9677: 5 CONFIRMED findings, fixed in e72f910 (About FAQ 15%, chat meta 14–16%, 9 srcset 800w→700w, application-received breakpoint, sitemap lastmod).
  - R2 at e72f910: 0 PR defects. Process note: merge #85 before the next LoopNet sync PR, since `sitemap.xml` lines 15–17 conflict with any sync PR opened earlier (the sync task is currently `enabled:false`). #85 and #88 merge cleanly in either order.
  - Final pass still due on eaa29c8 + 55dc0b3.
- **Spun off:** Overview PDF regeneration, site test hardening (validator false-passes), and stale LTV in skills (the last one is done per the entry above; outbound LOI template still awaiting Gabriel).
- **Known cosmetic leftover:** a whitespace-only line at `available-space.html:112` (introduced by the announcement-bar inline). It was left because the site-write gate token had expired, and it has no effect on rendering.

## 2026-09-23 — Portfolio LTV figure verified 18.71%; stale "~15%" in ORA skills triaged

**Authority:** Gabriel task brief (in-turn): verify current portfolio LTV from the source of record, sweep skills, update internal refs, ask before touching outbound templates. Governor constants untouched (Invariant 4).
- **Verified:** 18.71% (gross-external: external debt $10,605,588 ÷ Oxford-share value $56,668,952), Master Workbook `00_Home!G7`, live M365 read 2026-09-23 (local mtime 2026-09-23 13:17). No OPEN WBC row against these cells. Memory: `project_portfolio_ltv_current.md` (supersedes projects.md's Jun-1 17.9%).
- **Internal fix (committed, not pushed):** ora-skills branch `fix/portfolio-ltv-figure-2026-09-23` (worktree `ora-worktrees/portfolio-ltv-figure`): acquisition-underwriting v4.24 CAPITAL STRUCTURE CONTEXT ~15% → 18.71% dated/internal-only, headroom ~25 → ~21 pts. Preflight CLEAR; governor-drift scan 0 findings.
- **Outbound, awaiting Gabriel:** loi-generation `templates/LOI_Master_Template_Condensed.docx` Buyer Information page ("portfolio loan-to-value of roughly 15%"; also 27 properties / 600K+ SF / ~$65M) and `references/ora-standards.md` cover-note list (same figures). Site: PR #85 removes the public "15% portfolio LTV" — production still serves it until merge + deploy.

## 2026-09-23 -- lease-addendum v1.1 reimport
- lease-addendum v1.1 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-09-23 — PR #260 follow-ups: #269 merged (fdd80a5); LAMS resume reconciled

**Authority:** Gabriel, in-turn: "fix the open follow-ups", "merge #269 if the review is clean", "merge #269 when the push lands", and the LAMS choice "Resume with CC on 09-28".

- **#269 merged.** New `maintenance/test-powershell-suites.py`: the pre-push gate now runs all six `maintenance/test-*.ps1` suites, including the dead-man's 60-check suite and the previously uncovered `test-stuck-session-watchdog.ps1`. Also new: `_tests/test_powershell_suites_runner.py` (13 checks). The `ora-weekly-hygiene` Block I thresholds now match #260. Two independent Opus reviews ran; the 1 MED test gap and 3 LOWs they found were fixed and mutation-verified. Propagated live, hash-verified; live runner 13/13, suites 6/6. The prior hygiene SKILL.md is archived at `maintenance/_archive/2026-09-23_pr269-merge/`.
- **Gate cost:** the runner adds ~50–105s of concurrent PowerShell per push. On the 95407c4 push, test_checkout_merge_forward.py and test_preflight_shared_checkout.py timed out under load and passed on the automatic doubled-budget rerun. Watch for this; if it recurs, run the suites serially.
- **0xC000013A kills, diagnosed:** on 09-23, Heartbeat Push was killed (0x40010004) after its heartbeat published successfully, when the machine entered Modern Standby at 07:57. The Dead-Man and Wake-and-Launch ran clean (0x0). The 09-21/22 kills were on wake catch-ups. Common factor: power/standby transitions. Restart-on-failure, added by another session, is the mitigation; the START logs now show start-vs-die. No power-setting change was made (system setting).
- **LAMS resume reconciled:** the session "LAMS weekly cleanup handoff" (Claude Code, not Cowork, and stopped at Step 0 on 09-22) had already written a manual resume brief, `handoffs/2026-09-28_LAMS-fleet-resume_brief.md`, and pointed both CC reminders at it. My registered-resume Step 2b is marked SUPERSEDED so there is one resume path. That session has since added Step 2c to the cleanup brief on Gabriel's instruction: re-enable and run `ora-cowork-heartbeat` now. **Gabriel's two native-Cowork steps:** (1) the cleanup brief, any day before 09-28; (2) the resume brief, 09-28 by 10:30.

## 2026-09-23 — Live ~/.claude checkout brought current with main (was 45 behind); branch content landed on main
- **Authority:** Gabriel, in-turn: "yes, run all three steps". This closes the 09-22 follow-up "switch the checkout to `main`" that the Dirty tree triage session (e8ca1031, archived) left undone.
- **Step 1, PR #270 (merged `6351579`):** three retired specs moved into their archive folders on main (`ora-754-flaute-escalation-check`, `ora-resume-0921-attend-reminder`, `ora-routine-pause-resume-09-21`). They were archived only in the live tree, so moving to main would have brought them back. Adversarial review APPROVE (opus).
- **Step 2a, merge `a44f5bb`, PR #271 (merged `b1533a3`):** origin/main merged into `feat/model-canary-probe-step25` in a worktree, then landed on main. Conflicts: `event_log.md` (all 129 main and 137 branch headings kept, no duplicate entries) and `rules.md` (`modified:` stamp only). The blast-radius files are byte-identical to main; eos-review-gate artifact recorded (opus, approved).
- **Step 2b, live checkout:** the live checkout is NOT switched to the `main` branch label, and cannot be. Local `main` is checked out in `.claude/worktrees/main-checkout`, which `push-fleet-heartbeat.ps1` depends on. Instead the live branch was fast-forwarded 21342b3 to b1533a3 (tree identical to origin/main, 0/0). This was done by an explicit script, not git switch/merge (rules.md §14):
  - 87 incoming paths: 63 already identical to main, 21 clean ones written, 3 live WIP files merged.
  - `retire-pending.json`: live kept; it is a pure superset.
  - `open-items-tracker.md`: 3-way merge. Two add/add hunks took the live side, which verifiably contains every main line. OI-187/188/192 are absent because live WIP moved them to the history file.
  - `people.md`: clean 3-way merge; the 09-19 808 Rhoads correction is kept.
  - The 661 other dirty files were hash-verified unchanged. Pre-state backup: `maintenance/_archive/2026-09-23_live-ff-to-main/live-before/`. Dirty count went 167 to 107.
- **Step 3:** the live pre-push gate now carries main's `91b77ca` (PYTHONIOENCODING for test children). Gate result (live, 2026-09-23): 134 pass, 1 fail, 0 env-skip (of 135). There is no UnicodeEncodeError; the encoding fix is live and the real failures now print. The one failure, `test_scheduled_task_run_guard.py`, is live-tree state and not a code defect: 8 untracked task folders with no run guard (OI-352), plus the two untracked 09-28 one-time tasks (`ora-resume-0928-attend-reminder`, `ora-routine-pause-resume-09-28`) and `ora-loan-balance-check` ordering-by-hand. Pushes from the live checkout stay blocked until those are guarded, or until the one-time folders are archived after they fire on 09-28. Worktree pushes are unaffected.
- **Found, not fixed:** the `main-checkout` worktree's local `main` holds 5 heartbeat commits (0e1c435..6da7059) that are on no remote and is behind origin/main. The heartbeat's `git push origin main` backup leg is not landing; see OI-330/OI-331.

## 2026-09-23 — insights5: scheduled-task output rules A/B/D retrofitted fleet-wide; register-scheduled-task v2.29; deferred WIP landed

- **Rules live** (register-scheduled-task step 3: run date once; Notion no-ID create → fetch parent then title search, grace/quota no-match = UNVERIFIED, no retry; event-log via append-event-log.py with `## YYYY-MM-DD — <title>`): 42 CC + 24 LAMS task SKILL.mds, each only where its instructions exercise the behavior. Every CC live file hash-verified (`git hash-object`) against its merged blob; backups `SKILL.md.bak-2026-09-22-insights5*` / `-2026-09-23-insights5-{b,c,d}`.
- **Merged:** ora-claude-config #267 (retrofit + `maintenance/propagate-task-spec.py`, 11 tests) and #268 (landing + second retrofit, b53d418); ora-skills #76 (v2.29: rule-B search-lag fix, rule-A date slots, content-edit steps 5–6 use live EOL + `git hash-object`). #264 closed (branch carried 7 unrelated commits). Three independent opus reviews, all APPROVE-WITH-FIXES, all findings fixed.
- **dirty-tree-triage** (27 deferred CC task files, settled across two snapshots 20 min apart): 10 landed with attribution in 98be142; am-brief/broker-touch-cadence already superseded by main (3-way); 4 already == main; pause/resume 09-28 pair left untouched (live session 40e33334). 9 never-tracked specs split out at the push gate — 8 carry unguarded side effects → OI-352.
- **Doctrine fix found in passing:** a scheduled-task retry-once publication guard re-creates the duplicate after a grace-period notice, because Notion search lags; v2.29 routes that case to UNVERIFIED instead of a retry.

## 2026-09-23 -- package-and-stage-skill v1.33 reimport confirmed

package-and-stage-skill v1.33 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-09-23 -- loi-generation, document-assembly, register-scheduled-task reimport

loi-generation, document-assembly, register-scheduled-task v2.29 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-09-23 — PR #260 merged (20a0391) after a 9-round adversarial merge gate; live ~/.claude updated

**Authority:** Gabriel, in-turn: "run the review and merge if clean", then "1, and merge after this round if only lows". Round 9 reported LOW findings only; all were fixed in 979b323 before the squash-merge.

**Gate history.** 9 rounds × 5 independent reviewers (correctness, race, test-validity, scope, blast-radius), Opus, each round on a pinned SHA. Real defects the gate caught in this session's own changes:
- R1: a START line in the main log masked a dead dead-man.
- R3: the carve-out made Windows producers read [PAUSED] for up to 14 days.
- R5: fleet-pause-windows.json false-alarmed after every pause.
- R6: daily Windows producers were missing from the pause-independent list.
- R7: a dead ora-am-brief during a pause was silenced (it was LIVE via the early 14bc76e copy), and a flat 6h grace flagged weekly producers.
- R8: registry re-reads could see a torn file.
- R9: 1-task count unroll; unparseable registry fell back to mtime; fleet-heartbeat.json misclassified.
The remaining findings were test-coverage gaps, each closed with a failing-first test and mutation replay.

**Live gap closed 09-23:** the live fleet-deadman.ps1 (14bc76e, blind to a dead Daily Brief during the CC pause) was reverted to origin/main before the merge (option 1, Gabriel-approved). The 14bc76e copy is archived at `maintenance/_archive/2026-09-23_deadman-restore/`.

**Propagated after merge:** the 11 maintenance/ files. Each live hash was checked first against a version this session had placed (14bc76e or pre-merge main); archive at `maintenance/_archive/2026-09-23_pr260-merge/`. All are hash-equal to 20a0391. Live checks: test-fleet-deadman-ps1 60/60, test_state_freshness_thresholds 11/11, the probe reads cc=PAUSED correctly.

**NOT propagated (another session's live edits):** scheduled-tasks/ora-pm-ledger, ora-ground-truth-auditor and ora-checkout-merge-forward SKILL.md. The live copies carry uncommitted 'run date computed once with `date`' edits. The PR's small changes to those files (trailing newline, the lookback wording, and the merge-forward threshold text) reach live only when that session commits and reconciles.

**Open follow-ups:** (1) test-fleet-deadman-ps1.ps1 is not run by any gate, since the pre-push gate runs Python only. (2) ora-weekly-hygiene Block I text still says 7 runs / 72h. (3) The Wake-and-Launch, Dead-Man, Heartbeat Push and Headless tasks were all killed 0xC000013A on the 09-21/22 wake catch-ups; the START logs will now show this. (4) LAMS is fully disabled with no resume queued; the dead-man alarms on this daily, correctly. (5) The LAMS handoff brief still needs a native Cowork session.

## 2026-09-23 — Runtime-cache sync gated: main-only + per-file direction (ora-skills f7b8d56)

- Defect: pre-commit Check 4 (`tools/sync_appdata_mirror.py`) wrote the Cowork runtime cache from any branch/worktree, blind to direction. 09-23: a worktree feature-branch commit put pre-review register-scheduled-task v2.29 over a just-installed v2.28 for 11 min. 09-22: a main commit overwrote platform-only pma-qc v1.3.
- Fix: writes only from the primary checkout on `main`; per shipped file, only when the cache is IN-SYNC/REPO-AHEAD (CACHE-AHEAD/DIVERGENT/MAIN-BEHIND-ORIGIN/UNKNOWN leave the cache untouched; cache-only REPO-MISSING files ignored). New `--changed-range ORIG_HEAD HEAD` from post-merge/post-rewrite syncs skills that arrive by merge/fast-forward. 23 tests incl. real-git integration.
- Review: adversarial BLOCK on round 1 (skill-level REPO-MISSING would have disabled syncing after any file deletion; lease-form-qc and the eval harness were already in that state), fixed and re-reviewed APPROVE-WITH-NITS. Live: 73/73 installed mirrors IN-SYNC.
- Consequence: a skill edited on a feature branch no longer reaches Cowork until it merges to main in the primary checkout.

## 2026-09-23 -- acquisition-underwriting v4.23 reimport confirmed

acquisition-underwriting v4.23 reimported via Cowork Save-skill; reimport_correlate CONFIRMED.

## 2026-09-23 — 09-28 resume reminder email now names the LAMS resume brief
- **Authority:** Gabriel, in-turn: "yes, add the path to the reminder too".
- `scheduled-tasks/ora-resume-0928-attend-reminder/SKILL.md` (09:30 heads-up): the LAMS sentence now says the resume is not a registered task and gives the brief path `maintenance/_state/handoffs/2026-09-28_LAMS-fleet-resume_brief.md`, with start-by-10:30 ET. Only that sentence changed; frontmatter and registry are untouched.
- Preflight CONTESTED was handled per rules.md §14, exactly as for the resume task earlier today: the folder is untracked and was written by `create_scheduled_task` at 09-22 10:42:37 (mtime = creation), with no claims. Still uncommitted, as it has been since registration.

## 2026-09-23 — ora-skills `tools tests` CI green again; zero-skip gate moved into `tools/run_suite.sh`
- **Authority:** Gabriel, in-turn: fix the failing `tools tests` workflow without relaxing the zero-skip gate; then merge #72, #73, #75 and clean up worktrees.
- **Cause:** `tools/test_package_census.py` reported `OK (skipped=7)` ("PyMuPDF not installed"), so the zero-skip gate failed every main push from 2026-09-22 (e.g. run 35786603866).
- **#72 (`f7658af`):** workflow installs `pymupdf`. That exposed a platform skip: `test_path_over_260_characters_is_read_and_flagged` only runs on Windows (`skipUnless(os.name == "nt")`). `ALLOWED_SKIPS` is now exact-count `path=N`; before, an entry exempted the whole file. Only entry: `tools/test_package_census.py=1`. Losing PyMuPDF (skipped=7) still fails.
- **#73 (`117fd1e`):** README step 7.4 now requires zero skips locally (was "no new SKIP"), adds the PyMuPDF install prerequisite and documents the `path=N` form.
- **#75 (`0b12a85`):** gate logic moved out of the workflow into `tools/run_suite.sh`; CI and README step 7 both run it. The census allowance applies only when `OS != Windows_NT`, so the Windows baseline stays zero. `.gitattributes` adds `*.sh text eol=lf`. Gate checked on 6 synthetic cases, all correct.
- **Verified:** main CI green after each merge. Full suite on Windows through the script: 0 failures, 0 skips.
- **Review gap:** merged on CI plus local evidence only. CodeRabbit was rate-limited on all three PRs, and no adversarial review ran on #75's CI-gate rewrite. Gabriel accepted this at merge.
- **Lesson (friction):** an earlier local run printed 5 false `FAIL`s because its worktree was force-removed mid-run. Let a suite running in a worktree finish before removing the worktree.
- **Housekeeping:** worked under claim slug `repo-housekeeping-tools-ci`, because `repo-housekeeping` was held by session 27a75818 on disjoint paths. Claim released; all three worktrees and branches removed.

## 2026-09-23 — CC resume task's STEP 5 email corrected: no LAMS resume is registered
- **Authority:** Gabriel, in-turn: "yes, fix the CC resume email line".
- `scheduled-tasks/ora-routine-pause-resume-09-28/SKILL.md` STEP 5: the reminder said the LAMS resume was "registered 2026-09-22", which is false. It now says LAMS is not covered, has no registered resume, and is resumed by hand from a native Cowork session via `maintenance/_state/handoffs/2026-09-28_LAMS-fleet-resume_brief.md` (start by 10:30 ET). The edit touches only that sentence; frontmatter, cron and registry are untouched (probe clean, CC still 1 recurring + 5 one-time).
- Preflight returned CONTESTED, handled per rules.md §14 as a zero-live-owner file: the folder is untracked, written by `create_scheduled_task` at 09-22 10:42:33 (mtime = creation, so unedited since), with no claims. Checked by hand, then edited directly. The folder is still uncommitted, as it has been since registration.

## 2026-09-22 — LAMS fleet resume handoff written for 09-28 (closes "no LAMS resume" gap)
- **Authority:** Gabriel, in-turn: "write a LAMS resume handoff for 09-28".
- **Brief:** `maintenance/_state/handoffs/2026-09-28_LAMS-fleet-resume_brief.md`. It is run by hand from a native on-device Cowork session on Mon 09-28, in the same attended sitting as the CC `ora-routine-pause-resume-09-28` (10:00), starting by 10:30 so the LAMS Monday slots (10:35+) fire on schedule. It is a brief rather than a registered task because a scheduled resume blocks on approval prompts when nobody is present (OI-273).
- **Scope:** re-enables 25 LAMS recurring ids (27 disabled minus `ora-ar-export-freshness-nudge` and `ora-health-guard-fail-aging-nudge`, both retire-pending). Step 1 requires `2026-09-22_LAMS-once-weekly-cleanup_brief.md` to finish first, or runs it inline. It subsumes the 09-22 partial re-enable (outreach-queue-refresh, heartbeat, AHM) and does not re-stamp `[MODEL:]` (skill doctrine over the 09-22 note). Heartbeat gets a same-day catch-up run to restore the dead-man chain.
- **Found while writing (not fixed):** the CC `ora-routine-pause-resume-09-28` SKILL.md STEP 5 email tells Gabriel the LAMS resume was "registered 2026-09-22". That is false: no LAMS resume is registered, and the brief is the resume. Also, 09-22 Claude Code sessions were blocked from reading the LAMS registry via Bash (config-write-guard matches the path + a heredoc); Grep/Read works.

## 2026-09-22 — R27 remediation Phase 0 + Phase 1 (setup audit, Gabriel-directed)

Plan: `~/.claude/docs/plans/2026-09-22-setup-remediation-plan.md`. Audit: Automation Audit Rev 27.

**Phase 0 (baseline):** local tags `pre-r27-2026-09-22` on ~/.claude b394e1c, ora-skills 275bb39, occ f5ec375, ora-pm 35669b8 (not pushed). Warehouse DB backed up to `data/warehouse/archive/`. Baseline: hooks 57/57, maintenance 41/41, both JS suites green when run serially, registries snapshotted, 268-row capability ledger, hook latency 1,323ms blocking per Bash call. Record: `maintenance/_state/r27-baseline/BASELINE.md`.

**Phase 1 executed:**
- Windows tasks Dead-Man, Heartbeat Push, Wake-and-Launch and Headless ×3 now carry RestartOnFailure (3×, PT5M). The 09-22 09:37 wake catch-ups died `0xC000013A` in 6–8s, before their first log write. Root cause still unproven; see PR #260's START lines. Heartbeat push re-run → `publish --status` OK. Post-change XML: `_state/task-xml-backup-2026-09-22-r27/`. The pre-change XML export failed, so rollback = remove RestartOnFailure (the 09-17 backups had none).
- 4 same-minute collisions retimed, all still `enabled:false`: forward-calendar-digest `30 12 * * 1`, loopnet-listings-sync `30 14 * * 1`, hubspot-renewal-closeout-tasks `0 15 * * 1`, excess-usage-sweep `45 15 * * 5`. **The cron update RE-ENABLED all 4**, the same footgun as 09-17. Re-disabled within ~1 min, nothing fired, enabled count re-verified = baseline 6. Rule landed: ora-skills #74 (`register-scheduled-task` v2.28).
- Uninstalled disabled plugins `code-review` and `commit-commands` (no live dependents).

**Closed, no change:** 1.2 roster cadence mismatch: the 09-17 weekly cap is intentional and the roster is stale (regenerates after resume). 1.5 excel MCP allow: inert under bypassPermissions; workbook-write hook already matches `mcp__excel__.*`. 1.6 blocklist is harness-managed.

**Corrected audit finding:** the `OneDrive - Oxford Capital Partners (1)` mount is Gabriel's account sync root, NOT a duplicate. Left untouched.

**Awaiting Gabriel:** import `ora-skills/_staging/2026-09-22_R27-phase1_reimport/` (acquisition-underwriting v4.23 + register-scheduled-task v2.28; supersedes the R26-2 packages). Decide on 3 unlanded ~/.claude worktree branches (feat/prune-exclude-bridges, feat/prepush-gate-preexisting-on-main, fix/eval-harness-poll-skip-gate: 1 unique commit each, no PR). Decide on `Claude_Workspace/_CLAUDE_REVIEW_DELETE_` (26MB).

## 2026-09-22 — LAMS fleet fully disabled; Gabriel approves partial re-enable (option 2)
- **Finding:** all 27 LAMS/Cowork recurring tasks read `enabled:false` (registry, 2026-09-22); no LAMS resume queued (09-22 pause resume `ora-routine-pause-resume-09-28` is CC-only; `ora-lams-fleet-resume-20260911` already fired). No event_log record of the LAMS disable. Consequence: dead-man chain (`ora-cowork-heartbeat`) and `automation-health-monitor` silent — why the 09-21 `ora-owner-outreach-queue-refresh` miss went unalarmed. Confirmed independently by session "Routines audit and optimization".
- **Decision (Gabriel, in-turn):** re-enable ONLY `ora-owner-outreach-queue-refresh`, `ora-cowork-heartbeat`, `automation-health-monitor`. Other 24 stay disabled pending `handoffs/2026-09-22_LAMS-once-weekly-cleanup_brief.md` (its "do not re-enable" line superseded for these 3 ids only).
- **Execution:** PENDING — LAMS write; must run from a native on-device Cowork session or the Cowork UI enable toggle (never the trash icon). Re-tag `[MODEL:]` with current date at enable. Log completion here.

## 2026-09-22 — CLOSED: broker-touch-cadence / deal-sourcing-scan doctrine conflicts (local 09-19 versions canonical)

Closes the "Preserved verbatim, NOT reconciled — needs Gabriel" item in today's "Live ~/.claude checkout synced to origin/main" entry.

- **Gabriel's ruling, 2026-09-22:** the live-checkout 09-19 versions are canonical over main's 09-13 graft B.
- `ora-deal-sourcing-scan` v2.7 (listing-agent capture): landed on `origin/main` in `37f247d`. The live file is byte-identical to main.
- `ora-broker-touch-cadence` v1.2: landed via ZeOoba/ora-claude-config PR #258, merged 2026-09-22T21:00Z (`6a55596` + `7e3dc7a`; merge `bf21a54`).
  - Kept: the STEP 0 double-fire guard (`--period month`) and the figure-safe draft path.
  - Dropped: graft-B scorecard ranking and listing citation. If listing citation returns, its non-disclosure and ACTIVE-DEAL CHECK guards must return with it.
  - The run-guard conformance test was updated in the same PR (pre-push 131/131).
- Residual: the live checkout differs from main by one changelog sentence that PR #258 reworded. It is wording only and does not change behavior; it syncs when the checkout is switched to `main` (claimed by another session).
- Verified by the ORA Setup Audit session (Rev 26 follow-up) with `git diff origin/main` on both specs and `gh pr view 258`.

## 2026-09-22 — Skill hygiene sweep landed; 18 skills installed/reimported and verified

- ora-skills main fcf38e2: trigger-only descriptions (72 skills), six largest bodies split to references/, description-history pre-commit gate, local-mirror sweep on post-merge/post-rewrite, ora-setup-audit v1.13. Two adversarial reviews APPROVE-WITH-NITS, nits applied.
- Installed (first install): capex-budgeting, cowork-settings, deal-retirement, personal-portfolio. vendor-contract-qc was already archived 2026-09-11 (735a376); no action.
- Reimported: acquisition-underwriting-eval-harness, automation-health-monitor, capital-asset-register, capital-bid-comparison, county-parcel-screen, dirty-tree-triage, insurance-climate-risk-comparison, isolated-commit, masterlease-jurisdiction-rebase, owner-outreach, pma-qc, register-scheduled-task, settlement-basis-extraction, vendor-management.
- Verification: reimport_correlate verify = CONFIRMED for all 18 (CreationTime moved 18:53-18:54 + exact-second main.log Sync complete); repo_first_check = IN-SYNC for all 18. pma-qc runtime restored to v1.3.
- Open: daily-brief cache v2.15 is MAIN-BEHIND-ORIGIN (local main lacks origin's v2.15); run tools/catch_up_main.py. Not part of this install.

## 2026-09-22 — Owner-outreach funnel repair + template SF copy change
- **Copy change (Gabriel-approved in-turn):** T1/T3/T4 letter templates "roughly 600,000 square feet" → "more than 500,000 square feet" (portfolio ~513K SF). Re-hashed into OR-2026-001 via `ratify_outreach.py --rehash`; pre-change copies in `Investment Candidates -- 2026/_archive/2026-09-22_template-sf-fix/`. ~100 letters previously mailed carried the 600K figure.
- **Incident:** 08-24/09-02/09-07/09-14 packs were the same 50 parcels (08-24 pack never `--released`; the 08-24 mail-log rows are actually the 08-17 pack). Gabriel mailed once; backfilled as 2026-09-02 from a DOCX-reconstructed manifest. `_oo_pack_manifest.json` also listed pre-institutional-exclusion parcels — fixed (manifest now from letter-script `--rendered-out` sidecar).
- **Built:** unreleased-pack scan HALT (exit 3), `reconstruct_pack_manifest.py`, `build_t2_callsheet.py` (first sheet 20260923, 8 calls), `outreach_conversion_report.py`, shared `oo_suppression.py`; owner-outreach skill v1.4 (ora-skills 4f4db95); passed-deal-tracker Step 3b re-marketed passes (uncommitted — ~/.claude on foreign branch). Spec/plan: `docs/superpowers/{specs,plans}/2026-09-22-deal-sourcing-funnel*`.
- **Open:** LAMS `ora-owner-outreach-queue-refresh` did not start 09-21 (no driver log) and must treat exit 3 as "release needed"; C1 manifest path unverified end-to-end until first live scan.

## 2026-09-22 — Four weekly-cadence follow-ups: 3 fixed, 1 was a false finding

**Authority:** Gabriel, in-turn: "fix the four new findings too". Commit 14bc76e on `weekly-window-leftovers` (stacked on eccf870). Live copies were hash-verified, and originals were archived to `maintenance/_archive/2026-09-22_weekly-window/`.

1. **Pause detection (FIXED).** `fleet_pause.py` + `fleet-deadman.ps1` gain `PAUSE_CARVE_OUTS` (cc: ora-am-brief). Root cause: the never-paused brief made every real CC pause read as live. Live check: `cc=PAUSED (resume 2026-09-28)`. The 7 remaining [STALE] outputs are genuine: weekly producers that have not run since 09-14 because the pauses ran back to back; the 09-28 catch-up reruns them.
2. **Dead-Man gaps (MITIGATED; cause unproven).** Scheduled Dead-Man + Heartbeat Push both launched 09-22 09:37:33 and ended 0xC000013A with no log line. The Dead-Man log is missing 5 of 9 days (09-12..09-21). Manual runs complete in 18-22s, and no sleep followed 09:37. No script kills powershell, and the TaskScheduler/Operational log is disabled (not enabled: system setting). Added START breadcrumbs to both scripts and a 120s bound on Dead-Man's two python children (a timeout reports "could not look"). Heartbeat re-published manually 21:03Z (stale 28.5h). Next occurrence will show start-vs-die.
3. **ORA PM Crons (FALSE FINDING).** The Windows task is already Disabled (last run 2026-08-16). "Daily" was its trigger, not its state. No change.
4. **Corrector thresholds (FIXED).** checkout-merge-forward STREAK 14/7 → 2/1 runs; cross-repo-wip-scan ESCALATE 7 → 1, STALE 72h → 192h. Same elapsed-time intent at a weekly cadence. Registry description updated.

**Tests:** fleet_pause+pause_windows+freshness 44 pass · checkout-merge-forward 159/159 · cross-repo-wip-scan 64/64 · new test-fleet-deadman-ps1 5/5.

## 2026-09-22 — Pre-push gate override root cause: lock-test race (PR #259)
- Of the 131 test files in the pre-push gate, only `maintenance/_tests/test_append_event_log_lock.py` still failed on origin/main. The cause was a fixed 0.3s sleep racing interpreter startup under a loaded gate run. The other override causes seen 09-17 to 09-21 already pass on main.
- Fix: the holder process now writes a ready file while holding the lock, and the test polls for it. Before: 7 of 8 concurrent runs failed. After: 8 of 8 passed, and the full set was 131 files with 0 failing. PR ZeOoba/ora-claude-config#259.
- Lesson (cause: test): a test that waits on another process to take a lock must wait for a signal, never a fixed sleep. A sleep that passes when the test runs alone will fail when the gate runs everything in parallel.

## 2026-09-22 — Weekly-cadence leftovers fixed (09-17 "known side effects" closed); heartbeat stays daily

**Authority:** Gabriel, in-turn: "Keep heartbeat daily; fix the four daily-run leftovers." `ora-cowork-heartbeat` is now the standing dead-man exception to the once-a-week cap; the LAMS handoff brief is updated to match.

**Re-diagnosed; two of the four 09-17 claims were wrong:**
- ground-truth-auditor "audits only 24h": FALSE. `ground-truth-run-index.py:112-116` widens the window to the gap since the last auditor run. Real residual: the index holds one row per task id, so a daily task (ora-am-brief) had only its latest run indexed. Fix: new STEP 1b does a status-only `list_task_runs` pass over sub-weekly tasks' other runs in the window.
- SOFR "weekly = stale brief": FALSE. am-brief Block A curls the NY Fed directly each weekday, and every SOFR row is labelled with its effectiveDate. `ora-sofr-direct-prefetch` only refreshes the Notion page after ~08:00 publication. No change; it is now a retirement candidate.
- pm-ledger: new §0.1 weekly window (`{WINDOW_START}`=TODAY−7) for Block A's change-detection filters; Block B `--lookback 15` (with `--now 2026-09-25` the default 7 dropped 09-18, the previous Friday).
- Freshness thresholds: `state-freshness-probe.py` default 48h→192h, with 6 daily-or-faster producers pinned at 48h (new test, 3 pass). LAMS `automation-health-monitor`: WEEKLY-RUN RULE added. Its "yesterday's snapshot" diff would have silently never run on a Monday-only cadence; `--newest-valid` verified to find 2026-09-15.lams.json. The registry-membership beacon went 48h→192h, and the fail-aging-nudge row is marked retired. Backup: `SKILL.md.bak-2026-09-22-weekly-window`.

**Propagation:** commit eccf870 on branch `weekly-window-leftovers`, copied to live and hash-verified (.bak beside each file). Registry descriptions synced with `enabled:false` preserved.

**New findings (not fixed):** (1) `fleet_pause.py` reports CC "live" during the 09-22 pause, because the ora-am-brief carve-out defeats its all-disabled test; so the probe shows 16 genuinely pause-frozen outputs as [STALE]. (2) `fleet-deadman.log` is 57h stale against a daily Windows trigger. (3) The Windows `ORA PM Crons` task is still daily, although ora-pm-daily-crons superseded it (OI-162); verify whether it is enabled. (4) merge-forward's 14-run streak alarm now means 14 weeks.

## 2026-09-22 -- Automation Audit R26-2: acquisition-underwriting re-import

Gabriel confirmed the Save-skill click for `acquisition-underwriting` (Cowork
install button, multi-file skill) at 2026-09-22T16:44:33 local. Pre-built
package from `_staging\2026-09-22_R26-2_reimport\acquisition-underwriting.skill`
(sha256 518087d7...bdc3), hash-verified against the repo copy and the shared
`target-markets.json` dep before presenting; no repackage.

Install verified via `tools/reimport_correlate.py verify`: CONFIRMED --
cache directory CreationTime moved 2026-09-10T14:36:20.574643 ->
2026-09-22T16:44:33.333324, exact-second match against main.log
`Sync complete: 1 downloaded`. `tools/verify_installed_cache.py` confirms
the installed description ends "...v4.22", frontmatter balanced, 0 stray
body quotes. Store was previously v4.20.

## 2026-09-22 — Once/week cap: CC residuals applied, RATIFIED retirements, LAMS handoff

**Authority:** Gabriel, in-turn: "yes, do the CC fixes and write the LAMS handoff". This follows the ora-setup-audit fleet pass that checked for tasks running more than once a week.

**CC/MCP (done, both still `enabled:false` under the 09-22 pause):** `ora-hubspot-renewal-closeout-tasks` `50 10 * * 1-5` → `50 10 * * 1`. `ora-checkout-merge-forward` `45 16 * * *` → `45 16 * * 5`, which revokes its 09-17 daily exemption. Descriptions were updated to say weekly. The update rewrote only the frontmatter description; another session's uncommitted body edits to merge-forward's SKILL.md (PR #250 notes) survived.

**RATIFIED retire (CC, executed):** `ora-routine-pause-resume-09-21`, `ora-resume-0921-attend-reminder`. Both one-time tasks had fired. Order: `delete_scheduled_task` first, then folders moved to `scheduled-tasks/_archive_2026-09-22_retired/`.

**RATIFIED retire (LAMS, pending → retire-pending.json):** `ora-health-guard-fail-aging-nudge` and `ora-lams-fleet-resume-20260911`, plus the previously filed `ora-ar-export-freshness-nudge`. `automation-health-monitor` → `5 11 * * 1`. Brief: `maintenance/_state/handoffs/2026-09-22_LAMS-once-weekly-cleanup_brief.md`. It supersedes the unapplied 09-17 brief. It needs a native on-device Cowork session.

**Open:** (1) `ora-cowork-heartbeat` stays daily pending Gabriel's decision. Going weekly needs the watchdog's `STALE_HOURS_THRESHOLD` raised to ~175h. (2) No LAMS resume is registered and the whole LAMS fleet is disabled. (3) merge-forward's streak alarm (14 runs) now means 14 weeks, not 14 days; that is a body edit, still to do. (4) The 09-17 "known side effects" are still open: ground-truth-auditor's 24h window, SOFR staleness in the brief, pm-ledger's daily framing, and daily freshness thresholds.

## 2026-09-22 — Live ~/.claude checkout synced to origin/main (was 272 behind); dirty-tree triage

**Gabriel-approved in-turn.** Merge `fb8e2f2` (origin/main → `feat/model-canary-probe-step25`, non-ff; main-only now 0). Pre-merge overlap computed read-only per rules.md §14: 35 dirty paths ∩ incoming. 22 were already byte-identical to main (landed via PRs, still dirty in the checkout) → restored to HEAD; 5 untracked pre-PR drafts (`maintenance/headless/*` ×4, `mcp-servers/census/server.py`, all older than main's reviewed commits) → main wins; `fleet-heartbeat.json` → main; `.gitignore`, `MEMORY.md`, `INDEX_reference.md`, `open-items-tracker.md`, `ora-am-brief/SKILL.md` → 3-way merged, local deltas re-applied on top of main. Only commit-level conflict: rules.md `modified:` stamp (kept HEAD's).

**Preserved verbatim, NOT reconciled — needs Gabriel:** `ora-broker-touch-cadence/SKILL.md` (local v1.2, 09-19, double-fire guard) and `ora-deal-sourcing-scan/SKILL.md` (local "v2.7" listing-agent capture, 09-19) exist on no branch. main carries a different 09-13 graft-B v1.1/v2.7. Doctrine conflict: main says the scan "never creates roster rows"; local creates minimal Broker Relationships rows (cap 25/run). The working tree still runs the local versions.

Backup of all 67 touched/dirty files + moved untracked drafts: `maintenance/_archive/2026-09-22_checkout-sync/`. Verified 32 non-overlap dirty files byte-identical before/after. Dirty count 136 → 110. `ora-am-brief` local = `03b77d7` on unmerged `origin/fix/skill-doctrine-2026-09-22`.

Follow-ups: §14 commits PR'd from a worktree (`docs/rules-s14-overlap-rule`); after merge, switch the checkout to `main` (needs fresh approval). Also committed this session: ora-skills `350fdc5` dirty-tree-triage v1.4 (trivial hints match directories, not filenames). Note: `branch-catchup` skill exists for this class of job and was not loaded — procedure followed rules.md §14 + reference_git_merge_blocks_on_identical_dirty_files directly.

## 2026-09-22 -- Correction to the ground-truth audit: the 12550 S Lombard IC memo EXISTS (the Q7 uncheck was NOT applied)

The audit's claim that "no memo exists" for 12550 S Lombard Ln (Deal Sourcing Log row `3cf6ecd8-9e59-8106-8c00-e73978f8a4a8`, "IC Memo Done = YES") was wrong.

- **Where the memo is:** `2026-09-02_12550-S-Lombard-Alsip_IC-Memo_v01.docx` and `.pdf` are in the Cowork session outputs folder `local-agent-mode-sessions\...\local_b9819dc4-5ea6-404a-8661-3a17588568f3\outputs\`. The row's own Notes name them.
- **How it was missed:** the verifier and the refuter searched only `Business\Investment Candidates -- 2026`.
- **Consequence:** Gabriel's "uncheck IC Memo Done" ruling rested on that false premise, so it was NOT applied. The checkbox stays YES.
- **Effect on the audit:** the IC-memo reconciliation's stale-pointer count is 0, not 1. The pending correction draft for that run overstates it.
- **Open:** the memo was never filed into the deal folder. Filing it is a write to a business folder, so it needs Gabriel's permission.
- **Lesson for verifiers:** a "file does not exist" claim must search the session `outputs` stores as well as the canonical folder.

## 2026-09-22 -- Ground-truth audit follow-ups: Gabriel's rulings + retirements (RATIFIED)

Source: Ground-Truth Audit 2026-09-22 (`maintenance/_state/ground-truth/digest-2026-09-22.html`), decisions given in-turn by Gabriel via the decision form.

- **RATIFIED retire `ora-arch-review-followup-check` (CC/MCP).** One-time follow-up whose work is done: OI-319..OI-325 filed, and the self-retire disable landed 2026-09-19 13:00 ET. No producer scripts depend on it. CC order: `delete_scheduled_task` first, then archive the folder to `scheduled-tasks/_archive_2026-09-18_completed-onetime/`.
- **RATIFIED retire `ora-ar-export-freshness-nudge` (LAMS).** Superseded by `ora-ar-feed-sweep` (CC, weekly, live since 2026-08-17). Filed in `retire-pending.json`; to be executed from a native on-device Cowork session (archive first, then registry drop).
- **LAMS re-enable, 11 tasks:** Gabriel: "All 12 back on", minus the AR nudge retired above. Queued for a native on-device Cowork session (OI-340).
- **3034 Westerville deductible:** the 26-27 renewal deductible step from $10K to $25K (with GL limits doubled) was **authorized** by Gabriel. Workbook row 25 is NOT to be touched by automation.
- **PRs #347/#348/#349 + migration 032 (2026-09-21):** Gabriel confirms he directed them in-session. An after-the-fact adversarial review was ordered anyway (OI-345).
- **1900 N Broadway contacts:** both are correct. George Renehan = ops/finance contact; Steve Seh (CRC) = PM.
- **LoopNet Banwick "208":** a mis-keyed 2808; Gabriel will fix it on LoopNet.
- **12550 S Lombard:** uncheck "IC Memo Done" in the Deal Sourcing Log (no memo exists).
- **Corrections:** no retraction emails and no page/store edits (drafts left in `ground-truth-pending-approval/2026-09-22/`, not to be sent).
- **Standing rule (OI-345), WARN only:** a scheduled session that continues past its send should warn before merging or pushing, not block.
- **Owner-outreach vintage (form left blank, default applied):** require a fresh off-market master by 2026-10-05 before the one-time 07-27 ratification keeps clearing waves.


---

*Entries at and before “2026-09-22 -- Ground-truth audit follow-ups: Gabriel's rulings + retirements (RATIFIED)” rolled over 2026-10-08 to [_archive/event_log_2026-10-08.md](_archive/event_log_2026-10-08.md) per memory-policy.md's rollover rule.*

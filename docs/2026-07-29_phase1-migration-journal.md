# Architecture Migration Journal — Milestone 1 (Phase 1: zero-risk hygiene)

**Date:** 2026-07-29 · **Session:** 46a85dfc · **Authority:** Gabriel's in-turn approval of the 2026-07-29 Target-Architecture blueprint (`Claude_Workspace/02_Outputs/2026-07-29_Claude-Environment_Target-Architecture_v01.md`), Phase 1.
**Protocol:** work claim `repo-housekeeping` held; config-write override token minted per guard's documented path (Gabriel in-turn approval); no git commits made (shared checkout carries another session's WIP — reconciliation deferred by design); every change is a move-to-archive or mkdir, all reversible by moving back.

| # | Task (blueprint ref) | Action taken | Validation | Status |
|---|---|---|---|---|
| T1 | Defect #10 — `hooks/state/` absent | `mkdir hooks/state` | dir exists; confidentiality-guard breadcrumb can now land | DONE |
| T2 | §3.2 — stale test orphan | `hooks/test-ora-autonomy-gate.py` → `hooks/archive/test-ora-autonomy-gate.py.retired-2026-07-29` (was git-tracked; moved via plain mv, index untouched) | canonical `hooks/tests/` copy runs: ALL 66 PASS; top-level .py count 25→24 | DONE |
| T3 | §3.2 — retired flat sentinel | zero-byte `hooks/overrides/allow-website-change` → `hooks/archive/allow-website-change.flat-sentinel-removed-2026-07-29` (Invariant 6: archived, not deleted; untracked) | overrides/ empty; 2026-07-16 tombstone intact | DONE |
| T4 | §3.4 — `_shared/` run residue | 37 untracked `_tmp_*`/`hg-*`/report files → `scheduled-tasks/_shared/_archive_2026-07-29_run-residue/` | `_shared/` now holds only: canonical sender + send-log, 2 legacy senders (Phase-3 AIR), 2 credential files (Phase-2 relocation), docs, requirements | DONE |
| T5 | §3.5 — settings backup | `settings.json.bak-2026-07-14` → `backups/` (gitignored) | present in backups/ | DONE |
| T6 | §3.5 — plugin-state orphans | 8 orphan dirs → `plugins/data/_archive_2026-07-29_orphans/` (gitignored); live `hookify-claude-plugins-official` + `superpowers-superpowers-marketplace` untouched | only live dirs + archive remain | DONE |
| T7 | §3.1 — stray docx | `ORA_Master_Workbook_Dynamization_Prompt_v3_FINAL.docx` (project `.claude/`) → `~/.claude/prompts/_archive/` | project .claude/ clean | DONE |
| T8 | §3.4 — expired one-time entries | Registry delete = **verified NO-OP** (live registry no longer contains either id; 07-26 inventory was stale on this point). Folders content-archived to `scheduled-tasks/_archive_2026-07-29_completed-onetime/<id>/`; empty shells rmdir'd after a Permission-denied on direct rename (a process holds directory handles — file-level moves worked) | `task-folder-registration-probe.py`: OK both fleets; `list_scheduled_tasks` unchanged (28 CC entries incl. 2 live one-times) | DONE |

## Milestone validation

- Hook test gate (`git-prepush-hook-tests-gate.py`): **54 pass / 5 fail / 0 env-skip**. All 5 failures root-caused to PRE-EXISTING state independent of this milestone (see Findings). Autonomy-gate suite: 66/66 PASS. Doctrine-integrity-probe: OK (1 pre-existing warning). Fleet: both registries reconcile; VERDICT ATTENTION solely from documented benign throttle-skips.
- Scheduler untouched except the verified no-op; both fleets fire normally (post-milestone lastRunAt values current).
- No authority duplicated, no governance mechanism modified, no monitoring modified.

## Findings (out-of-scope defects discovered; NOT fixed — need their own lanes)

1. **governor-drift-probe false-positive class (3 live findings):** the probe misparses decimal LTV percentages in prose — `54.3% LTV` / `46.6% LTV` in `memory/disposition-ledger.md:38` and `memory/project_historical_evaluations_acquisition_review_2026-07-29.md:46` (both written by another session today, after the 07:57 green push) match as "LTV governor 3%/6% != canonical 40%". Probe regex fix = guard-layer/financial-adjacent code → L2 lane + mandatory REFUTE pass.
2. **memory-integrity-probe test-isolation defect:** its embedded governor check runs against LIVE paths even when the probe targets a sandbox dir, so live drift fails `test-memory-index-git-tracking` / `test-memory-retired-doc-links` / `test-memory-review-by` fixtures (plus one cp1252 UnicodeDecodeError in the same family — known Windows encoding gotcha class).
3. **open-items-tracker.md ID drift (data, not code):** orphaned sections OI-032/OI-033; missing sections OI-019/020/026/027/029 — fails `test_check_open_items_duplicate_ids`. Data reconciliation task.
4. **Consequence:** pushes from `~/.claude` are currently BLOCKED by the pre-push test gate until findings 1–3 are resolved (the gate is working as designed). The 07:30 heartbeat push tomorrow may therefore fail loudly.

## Rollback status
Nothing requires rollback. Full rollback of the milestone = move each archived item back to its origin path (all origins recorded above).

## Token/maintenance impact
Recurring-token impact: 0 (Phase 1 is hygiene by design). Maintenance: ~8 weekly-flagged/stale items eliminated; `_shared/` sensitive folder reduced from ~47 to 10 entries.

## Remaining work (per blueprint)
Phase 2 (defects, incl. the two P0s) → Phase 3 (conditional retirements) → Phase 4 (context optimization) → Phase 5 (governance). Plus the three new findings above, which slot naturally into Phase 2's defect list pending Gabriel's approval.

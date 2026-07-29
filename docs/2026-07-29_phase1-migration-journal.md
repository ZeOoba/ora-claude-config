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

---

# Milestone 2 (Phase 2: defect correction) — EXECUTED 2026-07-29 (same session, Gabriel-approved)

Handoff/state: `handoffs/2026-07-29_phase2-defect-correction-state.md`. Chip claim + `repo-housekeeping` claim held; config-write override token minted per guard path (Gabriel in-turn approval), removed at close.

| # | Task | Result | Validation |
|---|---|---|---|
| T1 | governor-drift-probe decimal-fragment FP | FIXED — `_LTV_VAL` fragment-guard + full-decimal capture + numeric compare; ledger narrative files exempt by exact name; **REFUTE pass (Fable agent, differential old-vs-new on 31 adversarial lines): NOT-REFUTED**; residual #1 (unit-interval silence) adopted as a hardening, residual #3 ('review' pattern token) REJECTED as FN-biased → exact-name exemption instead, residual #2 (decimal suppressor asymmetry, loud-not-silent) documented-accepted | suite 64/64 (6 new regression tests); live probe exit 0, 788 files |
| T2 | memory-integrity-probe sandbox bleed + cp1252 | FIXED — governor delegate skipped under ORA_MEMORY_DIR; both subprocess decodes pinned utf-8/errors=replace | 3 failing hook test files → all exit 0 |
| T3 | open-items-tracker ID drift | RECONCILED — OI-032 Closed row, OI-033 Open row, 5 detail sections added for row-only items | checker clean 33 rows/33 ids/33 sections; test 29/29 |
| T4 | Gate + commit reconciliation | Gate **59/59 GREEN**; 4 commits of this session's touched-set only (`ba2b0a8` probes, archival+tracker, `eb8f45a` MEMORY/event_log backlog drain, settings follow); pushed `021f528..eb8f45a` → all 3 pre-push gates passed. Remote had still been at `021f528` — confirming this morning's heartbeat commit never left the machine | push output; provenance guard raised no objection |
| T5 | P0 Fleet Dead-Man 0x800704A0 | ROOT CAUSE: Win32 1184 ("partition has begun termination") — Interactive-logon task fired during wake/session transition; script itself healthy (manual run exit 0, clean OK line). FIX: task-definition retry policy RestartCount=3 / RestartInterval=PT10M | settings verified; **deferred: next 2 scheduled 07:30 runs must show result 0** |
| T6 | P0 heartbeat-push registration | REGISTERED "ORA Fleet Heartbeat Push" (daily 07:30, StartWhenAvailable, 3×10min retry) via Register-ScheduledTask (schtasks blocked by Git-Bash path mangling). **Live-fire validated:** manual Start-ScheduledTask → emit → commit-only → push `f73d124` through all 3 gates. External dead-man leg now genuinely app-independent | task Ready, NextRun 2026-07-30 07:30; log OK |
| T7 | 2 superseded-convention inline hooks | DELETED from settings.json (blueprint classification) | JSON parses; 0 `[Address] [Purpose] [MM-YYYY]` strings; bindings 30→28 (effective for new sessions) |
| T8 | dead additionalDirectories | REMOVED (`oxford-perfection`, verified absent) | JSON parses; key gone |
| T9 | weekly-hygiene spec folder names | **VERIFIED ALREADY-DONE** — corrected 2026-07-26 (SCOPE-NAME CORRECTION notes at SKILL.md:131/183/462); blueprint entry derived from a same-day inventory snapshot predating the fix | grep shows only correction notes, no live stale refs |
| T10 | model-currency-probe phantom caller | ROOT CAUSE: `ora-task-integrity-guard` STEP 2.5 performs the check INLINE in its prompt body and appends `_state/model-currency-cc.md` itself — no script invocation anywhere; docstring's "wired into ora-health-guard" was never true. Docstring corrected to reality | model-currency test suite passes |
| T11 | credential placement | `FRED_API_KEY`: setx to user env, plaintext env block removed from `.claude.json` (server.py reads os.environ). `.dat` files: **zero live consumers** (sole consumer archived 2026-05-31) → relocated to `C:/Users/Owner/.secrets/`; tech.md §7 secrets index updated | json valid; **deferred: fred MCP reconnect on next app restart; re-check `.claude.json` next session (live harness could rewrite from memory)** |
| T12 | karpathy skillOverride discrepancy | ROOT CAUSE (claude-code-guide, docs-cited): **plugin skills are not affected by skillOverrides** — all ~14 plugin-qualified "off" entries are documented no-ops; real hiding = `/plugin` (Gabriel-side, interactive). Documented, not acted. NOTE for Phase 4: the skill-listing token lever via skillOverrides does NOT reach plugin skills | doc citation in report |

**Deferred validations (owner: next session / tomorrow's fires):** dead-man 2× green · heartbeat 07:30 unattended fire · fred MCP post-restart · `.claude.json` clobber check.
**Out-of-scope confirmations:** per-property LTV gap stays with PR #233 follow-up; OI-029 credential rotations remain Gabriel's.

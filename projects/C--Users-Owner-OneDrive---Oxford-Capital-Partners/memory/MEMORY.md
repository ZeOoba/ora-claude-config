# ORA Memory Index

> Policy: [memory-policy.md](memory-policy.md). **Start here:** [System of Record](00_system_of_record.md) — architecture + cold-start runbook.
>
> **Scope:** canonical = cwd `...Oxford Capital Partners\` (no "(1)") — syncs **egoldberg's** account; `(1)` = Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- **[Portfolio LTV — current, verified](project_portfolio_ltv_current.md)** — 18.71% as of 2026-09-23 (`00_Home!G7`, live read); internal only, no numeric LTV in counterparty/public text; supersedes 17.9% and every "~15%"
- **→ [Projects & system sub-index](INDEX_projects_system.md)** — audit revisions 7–25, oxfordra.net, Command Center, platform/governance, PFI, landed + closed work. **Not auto-loaded** — open it before starting project/audit/website/CC work
- [System of Record](00_system_of_record.md) — architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text. Closed items: [history](open-items-tracker-history.md).
- [Open items OI-357..364, standalone](open-items-2026-09-28-triage.md) — filed 09-28 outside the tracker; not yet merged into it
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls; companion to deal-decision-ledger.md
- [Active Projects](projects.md) — deal pipeline · E. Fulton (declassified) · React brain · oxfordra.net · PM/lease/governance
- **[Strategic constraints — Gabriel's answers 08-16](project_ora_strategic_constraints_2026-08-16.md)** — prioritization frame for ANY build: constraints = sourcing + AM capacity · stay lean, no hires · act-internal/draft-external · all 4 output classes distrusted
- **[Regression root-cause audit 08-28](project_regression_root_cause_audit_2026-08-28.md)** — 6-repo fix→refix pattern, 3 shared mechanisms (no-source-of-truth · heuristic-not-structure · no-real-failure-gate), report-only, [artifact](https://claude.ai/code/artifact/24cabf38-d976-4312-819e-691492696132)
- **OPEN/BLOCKED:** [open-items-tracker worktree/HEAD divergence 07-20](project_open_items_tracker_worktree_head_divergence.md) (don't force-resync) · [event_log IWNS block loss](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) (recovered; cause open) · [primary checkout main-move blocked 08-12](project_primary_checkout_main_move_blocked_2026-08-12.md) (CLEARED 08-16: the 117-file/15-session blocker no longer holds — re-measure, never cite a count from here; rule stands: don't force-switch, isolated worktree only) · [rent-comp retirement process gap 08-13](project_rent_comp_retirement_process_gap_2026-08-13.md) (data restored 08-12; no-dependency-check + no-skip-gate PROCESS gaps still open, task_cf7b9098 spawned)
- **PLANNED, awaiting Gabriel:** [artifact-content top-5](project_artifact_content_top5_plan_2026-07-18.md) · [setup-improvement top-5](project_setup_improvement_top5_plan_2026-07-18.md) + [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md)
- **⛔ [Automation Audit Rev 31 10-13](project_automation_audit_rev31_2026-10-13.md)** — nothing delete-grade; fleet 19/88; 56 skips = one outage burst; pm-monthly-billing never ran; backup push 18d stale. Rev 30 → INDEX_projects_system.md
- **⛔ [Automation Audit Rev 29 10-02](project_automation_audit_rev29_2026-10-02.md)** — latest pass (earlier: Projects & system sub-index; Rev 27 pointer moved there). Fleet 8/87 enabled, unexplained; CLAUDE.md 2w from FAIL; backup push failing; audit-skill copies drift
- **[R28 plugins/connectors 09-30](project_automation_audit_rev28_plugins_connectors_2026-09-30.md)** — Desktop Commander KEEP (19,310 calls); Notion trial lapses ~10-02; send/CMS guard gap; chains Rev 27
- **⚠️ [Run-once guard EXISTS as block-sentinel.py](reference_run_once_guard_is_block_sentinel_not_run_once_guard_ps1.md)** — shipped 08-09 (PR #39/#40); NOT `run-once-guard.ps1`, exits are 10/11/12 not 3/4. Re-specced from scratch once already — verify before building
- **[governor-drift-probe DSCR-changelog-scaling-multiplier fix + duplicate-session finding, 08-22](project_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22.md)** — landed `ecf7b42`; also caught 3+ parallel sessions independently fixing the identical bug — flag for Gabriel
- [Governor-LTV remediation PR #233](project_governor_ltv_remediation_2026-07-24.md) — 11 shipped; OPEN: debt-scoring ltv gap + silent-refusal reload path
- **[Financial-code sweep 09-14 — rent-zeroing](project_financial_code_integrity_sweep_2026-09-14_rent_zeroing.md)** — DATA half RESOLVED 09-18: all 3 zeroed leases (CJ's, Granite Tops, Tyson) mirror the workbook; tenants left, −$130,929.96 NOI is real. STILL OPEN: no guard detects rent zero-outs
- **⛔ [CC branch-protect/mjs-dmts gaps](project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24.md)** — OI-205/OI-206; 08-25: OI-205 now blocks ALL direct pushes to CC `main` — both snapshot tasks strand
- [HubSpot lease-renewal pipeline stalled 08-23](reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23.md) — open deals stuck at appointmentscheduled since 03-27, incl. tenants expiring within days. **Count anchor withdrawn 09-02 — re-measure, never cite one from that file**
- **⛔ [Northwood/EGFLLC $2.8M loan 07-27](project_northwood_egflc_loan_miscategorized_2026-07-27.md) — REOPENED. Reclassified 08-03, REVERSED unlogged 08-09 as a "duplicate"; Gabriel ruled C 08-10: INTERNAL DEBT REPORTING FROZEN until Eric produces the source doc. Quote external debt ($10,627,017) only — never Total Debt/internal. No governor impaired**

## Markets
- **→ [Markets & Deals sub-index](INDEX_markets.md)** — buy box + basis denominator, decision/disposition ledgers, decided deals, rent-roll & lease-data gotchas, insurance, master-lease and workbook findings. **Not auto-loaded — open it before any deal, buy-box, rent-roll, lease-data or workbook question rather than assuming no prior finding exists.** (Count deliberately not stated — a hardcoded anchor belongs in a computed field or nowhere.)
- **⛔ [511 Industrial Mile — duplicate rows + walk/offer conflict 08-16](reference_511_industrial_mile_duplicate_rows_and_walk_offer_conflict_2026-08-16.md)** — ORA's ONLY priced LOI loss ($1.575M won vs ORA's $1.45M). TWO Sourcing Log rows; Walk $930K sits BELOW the actual $1.45M offer, so Loss Class is held UNCLASSIFIED — don't pick a number. Re-engagement tickler fires 08-21. Pipeline `LOI Status` is unreliable — never branch on it
- **⛔ [Executed PSA replaced AFTER reconciliation 09-05](reference_executed_psa_replaced_after_reconciliation_2026-09-05.md)** — 754 Old State's executed PSA silently went 25pp→26pp (md5 `852637b4`→`7ee9d97b`) under the same filename/execution date, invalidating 13 Fact Table rows incl. the "most material defect" one. Hash + page-count the PDF before trusting ANY Fact Table; a post-execution attachment (rent roll dated 17 days after the Effective Date) is not a cure
- **⛔ [openpyxl re-save breaks exceljs workbook parse 08-14](reference_openpyxl_resave_breaks_exceljs_workbook_parse_2026-08-14.md)** — Exit 3 `Cannot read properties of undefined (reading 'comments')` = absolute comment rel targets, NOT a lock or corruption (zip clean, all parts present). Breaks both snapshot tasks AND the mirror deploy (there it reads only as `build:mirror failed (1)`) until Excel rewrites the file

## Reference
- **[Notion free-block quota — RESOLVED 09-30: upgraded to Plus, live create verified](reference_notion_free_block_quota_exhausted_2026-09-12.md)** — [OI-288](open-items-tracker-history.md#OI-288) CLOSED. 21+3 pages backfilled 09-18 (Daily Briefs/Inbox Pre-Briefs/EOD Ledgers/Doctrine checks/financial sweep/skill audit/Rate History), each marked [BACKFILLED] with source cited
- ⛔ **[Bounded pause VOIDS overlapping efficacy checks 08-21](reference_bounded_pause_voided_overlapping_efficacy_checks_2026-08-21.md)** — a paused task and a missed task are indistinguishable in `send-log.txt`; the 08-17 pause manufactured 3 fake misses in `ora-pm-ledger`'s 08-13→08-19 window (4 of 4 eligible days actually delivered ON-SLOT). Check `lastRunAt` + the FleetPause restore ledger BEFORE any efficacy verdict. Also: `recordedSkips` is ROLLING (~6d) — 107→4 is retention decay, not improvement
- **⛔ [Transcript mtime ≠ event date — hookify already stopped 08-13](reference_hookify_noop_hooks_every_tool_call.md)** — hookify's no-op hooks are HISTORICAL, nothing to disable. The reusable lesson: bucket transcript metrics by each event's own `timestamp`, never by file mtime — a resumed session's .jsonl is touched today but holds week-old lines, which made a dead finding read as live
- **⛔ [LastRunTime is re-stamped on Modern Standby resume 08-25](reference_lastruntime_restamped_on_modern_standby_resume.md)** — a long wall-clock scheduled-task run on this laptop is almost always SLEEP, not a hang (135.1 min wall − 126.9 suspended = 8.3 min real). Never bound it with a wall-clock timeout. `fix/deploy-mirror-deploy-timeout` is an EMPTY branch — the SKILL.md pointer to it is wrong
- **⛔ [Next Action Date stamping already wired 08-12](reference_next_action_date_stamping_already_wired_2026-08-12.md)** — live in acquisition-underwriting/loi-generation/deal-execution, runtime bundle verified byte-identical to repo; a flat 3/9 coverage count is not non-adoption — denominator is rows touched SINCE the wiring date, not all open rows
- **→ [Reference sub-index](INDEX_reference.md)** — pointers across tooling, standards, fleet/skill/Notion/workflow gotchas, git/event_log/Windows hazards, Command Center, hooks & guards. **Not auto-loaded — open it before debugging any tooling failure or assuming a gotcha is unrecorded.** (Count deliberately not stated: the baked "108" sat wrong against 133 actual and survived same-day edits to this file — a hardcoded anchor belongs in a computed field or nowhere.)
- **→ [Reference sub-index — git / event_log / Windows-shell](INDEX_reference_git_windows.md)** — shared-checkout, commit, event_log and Windows/shell gotchas; split 2026-09-22. Not auto-loaded
- **→ [Reference sub-index — resolved/closed](INDEX_reference_resolved.md)** — CLOSED findings + dated one-offs kept for citations; split 2026-09-02. Not auto-loaded
- [update_scheduled_task DROPS non-owned frontmatter keys](reference_update_scheduled_task_drops_frontmatter_keys.md) — a `description` retag deletes `output_contract`; diff vs HEAD after every call
- **[delete_scheduled_task resolves a colliding id to the LOCAL fleet 08-17](reference_delete_scheduled_task_resolves_colliding_id_to_local_fleet.md)** — no fleet param; "deregister the LAMS twin" run from Code deletes the LIVE CC task. Verify with a LAMS-only control id (`ora-cowork-heartbeat`) before firing
- **⛔ [Task description lives in ONE store — SKILL.md](reference_skill_description_registry_file_desync.md)** — neither registry holds `description`; a file edit IS durable. NEVER `update_scheduled_task` to "sync" one — that call drops frontmatter keys
- [SKILL.md frontmatter is deliberately NOT strict YAML](reference_skill_frontmatter_lenient_parse.md) — the harness parses line-wise, so ~97/147 fleet SKILL.md fail `yaml.safe_load` **by design**; do NOT mass-quote to satisfy it
- **⛔ [AR review-queue has NO resolver 08-24](reference_ar_review_queue_has_no_resolver.md)** — `review-queue.json` is write-only; the runbook's "run `scripts/ar-import.ts`" is a dead pointer (PDF-only, needs a server Guard 2 forbids). A queued row is not durable — one was erased by a sibling session's regen. Only `overlay.json` (gitignored) held the money
- **⚠️ [AR subsystem — registered 08-17, upstream feed is manual](reference_ar_subsystem_exists_but_dark_2026-08-16.md)** — 09-02: pipeline IS live (`ora-ar-feed-sweep`, CC/MCP, Mon 8:20); the gap moved upstream — the 4 platform exports are pulled BY HAND, ad hoc (7.15→8.21 = 37 days, nothing since), so a stalled feed re-imports the same as-of date and exits 0 looking healthy. `ora-ar-export-freshness-nudge` can't see the CC fleet and nags for a task that exists. Do NOT rebuild the pipeline — 3 sessions nearly did
- [ground-truth-pending-approval/ writer + timing-artifact correction 09-12](reference_ground_truth_auditor_pending_approval_mechanism_2026-09-12.md) — `ora-ground-truth-auditor` drafts there (legit); a "fabricated" in-session verdict was itself wrong. OI-287 dupes a same-session fix

## Rules & governance
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — storage rules, naming, staleness, archival
- [CLAUDE.md word budget is a FLOOR](reference_claude_md_word_budget_is_a_floor.md) — 1700 WARN ≠ ceiling; real gate is FAIL 1850. Don't trim in the 1694–1755 band
- [CLAUDE.md next relocation candidate](reference_claude_md_next_relocation_candidate_2026-08-28.md) — standing minimum-headroom policy; 08-28 used the single-writer bullet (1848→1793w), next pre-picked candidate on file
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to the Claude stack
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every ruling → multiple-choice + researched recommendation
- [Verified null vs inferred null](feedback_verified_null_vs_inferred_null.md) — a zero that could mean "couldn't look" is a FAILURE
- [Absence claims need verification before building](feedback_absence_claims_need_verification_before_building.md) — "nothing checks X" usually means it exists but is disconnected; grep before you build
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done
- [Financial code needs upfront load derivation](feedback_financial_code_upfront_load_derivation.md) — OI-162 took 5 review rounds; state the arithmetic + convergence property before coding, not after
- [Sweep, then verify](feedback_sweep_then_verify.md) — a first grep/edit pass misses instances QC later catches; take the full inventory first, re-grep after to prove zero
- [Polling-claim loop is the default](feedback_polling_claim_loop_default_2026-08-13.md) — contested claim/staged state: wait+recheck (1-4 min cleared it), don't force
- [Check active claims before optimization-queue work](feedback_check_active_claims_before_optimization_queue_work_2026-08-13.md) — 2 of 9 batch items were already claimed by other live sessions
- [Apply findings with outcomes — reusable macro](feedback_apply_findings_with_outcomes_macro.md) — proven twice (CC-round, ora-skills-round); triage → claim by touched path → fix → re-report outcomes
- [ora-skills tests: zero-tests rule](feedback_ora_skills_tests_zero_tests_rule.md) — stdlib unittest + `__main__` only; pytest-style runs 0 tests yet "ok"; run_suite.sh fails EMPTY/BARE (PR #80)
- [REFUTE differential harness](reference_refute_differential_harness.md) — guard/probe regex edits: old-vs-new differential battery; judge deltas, not absolutes
- [Refute gate's path scope went stale TWICE](reference_refute_gate_excludes_server_workbook.md) — never trust a path-scoped `git log` returning empty; diff it against an unscoped log first
- [git status --short hides branch, use -sb](feedback_git_status_short_hides_branch_use_sb.md) — before any commit in a shared checkout; generalizes [[rules.md §14]]
- [Dirty file status is not evidence of unlanded work](feedback_dirty_file_status_is_not_evidence_of_unlanded_work.md) — on a checkout far behind origin/main, dirty != unlanded WIP; diff vs origin/main first. 13/23 were already-merged

- [Piped gate output masks the exit code](feedback_piped_gate_exit_masking.md) — `| grep`/`tail` reports ITS 0, not the gate's; read the file, or the tool's `RESULT_JSON=` line; now [[rules.md §26]]
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — check ground truth before relaying
- [skillOverrides is ignored for plugin skills](reference_skilloverrides_ignored_for_plugin_skills.md) — any key with `:` is inert by construction; disable the plugin, not the skill
- [Browser pane is 0x0 until resized](reference_browser_pane_zero_viewport_blocks_images.md) — "screenshots impossible" is usually an unresized pane; 9/9 agents got this wrong
- [Findings decay — re-check before WRITING](feedback_findings_decay_recheck_before_writing.md) — minutes-long shelf life on shared files; waiting beat intervening 4/4
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims need a citation
- [Session-retro evidence rule](reference_session_retro_evidence_rule.md) — retros need citation + null-result path or they fabricate
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts/aging anchors rot, in data fields too; an anchor belongs in a computed field or nowhere
- [Outlook search filters are UTC, not ET](reference_outlook_search_filters_are_utc_not_et.md) — silently shifts ET-planned sweep windows 4h; results also page at 25
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args
- [Bash tool collapses \n in heredocs](feedback_bash_tool_heredoc_collapses_newlines.md) — corrupted a test file mid-edit; write the patch to a scratch file first
- [Subagent double-completion 09-12](feedback_subagent_double_completion_and_legit_agreement.md) — one task-id can notify twice with different answers; wait for all, differing = failed. Cross-agent identity is fine
- Model tiers: [routines = sonnet-5](feedback_routines_default_model.md) · [oxfordra.net = opus always](feedback_website_model_tier.md) (Gabriel override) · [Agent `model:` pin can fall back mid-run](feedback_agent_model_pin_not_held_end_to_end.md) — verify the transcript, don't assume
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — merged selectively; Hard Invariants supreme
- [Auto-review blast-radius gate](feedback_auto_review_blast_radius_gate.md) — 07-24: blocking for hooks/financial code; needs an AgentTool carve-out
- [config-write-guard: no fast-path](feedback_config_write_guard_no_fast_path.md) — 08-14: investigated and declined; single-line ≠ low-risk in hooks/settings.json/CLAUDE.md
- [Force-push deny stays hard](feedback_destructive_git_deny_stays_hard.md) — 10-15: glob can't allow --force-with-lease safely; narrowing BLOCKED twice, reverted; user runs lease pushes
- [Artifact staleness scan false positives](feedback_artifact_staleness_scan_mtime_false_positives.md) — mtime can't measure a live-read artifact; LIVE/FROZEN/HYBRID convention
- [Relay a model's output in full](feedback_relay_model_output_in_full.md) — 09-18: Cowork cited text it was never sent; summarizing a relay yields confident invention, not an error
- [Worktrees freeze stale memory](reference_worktrees_freeze_stale_memory.md) — 09-18: a 163-behind worktree recalled a withdrawn count as its `description:`; search all worktrees, not just the live tree
- [Livingston Heartland NEVI signed](project_livingston_heartland_nevi_signed.md) — 2026-09-23 site-host agreement executed; ORA pays station power, no host fee (draft terms)

---
*Index holds pointers, not narration — history in [event_log.md](event_log.md).*

*Size gate RECALIBRATED 2026-07-31 (Gabriel): WARN 17.1KB → 21.5KB. The old target was unsatisfiable — stripping every hook floors this file at 15.2KB, so 17.1KB allowed ~10 chars of description per entry, and the only alternative was deleting ~30 live pointers. Both 07-28 blockers re-verified and still true: archiving the CLOSED entries orphans inbound refs in other memory files, and a sub-index fails check 1. Rationale + measurements: [Memory index size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).*

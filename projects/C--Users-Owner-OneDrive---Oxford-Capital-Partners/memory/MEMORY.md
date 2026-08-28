# ORA Memory Index

> Policy: [memory-policy.md](memory-policy.md). **Start here:** [System of Record](00_system_of_record.md) — architecture + cold-start runbook.
>
> **Scope:** canonical = cwd `...Oxford Capital Partners\` (no "(1)") — syncs **egoldberg's** account; `(1)` = Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- **→ [Projects & system sub-index](INDEX_projects_system.md)** — audit revisions 7–12, oxfordra.net, Command Center, platform/governance, PFI, landed + closed work. **Not auto-loaded** — open it before starting project/audit/website/CC work
- [System of Record](00_system_of_record.md) — architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls; companion to deal-decision-ledger.md
- [Active Projects](projects.md) — deal pipeline · E. Fulton (declassified) · React brain · oxfordra.net · PM/lease/governance
- **[Strategic constraints — Gabriel's answers 08-16](project_ora_strategic_constraints_2026-08-16.md)** — prioritization frame for ANY build: constraints = sourcing + AM capacity · stay lean, no hires · act-internal/draft-external · all 4 output classes distrusted
- **OPEN/BLOCKED:** [open-items-tracker worktree/HEAD divergence 07-20](project_open_items_tracker_worktree_head_divergence.md) (don't force-resync) · [event_log IWNS block loss](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) (recovered; cause open) · [primary checkout main-move blocked 08-12](project_primary_checkout_main_move_blocked_2026-08-12.md) (CLEARED 08-16: the 117-file/15-session blocker no longer holds — re-measure, never cite a count from here; rule stands: don't force-switch, isolated worktree only) · [rent-comp retirement process gap 08-13](project_rent_comp_retirement_process_gap_2026-08-13.md) (data restored 08-12; no-dependency-check + no-skip-gate PROCESS gaps still open, task_cf7b9098 spawned)
- **PENDING (uncommitted, staging contention):** [OI-140 CLI-arg fix](reference_oi140_check_open_items_duplicate_ids_cli_fix_2026-08-13.md) (live checkout working tree, verified working, not yet committed)
- **PLANNED, awaiting Gabriel:** [artifact-content top-5](project_artifact_content_top5_plan_2026-07-18.md) · [setup-improvement top-5](project_setup_improvement_top5_plan_2026-07-18.md) + [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md)
- [Automation Audit Rev 17 08-21](project_automation_audit_rev17_2026-08-21.md) — superseded by Rev 18; LAMS duplicate-resurrection bug fix detail → event_log.md 2026-08-21
- **⛔ [Automation Audit Rev 18 08-22](project_automation_audit_rev18_2026-08-22.md)** — MEMORY.md 266B from HARD ceiling (this entry compacted Rev 17 to stay under it); event_log.md 35 days unrolled (1.42MB); LAMS retirement confirmed ratified-not-executed. R17-2 trigger collision CLOSED
- **⚠️ [Run-once guard EXISTS as block-sentinel.py](reference_run_once_guard_is_block_sentinel_not_run_once_guard_ps1.md)** — shipped 08-09 (PR #39/#40); NOT `run-once-guard.ps1`, exits are 10/11/12 not 3/4. Re-specced from scratch once already — verify before building
- **[Usage-report remediation 08-21](project_usage_report_horizon_builds_scoped_2026-08-21.md)** — 5 items shipped (commit-hygiene GAP C advisory PR #142, isolated-commit skill, rules.md §22-24); 3 "on the horizon" builds scoped-only, NOT implemented — read before starting the self-healing fleet, adversarial pre-push swarm, or environment-preflight builds
- **[governor-drift-probe DSCR-changelog-scaling-multiplier fix + duplicate-session finding, 08-22](project_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22.md)** — landed `ecf7b42`; also caught 3+ parallel sessions independently fixing the identical bug — flag for Gabriel
- [Governor-LTV remediation PR #233](project_governor_ltv_remediation_2026-07-24.md) — 11 shipped; OPEN: debt-scoring ltv gap + silent-refusal reload path
- ✅ [3700 Kinsman Blvd FedEx — walk-price breach, RESOLVED 08-24](project_fedex_kinsman_walk_price_breach_2026-08-23.md) — Gabriel let the $3.8M LOI lapse, never transmitted; confirmed via ora-deal-aging-sla 08-26 pull
- **⛔ [CC branch-protect/mjs-dmts gaps](project_ccm_mjs_dmts_parity_and_branch_protection_gap_2026-08-24.md)** — OI-205/OI-206; 08-25: OI-205 now blocks ALL direct pushes to CC `main` — both snapshot tasks strand
- [HubSpot lease-renewal pipeline stalled 08-23](reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23.md) — all 43 deals stuck at appointmentscheduled since 03-27, incl. tenants expiring within days
- **⛔ [Northwood/EGFLLC $2.8M loan 07-27](project_northwood_egflc_loan_miscategorized_2026-07-27.md) — REOPENED. Reclassified 08-03, REVERSED unlogged 08-09 as a "duplicate"; Gabriel ruled C 08-10: INTERNAL DEBT REPORTING FROZEN until Eric produces the source doc. Quote external debt ($10,627,017) only — never Total Debt/internal. No governor impaired**

## Markets
- **→ [Markets & Deals sub-index](INDEX_markets.md)** — buy box + basis denominator, decision/disposition ledgers, decided deals, rent-roll & lease-data gotchas, insurance, master-lease and workbook findings. **Not auto-loaded — open it before any deal, buy-box, rent-roll, lease-data or workbook question rather than assuming no prior finding exists.** (Count deliberately not stated — a hardcoded anchor belongs in a computed field or nowhere.)
- **⛔ [511 Industrial Mile — duplicate rows + walk/offer conflict 08-16](reference_511_industrial_mile_duplicate_rows_and_walk_offer_conflict_2026-08-16.md)** — ORA's ONLY priced LOI loss ($1.575M won vs ORA's $1.45M). TWO Sourcing Log rows; Walk $930K sits BELOW the actual $1.45M offer, so Loss Class is held UNCLASSIFIED — don't pick a number. Re-engagement tickler fires 08-21. Pipeline `LOI Status` is unreliable — never branch on it
- **⛔ [openpyxl re-save breaks exceljs workbook parse 08-14](reference_openpyxl_resave_breaks_exceljs_workbook_parse_2026-08-14.md)** — Exit 3 `Cannot read properties of undefined (reading 'comments')` = absolute comment rel targets, NOT a lock or corruption (zip clean, all parts present). Breaks both snapshot tasks AND the mirror deploy (there it reads only as `build:mirror failed (1)`) until Excel rewrites the file

## Reference
- **[debt-scoring.ts JV-debt basis CONFIRMED 08-22](reference_debt_scoring_oxfordnoi_basis_conservative_not_correct_2026-08-22.md)** — 9cb6169 verified vs live workbook, not just conservative
- **[claim_work.py --paths is space-separated, not comma 08-24](reference_claim_work_paths_comma_vs_space.md)** — a comma-joined value silently becomes ONE bogus path, no error; `covering N path(s)` in the output is the tell
- ✅ **[CC snapshot shrink guard widened to all top-level keys, CLOSED 08-24](reference_cc_snapshot_shrink_guard_covers_lists_only.md)** — root cause (`6b9b507`) + guard gap (`bcda1fc`) both fixed; generic populated→empty/null check now covers any future server-attached section
- ⚠️ **[Rate Snapshot fetched_at 7-day stale 08-24](reference_rate_snapshot_fetched_at_7day_stale_2026-08-24.md)** — ora-sofr-direct-prefetch found ora-am-brief's header stamp still 08-17 on 08-24; a persistent multi-day gap, not the documented same-burst ordering race. §2 patched; §1/3/4 untouched (not this task's scope)
- ⛔ **[Bounded pause VOIDS overlapping efficacy checks 08-21](reference_bounded_pause_voided_overlapping_efficacy_checks_2026-08-21.md)** — a paused task and a missed task are indistinguishable in `send-log.txt`; the 08-17 pause manufactured 3 fake misses in `ora-pm-ledger`'s 08-13→08-19 window (4 of 4 eligible days actually delivered ON-SLOT). Check `lastRunAt` + the FleetPause restore ledger BEFORE any efficacy verdict. Also: `recordedSkips` is ROLLING (~6d) — 107→4 is retention decay, not improvement
- ✅ **[Rev 10 remediation efficacy — CLOSED 08-26](reference_rev10_efficacy_2026-08-20.md)** — the lone FAIL (R10-4) is closed: `ora-psa-drift-watch` fired 08-26 13:50 ET on its first unobstructed slot after the 08-17→08-21 pause, exercising the Rev 7 retime (`45 13 * * 3`). Do not re-open. Marketplaces, eval-harness runs/, ora-setup-audit mirror parity all PASS
- **[Tax & Basis Register entity EINs + 1031 exchange index 08-17](reference_tax_settlement_entity_and_exchange_index_2026-08-17.md)** — 6 entity EINs, EX-12-*/IPX exchange numbers 2015-2026; 5 priority-1 findings filed as [OI-189](open-items-tracker.md#OI-189)-[OI-193](open-items-tracker.md#OI-193)
- **["Metrics History"/Category 4a/4b doesn't exist 08-17](reference_metrics_history_pattern_does_not_exist_2026-08-17.md)** — tax data's home is `property_tax_assessments`
- **⛔ [Transcript mtime ≠ event date — hookify already stopped 08-13](reference_hookify_noop_hooks_every_tool_call.md)** — hookify's no-op hooks are HISTORICAL, nothing to disable. The reusable lesson: bucket transcript metrics by each event's own `timestamp`, never by file mtime — a resumed session's .jsonl is touched today but holds week-old lines, which made a dead finding read as live
- **[DISABLE_AUTOUPDATER also breaks manual `claude update` 08-16](reference_disable_autoupdater_blocks_manual_update.md)** — fails with a false "npm registry unreachable"; registry was fine. Use `env -u DISABLE_AUTOUPDATER claude update`
- **[memory/ missing from single-writer list 08-14](reference_memory_dir_not_in_single_writer_list_2026-08-14.md)** — flagged for next `ora-setup-audit`, not fixed ad hoc; found via external-artifact review
- **[ora-skills "full claim protocol: tech.md §2" pointer is stale 08-14](reference_ora_skills_claim_protocol_pointer_stale_2026-08-14.md)** — only the git-log-diff check exists, no `claim_work.py`-style system; flagged for next `ora-setup-audit`
- [Alert-engine "duplicate" emails 08-11](reference_alert_engine_duplicate_emails_diagnosis_2026-08-11.md) — `bytes=` in the send log is the discriminator. Also: `property_insurance_policies.property_id` holds POLICY slugs, matching 0 of 14 properties
- [ora-session-sweep LAMS registry gap 08-11](reference_ora_session_sweep_lams_registry_gap.md) — OI-121, OPEN: `list_scheduled_tasks` saw CC/MCP only
- **[AM-cluster late wake root cause 08-13](reference_am_cluster_late_wake_root_cause_2026-08-13.md)** — WU reboots killed the app ~33min pre-slot; logon entry existed but had a dead MSIX path — FIXED 08-27. Not sleep config
- **⛔ [LastRunTime is re-stamped on Modern Standby resume 08-25](reference_lastruntime_restamped_on_modern_standby_resume.md)** — a long wall-clock scheduled-task run on this laptop is almost always SLEEP, not a hang (135.1 min wall − 126.9 suspended = 8.3 min real). Never bound it with a wall-clock timeout. `fix/deploy-mirror-deploy-timeout` is an EMPTY branch — the SKILL.md pointer to it is wrong
- **[Acquisition Pipeline uniform-stamp + detector BUILT 08-16](reference_acquisition_pipeline_uniform_stamp_2026-08-16.md)** — all 6 A.1 sources now covered; `⏰ Action Overdue` trap; **scheduled-task files are gitignored — `git add -f` or they go unbacked**
- **[automation-health-monitor repo copy is NOT live 08-16](reference_automation_health_monitor_repo_copy_is_not_live_2026-08-16.md)** — ora-skills copy is v1.5/137 lines, LIVE Scheduled\ copy is v1.24/353 lines; ENTIRE file differs. Edit the Scheduled\ copy. Also: scheduled-task registries store NO description field, so there is no desync risk there (contradicts the older general note)
- [check-open-items ignores its path arg](reference_check_open_items_ignores_path_arg.md) — takes NO args, always reads the canonical tracker while PRINTING the path you passed
- **⛔ [Next Action Date stamping already wired 08-12](reference_next_action_date_stamping_already_wired_2026-08-12.md)** — live in acquisition-underwriting/loi-generation/deal-execution, runtime bundle verified byte-identical to repo; a flat 3/9 coverage count is not non-adoption — denominator is rows touched SINCE the wiring date, not all open rows
- **→ [Reference sub-index](INDEX_reference.md)** — pointers across tooling, standards, fleet/skill/Notion/workflow gotchas, git/event_log/Windows hazards, Command Center, hooks & guards. **Not auto-loaded — open it before debugging any tooling failure or assuming a gotcha is unrecorded.** (Count deliberately not stated: the baked "108" sat wrong against 133 actual and survived same-day edits to this file — a hardcoded anchor belongs in a computed field or nowhere.)
- [update_scheduled_task DROPS non-owned frontmatter keys](reference_update_scheduled_task_drops_frontmatter_keys.md) — a `description` retag deletes `output_contract`; diff vs HEAD after every call
- **[delete_scheduled_task resolves a colliding id to the LOCAL fleet 08-17](reference_delete_scheduled_task_resolves_colliding_id_to_local_fleet.md)** — no fleet param; "deregister the LAMS twin" run from Code deletes the LIVE CC task. Verify with a LAMS-only control id (`ora-cowork-heartbeat`) before firing
- **⛔ [Task description lives in ONE store — SKILL.md](reference_skill_description_registry_file_desync.md)** — neither registry holds `description`; a file edit IS durable. NEVER `update_scheduled_task` to "sync" one — that call drops frontmatter keys
- [SKILL.md frontmatter is deliberately NOT strict YAML](reference_skill_frontmatter_lenient_parse.md) — the harness parses line-wise, so ~97/147 fleet SKILL.md fail `yaml.safe_load` **by design**; do NOT mass-quote to satisfy it
- **⛔ [AR review-queue has NO resolver 08-24](reference_ar_review_queue_has_no_resolver.md)** — `review-queue.json` is write-only; the runbook's "run `scripts/ar-import.ts`" is a dead pointer (PDF-only, needs a server Guard 2 forbids). A queued row is not durable — one was erased by a sibling session's regen. Only `overlay.json` (gitignored) held the money
- **⚠️ [AR subsystem ran for the first time 08-17](reference_ar_subsystem_exists_but_dark_2026-08-16.md)** — `data/ar/` + `arBalances[]` now populated (~$204,788), but it was a one-off manual run, still unregistered (no inbox, no schedule) and unreviewed by Gabriel. Do NOT rebuild the pipeline — 3 sessions nearly did before this

## Rules & governance
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — storage rules, naming, staleness, archival
- [CLAUDE.md word budget is a FLOOR](reference_claude_md_word_budget_is_a_floor.md) — 1700 WARN ≠ ceiling; real gate is FAIL 1850. Don't trim in the 1694–1755 band
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
- [REFUTE differential harness](reference_refute_differential_harness.md) — guard/probe regex edits: old-vs-new differential battery; judge deltas, not absolutes
- [Refute gate's path scope went stale TWICE](reference_refute_gate_excludes_server_workbook.md) — never trust a path-scoped `git log` returning empty; diff it against an unscoped log first
- [git status --short hides branch, use -sb](feedback_git_status_short_hides_branch_use_sb.md) — before any commit in a shared checkout; generalizes [[rules.md §14]]
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — check ground truth before relaying
- [skillOverrides is ignored for plugin skills](reference_skilloverrides_ignored_for_plugin_skills.md) — any key with `:` is inert by construction; disable the plugin, not the skill
- [Browser pane is 0x0 until resized](reference_browser_pane_zero_viewport_blocks_images.md) — "screenshots impossible" is usually an unresized pane; 9/9 agents got this wrong
- [Findings decay — re-check before WRITING](feedback_findings_decay_recheck_before_writing.md) — minutes-long shelf life on shared files; waiting beat intervening 4/4
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims need a citation
- [Session-retro evidence rule](reference_session_retro_evidence_rule.md) — retros need citation + null-result path or they fabricate
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts/aging anchors rot, in data fields too; an anchor belongs in a computed field or nowhere
- [Outlook search filters are UTC, not ET](reference_outlook_search_filters_are_utc_not_et.md) — silently shifts ET-planned sweep windows 4h; results also page at 25
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args
- Model tiers: [routines = sonnet-5](feedback_routines_default_model.md) · [oxfordra.net = opus always](feedback_website_model_tier.md) (Gabriel override) · [Agent `model:` pin can fall back mid-run](feedback_agent_model_pin_not_held_end_to_end.md) — verify the transcript, don't assume
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — merged selectively; Hard Invariants supreme
- [Auto-review blast-radius gate](feedback_auto_review_blast_radius_gate.md) — 07-24: blocking for hooks/financial code; needs an AgentTool carve-out
- [config-write-guard: no fast-path](feedback_config_write_guard_no_fast_path.md) — 08-14: investigated and declined; single-line ≠ low-risk in hooks/settings.json/CLAUDE.md
- [Artifact staleness scan false positives](feedback_artifact_staleness_scan_mtime_false_positives.md) — mtime can't measure a live-read artifact; LIVE/FROZEN/HYBRID convention

---
*Index holds pointers, not narration — history in [event_log.md](event_log.md).*

*Size gate RECALIBRATED 2026-07-31 (Gabriel): WARN 17.1KB → 21.5KB. The old target was unsatisfiable — stripping every hook floors this file at 15.2KB, so 17.1KB allowed ~10 chars of description per entry, and the only alternative was deleting ~30 live pointers. Both 07-28 blockers re-verified and still true: archiving the CLOSED entries orphans inbound refs in other memory files, and a sub-index fails check 1. Rationale + measurements: [Memory index size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).*

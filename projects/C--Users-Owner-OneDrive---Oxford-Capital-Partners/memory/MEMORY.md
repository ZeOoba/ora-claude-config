# ORA Memory Index

> Policy: [memory-policy.md](memory-policy.md). **Start here:** [System of Record](00_system_of_record.md) — architecture + cold-start runbook.
>
> **Scope:** canonical = cwd `...Oxford Capital Partners\` (no "(1)") — syncs **egoldberg's** account; `(1)` = Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- [county-sales-monitor skill draft 08-15](project_county_sales_monitor_skill_draft_2026-08-15.md) — v0.2 DRAFT; cadence/delivery/scope ratified (monthly, Notion DB, Tier A only, Louisville deferred); pilot build not started
- [Dangling worktree landing 08-15](project_dangling_worktree_landing_2026-08-15.md) — CLOSED: PRs #110/#112/#113/#114 merged, 2 others already-landed-elsewhere; settings.json dupe-registration collision found+fixed, PR #105 now CLEAN
- [Multi-repo triage landed 08-15](project_multirepo_triage_landed_2026-08-15.md) — 4-repo dirty/PR/worktree sweep; oxford-command-center PRs #276/#277/#278 landed (OI-049/050/051 plan, confidentiality gate, debt-book-trust), 17 stale worktrees/branches removed, 0 open PRs left anywhere
- [System of Record](00_system_of_record.md) — architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls; companion to deal-decision-ledger.md
- [Active Projects](projects.md) — deal pipeline · E. Fulton (declassified) · React brain · oxfordra.net · PM/lease/governance
- **OPEN/BLOCKED:** [broker OM intake BROKEN in prod 08-04](project_broker_pipeline_blobs_v1_outage_2026-08-04.md) (V1 fns can't auto-provision Blobs; PR #64 ≠ fixed; no data lost) · [open-items-tracker worktree/HEAD divergence 07-20](project_open_items_tracker_worktree_head_divergence.md) (don't force-resync) · [event_log IWNS block loss](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) (recovered; cause open) · [primary checkout main-move blocked 08-12](project_primary_checkout_main_move_blocked_2026-08-12.md) (117+ uncommitted files span 15+ sessions' WIP; don't force-switch, isolated worktree only) · [rent-comp retirement process gap 08-13](project_rent_comp_retirement_process_gap_2026-08-13.md) (data restored 08-12; no-dependency-check + no-skip-gate PROCESS gaps still open, task_cf7b9098 spawned)
- **PENDING (uncommitted, staging contention):** [OI-140 CLI-arg fix](reference_oi140_check_open_items_duplicate_ids_cli_fix_2026-08-13.md) (live checkout working tree, verified working, not yet committed)
- [isolated_commit.py repair wrapper](reference_isolated_commit_repair_wrapper_2026-08-13.md) — LANDED 08-13
- **PLANNED, awaiting Gabriel:** [artifact-content top-5](project_artifact_content_top5_plan_2026-07-18.md) · [setup-improvement top-5](project_setup_improvement_top5_plan_2026-07-18.md) + [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md)
- [Acquisition-underwriting eval harness — PILOTED + scheduled 08-14](reference_skill_eval_harness_gap_2026-08-14.md) — merged `ora-skills` main; poll registered (`ora-acquisition-underwriting-eval-harness`)
- **[Automation Audit Rev 11 08-16](project_automation_audit_rev11_2026-08-16.md)** — narrow follow-up, not full-fleet; README HOOKS→MAINT diagram edge + 7-file `.gitignore` churn fix, both executed; not yet PR'd to main
- **[Automation Audit Rev 10 08-14](project_automation_audit_rev10_2026-08-14.md)** — first UNATTENDED run; it loaded a STALE v1.2 copy of its own skill (repo is v1.3); eval-harness dirties `ora-skills` daily; 3 zero-plugin marketplaces
- [Rev 9 remediation FULLY CLOSED 08-15](project_audit_rev9_remediation_landed_2026-08-14.md) — splits reimported live; capex-budgeting + 5 siblings confirmed Removed via Claude in Chrome
- [Automation Audit Rev 9 08-14](project_automation_audit_rev9_2026-08-14.md) — skills-only: usage ranking, top-skill token recs, 49-skill zero-usage tail sorted keep/ask; first rev under the new 4-band cap
- [Automation Audit Rev 8 08-14](project_automation_audit_rev8_2026-08-14.md) — FULLY CLOSED
- [oxfordra.net SEO Audit](project_oxfordra_seo_audit_2026-07.md) — 84/100; open: portfolio SF/counts, FAQ order, /markets redirect
- [oxfordra.net LCP render delay 08-12](project_oxfordra_lcp_render_delay_2026-08-12.md) — forced-reflow FIXED + live (PR #66); OPEN residual: ~1s@8x Layout cost persists
- [oxfordra.net desktop Perf 98 not 100 08-13](project_oxfordra_desktop_perf_98_not_100_2026-08-13.md) — scoring-curve residue, not a defect; CLS culprit unidentified
- [Claude Env Architecture Baseline 07-29](project_claude_env_architecture_baseline_2026-07-29.md) — forensic baseline; optimization NOT yet approved
- [CC Build State](cc-build-state.md) — PR #200-204 merged; HUBSPOT_TOKEN needed (OI-019)
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — merged; open B2/B3/B5
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — SUPERSEDED
- [Intelligence Platform Roadmap — RATIFIED 07-29](project_intelligence_platform_roadmap_ratified_2026-07-29.md) — merged [PR #246](https://github.com/ZeOoba/oxford-command-center/pull/246); Phase 0 kickoff next
- [Engineering Constitution — RATIFIED 07-29](project_engineering_constitution_ratified_2026-07-29.md) — merged [PR #247](https://github.com/ZeOoba/oxford-command-center/pull/247); governs roadmap/ADRs
- [PFI Build Canon](pfi-build-canon.md) — ratified 14-unit roster, PM assignments, accounting rulings
- [PFI Warehouse Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra; Cowork round-trip unreachable from Code
- [brain.oxfordra.net Access](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is a DEAD END
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — "never pulls" FIXED (PR #192); open: kill-class alerting blind spot, PR #248
- [Mirror Deploy 0xC000013A is usually benign](reference_mirror_deploy_0xc000013a_is_usually_benign.md) — run the classifier; duration is not a detector
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — live on 2 repos; #7 awaits sign-off
- [oxford-cc worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree
- [portfolio.json generatedAt churn](reference_portfolio_json_generatedat_commit_churn.md) — RESOLVED 07-27; dirty ≠ lease data changed
- Setup audits: [07-09](project_claude-setup-audit-2026-07-09.md) (CLOSED) · [07-16](project_claude-setup-audit-2026-07-16.md) (chip TERMINAL, needs Gabriel)
- [eos-review-gate shipped](project_eos_review_gate_shipped_2026-07-24.md) — blast-radius commit review gate, `c53c69c`
- **⚠️ [Run-once guard EXISTS as block-sentinel.py](reference_run_once_guard_is_block_sentinel_not_run_once_guard_ps1.md)** — shipped 08-09 (PR #39/#40); NOT `run-once-guard.ps1`, exits are 10/11/12 not 3/4. Re-specced from scratch once already — verify before building
- [Governor-LTV remediation PR #233](project_governor_ltv_remediation_2026-07-24.md) — 11 shipped; OPEN: debt-scoring ltv gap + silent-refusal reload path
- **⛔ [Northwood/EGFLLC $2.8M loan 07-27](project_northwood_egflc_loan_miscategorized_2026-07-27.md) — REOPENED. Reclassified 08-03, REVERSED unlogged 08-09 as a "duplicate"; Gabriel ruled C 08-10: INTERNAL DEBT REPORTING FROZEN until Eric produces the source doc. Quote external debt ($10,627,017) only — never Total Debt/internal. No governor impaired**
- CLOSED (detail in each file): [Deal-join id-based redesign](project_deal_join_id_based_redesign_queued_2026-08-12.md) ([PR #273](https://github.com/ZeOoba/oxford-command-center/pull/273)) · [acquisition-underwriting doctrine review](project_acquisition_underwriting_doctrine_review_2026-07-18.md) · [Tenant DB renewal-watch view](project_tenant_db_renewal_watch_view_2026-07-22.md) · [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) · [orphan-guard timing](project_orphan_guard_timing_2026-07-24.md) · [autonomy-gate indirection ceiling](project_autonomy_gate_indirection_ceiling_followup.md) · [bash-guard indirection gap](project_bash_guard_indirection_gap.md) · [owner-outreach stale-guard](project_owner_outreach_stale_guard_watch.md) · [Lighthouse perf/CSP](reference_oxfordra_lighthouse_csp_fix_2026-07-21.md)

## Markets
- [Market Intelligence](markets.md) — cross-market snapshots, macro (FRED), replacement cost, comps
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of replacement
- [Notion Pipeline Tracker stale governor fields](reference_notion_pipeline_tracker_stale_governor_fields.md) — RCR formula stale at $95/SF; DSCR text asserted a non-canonical floor; fixed 08-11
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE + buy-box rule validated
- [Disposition & Exit Ledger](disposition-ledger.md) — POST-acquisition lifecycle: ACQUIRED/HOLD/REFI/1031/SALE; 13 deals + 1100 Rarig HOLD backfilled 07-29
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store DG net-lease + cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — basis/NOI/cost-seg; open gaps in file
- [Historical Evaluations acquisition review 07-29](project_historical_evaluations_acquisition_review_2026-07-29.md) — 13-deal table; 2 LTV exceptions, 2 open date discrepancies
- [entry-market-scan defects 08-04](reference_entry_market_scan_defects_2026-08-04.md) — `Gate Review` field: blank = awaiting Gabriel, never placeholder it
- [5515 Catfish Court broker-correspondence claim is FALSE](reference_catfish_court_broker_correspondence_claim_false.md) — 08-14 re-check is a warm follow-up, not a cold call
- [808 Rhoads real broker is Elford, not Koon/Menninger](reference_808_rhoads_real_broker_is_elford_not_koon.md) — Deal went OUT of contract 06-26; seller wants ~$3.5M vs the $2.86M LOI plan
- [Delinquency collection-status blind spot](reference_delinquency_report_collection_status_blindspot.md) — "no action taken" is inferred; wrong 4 of 6 tenants
- [Columbus Suburban default/vacate 07-28](tenant_columbus_suburban_default_2026-07-28.md) — ORA-T-105 gone; $20,457 owed, PM misspells name "Suburan"; vacate ≠ contract expiry
- [Rent-roll vacancy convention changed 08-01](reference_rent_roll_vacancy_convention_change_2026-08-01.md) — occupancy 98.6%→94.9% is definitional, not deterioration
- [parseLeases vacancy-block phantom leases](reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md) — CLOSED 08-03
- [portfolio.json Notion seed-fallback regression](reference_portfolio_json_notion_seed_fallback_regression.md) — FIXED 08-09
- [Both snapshot tasks write ONE file](reference_snapshot_tasks_share_one_file_diff_absorption.md) — the sibling's "no commit" is correct, not broken
- **⛔ [openpyxl re-save breaks exceljs workbook parse 08-14](reference_openpyxl_resave_breaks_exceljs_workbook_parse_2026-08-14.md)** — Exit 3 `Cannot read properties of undefined (reading 'comments')` = absolute comment rel targets, NOT a lock or corruption (zip clean, all parts present). Breaks both snapshot tasks AND the mirror deploy (there it reads only as `build:mirror failed (1)`) until Excel rewrites the file
- [CC snapshot is TRACKED, not ignored](reference_command_center_snapshot_is_tracked_not_ignored.md) — auto-committed unattended; the task file's "git-ignored" claim is wrong
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — split on `Row Retired`, not the ⛔ARCHIVED prefix
- [ora-pm critical-dates feed unreliable 08-04](reference_ora_pm_critical_dates_feed_unreliable_2026-08-04.md) — wrong on 5 of 10 rows; match on property+unit, never tenant name
- [Lease-date detector defects 07-24](reference_lease_date_detector_defects_2026-07-24.md) — PR #232 merged; diff by business key not id
- [HubSpot missed the 07-16 lease-date correction](reference_hubspot_missed_lease_date_correction.md) — HubSpot never fixed; J&R live conflict
- [Insurance lapse confirmed REAL 07-25](project_insurance_lapse_confirmed_real_2026-07-25.md) — 5 properties expired/cancelled, 3 with no plan
- [Master Lease landlord entity states 08-03](project_masterlease_landlord_entity_states_2026-08-03.md) — MD/MO entities sourced; Baqir/Baquir + 13B/B13 open
- [Master Lease next-rev upstream notes](reference_masterlease_next_rev_upstream_notes.md) — typo RESOLVED in v2.4.1; heading fragmentation still open
- [Master workbook no single-writer 07-24](project_master_workbook_no_single_writer_2026-07-24.md) — OPEN: uncoordinated concurrent edits
- [Master workbook single-writer proposal 07-25](project_master_workbook_single_writer_proposal_2026-07-25.md) — RATIFIED; text now [tech.md](tech.md) §3d
- [Cash Data excludes PM-held accounts](reference_cash_data_excludes_pm_held_accounts.md) — negative balance is usually tax-timing, not distress
- [Annual debt service 366-day over-capture](reference_workbook_annual_debt_service_366day_overcapture.md) — RESOLVED 08-05
- [ELS EOMONTH pair-fix landed HALF](reference_els_eomonth_pair_fix_half_applied_2026-08-05.md) — OI-094: `H6:I9` moved to EOMONTH but `Assumptions!B30` was never constrained to month-end; strictly WORSE than pre-fix under manual override

## Reference
- **[memory/ missing from single-writer list 08-14](reference_memory_dir_not_in_single_writer_list_2026-08-14.md)** — flagged for next `ora-setup-audit`, not fixed ad hoc; found via external-artifact review
- **[ora-skills "full claim protocol: tech.md §2" pointer is stale 08-14](reference_ora_skills_claim_protocol_pointer_stale_2026-08-14.md)** — only the git-log-diff check exists, no `claim_work.py`-style system; flagged for next `ora-setup-audit`
- [settings.json enabledPlugins/skillOverrides attribution](reference_settings_json_enabledplugins_skilloverrides_attribution_2026-08.md) — 08-09's "not investigated" was wrong; both collapses are git-attributed (a0e95bf, 165fff3)
- [Alert-engine "duplicate" emails 08-11](reference_alert_engine_duplicate_emails_diagnosis_2026-08-11.md) — `bytes=` in the send log is the discriminator. Also: `property_insurance_policies.property_id` holds POLICY slugs, matching 0 of 14 properties
- [CC snapshot DQ-flag alert was count, not severity](reference_cc_snapshot_refresh_dq_flag_alert_is_count_not_severity.md) — FIXED 08-11; never read `Data-quality flags: 1` as an exception — check `severity`
- [ora-session-sweep LAMS registry gap 08-11](reference_ora_session_sweep_lams_registry_gap.md) — OI-121, OPEN: `list_scheduled_tasks` saw CC/MCP only
- **→ [Reference sub-index](INDEX_reference.md)** — 108 pointers across tooling, standards, fleet/skill/Notion/workflow gotchas, git/event_log/Windows hazards, Command Center, hooks & guards. **Not auto-loaded — open it before debugging any tooling failure or assuming a gotcha is unrecorded.**
- [update_scheduled_task DROPS non-owned frontmatter keys](reference_update_scheduled_task_drops_frontmatter_keys.md) — a `description` retag deletes `output_contract`; diff vs HEAD after every call
- [Task description lives in TWO stores](reference_skill_description_registry_file_desync.md) — editing SKILL.md alone desyncs the registry; sync both, verify by sha
- [SKILL.md frontmatter is deliberately NOT strict YAML](reference_skill_frontmatter_lenient_parse.md) — the harness parses line-wise, so ~97/147 fleet SKILL.md fail `yaml.safe_load` **by design**; do NOT mass-quote to satisfy it

## Rules & governance
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — storage rules, naming, staleness, archival
- [CLAUDE.md word budget is a FLOOR](reference_claude_md_word_budget_is_a_floor.md) — 1700 WARN ≠ ceiling; real gate is FAIL 1850. Don't trim in the 1694–1755 band
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to the Claude stack
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every ruling → multiple-choice + researched recommendation
- [Verified null vs inferred null](feedback_verified_null_vs_inferred_null.md) — a zero that could mean "couldn't look" is a FAILURE
- [Absence claims need verification before building](feedback_absence_claims_need_verification_before_building.md) — "nothing checks X" usually means it exists but is disconnected; grep before you build
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done
- [Polling-claim loop is the default](feedback_polling_claim_loop_default_2026-08-13.md) — contested claim/staged state: wait+recheck (1-4 min cleared it), don't force
- [Check active claims before optimization-queue work](feedback_check_active_claims_before_optimization_queue_work_2026-08-13.md) — 2 of 9 batch items were already claimed by other live sessions
- [REFUTE differential harness](reference_refute_differential_harness.md) — guard/probe regex edits: old-vs-new differential battery; judge deltas, not absolutes
- [Refute gate's path scope went stale TWICE](reference_refute_gate_excludes_server_workbook.md) — never trust a path-scoped `git log` returning empty; diff it against an unscoped log first
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

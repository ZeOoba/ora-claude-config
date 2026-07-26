# ORA Memory Index

> Policy: [memory-policy.md](memory-policy.md). **Start here:** [System of Record](00_system_of_record.md) — architecture + cold-start runbook.
>
> **Scope:** canonical = cwd `...Oxford Capital Partners\` (no "(1)") — syncs **egoldberg's** account; `(1)` = Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- [System of Record](00_system_of_record.md) — architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls; companion to deal-decision-ledger.md
- [Active Projects](projects.md) — deal pipeline · E. Fulton (declassified) · React brain · oxfordra.net · PM/lease/governance
- **OPEN/BLOCKED:** [open-items-tracker worktree/HEAD divergence 07-20](project_open_items_tracker_worktree_head_divergence.md) (don't force-resync) · [event_log IWNS block loss](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) (recovered; cause open)
- **CLOSED 07-26:** [FRED API key exposure 07-24](project_fred_key_exposure_2026-07-24.md) — rotated + all 21 copies resolved; durable lesson: FRED MCP is stdio, spawns fresh per session, no fleet restart ever needed
- **PLANNED, awaiting Gabriel:** [acquisition-underwriting doctrine review](project_acquisition_underwriting_doctrine_review_2026-07-18.md) (9 items) · [artifact-content top-5](project_artifact_content_top5_plan_2026-07-18.md) · [setup-improvement top-5](project_setup_improvement_top5_plan_2026-07-18.md) + [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md)
- [oxfordra.net SEO Audit](project_oxfordra_seo_audit_2026-07.md) — 84/100 at 6th pass; open: portfolio SF/counts, FAQ order, /markets redirect
- [CC Build State](cc-build-state.md) — PR #200-204 merged; HUBSPOT_TOKEN needed (OI-019)
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — merged; open B2/B3/B5
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — Phase 0→3; remaining gaps in file
- [PFI Build Canon](pfi-build-canon.md) — ratified 14-unit roster, PM assignments, accounting rulings
- [PFI Warehouse Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra, v1.0 self-assessed 07-10; Cowork round-trip unreachable from Code + no gate sign-off (07-26)
- [brain.oxfordra.net Access](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is a DEAD END
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — hourly deploy never pulls
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — claude-code-action@v1 live on 2 repos; #7 awaits sign-off
- [oxford-cc worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree
- Claude Code setup audits: [07-09](project_claude-setup-audit-2026-07-09.md) (migration CLOSED 07-17; 15/21 resolved) · [07-16](project_claude-setup-audit-2026-07-16.md) (G1-G8 done; chip TERMINAL, needs Gabriel)
- [eos-review-gate shipped](project_eos_review_gate_shipped_2026-07-24.md) — blast-radius commit review gate, merged `c53c69c`
- [Governor-LTV remediation PR #233](project_governor_ltv_remediation_2026-07-24.md) — 11 defects shipped; OPEN: debt-scoring per-property ltv gap + silent-refusal reload path
- CLOSED threads (pointer only — detail in each file + [event_log](event_log.md)): [config corruption-recurrence 07-25](project_config_corruption_recurrence_closed_2026-07-25.md) · [Tenant DB renewal-watch view](project_tenant_db_renewal_watch_view_2026-07-22.md) · [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) · [setup-self-audit frontmatter probe](project_setup_self_audit_frontmatter_probe_2026-07-24.md) · [orphan-guard timing](project_orphan_guard_timing_2026-07-24.md) · [config-write-guard boundary fix](project_config_write_guard_boundary_fix_2026-07-21.md) · [tenant-HubSpot reconciliation](project_tenant_hubspot_reconciliation_2026-07-21.md) · [autonomy-gate indirection ceiling](project_autonomy_gate_indirection_ceiling_followup.md) · [bash-guard indirection gap](project_bash_guard_indirection_gap.md) · [owner-outreach stale-guard](project_owner_outreach_stale_guard_watch.md) · [sell-your-building page](project_sell_your_building_page_shelved_2026-07-20.md) · [seller resource hub](project_seller_resource_hub_2026-07-21.md) · [Lighthouse perf/CSP](reference_oxfordra_lighthouse_csp_fix_2026-07-21.md)

## Markets
- [Market Intelligence](markets.md) — cross-market snapshots, macro (FRED), replacement cost, comps, Columbus submarket
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of true replacement
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE/TERMINATE + buy-box rule validated
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store Dollar General net-lease + DG cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — sourced basis/NOI/cost-seg; open gaps in file
- [Delinquency collection-status blind spot](reference_delinquency_report_collection_status_blindspot.md) — "no action taken" is inferred from a static 90+ balance; wrong for 4 of 6 tenants on 07-24
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — LARGELY RESOLVED 07-24; split on `Row Retired`, not the ⛔ARCHIVED prefix
- [Lease-snapshot id re-baseline 07-24](project_lease_snapshot_id_rebaseline_pending_2026-07-24.md) — CLOSED same day; found 2 tenants in undetected holdover. Diff by business key, not id
- [Lease-date detector defects 07-24](reference_lease_date_detector_defects_2026-07-24.md) — PR #232 MERGED + re-baselined, surfaced 2 holdover tenants; diff false positives FIXED
- [HubSpot missed the 07-16 lease-date correction](reference_hubspot_missed_lease_date_correction.md) — Notion+workbook fixed, HubSpot never was; J&R is a live unresolved conflict
- [Insurance lapse confirmed REAL 07-25](project_insurance_lapse_confirmed_real_2026-07-25.md) — not a snapshot artifact; 5 properties genuinely expired/cancelled, 3 with no recorded plan
- [Master workbook no single-writer protocol 07-24](project_master_workbook_no_single_writer_2026-07-24.md) — OPEN: Claude Log shows ~140 turns, uncoordinated concurrent edits
- [Master workbook single-writer proposal 07-25](project_master_workbook_single_writer_proposal_2026-07-25.md) — RATIFIED 07-25; canonical protocol text now [tech.md](tech.md) §3d

## Reference
- [Tech Stack & Paths](tech.md) — paths, MCP connectors, secrets index, scheduler, machine constraints
- [Standards — Financial & Communication](standards.md) — modeling conventions (DSCR 1.25×/LTV 40%) + comms tone
- [Lean-RAM Toolkit](reference_lean_ram_toolkit.md) — RAM-saver commands (ram/ora/heavy/handoff/solo) + auto-park watchdog
- [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) — `(1)` folder = ggoldberg's account; no-suffix = **egoldberg's**
- [OneDrive Business/Personal Scope](reference_onedrive_business_scope.md) — consult before broad OneDrive-root searches
- [QuickBooks & Entity Financials](reference_quickbooks_financials.md) — CloudVara RDP, .QBB unparseable, where statements live
- [Warehouse Basis Parsing](reference_warehouse_basis_parsing.md) — where each PM platform states accounting basis
- [Tenant Name Mappings](reference_tenant_name_mappings.md) — PM platform → Notion Tenant DB aliases
- [Property→LLC Signature Roster](reference_property_llc_signature_roster.md) — property → signing-LLC for landlord mail
- [ORA PM App](reference_ora_pm.md) — ZeOoba/ora-pm; 07-16 audit (3 criticals) + confidential-terms purge status
- [oxfordra.net Deploy Canon](reference_oxfordra_deploy_canon.md) — netlify-cli from website-canonical is THE path; merged PR auto-deploys PROD
- [Model Release Checklist](reference_model_release_checklist.md) — hardcoded model IDs + sweep process for new releases
- [Claude Code Setups](reference_claude_code_setups.md) — best public setups: obra/superpowers, Anthropic docs, disler hooks
- [ECC Repo Flagged](reference_ecc_repo_flagged.md) — affaan-m/ECC rejected: malware-clone risk, redundant with skill stack
- [setup-writing-style Platform Skill](reference_writing_style_platform_skill.md) — gated, per-account; never on the filesystem
- [Obsidian Copilot Keychain Gap](reference_obsidian_copilot_keychain_migration_gap.md) — post-migration "Needs API key" = re-enter keys
- [NY Fed API 403 to Hosted Fetch](reference_newyorkfed_api_403_hosted_fetch.md) — pull SOFR locally via Desktop Commander
- [WebFetch Markdown False Negatives](feedback_webfetch_markdown_false_negatives.md) — HTML→markdown strips head/script; verify via raw curl
- [session-env Retention Proposal](reference_session_env_retention_proposal.md) — PROPOSAL: age-gate session-env\ (763 empty dirs, growing)
- [Subagent Anti-Delegation](feedback_subagent_anti_delegation.md) — `Tools:*` subagents may recurse via Agent instead of working; forbid it
- [Concurrent Session Duplicate Hardening](reference_concurrent_session_duplicate_hardening_work.md) — 2 sessions built the same fix unknowingly
- **Fleet & scheduler:** [probe scan sets](reference_probe_scan_sets.md) (what each probe actually globs) · [dual-fleet read](reference_fleet_status_dual_read.md) (WRITES need matching MCP) · [throttle-skip = catch-up burst](reference_fleet_throttle_skip_catchup_burst.md) (inverts producer/consumer order) · [model standard](reference_scheduled_task_model_standard.md) (sonnet-5; observable, not settable) · [filePath mechanism](reference_cc_scheduler_filepath_mechanism.md) (editing SKILL.md IS authoritative) · [approvedPermissions](reference_scheduled_task_approved_permissions.md) (missing grant silently no-ops writes) · [staleness-guard trips](reference_scheduled_task_staleness_guard_trips.md) (case log) · [ora-pm-ledger double-fire](reference_ora_pm_ledger_double_fire.md) (RESOLVED) · [ripgrep blind spot](reference_ripgrep_scheduled_tasks_false_negative.md) (fixed via .ignore) · [schematic producer-clobber](reference_schematic_producer_clobber_recurrence.md) (self-heals via pre-check)
- **Skill gotchas:** [lenient frontmatter parse](reference_skill_frontmatter_lenient_parse.md) (do NOT mass-quote descriptions) · [args corrupts $-amounts](reference_skill_args_positional_substitution_bug.md) (claude-code#79859) · [reimport sync lag](reference_skill_reimport_sync_lag.md) (verify via main.log) · [description version gotcha](reference_skill_description_version_extraction_gotcha.md) (check body H1 first) · [skill surfaces](reference_skill_surfaces.md) (Code plugins vs Cowork OneDrive) · [skill home loss 07-09](reference_skill_home_loss_2026-07-09.md) (probe excludes ora-skills)
- **Notion gotchas:** [dashed UUIDs required](reference_notion_query_requires_dashed_uuid.md) · [view-DSL formula filters are a silent no-op](reference_notion_view_dsl_formula_filter_bug.md) (blank/relative date literals too — always re-query the view) · [pipeline `Last Updated` stalls](reference_pipeline_tracker_last_edited_time_stall.md) (use `Last Activity`) · [cache & quota myth](reference_tenant_db_cache_and_notion_quota_myth.md) (quota is an MCP-tool gate)
- **Workflow gotchas:** [named args dropped](feedback_workflow_named_args_not_delivered.md) (hardcode scriptPath) · [CRLF scriptPath rejection](reference_workflow_scriptpath_crlf_rejection.md) · [synthesis invents specifics](feedback_workflow_synthesis_ungrounded_specifics.md) · [workflows dir single-writer](reference_workflows_dir_single_writer_gap.md) (RESOLVED; mtime sweep still needed) · [deep-research synthesize bug](reference_deep_research_synthesize_stage_bug.md) (FIXED)
- **Git & shared-checkout hazards:** [commit-provenance guard](reference_commit_provenance_guard.md) · [compound-add blind spot FIXED 07-24](feedback_positive_attribution_over_mtime.md) (commit only your own touched-set) · [claim mechanism already exists](reference_provenance_claim_mechanism_already_exists.md) (don't build a 2nd) · [co-file patch hazard](shared-checkout-cofile-patch-hazard.md) · [git index is shared state](feedback_git_index_is_shared_state.md) (re-check `git diff --cached` before committing) · [partial-commit splice](reference_event_log_partial_commit_splice.md) · [pathspec discards the splice](feedback_pathspec_commit_discards_index_splice.md) · [destructive git = hard deny](feedback_destructive_git_deny_stays_hard.md) · [worktree node_modules junction](reference_worktree_node_modules_junction_hazard.md) · [GitHub credential path](reference_github_credential_path.md) · [stale MERGE_HEAD poisons graph](reference_stale_merge_head_poisons_graph.md) (merge silently absorbed by another session) · [is-ancestor insufficient](reference_worktree_staleness_ancestor_check_insufficient.md) (squash breaks ancestry — verify via blob-diff)
- **event_log.md hazards:** [uncommitted backlog](reference_event_log_uncommitted_backlog.md) (whoever notices commits their own entry) · [app-handle lock](reference_event_log_app_handle_lock.md) (drain in-place with backup) · [stdin encoding](feedback_append_event_log_stdin_encoding.md) (use --entry-file)
- **Windows/shell gotchas:** [NUL bytes survive the gate](feedback_nul_bytes_survive_the_gate.md) (tests pass; `git diff` "Bin" is the only tell) · [path escape corruption](feedback_sed_windows_path_escapes.md) (sed + Python non-raw literals mangle `C:\...` — use raw strings/forward slashes) · [unquoted paths collapse](feedback_bash_unquoted_windows_paths_collapse.md) (interpreter path breaks too) · [\$ escapes to literal $](feedback_bash_backslash_dollar_escape_windows_path.md) (misdirects a WRITE; readback can't catch it) · [hook stdin cp1252](reference_windows_hook_stdin_cp1252_encoding_gap.md) · [npm test access violation](feedback_npm_test_intermittent_access_violation.md) (spurious; rerun) · Desktop Commander: [slow init](reference_desktop_commander_extension_slow_init.md) · [$var stripping](reference_desktop_commander_powershell_variable_stripping.md) · [nested-quote mangling](reference_desktop_commander_nested_quote_mangling.md) · [autocrlf defeats hash gates](reference_autocrlf_defeats_content_hash_gates.md) (use git blob ids, not sha256)
- **Command Center:** [repo health](oxford-cc-repo-health.md) (~90 unmerged branches need review) · [gate vs gate:ci](feedback_command_center_gate_vs_gate_ci_divergence.md) (gate:ci runs a real vite build) · [piped gate exit masking](feedback_piped_gate_exit_masking.md) · [CRLF hazard](reference_command_center_crlf_hazard.md) (prefer the Edit tool)
- **Hooks & guards:** [PreToolUse vs git-hook exit codes](reference_pretooluse_vs_git_hook_exit_codes.md) · [PreToolUse sees pre-command state](reference_pretooluse_evaluates_pre_command_state.md) (compound `A && B` judged before `A` ran) · [systemMessage never reaches the model](reference_hook_systemmessage_not_model_visible.md) (use additionalContext) · [confidentiality guard self-deadlock](feedback_confidentiality_guard_selfdeadlock.md) · [config-write-guard quote-split gap](reference_config_write_guard_quote_split_gap.md) (still open) · [fail-open + TTL beats mutex](feedback_fail_open_over_mutex_for_fleet_gates.md) · autonomy gate: [blocks writes not reads](feedback_autonomy_gate_blocks_writes_not_reads.md) · [matcher can't be narrowed](feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md) · [override mechanism](reference_autonomy_gate_override_mechanism.md) · [git_commit_parse.py review risk](reference_git_commit_parse_review_risk.md) (budget 2+ adversarial rounds, not one)
- **Verify before trusting:** [subagent "safe" claims](feedback_verify_subagent_safe_claims.md) · [registry mutation claims](feedback_verify_registry_mutation_claims.md) · [probe findings](feedback_verify_probe_findings_before_acting.md) (hypothesis, not verdict) · [reflagging known gaps](feedback_recheck_before_reflagging_tooling_gaps.md) · [negative Glob results](feedback_verify_negative_glob_results.md) (cross-check `git ls-files`) · [WIP settled via mtime](feedback_verify_wip_settled_via_mtime.md) · [fixture-shaped tests](feedback_fixture_shaped_tests_certify_dead_branches.md) (0%/100% ⇒ suspect the emitter) · [guard session attribution unreliable](feedback_shared_checkout_guard_session_attribution_unreliable.md) · [WorkingSet overcounts RAM](feedback_workingset_sum_overcounts_shared_ram.md) (use Available MBytes) · [chained && hides a skip](feedback_bash_chain_short_circuit_hides_skip.md) (later echo can print after an earlier step failed — re-verify, don't trust narration)

## Rules & governance
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — storage rules, naming, staleness, archival
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to the Claude/agent stack
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every Gabriel ruling → multiple-choice with a researched recommendation
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — check ground truth before relaying another session's claim
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims in artifacts need a citation
- [Session-retro evidence rule](reference_session_retro_evidence_rule.md) — retro templates need citation + null-result path or they fabricate on thin sessions
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts rot; tag `curated @` + VERIFY
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args; verify post-run
- Model tiers: [routines default to sonnet-5](feedback_routines_default_model.md) · [oxfordra.net work = opus always](feedback_website_model_tier.md) (Gabriel override)
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — ChatGPT proposals merged selectively; Hard Invariants supreme
- [Auto-review blast-radius gate](feedback_auto_review_blast_radius_gate.md) — 07-24 ruling: auto-review for hooks/financial code, blocking; needs an AgentTool carve-out first

---
*Index holds pointers, not narration — history in [event_log.md](event_log.md). Last compacted 2026-07-26 (partial — see event_log for what's left).*

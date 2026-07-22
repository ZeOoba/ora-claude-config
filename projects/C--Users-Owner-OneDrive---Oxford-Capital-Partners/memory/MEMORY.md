# ORA Memory Index

> Policy: [memory-policy.md](memory-policy.md). **Start here:** [System of Record](00_system_of_record.md) — architecture + cold-start runbook.
>
> **Scope:** canonical = cwd `...Oxford Capital Partners\` (no "(1)") — syncs **egoldberg's** account; `(1)` = Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — Entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — Role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- [Tenant-HubSpot Reconciliation — CLOSED 07-21](project_tenant_hubspot_reconciliation_2026-07-21.md) — 7 deals corrected, exception-detection v1.2, new monthly task
- [event_log.md IWNS block loss — UNATTRIBUTED](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) — 6 entries recovered; root cause open
- [Acquisition-Underwriting Doctrine Review — PLANNED 07-18](project_acquisition_underwriting_doctrine_review_2026-07-18.md) — 9-item plan, awaiting Gabriel go/no-go
- [Autonomy-gate indirection ceiling — CLOSED 07-17](project_autonomy_gate_indirection_ceiling_followup.md) — [OI-007](open-items-tracker.md#OI-007)
- [bash-guard.mjs indirection gap — CLOSED 07-17](project_bash_guard_indirection_gap.md) — [OI-010](open-items-tracker.md#OI-010)/[OI-011](open-items-tracker.md#OI-011)
- [ora-am-brief LAMS retirement — BLOCKED](project_ora_am_brief_lams_retirement_blocked.md) — both fleets double-firing 0 6 * * *
- [Active Projects](projects.md) — deal pipeline · E. Fulton (declassified) · React brain · oxfordra.net · PM/lease/governance
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra, v1.0 shipped 07-10
- [System of Record](00_system_of_record.md) — architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [CC Build State](cc-build-state.md) — PR #200-204 MERGED; HUBSPOT_TOKEN needed ([OI-019](open-items-tracker.md))
- [brain.oxfordra.net Access Finding](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is DEAD END
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — hourly deploy never pulls
- [PFI Build Canon](pfi-build-canon.md) — ratified 14-unit roster, PM assignments, accounting rulings
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — Phase 0→3; remaining gaps in file
- [PFI Warehouse Systematization Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — MERGED; open B2/B3/B5
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — claude-code-action@v1 LIVE on 2 repos; #7 awaits sign-off
- [oxford-command-center worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree
- [Claude Code Setup Audit 2026-07-09](project_claude-setup-audit-2026-07-09.md) — migration CLOSED 07-17; 15/21 resolved, rest in file
- [Claude Setup Comprehensive Review 2026-07-16](project_claude-setup-audit-2026-07-16.md) — G1-G8 done; chip TERMINAL, needs Gabriel
- [oxfordra.net SEO Audit 2026-07](project_oxfordra_seo_audit_2026-07.md) — 4th pass 07-21: B-(74); seller-hub closed same-day, PR #46 open for 3 warnings
- [Owner-Outreach Stale-Guard Watch](project_owner_outreach_stale_guard_watch.md) — CLOSED 07-14: SKILL.md v1.3 remembers vintage
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls; companion to deal-decision-ledger.md
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text
- [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) — CLOSED 07-17: OI-003–006 executed
- [Artifact content — top-5 open items](project_artifact_content_top5_plan_2026-07-18.md) — PLANNED 07-18: closeout/bug/verify punch-list
- [open-items-tracker.md worktree/HEAD divergence — OPEN 07-20](project_open_items_tracker_worktree_head_divergence.md) — don't force-resync
- [Sell-your-building page — LIVE 07-21](project_sell_your_building_page_shelved_2026-07-20.md) — PR #43 merged/deployed, both known issues fixed
- [Seller-intent resource hub — CLOSED 07-21](project_seller_resource_hub_2026-07-21.md) — PR #45 merged/live, 4 guides + hub index
- [Lighthouse perf/CSP thread — CLOSED 07-21](reference_oxfordra_lighthouse_csp_fix_2026-07-21.md) — PRs #47-52/#54 merged+live; #54 fixed a silent build-pipeline break
- Setup-improvement top-5 (07-18): [overview](project_setup_improvement_top5_plan_2026-07-18.md) · [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md) — PLANNED, awaiting approval

## Markets
- [Market Intelligence](markets.md) — Cross-market snapshots, macro (FRED), replacement cost, comps, Columbus submarket
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store Dollar General net-lease + DG cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — sourced basis/NOI/cost-seg; open gaps in file
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — 124/296 rows archived (reversible); 3 exceptions in file
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE/TERMINATE + buy-box rule validated
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of true replacement

## Reference
- [Skill args positional-substitution bug](reference_skill_args_positional_substitution_bug.md) — `args` corrupts $-amounts; filed claude-code#79859
- [Skill reimport sync lag](reference_skill_reimport_sync_lag.md) — "Save skill" lags disk ~10min; verify via main.log not PENDING_REIMPORT
- [Skill description version-extraction gotcha](reference_skill_description_version_extraction_gotcha.md) — description `vX.Y` can be a sub-component version, not the file version; check body H1 first (acquisition-underwriting: desc said v1.1, file is v4.3)
- [Tenant DB Cache & Notion Quota Myth](reference_tenant_db_cache_and_notion_quota_myth.md) — quota is an MCP-tool gate; `ora-pm-ledger`'s snapshot has the data
- [Deep-Research Synthesize-Stage Bug](reference_deep_research_synthesize_stage_bug.md) — FIXED: schema requires real confirmed claims, stub now fails validation
- [ECC Repo Flagged](reference_ecc_repo_flagged.md) — affaan-m/ECC rejected: malware-clone risk, redundant with skill stack
- [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) — `(1)` folder = ggoldberg's account; no-suffix = **egoldberg's**
- [Subagent Anti-Delegation](feedback_subagent_anti_delegation.md) — `Tools:*` subagents may recurse via Agent instead of working; forbid it
- Verify-before-trusting cluster: [subagent "safe" claims](feedback_verify_subagent_safe_claims.md) (grep-for-refs misses doctrine-in-prose) · [registry mutation claims](feedback_verify_registry_mutation_claims.md) (need a re-check) · [probe findings](feedback_verify_probe_findings_before_acting.md) (a hypothesis, not a verdict)
- [fleet-status.py Dual-Fleet Read](reference_fleet_status_dual_read.md) — reads both registries either surface; WRITES need matching MCP
- [Throttle-skip "global_limit" = catch-up burst](reference_fleet_throttle_skip_catchup_burst.md) — not a bug; lone repeated skips WOULD be
- More verify-first: [negative Glob results](feedback_verify_negative_glob_results.md) (cross-check `git ls-files`) · [WIP settled via mtime](feedback_verify_wip_settled_via_mtime.md) (isRunning isn't per-file)
- [Shared-Checkout Guard Session Attribution Unreliable](feedback_shared_checkout_guard_session_attribution_unreliable.md) — named IDs traced to no match; verify first
- [Workflow named-args not delivered](feedback_workflow_named_args_not_delivered.md) — Workflow({name,args}) drops args on CC Desktop; hardcode scriptPath
- [Workflow synthesis ungrounded specifics](feedback_workflow_synthesis_ungrounded_specifics.md) — synthesis can invent precise-sounding IDs
- Autonomy gate cluster: [writes not reads](feedback_autonomy_gate_blocks_writes_not_reads.md) ("blocked read" = a write indicator was present) · [matcher can't be narrowed](feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md) (3 rounds found bypasses) · [override mechanism](reference_autonomy_gate_override_mechanism.md) (session-scoped tokens, old sentinel RETIRED)
- [PreToolUse vs Git Hook Exit Codes](reference_pretooluse_vs_git_hook_exit_codes.md) — PreToolUse exit 1 non-blocking; git hooks any non-zero blocks
- [Concurrent Session Duplicate Hardening](reference_concurrent_session_duplicate_hardening_work.md) — 2 sessions built the same fix unknowingly
- [Confidentiality Guard Self-Deadlock](feedback_confidentiality_guard_selfdeadlock.md) — malformed confidential-terms.json fail-closes Write/Edit/Bash
- [Sed Windows path escapes](feedback_sed_windows_path_escapes.md) — never sed with literal backslash paths; use Python
- [append-event-log.py stdin encoding](feedback_append_event_log_stdin_encoding.md) — heredoc-to-stdin mangles UTF-8; use --entry-file
- [event_log app-handle lock](reference_event_log_app_handle_lock.md) — Claude.exe can block os.replace; drain in-place with backup
- [Destructive git deny stays hard](feedback_destructive_git_deny_stays_hard.md) — reset --hard/push --force are a categorical deny
- [npm test intermittent access violation](feedback_npm_test_intermittent_access_violation.md) — spurious 0xC0000005 ~30-50%; just rerun
- [OneDrive Business/Personal Scope](reference_onedrive_business_scope.md) — consult before broad OneDrive-root searches
- [Model Release Checklist](reference_model_release_checklist.md) — hardcoded model IDs + sweep process for new releases
- [Windows Hook Stdin cp1252 Gap](reference_windows_hook_stdin_cp1252_encoding_gap.md) — hooks can decode stdin as cp1252; audit CLOSED
- [Tech Stack & Paths](tech.md) — Paths, MCP connectors, secrets index, scheduler, machine constraints
- [ORA PM App](reference_ora_pm.md) — ZeOoba/ora-pm; 07-16 audit (3 criticals) + confidential-terms purge status
- [oxfordra.net Deploy Canon](reference_oxfordra_deploy_canon.md) — netlify-cli from website-canonical is THE path; merged PR auto-deploys PROD
- [Standards — Financial & Communication](standards.md) — Modeling conventions (DSCR 1.25×/LTV 40%) + comms tone
- [Scheduled-Task Model Standard](reference_scheduled_task_model_standard.md) — standard = claude-sonnet-5; observable, not settable
- [CC Scheduler filePath Mechanism](reference_cc_scheduler_filepath_mechanism.md) — registry stores filePath only; editing SKILL.md IS authoritative
- [Scheduled-Task approvedPermissions](reference_scheduled_task_approved_permissions.md) — missing tool grant silently no-ops writes
- [Tenant Name Mappings](reference_tenant_name_mappings.md) — PM platform → Notion Tenant DB reconciliation aliases
- [ripgrep blind on scheduled-tasks](reference_ripgrep_scheduled_tasks_false_negative.md) — rg false-negatives rooted there; fixed via .ignore
- [Hook systemMessage never reaches model](reference_hook_systemmessage_not_model_visible.md) — PreToolUse systemMessage is USER-only; use additionalContext
- [Commit-provenance guard](reference_commit_provenance_guard.md) — blocks a commit sweeping another live session's work
- [event_log.md uncommitted backlog](reference_event_log_uncommitted_backlog.md) — no single committer; whoever notices commits their own entry
- [Fail-open + TTL beats mutex](feedback_fail_open_over_mutex_for_fleet_gates.md) — ratified default for cross-session coordination guards
- [Property→LLC Signature Roster](reference_property_llc_signature_roster.md) — canonical property→signing-LLC lookup for landlord mail
- [ora-pm-ledger Double-Fire](reference_ora_pm_ledger_double_fire.md) — RESOLVED: CC/MCP is sole registration, LAMS twin was orphaned
- [QuickBooks & Entity Financials](reference_quickbooks_financials.md) — CloudVara RDP, .QBB unparseable, where statements live
- [Warehouse Basis Parsing](reference_warehouse_basis_parsing.md) — where each PM platform states accounting basis; accrual vs cash
- [Lean-RAM Toolkit](reference_lean_ram_toolkit.md) — RAM-saver commands (ram/ora/heavy/handoff/solo) + auto-park watchdog
- [Claude Code Setups](reference_claude_code_setups.md) — best public CC setups: obra/superpowers, Anthropic docs, disler hooks
- [Skill Surfaces](reference_skill_surfaces.md) — skills split Code (plugins) vs Cowork (OneDrive)
- [Skill Home Loss 2026-07-09](reference_skill_home_loss_2026-07-09.md) — probe scan excludes ora-skills; 4 skills lost outputs/, restored
- Desktop Commander gotchas: [slow-init](reference_desktop_commander_extension_slow_init.md) (~36s cold-start, not a failure) · [$var stripping](reference_desktop_commander_powershell_variable_stripping.md) (start_process; use cmd) · [nested-quote mangling](reference_desktop_commander_nested_quote_mangling.md) (write a .bat instead)
- [Scheduled-Task Staleness-Guard False Positives](reference_scheduled_task_staleness_guard_trips.md) — case log; check new trips here first
- [Worktree node_modules Junction Hazard](reference_worktree_node_modules_junction_hazard.md) — never junction node_modules then worktree remove --force
- [GitHub Credential Path](reference_github_credential_path.md) — gh.exe-scoped helper overrides GCM; GCM -c fallback + re-seed procedure
- [oxford-command-center Repo Health](oxford-cc-repo-health.md) — tombstones + stale branches pruned; ~90 unmerged need review
- [gate vs gate:ci divergence](feedback_command_center_gate_vs_gate_ci_divergence.md) — gate:ci runs a real vite build that gate skips
- [Piped gate exit masking](feedback_piped_gate_exit_masking.md) — `gate | tail` returns tail's exit code; redirect to file instead
- [Command Center CRLF Hazard](reference_command_center_crlf_hazard.md) — writeFileSync flips EOL and bloats diffs; prefer the Edit tool
- [Shared-Checkout Co-File Patch Hazard](shared-checkout-cofile-patch-hazard.md) — `git diff -- <file>` grabs the other writer's hunks too
- [event_log.md Partial-Commit Splice](reference_event_log_partial_commit_splice.md) — `hash-object`+`update-index` to commit only your entries from a co-mingled file
- [session-env Retention Proposal](reference_session_env_retention_proposal.md) — PROPOSAL: age-gate session-env\ (763 empty dirs, growing)
- [WebFetch Markdown False Negatives](feedback_webfetch_markdown_false_negatives.md) — HTML→markdown strips head/script; verify via raw curl
- [workflows dir single-writer gap](reference_workflows_dir_single_writer_gap.md) — RESOLVED: workflows/ now git-tracked; mtime sweep still needed
- [Obsidian Copilot Keychain Migration Gap](reference_obsidian_copilot_keychain_migration_gap.md) — post-migration "Needs API key" = re-enter keys
- [NY Fed API 403 to Hosted Fetch](reference_newyorkfed_api_403_hosted_fetch.md) — SOFR API 403s hosted fetch; pull locally via Desktop Commander
- [setup-writing-style Platform Skill](reference_writing_style_platform_skill.md) — real gated skill, per-account; never on the filesystem

## Rules & governance
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every Gabriel ruling → multiple-choice with a researched recommendation
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — check ground truth before relaying another session's claim
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done; caught 2 real defects first time
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims in artifacts need a citation
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts rot; refresh at runtime or tag `curated @` + VERIFY
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args; verify result post-run
- [Routines default model](feedback_routines_default_model.md) — all routines default to claude-sonnet-5 unless told otherwise
- [Website work — always highest-intelligence model](feedback_website_model_tier.md) — Gabriel override: opus for all oxfordra.net work
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — ChatGPT proposals merged selectively; Hard Invariants supreme
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — Storage rules, naming, staleness, archival
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to Claude/agent stack

---
*Index holds pointers, not narration — history in [event_log.md](event_log.md). Last compacted 2026-07-21.*

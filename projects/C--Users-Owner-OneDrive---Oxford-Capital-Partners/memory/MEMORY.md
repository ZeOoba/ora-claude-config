# ORA Memory Index

> Policy: See [memory-policy.md](memory-policy.md) for storage rules, naming conventions, and governance.
> **Start here:** [System of Record](00_system_of_record.md) — architecture map + cold-start runbook for the whole brain (data sources, fleet, hooks, connectors, secrets, deploy targets).
>
> **Scope:** canonical = cwd `C:\Users\Owner\OneDrive - Oxford Capital Partners\` (no "(1)" suffix), ratified 2026-07-10 — syncs **egoldberg's** account; `(1)` syncs Gabriel's. Detail: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — Entity, portfolio, team, investment criteria/governor, ops footprint
- [Gabriel Goldberg — Profile](user.md) — Role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- [Acquisition-Underwriting Doctrine Review — PLANNED 07-18](project_acquisition_underwriting_doctrine_review_2026-07-18.md) — 9-item research-grounded plan, Fable-adversarially-reviewed, awaiting Gabriel go/no-go; no edits made yet
- [Autonomy-gate indirection ceiling — CLOSED 07-17](project_autonomy_gate_indirection_ceiling_followup.md) — outbound-action checks landed both sides (email on `main`, netlify via merged PR #30); [OI-007](open-items-tracker.md#OI-007)
- [bash-guard.mjs indirection gap — CLOSED 07-17](project_bash_guard_indirection_gap.md) — indirection + read/write fixes landed; [OI-010](open-items-tracker.md#OI-010)/[OI-011](open-items-tracker.md#OI-011)
- [ora-am-brief LAMS retirement — BLOCKED](project_ora_am_brief_lams_retirement_blocked.md) — Code can't reach LAMS registry writes; both fleets double-firing 0 6 * * *
- [ORA Notion Daily Digest gaps](project_notion_daily_digest_coverage_gaps_2026-07-16.md) — CLOSED 07-16: edit-detection upgraded, 3 wrong lease-exp dates fixed
- [BrainVault vault-backup fix](project_brainvault_vault_backup_failure_2026-07-16.md) — CLOSED 07-16, 6 commits; PR #2 tie-break bullet still needs separate landing
- [Active Projects](projects.md) — deal pipeline (6 deals) · E. Fulton (declassified 07-09) · React brain · oxfordra.net · PM/lease/governance
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra, v1.0 shipped 07-10; verify here before treating any AAOS reference as injected
- [System of Record](00_system_of_record.md) — full architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions (newest first)
- [CC Build State](cc-build-state.md) — PR #200/202/203/204 MERGED; HUBSPOT_TOKEN still needed in .env
- [brain.oxfordra.net Access Finding](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is a DEAD END, do NOT re-attempt
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — hourly deploy never `git pull`s; check `git log HEAD..origin/main` before trusting "baked" as current
- [PFI Build Canon](pfi-build-canon.md) — source of truth: ratified 14-unit roster, PM assignments, accounting rulings
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — Phase 0→3 (06-13): warehouse built; gaps = acquisitions/debt/leasing/forecast/capital
- [PFI Warehouse Systematization Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups, routed to owners
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — MERGED; B1/B4 decided (KEEP deal terms private — do NOT re-flag), open B2/B3/B5
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — claude-code-action@v1 LIVE on 2 repos; ora-claude-config#7 awaits sign-off
- [oxford-command-center brand ratification](project_oxford-command-center-brand-ratification-ambiguity.md) — COMPLETE; repo has 2+ brand systems, grep whole repo
- [oxford-command-center worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree; warehouse:verify EPERM in worktrees only
- [CLAUDE.md Formal Audit](project_claude-md-formal-audit-2026-07-08.md) — Phases 0-3 DONE; 4 deferred items in file
- [Claude Code Setup Audit 2026-07-09](project_claude-setup-audit-2026-07-09.md) — migration CLOSED 07-17; 15/21 items resolved
- [Claude Setup Comprehensive Review 2026-07-16](project_claude-setup-audit-2026-07-16.md) — G1-G8 done; chip TERMINAL, needs Gabriel
- [oxfordra.net SEO Audit 2026-07](project_oxfordra_seo_audit_2026-07.md) — overall C- (59/100); action list in file
- [Owner-Outreach Stale-Guard Watch](project_owner_outreach_stale_guard_watch.md) — CLOSED 07-14: guard confirmed correct, SKILL.md v1.3 remembers vintage
- [Ops Decision Log](ops_decision_log.md) — recurring operational yes/no calls, so they aren't re-litigated; companion to deal-decision-ledger.md
- [Open Items Tracker](open-items-tracker.md) — canonical punch-list; other files POINT here, never restate item text
- [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) — CLOSED 07-17: OI-003–006 all executed
- ROI-brief implementation 2026-07-17 — CLOSED, pushed `08c305c`; record in the schematic + 07-09/07-16 audit files above
- [Artifact content — top-5 open items](project_artifact_content_top5_plan_2026-07-18.md) — PLANNED 07-18: northridge/brockton closeout, ora-pm /100 bug, LOI-throughput line, heartbeat fix, 511/275/monthly-close verify
- [Stale audit report reconciliation — 07-19](project_2026-07-19_stale_audit_report_reconciliation.md) — 7/8 pasted findings already resolved; only real gap (code-debugging-optimizations deploy-gate carve-out) fixed

## Markets
- [Market Intelligence](markets.md) — Cross-market snapshots, macro (FRED), replacement cost, comps, Columbus submarket
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store Dollar General net-lease + DG cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — sourced basis/NOI/cost-seg; open gaps (depreciation, value, REPS)
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — 124/296 rows archived (reversible); 2 held back, 1 unresolved
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE/TERMINATE + the buy-box rule it validates
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of true replacement

## Reference
- [Deep-Research Synthesize-Stage Bug](reference_deep_research_synthesize_stage_bug.md) — FIXED 07-18: schema now built from real confirmed claims (enum+minLength) so a stub fails validation instead of silently passing
- [ECC Repo Flagged](reference_ecc_repo_flagged.md) — affaan-m/ECC evaluated + rejected: documented malware-clone risk, fully redundant with existing skill stack
- [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) — `(1)` folder = ggoldberg's account; canonical no-suffix = **egoldberg's**
- [Subagent Anti-Delegation](feedback_subagent_anti_delegation.md) — `Tools:*` subagents may recurse via Agent/Task instead of working; forbid explicitly
- [Verify Subagent "Safe" Claims](feedback_verify_subagent_safe_claims.md) — re-verify file-move "safe-now" claims directly; grep-for-refs misses doctrine-in-prose
- [Verify Registry Mutation Claims](feedback_verify_registry_mutation_claims.md) — a logged registry delete/update isn't confirmed without a same-fleet re-check
- [Verify Probe Findings Before Acting](feedback_verify_probe_findings_before_acting.md) — a probe finding is a hypothesis, not a verdict; the defect can be in the probe
- [fleet-status.py Dual-Fleet Read](reference_fleet_status_dual_read.md) — reads both registries off disk from either surface; only WRITES need the matching MCP tool
- [Verify Negative Glob Results](feedback_verify_negative_glob_results.md) — a Glob "no files" isn't proof of absence; cross-check `git ls-files`
- [Verify WIP Settled via mtime](feedback_verify_wip_settled_via_mtime.md) — isRunning isn't per-file; compare mtimes across spaced checks first
- [Shared-Checkout Guard Session Attribution Unreliable](feedback_shared_checkout_guard_session_attribution_unreliable.md) — named session IDs traced twice to no registry match; verify before treating as a live blocker
- [Workflow named-args not delivered](feedback_workflow_named_args_not_delivered.md) — Workflow({name, args}) drops args on CC Desktop; hardcode via scriptPath
- [Workflow synthesis ungrounded specifics](feedback_workflow_synthesis_ungrounded_specifics.md) — a planning workflow's own synthesis can invent a precise-sounding count/ID with no real artifact behind it; verify before handing off a write task
- [Autonomy Gate: writes not reads](feedback_autonomy_gate_blocks_writes_not_reads.md) — a "blocked read" means a write indicator was present; read the hook before the override
- [Autonomy Gate Matcher Cannot Be Narrowed](feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md) — 3 rounds each found a real bypass narrowing it; reverted, broad match stays
- [Autonomy Gate Override Mechanism](reference_autonomy_gate_override_mechanism.md) — tokens session-scoped + severity-split + content-bound; old flat sentinel RETIRED
- [PreToolUse vs Git Hook Exit Codes](reference_pretooluse_vs_git_hook_exit_codes.md) — opposite conventions (PreToolUse exit 1 non-blocking; git hooks any non-zero blocks)
- [Concurrent Session Duplicate Hardening](reference_concurrent_session_duplicate_hardening_work.md) — 2 sessions built the same fix unknowingly; check `git worktree list` + active sessions first
- [Confidentiality Guard Self-Deadlock](feedback_confidentiality_guard_selfdeadlock.md) — malformed confidential-terms.json fail-closes Write/Edit/Bash; recover via desktop-commander
- [Sed Windows path escapes](feedback_sed_windows_path_escapes.md) — never sed with literal backslash paths; use Python
- [append-event-log.py stdin encoding](feedback_append_event_log_stdin_encoding.md) — heredoc-to-stdin mangles UTF-8; use --entry-file
- [event_log app-handle lock](reference_event_log_app_handle_lock.md) — Claude.exe can hold the file, blocking os.replace; drain in-place with backup
- [Destructive git deny stays hard](feedback_destructive_git_deny_stays_hard.md) — reset --hard/push --force are a categorical deny; never loosen
- [npm test intermittent access violation](feedback_npm_test_intermittent_access_violation.md) — spurious 0xC0000005 ~30-50% of runs; just rerun
- [OneDrive Business/Personal Scope](reference_onedrive_business_scope.md) — classification only; consult before broad OneDrive-root searches
- [Model Release Checklist](reference_model_release_checklist.md) — where hardcoded model IDs live + sweep process for new releases
- [Windows Hook Stdin cp1252 Gap](reference_windows_hook_stdin_cp1252_encoding_gap.md) — harness-spawned hooks can decode stdin as cp1252; 4/16 hooks fixed, 12 confirmed low-risk, audit CLOSED
- [Tech Stack & Paths](tech.md) — Paths, MCP connectors, secrets index, scheduler, machine constraints
- [ORA PM App](reference_ora_pm.md) — ZeOoba/ora-pm; 07-16 audit (3 criticals) + confidential-terms purge status
- [oxfordra.net Deploy Canon](reference_oxfordra_deploy_canon.md) — netlify-cli from website-canonical is THE path; a merged PR auto-deploys PROD
- [Standards — Financial & Communication](standards.md) — Modeling conventions (DSCR 1.25×/LTV 40%) + comms tone by audience
- [Scheduled-Task Model Standard](reference_scheduled_task_model_standard.md) — standard = claude-sonnet-5; model is observable but not settable
- [CC Scheduler filePath Mechanism](reference_cc_scheduler_filepath_mechanism.md) — registry stores only filePath; editing a task's SKILL.md IS authoritative
- [Scheduled-Task approvedPermissions](reference_scheduled_task_approved_permissions.md) — dispatch ≠ completion; a task missing its tool grant makes unattended writes silently fail (lastRunAt still advances)
- [Tenant Name Mappings](reference_tenant_name_mappings.md) — PM platform → Notion Tenant DB reconciliation aliases
- [ripgrep blind on scheduled-tasks](reference_ripgrep_scheduled_tasks_false_negative.md) — rg returns zero matches rooted at scheduled-tasks/; fixed via rg-only .ignore
- [Hook systemMessage never reaches model](reference_hook_systemmessage_not_model_visible.md) — PreToolUse systemMessage is USER-only; use additionalContext
- [Commit-provenance guard](reference_commit_provenance_guard.md) — blocks a commit sweeping another live session's work; pathspec-vs-partial-hunk safety condition inside
- [event_log.md uncommitted backlog](reference_event_log_uncommitted_backlog.md) — no single committer; whoever notices commits it, isolating only their own entry
- [Fail-open + TTL beats mutex](feedback_fail_open_over_mutex_for_fleet_gates.md) — ratified default for cross-session coordination guards
- [Property→LLC Signature Roster](reference_property_llc_signature_roster.md) — canonical property→signing-LLC lookup for landlord mail
- [ora-pm-ledger Double-Fire](reference_ora_pm_ledger_double_fire.md) — RESOLVED 07-12: CC/MCP is sole registration, LAMS twin was an orphan
- [QuickBooks & Entity Financials](reference_quickbooks_financials.md) — CloudVara RDP, .QBB unparseable, where statements live
- [Warehouse Basis Parsing](reference_warehouse_basis_parsing.md) — where each PM platform states accounting basis; accrual vs cash
- [Lean-RAM Toolkit](reference_lean_ram_toolkit.md) — RAM-saver commands (ram/ora/heavy/handoff/solo) + auto-park watchdog
- [Claude Code Setups](reference_claude_code_setups.md) — best public CC setups: obra/superpowers, Anthropic docs, disler hooks
- [Skill Surfaces](reference_skill_surfaces.md) — skills split Code (plugins) vs Cowork (OneDrive); deal-lifecycle lives on Cowork
- [Skill Home Loss 2026-07-09](reference_skill_home_loss_2026-07-09.md) — probe scan excludes ora-skills; 4 skills lost outputs/, restored
- [Desktop Commander extension slow-init](reference_desktop_commander_extension_slow_init.md) — "can't connect" is usually a ~36s cold-start, not a failure
- [Desktop Commander PowerShell $var stripping](reference_desktop_commander_powershell_variable_stripping.md) — start_process strips $vars; use cmd.exe with literal paths
- [Desktop Commander nested-quote mangling](reference_desktop_commander_nested_quote_mangling.md) — nested cmd.exe quoting injects a leading space; write a .bat instead
- [Scheduled-Task Staleness-Guard False Positives](reference_scheduled_task_staleness_guard_trips.md) — case log; check new trips here first
- [Worktree node_modules Junction Hazard](reference_worktree_node_modules_junction_hazard.md) — never junction node_modules then worktree remove --force
- [GitHub Credential Path](reference_github_credential_path.md) — gh.exe-scoped helper overrides GCM; GCM -c fallback + re-seed procedure
- [oxford-command-center Repo Health](oxford-cc-repo-health.md) — tombstones + 24 stale branches pruned; ~90 unmerged need a supervised pass
- [gate vs gate:ci divergence](feedback_command_center_gate_vs_gate_ci_divergence.md) — gate:ci runs a real vite build that gate skips
- [Piped gate exit masking](feedback_piped_gate_exit_masking.md) — `gate | tail` returns tail's exit code; redirect to file when the code is the evidence
- [Command Center CRLF Hazard](reference_command_center_crlf_hazard.md) — writeFileSync flips EOL and bloats diffs; prefer the Edit tool
- [Shared-Checkout Co-File Patch Hazard](shared-checkout-cofile-patch-hazard.md) — `git diff -- <file>` grabs the other writer's hunks too; inspect diff content
- [session-env Retention Proposal](reference_session_env_retention_proposal.md) — PROPOSAL: age-gate session-env\ (763 empty dirs, growing)
- [WebFetch Markdown False Negatives](feedback_webfetch_markdown_false_negatives.md) — HTML→markdown strips head/script; verify via raw curl before trusting
- [workflows dir single-writer gap](reference_workflows_dir_single_writer_gap.md) — RESOLVED 07-16: workflows/ now git-tracked; mtime sweep still catches in-flight edits
- [Obsidian Copilot Keychain Migration Gap](reference_obsidian_copilot_keychain_migration_gap.md) — "Needs API key" post-migration = empty secretStorage, re-enter keys
- [NY Fed API 403 to Hosted Fetch](reference_newyorkfed_api_403_hosted_fetch.md) — SOFR API 403s hosted fetch; pull locally via Desktop Commander
- [setup-writing-style Platform Skill](reference_writing_style_platform_skill.md) — real gated skill, per-account; never on the filesystem

## Rules & governance
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every Gabriel ruling → multiple-choice interactive with a researched recommendation (2026-07-18)
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — confirmed 2x in one session; check ground truth before relaying another session's status claim
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done; caught 2 real defects first time
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims in artifacts need a citation; 3/3 artifacts failed this 07-18
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts rot; refresh at runtime or tag `curated @` + VERIFY
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args; verify result post-run
- [Routines default model](feedback_routines_default_model.md) — all routines default to claude-sonnet-5 unless told otherwise
- [Website work — always highest-intelligence model](feedback_website_model_tier.md) — Gabriel override: opus for all oxfordra.net work
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — ChatGPT-drafted proposals merged selectively; Hard Invariants supreme
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, chip claim-lock §8, confidentiality §7a, permission regime §10
- [Memory Policy](memory-policy.md) — Storage rules, naming, staleness, archival
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to the Claude/agent stack, not per-seat SaaS

---
*Index hygiene history moved to [event_log.md](event_log.md) — the index holds pointers, not narration. Last compacted 2026-07-17.*

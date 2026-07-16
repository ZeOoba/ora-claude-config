# ORA Memory Index

> Policy: See [memory-policy.md](memory-policy.md) for storage rules, naming conventions, and governance.
> **Start here:** [System of Record](00_system_of_record.md) — architecture map + cold-start runbook for the whole brain (data sources, fleet, hooks, connectors, secrets, deploy targets).
>
> **Scope:** canonical memory scope = cwd `C:\Users\Owner\OneDrive - Oxford Capital Partners\` (no "(1)" suffix), ratified 2026-07-10. It syncs **egoldberg's** OneDrive account; the non-canonical `(1)` folder syncs Gabriel's. Full history, guard-repoint status, and the open business-bulk question: [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md).

## Firm & people
- [Firm Context](firm.md) — Entity, portfolio, team, investment criteria/governor, ops footprint, active-initiative pointers
- [Gabriel Goldberg — Profile](user.md) — Role, expertise, working style, contact, surfaces
- [People](people.md) — Eric, Gabriel, Philip Collins (counsel), Tamara Lucas (title); brokers/lenders/vendors

## Projects & system
- [BrainVault vault-backup silent failure](project_brainvault_vault_backup_failure_2026-07-16.md) — 0 backups since 07-10 20:05, likely Windows Job-Object kill of detached child; PR #2 OPEN not merged; 1,123-path backlog awaits Gabriel review
- [Active Projects](projects.md) — deal pipeline (6 deals) · E. Fulton (TERMINATED→lender note, declassified 07-09) · React brain · oxfordra.net · PM/lease/governance
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra (`C:\Users\Owner\AAOS` + OneDrive seam), v1.0 shipped 2026-07-10; verify here before treating any AAOS reference as injected
- [System of Record](00_system_of_record.md) — full architecture + cold-start runbook + fleet/connector/secret inventory
- [Event Log](event_log.md) — append-only system changes, deal milestones, decisions, closed deals (newest first)
- [CC Build State](cc-build-state.md) — PR #200/#202/#203/#204 all MERGED (mirror-deploy git-auth, HubSpot acq sync, debt_positions fix); HUBSPOT_TOKEN still needed in .env
- [brain.oxfordra.net Access Finding](brain-oxfordra-access-finding.md) — LIVE via Pages mirror (Option A), Access-gated; tunnel path was a DEAD END — do NOT re-attempt
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — hourly deploy task never `git pull`s; check `git log HEAD..origin/main` before trusting "baked Nm ago" as current
- [PFI Build Canon](pfi-build-canon.md) — Property Financial Intelligence source of truth: Gabriel-ratified 14-unit roster, PM assignments, accounting rulings (2026-06-12)
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — Phase 0→3 plan (2026-06-13): warehouse built; gaps = acquisitions/debt-refi/leasing/forecast/capital-allocation
- [PFI Warehouse Systematization Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups routed to multi-agent owners (contended files, 2026-06-13)
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — PR #28 MERGED (37-finding audit); B1/B4 decided (KEEP deal terms in private repo — do NOT re-flag), open B2/B3/B5
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — claude-code-action@v1 LIVE on ora-skills + ora-cowork-watchdog (OAUTH_TOKEN auth); ora-claude-config#7 awaits sign-off
- [oxford-command-center brand ratification](project_oxford-command-center-brand-ratification-ambiguity.md) — retokenization COMPLETE (PR-A/B/C/189/191 merged); repo has 2+ brand systems — grep whole repo
- [oxford-command-center worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree; warehouse:verify EPERM on tmp-cleanup only in worktrees
- [CLAUDE.md Formal Audit](project_claude-md-formal-audit-2026-07-08.md) — 2026-07-08 5-agent audit, Phases 0-3 DONE; 4 deferred items in file
- [Claude Code Setup Audit 2026-07-09](project_claude-setup-audit-2026-07-09.md) — 9-agent audit; machine-migration status OPEN (needs Gabriel); 8 fixes applied; 21 items pending — full report is an artifact, link in file
- [Claude Setup Comprehensive Review 2026-07-16](project_claude-setup-audit-2026-07-16.md) — 6-agent review + tiered plan; dead-man chain broken, v4.0 stranded, middle-funnel void; NOTHING executed yet
- [oxfordra.net SEO Audit 2026-07](project_oxfordra_seo_audit_2026-07.md) — 11-part Searchfit audit 2026-07-10: overall C- (59/100); technical strong, content/market coverage weak. Report + action list in file
- [Owner-Outreach Stale-Guard Watch](project_owner_outreach_stale_guard_watch.md) — CLOSED 2026-07-14: guard re-tripped 07-13 correctly (real staleness); Gabriel ratified vintage same-day, SKILL.md v1.3 now remembers it per-vintage
- [Ops Decision Log](ops_decision_log.md) — standing log of small recurring operational yes/no calls, so they aren't re-litigated each session; companion to deal-decision-ledger.md

## Markets
- [Market Intelligence](markets.md) — Cross-market snapshots, macro (FRED), replacement cost, comps, Columbus submarket
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store Dollar General net-lease (PASS, out-of-box) + DG cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — unencumbered, sourced basis/NOI/cost-seg; open gaps (depreciation, value, REPS profile); Tenant DB row-completeness flag
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — REMEDIATION EXECUTED 2026-07-12: 124 of 296 rows archived, all reversible; 2 held back, 1 unresolved. Detail in file
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE/TERMINATE with the buy-box rule each one validates or refines
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — ✅ RATIFIED 2026-07-14: RCT v03 is the ONE denominator; floor = vintage ramp 65%→60%; ORA buys at ~35-40% of true replacement

## Reference
- [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) — `--1-`="(1)" folder = ggoldberg's own account; canonical no-suffix folder = **egoldberg's** account, ratified MAIN 2026-07-10
- [Subagent Anti-Delegation](feedback_subagent_anti_delegation.md) — `Tools:*` general-purpose subagents may recurse via Agent/Task instead of working; forbid it explicitly
- [Verify Subagent "Safe" Claims](feedback_verify_subagent_safe_claims.md) — re-verify a workflow's "safe-now" file-move claims directly before executing; grep-for-code-refs misses doctrine-in-prose references
- [Verify Registry Mutation Claims](feedback_verify_registry_mutation_claims.md) — a logged scheduled-task delete/update isn't confirmed without a same-fleet `list_scheduled_tasks` re-check; cross-fleet calls can silently no-op
- [Verify Probe Findings Before Acting](feedback_verify_probe_findings_before_acting.md) — a probe finding is a hypothesis, not a verdict; the defect can be in the probe, not the flagged artifact
- [fleet-status.py Dual-Fleet Read](reference_fleet_status_dual_read.md) — reads BOTH registries directly off disk from either surface; only WRITES need the matching-surface MCP tool, don't handoff just to check state
- [Verify Negative Glob Results](feedback_verify_negative_glob_results.md) — a Glob "no files found" isn't proof of absence; cross-check with `git ls-files`/`ls` before claiming something has no repo home
- [Workflow named-args not delivered](feedback_workflow_named_args_not_delivered.md) — Workflow({name, args}) drops args on CC Desktop (4 runs, 2026-07-16); hardcode targets via scriptPath + verify the first agent prompt
- [Autonomy Gate Blocks Writes, Not Reads](feedback_autonomy_gate_blocks_writes_not_reads.md) — a "blocked read" on website-canonical means the command carried a write indicator (`>`, `2>&1`); read the hook before the override sentinel
- [Autonomy Gate Matcher Cannot Be Safely Narrowed](feedback_autonomy_gate_matcher_cannot_be_safely_narrowed.md) — 3 adversarial review rounds each found a real bypass in one 2026-07-16 attempt; reverted, the broad match stays
- [Confidentiality Guard Self-Deadlock](feedback_confidentiality_guard_selfdeadlock.md) — malformed confidential-terms.json fail-closes Write/Edit/Bash machine-wide; recover via desktop-commander edit_block
- [Sed Windows path escapes](feedback_sed_windows_path_escapes.md) — never sed s/// with literal backslash paths in replacement; use Python
- [append-event-log.py stdin encoding](feedback_append_event_log_stdin_encoding.md) — heredoc-to-stdin mangles UTF-8 on Windows; use --entry-file
- [event_log app-handle lock](reference_event_log_app_handle_lock.md) — Claude.exe can hold event_log.md, blocking the appender's os.replace while direct writes work; drain in-place with backup + mtime guard
- [Destructive git deny stays hard](feedback_destructive_git_deny_stays_hard.md) — git reset --hard/push --force are a categorical permissions.deny (intentional); never suggest loosening
- [npm test intermittent access violation](feedback_npm_test_intermittent_access_violation.md) — npm test/gate throws spurious 0xC0000005 ~30-50% of runs; content always correct — just rerun, don't debug
- [OneDrive Business/Personal Scope](reference_onedrive_business_scope.md) — classification only, no files moved; consult before broad business-focused OneDrive-root searches
- [Model Release Checklist](reference_model_release_checklist.md) — where hardcoded Claude model IDs live (settings.json, scheduled-task standard, oxford-command-center) + sweep process for new releases
- [Tech Stack & Paths](tech.md) — Paths, MCP connectors + Composio/FRED gotchas, secrets index, scheduler, Obsidian mirror, machine constraints
- [ORA PM App](reference_ora_pm.md) — ZeOoba/ora-pm (local `C:\Users\Owner\ora-pm`); 07-16 audit (3 criticals) + confidential-terms purge status
- [oxfordra.net Deploy Canon](reference_oxfordra_deploy_canon.md) — netlify-cli from website-canonical is THE path; ⚠ merging a PR to `main` auto-deploys to PROD — gate before merge, not after
- [Standards — Financial & Communication](standards.md) — Modeling conventions (DSCR 1.25×/LTV 40%) + comms tone by audience
- [Scheduled-Task Model Standard](reference_scheduled_task_model_standard.md) — standard = claude-sonnet-5; `[MODEL: …]` tag per task; CC/MCP model is observable but NOT settable (server-pinned)
- [CC Scheduler filePath Mechanism](reference_cc_scheduler_filepath_mechanism.md) — registry stores only `filePath`, not prompt text → editing a task's SKILL.md IS authoritative; specs are NOT git-versioned
- [Tenant Name Mappings](reference_tenant_name_mappings.md) — PM platform → Notion Tenant DB reconciliation aliases (operational data)
- [Property→LLC Signature Roster](reference_property_llc_signature_roster.md) — canonical property→signing-LLC lookup; fixes recurring Outbox QC Check-D (landlord mail signed with personal block)
- [ora-pm-ledger Double-Fire](reference_ora_pm_ledger_double_fire.md) — RESOLVED 2026-07-12: CC/MCP copy is the sole live registration; the LAMS "twin" was a misfiled orphan folder, never registered
- [QuickBooks & Entity Financials](reference_quickbooks_financials.md) — CloudVara RDP, .QBB un-parseable, where statements live, per-property P&L basis
- [Warehouse Basis Parsing](reference_warehouse_basis_parsing.md) — where each PM platform states accounting basis (QB Desktop = print header); accrual vs cash entities
- [Lean-RAM Toolkit](reference_lean_ram_toolkit.md) — RAM-saver commands (`ram`/`ora`/`heavy`/`handoff`/`solo`) + auto-park watchdog, retuned for 32GB; also the 07-11 terminal/VS Code rebuild
- [Claude Code Setups](reference_claude_code_setups.md) — best public CC setups (2026-06-06): obra/superpowers, Anthropic docs, disler hooks; steipete→agent-scripts
- [Skill Surfaces](reference_skill_surfaces.md) — skills split Code (plugins) vs Cowork (OneDrive); deal-lifecycle skills live on Cowork — not "missing" from CLI
- [Skill Home Loss 2026-07-09](reference_skill_home_loss_2026-07-09.md) — doctrine probe scan roots exclude the ora-skills repo; 4 skills lost their live `outputs/` home in the clone archival, restored 2026-07-10
- [Desktop Commander extension slow-init](reference_desktop_commander_extension_slow_init.md) — "Unable to connect to extension server" is usually a ~36s cold-start timeout, not a failure; re-enable, wait 60s
- [Desktop Commander PowerShell $var stripping](reference_desktop_commander_powershell_variable_stripping.md) — `start_process` silently strips `$variable` tokens from PowerShell `-Command`; use cmd.exe with literal paths
- [Desktop Commander nested-quote mangling](reference_desktop_commander_nested_quote_mangling.md) — nested `cmd.exe /c` quoting silently injected a leading space into a path arg; write it to a `.bat` and run that
- [Scheduled-Task Staleness-Guard False Positives](reference_scheduled_task_staleness_guard_trips.md) — case log for fail-loud staleness guards; check new trips here before re-diagnosing from scratch
- [Worktree node_modules Junction Hazard](reference_worktree_node_modules_junction_hazard.md) — never junction node_modules into a worktree then `worktree remove --force` (deletes through junction); use `npm run worktree`
- [GitHub Credential Path](reference_github_credential_path.md) — gh.exe-scoped helper overrides GCM for github.com; GCM `-c` fallback + API-token recipe; auth re-seed procedure
- [oxford-command-center Repo Health](oxford-cc-repo-health.md) — tombstones deleted + 24 stale branches pruned 2026-07-07; ~90 unmerged branches need a supervised pass
- [gate vs gate:ci divergence](feedback_command_center_gate_vs_gate_ci_divergence.md) — `gate:ci` runs a real `vite build` that `gate` skips; run `gate:ci` locally to catch build-only breaks
- [Piped gate exit masking](feedback_piped_gate_exit_masking.md) — `gate | tail` returns TAIL's exit code (masked 2 red gates 2026-07-16); redirect to file + `echo $?` when the exit code is the evidence
- [Command Center CRLF Hazard](reference_command_center_crlf_hazard.md) — CRLF blobs + autocrlf=true: script writeFileSync flips EOL and bloats diffs; prefer the Edit tool (EOL-preserving)
- [Shared-Checkout Co-File Patch Hazard](shared-checkout-cofile-patch-hazard.md) — `git diff -- <file>` scopes files not hunks; on a co-edited file it grabs the other writer's hunks too — inspect diff CONTENT before committing
- [session-env Retention Proposal](reference_session_env_retention_proposal.md) — PROPOSAL (unimplemented): age-gate `session-env\` (763 empty dirs, 150-350/day growth) per the `hooks\sessions\` precedent in `ora-nightly-disk.ps1`
- [WebFetch Markdown False Negatives](feedback_webfetch_markdown_false_negatives.md) — WebFetch's HTML→markdown strips `<head>`/`<script>`; false "no title/meta/schema" claims on SEO checks — verify via raw curl before trusting
- [workflows dir single-writer gap](reference_workflows_dir_single_writer_gap.md) — RESOLVED 2026-07-16: workflows/ now git-tracked (fa9da40); mtime sweep still catches in-flight edits
- [ECC Repo Flagged](reference_ecc_repo_flagged.md) — affaan-m/ECC rejected 2026-07-10: documented malware-clone risk + inflated star stats; redundant with the existing skill stack
- [Obsidian Copilot Keychain Migration Gap](reference_obsidian_copilot_keychain_migration_gap.md) — post-migration "Needs API key" on every model = empty per-machine secretStorage, not a vault bug; Gabriel must re-enter keys himself
- [NY Fed API 403 to Hosted Fetch](reference_newyorkfed_api_403_hosted_fetch.md) — NY Fed SOFR API 403s hosted fetch; 180d-avg+Index have no web_search fallback and go stale — pull locally via Desktop Commander
- [setup-writing-style Platform Skill](reference_writing_style_platform_skill.md) — real gated Claude/Cowork skill listed per-account (setup-writing-style vs my-writing-style); never on the filesystem, not an ora-skills defect

## Rules & governance
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run it proactively, before declaring done — caught 2 real defects first time (2026-07-14)
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts/ratification claims in prompts rot; refresh at runtime or tag `curated @` + VERIFY (proven 2x 2026-07-16)
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — two Workflow-tool hazards (stale name resolution, stringified args) -- verify result.worktree/agent roster post-run
- [Routines default model](feedback_routines_default_model.md) — all routines (schedule skill / CronCreate) default to claude-sonnet-5 unless told otherwise
- [Website work — always highest-intelligence model](feedback_website_model_tier.md) — Gabriel override (2026-07-09): opus for all oxfordra.net/website-canonical work, no sonnet/haiku dispatch
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — ChatGPT-drafted autonomy/"constitution" proposals merged selectively; Hard Invariants stay supreme
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, chip claim-lock §8, confidentiality §7a, permission regime §10, Edit/bash sync §11
- [Memory Policy](memory-policy.md) — Storage rules, naming, staleness, archival
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, tooling spend goes to the Claude/agent stack, not per-seat PropTech SaaS (Gabriel-approved)

---
*Index hygiene 2026-06-09 (monthly consolidation): the inline QuickBooks block was moved to [reference_quickbooks_financials.md](reference_quickbooks_financials.md) — the index holds pointers, not content. Scheduled-fleet count corrected 22 → **14 live** (observed via `list_scheduled_tasks`) in [tech.md](tech.md) §3 + [00_system_of_record.md](00_system_of_record.md) §7.*

*Index hygiene 2026-06-11 (Phase A remediation): the inline "2026-06-09 Deep folder sweep + Master WB findings" block was relocated to [reference_quickbooks_financials.md](reference_quickbooks_financials.md) — the index holds pointers, not content. Fleet roster is now REGISTRY-GENERATED into `~/.claude/session-context.md` (registry-membership-probe.py, daily) — never hand-edit counts here or anywhere.*

*Scope merge 2026-07-08: this index absorbed the `--1-`-scope index verbatim (all link targets now resolve locally — every source file was copied alongside this merge) plus this session's own 6 pre-existing entries. No content was dropped or overwritten; nothing in the `--1-` scope was deleted.*

*Index consolidation 2026-07-14: collapsed all 15 over-length index hooks (>150 chars) plus the oversized scope blockquote down to one-line pointers — doctrine-probe over-length count 15 → **0**, total warnings 17 → 2. No content was lost: every trimmed detail was verified present in its linked file first. Side finding while checking the dated [Owner-Outreach Stale-Guard Watch](project_owner_outreach_stale_guard_watch.md): its watched 2026-07-13 fire DID re-trip the guard, but as a **true** positive (33-day content staleness) — watch closed, [Case 2](reference_scheduled_task_staleness_guard_trips.md) logged, and an unanswered QUESTIONS-FOR-GABRIEL email is holding Notion promotions until the off-market master is refreshed.*

*Monthly consolidation 2026-07-12: archived the stale `composio-ora` config detail out of [tech.md](tech.md) into `_archive/reference_composio_ora_config_historical_2026-07-12.md`; added a live-registry drift-check note in tech.md §3 (LAMS = 20 tasks, expected growth not drift); confirmed no retired connector (Rube/Composio/Zapier/Gmail) is mis-stated as active anywhere; confirmed OXFORDRA_REPO resolves; doctrine/governor audit logged in [event_log.md](event_log.md) (clean, no overrides). Full detail in event_log.md.*

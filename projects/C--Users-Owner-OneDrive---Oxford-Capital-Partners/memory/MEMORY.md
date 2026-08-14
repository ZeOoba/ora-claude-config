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
- **OPEN/BLOCKED:** [broker OM intake BROKEN in prod 08-04](project_broker_pipeline_blobs_v1_outage_2026-08-04.md) (V1 fns can't auto-provision Blobs; PR #64 ≠ fixed; no data lost) · [open-items-tracker worktree/HEAD divergence 07-20](project_open_items_tracker_worktree_head_divergence.md) (don't force-resync) · [event_log IWNS block loss](project_event_log_iwns_block_loss_unattributed_2026-07-21.md) (recovered; cause open)
- **PLANNED, awaiting Gabriel:** [acquisition-underwriting doctrine review](project_acquisition_underwriting_doctrine_review_2026-07-18.md) (9 items) · [artifact-content top-5](project_artifact_content_top5_plan_2026-07-18.md) · [setup-improvement top-5](project_setup_improvement_top5_plan_2026-07-18.md) + [Plan 2 design](project_plan2_effect_verification_design_2026-07-18.md)
- [oxfordra.net SEO Audit](project_oxfordra_seo_audit_2026-07.md) — 84/100; open: portfolio SF/counts, FAQ order, /markets redirect
- [Claude Env Architecture Baseline 07-29](project_claude_env_architecture_baseline_2026-07-29.md) — official forensic baseline; optimization NOT yet approved
- [CC Build State](cc-build-state.md) — PR #200-204 merged; HUBSPOT_TOKEN needed (OI-019)
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — merged; open B2/B3/B5
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — SUPERSEDED, Financial-Intel phases all shipped
- [Intelligence Platform Roadmap — RATIFIED 07-29](project_intelligence_platform_roadmap_ratified_2026-07-29.md) — merged [PR #246](https://github.com/ZeOoba/oxford-command-center/pull/246); Phase 0 kickoff (IP-0.1–0.10) is next open action
- [Engineering Constitution — RATIFIED 07-29](project_engineering_constitution_ratified_2026-07-29.md) — merged [PR #247](https://github.com/ZeOoba/oxford-command-center/pull/247); governs roadmap/ADRs unless amended; Phase 0 kickoff still next
- [PFI Build Canon](pfi-build-canon.md) — ratified 14-unit roster, PM assignments, accounting rulings
- [PFI Warehouse Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra; Cowork round-trip unreachable from Code, no gate sign-off
- [brain.oxfordra.net Access](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is a DEAD END
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — "never pulls" FIXED (PR #192); open: kill-class alerting blind spot, PR #248
- [Mirror Deploy 0xC000013A is usually benign](reference_mirror_deploy_0xc000013a_is_usually_benign.md) — run the classifier; duration is not a detector; the script can't self-report a kill
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — live on 2 repos; #7 awaits sign-off
- [oxford-cc worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree
- [portfolio.json generatedAt churn](reference_portfolio_json_generatedat_commit_churn.md) — RESOLVED 07-27; dirty ≠ lease data changed
- Setup audits: [07-09](project_claude-setup-audit-2026-07-09.md) (migration CLOSED; 15/21 resolved) · [07-16](project_claude-setup-audit-2026-07-16.md) (G1-G8 done; chip TERMINAL, needs Gabriel)
- [eos-review-gate shipped](project_eos_review_gate_shipped_2026-07-24.md) — blast-radius commit review gate, `c53c69c`
- **⚠️ [Run-once guard EXISTS as block-sentinel.py](reference_run_once_guard_is_block_sentinel_not_run_once_guard_ps1.md)** — shipped 08-09 (PR #39/#40); NOT `run-once-guard.ps1`, exits are 10/11/12 not 3/4. Re-specced from scratch once already — verify before building
- [Governor-LTV remediation PR #233](project_governor_ltv_remediation_2026-07-24.md) — 11 shipped; OPEN: debt-scoring per-property ltv gap + silent-refusal reload path
- [Northwood/EGFLLC loan miscategorized 07-27](project_northwood_egflc_loan_miscategorized_2026-07-27.md) — RESOLVED 08-03; workbook LTV cells now correct, stop applying the manual back-out
- CLOSED (detail in each file): [Tenant DB renewal-watch view](project_tenant_db_renewal_watch_view_2026-07-22.md) · [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) · [orphan-guard timing](project_orphan_guard_timing_2026-07-24.md) · [autonomy-gate indirection ceiling](project_autonomy_gate_indirection_ceiling_followup.md) · [bash-guard indirection gap](project_bash_guard_indirection_gap.md) · [owner-outreach stale-guard](project_owner_outreach_stale_guard_watch.md) · [Lighthouse perf/CSP](reference_oxfordra_lighthouse_csp_fix_2026-07-21.md)

## Markets
- [Market Intelligence](markets.md) — cross-market snapshots, macro (FRED), replacement cost, comps
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of replacement
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE + buy-box rule validated
- [Disposition & Exit Ledger](disposition-ledger.md) — POST-acquisition lifecycle: ACQUIRED/HOLD/REFI/1031/SALE per owned asset; 13 deals + 1100 Rarig HOLD backfilled 07-29
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store DG net-lease + cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — basis/NOI/cost-seg; open gaps in file
- [Historical Evaluations acquisition review 07-29](project_historical_evaluations_acquisition_review_2026-07-29.md) — 13-deal price/NOI table; 2 LTV exceptions accepted; 2 open date discrepancies
- [entry-market-scan defects 08-04](reference_entry_market_scan_defects_2026-08-04.md) — `Gate Review` field CREATED 08-04; blank = awaiting Gabriel, never placeholder it
- [5515 Catfish Court broker-correspondence claim is FALSE](reference_catfish_court_broker_correspondence_claim_false.md) — Sullivan thread exists; 08-14 re-check is a warm follow-up, not a cold call
- [Delinquency collection-status blind spot](reference_delinquency_report_collection_status_blindspot.md) — "no action taken" is inferred; wrong for 4 of 6 tenants 07-24
- [Columbus Suburban default/vacate 07-28](tenant_columbus_suburban_default_2026-07-28.md) — ORA-T-105 gone; $20,457 owed, PM misspells name "Suburan"; vacate ≠ contract expiry
- [Rent-roll vacancy convention changed 08-01](reference_rent_roll_vacancy_convention_change_2026-08-01.md) — occupancy 98.6%→94.9% is definitional, not deterioration
- [parseLeases vacancy-block phantom leases](reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md) — parser FIXED (PR #250, `d35931a`); PR #251 (`d705a3f`) added a CI-gate check, NOT the write-path wiring — fleet writes stay suspended
- [CC snapshot is TRACKED, not ignored](reference_command_center_snapshot_is_tracked_not_ignored.md) — auto-committed unattended; the task file's "git-ignored" claim is wrong
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — split on `Row Retired`, not the ⛔ARCHIVED prefix
- [Lease-date detector defects 07-24](reference_lease_date_detector_defects_2026-07-24.md) — PR #232 merged; diff by business key not id
- [HubSpot missed the 07-16 lease-date correction](reference_hubspot_missed_lease_date_correction.md) — HubSpot never fixed; J&R live conflict
- [Insurance lapse confirmed REAL 07-25](project_insurance_lapse_confirmed_real_2026-07-25.md) — 5 properties expired/cancelled, 3 with no plan
- [Master Lease landlord entity states 08-03](project_masterlease_landlord_entity_states_2026-08-03.md) — MD/MO entities sourced; Baqir/Baquir + 13B/B13 open
- [Master Lease next-rev upstream notes](reference_masterlease_next_rev_upstream_notes.md) — typo RESOLVED in v2.4.1; heading fragmentation still open
- [Master workbook no single-writer 07-24](project_master_workbook_no_single_writer_2026-07-24.md) — OPEN: uncoordinated concurrent edits
- [Master workbook single-writer proposal 07-25](project_master_workbook_single_writer_proposal_2026-07-25.md) — RATIFIED; text now [tech.md](tech.md) §3d
- [Cash Data excludes PM-held accounts](reference_cash_data_excludes_pm_held_accounts.md) — negative balance is usually tax-timing, not distress

## Reference
- [settings.json enabledPlugins/skillOverrides attribution](reference_settings_json_enabledplugins_skilloverrides_attribution_2026-08.md) — 08-09's "not investigated" was wrong; both collapses are git-attributed (a0e95bf, 165fff3)
- **→ [Reference sub-index](INDEX_reference.md)** — 108 pointers: tooling & paths, standards, fleet/scheduler gotchas, skill gotchas, Notion gotchas, workflow gotchas, git & shared-checkout hazards, event_log hazards, Windows/shell gotchas, Command Center, hooks & guards, verify-before-trusting. **Not auto-loaded — open it before debugging any tooling failure or assuming a gotcha is unrecorded.**
- [SKILL.md frontmatter is deliberately NOT strict YAML](reference_skill_frontmatter_lenient_parse.md) — the harness parses line-wise, so ~97/147 fleet SKILL.md fail `yaml.safe_load` **by design**; do NOT mass-quote descriptions to satisfy a parser the harness doesn't use. Promoted out of the sub-index 2026-08-05 after a **2nd recurrence** — a session raised it as a fresh "pre-existing defect" despite the memory existing, because the sub-index isn't auto-loaded. `setup-self-audit.py` already prints "not a strict YAML parse", but that only helps a session that runs the probe rather than its own `yaml.safe_load`

## Rules & governance
- [Standing Rules & Preferences](rules.md) — working-style, Outlook-only email, QB Desktop, Netlify, CSP, confidentiality
- [Memory Policy](memory-policy.md) — storage rules, naming, staleness, archival
- [CLAUDE.md word budget is a FLOOR](reference_claude_md_word_budget_is_a_floor.md) — 1700 WARN ≠ ceiling; real gate is FAIL 1850. Don't trim in the 1694–1755 band
- [Procurement Stance — Deepen, Don't Migrate](procurement-stance-deepen-not-migrate.md) — below $150M AUM, spend goes to the Claude stack
- [Interactive decision questions](feedback_interactive_decision_questions.md) — every ruling → multiple-choice + researched recommendation
- [Verified null vs inferred null](feedback_verified_null_vs_inferred_null.md) — a zero that could mean "couldn't look" is a FAILURE
- [Absence claims need verification before building](feedback_absence_claims_need_verification_before_building.md) — "nothing checks X" usually means it exists but is disconnected; grep before you build
- [Refute pass — proactive by default](feedback_refute_pass_proactive_default.md) — run before declaring done
- [REFUTE differential harness](reference_refute_differential_harness.md) — guard/probe regex edits: old-vs-new differential battery; judge deltas, not absolutes
- [Verify before repeating session claims](feedback_verify_before_repeating_session_claims.md) — check ground truth before relaying
- [skillOverrides is ignored for plugin skills](reference_skilloverrides_ignored_for_plugin_skills.md) — any key with `:` is inert by construction; disable the plugin, not the skill
- [Browser pane is 0x0 until resized](reference_browser_pane_zero_viewport_blocks_images.md) — "screenshots impossible" is usually an unresized pane; 9/9 agents got this wrong
- [Findings decay — re-check before WRITING](feedback_findings_decay_recheck_before_writing.md) — minutes-long shelf life on shared files; waiting beat intervening 4/4
- [Artifact citation requirement](feedback_artifact_citation_requirement.md) — Resolved/Closed claims need a citation
- [Session-retro evidence rule](reference_session_retro_evidence_rule.md) — retros need citation + null-result path or they fabricate
- [Prompt-embedded current-state prose](feedback_prompt_current_state_prose.md) — baked shas/counts/aging anchors rot, in data fields too; an anchor belongs in a computed field or nowhere
- [Workflow invocation gotchas](feedback_workflow_invocation_gotchas.md) — stale name resolution + stringified args
- Model tiers: [routines = sonnet-5](feedback_routines_default_model.md) · [oxfordra.net = opus always](feedback_website_model_tier.md) (Gabriel override) · [Agent `model:` pin can fall back mid-run](feedback_agent_model_pin_not_held_end_to_end.md) — verify the transcript, don't assume
- [External AI Governance Proposals](feedback_external_ai_governance_proposals.md) — merged selectively; Hard Invariants supreme
- [Auto-review blast-radius gate](feedback_auto_review_blast_radius_gate.md) — 07-24: blocking for hooks/financial code; needs an AgentTool carve-out
- [Artifact staleness scan false positives](feedback_artifact_staleness_scan_mtime_false_positives.md) — mtime can't measure a live-read artifact; LIVE/FROZEN/HYBRID convention
- [Sweep-then-verify](feedback_sweep_then_verify.md) — grep-inventory before multi-instance edits, re-grep after to prove zero remain

---
*Index holds pointers, not narration — history in [event_log.md](event_log.md).*

*Size gate RECALIBRATED 2026-07-31 (Gabriel): WARN 17.1KB → 21.5KB. The old target was unsatisfiable — stripping every hook floors this file at 15.2KB, so 17.1KB allowed ~10 chars of description per entry, and the only alternative was deleting ~30 live pointers. Both 07-28 blockers re-verified and still true: archiving the CLOSED entries orphans inbound refs in other memory files, and a sub-index fails check 1. Rationale + measurements: [Memory index size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).*

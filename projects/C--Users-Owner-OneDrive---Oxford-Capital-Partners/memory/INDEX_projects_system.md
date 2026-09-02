---
name: index-projects-system
description: "Sub-index of MEMORY.md — projects & system pointers (audit revisions, oxfordra.net, Command Center, platform/governance, PFI, landed work). Split out 2026-08-16; MEMORY.md links this file, and memory-integrity-probe check 1 follows it one level."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 16c5371f-037c-41a7-907c-504cc9671b5b
  modified: 2026-08-22T21:58:56.573Z
---

# ORA Memory Index — Projects & System

> **Sub-index of [MEMORY.md](MEMORY.md).** Split out 2026-08-16: the root index was ~1.7KB from the 24.4KB Read-tool hard limit and this section was 9,093 B / 46 entries — the largest by more than the next two sections combined. These pointers are NOT auto-loaded into every session the way the root index is — read this file before starting project, audit, website, or Command Center work rather than assuming no prior finding exists.
>
> **What stayed in the root index, deliberately:** navigational anchors (System of Record, Event Log, Open Items Tracker, Ops Decision Log, Active Projects), everything OPEN/BLOCKED or PENDING, the two standing operational constraints (⛔ Northwood debt reporting, ⚠️ run-once guard), the open governor-LTV gap, and the newest audit revision. Anything that must be seen *without* opening a file was not moved.
>
> Same rules as the root index: one line per entry, pointers only, never content. Detail lives in the target file. Rationale for the split: [size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).

## Automation / setup audit revisions
- [Automation Audit Rev 18 08-22](project_automation_audit_rev18_2026-08-22.md) — MEMORY.md 266B from hard ceiling; event_log 35d unrolled; superseded by Rev 20
- [Automation Audit Rev 17 08-21](project_automation_audit_rev17_2026-08-21.md) — LAMS resume would have resurrected the retired passed-deal-tracker twin; fixed pre-fire
- **[Automation Audit Rev 12 08-16](project_automation_audit_rev12_2026-08-16.md)** — both Rev 9 data-quality items REFUTED: capex-budgeting never republished (repo commit ≠ store publish); `@inline` store plugins never appear in `enabledPlugins`, so that test proves nothing
- **[Automation Audit Rev 11 08-16](project_automation_audit_rev11_2026-08-16.md)** — narrow follow-up, not full-fleet; README HOOKS→MAINT diagram edge + 7-file `.gitignore` churn fix, both executed; not yet PR'd to main
- **[Automation Audit Rev 10 08-14](project_automation_audit_rev10_2026-08-14.md)** — first UNATTENDED run; it loaded a STALE v1.2 copy of its own skill (repo is v1.3); eval-harness dirties `ora-skills` daily; 3 zero-plugin marketplaces
- [Rev 9 remediation FULLY CLOSED 08-15](project_audit_rev9_remediation_landed_2026-08-14.md) — splits reimported live; capex-budgeting + 5 siblings confirmed Removed via Claude in Chrome
- [Automation Audit Rev 9 08-14](project_automation_audit_rev9_2026-08-14.md) — skills-only: usage ranking, top-skill token recs, 49-skill zero-usage tail sorted keep/ask; first rev under the new 4-band cap
- [Automation Audit Rev 8 08-14](project_automation_audit_rev8_2026-08-14.md) — FULLY CLOSED
- [Automation Audit Rev 7 08-13](project_automation_audit_rev7_2026-08-13.md) — 5 findings (schematic bloat, fleet, plugins, routing); none executed, all pending sign-off
- Setup audits: [07-09](project_claude-setup-audit-2026-07-09.md) (CLOSED) · [07-16](project_claude-setup-audit-2026-07-16.md) (chip TERMINAL, needs Gabriel)
- [Claude Env Architecture Baseline 07-29](project_claude_env_architecture_baseline_2026-07-29.md) — forensic baseline; optimization NOT yet approved

## oxfordra.net
- [oxfordra.net SEO Audit](project_oxfordra_seo_audit_2026-07.md) — 84/100; open: portfolio SF/counts, FAQ order, /markets redirect
- [oxfordra.net LCP render delay 08-12](project_oxfordra_lcp_render_delay_2026-08-12.md) — forced-reflow FIXED + live (PR #66); OPEN residual: ~1s@8x Layout cost persists
- [oxfordra.net desktop Perf 98 not 100 08-13](project_oxfordra_desktop_perf_98_not_100_2026-08-13.md) — scoring-curve residue, not a defect; CLS culprit unidentified

## Command Center & infrastructure
- [CC Build State](cc-build-state.md) — PR #200-204 merged; HUBSPOT_TOKEN needed (OI-019)
- [CC Autonomous Audit — PR #28](cc-autonomous-audit-pr28.md) — merged; open B2/B3/B5
- [Command Center Mirror Deploy Gap](reference_command_center_mirror_deploy_gap.md) — "never pulls" FIXED (PR #192); open: kill-class alerting blind spot, PR #248
- [Mirror Deploy 0xC000013A is usually benign](reference_mirror_deploy_0xc000013a_is_usually_benign.md) — run the classifier; duration is not a detector
- [oxford-cc worktree gotchas](project_oxford-command-center_worktree_gotchas.md) — WORKBOOK_PATH not inherited per-worktree
- [portfolio.json generatedAt churn](reference_portfolio_json_generatedat_commit_churn.md) — RESOLVED 07-27; dirty ≠ lease data changed
- [AAOS Agent Coordination Layer](project_aaos_agent_coordination_layer.md) — real infra; Cowork round-trip unreachable from Code
- [brain.oxfordra.net Access](brain-oxfordra-access-finding.md) — LIVE via Pages mirror; tunnel path is a DEAD END
- [GitHub CI Auto-Fix Rollout](github_ci_autofix_rollout.md) — live on 2 repos; #7 awaits sign-off

## Platform & governance
- [Intelligence Platform Master Plan](ora-intelligence-platform-master-plan.md) — SUPERSEDED
- [Intelligence Platform Roadmap — RATIFIED 07-29](project_intelligence_platform_roadmap_ratified_2026-07-29.md) — merged [PR #246](https://github.com/ZeOoba/oxford-command-center/pull/246); Phase 0 kickoff next
- [Engineering Constitution — RATIFIED 07-29](project_engineering_constitution_ratified_2026-07-29.md) — merged [PR #247](https://github.com/ZeOoba/oxford-command-center/pull/247); governs roadmap/ADRs
- [eos-review-gate shipped](project_eos_review_gate_shipped_2026-07-24.md) — blast-radius commit review gate, `c53c69c`

## PFI
- [PFI Build Canon](pfi-build-canon.md) — ratified 14-unit roster, PM assignments, accounting rulings
- [PFI Warehouse Backlog](pfi-warehouse-systematization-backlog.md) — 3 queued basis-recovery follow-ups

## Recently landed
- ✅ [ora-skills PR #48 — shared ora_doc_qc module, MERGED 08-18](project_ora_doc_qc_shared_module_pr48_2026-08-17.md) — unifies pma-qc/listing-agreement-qc/lease-form-qc extraction, closes false-clean + T1-spurious-BLOCK bugs
- ✅ [lease-addendum cache/repo orphaned-branch divergence, RESOLVED 08-21](project_lease_addendum_cache_orphaned_branch_2026-08-21.md) — PR #48's shared-module pattern also applied to lease-addendum on a branch that never merged; ran 4 days CACHE-AHEAD/DIVERGENT until a same-day fleet pass merged it (`ab6ce5d`, `92fdd41`)
- ✅ [governor-drift-probe LTV 65%/40% split false positive](project_usage_report_horizon_builds_scoped_2026-08-21.md) — LANDED 08-22 (`c7875a5`)
- [Live checkout 132 behind 08-15](project_live_checkout_132_behind_settings_json_overlap_2026-08-15.md) — SUPERSEDED 08-16: the 132-commit gap closed; kept for the settings.json conflict-class lesson
- [Workflow-optimizations punch list 08-21 resolution](project_workflow_optimizations_2026-08-21_resolution.md) — 1 already fixed elsewhere (discarded dup), 1 shipped on branch awaiting merge, 1 filed not fixed, 2 investigation/memory-only
- [county-sales-monitor skill draft 08-15](project_county_sales_monitor_skill_draft_2026-08-15.md) — v0.2 DRAFT; cadence/delivery/scope ratified (monthly, Notion DB, Tier A only, Louisville deferred); pilot build not started
- [Dangling worktree landing 08-15](project_dangling_worktree_landing_2026-08-15.md) — CLOSED: PRs #110/#112/#113/#114 merged, 2 others already-landed-elsewhere; settings.json dupe-registration collision found+fixed, PR #105 now CLEAN
- [Multi-repo triage landed 08-15](project_multirepo_triage_landed_2026-08-15.md) — 4-repo dirty/PR/worktree sweep; 3 oxford-command-center PRs landed, 17 stale worktrees/branches removed, 0 open PRs left anywhere
- [isolated_commit.py repair wrapper](reference_isolated_commit_repair_wrapper_2026-08-13.md) — LANDED 08-13
- [Acquisition-underwriting eval harness — PILOTED + scheduled 08-14](reference_skill_eval_harness_gap_2026-08-14.md) — merged `ora-skills` main; poll registered (`ora-acquisition-underwriting-eval-harness`)

## Closed
- CLOSED (detail in each file): [Deal-join id-based redesign](project_deal_join_id_based_redesign_queued_2026-08-12.md) ([PR #273](https://github.com/ZeOoba/oxford-command-center/pull/273)) · [acquisition-underwriting doctrine review](project_acquisition_underwriting_doctrine_review_2026-07-18.md) · [Tenant DB renewal-watch view](project_tenant_db_renewal_watch_view_2026-07-22.md) · [Tenant DB sync](project_tenant_db_no_sync_rootcause.md) · [orphan-guard timing](project_orphan_guard_timing_2026-07-24.md) · [autonomy-gate indirection ceiling](project_autonomy_gate_indirection_ceiling_followup.md) · [bash-guard indirection gap](project_bash_guard_indirection_gap.md) · [owner-outreach stale-guard](project_owner_outreach_stale_guard_watch.md) · [Lighthouse perf/CSP](reference_oxfordra_lighthouse_csp_fix_2026-07-21.md)

---
*Sub-index holds pointers, not narration — history in [event_log.md](event_log.md). Back to [MEMORY.md](MEMORY.md).*

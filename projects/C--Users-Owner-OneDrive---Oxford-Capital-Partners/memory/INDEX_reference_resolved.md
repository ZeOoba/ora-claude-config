---
name: index-reference-resolved
description: "Sub-index of MEMORY.md — RESOLVED/CLOSED reference findings and dated one-off gotchas, kept for the citation trail. Split out 2026-09-02 when INDEX_reference.md crossed the 24.4KB Read-tool limit."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0fc18634-d92f-4211-8be2-5903fcf2975f
  modified: 2026-09-12T21:57:59.014Z
---

# ORA Memory Index — Reference (resolved / closed)

> **Sub-index of [MEMORY.md](MEMORY.md).** Split out 2026-09-02: the 2026-09-02 root-index relocation pushed [INDEX_reference.md](INDEX_reference.md) to 25,039 B, over the 24,400 B Read-tool limit. Everything here is CLOSED, RESOLVED, or a dated one-off — consult for citations, not for live hazards (those stay in the root index and INDEX_reference.md).
>
> Same rules as the root index: one line per entry, pointers only, never content. Rationale: [size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).

## Resolved / closed reference findings (previously inline in INDEX_reference.md)


## Relocated from the root index 2026-09-02 (root crossed its 21,500-byte runway marker; moved verbatim, newest-first as they sat in MEMORY.md)
- **[Machine clock on UTC+2 — RESOLVED 09-05](reference_machine_clock_utc_plus_2_fleet_shift_2026-09-02.md)** — skew window was 09-02→09-05 only (host back on Eastern); read host-local stamps inside it as UTC+2. Rule survives + was vindicated: check Get-TimeZone before calling a fire time odd; flag, never retime *(relocated 2026-09-12, same runway-marker reason)*
- **[debt-scoring.ts JV-debt basis CONFIRMED 08-22](reference_debt_scoring_oxfordnoi_basis_conservative_not_correct_2026-08-22.md)** — 9cb6169 verified vs live workbook, not just conservative
- ✅ [1900 Broadway insurance fix + BCL relabel 08-28](reference_1900broadway_insurance_fix_and_collapsetocurrentterm_tiebreak_2026-08-28.md) — warehouse AND live workbook both fixed (Gabriel confirmed the write); **fully CLOSED 09-02** — the scheduled portfolio.json re-extract landed both fixes in the snapshot the Daily Brief reads
- **[claim_work.py --paths is space-separated, not comma 08-24](reference_claim_work_paths_comma_vs_space.md)** — a comma-joined value silently becomes ONE bogus path, no error; `covering N path(s)` in the output is the tell
- ✅ **[CC snapshot shrink guard widened to all top-level keys, CLOSED 08-24](reference_cc_snapshot_shrink_guard_covers_lists_only.md)** — root cause (`6b9b507`) + guard gap (`bcda1fc`) both fixed; generic populated→empty/null check now covers any future server-attached section
- ⚠️ **[Rate Snapshot fetched_at 7-day stale 08-24](reference_rate_snapshot_fetched_at_7day_stale_2026-08-24.md)** — ora-sofr-direct-prefetch found ora-am-brief's header stamp still 08-17 on 08-24; a persistent multi-day gap, not the documented same-burst ordering race. §2 patched; §1/3/4 untouched (not this task's scope)
- ✅ **[Rev 10 remediation efficacy — CLOSED 08-26](reference_rev10_efficacy_2026-08-20.md)** — the lone FAIL (R10-4) is closed: `ora-psa-drift-watch` fired 08-26 13:50 ET on its first unobstructed slot after the 08-17→08-21 pause, exercising the Rev 7 retime (`45 13 * * 3`). Do not re-open. Marketplaces, eval-harness runs/, ora-setup-audit mirror parity all PASS
- **[Tax & Basis Register entity EINs + 1031 exchange index 08-17](reference_tax_settlement_entity_and_exchange_index_2026-08-17.md)** — 6 entity EINs, EX-12-*/IPX exchange numbers 2015-2026; 5 priority-1 findings filed as [OI-189](open-items-tracker.md#OI-189)-[OI-193](open-items-tracker.md#OI-193)
- **["Metrics History"/Category 4a/4b doesn't exist 08-17](reference_metrics_history_pattern_does_not_exist_2026-08-17.md)** — tax data's home is `property_tax_assessments`
- **[DISABLE_AUTOUPDATER also breaks manual `claude update` 08-16](reference_disable_autoupdater_blocks_manual_update.md)** — fails with a false "npm registry unreachable"; registry was fine. Use `env -u DISABLE_AUTOUPDATER claude update`
- **[memory/ missing from single-writer list 08-14](reference_memory_dir_not_in_single_writer_list_2026-08-14.md)** — flagged for next `ora-setup-audit`, not fixed ad hoc; found via external-artifact review
- **[ora-skills "full claim protocol: tech.md §2" pointer is stale 08-14](reference_ora_skills_claim_protocol_pointer_stale_2026-08-14.md)** — only the git-log-diff check exists, no `claim_work.py`-style system; flagged for next `ora-setup-audit`
- [Alert-engine "duplicate" emails 08-11](reference_alert_engine_duplicate_emails_diagnosis_2026-08-11.md) — `bytes=` in the send log is the discriminator. Also: `property_insurance_policies.property_id` holds POLICY slugs, matching 0 of 14 properties
- [ora-session-sweep LAMS registry gap 08-11](reference_ora_session_sweep_lams_registry_gap.md) — OI-121, OPEN: `list_scheduled_tasks` saw CC/MCP only
- **[AM-cluster late wake root cause 08-13](reference_am_cluster_late_wake_root_cause_2026-08-13.md)** — WU reboots killed the app ~33min pre-slot; logon entry existed but had a dead MSIX path — FIXED 08-27. Not sleep config
- **[Acquisition Pipeline uniform-stamp + detector BUILT 08-16](reference_acquisition_pipeline_uniform_stamp_2026-08-16.md)** — all 6 A.1 sources now covered; `⏰ Action Overdue` trap; **scheduled-task files are gitignored — `git add -f` or they go unbacked**
- **[automation-health-monitor repo copy is NOT live 08-16](reference_automation_health_monitor_repo_copy_is_not_live_2026-08-16.md)** — ora-skills copy is v1.5/137 lines, LIVE Scheduled\ copy is v1.24/353 lines; ENTIRE file differs. Edit the Scheduled\ copy. Also: scheduled-task registries store NO description field, so there is no desync risk there (contradicts the older general note)
- [check-open-items ignores its path arg](reference_check_open_items_ignores_path_arg.md) — takes NO args, always reads the canonical tracker while PRINTING the path you passed
- [OI-140 CLI-arg fix — COMMITTED fe14d91 (PR #136), OI-140 closed 09-19](reference_oi140_check_open_items_duplicate_ids_cli_fix_2026-08-13.md) — the fix for the line above: check-open-items-duplicate-ids.py now REJECTS any CLI arg (exit 2) instead of silently checking the canonical tracker

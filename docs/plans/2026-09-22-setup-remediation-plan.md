# ORA Setup Remediation Plan: Automation Audit Revision 27

**Goal:** remove redundancy and context cost, and add the missing market-intelligence store, **without losing any capability**.
**Source:** Automation Audit Revision 27 (https://claude.ai/artifact/JBgJjqcCckM3pUeEp2vtQE) · memory `project_automation_audit_rev27_2026-09-22.md`.
**Order of operations:** baseline first (Phase 0), then lowest risk to highest. Each phase ends on a verification gate. A phase that fails its gate rolls back, and nothing downstream starts.

## Operating rules (apply to every phase)

1. **Capability ledger = regression oracle.** Before any consolidation, every skill, agent, task, hook and connector is listed with the capability it provides. After each phase, every ledger row must map to a surviving component. A row with no home blocks the phase.
2. **Consolidate by shadow, never by swap.** A new merged task or hook runs alongside the old ones for 2 cycles, with outputs diffed. Old components are PAUSED (not retired) until parity is shown, then retired archive-first per `register-scheduled-task`.
3. **Single-writer.** Every edit to `~/.claude`, `ora-skills` or `oxford-command-center` runs `preflight-shared-checkout.py`, a `claim_work.py` claim, and an isolated worktree. Two live claims at plan time: `hooks-override-auth` (session c4cd2d5a) and `repo-housekeeping` (f3aeafca). Phases touching those scopes wait or coordinate.
4. **Blast-radius items need Gabriel's go per item:** hooks, settings.json, CLAUDE.md, registries, governor code. Invariants 1–7 are unchanged; nothing here touches DSCR/LTV constants or confidential-terms.
5. **Evidence before claim.** Each gate is a command whose output is cited, never a narrative.
6. **Dispatch:** implementers on Sonnet; reviewers at Opus or above (reviewer ≥ implementer); warehouse and financial code gets a Fable REFUTE pass.

---

## Phase 0: Safety baseline (no changes)

| Step | Action | Output |
|---|---|---|
| 0.1 | Tag rollback points: `git tag pre-r27-<date>` in `~/.claude`, `ora-skills`, `oxford-command-center`, `ora-pm`. Copy `finance.sqlite` to `archive/` | 4 tags + DB copy |
| 0.2 | Green baseline: hook test suite, `doctrine-integrity-probe`, `governor-drift-probe`, `memory-integrity-probe`, `state-freshness-probe`, `frontmatter_sweep`, mirror check, occ CI, ora-pm CI | Baseline log in `_state/r27-baseline/` |
| 0.3 | Fleet snapshot: `fleet-status.py` read-only, plus a copy of both registries | Pre-change membership |
| 0.4 | Build the capability ledger (CSV: component, type, capability, callers, surface) from skills, agents, task specs, hooks, and settings.json allow entries | `r27-capability-ledger.csv` |
| 0.5 | Latency baseline: time 20 trivial Bash calls with the current hooks | ms per call |
| 0.6 | Wait for the 09-28 fleet resume to complete. Phases 3 and 6 need a live fleet to shadow-test | — |

**Gate:** all suites green, or pre-existing failures recorded as known. Ledger complete.

## Phase 1: Zero-capability-risk hygiene (small, reversible)

| # | Item | Change | Verify | Rollback | Gabriel? |
|---|---|---|---|---|---|
| 1.1 | R26-2 store lag | Gabriel imports the already-packaged `acquisition-underwriting` v4.22 / `register-scheduled-task` v2.26 `.skill` files | `ListSkills`: store = repo on all canaries; listing descriptions carry no version text | Re-import prior version | **Click** |
| 1.2 | R27-4 cadence mismatch | Read both registries; decide the intended cron for `ora-memory-commit-sweep` and `ora-pm-ledger`; fix via `update_scheduled_task` or regenerate the roster | Roster and live agree | Revert cron | Yes (registry) |
| 1.3 | 4 same-minute collisions | Re-time the second task of each pair +5 min (10:40, 10:50, 12:10, 15:00) | `fleet-status` shows 0 collisions; throttle skips trend down over 2 weeks | Restore crons | Yes (registry) |
| 1.4 | Disabled plugins | Remove `code-review` and `commit-commands` from `installed_plugins`/`enabledPlugins`; archive their cache | Ledger: native `/code-review` still covers review (the tie-break already routes there) | Reinstall | Yes (settings) |
| 1.5 | excel MCP breadth | Grep skills and tasks for `mcp__excel__write/create/apply/...`. If none, narrow the allow to `get_workbook_metadata`, `read_data_from_excel` and `validate_*` | Scouts still read; `model-bulk-edit` still uses COM | Restore wildcard | Yes (settings) |
| 1.6 | blocklist.json | Refresh (auto-fetched by the harness; confirm the timestamp moves) | Timestamp current | n/a | No |
| 1.7 | Duplicate surfaces | For each of the OneDrive `(1)` mount, `oxford-command-center-deploy-build`, 4 `*-wt-*` worktrees and `_CLAUDE_REVIEW_DELETE_`: check git status, unpushed commits and any path reference in tasks, hooks or skills. Clean and unreferenced → move to `_archive-non-onedrive/`. `git worktree prune` only after the move | grep shows 0 references; tasks still resolve paths | Move back | Yes (per item) |

**Gate:** Phase 0 suites still green; ledger unchanged.

## Phase 2: Context layer (relocate, never delete)

| # | Item | Change | Verify |
|---|---|---|---|
| 2.1 | CLAUDE.md 1,843/1,850 | Keep every tie-break as a one-liner (the probe needs the skill names inline). Move parentheticals (lease-addendum's module list, the comms letter-vs-email rationale, debugging autonomy detail) to `rules.md §Routing`, with a pointer. Target ≈1,650w | `doctrine-integrity-probe` passes; Check 11 guard names intact; 34/34 references resolve |
| 2.2 | session-context.md | Move stable procedure (claim_work syntax, registry single-writer, RETIRE order, OI allocation) to `rules.md §14` and `register-scheduled-task`. Leave one-line pointers; keep volatile state | ≤20 lines; `session-context-xref-probe` clean; SessionStart output shrinks |
| 2.3 | Second memory scope | Add one clause to the CLAUDE.md Memory bullet naming `C--Users-Owner/memory` (the harness auto-loads it). Word-neutral against 2.1's savings | Probe count |
| 2.4 | open-items tracker (710KB) | Short term: enforce the existing closed→history rollover. Long term: moves to a warehouse table in Phase 5 | Tracker <400KB; `open-items-triage` agent still reads it |
| 2.5 | Audit-revision memory sprawl (16 files) | Leave the files alone. The index split from R26-3 already carries the cost | none |

**Gate:** all probes green; a fresh test session starts and routes 5 canary prompts correctly (underwrite, LOI, lease addendum, schedule, daily brief).

## Phase 3: Fleet consolidation (after the 09-28 resume)

| # | Item | Change | Verify |
|---|---|---|---|
| 3.1 | 4 never-fired tasks | `orphaned-task-forensics` on each: registry row, enabled state, cron, surface, `list_task_runs`. Fix the root cause, or retire if superseded | Each has ≥1 successful run, or a documented retire |
| 3.2 | HubSpot reconcile 5 → 1 | Map every step of `tenant-hubspot-reconciliation`, `renewal-hubspot-reconcile`, `hubspot-renewal-closeout-tasks`, `hubspot-notion-contact-sync` and `tenant-contact-gap-sweep` into a ledger. Build `ora-hubspot-reconcile` (weekly, with a daily closeout sub-step only if the closeout needs daily cadence). Shadow for 2 cycles; diff the outputs | Every ledger step present; output diff empty or explained; HubSpot `global_limit` skips fall |
| 3.3 | Command-center mirror 3 → 1 | Same method for `cc-schematic-refresh`, `cc-snapshot-refresh` and `command-center-mirror-drift-check` | Same |
| 3.4 | `ora-health-guard` (19.6K w daily) | Split into a daily core (fast pass/fail checks that feed the deadman) and a weekly deep pass. Extract narrative to `references/`. Target ≤6K w daily | Same checks fire (checklist diff); the daily spec load aggregate drops |
| 3.5 | Self-maintenance ratio | After 3.2–3.4, re-measure the business/maintenance split. Target ≤35% maintenance | fleet-status count |

**Gate:** 2 clean cycles; `automation-health-monitor` green; `state-freshness-probe` shows no newly stale writers.

## Phase 4: Hook latency (blast radius, tested)

| # | Item | Change | Verify |
|---|---|---|---|
| 4.1 | PostToolUse dispatcher | Mirror `pretooluse-dispatcher.py`: one Python process running the ~5 PostToolUse checks in-process, preserving order, fail-open semantics and matchers. The `deploy` curl runs only for commands that match a deploy regex (not any substring) | Full hook test suite green; mutation-check on a COPY (per memory); latency per Bash call vs the 0.5 baseline |
| 4.2 | Review | Adversarial merge gate (Opus); each individual hook's tests still pass through the dispatcher path | `adversarial-merge-gate` verdict |

**Rollback:** revert the settings.json hooks block to the tag from 0.1. **Gabriel:** go required (hooks plus settings.json).

## Phase 5: Market-intelligence warehouse (the strategic build, `/build` L3)

| # | Item | Change | Verify |
|---|---|---|---|
| 5.1 | Schema | occ migrations 033+: `sale_comps`, `lease_comps`, `listings` (with price/status history), `owners`, `parcels`, `brokers`, `broker_submissions`, `open_items`. Provenance columns (source, fetched_at, confidence) on every row. Update the schema-lock doc | Migration tests; CI green; Fable REFUTE on the schema |
| 5.2 | Backfill | Notion comps DB (county-sales-monitor), parcel-screen workbooks, off-market master, deal-flow-triage history, lease abstracts (`lease_comps` from ORA's own leases) | Row counts reconcile to source; spot-check 20 rows |
| 5.3 | Dual-write | `county-sales-monitor`, `county-parcel-screen`, `deal-flow-triage` and `owner-outreach` write to the warehouse and to their current target. Notion stays the human view | 2 cycles, both targets agree |
| 5.4 | Read path | `acquisition-underwriting` COMPS mode, `deal-recon` and `market-monitor` query the warehouse first and fall back to web research; results cite warehouse rows | Golden-set eval harness shows no score regression |
| 5.5 | Cutover | Notion becomes a writeback view of the warehouse (the `notion-writeback.ts` pattern exists) | No lost fields (ledger diff) |

**Gate:** eval harness is flat or better. Invariant 7 holds: every comp carries a source.

## Phase 6: Host resilience

| # | Item | Change |
|---|---|---|
| 6.1 | Classify tasks | Deterministic (ingest, backups, billing, heartbeat) vs judgment (brief, triage, drafting) |
| 6.2 | Move deterministic jobs | Move them to Windows Task Scheduler or GitHub Actions (the ora-pm backups already set the precedent). Judgment tasks stay on the fleet |
| 6.3 | Pause/resume | Resume no longer depends on an attended session for moved jobs |

**Gate:** the moved jobs run with the Desktop app closed for 3 days.

## Do not build yet
More guards, probes or audit layers · new agents · a CoStar/Crexi integration (licensing decision first) · a new orchestration framework · a rewrite of the skill catalog (0 delete-candidates, confirmed again).

## Capability-preservation map (nothing lost)
| Removed/merged | Capability now lives in |
|---|---|
| code-review / commit-commands plugins | native `/code-review`; git via Bash/isolated-commit |
| 5 HubSpot tasks | `ora-hubspot-reconcile` (every step ledgered) |
| 3 mirror tasks | one mirror task |
| health-guard narrative | `references/` (checks unchanged) |
| CLAUDE.md parentheticals | `rules.md §Routing` (pointer kept) |
| session-context procedures | `rules.md §14` / `register-scheduled-task` |
| duplicate checkouts/worktrees | `_archive-non-onedrive/` (recoverable) |
| excel MCP write tools | Excel COM (`model-bulk-edit`), already the mandated path |

## Sequencing and effort
Phase 0: 1 session · Phase 1: 1 session plus Gabriel's clicks · Phase 2: 1 session · Phase 3: 2–3 sessions across 2 weeks (shadow cycles) · Phase 4: 1–2 sessions · Phase 5: 3–5 sessions · Phase 6: 1–2 sessions. Phases 0–2 are executable this week. 3 and 6 wait for the 09-28 resume. 5 can start in parallel after Phase 0 (separate repo, no conflict).

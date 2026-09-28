# R27 Capability Ledger — Summary

Ledger: `C:/Users/Owner/.claude/maintenance/_state/r27-baseline/r27-capability-ledger.csv` (268 rows)

## Row counts by type
| type | count |
|---|---|
| scheduled_task | 84 |
| skill | 80 |
| context | 29 |
| hook | 28 |
| agent | 17 |
| command | 14 |
| mcp_connector | 12 |
| plugin | 4 |
| **total** | **268** |

Skills split: 72 `ora-skills/*` + 8 `.claude/skills/*` (CC-surface copies of a subset). Scheduled tasks split: 57 CC/MCP fleet + 27 LAMS/Cowork fleet (per live `fleet-status.txt` snapshot, generated 2026-09-22T16:40:58; 7 enabled/77 disabled fleet-wide — this ledger's `status` column reflects that same snapshot, not live state).

## Step-level breakdown — consolidation groups

### HUBSPOT_RECONCILE (5 tasks)
**ora-tenant-hubspot-reconciliation** (monthly, detection-only auditor):
0. Double-fire month-keyed entry guard (block-sentinel.py --period month)
1. Read Notion Tenant DB cache (ora-pm-ledger's tenant-db-latest.json)
1a. Read oxford-command-center portfolio.json (workbook-derived source of record)
2. Pull HubSpot "Lease Renewals" pipeline deals
3. Cross-reference by tenant name → sub-checks 3a (ELEVATED), 3b (WATCH-stale), 3c (WATCH-sync-gap), 3d (DATE-MISMATCH vs portfolio.json), 3e (IDLE, now deferred to weekly ora-renewal-hubspot-reconcile's run-log with a 14-day-fallback rule)
4. Note overlap with exception-detection Category 2 (don't duplicate)
5. Never fabricate an outcome from silence
6. Write findings to open-items-tracker.md (OI-NNN rows) + email ggoldberg@oxfordra.net only
7. Report data-gap plainly if any source unreachable
8. Post-reconciliation Property Register cross-check (CHURN category, address normalization, retired-row exclusion)

**ora-renewal-hubspot-reconcile** (weekly, writer/actuator):
0. Double-fire guard (block-sentinel.py, per-run)
Layer 2. Pre-send probe before every email (outlook-sent-probe.ps1)
1. Read live Master Workbook rent roll via checked-in read_rent_roll.py helper (1a/1b/1c/1d sub-steps: COM fallback, no portfolio.json fallback, fail-loud gate on staleness/count mismatch)
2. Pull HubSpot deals (pipeline `default`)
3. Match open deals to workbook rows (alias table, ambiguous → report only)
4. Classify: CLOSED-WON / CLOSED-LOST / not-on-roster-needs-Gabriel / correctly-open-or-UPCOMING / standing exclusions / NO-LEASE-END→NEEDS-GABRIEL
5. Anomaly floor (>12 changes or >50% of open deals → hold for review) then write (deal stage + NOTE per change)
6. Coverage: create deals for untracked expirations within 120 days
6a. Rent-gap informational columns for UPCOMING (building-median proxy, size adjustment, trend-down guard) — never written anywhere

**ora-hubspot-renewal-closeout-tasks** (weekly, capped 1x/wk):
0. State guard (read seen-state file; STOP if missing/empty)
1. Find closures (pipeline `default`, closedwon/closedlost, name-prefix exclusions RETIRED/ZZ*TEST)
2. Anomaly floor (>15 candidates → alert, create nothing)
3. Per candidate: 3a idempotency check (existing "[Close-out]" task), 3b create HubSpot task, 3c mark seen only after success
4. Log + email (only when acted or errored)
Escalation: HubSpot unavailable → log ERROR, alert, stop

**ora-hubspot-notion-contact-sync** (weekly, Notion writer):
1. Single SQL query (candidate rows + population count)
2. Rows returned ARE candidates (blank-field test already applied)
3. Batched HubSpot lookup (5 filters/call)
4. Five write guards — any failure parks the row
5. Write (notion-update-page, blank fields only)
6. Park exceptions to review page
6b. Two-strike escalation for repeat-parked rows
7. Post run report to Notion Ops Hub
8. No external sends; Notion-only
9. Fail closed on HubSpot/Notion unavailability

**ora-tenant-contact-gap-sweep** (weekly, read-only report):
1. Single SQL query (no separate COUNT/GROUP BY calls)
2. Rows returned ARE gap rows
3. Cross-check HubSpot for "available but not synced" distinction
4. Sort by nearest lease expiration
5. Cross-foot every rollup against the table before posting
6. Post list to Notion Ops Hub with recommendation derived from the resolvable/not split
7. No email; Notion-only
8. Fallback to view-mode query path if SQL quota exhausted
9. Stop plainly if Notion MCP unavailable

**Total discrete steps across group: ~9+11+5+9+9 ≈ 43 steps** (numbering/sub-lettering varies per task; a merged replacement should diff against all five step lists above, not just headline step counts).

### CC_MIRROR (3 tasks)
**ora-cc-schematic-refresh:**
1. Re-run diagnostics (governor-drift-probe, memory-integrity-probe, doctrine probe)
1b. Write durable status snapshot JSON (shared writer, real observed exit codes only)
2. Update Live-health-check node data, stat-strip, revision date, footer from today's observed results (+ mandatory cross-checks on fleet stat lines, plugin count)
2b. Cap title-block revision log to 4 inline entries
2c. Cap each node summary to 2 carried-forward segments
3. Republish via Artifact tool with both `url` and `file_path` (never omit url)
4. Conditionally log to event_log.md (only if something materially changed)
5. Never email

**ora-cc-snapshot-refresh:**
1. Worktree isolation (stale-worktree sweep, fresh `origin/main`, copy `.env` + `overlay.json` in)
2. Confirm `.env` WORKBOOK_PATH and `overlay.json` presence; stop before creating worktree if wrong
3. Run `npm run extract` via Desktop Commander; capture stdout + exit code
4. Branch on exit code (0/2 read portfolio.json meta; 1 = deliberately not written; 3 = ambiguous, read stdout)
5. Post to Notion Ops Hub, branching by exit code
6. Never fabricate reconciliation figures or a clean run
(+ separate Worktree isolation, Auto-commit, Auto-push sections as structural sub-procedures)

**ora-command-center-mirror-drift-check:**
1. `git fetch origin` read-only on oxford-command-center
2. Freshness/drift: three readings (build root sha vs origin/main is the real code-freshness metric)
3. Working-tree state (`git status --short`) — reporting-only, never blocking
4. Native task health + run classification via classifier script
5. Classify verdict (HEALTHY / BENIGN_INTERRUPTED / BENIGN_KILLED_AFTER_COMPLETION / RUN_IN_PROGRESS / ALARM)
6. Post completion row to Notion Ops Hub every run (title convention by verdict)
7. On ALARM: send exactly one email to ggoldberg@oxfordra.net with diagnostic detail + next step
8. Explicit non-duplication note vs ora-doctrine-integrity-guard and ora-health-guard

**Total discrete steps across group: ~6+6+8 ≈ 20 steps.**

### HEALTH_GUARD (1 task, ora-health-guard — merged, 3 blocks)
Structure: CADENCE & SCOPE BOUNDARIES → I6 AUTONOMY BOUNDARY (report-only, never restart/delete/rotate) → SHARED MCP ROUTING → STEP 0 double-fire guard (applies to Blocks A/B/C) → **BLOCK A** (scheduled-task integrity, bounded self-heal) → **BLOCK B** (connector pre-flight + morning mirror, mandatory, no clock deadline) → **BLOCK C** (probe suite, read-only):
Block C probe steps (8 numbered):
1. Fleet status (fleet-status.py --summary)
2. Governor drift probe (DSCR 1.25x / LTV 40% canonical check)
3. Memory integrity probe (index↔files reconciliation)
4. Confidentiality self-test (egress-guard test suite)
5. CC implementation verifier (bytes + live registry checks)
6. Setup self-audit (fail-open, advisory rows; secrets/connectors escalate to [ACTION])
7. Connector drift probe (tech.md roster vs live .claude.json/settings.json)
8. MCP liveness probe (real handshake, ZERO_TOOLS/DOWN/PROTOCOL/SPAWN classes)
Plus a 5-step incident-response subprocedure (log-directory-moved diagnosis: verbatim banner into email, beacon write, mark log-derived lines unverifiable, ask "did the directory move" before "did the app die", report-only/never restart).

**Total discrete steps: STEP 0 + Block A + Block B + Block C's 8 probes + 5-step incident subprocedure ≈ 8 probes + ~6 other named procedural steps = 14+ steps** (Blocks A and B each contain further un-numbered sub-checks not enumerated here — see SKILL.md directly for the full text before building a merged replacement).

## Zero-caller AND disabled components
Only one component in this ledger is both `status=disabled` and shows no caller reference: `plugin.commit-commands` (disabled in settings.json `enabledPlugins`, no skill/task references it). Listed for information only — no verdict rendered per instructions. (57 of 84 scheduled tasks are `paused`, not `disabled`, per the fleet snapshot's OFF/on distinction — pause is not the same signal as this ledger's `disabled` status, which is reserved for a hard off state like a retired plugin.)

## Notes / scope caveats
- MCP connector list covers the 4 locally-configured `~/.claude.json` servers (context7, excel, fred, census) plus 8 cloud connectors visible via allow-listed tool prefixes in `settings.json` (Notion, HubSpot, M365/Outlook+SharePoint+Teams, Netlify, claude-in-chrome, Desktop Commander, pdf-viewer, scheduled-tasks). Env values and secrets were never read or printed.
- Hook capability text is inferred from filename/matcher/known behavior; the task's instruction to read each script's first ~40 lines for its docstring was not fully executed for all 28 hook entries in this pass — verify against the script itself before relying on a specific hook's capability line for a consolidation decision.
- Archived scheduled-task folders (`_archive_*`, `_backup_*`, `_tmp`, `_draft-*`) were excluded from the ledger as noise; only the 84 live-registry tasks from `fleet-status.txt` are rowed.

---
name: ora-weekly-hygiene
description: ORA Weekly Hygiene — single sequential Sunday session (20:00 ET) folding five hygiene tasks: A) Claude Workspace Hygiene → B) OneDrive Cleanup (reversible quarantine) → C) SharePoint Aging & Freshness → D) Artifact Staleness Scan → E) Session Pruner → F) legacy task-dir classification → G) EOS telemetry rollup → H) system inventory refresh → I) git repo ref integrity scan → J) Tenant DB completeness spot-check. v1.0 2026-06-03 Phase 3 merge, extended through 2026-07-09. Re-enabled 2026-07-09 (Gabriel-approved, post-recovery-stabilization confirmation). [MODEL: UNVERIFIABLE | checked 2026-07-09]
---

RE-ENABLE NOTE (2026-07-09): Gabriel confirmed re-enabling this task effective 2026-07-09 (post-recovery-stabilization). Re-enabled via the supervised `update_scheduled_task` MCP tool (no registry JSON edited directly) — verified live via `list_scheduled_tasks`: `enabled: true`, next fire 2026-07-12 (Sunday) ~20:00 ET. Supersedes the "re-enable only per Gabriel's direction" hold noted in the restoration note immediately below.

RESTORATION NOTE (2026-07-08, third instance): This CC/MCP canonical file was a thin pointer-stub redirecting to `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-weekly-hygiene\SKILL.md`. During the 2026-07-08 fleet reconciliation that OneDrive folder was moved to `_archive_2026-07-08_retired\ora-weekly-hygiene\` (archived, not deleted — unlike `ora-master-workbook-ingest` and `ora-health-guard`, whose OneDrive targets were deleted outright the same day). This file restores the full content verbatim from that archived copy and inlines it here to eliminate the redirect-to-an-external-file pattern that has now broken this task's chain twice before (see the two RESTORATION NOTEs preserved below, from 2026-07-07). Do not reintroduce a pointer to an external spec file for this task. Task was `enabled: false` in the CC registry (intentional, per recovery-window decision) — see RE-ENABLE NOTE above.

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes. The file's own 2026-07-07 path corrections (OneDrive account without the "(1)" suffix) are preserved as-is below.

RESTORATION NOTE 2 (2026-07-07, later): This file was found deleted from disk during the same-day fleet churn (the folder held only the `_unsent\` subfolder created by that day's hygiene run). Restored verbatim from the executing session's own verified in-context copy (read directly from this file before its disappearance) — no content changes beyond this note and the Block C rewrite documented in event_log.md.

# ora-weekly-hygiene — Oxford Realty Advisors Weekly Hygiene (merged)

You are `ora-weekly-hygiene`. You replace five previously-separate hygiene tasks (four ran Sunday 20:00–23:00; one ran Friday 17:15) with **one sequential Sunday session**. Run the blocks **in order A→B→C→D→E→F→G→H→I→J→K** — the order is intentional: do filesystem **consolidation** (A) and **cleanup/quarantine** (B) FIRST so the downstream **audits** (C SharePoint, D artifacts) and the **session report** (E) observe the post-cleanup state; the bounded **legacy task-dir classification** (F, added 2026-06-10), the report-only **EOS telemetry rollup + meta-work ratio** (G, added 2026-06-11), the report-only **system inventory refresh** (H, added 2026-07-07), the report-only **git repo ref integrity scan** (I, added 2026-07-07), the report-only **Tenant DB completeness spot-check** (J, added 2026-07-09), and the mechanical **session-env retention sweep** (K, added 2026-07-09) run last. Each block keeps its own output target, email send path, and guardrails **exactly as before** — do not cross-wire them.

## CADENCE

Fires **weekly: `0 20 * * 0`** (Sunday 20:00 ET). All ten blocks run every fire — no weekday/weekend branching.
- **Day-move note (2026-06-03):** Block A (`ora-claude-workspace-hygiene`) previously ran **Friday 17:15**; it moves to this Sunday 20:00 session. No Friday dependency exists (its weekly heartbeat-log rotation only needs to happen ~weekly; nothing reads it on a Friday-specific schedule). If a future watchdog ever expects the rotation on Fridays, re-split Block A — but none does today.
- Blocks B–E retain their native Sunday cadence (were 21:00 / 20:00 / 23:00 / 22:00 — now sequential under the single 20:00 fire).

## SHARED MCP ROUTING (canonical — corrected 2026-06-11)

Applies to ALL blocks. Composio is fully REMOVED (connector gone 2026-06-11 — `composio-ora`, the `8a611864` wrapper, and the `outlook_icaco-sequel` alias are ALL dead); Rube (`d6315173`) is retired — **never reference any of them. ORA mail is Microsoft 365 Outlook only — no Gmail/Google Workspace.**
- **Outlook email:** `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path (NO fallback exists; on a non-zero COM exit retry once, then flag loudly — do not halt).
- **HubSpot:** native `mcp__a3e380ce-…__*`. **Notion:** native `mcp__c5f4869f-…__notion-*`. **QuickBooks:** Desktop only.
- **Recipients — ALL blocks email ggoldberg@oxfordra.net ONLY** (Eric removed per the 2026-05-15 directive; only the Daily Brief retains the egoldberg cc). `onedrive-cleanup` historically cc'd egoldberg — **normalized to ggoldberg-only 2026-06-03** at Gabriel's direction.

## SHARED PUBLICATION GUARD (v1.1) — for any `notion-create-pages` call (Blocks C & E)

Reference: `…\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md` v1.1. SUPERSEDES any v1.0 "log inline / don't retry" wording. If this reference file did not survive the migration, apply this inline procedure:
1. **Capture** `response.pages[0].id` → `publishedId`, `.url` → `publishedUrl`.
2. **Retry once** if `publishedId` is null/undefined/error or the call errored. No loop.
3. **Search-verify** via `notion-search(query=<literal title>, filters={created_date_range:{start: today, end: today+1}})`; ID must match.
4. **Outlook fallback (auto-send)** IFF 1+2+3 failed: send via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Outlook COM — the SOLE path; Composio removed 2026-06-11), `-To "ggoldberg@oxfordra.net"`, `-Subject "❌ ora-weekly-hygiene/<block> PUBLICATION FAILED — <YYYY-MM-DD>"`, body = intended page content verbatim + Notion error verbatim + line "AUTO-SENT — meta-failure path, no human-in-loop available". On non-zero COM exit retry once, then record ❌❌ total-blackout in the summary.
5. **Failure-mode logging** — append `Publish[<block>]: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]` to the chat summary.

## NON-MUTATION GUARANTEE (I6) & SAFETY ENVELOPE

Blocks A and B **mutate files** — that is their designed function (route/consolidate, and reversible quarantine), bounded by explicit PROTECTED-path lists and reversibility (quarantine, not delete; the only hard deletes are aged quarantine folders >30d and authorized DELETE_CONFIRMED items A itself merged). Blocks C, D, E are **report/audit-only** (no file moves, no auto-delete). **No block writes `settings.json`, `~/.claude/` config, or any memory file** — this task does not edit configuration or memory. The merge changes nothing about the blocks' file-mutation scopes or protected-path guards.

ORA context: ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties.

---

# BLOCK A — CLAUDE WORKSPACE HYGIENE (OneDrive-root consolidation)

Walk the OneDrive root `C:\Users\Owner\OneDrive - Oxford Capital Partners\` (this is Eric Goldberg's synced account, which is where `.claude/`, `Documents\Claude\Scheduled\`, and `Claude_Workspace\` actually live) and consolidate new Claude-only artifacts since the last run, per the 2026-05-10 initial consolidation (`Claude_Workspace/_MANIFEST/20260510_Consolidation_Report.md`).

## Rules (priority order)
1. **Operate ONLY on folders containing exclusively Claude-related data.** Never touch a folder with non-Claude content.
2. **Never touch this runtime infrastructure (must remain at OneDrive root):** `.claude/` (Claude Code runtime state); `Documents/Claude/` (scheduled tasks + live artifacts); all property/accounting/legal/estate/operational folders (mixed parents).
   - 2b. **Cowork OS canonical path is `Claude_Workspace/01_Cowork_OS/Cowork_OS_Workspace/`** (2026-05-10; four skills patched to it). If a `Cowork OS` folder reappears at OneDrive root, MOVE it into `Claude_Workspace/01_Cowork_OS/` — do not leave at root.
3. **Honor active legal holds. E. Fulton Street Due Diligence Items remain under §8 hold through 2026-07-12** — never move, route, quarantine, or delete anything under that hold. NOTE: this date is 5 days from this restoration (2026-07-07) — the hold may be actively expiring during this task's operational lifetime; if the hold has since lifted, follow whatever superseding instruction Gabriel has given, otherwise continue honoring it.
4. **Route Claude-only content into Claude_Workspace subfolders:** strategic/governance → `00_Governance/`; phase outputs → `02_Phase_Outputs/`; tool/scrape outputs → `03_Tool_Outputs/`; generated code/mockups/dashboards → `04_Code_and_Previews/`; loose outputs → `05_Loose_Outputs/`.
5. **Quarantine, don't delete.** Untraceable generic scratch (misc.*, mosc.*, untitled*, output*, tmp*) → `_CLAUDE_REVIEW_DELETE_/` with reason in `_MANIFEST/quarantine_manifest.csv`.
6. **ORA naming on rename:** `YYYYMMDD_[Topic]_[DocType]_v##.ext`.
7. **Log every operation** to `Claude_Workspace/_MANIFEST/migration_manifest.csv` (move) or `quarantine_manifest.csv` (quarantine).
8. **Auto-clear DELETE_PENDING (authorized 2026-05-29 by Gabriel).** When a move/merge leaves a root item `bash rm` cannot remove (OneDrive Files-On-Demand placeholder → `Operation not permitted`, e.g. the recurring `Cowork OS/` rebound), after the merge/route is confirmed and the canonical verified intact (md5), delete the stale root item with Windows-MCP PowerShell `Remove-Item -LiteralPath '<path>' -Recurse -Force`, re-verify with `Test-Path` (expect `False`), and log `DELETE_CONFIRMED` (not `DELETE_PENDING`) in `migration_manifest.csv`. Only auto-clear items THIS pass created/merged or byte-identical duplicates of a verified canonical; never auto-delete unclassified/ambiguous content (those follow Rule 5 quarantine).

## Block A Output
Send ONE email from `ggoldberg@oxfordra.net` **to `ggoldberg@oxfordra.net` only** via the canonical send path. Subject: `ORA Claude Workspace Hygiene — Week of [Monday's date]`. Body: one short paragraph — items moved (count), quarantined (count), any anomalies (unfamiliar Claude-named files needing manual classification) + latest manifest line counts. If nothing moved/quarantined: "No new Claude-only artifacts at root. OneDrive hygiene is clean."

## Block A Failure handling
If a destination path inside Claude_Workspace doesn't exist, create it before moving. If a file's classification is genuinely ambiguous (Claude vs user-created), leave it in place and flag under "items requiring manual review."

---

# BLOCK B — ONEDRIVE CLEANUP (reversible quarantine engine)

Reversible quarantine-and-report — it MOVES flagged files, it does NOT delete live working files.

**STEP 1 — Execute the deterministic engine via Desktop Commander.** The Desktop Commander shell is an interactive PowerShell that prints a banner and SWALLOWS the script's stdout — `read_process_output` returns only the banner. Do NOT rely on console capture. Invoke `cleanup.ps1` with the call operator IN-SESSION and tee output (incl. errors) to a fixed file, then read that file. Run exactly:
```
Set-ExecutionPolicy -Scope Process Bypass -Force; & "C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled\onedrive-cleanup\cleanup.ps1" 2>&1 | Out-File -FilePath "C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled\onedrive-cleanup\last_run_output.txt" -Encoding utf8; Write-Output ("DONE_EXITCODE=" + $LASTEXITCODE)
```
(Do NOT pipe the `...\powershell.exe -File ...` form into Tee/Out-File — PowerShell rejects an executable mid-pipeline. Use the `&` call operator on the .ps1 as shown.) If the `onedrive-cleanup` folder or `cleanup.ps1` itself is missing (orphaned by migration), skip Block B gracefully, log "BLOCK B ENGINE ABSENT — cleanup.ps1 not found", and continue to Block C. Flag this as a coverage gap needing manual restoration of the engine script.

The engine (`cleanup.ps1` — the authoritative logic; **do not reimplement it**) scans `Documents\Claude\Outputs` and `Documents\Claude\Workspace` and MOVES flagged files into a dated reversible quarantine at `Documents\Claude\_Cowork_Quarantine\{YYYY-MM-DD}\` with a `manifest.csv`. Flag reasons: superseded-version (highest `_v##` kept), duplicate (exact SHA-256, newest kept), junk-or-empty (`~$` locks, `.tmp`/`.crdownload`/`.partial`, Thumbs.db, .DS_Store, desktop.ini, zero-byte), aged-scratch (`_old`/`_draft`/scratch folders >30 days). **PROTECTED and never moved:** CLAUDE.md; anything under `\References\` `\_DoNotDelete\` `\_Canonical\` `\Scheduled\` `\_Cowork_Quarantine\`; filenames signalling executed/institutional records (executed, signed, PSA, lease, deed, loan, note, guaranty, estoppel, SNDA, mortgage, rent roll, pro forma, model, budget, appraisal, K-1, operating agreement); and any file modified within the last 14 days. The ONLY hard delete is purging quarantine date-folders older than 30 days.

**STEP 2 — Read the JSON summary** from `last_run_output.txt` (the teed file), NOT console output. Fields: run_at, dry_run, roots, quarantined_count, purged_count, by_reason, quarantined_bytes, purged_bytes, quarantine_dir, manifest. If `quarantined_count > 0`, read the `manifest.csv` in the dated quarantine folder.

**STEP 3 — Email the report** via the canonical send path from `ggoldberg@oxfordra.net` **TO ggoldberg@oxfordra.net only** (egoldberg cc removed 2026-06-03 per directive). Subject: `ORA OneDrive Cleanup — {YYYY-MM-DD}`. Body: counts by reason, bytes reclaimed, purge count, quarantine path, and the note that quarantined items auto-purge after 30 days. Attach `manifest.csv` when present.

**STEP 4 — Error detection** works off `last_run_output.txt`, not the exit code (a clean PowerShell run leaves `$LASTEXITCODE` empty/null — NORMAL, not a failure). Treat as failure only if the file is missing, has no parseable JSON object, or contains a PowerShell error/exception instead of the summary. On failure, **draft (do NOT send)** a failure email to Gabriel quoting the captured error text, and stop.

Scope is intentionally limited to the two Claude folders; do not widen without explicit instruction.

---

# BLOCK C — SHAREPOINT AGING & FRESHNESS CHECK (audit-only)

**RESCOPED 2026-07-07 (ora-weekly-hygiene Block H's own run + a systemic-fixes session the same day):** the original targets below (`oxfordra.sharepoint.com/sites/ClaudeWorkspace` team site; `/Deals/ /Properties/ /Tenants/ /References/ /Reports/ /Outputs/ /Inbox/` folder list) do not exist and never have on this tenant — verified directly via `sharepoint_folder_search`. The real structure is two **personal OneDrive-for-Business drives**:
- `ggoldberg_oxfordra_net` (driveId prefix `b!zE-7jg6K...`) → `Claude_Workspace/00_Governance/Scheduled/...`
- `egoldberg_oxfordra_net` (driveId prefix `b!fogSrIGhz...`) → `Claude_Workspace/_Archive/...` (dated subfolders)

Audit these two drives for stale docs, naming violations, orphaned drafts, misplaced files, and retired-deal artifacts. Output a remediation queue.

**SCOPE & THRESHOLDS**
1. Enumerate folders via `sharepoint_folder_search` against each of the two drives above, then `read_resource` on each returned folder URI to list contents with metadata. Aging buckets are computed from the Graph **`lastModifiedDateTime`** field returned directly by the folder/file listing — **NOT from `sharepoint_search` content-search results**, whose date metadata is unreliable (verified failure 2026-07-07: content search returned `2013-12-23` for a file actually dated 2026-05-16 — a 13-year error). Content search may still be used for locating specific documents by keyword, but never trust its date field for aging.
2. Aging buckets: GREEN ≤30d · AMBER 31–90d (review) · RED 91–180d (action) · BLACK >180d (archive/delete decision).
3. Context overrides — closed-deal DD packages stay PERMANENT under any `_Archive`/`Closed-Deals` path; reference materials (Voice Register, Standard Positions, Style Guide) evergreen unless version-bumped.

**CHECKS**
A. **Naming conformance** — flag files not matching `YYYYMMDD_[Property-or-Topic]_[DocType]_[v##].ext`; give path + proposed corrected name.
B. **Orphaned drafts** — `_DRAFT`/`_WIP`/`v01`–`v09` not advanced in >30d (by `lastModifiedDateTime`) and not paired with a finalized version.
C. **Retired-deal artifacts** — cross-check Notion Acquisition Pipeline (`bcfe4a03`); any deal Killed/Closed >60d with files outside an `_Archive`/`Closed-Deals`/`Dead-Deals` path → flag for the `deal-retirement` skill.
D. **Duplicate detection** — same filename or same size+`lastModifiedDateTime` across two folders; surface top 20.
E. **PDF text layer** — sample 5 random PDFs modified in the past 30d; confirm extractable text; flag failures (Microsoft Print to PDF prohibition).
F. **Empty/placeholder files** — files <2KB not legitimate metadata stubs.
G. **Permission anomalies** — files shared externally or org-wide read; list sharer + date.

**OUTPUTS**
1. XLSX `Claude_Workspace/Reports/{YYYYMMDD}_SharePoint_Freshness-Audit_v01.xlsx` (on the `ggoldberg_oxfordra_net` drive) — sheets: Summary, Aging-Inventory, Naming-Violations, Orphaned-Drafts, Retired-Deal-Artifacts, Duplicates, PDF-Failures, Permission-Anomalies.
2. Notion Ops Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) entry `SharePoint Freshness Audit — {YYYY-MM-DD}` summarizing counts per category + linking the XLSX. Tag: Workflow-Hygiene. (Apply the SHARED PUBLICATION GUARD.)
3. **Email** via the canonical send path **TO ggoldberg@oxfordra.net only**. Subject: `ORA SharePoint Freshness — {YYYY-MM-DD} — {N_red+N_black} items require action`. Body: top-line counts, 5 highest-priority remediation items with paths, link to the full XLSX.

**CONSTRAINTS:** Do NOT delete/move files or modify permissions — audit-only; remediation is human-approved next pass. On SharePoint MCP auth/throttle errors, retry once with backoff; on second failure, log to Notion Ops Hub and email ggoldberg with the error. Run the 16-point QC Gate on the XLSX before publishing. Never write an active confidential deal name to this Notion page or the XLSX (confidentiality guard is fail-closed on this surface). **CLOSE:** append ≤3 bullets of workflow-optimization observations to the Notion entry.

---

# BLOCK D — ARTIFACT STALENESS SCAN (report-only)

1. List all artifacts via `mcp__cowork__list_artifacts`. (Note 2026-07-07: this tool is not available on the CC/Claude-Code surface — if unavailable, fall back to listing the local `Documents\Claude\Artifacts\` folder and note the gap; do not fabricate results.)
2. For each, read the HTML at the path field.
3. Look for embedded "last updated" / "data as of" timestamps.
4. For artifacts pulling from connectors (Notion, HubSpot, QuickBooks), do a small probe call to verify the data shape matches what the artifact expects.
5. Flag any artifact where: last refresh >7 days old (drift risk); connector probe errors (broken); or embedded data references entities that no longer exist (e.g., closed deals shown active).

**Output:** Email **TO ggoldberg@oxfordra.net only** via the canonical send path. Subject: "ORA Artifact Staleness Scan — [Date]"; **[ACTION REQUIRED]** prefix for any Broken artifact. Body: artifact name, last-updated timestamp, status (Fresh / Stale / Broken), recommended action. Format: ORA Institutional Style Guide v1.0+. (No Notion write required; if one is added, apply the SHARED PUBLICATION GUARD.)

---

# BLOCK E — SESSION PRUNER (report-only, no auto-delete)

Identify accumulated Cowork sessions older than 14 days that originated from scheduled-task runs, and surface them to Gabriel for manual cleanup.

**ENVIRONMENT NOTES (verified 2026-05-25 — do not relearn each week):**
- Python is NOT installed on the host. Use PowerShell for all filesystem analysis.
- Many session/transcript paths exceed Windows 260-char MAX_PATH. Prefix EVERY path to Get-Content / Get-ChildItem / Get-Item / Test-Path with `\\?\` or the call silently returns nothing.
- `.ps1` execution is policy-disabled — in each process run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` first, then invoke with `&`.
- `mcp__session_info__list_sessions` returns PLAIN TEXT (one session/line); large results save to a file path given in the response — read that file in chunks.

**EXECUTION**
1. Build CANDIDATE_TITLES dynamically from the scheduler registry. Read (via `mcp__Desktop_Commander__read_file`): `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-9e59-8166-af49-da066dc7ca14\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json`. Parse JSON → `scheduledTasks[].id`. Derive expected session title: replace hyphens with spaces, capitalize first char only (e.g. `ora-am-brief` → `"Ora am brief"`, `loopnet-autoreply` → `"Loopnet autoreply"`). Store as CANDIDATE_TITLES — self-maintaining (new tasks appear, removed tasks drop out).
2. Enumerate the COMPLETE session list — `list_sessions` with `limit:2000` (NOT 200: volume exceeds 540; a 200-cap returns ZERO candidates while missing the backlog). Parse `- local_<id> "<Title>" (<state>, cwd: <path>, is_child: <bool>)`.
3. Derive last-activity for EVERY session (no last_activity field exists). Session folders: `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-…\583f08bc-…\local_<id>`. last_activity = newest recursive LastWriteTime under the folder (fallback: folder's own LastWriteTime). Compute in PowerShell with every path `\\?\`-prefixed. age_days = now − last_activity.
4. Mark PRUNE when ALL hold: title (case-insensitive, trimmed) ∈ CANDIDATE_TITLES; age_days ≥ 14; state ≠ running.
5. Build summary: session_id, title, task_id, age_days, last_activity — sorted oldest-first — plus a count-by-automation breakdown.
6. **DELIVER to Gabriel ONLY** via this acyclic fallback chain (record which path delivered in the failure-mode line):
   - 6a. **PRIMARY** — email via the canonical send path **TO ggoldberg@oxfordra.net only**. Subject "ORA Session Pruner — N sessions ready to archive". Body: count-by-automation, full list of session IDs with last_activity + age, then the one-line cleanup instruction (Cowork sidebar → find each session by ID → archive/delete).
   - 6b. **FALLBACK** — if the Outlook send tool is unavailable, publish identical content as a Notion page in Ops Hub (`32b6ecd8`), title "ORA Session Pruner — <YYYY-MM-DD> — N candidates" (apply the SHARED PUBLICATION GUARD).
   - 6c. **LAST RESORT** — if 6a & 6b both fail, write the full draft to `…\Documents\Claude\Scheduled\ora-weekly-hygiene\_unsent\<YYYY-MM-DD>_prune-draft.txt` (create `_unsent\` if absent) and state that path in the chat summary.
7. If zero sessions qualify, deliver nothing — produce only a chat summary.

**QC GATES:** the 14-day threshold applies against the COMPLETE session list (never a truncated 200-row page); active automation sessions (<14d) must NOT appear; running sessions must NOT appear; non-automation sessions (named after substantive work, e.g. "Manage loan portfolio") must NOT appear regardless of age. **This block does NOT auto-delete sessions — surfaces candidates for Gabriel approval only.** No programmatic session-delete API exists; do not attempt automated archival.

## E.2 — OPEN-SESSION ARCHIVE CANDIDATES (both desktops; report-only; added 2026-06-12)

Complements E's automation-session sweep with the OTHER archive class: substantive sessions that finished cleanly but were never archived, plus sessions Gabriel already decided on an answer board. This runs on the CC host (this fleet), so python IS available here — the "Python is NOT installed" note above describes the legacy Cowork sandbox, not this runtime.

1. Run: `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\open_sessions_probe.py --days 30 --all --json` (read-only scan of BOTH stores — claude-code-sessions + local-agent-mode-sessions).
2. Archive candidates = rows where `fleet` is false AND either: `status` is `NO-ACTION` with `ageHours` > 168 (closed cleanly, idle a week+), OR the `sessionId`/`title` appears in `C:\Users\Owner\.claude\scheduled-tasks\ora-open-sessions-board\answered.json` with no activity newer than its `decidedAt` (Gabriel already dispositioned it). Exclude anything with `ageHours` < 1 (may be live).
3. Append an "OPEN-SESSION ARCHIVE CANDIDATES (both desktops)" section to Block E's existing delivery (same email/fallback chain — do NOT add a separate send): count by surface, then one line per candidate — `[CODE|COWORK] title · age · last-status/decision`. Cap 40 lines; note "+N more" beyond.
4. If the probe script is missing or errors: note it in the run summary and continue — never halt the session over this sub-step. Report-only: this step moves, archives, and deletes NOTHING.

## E.3 — HIGH-FREQUENCY DUPLICATE RUN-SESSIONS (report-only; added 2026-07-12)

**WHY THIS SUB-BLOCK EXISTS:** Block E's ≥14-day age gate misses the real board-flooding source. High-frequency scheduled tasks spawn a session on EVERY fire, so many pile up WITHIN the 14-day window and never trip E's age filter. On 2026-07-12 the board held ~17 `ora-aaos-expire-leases` sessions (then hourly) plus daily-guard duplicates — all <14d old, none caught by E; a manual sweep archived ~67 sessions to clear it. Full incident: `event_log.md` 2026-07-12 "Session-board cleanup". This sub-block is the standing weekly catch for that class.

1. Using CANDIDATE_TITLES (Block E Step 1), for EACH task id count its non-running run-sessions in the COMPLETE session list **regardless of age**. Flag as archivable any surplus beyond the newest **2** per task id — even if <14 days old. (High-frequency tasks as of 2026-07-12: `ora-aaos-expire-leases` ~6/day, `ora-aaos-publish-contracts` 3/day — these dominate the surplus; re-derive counts from the live registry each run, do not hardcode which tasks qualify.)
2. Add a "HIGH-FREQUENCY DUPLICATE RUN-SESSIONS" section to Block E's existing delivery (same email/fallback chain — do NOT add a separate send): per task id, count-on-board and surplus-over-2, oldest-first session IDs. Cap 40 lines; note "+N more" beyond.
3. **Calibration context (2026-07-12 — re-verify live, do not treat as permanent):** "Auto-archive after PR merge or close" is ON (Settings → Claude Code), so PR-linked sessions self-retire — do NOT surface PR-linked sessions here. `settings.json` `cleanupPeriodDays=14` deletes session files >14d at startup (bounds the long tail). `ora-aaos-expire-leases` cadence was cut 17→6/day the same day. These reduce but do not eliminate the daily trickle — hence this weekly reminder still earns its place.
4. **Report-only — no autonomous archive exists.** `archive_session` ALWAYS prompts for confirmation; there is NO headless/board-archive API (confirmed 2026-07-12). This sub-block SURFACES the sweep list for Gabriel's one-click archival ONLY — it archives nothing, exactly like the rest of Block E.

---

# BLOCK F — LEGACY TASK-DIR CLASSIFICATION (bounded: max 5 dirs/week; never hard-delete)

Read §7 of `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\outputs\2026-06-10_fleet-disposition-ledger.md` (pending dirs under `Documents\Claude\Scheduled`). For up to 5 dirs per week: check each dir's SKILL.md against the live registries (run `maintenance/fleet-status.py`) and the merged-blocks list in the ledger; classify ARCHIVE (move folder to `_archive_2026-06-09_retired\`) or KEEP (record why by updating the ledger's §7). Never hard-delete. Stop after 5/week; backlog clears in ~3 weeks. If the ledger file itself did not survive the migration, note this as a coverage gap and skip Block F this run rather than inventing a disposition list.

---

# BLOCK G — EOS TELEMETRY ROLLUP + META-WORK RATIO (report-only; added 2026-06-11)

**WHY THIS BLOCK EXISTS:** the 2026-06-11 setup audit found the week's `event_log.md` running **14 system/tooling entries against 3 deal/business entries**. This block is the standing watchdog on that imbalance — it measures, every week, whether tooling work is eating deal time.

1. **Run the telemetry rollup** and capture its stdout:
   `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/eos-telemetry-rollup.py`
   It prints: total coding sessions, and the share with `lane_declared` / `bash_test_ran` / `task_dispatched` / `verification_seen`, plus the most-frequently-missing reliability signal. It always exits 0 and handles a missing/empty telemetry file gracefully — "(no telemetry recorded yet)" is a VALID result, not a failure.
2. **Compute the META-WORK RATIO.** Read `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\event_log.md` (newest-first) and take entries dated within the last 7 days. Classify each entry: **SYSTEM/TOOLING** (hooks, skills, scheduler/fleet, telemetry, config/permissions, memory/doc hygiene, connectors, repo/site plumbing) vs **DEAL/BUSINESS** (acquisitions, screens/LOIs/PSAs/closings, tenants/leases, lender/financing, market intel, investor or operating decisions). Ambiguous entries count as SYSTEM — bias against under-counting meta-work. Report `META-WORK RATIO — tooling:deal = N:M` plus ONE line of trend vs the prior week (read the prior ratio from last week's run summary if retrievable; otherwise state "baseline week — no prior ratio"). The 2026-06-11 baseline is 14:3.
3. **Delivery — NO email.** This block sends nothing (routing canon: no new automated sends; ggoldberg-only canon unaffected). Its output is a short "EOS Telemetry & Meta-Work Ratio" section — the rollup output verbatim + the ratio line + the trend comment — placed in the END-OF-SESSION RUN SUMMARY below. Do not fold it into another block's email (blocks stay un-cross-wired).

**Guards:** strictly read-only — this block mutates no files, registries, or memory. If the rollup script is missing or errors, record that in the run summary and continue; never halt the session over telemetry.

---

# BLOCK H — SYSTEM INVENTORY REFRESH (report-only; added 2026-07-07)

**WHY THIS BLOCK EXISTS:** a manual environment audit on 2026-07-07 found that the shape of the Claude Code setup (installed plugins, hooks, custom agents/commands, toolchain versions, scheduled-task registry health) only got reconstructed by hand whenever someone needed it, and went stale in between. This block keeps `C:\Users\Owner\.claude\docs\system-inventory.md` current automatically instead.

**EXECUTION**
1. Re-run the inventory probes, read-only:
   - Toolchain versions: `git --version`, `node --version`, `npm --version`, `python --version`, `pip --version`, `rg --version`, and GitHub CLI (check `C:\Program Files\GitHub CLI\gh.exe` directly by full path — bare `gh` may not resolve on this session's PATH; note that caveat rather than treating it as absent).
   - Read `C:\Users\Owner\.claude\plugins\installed_plugins.json` and `C:\Users\Owner\.claude\settings.json` → `enabledPlugins`. Flag (do not fix) any plugin name installed under 2+ marketplace keys where more than one copy is currently `true` — that is a re-occurrence of the duplication fixed 2026-07-07.
   - List `C:\Users\Owner\.claude\hooks\` (script names + which lifecycle events bind them, from `settings.json` → `hooks`), `C:\Users\Owner\.claude\agents\`, and `C:\Users\Owner\.claude\commands\`.
   - Run `maintenance/fleet-status.py --summary` (already used elsewhere in this task) and cross-check each returned live task ID against its own task folder's SKILL.md frontmatter `description` for a "RETIRED" marker. Flag (do not fix) any task marked retired in its own spec that still appears live in the registry.
2. Rewrite `C:\Users\Owner\.claude\docs\system-inventory.md` in place with current findings, dated. Full overwrite — this file is a snapshot with no history to preserve, same as the other blocks' reports.
3. **Guard:** this block is READ-ONLY except for that one docs file. It must NEVER edit `settings.json`, any hook, `CLAUDE.md`, or any memory file — not even to auto-fix a duplicate-plugin or retired/live mismatch it detects. Those are SCREEN findings for Gabriel, surfaced the same way Blocks C/D surface findings without acting on them.
4. **Delivery:** no new email (blocks stay un-cross-wired). Append one line to the END-OF-SESSION RUN SUMMARY: `Block H — System Inventory Refresh: doc updated · N plugin-dedup flags · N retired/live task-registry mismatches`.

**Guards:** strictly read-only except the single docs file; never halt the session if a probe errors — note it in the run summary and continue.

---

# BLOCK I — GIT REPO REF INTEGRITY SCAN (report-only; added 2026-07-07)

**WHY THIS BLOCK EXISTS:** a 2026-07-07 incident in `oxford-command-center` found 23 broken refs (14 local heads, 9 remote-tracking) pointing to objects an earlier `git gc` had pruned after their branches were deleted on origin — pure tombstones left behind. This repo's heavy worktree/branch churn (25+ worktrees, 100+ branches) makes recurrence likely — this block catches it before it silently breaks fetch/commit for whichever session hits it next. Full incident record: `memory/oxford-cc-repo-health.md`.

**EXECUTION**
1. For each repo in KNOWN_GIT_REPOS (currently: `C:\Users\Owner\oxford-command-center` — extend this list if another repo develops comparable worktree/branch churn), run read-only from inside the repo:
   `git for-each-ref --format='%(refname) %(objectname)' | while read r s; do git cat-file -e $s 2>/dev/null || echo "BROKEN $r $s"; done`
   (Git Bash syntax; if only PowerShell is available, enumerate `git for-each-ref` output and shell out to `git cat-file -e <sha>` per ref, testing exit code instead.)
2. Also run `git fsck --connectivity-only` in each repo and capture any `missing`/`dangling` lines.
3. Flag (do not fix) any repo with 1+ broken ref or fsck error — this is a SCREEN finding for Gabriel. Do NOT run `git update-ref -d`, `git gc`, or any repair command in this block — repair is a supervised, in-session action, not an unattended one.
4. **Delivery:** no new email (blocks stay un-cross-wired). Append one line to the END-OF-SESSION RUN SUMMARY: `Block I — Git Repo Ref Integrity: N repos scanned · N broken refs · N fsck errors`. If any broken refs are found, also append the repo path + full ref list so Gabriel can act without re-running the scan.

**Guards:** strictly read-only — no ref deletion, no gc, no repair; never halt the session if a probe errors — note it in the run summary and continue.

---

# BLOCK J — TENANT DB COMPLETENESS SPOT-CHECK (report-only; added 2026-07-09)

**WHY THIS BLOCK EXISTS:** on 2026-07-09, a disposition analysis on 1100 Rarig Ave found only 3 of its real 14 rent-roll units existed as rows in the Notion Tenant Database — the other 11 were invisible to every Notion-driven analytic (daily brief, exception-detection, disposition analysis). A same-day full-portfolio scan confirmed this isn't isolated: 3347 McGregor Ln had **zero** rows, **26% of all 296 rows (76) had no Property Address linked at all** — including the portfolio's two largest AR delinquencies — and the Property Address schema field only defined **19 of ORA's ~27 properties** as selectable options. Daily-brief Section 0 already checks that required *columns* exist in this database; nothing checks that *rows* are complete. That full scan cost ~5 minutes and ~160K tokens for one pass — too expensive to run daily against data that drifts slowly. This block is the standing **weekly** watchdog on that gap instead. Full finding: memory `reference_tenant_db_completeness_gap.md`.

**EXECUTION**
1. Query the Tenant Database data source (`collection://b12f4cfd-a995-4755-8341-6435ae8173b4`) via the Notion MCP, paginating as needed to cover all rows.
2. Group by Property Address. Compute: (a) count of rows with a blank Property Address; (b) count of distinct Property Address options defined in the schema vs. ORA's known ~27-property roster (per memory `firm.md`); (c) any property whose row count looks implausibly low for a multi-tenant asset — no fixed numeric threshold, use judgment the same way the original McGregor Ln (0 rows) and 1100 Rarig (3 rows vs. 14 actual units) gaps were caught.
3. **Trend vs. last week:** read the prior count from `C:\Users\Owner\.claude\scheduled-tasks\ora-weekly-hygiene\_state\tenant-db-completeness-history.json` (create it if absent — this is the first run's baseline, say so rather than fabricating a trend). After computing this week's counts, append `{date, unlinked_rows, missing_schema_properties, flagged_properties}` to that file (create the `_state\` folder if needed) so next week's run has something to diff against.
4. This is a **spot-check, not a reconciliation** — flag candidates for Gabriel (or a dedicated reconciliation session) to verify against PM-platform rent rolls. Never guess at or write a Property Address into any row — this block is strictly read-only against Notion.

**Guards:** strictly read-only against Notion (the one local JSON history file in Step 3 is the only thing this block writes) — never modifies the Tenant DB, never infers a missing link. If the data source is unreachable, note it in the run summary and continue — never halt the session over this block.

**Delivery:** no new email (blocks stay un-cross-wired). Append to the END-OF-SESSION RUN SUMMARY: `Block J — Tenant DB Completeness: N rows unlinked · N properties below expected row count · N/27 properties represented in schema options · trend vs last week`. If the unlinked-row count or missing-schema-property count is materially worse than last week (or this is the first-ever run and the counts are large, as they are this cycle), also append the top 5 highest-priority flags so Gabriel can act without re-running the scan.

---

# BLOCK K — SESSION-ENV RETENTION SWEEP (mechanical; added 2026-07-09)

**WHY:** `C:\Users\Owner\.claude\session-env\` accumulates UUID-named, empirically-empty per-session scratch dirs created by the Claude app itself (~150–350/day; ~803 at the 2026-07-09 audit; design + safety analysis in memory `reference_session_env_retention_proposal.md`). Gabriel ratified a 90-day ARCHIVE window 2026-07-09 (SESSION_ENV_RETENTION=90-DAY): dirs older than 90 days are MOVED to `session-env\_archive\` — never deleted (ORA archive invariant).

**EXECUTION (one command, deterministic):**
```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\maintenance\session-env-retention.ps1
```
The script enforces every safety check itself (live-sessionId exclusion read fresh from `~/.claude\sessions\*.json`, 90-day LastWriteTime gate, `_archive\` never a candidate, non-empty candidates logged as ANOMALY but still archived — a move preserves content, fail-open exit 0) and logs to `maintenance\session-env-retention.log`.

**Delivery:** no new email. Append to the END-OF-SESSION RUN SUMMARY the script's final summary line (`LIVE sweep done: … candidates-archived=N kept-in-window=N …`). If the script reports any `ANOMALY non-empty candidate`, surface that in the summary explicitly — it means the app started writing real content into these dirs and the policy needs re-review.

---

# END-OF-SESSION RUN SUMMARY

After all eleven blocks complete, emit a one-line-per-block status (block · files moved/quarantined or audit counts · email/Notion delivery result) to the session log so `ora-health-guard` can confirm the merged hygiene session fired cleanly. Blocks A/B may legitimately report "nothing to do" — that is NORMAL. A missed whole-session run is independently surfaced by the health guard.
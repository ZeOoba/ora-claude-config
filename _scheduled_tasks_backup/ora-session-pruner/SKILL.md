---
name: ora-session-pruner
description: Weekly Sunday 10 PM session hygiene — lists Cowork sessions older than 14 days originating from scheduled tasks, delivers Gabriel a one-click prune list (Outlook email, Notion fallback). Does not auto-delete; user-triggered cleanup.
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

You are running the ORA Weekly Session Pruner.

OBJECTIVE
Identify accumulated Cowork sessions older than 14 days that originated from scheduled-task runs, and surface them to Gabriel for manual cleanup.

ENVIRONMENT NOTES (verified during the 2026-05-25 run — do not relearn these each week)
- Python is NOT installed on the host. Use PowerShell for all filesystem analysis.
- Many session/transcript paths exceed the Windows 260-char MAX_PATH limit. Prefix EVERY
  path passed to Get-Content / Get-ChildItem / Get-Item / Test-Path with the `\\?\`
  long-path device prefix, or the call returns nothing and fails silently.
- `.ps1` execution is disabled by policy. In each process, run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` first, then invoke
  the script with the call operator (`&`).
- mcp__session_info__list_sessions returns PLAIN TEXT (not JSON), one session per line.
  When the result is large it is saved to a file whose path is given in the tool
  response — read that file in chunks rather than expecting inline output.

EXECUTION

1. Build CANDIDATE_TITLES dynamically from the scheduler registry:
   Call mcp__Desktop_Commander__read_file on:
   `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json`
   Parse JSON → extract `scheduledTasks[].id`. For each id, derive expected session title:
     - Replace all hyphens with spaces
     - Capitalize first character only (rest unchanged)
     Examples: `ora-daily-brief-6am` → `"Ora daily brief 6am"`, `loopnet-autoreply` → `"Loopnet autoreply"`
   Store all derived titles as CANDIDATE_TITLES set. Self-maintaining — new tasks appear
   automatically when registered; removed tasks drop out.

2. Enumerate the COMPLETE session list. Call mcp__session_info__list_sessions with a
   limit well above the current session count (use limit:2000). Do NOT cap at 200:
   session volume now exceeds 540, the 200 most-recent sessions are all under the 14-day
   threshold, and a 200 cap therefore returns ZERO candidates while silently missing the
   entire backlog. Parse each line in the form:
     `- local_<id> "<Title>" (<state>, cwd: <path>, is_child: <bool>)`

3. Derive a last-activity timestamp for EVERY session. list_sessions does NOT expose a
   last_activity field, so read it from the filesystem. Session folders are at:
   `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\local_<id>`
   last_activity = newest LastWriteTime of any file under that folder (recursive),
   falling back to the folder's own LastWriteTime if empty/unreadable. Compute in
   PowerShell with every path `\\?\`-prefixed. age_days = now − last_activity.

4. Mark a session PRUNE when ALL of the following hold:
     - title (case-insensitive, trimmed) is in CANDIDATE_TITLES
     - age_days ≥ 14
     - state ≠ running

5. Build the summary: session_id, title, task_id, age_days, last_activity — sorted
   oldest first — plus a count-by-automation breakdown.

6. DELIVER to Gabriel ONLY (NOT Eric — this supersedes the global cc-Eric default).
   Output must NEVER be stranded; follow this acyclic fallback chain:
   6a. PRIMARY — email from ggoldberg@oxfordra.net via Composio `OUTLOOK_SEND_EMAIL`
       (account_id "outlook_icaco-sequel"). Subject:
       "ORA Session Pruner — N sessions ready to archive". Body: count-by-automation,
       then the full list of session IDs with last_activity + age, then the one-line
       cleanup instruction (Cowork sidebar → find each session by ID → archive/delete).
   6b. FALLBACK — if the Composio Outlook send tool is NOT in the session toolset,
       publish identical content as a Notion page in the Operations Hub
       (database 32b6ecd8), title "ORA Session Pruner — <YYYY-MM-DD> — N candidates".
       Apply the Publication Guard below to that write.
   6c. LAST RESORT — if 6a and 6b both fail, write the full draft to
       `...\Documents\Claude\Scheduled\ora-session-pruner\_unsent\<YYYY-MM-DD>_prune-draft.txt`
       (create `_unsent\` if absent) and state that path in the chat summary. This
       disk-write supersedes the Publication Guard Step-4 Outlook fallback whenever
       Outlook is the unavailable connector that triggered 6b.
   Record which path delivered (6a / 6b / 6c) in the failure-mode logging line.

7. If zero sessions qualify, deliver nothing — produce only a chat summary.

QC GATES
- The 14-day threshold is applied against the COMPLETE session list — never a truncated
  200-row page.
- Active automation sessions (< 14 days old) must NOT appear in the prune list.
- Running sessions must NOT appear.
- Non-automation sessions (named after substantive work like "Manage loan portfolio")
  must NOT appear regardless of age.
- This task does NOT auto-delete sessions. It surfaces candidates for Gabriel approval
  only. No programmatic session-delete API exists; do not attempt automated archival.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="outlook_icaco-sequel"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-session-pruner PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*

*Revised 2026-05-25 (v1.2) — optimizations applied from the 2026-05-25 run: (1) limit:200 cap removed, threshold now applied to the complete session list; (2) last-activity derived from session-folder mtime via PowerShell with `\\?\` long-path prefixes, since list_sessions exposes no last_activity field; (3) connector-resilient delivery chain added — Outlook → Notion Ops Hub → disk — so output is never stranded; (4) environment notes section added. Prior version archived as SKILL_pre-20260525_v1.1.md.*

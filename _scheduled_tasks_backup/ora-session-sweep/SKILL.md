---
name: ora-session-sweep
description: Weekly Sunday 20:00 session-index sweep — self-contained (no longer depends on reading an external prompt file). Indexes new Cowork sessions into BrainVault Sessions folder, sourcing date: from list_scheduled_tasks.lastRunAt cross-reference where possible (falls back to index-date, explicitly labeled, never fabricated). Step 0 re-attempts the BrainVault mount defensively for unattended runs; if still unreadable, fails closed to Notion Ops Hub with escalation to Gabriel (persistent mount grant, or migrate to CC/MCP fleet) rather than retrying blindly. v1.1 (2026-08-11, fixes both the 2026-08-10 mount failure and the index-date-only gap found during that recovery). [MODEL: claude-sonnet-5 | set 2026-08-11]
---

This is an automated run of a scheduled task. The user is not present to answer questions. For implementation details, execute autonomously without asking clarifying questions — make reasonable choices and note them in your output. "write" actions (e.g. MCP tools that send, post, create, update, or delete), only take them if these instructions ask for that specific action. When in doubt, producing a report of what you found is the correct output.

You are running the ORA weekly session sweep (v1.1, 2026-08-11 — now self-contained; previously pointed at C:\Users\Owner\Obsidian\BrainVault\.claude\scripts\session-sweep-prompt.md, which is a human-readable mirror of these same steps but is no longer the execution dependency). Follow these steps exactly:

0. Call `request_cowork_directory` with path `C:\Users\Owner\Obsidian\BrainVault`. This is a best-effort re-mount attempt for the unattended context — cheap/idempotent if access is already granted. If BrainVault is still unreadable after this (Step 2 fails), skip to the FAIL-CLOSED PATH at the bottom — do not improvise, do not guess at paths.

1. Call `list_sessions` (include_archived: true, limit: 50) to get all sessions.

1a. Call `list_scheduled_tasks` (no args) and keep the full result — used in Step 4a for date sourcing.

2. Read all existing session notes from `C:/Users/Owner/Obsidian/BrainVault/60-Reference/Sessions/` — extract the `session_id` frontmatter field from each file to build a set of already-indexed IDs.

3. Filter the session list: exclude sessions where title contains "email queue" (case-insensitive), title is empty/null, or session_id already exists in the vault notes.

4. For each new substantive session, create a note at `C:/Users/Owner/Obsidian/BrainVault/60-Reference/Sessions/YYYY-MM-DD_<slug>.md`. If a title collides with another new session's filename in this same run, disambiguate by appending the last 6 hex characters of the session id to EVERY colliding filename (matches existing `-60ea1d` / `-acddfb` vault convention). Frontmatter/structure:
```
---
type: session
date: YYYY-MM-DD
title: "Session Title"
session_id: local_xxxxx
surface: cowork
confidential: false
tags: [session, cowork]
status: indexed
---

# Session Title

**Date:** YYYY-MM-DD
**Surface:** cowork
**Session ID:** `local_xxxxx`

## Topics / Summary
*Auto-indexed [RUN DATE]. [DATE PROVENANCE NOTE — see Step 4a]*

## Key Outputs
-

## Decisions
-

## Open Items
-
```

4a. DATE SOURCING — do this BEFORE writing the file (filenames cannot be renamed once written in this vault, so get it right on first write):
- Neither `list_sessions` nor `read_transcript` expose a session start timestamp. Do not fabricate one.
- Normalize the session title and compare against every `description`/`taskId` in the Step 1a `list_scheduled_tasks` result. On a clear match, use that task's `lastRunAt` converted from UTC to America/New_York as `date:`. Topics/Summary line: "Cross-referenced against list_scheduled_tasks: matches task `<taskId>`, lastRunAt <ISO timestamp> (converted to America/New_York)."
- Duplicate titles: lastRunAt is the MOST RECENT firing only. Apply it to the first (most-recent) occurrence in list_sessions order; do not back-date older duplicates by assuming a regular cadence — misses/catch-up bursts are documented (e.g. 2026-08-09 ora-friday-closeout ran as a Sunday catch-up after a Friday miss). Older duplicates fall through to the no-match case.
- Title-embedded date (e.g. "CC/MCP fleet defects 2026-08-05"): usable, but label it "Date taken from the session's own title — self-description, not an independently verified timestamp."
- No match, no title date: use today's run date and write "Auto-indexed [RUN DATE]. Session start date not independently derivable from list_sessions/read_transcript in this environment — date field reflects index date, not session-origination date."

5. If the session title contains "fulton" or "e fulton" (case-insensitive), set `confidential: true` and add: `> **CONFIDENTIAL** — No deal specifics in this note.`

6. Report to Notion Ops Hub (`32b6ecd8`): X new indexed, Y already existed, Z skipped, and how many of X were date-sourced from list_scheduled_tasks vs. index-date fallback.

Do not summarize session content — index only.

FAIL-CLOSED PATH (BrainVault unreadable after Step 0): log the failure to Notion Ops Hub (`32b6ecd8`) and stop. Additionally note that full unattended reliability requires ONE of: (a) Gabriel granting BrainVault as a persistently-connected folder for scheduled/unattended Cowork sessions — no create_scheduled_task/update_scheduled_task field exists to pre-authorize a directory mount (confirmed against the tool schema 2026-08-11), this is an app-settings action only Gabriel can take; or (b) migrating this task to the CC/MCP (Claude Code) fleet, where BrainVault is native filesystem with no mount/approval step — requires registration from a supervised Claude Code session (register-scheduled-task Rule 1; a Cowork session cannot do this for itself). Do not retry either fix automatically.
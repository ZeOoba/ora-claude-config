---
name: ora-capex-idea-stage-nudge
description: Monthly (1st, 12:15 PM ET) — scans the Notion CapEx & Maintenance Log for opportunities stuck in Opportunity Stage = Idea for 30+ days and nudges Gabriel to advance them to Screening. Closes the gap found 2026-07-26 (no existing task monitored Idea-stage staleness on this log — same class of gap ora-critical-deadlines-scan closed for the Critical Deadlines Tracker same day). [MODEL: claude-sonnet-5 | set 2026-07-26]
---

ORA CapEx & Maintenance Log — Idea-Stage Staleness Nudge. Runs monthly, 1st of the month, 12:15 PM ET.

PURPOSE: The 🔧 CapEx & Maintenance Log (Notion database id 5dfcc3ad-532e-4e5f-bf8d-512e2b69e317, data source collection://acd5102e-16bc-4171-9cde-19a2496b1429) has an "Opportunity Stage" select field (Idea → Screening → Underwriting → Approved → Underway → Complete → Rejected) but nothing was monitoring how long items sit in "Idea" before advancing. This mirrors the gap ora-critical-deadlines-scan closed for the Critical Deadlines Tracker (2026-07-26) — a database with no dedicated staleness monitor.

STEPS:
1. Query the data source: SELECT "CapEx ID", "Description", "Category", "Opportunity Type", "Created", "Property", "Expected Annual NOI Impact" FROM "collection://acd5102e-16bc-4171-9cde-19a2496b1429" WHERE "Opportunity Stage" = 'Idea'.
2. For each row, compute age in days from "Created" (ISO datetime) to the run date. Flag any row with age >= 30 days as STALE.
3. For STALE rows, resolve the linked "Property" relation (collection://24d6a531-f4b7-4c38-87fb-3b1be4a4f1f3) to get a human-readable property name/address for the report — do not fabricate a property name if the relation is empty; report "No property linked" instead.
4. Never fabricate NOI impact, category, or any other field — read only what the query returns. If "Expected Annual NOI Impact" is blank, report it as blank, not as zero or an estimate.
5. Post a summary to the Notion Operations Hub (Ops Hub page id 32b6ecd8-9e59-81f2-b329-df3fd0e25062, or its CapEx-tracking sub-block if one exists — search before assuming placement) listing: CapEx ID, Description, Property, age in days, Expected Annual NOI Impact. Group into "STALE (30+ days, needs Screening decision)" and "Fresh (<30 days)".
6. If any STALE rows exist, draft (via Outlook COM, C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — the sole automated send path, no fallback connector) a short nudge email to ggoldberg@oxfordra.net ONLY (never cc, never ze@) listing the stale items and asking whether each should advance to Screening, stay in Idea, or be Rejected. On a non-zero COM exit code: retry once, then flag the failure loudly in the Notion completion row — do not halt the task.
7. If zero Idea-stage rows exist or zero are stale, post a clean-pass line to Ops Hub and skip the email — do not send a nudge with nothing to nudge.
8. QUESTIONS FOR GABRIEL: if the "Opportunity Stage" schema changes (options renamed/removed) or the data source id stops resolving, stop and surface that as a flagged exception in the Ops Hub post rather than guessing at a replacement field/id.

Do not duplicate ora-critical-deadlines-scan's logic (that task owns the Critical Deadlines Tracker, a different database) — this task owns Idea-stage CapEx staleness only.
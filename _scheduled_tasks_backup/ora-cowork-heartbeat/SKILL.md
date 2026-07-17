---
name: ora-cowork-heartbeat
description: Silent dead-man's-switch heartbeat — 05:50 + 17:50 ET daily. Updates hardcoded Notion page timestamp by ID; no search, no email, no page creation. Watched by external GitHub Actions watchdog (16h threshold). v03. [MODEL: claude-sonnet-5 | set 2026-07-08 | tool-grant re-approved 2026-07-17]
---

**Cowork Heartbeat — silent signal task** (v03, re-registered 2026-07-08 to standardize onto claude-sonnet-5; preserves v02 hardening of 2026-05-23 and v03 retiming of 2026-06-10. v02 root-cause: notion-search is semantic and unreliable for exact-title lookup; v01's create-if-missing branch produced duplicate pages. Therefore: hardcoded ID only, never search, never create.)

## Purpose
You are emitting a heartbeat signal that an external watchdog (GitHub Actions) reads to detect Cowork outages. Output goes to ONE specific Notion page identified by ID. Do NOT send email. Do NOT create new pages. Do NOT print verbose chat. Total runtime under 5 seconds.

## Canonical target — DO NOT CHANGE without coordinating watchdog repoint
- Page ID: `35c6ecd8-9e59-81d5-8d2c-d08002458b78`
- Title: `Cowork Heartbeat — 2x/day signal`
- Parent: `32b6ecd8-9e59-81f2-b329-df3fd0e25062` (Oxford Real Assets — Operations Hub)

## Procedure
1. Compute `now_utc` (ISO-8601, e.g. `2026-06-10T22:00:05Z`) and `next_utc = now_utc + 12h`.
2. Call the Notion `notion-update-page` tool with page_id `35c6ecd8-9e59-81d5-8d2c-d08002458b78`, command `update_content`, and a single search-and-replace targeting the existing `Last heartbeat:` line. If you do not know the existing line verbatim, first call `notion-fetch` on the page ID to read the current `Last heartbeat: <…> · Next expected: <…>` line, then use that exact string as old_str. Replacement: `Last heartbeat: <now_utc> · Next expected: <next_utc>`.
3. **Failure handling — no auto-create.** If the update errors (page not found, 403, network), emit ONE line to chat: `HB ❌ <error summary>`. Do NOT call notion-create-pages. Do NOT search for a replacement page. Duplicates are the exact failure mode v02 prevents. The external watchdog alarms within 16h — that is the intended signal.
4. On success, optionally log one line: `HB ✅ <now_utc>`. Nothing else.
5. **No email under any circumstance.** Email-on-failure is the watchdog's job, not the heartbeat's.

## Manual recovery — if the canonical page is destroyed
Restore from Notion trash (preserves page ID). If unrestorable: create a new page under parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062` titled `Cowork Heartbeat — 2x/day signal` (icon 💓) with the standard 4-line body ending `Last heartbeat: <now_utc> · Next expected: <next_utc>`, then update this task's Canonical target block AND repoint the external watchdog in the same maintenance window.

**Restoration note:** Re-registered 2026-07-08 to standardize execution model onto claude-sonnet-5 (previously re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned it). Content restored verbatim from the surviving SKILL.md. Re-approved 2026-07-17 to grant this task's unattended runs a standing tool-approval for `notion-fetch` and `notion-update-page` — the missing grant was the confirmed root cause of the 2026-07-15/16 ~42h beacon stale incident (dispatch succeeded per registry `lastRunAt`, but the unattended notion-update-page call could not complete without an approved permission, so the write silently failed).
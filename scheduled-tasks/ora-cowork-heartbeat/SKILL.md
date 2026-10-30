---
name: ora-cowork-heartbeat
description: Silent dead-man's-switch heartbeat — 05:50 ET daily. Updates the hardcoded Notion page 35c6ecd8 timestamp by ID only — no search, no email, no page creation; now_utc from a real clock (shell date -u), next-expected = now_utc +24h. Watched by the external GitHub Actions watchdog (ZeOoba/ora-cowork-watchdog) on the page's last_edited_time (30h threshold). Migrated LAMS→CC 2026-10-30 (Gabriel in-turn; LAMS fleet dark since 09-15); LAMS twin retire-pending. Day-keyed double-fire guard, fail-open. [MODEL: UNVERIFIABLE | checked 2026-10-30]
---

MIGRATION NOTE (2026-10-30, v08): Moved from the LAMS/Cowork fleet to the CC/MCP fleet (Gabriel in-turn, Deal Sourcing Expansion Plan Phase 1 decisions — the whole LAMS fleet has been disabled since 2026-09-15 with no resume queued, so the dead-man chain had no producer). This CC copy is canonical; the LAMS twin is disabled and retire-pending (maintenance/_state/retire-pending.json) and this file must NOT redirect to the LAMS path. Adaptations versus LAMS v07, all non-logic except the guard: STEP 0 double-fire guard added (required for any new CC task with a side effect; fail-open, so it can never suppress the first heartbeat of a day); step 1a is the expected path because Claude Code always has a shell. Other edits, all wording or provenance: frontmatter [MODEL:] tag reset to UNVERIFIABLE (a new CC registration; the LAMS `claude-sonnet-5 | set 2026-08-11` set-value does not carry over); Purpose "Cowork outages" → "fleet outages" and "under 5 seconds" → "well under a minute"; step 3 "ONE line to chat" → "ONE line", the OI-280 closure citation (ora-cowork-watchdog PR #13, d5264342) is kept only here in this note; step 1b dropped the parenthetical "(the fetch in step 2 returns it)"; the v05/v04 restoration notes condensed into one "Restoration history" paragraph and the 2026-08-17 class-n note dropped; a Changelog section added; and the step 3 no-tools branch now also closes the claim with `fail`. The signal now proves "the Desktop app's CC fleet fired today" — the watchdog semantics (30h on last_edited_time) are unchanged.

**Cowork Heartbeat — silent signal task** (v08 CC, 2026-10-30; body from v07, 2026-09-13, OI-297: step 1 requires `now_utc` from a real clock — shell `date -u`, else the notion-fetch "as of" server timestamp, else abort — after the 2026-09-13 run wrote a model-computed `20:22:00Z` 7h35m ahead of Notion's actual edit time; watchdog references 16h → 30h per OI-280. v06 2026-08-11 corrected the 2x/day → 1x/day drift; v02 root cause: notion-search is semantic and unreliable for exact-title lookup and v01's create-if-missing branch produced duplicate pages — therefore hardcoded ID only, never search, never create.)

## Purpose
You are emitting a heartbeat signal that an external watchdog (GitHub Actions) reads to detect fleet outages. Output goes to ONE specific Notion page identified by ID. Do NOT send email. Do NOT create new pages. Do NOT print verbose chat. Total runtime well under a minute.

## Canonical target — DO NOT CHANGE without coordinating watchdog repoint
- Page ID: `35c6ecd8-9e59-81d5-8d2c-d08002458b78`
- Title: `Cowork Heartbeat — 1x/day signal`
- Parent: `32b6ecd8-9e59-81f2-b329-df3fd0e25062` (Oxford Real Assets — Operations Hub)

## Procedure
0. **DOUBLE-FIRE ENTRY GUARD** (v08; fleet standard, `_shared/README-DOUBLE-FIRE-GUARD.md`). First action, before any Notion call:
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-cowork-heartbeat --block main --run-id <run_id> --period day --ttl-min 15
   - Exit 10 → today's heartbeat already landed. Stop silently (no Notion call); this is a normal skip.
   - Exit 11 → another fire is live right now. Stop silently.
   - Exit 0 → proceed to step 1.
   - ANY other exit (tooling failure) → FAIL OPEN: proceed to step 1 anyway and emit the code verbatim in your one-line output. A broken guard must never silence the dead-man signal.
   After a successful update (step 4), close the claim:
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-cowork-heartbeat --block main --run-id <run_id> --period day
   If the update fails (step 3), close it with:
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-cowork-heartbeat --block main --run-id <run_id> --period day --error "<error summary>"
   Only the run holding the claim (exit 0) calls `complete` or `fail`; a stand-down (10/11) or a fail-open run calls neither. Always pass `--period day` on every call.
1. **Read `now_utc` from a real clock — NEVER compute, recall, or derive it from the page's existing `Last heartbeat:` value** (OI-297). Source, in order:
   a. Run `date -u +%Y-%m-%dT%H:%M:%SZ` (bash) or `(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')` (PowerShell) and use its output verbatim.
   b. Otherwise use the server timestamp from the `notion-fetch` response header line `... as of <ISO timestamp>:` — truncate fractional seconds, keep the `Z`.
   c. If neither is available, do NOT write a guessed time: emit `HB ❌ no clock source`, close the claim with `fail`, and stop (the watchdog alarms on `last_edited_time`, which is the real signal).
   Then `next_utc = now_utc + 24h` (1x/day cadence) — this addition is the only arithmetic permitted.
2. Call the Notion `notion-update-page` tool with page_id `35c6ecd8-9e59-81d5-8d2c-d08002458b78`, command `update_content`, and a single search-and-replace targeting the existing `Last heartbeat:` line. If you do not know the existing line verbatim, first call `notion-fetch` on the page ID to read the current `Last heartbeat: <…> · Next expected: <…>` line, then use that exact string as old_str. Replacement: `Last heartbeat: <now_utc> · Next expected: <next_utc>`.
3. **Failure handling — diagnose before escalating.** If no `notion-*` tools are available in the session at all (ToolSearch for "notion" returns nothing), the cause is a disconnected connector, not a permission grant — check `mcp-registry list_connectors`/`search_mcp_registry` for Notion's `connected` status before assuming anything else, then emit `HB ❌ notion tools unavailable` and close the claim with `fail`. If tools ARE available but the update call itself errors (page not found, 403, network), emit ONE line: `HB ❌ <error summary>` and close the claim with `fail`. Do NOT call notion-create-pages. Do NOT search for a replacement page. Duplicates are the exact failure mode v02 prevents. The external watchdog alarms once `last_edited_time` is more than 30h old — that is the intended signal.
4. On success, close the claim with `complete`, then optionally log one line: `HB ✅ <now_utc>`. Nothing else.
5. **No email under any circumstance.** Email-on-failure is the watchdog's job, not the heartbeat's.

## Manual recovery — if the canonical page is destroyed
Restore from Notion trash (preserves page ID). If unrestorable: create a new page under parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062` titled `Cowork Heartbeat — 1x/day signal` (icon 💓) with the standard 4-line body ending `Last heartbeat: <now_utc> · Next expected: <next_utc>`, then update this task's Canonical target block AND repoint the external watchdog in the same maintenance window.

**Restoration history (from LAMS v05/v04, kept for diagnosis):** the 2026-07-29 failure was the Notion connector being disconnected from the session entirely (`connected: false`), fixed by Gabriel reconnecting via OAuth — not a per-task approvedPermissions gap (the superseded v04 theory). On a future failure, first check whether `notion-*` tools exist and the connector shows `connected: true` before pursuing a permission or registry-field theory.

## Changelog
- **v08 (2026-10-30):** migrated LAMS→CC/MCP; STEP 0 day-keyed, fail-open double-fire guard; clock step 1a is the CC default. Body otherwise carried from v07.
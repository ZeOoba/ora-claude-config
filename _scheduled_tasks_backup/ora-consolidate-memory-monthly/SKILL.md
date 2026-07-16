---
name: ora-consolidate-memory-monthly
description: Monthly reflective consolidation pass over the ORA memory files — merge duplicates, fix stale facts, prune the index. Runs the consolidate-memory skill and emails a change summary. 05:00 on the 2nd of each month ET. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

# Monthly Memory Consolidation

**Purpose:** Keep the ORA memory store accurate and lean. Memory drifts (stale task counts, retired connectors, superseded deal facts); this task catches that drift on a monthly cadence instead of relying on ad-hoc cleanups.

## Steps

1. **Run the consolidate-memory skill** against `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/` (corrected 2026-07-08, Gabriel-authorized — the prior `--1-`-suffixed path pointed at a separate, incomplete OneDrive folder; see `reference_memory_scope_fragmentation.md`):
   - Merge duplicate entries across the topical files (user_, firm_, people_, project_, market_, reference_, feedback_, governance_).
   - Fix stale facts — verify against observed state; trust observation over memory and update.
   - Prune / refresh the `MEMORY.md` index so every file is listed and dated.
   - Respect the append-with-dated-headers convention; never silently overwrite institutional history — move superseded content to `_archive/` with a dated note.
2. **Special checks each run:**
   - Confirm the scheduled-task count in `reference_tech.md` still matches the live LAMS registry; update if drifted. (Note: as of 2026-07-07 this is a fresh count post-migration/restore — expect a large delta from the pre-migration figure and record it as a one-time step-change, not drift.)
   - Confirm no retired connector (Rube, Gmail, Zapier, Composio) has crept back into any memory file as "active."
   - Confirm `OXFORDRA_REPO` / canonical-repo references still resolve on disk.
   - **Doctrine/governor audit line (Phase 3 item 5):** read `C:/Users/Owner/.claude/maintenance/_state/doctrine-status.json` (if present) for the past month's most recent doctrine/governor probe results, and grep `C:/Users/Owner/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md` for `"Pre-push proceeded DESPITE doctrine drift"` entries dated within the past month (pre-push override-sentinel uses). Log ONE line into this run's monthly consolidation `event_log.md` entry: doctrine/governor pass/fail counts + any override reasons found (or "no overrides"). This closes the audit line on a recurring cadence, not just opportunistically. Never echo a confidential term when summarizing doctrine check-8 findings — index reference only.
3. **Produce a concise change summary** (files touched, facts corrected, duplicates merged, index changes).

## Email delivery to ggoldberg@oxfordra.net (mandatory final step)

Deliver the change summary as an Outlook email to **ggoldberg@oxfordra.net** ONLY (no egoldberg cc — routing canon: only the Daily Brief cc's Eric) — in addition to any other output. Follow `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md` if present; otherwise:

1. Compose the summary as HTML (not a link).
2. Write it to `C:/Users/Owner/AppData/Local/Temp/ora-consolidate-memory-monthly-email-body.html`.
3. Send via Outlook COM (PRIMARY): invoke `C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1` with `-To "ggoldberg@oxfordra.net" -Subject "[ORA] Monthly Memory Consolidation - YYYY-MM-DD" -BodyFile <temp> -BodyFormat html`.
4. On non-zero exit: retry once, then flag the failure (do not halt) — `send-via-outlook.ps1` is the SOLE send path; Composio was removed 2026-06-11 and no fallback connector exists. (Rube is retired — never route through it.)

**This task's values:** `TASK_ID=ora-consolidate-memory-monthly`, `DISPLAY_NAME=Monthly Memory Consolidation`
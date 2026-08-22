---
name: project_automation_audit_rev17_2026-08-21
description: "ORA Automation Audit Revision 17 (2026-08-21) — caught and fixed a time-critical LAMS fleet duplicate-resurrection bug before its 5PM ET fire; one new skill-trigger collision flagged; corrected Revision 13's own CLAUDE.md word-count refutation."
metadata: 
  node_type: memory
  type: project
  originSessionId: 187b7d31-f27a-4955-be9d-acc6540e8802
  modified: 2026-08-21T20:40:07.965Z
---

Revision 17 of the ORA Automation Audit artifact (https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7). Full findings live in the artifact itself (Revision 17 rev-band) — this entry holds only what a future session needs before trusting that artifact at face value.

**R17-1, executed same-pass (time-critical, fixed before it could fire):** The 2026-08-17 "LAMS bounded-pause has no auto-resume" gap that [[project_ora_doc_qc_shared_module_pr48_2026-08-17]]'s sibling event_log entries described as open is actually CLOSED — `ora-lams-routine-resume-08-21` was registered and correctly built since then; live `fleet-status.py` is ground truth over the 3-day-stale MEMORY.md snapshot on this. But reading both fleets' resume scripts side-by-side (they were built on separate surfaces the same day, 08-17, never cross-checked against each other) found a fresh bug: both listed `ora-passed-deal-tracker` for re-enable, including the LAMS copy that was deliberately superseded by an 08-15 migration to CC/MCP and already failed once with "no COM access." Left alone, both fleets' resumes (5:00 PM ET 2026-08-21) would have silently resurrected the broken duplicate. Edited `ora-lams-routine-resume-08-21/SKILL.md` directly (Gabriel-approved via AskUserQuestion) to drop it from the re-enable list — 25 of 26 LAMS tasks resume; the CC/MCP copy resumes normally, unaffected.

**Still open, Gabriel's call:** the LAMS copy of `ora-passed-deal-tracker` needs a supervised, archive-first retirement (R13-3's original recommendation, never executed) — it will keep resurfacing in any future blanket LAMS operation until it's actually retired, not just left disabled.

**R17-2, not executed (skill-file edit, Gabriel's call):** `daily-brief` and `market-monitor` both carry the literal trigger phrase "market update" and CLAUDE.md's tie-breaks don't arbitrate the pair. Recommended fix: drop the phrase from `daily-brief`'s trigger list.

**R17-3, correction:** Revision 13's own verification pass had refuted R13-5's "CLAUDE.md is 1,841 words, 9 from the FAIL gate" finding using a bare `wc -w`, which undercounts by ~135 words (documented locale bug). The live authoritative counter (`doctrine-integrity-probe.py`) reconfirmed 1,841w on 2026-08-21 — R13-5's original reading was right, the "refutation" was wrong. Any future CLAUDE.md word-count claim in this artifact's lineage should state which counter produced it.

**Also current as of this pass:** MEMORY.md was 22,418B (918B past the 21,500B WARN marker) — Gabriel chose archival-with-ref-repair same-session. Archived 4 genuinely-closed entries (portfolio.json seed-fallback, settings.json enabledPlugins attribution, broker-pipeline-blobs outage, cc-snapshot-refresh dq-flag) to `_archive/*_archived_2026-08-21.md`, repaired both inbound refs in `open-items-tracker.md` (one literal path link, one wikilink annotation). MEMORY.md now 21,437B, back under WARN with 2,963B of headroom. `memory-integrity-probe.py` confirms zero new orphaned links or unlisted files from this pass. Both this artifact's own rev-band cap and the System Schematic's title-block + node-summary caps are correctly honored right now (the skill's own "highest-value check" came back clean). Threads 1 (plugins/connectors) and most of thread 3 (skill catalog) came back clean beyond R17-2.

**Also executed same-session (Gabriel: "proceed with all recommendations and fixes"):** R17-2 fixed — `daily-brief` v2.11→v2.12 (`ora-skills` commit `fd9bd17`), dropped the "market update" trigger phrase. **Still blocked:** the LAMS `ora-passed-deal-tracker` retirement cannot be executed from a Code/CC-MCP session — `update_scheduled_task`/`delete_scheduled_task` resolve to the local fleet with no fleet parameter, and this id collides with the live CC copy, so calling those tools from here risks deleting the wrong task. Needs a native on-device Cowork session.

**Housekeeping:** Revision 13 rolled off to `ora-automation-audit-history.md` (full prose, verbatim) per the 4-entry inline cap — Revisions 17/16/15/14 are now the inline set.

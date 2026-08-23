---
name: project_automation_audit_rev18_2026-08-22
description: "ORA Automation Audit Revision 18 (2026-08-22) — MEMORY.md 266B from HARD ceiling, event_log.md 35 days unrolled, LAMS retirement still unexecuted"
metadata: 
  node_type: memory
  type: project
  originSessionId: f99e2f98-e5b4-4a98-a24a-0ba03206b73d
  modified: 2026-08-22T20:01:55.092Z
---

Revision 18 of the "ORA Automation Audit" artifact (https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7) ran via [[ora-setup-audit]], continuing Revision 17. Full findings live in the artifact — this entry is only what a future session needs before trusting it at face value.

**Lead finding, needs Gabriel's go-ahead, not yet executed:** MEMORY.md was 266B from its 24,400B HARD read-ceiling at measurement time (24,134B; +1,716B in one day, largely this audit's own pointer output). This entry itself was written by compacting the superseded Revision 17 index line rather than only appending, to avoid breaching the ceiling on the write that reports the ceiling risk — same self-compaction pattern Revision 10 used (R10-11). If MEMORY.md is still tight next session, the next lever is archiving more Projects & system entries with ref-repair, not deleting live pointers.

**Second finding, same status:** event_log.md is 1.42MB, unrolled for 35 days (3.5x the largest of its 3 prior archived chunks). `rollover-event-log.py` exists and works but has no size-based trigger — only fires when someone remembers to run it.

**Verified, not just repeated:** the LAMS `ora-passed-deal-tracker` twin's retirement was described elsewhere as "ratified 2026-08-22" — direct read of the live LAMS registry JSON shows it's still registered, `enabled: false`, folder unarchived. Ratified ≠ executed; still open, still `ask`.

**Closed this pass:** R17-2 (daily-brief/market-monitor "market update" trigger collision) — daily-brief v2.12 dropped the phrase, confirmed live; no CLAUDE.md edit needed.

**New, not yet executed:** session-context.md has 2 bullets over the 80-word cap (owner-outreach ratification, ora-passed-deal-tracker id-collision) — probe recommends moving both to event_log.md.

Threads 1 (plugins/connectors) and fleet health came back clean, re-verified independently — see artifact for evidence. Two skills flagged still-growing (`register-scheduled-task` 3,475w, `package-and-stage-skill` 8,583w) — `ask`, changelog-extraction candidates, not executed.

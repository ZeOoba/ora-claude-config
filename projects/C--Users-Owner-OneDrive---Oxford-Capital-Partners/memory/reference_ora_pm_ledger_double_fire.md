---
name: reference-ora-pm-ledger-double-fire
description: ora-pm-ledger WAS double-registered; LAMS twin confirmed absent/retired (2026-07-12, Cowork registry + live-store filesystem both checked), CC/MCP copy (cron 0 18) is the sole live registration; orphan spec folder archived (not deleted) 2026-07-12; §0.5 de-dupe guard retained as backstop.
metadata: 
  node_type: memory
  type: project
  originSessionId: a1df4067-a0a1-474e-ab35-bae1d41dc51e
---

`ora-pm-ledger` is registered on BOTH fleets: CC/MCP (`enabled`, cron `0 18`, reachable via `list_scheduled_tasks`) AND a LAMS/Cowork twin (spec at `Claude_Workspace/00_Governance/Scheduled/ora-pm-ledger/SKILL.md`). On 2026-07-09 both fired the same day (LAMS ~16:27 ET delivered A/B/C; CC 18:00 fire would have duplicated). Duplicate Ops Hub pages also double-count in the next morning's brief.

**Fix applied 2026-07-09:** a **§0.5 PRE-FLIGHT DE-DUPE GUARD** added to BOTH pm-ledger SKILL.mds — checks today's Sent-Items subjects / Ops Hub pages / send-log, skips any block already delivered, no-ops (one-line Ops Hub note, sends nothing) if all delivered. This neutralizes the double-fire regardless of which fleet runs second.

**RESOLVED 2026-07-12 — nothing to retire (verified on both surfaces):** a Cowork (LAMS) `list_scheduled_tasks` shows NO `ora-pm-ledger` on the LAMS fleet, and a CC-side filesystem check found no `ora-pm-ledger` under the LIVE LAMS store `...\Documents\Claude\Scheduled\` (its three consolidated ancestors — ora-notion-daily-digest / ora-outbox-qc-sweep / ora-eod-action-ledger — sit archived under `_archive_2026-06-11_orphans\`). The redundant LAMS registration behind the 2026-07-09 double-fire is already gone. **Correction to the narrative above:** the `Claude_Workspace\00_Governance\Scheduled\ora-pm-ledger\SKILL.md` folder cited earlier was NEVER the live LAMS store (per register-scheduled-task, live LAMS store = `Documents\Claude\Scheduled\{id}\`, CC/MCP store = `~\.claude\scheduled-tasks\{id}\`); it is an orphaned/misfiled spec never wired to the scheduler — flagged for archival. CC/MCP `ora-pm-ledger` (cron `0 18`, last fired 2026-07-11 18:09 ET) is the SOLE live registration. §0.5 de-dupe guard kept as belt-and-suspenders. Disambiguation lesson folded into [[register-scheduled-task]] v2.3 (PATH-DISAMBIGUATOR rule: verify a live registration via `list_scheduled_tasks` + store-root path match, never from a folder's existence at an assumed path).

**Archived 2026-07-12 (Code surface):** the orphan folder moved from `Claude_Workspace\00_Governance\Scheduled\ora-pm-ledger\` to `...\Scheduled\_archive_2026-07-12_orphans\ora-pm-ledger\` (move, not delete). Independently re-confirmed via a direct `list_scheduled_tasks` call before the move: CC/MCP `ora-pm-ledger` `enabled: true`, cron `0 18 * * *`, `lastRunAt` 2026-07-11T22:09:15Z — sole live registration, untouched.

Related: the deal-inactivation gap ([[deal-decision-ledger]]) — no task writes an inactive `Stage` on pass/close, so decided deals (Liberty Office Park, `Stage: Candidate`) re-nudge weekly; `ora-stale-pipeline-nudge` STEP 2b now escalates such status-conflicts for a one-field human fix. See [[reference-property-llc-signature-roster]].

---
name: project-lams-fleet-dark-cowork-heartbeat-disabled-2026-10-30
description: "LAMS/Cowork fleet is fully dark (0/27 recurring enabled, no resume queued) as of the 2026-10-30 ora-task-integrity-guard run; ora-cowork-heartbeat (the dead-man producer) is among the disabled — awaiting Gabriel's decision"
metadata:
  node_type: memory
  type: project
  originSessionId: d05a94fb-a4ee-43d1-8d36-35a16db33eb1
  modified: 2026-10-30T15:41:18.876Z
---

2026-10-30's `ora-task-integrity-guard` run (a catch-up fire against its Monday 07:05 ET cron — the guard itself had been believed OFF per a now-corrected stale memory note, but the live registry showed `enabled:true`) found the LAMS/Cowork fleet newly disabled across 27 recurring tasks, with `disappeared[]`/`added[]` empty (diff is against the live LAMS registry, not the 45-day-stale LAMS snapshot — `snapshot_suppressed:true` confirms the stale snapshot did not drive this). `state-freshness-probe.py`'s own pause check explicitly ruled out a bounded pause: *"all 27 recurring tasks disabled with NO resume queued within 14 days -- this is not a bounded pause."* 13 `_state/` detector outputs fed by LAMS producers have gone stale up to ~1105h (~46 days), consistent with the fleet going dark around mid-September.

**Why: unknown — this is the open question.** The disabled list includes `ora-cowork-heartbeat`, the SOLE producer of the external dead-man pulse (→ Notion `35c6ecd8` → GitHub `ZeOoba/ora-cowork-watchdog`), and the LAMS copy of `automation-health-monitor`. It is plausible this is a deliberate consequence of the broader CC/MCP migration (many individual LAMS tasks have been retired piecemeal over months per other memory entries, and the live fleet summary already states "LAMS/Cowork — 0 live recurring"), but no ratified decision or resume plan for the fleet as a whole, or for `ora-cowork-heartbeat` specifically, is on file.

**How to apply:** Before assuming the dead-man chain is covered, confirm with Gabriel whether (a) the LAMS fleet's full wind-down is intentional and permanent (in which case `ora-cowork-heartbeat` needs a replacement dead-man producer, since nothing else currently fills that role), or (b) it should be restored. Do not silently re-enable `ora-cowork-heartbeat` or any of the 27 without his direction — registering/pausing/retiring scheduled tasks routes through `register-scheduled-task` per CLAUDE.md. Full per-task list and the three other 2026-10-30 alarm findings (git-uncommitted/behind-upstream SKILL.mds, 127 unbacked backup-completeness files, the stale-detector list): `event_log.md` 2026-10-30 entry; raw probe output: `~/.claude/maintenance/_state/task-folder-backup-completeness-2026-10-30.log`.

Relates to [[reference_hookify_noop_hooks_every_tool_call]] and the broader scheduler doctrine in `CLAUDE.md`'s Email & scheduler section; see also the auto-loaded `session-context.md` Integrity-guard line, updated same day.

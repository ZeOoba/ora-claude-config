---
name: reference-delete-scheduled-task-resolves-colliding-id-to-local-fleet
description: "When the SAME task id is registered on BOTH fleets, delete_scheduled_task resolves it to the LOCAL surface's entry with no fleet parameter and no disambiguation — so 'deregister the LAMS twin' run from Code deletes the LIVE CC task instead. Verify with a LAMS-only control id before firing."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 75dbb430-5eb1-48e5-bfdd-ee0bfebb696c
  modified: 2026-08-22T16:02:47.232Z
---

`mcp__scheduled-tasks__delete_scheduled_task` takes **`taskId` only** — no fleet/surface
parameter. Its schema says the id "must be an exact ID from list_scheduled_tasks", and
`list_scheduled_tasks` is surface-scoped (see [[reference_fleet_status_dual_read]]: reads are
cross-fleet via `fleet-status.py`, but registry **writes** require the correctly-scoped MCP tool
on the matching surface).

**The trap:** when the same id exists on both fleets, the delete silently binds to whichever
entry the CURRENT surface can see. An instruction phrased by fleet ("deregister the LAMS
`ora-passed-deal-tracker` entry") cannot be executed from Code at all — the only id Code's MCP
resolves is the CC entry, which is the live one you meant to keep. Deleting it loses the
registration, cron, and approved-permissions set; the SKILL.md survives on disk, but
re-registration is a supervised `create_scheduled_task` operation, not an undo.

**How to prove which fleet you are about to hit — do this before any cross-fleet delete:**
pick an id known to exist ONLY on the other fleet and check whether `list_scheduled_tasks`
returns it. Confirmed LAMS-only controls: `ora-cowork-heartbeat`,
`ora-health-guard-fail-aging-nudge`. On 2026-08-17 both were present in the LAMS registry JSON
and absent from a Code session's `list_scheduled_tasks` (38 entries = CC's 34 recurring + 4
one-time), which is what proved the scoping rather than assuming it from counts alone.

**Also still true, and the reason this matters here:** the Cowork Scheduled-sidebar
delete/trash icon is folder-destructive and documented as able to break a same-id task on the
OTHER fleet — so it is the worst option precisely when an id collision is what you are trying
to fix. Use `delete_scheduled_task` from a Cowork/LAMS session, then archive the LAMS folder.

**"A Cowork session" is NOT specific enough — this is where three attempts have died
(2026-08-17 ×1, 2026-08-22 ×2).** Cowork has two surfaces and only one of them can do this:
a **cloud-sandbox** session (device-bridge only, no native app process) carries NONE of
`list_scheduled_tasks` / `create_scheduled_task` / `update_scheduled_task` /
`delete_scheduled_task`, no matter how the task brief is worded. Only Cowork running as a
**native on-device process** ("Run this task → On your computer") carries them. Absence of the
tool is the surface, not a transient error — per `register-scheduled-task` Rule 1 you STOP,
you do not substitute Desktop Commander or a device bridge.

**Fast positive signature of the useless surface (2026-08-22):** if the session has
`mcp__remote-devices__*` tools bridging to `laptop-cshscbe6`, with Desktop Commander /
computer-use proxied *through* that bridge, it is a cloud sandbox — abort before Step 0b. A
2026-08-22 session correctly identified itself this way and declined to hand-edit
`scheduled-tasks.json` through the bridge, which would have violated Rule 2.

**Why an id collision shows up at all:** `guard.ps1` keys its backup map on task id, so two
registry entries resolving to two different `filePath`s means only one SKILL.md is guarded —
reported as `id_collisions[]`, a STEP-3 alarm in `ora-task-integrity-guard`. A *disabled* twin
still collides: pausing a task does not deregister it. Closing the collision requires removing
the duplicate registry ENTRY, which is why the fix cannot be done from the wrong surface.

**WHICH copy goes unguarded is deterministic, and it is the live one (verified 2026-08-22
against guard.ps1 lines 153–160).** Enumeration globs `*-sessions\*\*\scheduled-tasks.json`
and assigns `$ids[$t.id] = $t.filePath` with no `enabled` filter, so for a colliding id the
LAST registry enumerated silently overwrites the first. `local-agent-mode-sessions` sorts
after `claude-code-sessions`, so **the LAMS path always wins and the CC copy is the one left
unmirrored and un-restorable.** For `ora-passed-deal-tracker` that meant the guard was
protecting a superseded 4,775-byte LAMS file while the live 25,288-byte CC spec had no
coverage at all. So an id collision is an active protection gap on the surviving task, not
cosmetic tidy-up — and archiving the LAMS canonical while its registry entry lives does NOT
help: the guard just restores it from the `gov` mirror
(`Claude_Workspace\00_Governance\Scheduled\<id>\`) at the next 07:05 run.

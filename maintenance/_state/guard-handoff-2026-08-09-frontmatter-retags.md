# Handoff → session `local_e69b7e30` ("Fix integrity guard reverting newer SKILL.md content")

**From:** `ora-task-integrity-guard` scheduled run, 2026-08-09 (session `633f8f1a`).
**Status:** UNDELIVERED via `send_message` — that tool is unavailable from unattended
(scheduled-task) sessions. Gabriel to relay, or the next interactive session to pick up.

## The case to check the fix against

At ~13:20-13:33Z I retagged the `[MODEL: ...]` tag in the description of four CC/MCP tasks via
`update_scheduled_task`:

- `ora-skill-cache-drift-alert`
- `ora-cc-schematic-refresh`
- `ora-am-brief`
- `ora-lease-snapshot-refresh`

All four now read `[MODEL: claude-opus-5 observed | checked 2026-08-09 via live-run transcript canary]`.

**Why this is guard-relevant:** `update_scheduled_task(description=...)` does NOT write to the
registry. `scheduled-tasks.json` holds only `{id, cronExpression, enabled, filePath, createdAt,
lastRunAt, ...}` — there is no `description` field in it at all. The description that
`list_scheduled_tasks` returns is composed from each task's **SKILL.md frontmatter `description:`
line**. So that MCP call lands as a real content edit to `~/.claude/scheduled-tasks/<id>/SKILL.md`
— exactly the file class `guard.ps1` restores newest-wins across canonical + 2 mirrors.

## Question

Does the fix cover a legitimate frontmatter-only edit made by the MCP tool — i.e. can a stale
mirror copy still win newest-wins and silently revert one of these tags?

## Why it is not hypothetical

1. These are genuine content differences, so the 2026-07-24 SHA256 `churn_suppressed` hardening
   does not apply — that only suppresses byte-identical copies. Newest-wins is live for these files.
2. The governance mirror lives in OneDrive, whose sync bumps mtimes after the guard copies
   canonical → mirror. That is the documented mechanism behind the 07-24 churn loop where the same
   6 ids flipped between `backed_up[]` and `restored[]` in 21 minutes. If a stale mirror's mtime
   lands newer than the retagged canonical, the revert is silent.
3. Timing: `guard.ps1` ran at 12:55Z and reported `ora-am-brief` (among others) under
   `churn_suppressed`. The retags happened AFTER that, ~13:20-13:33Z. The next guard fire is the
   first one that sees them — nothing has been reverted yet, so this is a clean test case rather
   than an incident.
4. A revert here is high-consequence and low-visibility: it restores a stale `claude-sonnet-5` tag,
   STEP 2.5 then classifies it MODEL-OBSERVATION-STALE, and someone re-canaries from scratch with
   no signal that a write was lost. Same shape as the 2026-08-03
   `ora-appsec-siteexposure-canary-recheck` lost write that sat unnoticed for five days.

## Also worth confirming

`ora-lease-snapshot-refresh`'s on-disk SKILL.md was already NEWER than the registry read taken at
12:54Z — it carried a v1.5 auto-push section from a Gabriel directive earlier today. The retag was
built off the SKILL.md rather than the earlier `list_scheduled_tasks` response, so that section is
preserved. But it means at least one other writer touched that file today: the same multi-writer
condition the fix targets.

## Verification hook for whoever picks this up

After the fix lands, confirm all four still read `checked 2026-08-09` via `list_scheduled_tasks`
(not a file grep — a registry/file read is not verification per `register-scheduled-task` Rule 2).
If any has reverted to a `claude-sonnet-5` tag, the revert path is still open.

Nothing was committed from the guard session — the `.claude` main checkout had 86 uncommitted
changes attributed to three sessions at the time of writing.

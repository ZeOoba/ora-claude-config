---
name: reference-fleet-status-dual-read
description: "fleet-status.py (~/.claude/maintenance/fleet-status.py) reads BOTH CC/MCP and LAMS/Cowork scheduled-task registries directly off disk, from either surface — it is NOT scoped like the list_scheduled_tasks MCP tool. Use it before ever treating 'the other fleet' as unreachable for a READ."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 5cf0864a-7da5-4f49-95b8-389c83259d46
---

`fleet-status.py`'s `discover_registries()` globs both AppData stores directly
(`claude-code-sessions\**\scheduled-tasks.json` AND `local-agent-mode-sessions\**\scheduled-tasks.json`)
and reads whichever JSON file in each has the most tasks / newest mtime — no MCP call, no
surface scoping. Run `python C:\Users\Owner\.claude\maintenance\fleet-status.py --json` from
**either** a Code/CC session or a Cowork/LAMS session and get both fleets back in one call
(`per_fleet_enabled: {cc, lams}`, plus `onetime`/`expired_onetime`/`collisions` etc. already
cross-fleet).

**Why this matters:** the `mcp__scheduled-tasks__list_scheduled_tasks` MCP tool IS genuinely
scoped to whichever app surface is running it — a CC/MCP session's `list_scheduled_tasks` call
only ever returns the CC fleet, and vice versa on Cowork. That real limitation got
over-generalized into "the other fleet's registry is unreachable from this session" — true for
the MCP tool, false for the underlying JSON files, which `fleet-status.py` reads unconditionally.

**What happened (2026-07-15):** a stale-entry cleanup (`ora-tenant-db-dedup-remediation`, a LAMS
one-time task) got treated as fully unreachable from a CC/MCP session and handed off wholesale to
a Cowork session for a `list_scheduled_tasks` → verify round-trip — when `fleet-status.py --json`,
run directly from the CC session, would have shown the live LAMS state (task absent from
`onetime`/`expired_onetime`) in one call, no handoff needed. See `event_log.md` 2026-07-15 entries
for the full trace, and [[feedback_verify_registry_mutation_claims]] for the related "don't trust
a logged completion claim without a live re-check" lesson from the same incident.

**How to apply:** before invoking any cross-fleet handoff (a background task, a "needs Cowork
session" note, an `AskUserQuestion` about registry state) — first run `fleet-status.py --json`.
If it answers the question, no handoff is needed. Reserve actual cross-surface handoffs for
**writes** (`create_scheduled_task`/`update_scheduled_task`/`delete_scheduled_task`), which
genuinely do require the correctly-scoped MCP tool on the matching surface — the running app
needs to know about the change in its own live process state, not just the file. This
correction was written into `orphaned-task-forensics` and `fleet-advisory-remediation` v1.1
(2026-07-15), both at their real source of record `C:\Users\Owner\ora-skills\<skill>\SKILL.md`
(commit `9da6b35`) — gated (`tools/desc_lengths.py`, clean) and committed. Still needs
`tools/package_skills.py` + Gabriel's Save-skill re-import click to reach the live Cowork
runtime.

**Correction (2026-07-15, same day):** an earlier pass of this same investigation concluded
these two skills had "no git-tracked home," based on a `Glob` search of `C:\Users\Owner\ora-skills`
that returned no matches — that Glob result was simply wrong. `git ls-files` and a plain `ls -1`
in the repo immediately showed both `orphaned-task-forensics/` and `fleet-advisory-remediation/`
present and tracked (added in the same 2026-07-11 commit as their runtime-cache copies'
changelog claims). Lesson: when a Glob/search tool returns "no files found" for something
expected to exist in a git repo, cross-check with `git ls-files`/`ls` directly before concluding
absence — a negative search result is not itself proof of absence.

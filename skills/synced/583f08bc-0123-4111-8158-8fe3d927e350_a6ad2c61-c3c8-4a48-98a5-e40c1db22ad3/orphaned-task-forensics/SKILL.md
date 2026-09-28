---
name: orphaned-task-forensics
description: Root-cause a stale or missing scheduled-task output (a Notion page, dashboard section, or downstream file that silently stopped updating) back to its producer task across the dual CC/MCP + LAMS/Cowork fleet, and separately recover a scheduled task's own lost SKILL.md content via session-transcript archaeology when the file itself has vanished. Use when the user mentions: stale Notion page, this page stopped updating, what happened to [task name], recover a lost SKILL.md, a scheduled task went missing, silently dropped, trace this back to its producer, or after a health-guard/automation-health-monitor advisory flags a stale-data symptom. Formalizes a trace/recover/verify procedure used ad hoc at least 3-4 times (ora-weekly-hygiene, ora-pm-ledger, ora-health-guard, ora-treasury-yield-prefetch recoveries) before ever being codified. v1.1
license: ORA Internal
---

# Orphaned Task Forensics

Two related failure modes recur in the dual-fleet scheduler: (1) a task's *output* goes silently stale because the task that used to produce it was archived, refactored, or its duty was assumed-but-not-verified to have been absorbed elsewhere; (2) a task's *own spec file* (`SKILL.md`) is lost outright — deleted in a cleanup pass, clobbered by an app reinstall, or dropped during a fleet-consolidation merge. Both have been fixed before, each time by improvising the same investigative steps from scratch. This skill codifies them.

## Scope

Triggered by a symptom (stale page, missing file, task not in either registry) rather than a known cause — the point of this skill is finding the cause.

## Triggers

"This Notion page hasn't updated in N days", "what happened to [task]", "I can't find the SKILL.md for [task]", "this used to be automated and isn't anymore", "recover [task]'s spec", "trace this stale [page/file] back to its producer" — including when handed off from a `ora-health-guard`/`automation-health-monitor`/`ora-task-integrity-guard` advisory that flags a staleness symptom without identifying root cause.

## Inputs

- The symptom: what's stale/missing, and its last-known-good timestamp if visible (e.g. a Notion page's `fetched_at`/`last_edited_time`).
- Both scheduled-task registries — prefer `python C:\Users\Owner\.claude\maintenance\fleet-status.py --json`, which reads both fleets' `scheduled-tasks.json` directly off disk in one call from either surface (a genuine cross-fleet READ, unlike the `list_scheduled_tasks` MCP tool, which only sees the fleet its own app surface owns). Falling back to `list_scheduled_tasks` gets you one fleet only. Reserve an actual cross-surface handoff for WRITES (registry mutations), not for checking state.
- `event_log.md` and any `_archive_*` folders under `~/.claude/scheduled-tasks/` and `…\Documents\Claude\Scheduled\` (candidate homes for a task that was archived rather than deleted outright).

## Standard Workflows

### Workflow A — Trace a stale output back to its producer

1. Identify the symptom precisely: which page/file, what freshness signal proves it's stale (a `fetched_at` timestamp, a "last updated" field, or a downstream task's own advisory).
2. Search both fleets (`fleet-status.py`, `list_scheduled_tasks`, and a grep of `_archive_*` folders under both registry roots) for any task whose description or SKILL.md content references the stale artifact by name.
3. If a matching task is found live but not firing: check `lastRunAt`, throttle-skip counts, and recent run transcripts for silent failures — this is a liveness problem, not an orphaning, and belongs to `automation-health-monitor`/`ora-task-integrity-guard`, not this skill.
4. If a matching task is found in an `_archive_*` folder: **do not assume its duty was absorbed elsewhere just because it was archived as "redundant."** Grep the task(s) presumed to have absorbed it for the specific logic (the API call, the write target, the field name) that produced the stale artifact. Absorption must be confirmed in the successor's actual content, not inferred from an archival note's stated intent — an unverified "assumed absorbed" note caused a real 19-day-stale Notion page (`ora-treasury-yield-prefetch`, archived 2026-06-11 on an assumption `ora-am-brief` had absorbed it; it hadn't).
5. If no task references the artifact at all (never existed, or Workflow B applies — the task file itself is gone): proceed to Workflow B.
6. Once root cause is confirmed (never-absorbed archival, silent failure, or true gap), present Gabriel the finding via `AskUserQuestion`: revive the archived task, fold its logic into an existing task, or leave it retired with the consumer's expectation adjusted. Do not silently re-register anything — a revived producer writing the same target as an unnoticed duplicate is the near-miss this step exists to prevent.
7. Log the finding and resolution to `event_log.md` regardless of which option was chosen.

### Workflow B — Recover a lost SKILL.md via transcript archaeology

Use when a scheduled task's own `SKILL.md` (or a `SKILL.md`-adjacent script it depends on) is missing from both `~/.claude/scheduled-tasks/` and the LAMS `…\Documents\Claude\Scheduled\` tree, including their `_archive_*` subfolders — i.e. it wasn't archived, it's actually gone (a reinstall, a bad cleanup pass, a sync race).

1. Confirm it's truly gone, not just moved: search both registry roots' `_archive_*` folders and `event_log.md` for the task name before concluding it needs recovery.
2. Search local session transcripts (`~/.claude/projects/<project>/*.jsonl`, both top-level and `subagents/`) for the task name. A prior run of the task will contain a verbatim copy of its own `SKILL.md` content in the injected `<scheduled-task>` system prompt — this is the recovery source, not memory or reconstruction from memory of what it "should" contain.
3. Prefer the **most recent** transcript that shows the full content, and **cross-corroborate against a second, independent transcript** if more than one exists — a single transcript could itself be mid-edit or truncated.
4. Reconstitute the file at its correct canonical path (check `register-scheduled-task` doctrine for which fleet/path it belongs on) with the recovered content verbatim — do not "improve" or restructure it during recovery; that's a separate follow-up, not part of restoring what was lost.
5. Verify: re-run the task once (or dry-run if it has one) and confirm output matches what downstream consumers expect.
6. Log the loss and recovery to `event_log.md`, including the transcript session ID(s) used as the recovery source — this is the third+ time this exact failure mode has recurred (`ora-weekly-hygiene`, `ora-pm-ledger`, `ora-health-guard` restorations); the log entry is what lets a future recovery — or a decision to finally fix the root cause — find the pattern.

## Outputs

- Root-cause finding (producer identified, absorption confirmed/denied, or file recovered) presented via `AskUserQuestion` before any registry write.
- `event_log.md` entry documenting symptom → cause → resolution, and (Workflow B) the transcript session ID(s) recovery relied on.
- Recovered `SKILL.md` at its correct canonical path, verbatim from the transcript source.

## Boundaries

- Never silently re-register a revived task without confirming no successor already covers its duty — that creates a duplicate producer, which is worse than the original staleness.
- Never reconstruct a lost `SKILL.md` from memory of "what it probably said" — only from a verbatim transcript copy, cross-corroborated where possible.
- This skill diagnoses and recovers; it does not resolve *why* tasks keep going missing (that's a fleet-process fix — e.g. "verify successor logic before archiving" — worth raising to Gabriel as a standing-process gap if this skill fires more than once or twice more).

## Dependencies

- `fleet-advisory-remediation` skill (hands off root-cause tracing to this skill's Workflow A when an advisory flags a stale-producer symptom rather than a mechanical dark-task/expired-entry issue)
- `register-scheduled-task` skill (the actual re-registration/revival mechanics once Workflow A concludes revival is correct)
- `automation-health-monitor` / `ora-task-integrity-guard` (liveness detection that triggers this skill; not a substitute for it — they detect symptoms, this skill finds causes)

## Changelog

- v1.1 (2026-07-15): Inputs corrected — `fleet-status.py` genuinely reads BOTH registries from either surface (direct disk read, not MCP-scoped); don't treat the other fleet as unreachable for verification purposes, only for writes. Also: a registry-mutation completion claim in `event_log.md` is not itself proof — re-check live state before trusting one (see `feedback_verify_registry_mutation_claims` memory for the incident that surfaced this, `ora-tenant-db-dedup-remediation`).
- v1.0 (2026-07-11): initial. Codifies a trace/recover/verify procedure previously improvised ad hoc at least 3-4 times (`ora-weekly-hygiene`, `ora-pm-ledger`, `ora-health-guard`, `ora-treasury-yield-prefetch` recoveries) — surfaced by a workflow-audit session mining recent Claude Code transcripts for repeated uncodified patterns.

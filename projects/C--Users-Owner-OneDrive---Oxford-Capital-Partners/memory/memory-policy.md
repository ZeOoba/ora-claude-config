---
name: memory-policy
description: "How Claude stores, updates, archives, and indexes ORA memory. Rewritten 2026-06-03 (G3) — fixed living-doc set, current-state-on-top, history → event_log, archive-not-delete."
metadata: 
  node_type: memory
  type: governance
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-08-14T18:30:50.076Z
---

# ORA Memory Governance Policy (v2 — 2026-06-03)

Supersedes the v1 "category-prefix / never-overwrite / append-forever" model, which produced a 31-file junk drawer. New model: a **small fixed set of living docs that are OVERWRITTEN to reflect current state**, plus **one append-only event log** for history.

## 1. The fixed document set (~13 files; do not proliferate)
**Living docs (overwrite to current state):** `00_system_of_record.md`, `firm.md`, `user.md`, `people.md`, `markets.md`, `standards.md`, `tech.md`, `rules.md`, `projects.md`.
**Append-only:** `event_log.md` (system changes, deal milestones, decisions, closed deals — newest first).
**Operational data:** `reference_tenant_name_mappings.md`.
**Meta:** `MEMORY.md` (index), `memory-policy.md` (this).

Before creating a NEW file, prove the fact has no home in the set above. New top-level docs require a real new domain (or a new confidential deal key in `hooks/confidential-terms.json`). Default is to UPDATE an existing living doc.

## 2. Update model
- **Living docs are overwritten in place** to reflect current truth. Do not accumulate dated `## History` walls inside them.
- **History goes to `event_log.md`** — when a living-doc fact changes materially, append the change (what/why/date) to the event log, then update the living doc to the new state.
- **Corrections beat history:** if memory conflicts with observed reality, trust observation, update the living doc immediately, and log it. Say so: "Memory said X, observing Y — updating."
- **One source of truth per fact (I3).** Never assert a fact in two living docs that can disagree. Cross-reference by filename instead (e.g. "see [tech.md](tech.md)"). The governor (DSCR 1.25×/LTV 40%), digest recipients, and key paths are drift-probed.

## 3. Index rules (MEMORY.md)
Master index. Must list every living/operational/meta file as a `[link](file.md)` with a one-line description, grouped by section. **No orphaned links** (referenced but absent) and **no unlisted files** (present but unindexed) — `maintenance/memory-integrity-probe.py` enforces this. Update the index in the same action as any create/rename/archive.

### 3a. Index-hook cap (enforced at write time, 2026-07-14)
Each index hook (the description AFTER the link) is capped at **150 chars** — `doctrine-integrity-probe.py` check 9 audits it daily, and `hooks/memory-index-guard.py` (PreToolUse) now **denies** any edit that would ADD a new over-length entry, so bloat can't accumulate between audits. The guard only blocks edits that make the count *worse*: a pre-existing violation never locks the index, and a consolidation pass that fixes entries always passes. If it fires, the fix is always the same — move the detail into the linked file and leave a pointer here.

### 3b. `review_by:` — dated memories must declare their own expiry
Any memory that is only true *until some date* — a watch note, a "check back after the next run" tracking item, a deferred decision — MUST carry a frontmatter field:

```
review_by: YYYY-MM-DD
```

`memory-integrity-probe.py` warns on every run once that date has passed ("OVERDUE ... resolve it or archive it"), so a dated note can no longer quietly rot. **Report-only** — an overdue note nudges, it never fails the probe.

**Why this exists:** `project_owner_outreach_stale_guard_watch.md` set its own deadline in prose ("don't let it go stale past 2026-07-13 + a few days"), sailed past it, and nothing noticed. When it was finally checked on 2026-07-14, the answer *inverted the note's premise* — the watched guard had re-tripped, but as a TRUE positive, meaning the code fix the note prescribed would have been actively harmful. A deadline written in prose is a hope; a deadline in frontmatter is a check.

## 4. Archival (no hard deletes — I1)
Superseded or historical files move to `memory/_archive/` with a `_<reason>_<YYYY-MM-DD>.md` suffix; never `rm`. Single C: volume → archiving frees no disk, but preserves recoverability; compress (`compact /c`) for space. Closed deals: append a precedent entry to `event_log.md` (Outcome · numbers · rationale · lessons · precedent clauses).

**Event-log rollover (soft cap ~1000 lines):** `event_log.md` is the one unbounded append-wall. When it crosses ~1000 lines, run `python ~/.claude/maintenance/rollover-event-log.py` (mirrors `append-event-log.py`'s mtime-guard + atomic-replace + backup; supports `--dry-run`) to move the OLDEST entries (the bottom — it is newest-first) into `_archive/event_log_<YYYY-MM-DD>.md`, keeping roughly the most recent 600 lines live with a one-line pointer at the bottom. Never hard-delete (I1). (Rolled over 2026-07-09: event_log.md had grown to 1704 lines, ~700 over cap; entries before 2026-06-13 (session 2) moved to `_archive/event_log_2026-07-09.md`, live log trimmed to ~600 lines with a pointer at the bottom — done by hand, no script yet. Rolled over again 2026-07-16: log had grown to 3083 lines, ~3x over cap; entries before "cc-audit-army generalized to repo-generic audits" moved to `_archive/event_log_2026-07-16.md` via the new script, live log trimmed to 604 lines. `append-event-log.py` remains the single-writer path for ongoing appends — rollover is a one-time structural edit, not a new append; check for concurrent sessions before re-running.)

## 5. What to save / not save
**Save immediately:** corrections → `rules.md`; new contacts → `people.md`; deal decisions/milestones → `projects.md` (current) + `event_log.md` (the decision); validated market data → `markets.md`; system/tool/path changes → `tech.md` (+ `event_log.md`); financial conventions → `standards.md`.
**Don't save:** transient one-off task detail, raw data dumps (save the insight), content already in CLAUDE.md, unflagged speculation.

### 5a. Flush checkpoint (added 2026-08-14, harvested from external-artifact review of `task-observer`/"one-skill-to-rule-them-all" — see `event_log.md`)
"Save immediately" is a soft prompt that doesn't reliably survive cognitive load in long sessions — the insight arrives mid-flow and gets deferred past the point of recall. Tie the save-check to an action that already happens rather than trusting memory: roughly every 3rd `TaskUpdate`/TodoWrite completion, and whenever presenting a finished deliverable (artifact, file send, PR), pause and ask "does this stretch contain a correction, a confirmed judgment call, or a fact that belongs in memory?" — write it then, don't defer to end-of-session recall.

## 6. Naming
Lowercase, descriptive, no date suffixes on living docs (dates live inside / in the event log). Archived files take a dated suffix.

## 7. Staleness (report-only)
`memory-integrity-probe.py` (weekly, report-only) flags: index↔file mismatches, governor/recipient/path contradictions, and stale data (markets >90d, people unverified >30d, projects current-state >14d). It proposes; it never auto-edits memory (I6).

## Deal-state freshness (added 2026-06-11)
Deal-state sections (e.g. the "Active deal pipeline" table in [projects.md](projects.md)) carry a **"Last verified: YYYY-MM-DD"** header. If that date is **>14 days old, the section is STALE** — trust Notion (Acquisition Pipeline Tracker / Deal Sourcing Log) + the Cowork deal memory over it, then re-verify and refresh the header. Update the section **on every material deal event** (LOI, PSA, amendment, kill, close), not on a calendar. Project instructions on the Cowork surface follow the same pattern — the 2026-04→06 staleness incident (project instructions still citing the obsolete 6/12 hard close two months after it was superseded) is the precedent.

## 8. Session behavior
MEMORY.md auto-loads at start; read specific docs only when relevant (don't preload all). Create file + update index in one action. CLAUDE.md remains the authoritative session context; memory holds the detail and must not contradict it.

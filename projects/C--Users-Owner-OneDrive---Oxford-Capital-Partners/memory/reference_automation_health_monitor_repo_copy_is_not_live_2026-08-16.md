---
name: automation-health-monitor-repo-copy-is-not-live-2026-08-16
description: "The ora-skills copy of automation-health-monitor is a DIFFERENT, far older document than the live scheduled-task copy — edit the Scheduled\\ copy, never the repo one"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 04649f52-2fab-4ed0-82ed-62ce390a746b
  modified: 2026-08-22T21:57:53.004Z
---

**Editing `ora-skills\automation-health-monitor\SKILL.md` has ZERO effect on the running health monitor.** Verified 2026-08-16 by direct comparison:

| Copy | Path | Lines | Version | Steps |
|---|---|---|---|---|
| **LIVE (authoritative)** | `OneDrive…\Documents\Claude\Scheduled\automation-health-monitor\SKILL.md` | 353 | v1.24 | 19 |
| Repo (inert for execution) | `C:\Users\Owner\ora-skills\automation-health-monitor\SKILL.md` | 137 | v1.5 | 4 |

`diff` reports `1,137c1,330` — the ENTIRE file differs. These are not two revisions of one document that drifted; they are different documents. The repo copy lacks Steps 0.03/0.08/0.5b/0.5c/0.55/0.56/0.57/0.95 entirely (throttle checks, host-unavailable suppression, producer-consumer beacons, output_contract checks, held-state detection, duplicate-title cross-linking). It is roughly two months and eighteen versions behind.

**Why this is the LAMS execution model, not a bug to "fix" by syncing:** per this file's own v1.21 NOTE 2 (verified 2026-08-12 by structural inspection of both registry JSONs), **neither fleet's registry stores a `description` field at all** — `list_scheduled_tasks` renders it by READING the SKILL.md at `filePath`. So the Scheduled\ copy is the sole store for BOTH description and prompt. There is no registry desync risk when editing it directly, and no second copy to resync. This CONTRADICTS the older, more general claim in [[reference_skill_description_registry_file_desync]] — that note may still hold for packaged/plugin skills, but NOT for scheduled tasks on either fleet. Prefer the 08-12 structural verification over the older inference.

**Rule:** for any scheduled task, the file at the registry's `filePath` is authoritative. Read it FIRST; never assume the `ora-skills` copy of a same-named skill is what runs. Confirm with `fleet-status.py` (reads both fleets from any surface) plus a `wc -l`/`sha256sum` comparison before editing.

**Do NOT naively sync the repo copy up to the live one** — the live copy contains task-execution prose (fleet-specific steps, hardcoded Notion page IDs, registry paths) that does not belong in a portable skill. Reconciling them is its own scoped project, not a side effect of a task edit. Related: the Rev 13 audit's recurring "skill-mirror drift" finding (archived 2026-08-22, superseded by Rev 18 — see `_archive/project_automation_audit_rev13_2026-08-16_archived_2026-08-22.md`).

Found while adding Step 0.57 (BLOCKED-AWAITING-GABRIEL detection) — a worktree had already been cut against `ora-skills` before the comparison revealed the edit would have had no effect. See [[project_ora_strategic_constraints_2026-08-16]].

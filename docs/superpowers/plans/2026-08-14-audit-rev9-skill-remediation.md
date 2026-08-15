# Audit Rev 9 Skill Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Act on the 4 actionable findings from ORA Automation Audit Revision 9 (https://claude.ai/code/artifact/8b29049b-d7a0-4394-a602-d51e52fd21e7): split `register-scheduled-task` and `daily-brief`'s SKILL.md files to cut per-invocation token cost, and resolve two open data-quality discrepancies (`capex-budgeting` unpublish contradiction, orphaned `ora-operations-extensions:submarket-spatial-analysis` plugin registration).

**Architecture:** For the two SKILL.md splits, follow the exact precedent already proven on `acquisition-underwriting` and already partially adopted by `cowork-settings`: move non-operative content (changelogs, incident-narrative justification) out of the auto-loaded `SKILL.md` into a top-level `versions/` directory (repo-only, excluded from packaging by `tools/package_skills.py`'s `is_bundled()` — confirmed at `tools/package_skills.py:405-412`) or a `references/` directory (packaged but only read on-demand, never auto-loaded at invocation). Every operative rule stays inline verbatim; only dated incident-narrative justification and changelog entries move. The two investigation findings are research tasks that end in a decision point, not a code change — do not force them into a fix.

**Tech Stack:** Markdown SKILL.md files, `ora-skills` git repo, `tools/package_skills.py` (sanctioned packager), git worktrees for isolation.

## Global Constraints

- `~/ora-skills` is a single-writer repo (CLAUDE.md, `tech.md §2`). **Before Task 1's worktree creation, and again immediately before Task 5's commit/fast-forward, run `git log --oneline -1` and `git status --short` fresh — do not trust the readings below, which are already stale the moment this plan is saved.** At plan-writing time (2026-08-14 ~17:35 ET), HEAD was `7dc70c8` and a different, live session had just committed twice to `lease-addendum/` in the minutes before this plan was written (`c29471e` → `53488c9` → `7dc70c8`) — confirming a concurrent session is actively working in this repo right now. `README.md` also shows as modified (10 insertions) in that session's working tree.
- **`lease-addendum` packaging (the task this session was mid-procedure on before this plan was requested) is BLOCKED, not part of this plan.** Do not touch `lease-addendum/` until the concurrent session's work is confirmed settled — see Task 8.
- Neither `register-scheduled-task` nor `daily-brief` is a `SHARED_ROOT_DEPS` consumer (that list is: acquisition-underwriting, daily-brief itself is NOT one — confirm via `grep -n "SHARED_ROOT_DEPS" -A6 tools/package_skills.py` before Task 2, since this plan's author read it as of 2026-07-16's list and it may have grown), so no shared-root-dep freshness check applies to either split.
- All edits happen in an isolated worktree, never the shared checkout directly (CLAUDE.md shared-checkout rule).
- Every operative rule (the actual "what to do") in both files stays inline, verbatim, unless a task below explicitly says to cut it. When in doubt, keep it inline — this plan errs toward under-cutting rather than risking a silently dropped rule.

---

### Task 1: Claim a worktree and verify the split targets are clean

**Files:** none created yet — this is a pre-flight/isolation task.

- [ ] **Step 1: Re-verify repo state (do not reuse the Global Constraints reading above)**

```bash
cd ~/ora-skills
git log --oneline -1
git status --short
```

Expected: `register-scheduled-task/` and `daily-brief/` show no pending changes (they are not the files the concurrent session touched). If either shows uncommitted changes, STOP — do not proceed with this plan on those files; surface the conflict instead.

- [ ] **Step 2: Create the isolated worktree**

```bash
cd ~/ora-skills
git worktree add .worktrees/rev9-token-splits -b fix/rev9-token-splits
```

- [ ] **Step 3: Confirm the worktree is on the expected commit**

```bash
cd ~/ora-skills/.worktrees/rev9-token-splits
git log --oneline -1
```

Expected: matches Step 1's output exactly (same SHA).

---

### Task 2: `register-scheduled-task` — move Changelog to `versions/`

**Files:**
- Create: `~/ora-skills/.worktrees/rev9-token-splits/register-scheduled-task/versions/CHANGELOG-v2.0-v2.8.md`
- Modify: `~/ora-skills/.worktrees/rev9-token-splits/register-scheduled-task/SKILL.md` (removes lines 66-77, adds a 1-line pointer)

**Interfaces:** none — this is a pure content move, no code.

- [ ] **Step 1: Create the versions file with the moved content**

Write `register-scheduled-task/versions/CHANGELOG-v2.0-v2.8.md`:

```markdown
# register-scheduled-task — Changelog (v2.0–v2.8)

Archived from `SKILL.md` 2026-08-14 (ORA Automation Audit Revision 9 remediation — repo-only, excluded from packaging per `tools/package_skills.py`'s top-level `versions/` exclusion). Current version's changelog entry lives in `SKILL.md` itself; only superseded entries move here going forward.

- **v2.8 (2026-07-24):** Added step 4b — the `[MODEL:]` tag is now a registration-time requirement with a MANDATORY date half, and a QC-gate line item verified off the `list_scheduled_tasks` response. Added the re-enable precondition to PAUSE (a task exempt while paused is back in scope the instant it is enabled, and must be re-tagged in the same pass). Both fixes trace to `ora-task-integrity-guard`'s 2026-07-24 run: `ora-511-industrial-fallout-check` had shipped a bare undated `[MODEL: claude-sonnet-5]` that fit no classifier bucket cleanly, and three of four `MODEL-UNTAGGED` findings that day were one-time or paused tasks that should never have been counted as gaps at all. Scope/exemption rules live in `memory/reference_scheduled_task_model_standard.md` § "Tag scope & required fields" (one home — cited, not restated).
- **v2.7 (2026-07-16):** Path note corrected — the v2.0 "MSIX LocalCache path is the SAME file via virtualization, never a second store" claim is factually dead post-2026-07-05 machine migration: the MSIX store was verified EMPTY of Claude data 2026-07-16 (discovered when a cache→repo pull followed the doctrine path to a nonexistent file). Sole physical store is AppData\Roaming; rule is now probe-first with stop-and-escalate on divergence. Same correction applied same day to the Cowork master memory\CLAUDE.md SCHEDULER section and ora-skill-store-drift-check v1.8's CACHE→REPO PULL PATH. The v2.0 changelog line below is preserved as history, not doctrine.
- **v2.6 (2026-07-16):** Added the "re-home solely-run producer scripts before RETIRE" rule (setup-review finding C5) after retiring `ora-setup-audit` silently orphaned `registry-membership-probe.py` + `emit-fleet-heartbeat.py` for a week — see the RETIRE section.
- **v2.5 (2026-07-16):** Promoted the concurrent-writer check from a log-timestamp heuristic to a direct `session_info list_sessions` scan for a live sibling session, after a same-day incident where two Cowork sessions ran the identical LAMS retime handoff concurrently, converged on identical idempotent cron values (no duplicate ids — lower severity than the 2026-07-08 precedent), but collided on `event_log.md`'s file handle because neither checked for the other first and `registry-membership.log` has no visibility into cron-only edits. No data loss (spool-and-auto-drain absorbed it); the gap was purely in the pre-write check, not the write path.
- **v2.3 (2026-07-12):** Added the PATH-DISAMBIGUATOR rule to the dual-fleet model — when a same-id task may exist on both fleets, the `path` field from `list_scheduled_tasks` is the sole disambiguator (CC → `~\.claude\scheduled-tasks\`; LAMS → `Documents\Claude\Scheduled\`), and a folder found outside both store roots is an orphan, not a live registration. Added after a "retire the redundant LAMS ora-pm-ledger" task was scoped around a `00_Governance\Scheduled` path that is neither store root: the live LAMS registry had no such task (nothing to retire) and the on-disk folder there was a misfiled orphan. Lesson: verify a live registration via `list_scheduled_tasks` on the target fleet, never from a folder's existence at an assumed path.
- **v2.2 (2026-07-08):** Fixed a stale "(1)"-suffixed LAMS store path (pointed at a non-existent folder). Added the PAUSE-vs-RETIRE distinction as a hard rule after a "disable" instruction was carried out via the destructive sidebar delete, taking four unrelated CC/MCP tasks down as collateral damage. Added the cross-fleet shared-file blast-radius note (a CC redirect-stub and a same-id LAMS task can point at the same underlying OneDrive spec file). Added a concurrent-writer check, extending the ora-skills/event_log single-writer discipline to scheduled-task registry work, after two sessions independently recovered the same fleet simultaneously and registered duplicate ids. RETIRE now requires adding the task id to session-context.md's consolidated do-NOT-re-register list, not just the task's own frontmatter, after several previously-retired tasks were resurrected during the same incident because their retirement was recorded in a place nobody checked before rebuilding.
- **v2.1 (2026-06-11):** RETIRE hardened — ARCHIVE FIRST, DELETE SECOND ordering added after the sidebar-delete folder-destruction incident (UI delete hard-deletes the task folder, bypassing the Recycle Bin); RATIFIED event_log convention encoded for probe auto-ratification.
- **v2.0 (2026-06-11):** Full inversion of v1.0. MCP-only supervised registration; JSON-splice PROHIBITED (2026-06-09 registered-but-unscheduled proof); MSIX LocalCache path documented as the same file via virtualization (was wrongly framed as an alternate registry path); dual-fleet model encoded; email convention rewritten to COM-sole + ggoldberg-only routing (was Composio + cc-both, both superseded — Composio removed 2026-06-11, routing canon 2026-06-10).
- **v1.0:** Desktop Commander splice procedure (RETIRED — do not follow).
```

- [ ] **Step 2: Replace the Changelog section in SKILL.md with a pointer**

In `register-scheduled-task/SKILL.md`, find the `## Changelog` header and everything through the `v1.0` line (currently lines 66-77 — re-verify the line numbers in the worktree copy before cutting, Task 1 confirmed the commit matches but always re-grep rather than trust a cached line number). Replace the full block with:

```markdown
## Changelog

- **v2.8 (2026-07-24):** Added step 4b (`[MODEL:]` tag, mandatory date half) and the PAUSE re-enable re-tag precondition. Full history back to v1.0: `versions/CHANGELOG-v2.0-v2.8.md`.
```

- [ ] **Step 3: Verify the word-count reduction**

```bash
wc -w register-scheduled-task/SKILL.md register-scheduled-task/versions/CHANGELOG-v2.0-v2.8.md
```

Expected: `SKILL.md` drops from 2,885 to roughly 2,885 − 673 + 30 ≈ **2,242 words**; the new versions file shows roughly 690 words. (These are estimates from the plan's own word-count pass — record the actual numbers here when you run it; do not treat the estimate as ground truth.)

---

### Task 3: `register-scheduled-task` — move incident-narrative asides to `references/incident-history.md`

**Files:**
- Create: `~/ora-skills/.worktrees/rev9-token-splits/register-scheduled-task/references/incident-history.md`
- Modify: `~/ora-skills/.worktrees/rev9-token-splits/register-scheduled-task/SKILL.md` (5 targeted replacements)

**Interfaces:** none.

- [ ] **Step 1: Create the reference file**

Write `register-scheduled-task/references/incident-history.md`:

```markdown
# register-scheduled-task — Incident History & Rule Justification

Full narrative behind the compressed rules in `SKILL.md`. Not auto-loaded — read this only when you need the "why," not the "what to do" (which stays in `SKILL.md`). Packaged with the skill (unlike `versions/`, which is repo-only).

## Path note

Prior correction, 2026-07-08: the LAMS SKILL.md store path previously read a "(1)"-suffixed OneDrive folder that does not have a `Documents\Claude\Scheduled` directory at all (a second/legacy synced OneDrive account on this machine). Corrected 2026-07-16, superseding the v2.0 "same-file-via-virtualization" framing: the MSIX store `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\...` was verified to hold NO Claude data on this machine — no `Claude` folder under `LocalCache\Roaming` at all, recursive search zero hits. The post-2026-07-05-migration install does not write through MSIX virtualization.

## Cross-fleet shared-file risk (2026-07-08)

A CC/MCP task's `~/.claude/scheduled-tasks/{id}/SKILL.md` is very often just a thin redirect stub whose actual content lives at the SAME OneDrive path a LAMS task of the same id would use for its own full spec. If a task with a given id ever exists on BOTH fleets (which "never duplicate ids across either fleet" should prevent, but a same-id collision has now happened during a recovery), deleting or overwriting that file on ONE fleet's surface can silently destroy the OTHER fleet's task content too — even though only one registry entry was touched.

## Path disambiguator (2026-07-12 incident)

A "retire the redundant LAMS `ora-pm-ledger`" task was scoped around a `00_Governance\Scheduled\ora-pm-ledger\` folder; the live LAMS registry had no such task and that on-disk folder was an orphan in the wrong convention — net: nothing to retire, and a runbook built on the wrong path would have hard-aborted at best.

## PAUSE — sidebar-delete incident (2026-07-08)

A "disable these" instruction was carried out via the Cowork Scheduled-sidebar's delete/trash icon, destroying shared spec files and breaking tasks on the OTHER fleet too (see Cross-fleet shared-file risk above).

## RETIRE — do-NOT-re-register list incident (2026-07-08)

Several previously-retired tasks were resurrected during a fleet-recovery incident because their retirement was recorded only in the task's own SKILL.md frontmatter, not in one checkable place — a scattered record does not stop a future rebuild from re-creating it. This is why RETIRE requires adding the task id to `session-context.md`'s consolidated do-NOT-re-register list.

## RETIRE — archive-first-delete-second incidents (2026-06-11, 2026-07-08)

The Cowork Scheduled-sidebar delete is FOLDER-DESTRUCTIVE — it hard-deletes the task's SKILL.md folder along with the registry entry, bypassing the Windows Recycle Bin (OneDrive online recycle bin ~93d is the only recovery). 2026-06-11: `scheduled-task-integrity-guard`'s kept-by-design backups were lost this way. 2026-07-08: recurred, four unrelated CC/MCP tasks broken as collateral damage via the cross-fleet shared-file risk above.

## RETIRE — orphaned producer-script incident (2026-06-16, found 2026-07-16)

Retiring `ora-setup-audit` (2026-06-16) silently orphaned two downstream scripts it alone ran (`registry-membership-probe.py`, `emit-fleet-heartbeat.py`) — the external cross-fleet dead-man froze for a week (2026-07-09→07-16) with its own GitHub alarm sitting unread, before the 2026-07-16 setup review found the gap and fixed it by adding the two scripts as a new step inside `ora-task-integrity-guard`. A task's own SKILL.md naming what it "replaces" or "folds in" is not proof nothing downstream was missed.

## Concurrent-writer incidents

**2026-07-08:** two sessions (one on CC/MCP, one on Cowork/LAMS) independently recovered the same failed fleet at the same time without knowing about each other, registering duplicate task ids minutes apart across both fleets. Caught only by re-reading the live registry JSON directly rather than trusting an earlier `list_scheduled_tasks` response.

**2026-07-12 (lower severity, motivated the primary-check promotion in SKILL.md):** two Cowork sessions ran the identical LAMS retime handoff concurrently. Both converged on the same correct cron values for the same 3 existing task ids (idempotent, no duplicate ids created), but their simultaneous `append-event-log.py` writes collided on the `event_log.md` file handle (WinError 5 on Windows), and neither session had checked for a live sibling before starting — `registry-membership.log` had nothing to show since no ids were added or dropped. The append script's spool-and-auto-drain design absorbed the collision with zero data loss, but the check that should have prevented the redundant work entirely didn't exist yet. A `list_sessions` call at the start of either session would have shown the other as `running` with a matching title.
```

- [ ] **Step 2: Replace the dual-fleet path/risk/disambiguator bullets (3 bullets)**

In `register-scheduled-task/SKILL.md`, find (original lines 21-23):

```
- **Path note (corrected 2026-07-16 — supersedes the v2.0 same-file-via-virtualization framing):** the MSIX store `C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\...` holds NO Claude data on this machine — verified 2026-07-16: no `Claude` folder under `LocalCache\Roaming` at all, recursive LocalCache search zero hits. The post-2026-07-05-migration install does not write through MSIX virtualization; the SOLE physical store is `C:\Users\Owner\AppData\Roaming\Claude\...`. Probe (`Test-Path`) before sourcing either path; if both ever exist AND diverge (e.g. a future reinstall reintroduces MSIX virtualization), stop and escalate rather than pick a side. Never write to either directly (Rule 2). Prior correction retained, 2026-07-08: the LAMS SKILL.md store path above previously read a "(1)"-suffixed OneDrive folder that does not have a `Documents\Claude\Scheduled` directory at all (a second/legacy synced OneDrive account on this machine) — always verify with a directory check before trusting either "(1)" or no-suffix if a future re-sync reintroduces the ambiguity.
- **CROSS-FLEET SHARED-FILE RISK (2026-07-08):** a CC/MCP task's `~/.claude/scheduled-tasks/{id}/SKILL.md` is very often just a thin redirect stub whose actual content lives at the SAME OneDrive path a LAMS task of the same id would use for its own full spec. If a task with a given id ever exists on BOTH fleets (which Rule "never duplicate ids across either fleet" should prevent, but a same-id collision has now happened during a recovery), deleting or overwriting that file on ONE fleet's surface can silently destroy the OTHER fleet's task content too — even though only one registry entry was touched. Before deleting (not just disabling) any task folder, check whether a same-id task exists on the other fleet and whether its spec might share that path.
- **PATH-DISAMBIGUATOR — which copy am I about to touch? (2026-07-12):** When a same-id task may exist on both fleets, the `path` field returned by `list_scheduled_tasks` is the SOLE reliable disambiguator between the two copies: CC/MCP copy → `path` under `~\.claude\scheduled-tasks\{id}\`; LAMS/Cowork copy → `path` under `...\Documents\Claude\Scheduled\{id}\`. Pause/retire ONLY the entry whose `path` matches the fleet you intend to act on; never act on an entry whose `path` sits under the OTHER fleet's root. **A SKILL.md folder found on disk OUTSIDE both store roots (e.g. `Claude_Workspace\00_Governance\Scheduled\{id}\`) is an orphaned/misfiled copy, NOT evidence of a live registration** — the only proof of a live registration is the task appearing in `list_scheduled_tasks` on that fleet. If a task brief, memory note, or runbook cites a store path that is neither root, treat it as stale and verify against `list_scheduled_tasks` + the two roots above before acting — do not scope a retirement around an unverified path. (2026-07-12 incident: a "retire the redundant LAMS `ora-pm-ledger`" task was scoped around a `00_Governance\Scheduled\ora-pm-ledger\` folder; the live LAMS registry had no such task and that on-disk folder was an orphan in the wrong convention — net: nothing to retire, and a runbook built on the wrong path would have hard-aborted at best.)
```

Replace with:

```
- **Path note:** sole physical store is `C:\Users\Owner\AppData\Roaming\Claude\...` — the MSIX LocalCache path holds no Claude data on this machine. Probe (`Test-Path`) before sourcing either path; if both exist AND diverge, stop and escalate. Never write to either directly (Rule 2). Full verification history: `references/incident-history.md` § Path note.
- **CROSS-FLEET SHARED-FILE RISK:** a CC/MCP task's SKILL.md is often a thin redirect stub pointing at the SAME OneDrive path a same-id LAMS task uses for its own full spec — deleting or overwriting one can silently destroy the other. Before deleting (not disabling) any task folder, check whether a same-id task exists on the other fleet and whether its spec might share that path. Full mechanism + incident: `references/incident-history.md` § Cross-fleet shared-file risk.
- **PATH-DISAMBIGUATOR:** when a same-id task may exist on both fleets, the `path` field from `list_scheduled_tasks` is the SOLE reliable disambiguator (CC/MCP → `~\.claude\scheduled-tasks\{id}\`; LAMS/Cowork → `...\Documents\Claude\Scheduled\{id}\`). Act only on the entry whose `path` matches your target fleet. **A SKILL.md folder found OUTSIDE both store roots is an orphaned/misfiled copy, NOT evidence of a live registration** — the only proof is the task appearing in `list_scheduled_tasks`. Full incident precedent: `references/incident-history.md` § Path disambiguator.
```

- [ ] **Step 3: Trim the PAUSE bullet's incident parenthetical**

Find:

```
**NEVER use the Cowork Scheduled-sidebar's delete/trash icon for a pause** — that control performs RETIRE's destructive step (see below) regardless of intent, and there is no undo. If you are not certain the sidebar has a distinct disable-only control separate from delete, ask before touching it, or do the pause from Claude Code via `update_scheduled_task` instead (2026-07-08 incident: a "disable these" instruction was carried out via sidebar delete, destroying shared spec files and breaking tasks on the OTHER fleet too — see cross-fleet shared-file risk above).
```

Replace with:

```
**NEVER use the Cowork Scheduled-sidebar's delete/trash icon for a pause** — that control performs RETIRE's destructive step (see below) regardless of intent, and there is no undo. If you are not certain the sidebar has a distinct disable-only control separate from delete, ask before touching it, or do the pause from Claude Code via `update_scheduled_task` instead. Incident precedent: `references/incident-history.md` § PAUSE — sidebar-delete incident.
```

- [ ] **Step 4: Trim the RETIRE do-NOT-re-register parenthetical**

Find:

```
Add the task id to the consolidated "do NOT re-register" list in `session-context.md` (2026-07-08: several previously-retired tasks were resurrected during a recovery because the retirement was only recorded in that task's own SKILL.md frontmatter, not in one checkable place — a scattered record does not stop a future rebuild from re-creating it).
```

Replace with:

```
Add the task id to the consolidated "do NOT re-register" list in `session-context.md` — a retirement recorded only in the task's own frontmatter is not enough (incident: `references/incident-history.md` § RETIRE — do-NOT-re-register list incident).
```

- [ ] **Step 5: Trim the archive-first-delete-second and producer-script parentheticals**

Find:

```
**RETIRE — ARCHIVE FIRST, DELETE SECOND (hard ordering):** the Cowork Scheduled-sidebar delete is FOLDER-DESTRUCTIVE — it hard-deletes the task's SKILL.md folder along with the registry entry, bypassing the Windows Recycle Bin (OneDrive online recycle bin ~93d is the only recovery; 2026-06-11 incident: `scheduled-task-integrity-guard` kept-by-design backups lost this way; 2026-07-08 incident: recurred, four unrelated CC/MCP tasks broken as collateral damage via the cross-fleet shared-file risk above). Therefore: (1) MOVE the task folder to the dated `_archive_*` folder, (2) VERIFY the move landed, (3) only THEN delete the registry entry in the UI. Log planned removals to `memory/event_log.md` with the literal token `RATIFIED` + the task id — `registry-membership-probe.py` auto-ratifies such drops (≤14d window) instead of raising a false [ACTION].
- **RETIRE — re-home solely-run producer scripts BEFORE deleting the registry entry (added 2026-07-16, setup-review finding C5):** before retiring any task, grep `maintenance/*.py`, `hooks/*.py`, and every other live task's SKILL.md for scripts this task is the SOLE invoker of. If any are found, re-home them into a surviving task's steps (or explicitly retire the script too, with the same archive-first ordering) BEFORE completing this retirement — never after. Root incident: retiring `ora-setup-audit` (2026-06-16) silently orphaned two downstream scripts it alone ran (`registry-membership-probe.py`, `emit-fleet-heartbeat.py`) — the external cross-fleet dead-man froze for a week (2026-07-09→07-16) with its own GitHub alarm sitting unread, before the 2026-07-16 setup review found the gap and fixed it by adding the two scripts as a new step inside `ora-task-integrity-guard`. A task's own SKILL.md naming what it "replaces" or "folds in" is not proof nothing downstream was missed — this is the same producer-orphaning class the do-NOT-re-register list above prevents for the task itself, one level down, for what the task silently ran on the side.
```

Replace with:

```
**RETIRE — ARCHIVE FIRST, DELETE SECOND (hard ordering):** the Cowork Scheduled-sidebar delete is FOLDER-DESTRUCTIVE — it hard-deletes the task's SKILL.md folder along with the registry entry, bypassing the Windows Recycle Bin (OneDrive online recycle bin ~93d is the only recovery). Therefore: (1) MOVE the task folder to the dated `_archive_*` folder, (2) VERIFY the move landed, (3) only THEN delete the registry entry in the UI. Log planned removals to `memory/event_log.md` with the literal token `RATIFIED` + the task id — `registry-membership-probe.py` auto-ratifies such drops (≤14d window) instead of raising a false [ACTION]. Incidents behind this ordering: `references/incident-history.md` § RETIRE — archive-first-delete-second incidents.
- **RETIRE — re-home solely-run producer scripts BEFORE deleting the registry entry:** before retiring any task, grep `maintenance/*.py`, `hooks/*.py`, and every other live task's SKILL.md for scripts this task is the SOLE invoker of. If any are found, re-home them into a surviving task's steps (or explicitly retire the script too, with the same archive-first ordering) BEFORE completing this retirement — never after. A task's own SKILL.md naming what it "replaces" or "folds in" is not proof nothing downstream was missed. Root incident: `references/incident-history.md` § RETIRE — orphaned producer-script incident.
```

- [ ] **Step 6: Trim the two concurrent-writer incident paragraphs**

Find:

```
**2026-07-08 incident:** two sessions (one on CC/MCP, one on Cowork/LAMS) independently recovered the same failed fleet at the same time without knowing about each other, registering duplicate task ids minutes apart across both fleets. Caught only by re-reading the live registry JSON directly rather than trusting an earlier `list_scheduled_tasks` response.

**2026-07-12 incident (lower severity, motivated the primary-check promotion above):** two Cowork sessions ran the identical LAMS retime handoff concurrently. Both converged on the same correct cron values for the same 3 existing task ids (idempotent, no duplicate ids created), but their simultaneous `append-event-log.py` writes collided on the `event_log.md` file handle (WinError 5 on Windows), and neither session had checked for a live sibling before starting — `registry-membership.log` had nothing to show since no ids were added or dropped. The append script's spool-and-auto-drain design absorbed the collision with zero data loss, but the check that should have prevented the redundant work entirely didn't exist yet. A `list_sessions` call at the start of either session would have shown the other as `running` with a matching title.
```

Replace with:

```
Two incident precedents motivate the checks above (duplicate-id registration, and a same-day event_log.md write collision from an idempotent concurrent edit) — full narrative: `references/incident-history.md` § Concurrent-writer incidents.
```

- [ ] **Step 7: Verify word count and structural integrity**

```bash
wc -w register-scheduled-task/SKILL.md register-scheduled-task/references/incident-history.md
grep -c "^- \*\*" register-scheduled-task/SKILL.md   # sanity: bullet count didn't collapse below expected
```

Record actual before/after word counts here.

---

### Task 4: `daily-brief` — move Changelog to `versions/`

**Files:**
- Create: `~/ora-skills/.worktrees/rev9-token-splits/daily-brief/versions/CHANGELOG-v2.0-v2.9.md`
- Modify: `~/ora-skills/.worktrees/rev9-token-splits/daily-brief/SKILL.md` (removes the `## CHANGELOG` section, currently lines 348-359)

**Interfaces:** none.

**Scope note:** unlike `register-scheduled-task`, daily-brief's Sections 1-9 are ALL executed every single run ("Execute all 9 sections in sequence") — they are not optional/mode-gated reference material, so they stay inline in full. The "WHY THE 1-MATCH BRANCH CHANGED" callout (in DELIVERY NOTES) is a deliberate anti-regression guard placed exactly where a future editor would need to see it before "simplifying" the dedup logic back to something unsafe — **do not move it**, even though it reads like an incident narrative. Moving it would weaken the protection it exists to provide. Only the Changelog moves.

- [ ] **Step 1: Create the versions file**

Write `daily-brief/versions/CHANGELOG-v2.0-v2.9.md` with the full content currently at `daily-brief/SKILL.md` lines 348-359 (the `v2.9` through `v2.0` entries — copy verbatim; content omitted here for brevity but must be copied exactly, not summarized, when this step executes) under a header:

```markdown
# daily-brief — Changelog (v2.0–v2.9)

Archived from `SKILL.md` 2026-08-14 (ORA Automation Audit Revision 9 remediation — repo-only, excluded from packaging). Current version's changelog entry lives in `SKILL.md` itself; only superseded entries move here going forward.

[... v2.9 through v2.0 entries, copied verbatim from SKILL.md lines 348-359 ...]
```

- [ ] **Step 2: Replace the Changelog section in SKILL.md with a pointer**

Replace the `## CHANGELOG` section through the `v2.0` line with:

```markdown
## CHANGELOG

- **v2.9 (2026-08-11):** Corrected the Patch 3 pre-create dedup guard's 1-match branch — overwrite is now permitted only for a page this session created; any other match is a completed prior run (skip publication AND the send). Full history back to v2.0: `versions/CHANGELOG-v2.0-v2.9.md`.
```

- [ ] **Step 3: Verify word-count reduction**

```bash
wc -w daily-brief/SKILL.md daily-brief/versions/CHANGELOG-v2.0-v2.9.md
```

Expected: `SKILL.md` drops from 4,681 to roughly 4,681 − 765 + 40 ≈ **3,956 words**.

---

### Task 5: Package, verify, commit, land

**Files:**
- Modify: none new: this task packages and verifies Tasks 2-4's output.

**Interfaces:**
- Consumes: the edited `register-scheduled-task/` and `daily-brief/` directories from Tasks 2-4.

- [ ] **Step 1: Run the sanctioned packager against both skills (validates frontmatter + structure, does not install)**

```bash
cd ~/ora-skills/.worktrees/rev9-token-splits
python tools/package_skills.py /tmp/rev9-package-check register-scheduled-task daily-brief
```

Expected: exit 0, `description N/1024 OK` for both, forward-slash entry list, no error about the new `versions/`/`references/` files.

- [ ] **Step 2: Re-verify fresh git state before committing (Global Constraints — do not skip)**

```bash
cd ~/ora-skills
git log --oneline -1
git status --short
```

If the concurrent session's work has NOT settled (still shows unexpected changes outside this worktree's scope), pause and reconcile before proceeding — do not force a merge.

- [ ] **Step 3: Commit inside the worktree**

```bash
cd ~/ora-skills/.worktrees/rev9-token-splits
git add register-scheduled-task/ daily-brief/
git commit -m "$(cat <<'EOF'
refactor(skills): split changelog/incident-narrative out of register-scheduled-task and daily-brief

Follows the acquisition-underwriting core+reference precedent (Rev 9 audit
finding): register-scheduled-task drops from 2,885w to ~2,242w, daily-brief
from 4,681w to ~3,956w. Both are top-15-by-usage skills where every
invocation loads the full SKILL.md — moving non-operative changelog/incident
history to versions/ (repo-only) and references/ (packaged, not auto-loaded)
reduces steady-state token cost without touching any operative rule.

EOF
)"
```

- [ ] **Step 4: Fast-forward main and remove the worktree**

```bash
cd ~/ora-skills
git merge --ff-only fix/rev9-token-splits
git worktree remove .worktrees/rev9-token-splits
git branch -d fix/rev9-token-splits
```

- [ ] **Step 5: Flag for reimport**

Both skills are already-installed (`anthropic-skills:register-scheduled-task` rank 3, `anthropic-skills:daily-brief` rank 11), so this commit makes them repo-newer than the runtime cache. Run:

```bash
python tools/pending_reimport.py candidates
```

Confirm both skills appear, then hand off to the `package-and-stage-skill` skill for the actual Cowork reimport (separate skill, separate Save-skill click — this plan's scope ends at the commit).

---

### Task 6: Investigate the `capex-budgeting` unpublish contradiction

**Files:** none — read-only investigation, no code change expected.

**Interfaces:** produces a decision point for Gabriel, not a merge.

- [ ] **Step 1: Re-confirm the live catalog state**

Check whether `anthropic-skills:capex-budgeting` is still present in the currently-loaded skill list (it was as of Rev 9, 2026-08-14) and whether its description still shows the 2026-08-12 update marker.

- [ ] **Step 2: Grep for any event_log/memory record of a republish or an unpublish-reversal**

```bash
cd ~/ora-skills
grep -rn "capex-budgeting" --include="*.md" -i "$HOME/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md"
```

Look specifically for any entry between 2026-08-09 (the recorded unpublish) and 2026-08-12 (the live update) that mentions capex-budgeting, republishing, or a Save-skill click on it.

- [ ] **Step 3: Check the repo-side commit history for the 2026-08-12 change**

```bash
cd ~/ora-skills
git log --oneline -- capex-budgeting/ | head -10
```

This confirms the repo WAS edited 2026-08-12 (expected — Rev 9 cited its description's own changelog note), but a repo commit is not evidence of a store republish (same distinction this artifact's own methodology already draws for install verification). It only proves someone edited the skill; it does not explain why it's live in the catalog despite the recorded unpublish.

- [ ] **Step 4: This is a Gabriel decision point, not a fixable defect**

No tool on the Code surface reaches the claude.ai Skills store to check publish state directly (same limitation Revision 5 itself recorded). Present findings from Steps 1-3 and ask Gabriel directly: was `capex-budgeting` re-published intentionally after the 2026-08-09 unpublish (in which case the audit record should be corrected, not the skill), or should it be unpublished again (in which case that's a Gabriel action on claude.ai, not a repo change)? Do not take either action unilaterally.

---

### Task 7: Investigate the orphaned `ora-operations-extensions:submarket-spatial-analysis` plugin registration

**Files:** none — read-only investigation.

- [ ] **Step 1: Check whether the plugin is version-controlled in the repo**

```bash
cd ~/ora-skills
ls plugins/ora-operations-extensions/ 2>&1
cat plugins/ora-operations-extensions/plugin-build.json 2>&1
```

Recall from `package-and-stage-skill`'s own doctrine: `submarket-spatial-analysis` was confirmed 2026-07-16 to be a member of the `ora-operations-extensions` bundle (alongside `deal-retirement`), which is why it must install via a plugin rebuild, never a standalone Save-skill click.

- [ ] **Step 2: Check current settings.json for any trace of this plugin under a different key form**

```bash
grep -i "ora-operations" "$HOME/.claude/settings.json"
grep -i "ora-operations" "$HOME/.claude/plugins/installed_plugins.json"
```

- [ ] **Step 3: Check `.claude.json` for an `@inline`-style registration**

The Rev 7 finding already on record in this same artifact (see "The finding that changes the plan" section) established that `ora-operations-extensions:` registers as `@inline` in `.claude.json`, not through `settings.json`'s `enabledPlugins` — the same mechanism as the `anthropic-skills:` namespace. Check:

```bash
grep -c "ora-operations-extensions" "$HOME/.claude.json"
```

If this returns a nonzero count, the "orphaned" framing from Rev 9 was wrong — it's not missing from `enabledPlugins` because it's dead, it's missing because `@inline` plugins were never expected to appear there (same pattern as `anthropic-skills:`). Correct the finding rather than pursue a cleanup.

- [ ] **Step 4: Report finding, no unilateral cleanup**

If Step 3 confirms `@inline` registration is intact, this closes as a Rev 9 false alarm (an artifact for the next audit revision, not a fix). If Step 3 finds no trace anywhere, escalate to Gabriel as a genuinely orphaned registration (parallel to the `chrome-devtools-plugins` re-clone pattern this same artifact root-caused in Revision 8) — do not deregister anything without confirming `submarket-spatial-analysis` (CLAUDE.md-canonical) still resolves correctly through some other path first, since it must not become unreachable.

---

### Task 8: Resume `lease-addendum` packaging (blocked, not scoped to this plan)

**Files:** none new — resumes the paused `package-and-stage-skill` procedure from before this plan was requested.

- [ ] **Step 1: Re-check for the concurrent session, fresh**

```bash
cd ~/ora-skills
git log --oneline -5 -- lease-addendum/
git status --short
```

- [ ] **Step 2: Decision gate**

If `lease-addendum/` still shows uncommitted changes, or `git log` shows a commit newer than `7dc70c8` that this plan hasn't seen, the other session is still active — do NOT resume packaging. Wait, or ask Gabriel whether that session is done.

If the tree is clean and HEAD is stable across two checks a few minutes apart, resume `package-and-stage-skill`'s Entry point A from Step 1 (confirm source / git-clean — already satisfied), proceeding through Steps 2-8 as originally scoped. This is a full re-invocation of that skill, not a step folded into this plan.

---

## Self-Review

**Spec coverage:** Task 2-3 cover the `register-scheduled-task` split; Task 4 covers `daily-brief`; Task 6 covers the capex-budgeting discrepancy; Task 7 covers the orphaned-plugin finding; Task 8 covers the paused lease-addendum handoff explicitly requested to be noted, not re-planned. All 4 audit findings + the 1 paused task are addressed.

**Placeholder scan:** Every extraction step gives exact find/replace text. The one deliberately-not-fully-transcribed block (Task 4 Step 1's changelog body) is flagged inline as "must be copied exactly, not summarized, when this step executes" rather than left as a bare TODO — the source text is fully available at `daily-brief/SKILL.md:348-359` for whoever executes this task.

**Type/interface consistency:** N/A — no code interfaces in this plan; all tasks are file-content moves or read-only investigations.

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

## Bounded pause — LAMS fleet paused with no resume (2026-08-17)

Gabriel asked to pause all routines until Friday 2026-08-21 5:00 PM ET. The CC/MCP half was executed correctly: 35 recurring tasks disabled, and a one-time resume `ora-routine-pause-resume-08-21` registered to fire 2026-08-21 17:00 ET, naming all 35 ids explicitly and passing ONLY `enabled: true` on each `update_scheduled_task` call so hand-edits made during the window survive.

The LAMS/Cowork half did not get that far. The pause landed, but the matching `ora-lams-routine-pause-resume-08-21` was dispatched to a cloud-sandbox Cowork session, which carries none of the registry MCP tools (see SKILL.md § Dual-fleet registry model, surface note). That session correctly halted at Rule 1 rather than improvising — but the halt happened AFTER the pause had already committed, so the fleet was left disabled with no scheduled restore.

Verified against both registries the same day (read-only): CC/MCP 35 of 40 tasks disabled with the resume pending; LAMS 27 of 28 disabled with no resume of any kind — the sole enabled entry being `ora-counsel-review-standard-positions-2027`, a one-time task firing in August 2027. So the CC fleet restores itself on Friday and the LAMS fleet does not restore at all.

Three properties of the failure, each of which the v2.12 rule addresses separately:

1. **Split-by-surface is fine; split-by-turn is not.** A dual-fleet pause naturally divides by surface, since neither fleet's MCP tools reach the other registry. What failed is that one fleet's pause COMMITTED while its own resume registration was still pending on another surface. Pause and resume are one operation per fleet, not two deliverables that can land in different turns.
2. **"Pause all routines" is fleet-ambiguous.** The instruction named no fleet. Reporting "N tasks paused" after touching one registry reads as complete to everyone downstream.
3. **The pause swallowed its own detectors.** `ora-cowork-heartbeat` (dead-man chain → Notion `35c6ecd8…` → GitHub watchdog) and `automation-health-monitor` both live on LAMS and were both disabled by the sweep. The two mechanisms that would otherwise have surfaced a 4-day silent gap were themselves inside it. The only thing that flags the asymmetry is a reminder line in the CC resume task's step-6 summary email — which does not send until 2026-08-21 17:00 ET, i.e. at the end of the window rather than the start.

Separately, the CC resume task's step 5 instructs that re-enabling must NOT bump any `[MODEL:]` freshness date, because re-enabling is not an observation (`memory/feedback_verified_null_vs_inferred_null.md`). That is correct, and it contradicts a literal reading of the v2.8 PAUSE bullet's "re-tag it with a CURRENT date in the same pass." v2.12 reconciles them: the v2.8 rule binds a hand re-enable where the model is actually observed; an automated bulk resume leaves the dates alone and simply returns the task to scope for its next normal currency check.

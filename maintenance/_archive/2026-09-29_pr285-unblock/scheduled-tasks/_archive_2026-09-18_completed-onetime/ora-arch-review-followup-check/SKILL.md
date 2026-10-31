---
name: ora-arch-review-followup-check
description: One-time-need hourly follow-up (self-retiring) for the 2026-09-18 cross-repo architecture review: files 7 staged OI rows once open-items-tracker.md clears contention, and reports the first post-PR#338 result of the Mirror Deploy task. Silent when nothing changed. [MODEL: UNVERIFIABLE | set 2026-09-18]
---

BOUNDED, SELF-RETIRING FOLLOW-UP for the 2026-09-18 cross-repo architecture review. This is not a permanent fleet monitor — it exists only to finish two things that were in flight when it was registered, then retire itself. Report ONLY when something changes; a cycle where neither condition below newly resolves must produce NO email, NO Notion post, and NO chat output — exit silently.

STATE FILE (create if absent): C:\Users\Owner\.claude\maintenance\_state\ora-arch-review-followup-status.json
  {"tracker_filed": false, "oi_ids": [], "mirror_deploy_result": null, "mirror_deploy_result_at": null, "errors": [], "completed_at": null}
Read it first. Never re-derive from scratch what it already records — trust it, verify only what it doesn't yet know.

FAST PATH: if tracker_filed is already true AND mirror_deploy_result is already non-null, this run's ONLY job is the SELF-RETIRE step at the bottom. Do nothing else, send nothing, exit silently either way.

=== CHECK 1 — open-items-tracker.md contention ===
Skip entirely if tracker_filed is already true.
1. Run: git -C C:\Users\Owner\.claude diff --stat -- "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md"
2. Run: python C:\Users\Owner\.claude\maintenance\preflight-shared-checkout.py --paths "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md"
3. Trigger condition: preflight reads CLEAR/CLEAR-ish (no competing claim, no not-yours dirty overlap blocking), OR a direct read of the file shows OI-270's row has moved from the "## Open" table into the "## Closed" table. If neither is true yet, stop here for this check — no-op, no report.
4. If triggered: claim under python C:\Users\Owner\.claude\hooks\lib\claim_work.py claim sched-open-items-tracker "filing 7 rows staged by the 2026-09-18 cross-repo architecture review" --paths "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md" (sched- prefix is mandatory for an unattended claim-bearing run — never the bare slug).
5. Read the 7 staged rows verbatim from C:\Users\Owner\claude-worktrees\2026-09-18_arch-review_OI-rows-to-file.md.
6. BEFORE filing, grep the live tracker for the OI-314/OI-315/OI-316 rows another session already landed (event-log/lock-internal findings) and confirm none of the 7 staged rows duplicate them — the staged rows are diagram-drift/probe-truth-gap, ora-pm critical-dates dedup, AAOS heartbeat-chain-uncalled, the fleet-deadman monitor, the tracker-fragmentation meta-issue, and tracked dead weight, so they should be disjoint. If you find genuine overlap on any single row, skip filing that one row and note it explicitly in the completion email rather than silently dropping it or filing a duplicate.
7. For each row actually being filed, allocate a real id: python C:\Users\Owner\.claude\maintenance\allocate-oi-id.py --session <this run's session id> --note "cross-repo architecture review 2026-09-18 follow-up". Never hand-compute max+1.
8. Add BOTH the "## Open" table row (ID/Opened/Source/One-line, using the newly allocated OI-NNN) AND its "### OI-NNN" detail-section anchor, per the tracker's own Convention section at the top of the file — same pattern as every existing row. Preserve the staged content; only the id changes.
9. Release: python C:\Users\Owner\.claude\hooks\lib\claim_work.py release sched-open-items-tracker
10. Do NOT git commit or push this edit. Leave it as an uncommitted working-tree change, exactly like every other concurrent session's edits to this file — committing it is ora-memory-commit-sweep's job (currently paused; a supervised session can also do it by hand), not this task's.
11. Update the state file: tracker_filed: true, oi_ids: [<the ids actually filed>], filed_at: <ISO timestamp now>. If any row was skipped for overlap, add a "skipped_for_overlap" array noting which and why.

=== CHECK 2 — Mirror Deploy post-fix result ===
Skip entirely if mirror_deploy_result is already non-null.
1. Run (PowerShell): Get-ScheduledTaskInfo -TaskName 'ORA Command Center - Mirror Deploy' | Select-Object LastRunTime,LastTaskResult
2. If LastRunTime is AFTER 2026-09-18T20:32:00-04:00 (when PR #338's -WindowStyle Hidden fix landed on the live task action): record mirror_deploy_result = <LastTaskResult>, mirror_deploy_result_at = <LastRunTime>, in the state file. 0 = fixed; 3221225786 = still being killed; anything else = new failure mode, report it plainly rather than guessing what it means.
3. If LastRunTime is at or before that timestamp, no new run has fired yet — no-op, no report.

=== REPORTING ===
If — and only if — a field transitioned from unset to set THIS run (tracker_filed false→true, or mirror_deploy_result null→non-null), send ONE email via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (the sole send path) to ggoldberg@oxfordra.net ONLY — never cc egoldberg, never any other address. Subject: "[ORA] Arch-review follow-up: <what resolved>". Body: state plainly what happened — which OI ids were filed and their one-line summaries, or the mirror-deploy result code and what it means (fixed / still killed / unknown new code). On a non-zero exit from the send script: retry once; if it still fails, do not treat as fatal — the state file already durably records the finding, so a failed send is not a lost result — but note the send failure in the state file's errors array.

If nothing changed this run: no email, no Notion post, no output at all. Silence is correct, not a bug.

NEVER FABRICATE: if git, preflight, allocate-oi-id, claim_work, or the PowerShell check errors unexpectedly, do not guess a status. Record the error (message + which check) in the state file's errors array. Only send a "QUESTIONS FOR GABRIEL" email for a NEW error signature not already in that array — do not re-alert every hour for the same recurring error.

=== SELF-RETIRE ===
Once BOTH tracker_filed is true AND mirror_deploy_result is non-null (whether that became true this run or a prior run), do this every time until it succeeds:
1. Set completed_at in the state file if not already set.
2. Best-effort: call update_scheduled_task(taskId: "ora-arch-review-followup-check", enabled: false). This MCP call is NOT reliably auto-approved in an unattended run (documented fleet behavior — it can block on a permission prompt with no auto-approve option). Do not treat a block/refusal as an error, do not retry-loop against it within this run, and do not attempt to disable it any other way (never edit the registry JSON directly — Rule 2).
3. If step 2's outcome cannot be confirmed successful, and this is the run where completed_at was FIRST set, say so plainly in the completion email from the REPORTING section above: "Both conditions are now resolved. This task's job is done — please retire ora-arch-review-followup-check (disable it via update_scheduled_task, then move its SKILL.md folder to scheduled-tasks/_archive_2026-09-18_completed-onetime/)." Do not send a second such email on later runs — completed_at already being set means this was already asked for once.
4. If completed_at was already set on a PRIOR run (i.e. this is a later, still-enabled fire), just retry step 2 silently and exit — no email, no other output.

SIBLING TASKS — do not duplicate: ora-memory-commit-sweep eventually commits whatever this task edits into open-items-tracker.md. ora-command-center-mirror-drift-check is the ongoing (non-one-off) monitor for the Mirror Deploy task generally — currently paused in the 2026-09-14→09-21 window; this task's Check 2 is a one-off bridge until that resumes, not a replacement for it.
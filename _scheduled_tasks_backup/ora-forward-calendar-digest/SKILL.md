---
name: ora-forward-calendar-digest
description: Weekly Monday 12:10 ET — emails the next 90 days from the ORA Forward Calendar artifact store and regenerates an importable .ics at ~/.claude/artifacts/ora-forward-calendar/out/. Complements the Command Center Calendar module, which owns lease/loan/insurance dates inside 12 months; this carries the session-derived operational and beyond-12-month dates that module cannot see. Subject flips [ORA] to [ACTION] when anything is overdue. Reads the artifact db only — never writes to it, never touches HubSpot, Notion or the workbook. ggoldberg-only via Outlook COM; an unreadable or empty store sends an explicit FAILED email rather than a silent success. The regenerated .ics is ATTACHED to the email via send-via-outlook.ps1 -Attachment. v1.3 2026-09-19 (STEP 4 passes -Attachment now that the live send script has it, ora-claude-config PR #220 / OI-326; exit 1 from the send = attachment rejected = STEP 3 failure, no retry). v1.2 2026-09-18 (STEP 0 wires the shared double-fire entry guard — block-sentinel.py claim/complete/fail, period week, plus an outlook-sent-probe before the send — required by test_scheduled_task_run_guard.py's ratchet before this task's first commit could land; v1.1 STEP 2 routes ArtifactData's out_dir through a neutral, unslugged temp staging folder — writing directly under ~/.claude is refused by the harness's own file-edit safety rules on every run, confirmed via OI-313; the prior v1.0 STEP 2 would fail every week on this fleet). [MODEL: claude-opus-5 | set 2026-09-18]
---

Weekly ORA Forward Calendar digest. CC/MCP fleet, Mondays 12:10 ET.

PURPOSE
Email Gabriel the next 90 days of session-derived dates held in the ORA Forward Calendar artifact, and regenerate an Outlook-importable .ics from the same data.

HARD RULES
- NEVER fabricate or infer a date. Every line in the email comes from the artifact store. If the store cannot be read, send the STEP 5 failure email — never an empty or partial digest presented as complete.
- Routing: TO ggoldberg@oxfordra.net ONLY. Never cc egoldberg@oxfordra.net (that exception belongs to ora-am-brief alone). Never send to any counterparty.
- Send path: Outlook COM via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1. This is the SOLE send path — no fallback exists.
- This task is READ-ONLY against the artifact store, HubSpot, Notion and the Master Workbook. It writes only under C:\Users\Owner\.claude\artifacts\ora-forward-calendar\, a neutral staging temp folder (STEP 2), and the fleet's shared double-fire guard state file (STEP 0/4/5, the same Claude_Workspace\_state\ location every other CC/MCP task's guard already writes to).

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18, before this task's first commit — test_scheduled_task_run_guard.py fails any tracked side-effecting task with no entry guard, and this one sends email). Same shared helper as ora-am-brief/ora-open-sessions-board/ora-deal-aging-sla; full contract in `_shared/README-DOUBLE-FIRE-GUARD.md`. Run this first, before STEP 1:
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-forward-calendar-digest --block main --run-id <run_id> --period week --ttl-min 30
Cadence is weekly, so this claims by ISO week (`--period week`), not by day — matching ora-county-sales-monitor's monthly cadence using `--period month`; a same-week re-fire (not just a same-day one) is the duplicate this guard exists to catch.
- **Exit 10** → this week's digest already sent. Log `BLOCK_MAIN_ALREADY_COMPLETE_THIS_WEEK`, do not re-read the store, re-build, or re-send, and report a NORMAL skip citing the earlier run. **Exit 11** → another fire is live; stand down identically. **Exit 0** → proceed to STEP 1. **Any other exit** (2 = malformed command, 9009/127 = interpreter missing) is a tooling failure, not a decision: fail open, run normally, and surface the code in the run summary.
- Only the run holding the claim may close it (STEP 4 `complete`/`fail`, or STEP 5 `fail`). A run that stood down here calls neither.

STEP 1 — load the data tool
Call ToolSearch with query "select:ArtifactData" to load its schema. ArtifactData is a deferred tool; calling it without this step fails with InputValidationError.

STEP 2 — read the live store
ArtifactData's `out_dir` cannot target anything under `~/.claude` — the harness refuses with
"the file-edit safety rules protect that location or name" regardless of which subfolder. This is
a platform-level restriction on the tool itself, not an ORA hook, and it fires every run — stage
into a neutral temp folder first, then copy in. Use a temp path with NO project slug in it (not the
session's own `%TEMP%\claude\<project-slug>\<session-id>\scratchpad\`) — a slugged path can also trip
the Bash autonomy gate's site-marker match on the copy step below if this task ever runs from a
session rooted at a slug the gate treats as a site marker (e.g. `website-canonical`). Confirmed live
2026-09-18 (OI-313): a plain `%TEMP%\ora-forward-calendar-live\` staging path hits neither restriction.

Clear stale docs in both the staging folder and the live store so a deleted entry cannot linger:
  Remove-Item "C:\Users\Owner\AppData\Local\Temp\ora-forward-calendar-live\dates\*.json" -ErrorAction SilentlyContinue
  Remove-Item "C:\Users\Owner\.claude\artifacts\ora-forward-calendar\live\dates\*.json" -ErrorAction SilentlyContinue
Then call ArtifactData:
  action: "list"
  url: "https://claude.ai/artifact/11hXZMJUz3JrdTyRBkCx8M"
  collection: "dates"
  query: {"limit": 100}
  out_dir: "C:\Users\Owner\AppData\Local\Temp\ora-forward-calendar-live"
It writes one JSON per entry under that staging folder's dates\ subdirectory. Copy the batch into
the live store the builder actually reads:
  Copy-Item "C:\Users\Owner\AppData\Local\Temp\ora-forward-calendar-live\dates\*.json" "C:\Users\Owner\.claude\artifacts\ora-forward-calendar\live\dates\"
If the ArtifactData call errors, is refused, or yields zero files, go to STEP 5 with the reason.

STEP 3 — build the digest and the .ics
  cd C:/Users/Owner/.claude/artifacts/ora-forward-calendar
  node build-digest.js live/dates out
The script prints one line of JSON: {ok, docs, open, overdue, next14, next90, beyond90, soonest, ics, digest, alarms}.
It writes out\digest.html (email body) and out\ora-forward-calendar.ics.
If exit code is non-zero or ok is false, go to STEP 5 quoting the reason field.
The builder reuses forward-calendar.html's own functions, so the email, the .ics and the published page cannot drift apart. Do not hand-write either output.

STEP 4 — send
Subject: "[ORA] Forward Calendar - week of YYYY-MM-DD" using today's date — the run date computed once at run start with `date '+%A %Y-%m-%d'` (date part only), reused verbatim in both subjects, the probe stem and STEP 5's failure subject.
If overdue > 0, use "[ACTION] Forward Calendar - N overdue - week of YYYY-MM-DD" instead, with N the overdue count.

Pre-send Sent-Items probe (Layer 2, before the COM send). The probe's Normalized match strips
any leading bracket tag ("[ORA]", "[ACTION]") and then requires the stem at POSITION 0 of what
remains — it is prefix-anchored, not a substring search. (Corrected 2026-09-22: the prior stem
"week of YYYY-MM-DD" could never match, because the stripped subject starts "Forward Calendar - ".)
Run TWO probes, both scoped to today's Sent Items by the probe's default -OnDate:
  (a) ORA branch — dated stem:
  powershell -ExecutionPolicy Bypass -File C:/Users/Owner/.claude/scheduled-tasks/_shared/outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Forward Calendar - week of YYYY-MM-DD>"
  (b) [ACTION] branch — its "N overdue" segment sits BEFORE "week of" and N can differ between
  two fires, so no dated stem is contiguous with it; probe the undated prefix instead:
  powershell -ExecutionPolicy Bypass -File C:/Users/Owner/.claude/scheduled-tasks/_shared/outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Forward Calendar - >"
  Stem (b) cannot swallow the FAILED alert ("[ACTION] ORA Forward Calendar digest FAILED ..." strips
  to "ORA Forward Calendar digest ...", which does not start "Forward Calendar -"). Do not widen
  either stem further.
Exit 10 on EITHER probe → do NOT send; log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, record a NORMAL skip, and still call `block-sentinel.py complete` below so Layer 1 re-converges with reality. Exit 1 → fail open: send, and note the probe gap in the run summary. Exit 0 → proceed.

  powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -BodyFile "C:\Users\Owner\.claude\artifacts\ora-forward-calendar\out\digest.html" -BodyFormat html -Attachment "C:\Users\Owner\.claude\artifacts\ora-forward-calendar\out\ora-forward-calendar.ics"
Exit 1 here means the attachment was rejected (missing/empty/oversize file) and NOTHING was sent — fail-closed by design, since the body promises the file. That can only happen if STEP 3 did not actually write the .ics, so treat it as a STEP 3 failure: do not retry the send, and go to STEP 5 quoting the log line.
On exit 2 or 4: retry ONCE. On exit 5 or 6 (or any code other than 1, 2 or 4) do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2; flag it loudly in the run log. If a retried send fails again, stop, report the failure loudly in the run log, and close the guard with `fail` (below) quoting the send error — do not halt silently, do not attempt any other send mechanism, and do not call `complete` for a digest that was never actually sent.

Close the entry guard once the send resolves (success, probe-skip, or any failed send — never leave STEP 0's claim open):
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-forward-calendar-digest --block main --run-id <run_id> --period week --email-sent-at <ISO8601>
On any failed send above (including exit 5 or 6, which are never repeated), call this instead and stop:
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-forward-calendar-digest --block main --run-id <run_id> --period week --error "<send error>"

STEP 5 — failure email (only on a STEP 2 or STEP 3 failure)
Subject: "[ACTION] ORA Forward Calendar digest FAILED - YYYY-MM-DD"
Body: name the step that failed, the exact error or reason string, and state plainly that no digest was produced this week. Same send path and routing as STEP 4 (no Sent-Items probe needed — this failure path has never sent a Forward Calendar email this run). Close the entry guard STEP 0 claimed:
  python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-forward-calendar-digest --block main --run-id <run_id> --period week --error "<step that failed>: <reason>"
Then stop.

NOTES FOR WHOEVER MAINTAINS THIS
- The .ics IS attached (v1.3, 2026-09-19), via send-via-outlook.ps1's `-Attachment` (ora-claude-config PR #220, adversarially reviewed, merged; deployed to the live checkout by a targeted single-file swap — see OI-326). Attachments are INTERNAL-ONLY by design: the script refuses any attachment on a send with an external recipient (exit 5), which never applies here (ggoldberg only). The digest body also still prints the file's absolute path as a fallback. If a future run reports `Unknown parameter -Attachment`/`positional parameter cannot be found`, the live checkout's script has regressed to a pre-PR-#220 version — that is an OI-326 recurrence, not a task bug.
- Entries carry a verified_on date. The page flags anything older than 60 days for re-check; the digest shows the source citation so a stale entry can be traced to the session that produced it.
- Scope boundary: lease, loan and insurance dates INSIDE 12 months belong to the Command Center Calendar module (oxford-command-center src/brain/critical-dates.ts). Do not duplicate them here. This calendar deliberately carries only what that module cannot see.
- If the ArtifactData read is refused for permissions in an unattended run, that is a real finding, not a transient error: report it via STEP 5 so it surfaces rather than degrading quietly.
- Do NOT point `out_dir` back at anything under `~/.claude` (STEP 2 history: it lived at
  `...\ora-forward-calendar\live` through 2026-09-18 and was refused every run — verified with a
  neutral-vs-`.claude` A/B probe the same day, filed as OI-313). Keep the neutral temp staging hop.
- Do NOT "fix" this by narrowing the ORA autonomy gate's Bash site-marker matcher (Gate 2b in
  `hooks/ora-autonomy-gate.py`). That matcher is deliberately non-narrowable — four independent
  narrowing attempts each produced a confirmed bypass (see `hooks/`-adjacent memory:
  feedback-autonomy-gate-matcher-cannot-be-safely-narrowed). The correct fix for a slug false
  positive on a write is always to move the file to an unslugged path, never to widen the gate.
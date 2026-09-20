---
name: ora-resume-0921-attend-reminder
description: One-time 2026-09-21 09:30 ET — emails ggoldberg a reminder that ora-routine-pause-resume-09-21 fires at 10:00 and CANNOT complete unattended (the Desktop runner never auto-approves update_scheduled_task). Sends and stops. [MODEL: claude-sonnet-5 | set 2026-09-17]
---

One-time reminder. Send ONE email, then stop. Do not re-enable, retime, or run any scheduled task yourself -- this task only sends a reminder.

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18; run before sending). One-time tasks are still exposed to the fleet-wide overnight-offline catch-up burst (README-DOUBLE-FIRE-GUARD.md) and to a manual re-run before auto-disable takes effect -- either would send Gabriel a duplicate "come to the machine" reminder. Run this first:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-resume-0921-attend-reminder --block main --run-id <run_id> --ttl-min 30
```

- **Exit 10** -> already sent. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY` and stop -- do not send again.
- **Exit 11** -> another fire is live. Stand down identically.
- **Exit 0** -> proceed to send.

**Only the run that holds the claim may call `complete` or `fail`.** A run that stood down (exit 10 or 11) calls neither. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

**PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before the send below).** Layer 2 of the STEP 0 guard, dated stem:

```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: 10:00 today: CC fleet resume needs you at the machine>"
```

No date suffix needed on the stem -- this is a one-time task that fires exactly once (2026-09-21), so the subject text alone is already unambiguous; unlike a recurring task's dated stem, there is no cross-day collision risk to guard against here.

Exit 10 -> do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, and still call `block-sentinel.py complete` below so Layer 1 re-converges. Exit 1 -> fail open: send anyway, and note the probe gap in the report.

Send to ggoldberg@oxfordra.net ONLY, no cc, via:
```
powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
```

Subject: "[ACTION] 10:00 today: CC fleet resume needs you at the machine"

Body, in plain prose:
- ora-routine-pause-resume-09-21 fires at 10:00 ET today and re-enables the 37 CC/MCP tasks paused on 09-14.
- It CANNOT finish unattended: the Claude Desktop scheduled-task runner does not auto-approve mcp__scheduled-tasks__update_scheduled_task, and permission mode does not lift that (proven 2026-09-11, register-scheduled-task v2.23). Someone must open that run in the Desktop app and approve each call. Batched, the approvals go quickly.
- The run is longer than a plain resume: after re-enabling it runs a merge-forward unblock (STEP 1b) and then 9 catch-up task runs whose Monday slots fall before 10:00. Expect 1-2 hours typically, up to ~5 in the worst case.
- If nobody attends it, the 37 tasks stay paused -- including ora-checkout-merge-forward, which is what left the checkout 159 commits behind main in the first place.
- If today does not work, the resume can be re-fired later from a live session; it is a one-time task and nothing else depends on the 10:00 slot.

Then verify the send: report SEND OK or SEND FAIL from the script's output. On a non-zero exit, retry once, then stop. Never fabricate delivery.

Close the STEP 0 claim now that the email has landed (or been skipped as an already-sent duplicate per the probe above):

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-resume-0921-attend-reminder --block main --run-id <run_id> --email-sent-at <ISO8601>
```

If the run aborts before sending (both retries in the paragraph above failed), call `fail` instead so the claim does not strand at IN_PROGRESS for the full TTL:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-resume-0921-attend-reminder --block main --run-id <run_id> --error "<what broke>"
```
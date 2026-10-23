# LAMS/Cowork R-05: pre-apply checklist

Adapted from section 5 of the CC batch guide. Tick every box in the native Cowork session before the first `update_scheduled_task`. One fleet at a time (CC/MCP is done; this is LAMS only), one spec at a time.

## 1. Surface and authority
- [ ] The session is a native on-device Cowork session with the scheduled-tasks MCP tools loaded (`list_scheduled_tasks`, `update_scheduled_task`). A cloud sandbox or a Claude Code session does not qualify: stop.
- [ ] Gabriel is present to approve each supervised `update_scheduled_task` call (skill `register-scheduled-task`).
- [ ] The session will pass ONLY `taskId` and `prompt`. No cron, fireAt, enabled, description changes; no create / delete / registry edits.

## 2. Prerequisites carried over from the CC batch
- [ ] The R-05 script is live: `grep -c DedupTaskId C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1` is non-zero.
- [ ] R-05 soak is clean: no unexpected `SEND-STATE-UNKNOWN` / `QUARANTINE` lines in `send-log.txt` over the soak window.
- [ ] The CC-fleet edits (PR #334 and the live-checkout apply) are done, so the wording is not split across fleets in a surprising way.

## 3. Registry and concurrency
- [ ] `C:/Users/Owner/.claude/maintenance/_state/registry-membership.log`: latest timestamp is not from another session in the last hour; if it is, stop and reconcile ownership first.
- [ ] `python ~/.claude/maintenance/preflight-shared-checkout.py` is not needed for the OneDrive spec files themselves, but run it for any `~/.claude` file you also touch (for example the mirror step for `automation-health-monitor`).
- [ ] `list_scheduled_tasks` snapshot saved BEFORE (id, cron / fireAt, enabled, description, lastRunAt) for all 23 targets plus the full registry row count. Expected today (2026-10-19): every recurring row `enabled:false`; the only `enabled:true` row among targets is `ora-counsel-review-standard-positions-2027` (fireAt `1817211600000`); `ora-lams-fleet-resume-20260911` one-time and disabled (fireAt `1789156860000`).
- [ ] Confirm the two CC-only deal scans are not involved (they are CC specs; nothing here touches them).

## 4. Per-spec readiness (repeat inside the loop)
- [ ] Live SKILL.md re-read; CRLF-normalized sha256[:12] equals the `sha base` in `lams-r05-edits-table.md`. A mismatch means the live spec drifted: STOP, re-base the replacement on the live text, show Gabriel the diff; never overwrite.
- [ ] Each old string occurs exactly once in the live text.
- [ ] `SKILL.md.bak-r05-20261019` created beside the spec, same bytes, create-only; its sha equals sha base.
- [ ] The new text's CRLF-normalized sha equals `sha new` BEFORE it is passed to the tool.
- [ ] The three ASCII-style specs contain no new non-ASCII characters (`ora-dd-critical-tracker`, `ora-health-guard-fail-aging-nudge`, `ora-underwrite-doctrine-staleness-check`).
- [ ] The canary (`ora-gis-endpoint-liveping`) passed all three questions in the brief, section 3.0, before any other spec.

## 5. Decisions needed from Gabriel before the affected spec
- [ ] `automation-health-monitor`: ratify the three-hunk wording (l.10, l.425, Step 3 send), the exit-6 audit sentence, whether to mirror into github.com/ZeOoba/ora-skills (the synced skill), and whether to add a changelog line.
- [ ] `ora-skill-text-audit`: ratify the `Publish:` handling for a state-unknown fallback send (keep enum and add words, or add a new enum value).
- [ ] Skip or apply for `ora-health-guard-fail-aging-nudge` (retired 2026-09-22) and `ora-lams-fleet-resume-20260911` (spent one-time). Default: skip.

## 6. After each spec and after the batch
- [ ] File sha (normalized) equals `sha new`; `.bak` still equals sha base.
- [ ] `list_scheduled_tasks` row identical to the snapshot except content; `enabled` unchanged (a flip to true: re-disable that row only and stop).
- [ ] Whole-registry diff vs the BEFORE snapshot shows no other row changed.
- [ ] Apply log updated; rollback path (brief section 6: specs first, script last) still available.

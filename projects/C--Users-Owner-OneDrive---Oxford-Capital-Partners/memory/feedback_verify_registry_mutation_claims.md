---
name: feedback-verify-registry-mutation-claims
description: A scheduled-task registry mutation (delete/update) logged as complete in event_log.md is not confirmed until a follow-up list_scheduled_tasks call on the SAME fleet shows it took effect — a CC/MCP-surface session calling delete against a LAMS-fleet taskId (or vice versa) can silently no-op.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5cf0864a-7da5-4f49-95b8-389c83259d46
---

**What happened (2026-07-13 → 2026-07-15):** the LAMS one-time task `ora-tenant-db-dedup-remediation` was flagged 2026-07-13 as an orphaned expired entry needing supervised Cowork-side cleanup. A 2026-07-14 session logged (twice, duplicated) that it had retired the task via the supervised `delete_scheduled_task` MCP tool AND archived its SKILL.md folder per Hard Invariant 6. The archival half was real (confirmed on disk 2026-07-15, in `_archive_2026-07-14_stale-cleanup\`). The deletion half was not — the 2026-07-15 fleet-status run still showed the entry open/expired, unfired. Full trace: `event_log.md` 2026-07-15 entry ("Orphaned-task forensics...") and the mirrored handoff entry in `Claude_Workspace/01_Workspace/memory/event_log.md`.

**Why:** `delete_scheduled_task` / `list_scheduled_tasks` are scoped to whichever registry the calling session's surface (CC/MCP vs LAMS/Cowork) actually reaches. A session on one surface calling delete against the other fleet's taskId can silently no-op — the tool call doesn't necessarily raise an error the session treats as fatal — while an accompanying filesystem action (moving/archiving the SKILL.md folder, reachable from either surface) succeeds independently. The combined log entry then reads as fully true ("retired + archived") when only the file half actually happened.

**How to apply:** after any scheduled-task registry mutation a log entry will describe as done, re-run `list_scheduled_tasks` on the SAME surface/fleet the mutation targeted and confirm the entry is actually gone/changed *before* writing the completion claim. If the mutation targets the *other* fleet from the current session (a cross-fleet cleanup), do not log it as complete at all — hand off explicitly (a dated "action needed" entry naming the exact taskId and verification steps) and let that handoff's own session do the verifying re-list. Related but distinct from [[feedback_verify_subagent_safe_claims]] (that one: a subagent's grep-for-references check misses prose-embedded dependencies; this one: a session's own tool-call completion claim isn't confirmed without a same-surface read-back).

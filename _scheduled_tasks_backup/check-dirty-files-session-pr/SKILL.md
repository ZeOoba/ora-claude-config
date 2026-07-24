---
name: check-dirty-files-session-pr
description: PAUSED 2026-07-21 — event overtaken (tracked session's work superseded by PR #20, conflict resolved). Retire fully from a regular session.
---

One-off event-triggered check (NOT a standing automation — self-retire once the event fires).

Context: on 2026-07-20, a Claude Code session (title "Dirty files from active session", session_id local_996226f2-8fd4-4f00-949f-729b26f29774, cwd C:\Users\Owner\OneDrive - Oxford Capital Partners) was working directly on the main ~/.claude checkout with uncommitted changes, mid-workaround on a commit-provenance-guard.py false-positive that PR #20 (github.com/ZeOoba/ora-claude-config, branch claude/inspiring-pascal-d23945, commit ebb321f) already fixed. That session also holds an uncommitted edit to projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_commit_provenance_guard.md that will conflict with a section PR #20 already committed. Gabriel asked to be reminded once that session pushes a branch or opens a PR.

Each run, do this:
1. Run: gh pr list --repo ZeOoba/ora-claude-config --state all --limit 20 --json number,title,headRefName,state,author,updatedAt,createdAt
2. Look for any PR/branch that plausibly corresponds to that session's work — i.e. touches projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/reference_commit_provenance_guard.md, open-items-tracker.md, or event_log.md, created/updated after 2026-07-20T23:16 local time, and is NOT PR #20 itself. Also check `git -C "C:/Users/Owner/.claude" status --short` and `git -C "C:/Users/Owner/.claude" log --all --oneline -5` for a newly pushed branch even if no PR was opened yet.
3. If nothing found yet: do nothing further this run (no notification, no message to Gabriel) — just let the next scheduled run check again.
4. If a matching push/PR IS found: send Gabriel a clear notification identifying the PR/branch (number, title, URL if a PR exists) and a one-line note about the reference_commit_provenance_guard.md conflict risk to watch for when merging/rebasing. Then call mcp__scheduled-tasks__delete_scheduled_task with taskId "check-dirty-files-session-pr" to self-retire so this stops polling — do this in the same run, after sending the notification.

Do not modify any files, do not push/commit anything, do not message the other session — read-only check plus (conditionally) one notification to Gabriel and self-deletion.
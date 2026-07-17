---
name: check-code-audit-image-pass
description: One-time check on the concurrent "Oxford Realty Advisors code audit" session's site-wide responsive-image pass in website-canonical
---

Gabriel asked to check in 20 minutes on a concurrent Claude Code session that was mid-flight editing the same repo. Do the following and report back to Gabriel directly (this is a one-time check-in, not a recurring task — after reporting, no further action needed):

1. Call mcp__ccd_session_mgmt__list_sessions and find the session with session_id "local_d2295c9f-26f6-4502-9227-0ee564fc46dd" (title was "Oxford Realty Advisors code audit"). Note its isRunning status and lastActivityAt. If it's no longer in the list or archived, note that too.
2. Call mcp__ccd_session_mgmt__list_events with session_id "local_d2295c9f-26f6-4502-9227-0ee564fc46dd" and limit 20 to see its most recent activity/conclusion.
3. In C:/Users/Owner/website-canonical, run `git status --short` and `git log --oneline -5` to see whether the working tree has settled (no longer has the in-flight uncommitted changes to index.html, portfolio.html, track-record.html, available-space.html, tenant-application.html, markets/*.html, and the images/*-480w.avif/.webp files and re-encoded images/*.avif/.webp) or whether those changes have now been committed.
4. Report to Gabriel (ggoldberg@oxfordra.net) via a brief message/notification: is the other session done, still running, or stalled; and is the website-canonical working tree now clean/committed or still holding those uncommitted changes. Do not commit, push, revert, or otherwise modify anything in website-canonical yourself — this is a read-only status check only. Do not touch oxfordra.net deploys (Invariant 2 applies).
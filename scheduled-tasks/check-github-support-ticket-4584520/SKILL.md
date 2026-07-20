---
name: check-github-support-ticket-4584520
description: One-time check on GitHub Support ticket #4584520 (ora-pm sensitive-data purge request), then auto-disables
---

This is a ONE-TIME check, no memory of any prior conversation. Context: on 2026-07-19, Gabriel submitted a GitHub Support ticket (via his own authenticated GitHub session in Claude-in-Chrome) requesting GitHub purge a cached/orphaned git blob still retrievable via the Git Data API for the private repo ZeOoba/ora-pm, kept alive by refs/pull/2/head (a GitHub-internal PR ref). Ticket number: #4584520. He asked to have this checked the next day.

Do this:
1. Use the claude-in-chrome MCP tools (load via ToolSearch if deferred: tabs_context_mcp, navigate, computer, read_page) to check if Chrome is available with his logged-in GitHub session. Navigate to https://support.github.com/tickets/personal/0 (his personal tickets list).
2. Find ticket #4584520 ("Request to purge cached/orphaned blob still retrievable via Git Data API after h... (Repositories)"). Open it and read its current status and any replies from GitHub Support.
3. If Chrome/the browser tools are unavailable, or the ticket can't be located, or the session isn't logged in — say so plainly. Do NOT fabricate a status.
4. Report findings via email: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "GitHub Support ticket #4584520 - status check" -BodyFile <temp.html> -BodyFormat html (ggoldberg@oxfordra.net ONLY, no cc, per routing canon). Body: current ticket status (open/closed/waiting-on-you/etc.), any reply text from GitHub Support summarized, and a direct link to the ticket. If the check itself failed (browser unavailable, couldn't locate ticket, etc.), say that clearly instead — do not send a false "still open, no updates" if you couldn't actually verify it.
5. On email send failure: retry once; if it still fails, this is a one-time task so just note the failure in the final summary rather than escalating further.

This is a report-only, read-only check — do not reply to the ticket, do not click any action buttons on GitHub's support portal, do not modify anything. This task auto-disables after this single run.
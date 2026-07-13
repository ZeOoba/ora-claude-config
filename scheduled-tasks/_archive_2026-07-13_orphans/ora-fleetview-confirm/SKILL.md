---
name: ora-fleetview-confirm
description: One-time midnight check — attempts live visual confirmation of Claude Code Desktop's "FleetView" multi-session dashboard via computer-use; falls back to a session-list snapshot + honest non-confirmation if unattended access can't be granted. Emails ggoldberg only. One-off, auto-disables after firing.
---

ONE-TIME DIAGNOSTIC TASK — fires once at 2026-07-11T00:00 ET, then auto-disables. Not a recurring automation; no sibling skill duplicates this.

BACKGROUND: Earlier on 2026-07-10, Gabriel asked whether there's a way to view all running Claude Code Desktop sessions simultaneously in an organized way. That session found:
(a) A working MCP tool, `mcp__ccd_session_mgmt__list_sessions`, that returns every session with an `isRunning` flag — confirmed live, showing multiple concurrently running sessions at the time.
(b) A textual hint in this app's own Agent tool catalog: the catch-all "claude" agent's description says "FleetView's default when no agent name is typed" — implying this specific Claude Code Desktop build ships a native "FleetView" multi-session dashboard, distinct from anything in Anthropic's public docs.
(c) Via public-docs research (code.claude.com), a DIFFERENT, publicly-documented pair of features that must not be conflated with FleetView: "Agent View" (the `claude agents` terminal command — grouped table of sessions) and a two-session split-pane (Ctrl/Cmd+click a sidebar session). These are not FleetView.

GOAL: Get an actual visual/behavioral confirmation of what FleetView is and how it's accessed, since (b) above is inferred from a UI string, not observed directly.

STEPS:
1. Call `mcp__ccd_session_mgmt__list_sessions` (limit 30). Include this fresh snapshot in the report regardless of what else succeeds below — it's the one thing guaranteed to work unattended.
2. Attempt visual confirmation via computer-use:
   a. Call `request_access` for the Claude / Claude Code Desktop application.
   b. If access is granted: bring the app forward, screenshot it, and look specifically for any sidebar toggle, tab, or view switcher labeled "Fleet", "FleetView", "Agents", or similar that shows multiple sessions at once in a grid/list with live status. Describe precisely what you find.
   c. If `request_access` cannot complete — EXPECTED at midnight with nobody present to click the approval dialog, not a bug — do NOT retry in a loop. Note this plainly and move to step 3.
3. Never fabricate what the UI shows. If computer-use wasn't usable, report only what's actually confirmed (step 1's data + the textual hint from the agent catalog), explicitly flag visual confirmation as still outstanding, and recommend Gabriel do a 30-second live check himself next time he's at the machine.
4. Write a findings report, under 200 words: (a) the fresh session snapshot, (b) whether FleetView was visually confirmed and what it showed, or precisely why not, (c) a one-line recommendation for how Gabriel should view all running sessions at once going forward (FleetView if confirmed; otherwise the best fallback of Agent View / list_sessions / the existing `/open-sessions` board).
5. Send the report by email via the Outlook COM script ONLY: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. TO ggoldberg@oxfordra.net ONLY (no cc). Subject: "FleetView confirmation — 2026-07-11". On a non-zero exit code: retry once; if it still fails, do not halt — flag the send failure loudly in this task's completion output instead.

If anything here is ambiguous or a required data source is missing, say so plainly in the report rather than guessing — do not fabricate confirmation of a UI you didn't actually observe.
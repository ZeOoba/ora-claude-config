# /open-sessions

Find Claude Code Desktop + Cowork Desktop sessions that are waiting on Gabriel — unanswered questions, runs stalled mid-tool-call, messages that never got a reply. Read-only; never writes to either session store.

## Action
Run exactly this command and report its markdown output:

```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\open_sessions_probe.py --days 30
```

It walks both session stores (`%APPDATA%\Claude\claude-code-sessions` + `local-agent-mode-sessions`), tail-reads each unarchived session's transcript, and classifies:

- **NEEDS-ANSWER** — last assistant message asks Gabriel a question (or AskUserQuestion pending)
- **STALLED** — a tool call never returned (killed mid-run or awaiting approval)
- **INTERRUPTED** — Gabriel's last message never got a reply
- **NO-ACTION** — closed cleanly, just not archived (archive candidates; only shown with `--all`)

## Reporting rules
- The session you run this FROM always shows as STALLED (it is mid-turn) — drop it from the report.
- Items marked "may still be running" (<15 min activity) are likely live sessions, not stalled ones.
- Scheduled-fleet runs are excluded from actionable automatically (`Ora …` titles AND sessions whose first message is a `<scheduled-task>` tag).

## Board mode ("show me the board" / "board")
Render the actionable items as an interactive elicitation form (visualize MCP: `read_me` elicitation module → `show_widget`) — one group per item with a conversational question, a muted context line (surface · age · situation), action pills (always include drop/park), and a textarea where specifics are likely. On submit, dispatch per the answers: record decisions via the event-log append script + projects.md + the board task's `answered.json` (`~/.claude/scheduled-tasks/ora-open-sessions-board/answered.json`), execute safe internal follow-ups, draft-never-send anything external.

**Stale-card cross-check (MANDATORY before rendering — the 2026-06-12 stale-deal-card lesson):** for any card touching a deal, read the "Active deal pipeline" table in memory `projects.md` first. If the session's pending ask conflicts with newer deal state (price/structure/dates have moved), mark the card "⚠ possibly superseded — [newer fact]" or omit it and say why. Never present a stale deal decision as live. Skip sessions already in `answered.json` unless they have newer activity than their `decidedAt`.

The scheduled twin of this command is `ora-open-sessions-board` (daily 17:00 ET) — same procedure, self-contained in its SKILL.md.
- Summarize, don't dump: lead with NEEDS-ANSWER, then STALLED/INTERRUPTED. Cap at ~15 items; note "+N more" beyond that.
- If Gabriel wants the unarchived-but-done list, re-run with `--all` — those NO-ACTION rows are archive candidates. Archiving must happen from the app sidebar or a supervised session (`archive_session` is approval-gated and unavailable under bypassPermissions).

## Flags
`--days N` lookback (default 30) · `--all` include NO-ACTION + fleet · `--json` machine-readable

Runtime ~2 min over ~400 sessions. On a RAM-pinched day (see `/ram`), run it before launching anything heavy.

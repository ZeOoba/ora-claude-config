---
name: ora-cowork-settings-quarterly-review
description: Quarterly Cowork Global Settings review reminder (cowork-settings skill; v3.0 baseline 2026-10-17) [MODEL: claude-sonnet-5-5 | set 2026-10-17]
---

## STEP -1 — DOUBLE-FIRE ENTRY GUARD (run first)
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-cowork-settings-quarterly-review --block main --run-id <run_id> --period month --ttl-min 30
- Exit 10 = this month already completed; Exit 11 = another fire is live. Stand down: no reads, no email, no Notion row; report a NORMAL skip.
- Exit 0 = proceed. (Quarterly reminder; a weekend fire is acceptable.)
After the email sends: `... block-sentinel.py complete --task ora-cowork-settings-quarterly-review --block main --run-id <run_id> --period month --email-sent-at <ISO8601>`. On abort, and on a send that still fails after its one retry: `... fail ... --error "<what broke>"` (never `complete` without a real `--email-sent-at`). Only the claim holder calls complete/fail. ALWAYS pass `--period month`.

Run date: compute once with `date '+%A %Y-%m-%d'`, reuse everywhere.

1. Read the latest file in C:\Users\Owner\ora-skills\cowork-settings\versions\
   (sort by filename). Record its version, effective date and "next review" date.
2. Compute days since that version. If < 80, state "review not yet due" and
   finish with the email in step 4 marked INFO.
3. Run the cowork-settings parity gate read-only: diff the version's Settings
   Block against the ORA Global Operating Prompt copy in
   Claude_Workspace/00_Governance/References/. List every contradiction found
   (title, naming schemas, send path/routing, connector status, skill
   tie-breaks, Notion DB ids). Do NOT edit either document, and do not bump a
   version: ratification is Gabriel's, in a supervised session.
4. Email ggoldberg@oxfordra.net ONLY (no cc) via Outlook COM:
   C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1
   Subject: "Cowork Settings quarterly review — YYYY-MM-DD"
   Body: current version, days since, contradiction list (or "none found"),
   and the line "Run /cowork-settings in a supervised session to bump or log
   'no changes needed'." On exit 2 (COM failure) or 4 (timeout): retry the send ONCE, then flag loudly in
   the Notion completion row (Ops Hub 32b6ecd8). Do NOT halt.
5. Write a completion row to Notion Ops Hub 32b6ecd8. Before any retry of a
   create with no page ID, fetch the parent for an exact-title child.
Never fabricate. Put data gaps under "QUESTIONS FOR GABRIEL".

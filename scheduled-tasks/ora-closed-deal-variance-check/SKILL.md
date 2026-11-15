---
name: ora-closed-deal-variance-check
description: Monthly: flags ORA acquisitions crossing the 12/24/36-month closed-deal variance-review marks (acquisition-underwriting v4.33) and emails Gabriel what each review needs. Read-only; no Notion writes. [MODEL: claude-sonnet-5-5 | set 2026-11-06]
---

CONNECTOR SCOPE: none. This task works only with local files and the Outlook COM send script. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7 or Claude Code Remote, even if they are available in this session. If the local files or the COM script are unavailable, stop and report; never reach for a connector instead.

PURPOSE: the closed-deal variance review in acquisition-underwriting v4.33 runs at 12, 24 and 36 months after each ORA acquisition close. This task only TRIGGERS it. It finds the deals that crossed a mark, and lists what each review needs. It never computes variances, never edits doctrine, never changes a weight, floor or governor constant, and never writes to Notion. Gabriel approved this task in-turn on 2026-11-06.

GUARD: compute RUN_DATE once at the start with `date '+%A %Y-%m-%d'`. Reuse that exact value everywhere: its date part fills every date slot, and the weekday appears only where named. If this month's output file already exists, exit silently (no double fire).

DOUBLE-FIRE ENTRY GUARD (added 2026-11-14; run FIRST, before STEPS; see scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md):
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-closed-deal-variance-check --block main --run-id <session run_id> --ttl-min 30 --period month
- Exit 0 (PROCEED): this run owns the claim and MUST end in `complete` or `fail` below.
- Exit 10 (SKIP_ALREADY_COMPLETE): this month's run already completed. Skip the whole task (no writes, no email) and report a normal skip.
- Exit 11 (STAND_DOWN_IN_PROGRESS): another run holds the claim. Stand down and report it.
- Exit 12 or anything else: stop, run none of the steps, and report the exit and output.
Terminal call, after step 6, whether or not it sent an email:
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-closed-deal-variance-check --block main --run-id <run_id> --period month
(append `--email-sent-at <ISO time>` when step 6 sent the email).
If the run cannot finish (any step fails and the task stops), release the claim instead:
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-closed-deal-variance-check --block main --run-id <run_id> --period month --error "<one line>"
Never pass --force from a scheduled fire.

STEPS
1. Read the ACQUIRED rows of `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\disposition-ledger.md`. The settlement date is the close date. Apply any dated correction notes below the table. Skip a property whose newest row is a TERMINAL sale.
2. For each deal, list each mark (12, 24 and 36 months after close) that falls in the window from 31 days before RUN_DATE through 31 days after RUN_DATE. A deal with no mark in the window is not reported.
3. For each deal due, list:
   - the review lines: stabilized NOI; reassessed property tax; insurance; CapEx by roof, paving, HVAC, doors and electrical; downtime per rollover; renewal rate; TI/LC per lease; credit loss; market rent achieved at rollover;
   - the sources each line needs: the deal's UNDERWRITE workbook as closed, a P&L for the 12 months ending at the mark (the pm-portal-pnl-export skill, or QuickBooks Desktop exports), the delinquency export, and the Notion CapEx & Maintenance Log;
   - the workbook to enter results into: the newest `BackTestDataset_Portfolio_*.xlsx` in `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\`, sheet Variance_Review. Do NOT write to that workbook.
4. Never fabricate. A missing close date or ledger row goes under QUESTIONS FOR GABRIEL with the specific question.
5. Write `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\<RUN_DATE date>_Closed-Deal-Variance-Due_v01.md` with a table: deal, close date, mark, mark date, lines and sources, then QUESTIONS FOR GABRIEL. If nothing is due, write a one-line file saying so, so the guard works.
6. Email ONLY if at least one deal is due or a question exists. Send through `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, TO `ggoldberg@oxfordra.net` ONLY, with no cc. Subject: `ORA closed-deal variance reviews due — <RUN_DATE date>`. The body is the table from step 5. Retry only on exit 2 or 4, once; never resend after any other exit (send state unknown). If the retry fails, say so loudly in the output file. Do not halt.
7. Do not write to the event log; this task is a read-only reminder.

SIBLINGS (point to them; do not duplicate their logic): acquisition-underwriting `references/outcome-feedback-and-backtest.md` (the variance-review method and its routing rule) and pm-portal-pnl-export (the P&L actuals).
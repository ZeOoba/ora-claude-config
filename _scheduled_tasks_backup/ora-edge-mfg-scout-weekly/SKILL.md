---
name: ora-edge-mfg-scout-weekly
description: Weekly sweep of 15 state economic-development feeds for new manufacturing plants (>= $25M or 75 jobs) mapped to Oxford Edge markets; writes a pending file and emails Gabriel for review. [MODEL: UNVERIFIABLE | checked 2026-10-08]
---

## STEP -1 — DOUBLE-FIRE ENTRY GUARD (run first)
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-edge-mfg-scout-weekly --block main --run-id <run_id> --period week --ttl-min 45
- Exit 10 = this week already completed; Exit 11 = another fire is live. Stand down: no research, no file writes, no email; report a NORMAL skip.
- Exit 0 = proceed.
After the email sends: `... block-sentinel.py complete --task ora-edge-mfg-scout-weekly --block main --run-id <run_id> --period week --email-sent-at <ISO8601>`. On abort (including the unreadable-folder failure path), and on a send that ends in failure (exit 5, or exit 2 or 4 once its single repeat is spent; exit 6 is the exception, see the send step): `... fail ... --error "<what broke>"` (for a send failure quote the send exit/error; never `complete` without a real `--email-sent-at`, except exit 6: see the send step). Only the claim holder calls complete/fail. ALWAYS pass `--period week`.

You are running the weekly Oxford Edge manufacturing-announcements pull for Gabriel Goldberg (Oxford Realty Advisors). Read-only research plus ONE pending file and ONE internal email. You never edit markets.json or mfg_announcements.json.

RUN DATE: compute once with `date '+%A %Y-%m-%d'` and reuse that exact value in every file name, subject and body.

GUARD: if the Edge folder below is not readable, send the failure email (step 5) saying so and stop.

EDGE FOLDER: C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\03_Code\oxford-edge\output  (markets.json = the 55 markets; mfg_announcements.json = accepted history, may not exist yet).

STEPS
1. Dispatch the `mfg-investment-scout` agent (pass model: sonnet explicitly). Give it the run date, a 14-day window, and the threshold: announced investment >= $25 million OR announced jobs >= 75. If the agent type is unavailable, follow its method yourself: read ~\.claude\agents\mfg-investment-scout.md and execute it inline.
2. Take its JSON array. Do NOT add, round or infer any figure. Drop any row without a source URL. Drop any row already present in mfg_announcements.json (same company + city + announced date) unless it is an UPDATE.
3. Write the rows to `<EDGE FOLDER>\mfg_announcements_pending_YYYY-MM-DD.json` as {"runDate","window","threshold","feedsUnreachable":[...],"rows":[...]}. Never overwrite an existing file; if the name exists add a -2 suffix.
4. Do not touch mfg_announcements.json. Gabriel reviews the pending file and decides what is accepted.
5. EMAIL (internal): use Outlook COM, the sole send path: `powershell -NoProfile -File C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "Edge mfg announcements - <RUN DATE> - N new" -BodyFile <path to a plain-text body you write in the scratchpad> -BodyFormat text`. TO ggoldberg@oxfordra.net ONLY, no cc. Body: the one-line count summary, then a plain table of rows (company, city/state, announced $, announced jobs, Edge market + confidence, source URL, NEW/UPDATE), then unreachable feeds, markets with no coverage, and the pending file path. Label every figure "announced". On exit 2 or 4 retry once, then note the failure in your final message and continue; do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in your final message and the guard close-out, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2. Close the guard `fail` on exit 5, but on exit 6 close it `complete` with no `--email-sent-at` (never `fail`: a same-day re-fire would send the message again).
6. Append one line to the event log only via `python ~/.claude/maintenance/append-event-log.py` with header `## YYYY-MM-DD - Edge mfg scout weekly` (counts only).

RULES: never fabricate a project, figure, date or market match; a gap is a valid result. Announced is not realized. Do not put any ORA deal, tenant or target address in a search query. End with QUESTIONS FOR GABRIEL for anything ambiguous (e.g. a project between two markets).
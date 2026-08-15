---
name: ora-owner-outreach-queue-refresh
description: Weekly Phase-1+2 owner-outreach pipeline — refreshes the queue, upserts only net-new owners into the Notion Owner Outreach Queue DB, regenerates the T1 letter pack (DOCX+PDF), emails a summary to ggoldberg only. Draft-only — nothing sent to owners. Retimed 2026-07-21 (Gabriel-directed) from 10:00 AM to 10:55 AM ET, same root cause/fix as ora-monday-sync (see that task's description). v1.2 (2026-07-12): on this fully-unattended path, a STALE master now pauses Notion page-creation and routes to a QUESTIONS FOR GABRIEL email section instead of auto-proceeding. v1.3 (2026-07-14): STEP 1's STALE GUARD now checks the reported vintage against a STANDING RATIFICATIONS list before halting. [MODEL: claude-sonnet-5 | set 2026-07-13]
output_contract:
  version: 1
  blocks:
    - id: block-owner-outreach-mail
      artifact:
        type: sent_mail
        mailbox: "ggoldberg@oxfordra.net"
        subject_pattern: "ORA Owner-Outreach — Weekly — {DATE}"
        recipient: "ggoldberg@oxfordra.net"
      freshness_window_hours: 180
      expected_on:
        cron: "55 10 * * 1"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "STEP 5's summary email is the ONLY every-run artifact: the Notion Owner Outreach Queue upsert happens only when net-new owners exist, and the STALE GUARD can halt before it. Both the proceed and halt paths still email. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
---

RESTORATION NOTE: Re-registered 2026-07-07 after the 2026-07-05 machine migration orphaned this task (folder survived on disk; registry entry was lost). Content restored verbatim from the surviving SKILL.md — no logic changes.

Weekly Owner-Outreach pipeline (Oxford Realty Advisors, Phase 1 + Phase 2). Runs Mondays ~10:00 AM ET. Self-contained — assume no memory of prior sessions.

GOAL: Refresh the owner-outreach queue, add only NEWLY-promoted owners to the Notion Owner Outreach Queue DB (no duplicates), regenerate the T1 letter pack, and email Gabriel a summary. Owner outreach is external-counterparty communication — DRAFT ONLY; nothing is sent to any owner. Gabriel releases the weekly batch himself.

Use the Desktop Commander MCP (start_process, shell powershell.exe) for all local commands — the files and Outlook COM are reachable ONLY on the Windows machine, NOT in the sandbox bash.

STEPS:
1. Run the driver:
   python "C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Investment Candidates -- 2026\owner_outreach_weekly.py"
   (2026-07-21 fix: path corrected to add the missing "Business\" segment -- the 2026-07-05 migration nested this folder one level deeper and neither the 2026-07-11 nor 2026-07-12 fixes to owner_outreach_weekly.py/owner_outreach_queue.py's own internal FOLDER constants had been mirrored here, so this task's own invocation path was still broken even after those scripts were patched. Root-caused and fixed in the same session as those two.)
   It (a) runs the pinned queue script (READ-ONLY on the master), (b) dedups promoted parcels against owner-outreach-ledger.csv, (c) writes _oo_netnew_pages.json (net-new only, schema-mapped, mailing-overrides applied), and (d) regenerates the dated T1 letter pack DOCX. Capture its stdout — it prints: promoted count, NET-NEW count + by-market, Tier-0 RECOVER gaps (with Parcel IDs), and the queue/pack/payload paths.
   GUARD: if the driver exits NON-ZERO, the underlying queue script's fail-loud guard fired (empty queue / master missing / schema drift). Email the exact error to Gabriel as an ALERT and STOP — do NOT fabricate a queue or numbers.
   STALE GUARD (v1.3, unattended-path only): the driver's stdout now WARNs rather than halts on a stale master (2026-07-12 relax — that relax was scoped to Gabriel's own manual runs). On THIS unattended run, if stdout contains "STALE" or "[NOTE] master is STALE": first check the reported master vintage against STANDING RATIFICATIONS below.
   - If the reported vintage MATCHES a ratified entry: proceed normally through STEP 2 and STEP 3 (do NOT halt). Add one line to the STEP 5 summary email noting the run proceeded under that standing ratification (cite date + vintage), not a fresh confirmation — so Gabriel always sees when this is in effect.
   - If the reported vintage does NOT match any ratified entry (a new/different stale vintage — including a "refreshed" master that is nonetheless already >STALE_DAYS old): the full halt applies exactly as before. Do NOT proceed to STEP 2 or STEP 3. Skip straight to STEP 4/5: still regenerate/convert whatever pack the driver already produced if you want a record, but do NOT create any Notion pages and do NOT run --commit. Add a "QUESTIONS FOR GABRIEL" section to the summary email: state the master's reported vintage/mtime, that this looks stale by the filename-age heuristic, and that Notion page-creation was held pending his confirmation the master is current (or a refreshed master) — next Monday's run will retry automatically either way.

   STANDING RATIFICATIONS (scoped per-vintage — NOT a STALE_DAYS or policy change):
   - Vintage 2026-06-10 confirmed CURRENT by Gabriel on 2026-07-14 (interactive elicitation; see memory/ops_decision_log.md 2026-07-14 entry "Is the 2026-06-10 off-market master vintage current enough to promote to Notion?"). One-time ratification of this specific unrefreshed vintage — not a standing instruction to skip the guard, and not a widened STALE_DAYS threshold. This entry stops applying automatically the instant the reported vintage changes to anything other than 2026-06-10 (even a same-day re-save that shifts mtime without a new filename-dated vintage should be treated conservatively — if in doubt whether the reported vintage still reads as 2026-06-10, halt and ask rather than assume the ratification holds).
   - Do not add a new entry here without an explicit, dated Gabriel confirmation for that specific vintage. Do not delete this entry retroactively — if superseded, strike through and date the supersession instead, so the audit trail of what was ratified when survives.
2. Read _oo_netnew_pages.json (full path printed by the driver). If STEP 1's STALE GUARD fired, skip this step entirely. Otherwise, if the array is NON-EMPTY, create those pages in the Notion Owner Outreach Queue DB via the Notion connector: notion-create-pages with parent { type: data_source_id, data_source_id: "caa809b7-1da3-49d5-ab92-bcd7f36ca43e" }, passing the array as "pages" (batch in groups of ~20 if large). If the array is empty, skip Notion creation (no new promotions this week).
3. ONLY AFTER the Notion creation succeeds, commit the ledger:
   python "C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Investment Candidates -- 2026\owner_outreach_weekly.py" --commit
   (Appends the net-new parcels to owner-outreach-ledger.csv so next week won't re-create them.) Skip this step if there were no net-new pages.
4. Convert the regenerated DOCX letter pack to an extractable-text PDF via Word COM (NOT Microsoft Print to PDF). Use the DOCX path the driver printed:
   $docx='<pack path>'; $pdf=$docx -replace '\.docx$','.pdf'; $w=New-Object -ComObject Word.Application; $w.Visible=$false; $d=$w.Documents.Open($docx,$false,$true); $d.ExportAsFixedFormat($pdf,17); $d.Close($false); $w.Quit()
5. Email the summary to ggoldberg@oxfordra.net ONLY (no cc — never egoldberg@ or ze@) via the firm's SOLE automated send path: C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (inspect its parameter block if the signature is unknown). Subject: "ORA Owner-Outreach — Weekly — <today's date>". Body: promoted count; NET-NEW owners added to Notion (count + by market); Tier-0 RECOVER gaps (list the Parcel IDs — these need a county mailing pull before their T1 letter is deliverable; they are excluded from the pack); the letter pack PDF path; and the queue freshness/STALE line if present. On a NON-ZERO exit from the send script: retry once, then flag loudly in the Notion Operations Hub completion row (page 32b6ecd8) — do NOT halt.

Never fabricate owner/mailing data. RECOVER gaps are reported, never invented. Do not modify the master, the scripts, or the ledger by hand. If anything is ambiguous, add a "QUESTIONS FOR GABRIEL" section to the email instead of guessing. The queue/letter/upsert logic lives entirely in owner_outreach_weekly.py, owner_outreach_queue.py (v04), and build_t1_letterpack.py — do NOT reimplement it here.
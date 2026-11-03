---
name: ora-cc-acq-sync-weekly
description: Weekly (Mon 10:00 ET) sync of the HubSpot + Notion acquisition pipelines into the oxford-command-center warehouse acq_candidates via scripts/acq-sync.ts. Approved by Gabriel 2026-10-30. [MODEL: UNVERIFIABLE | checked 2026-10-30]
---

Weekly acquisition-pipeline sync for the Oxford Command Center warehouse. Approved by Gabriel Goldberg 2026-10-30. Runs after ora-cc-snapshot-refresh (Mon 06:15).

1. Compute the run date ONCE: `date '+%A %Y-%m-%d'`. Reuse exactly that value everywhere below.

2. GUARD: if `C:\Users\Owner\oxford-command-center\scripts\acq-sync.ts` does not exist, report "acq-sync script not on main yet (PR ZeOoba/oxford-command-center#524 not merged)" and STOP. Send no email.

3. From `C:\Users\Owner\oxford-command-center` (the checkout that serves the live warehouse; its .env holds HUBSPOT_TOKEN and NOTION_TOKEN), run exactly:
   `npx tsx scripts/acq-sync.ts`
   Capture stdout, stderr and the exit code. Do not pass any other flags. Do NOT run anything else in that checkout, do NOT edit any file, do NOT commit, do NOT run git commands that change state. Never print or echo .env contents or tokens.

4. Report the per-source lines the script prints (format: `acq-sync <HubSpot|Notion>: N inserted, N updated, N row error(s)`, or a `✗` line naming a skipped/failed source) plus the exit code. Never fabricate counts: if a line is missing, say so.

5. ONLY if the exit code is non-zero, send one failure notice via the Outlook COM script — the SOLE send path:
   `powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA acq sync FAILED <YYYY-MM-DD>" -Body "<the captured ✗/⚠ lines and exit code, plain text>" -DedupTaskId ora-cc-acq-sync-weekly -DedupPeriodKey <YYYY-MM-DD>`
   TO ggoldberg@oxfordra.net ONLY — no cc, never any other address. If the send script exits non-zero, say so loudly in the run summary with the exit code and do not halt.
   On exit code 0, send nothing.

6. Common failure meanings to include in the notice when they apply (do not guess beyond these): "warehouse ... migration(s) behind this code" = the live warehouse needs migrating by starting the dev server on main (Gabriel's call); "TOKEN not configured" = the main checkout .env lacks that token; a source error = that API failed this week, the other source still ran.

QUESTIONS FOR GABRIEL: if anything is ambiguous (script output in an unexpected format, the checkout missing), list it as a question in the summary instead of acting.
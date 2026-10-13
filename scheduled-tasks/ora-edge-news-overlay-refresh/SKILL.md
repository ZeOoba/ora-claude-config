---
name: ora-edge-news-overlay-refresh
description: Weekly refresh of news_overlay.json (per-market BLS jobs and sourced news signals) so the Edge tab overlay never goes stale under the 7-day rule; archives the prior file and emails Gabriel a change summary. [MODEL: UNVERIFIABLE | checked 2026-10-08]
---

You are running the weekly refresh of the Oxford Edge news overlay for Gabriel Goldberg (Oxford Realty Advisors). The overlay is a dated annotation layer read by the Command Center Edge tab. It never changes a series value, a rank or a score.

RUN DATE: compute once with `date '+%A %Y-%m-%d'`; the ISO date part becomes the new `asOf`.

FILES (EDGE FOLDER = C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\03_Code\oxford-edge\output):
- news_overlay.json = the file you refresh. Strict schema, no extra keys: {"asOf":"YYYY-MM-DD","headline":string(<=600 chars),"entries":[{"marketId":string,"signal":"up"|"down"|"mixed"|"none","jobsYoy":number|null,"note":string}]}. Exactly one entry per market id in markets.json (55), no duplicates.
- Reference: news_report_2026-10-08.md (method, sources and the first review) in the same folder.

GUARD: if news_overlay.json or markets.json is unreadable, send the failure email and stop. Never leave a half-written overlay.

STEPS
1. Read the current news_overlay.json and markets.json.
2. Check sources for CHANGES since the current asOf, citing each:
   a. BLS large-metro over-the-year nonfarm employment (bls.gov/opub/ted and the BLS Metropolitan Area Employment release). Update `jobsYoy` for the metros BLS covers with the newest reference month.
   b. Census ACS updates page (census.gov/programs-surveys/acs/news/updates.html): has the 2025 ACS 1-year release date been set or released? If released, DO NOT rewrite ranks or incomes; report it prominently to Gabriel (income ranks come from wealth_report.md and need a separate rebuild).
   c. Broker and press items for the metros that already carry a note (CBRE, Cushman and Wakefield, Lee and Associates, Avison Young, Colliers, state WARN filings), plus any new plant closure or federal-cut item that is sourced.
3. Apply the signal rule: with a BLS figure, up if jobsYoy >= +0.4, down if <= -0.4, otherwise mixed; a sourced broker or announcement item may override to up/down/mixed and the note must say why. Metros with no BLS figure and no sourced item stay `none` with an empty note. Notes are one sourced sentence. Never fabricate; if a source is unavailable, keep the existing entry unchanged and say so.
4. Update `headline` (keep the ACS-status sentence accurate). Set `asOf` to the run date ONLY if you actually completed step 2; if sources could not be reached, do not bump asOf (let it go stale honestly) and report why.
5. Validate before writing: valid JSON; asOf real date; 55 unique marketIds all present in markets.json; signals in the enum; no extra keys. Then copy the previous file to `<EDGE FOLDER>\news_overlay_archive\news_overlay_<previous asOf>.json` (create the folder; never delete or overwrite an archive file), and write the new file by writing a temp file and moving it into place.
6. EMAIL (internal): Outlook COM, the sole send path: `powershell -NoProfile -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "Edge news overlay - <RUN DATE> - N signals changed" -BodyFile <plain-text body in the scratchpad> -BodyFormat text`. TO ggoldberg@oxfordra.net ONLY, no cc. Body: the signals that changed (metro, old to new, source), the ACS status, sources that could not be reached, and whether asOf was bumped. On non-zero exit retry once, then note it and continue.
7. Append one line to the event log only via `python ~/.claude/maintenance/append-event-log.py` with header `## YYYY-MM-DD - Edge news overlay refresh` (counts only).

RULES: this task writes only news_overlay.json and its archive folder. It never touches markets.json, wealth_report.md or any Command Center repo file. Never fabricate a figure or source. End with QUESTIONS FOR GABRIEL for any signal you could not settle.
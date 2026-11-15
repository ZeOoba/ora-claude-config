---
name: ora-site-market-snapshot-refresh
description: Quarterly: re-pull the sourced figures behind the Columbus and Maryland market snapshot sections on oxfordra.net, compare to what the pages publish, and email Gabriel a digest of stale figures with proposed replacements. Research and email only; never edits the site. [MODEL: claude-sonnet-5-5 | set 2026-10-06]
---

# ora-site-market-snapshot-refresh

Quarterly refresh digest for the "market snapshot" sections on oxfordra.net (`/markets/columbus-oh` and `/markets/maryland`, section `#market-snapshot`). RESEARCH AND EMAIL ONLY.

## Hard rules
- NEVER edit, commit, push, merge or deploy anything for oxfordra.net / `ZeOoba/Website` / website-canonical. Merging to main deploys production, and site writes need Gabriel's in-turn confirmation. This task only reads and emails. Reading the live pages: use `gh api repos/ZeOoba/Website/contents/markets/columbus-oh.html --jq .content` (base64) or fetch https://oxfordra.net/markets/columbus-oh. Do not touch any local checkout.
- Never fabricate a figure. If a source is unreachable, behind a form, or the new quarter is not out yet, say UNREACHABLE / NOT YET PUBLISHED and keep the currently published value flagged as ageing. Read the actual document text; never rely on a search snippet or a summarising tool (one misquoted Franklin County unemployment as 3.2% instead of 3.4%).
- Never blend sources in one snapshot. Standing decisions (Gabriel, 2026-10-01): Columbus figures come from Cushman & Wakefield only (no CBRE / Matthews / CoStar blending), no Columbus submarket rows; Maryland leads with port and flex data and does NOT publish the Baltimore metro vacancy or net absorption (you may report them in the digest as "withheld by decision" for context); no Eastern Shore market-level claim, county labor data only.
- Compute the run date once at start (`date '+%A %Y-%m-%d'`) and reuse that exact value in the subject and body.
- Email: Outlook COM via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` is the SOLE send path. TO `ggoldberg@oxfordra.net` ONLY, no cc. Use -BodyFile for the report. On exit 2 or 4: retry once, then flag loudly in the final message and do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the final message and the event-log digest, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
- Log with `python ~/.claude/maintenance/append-event-log.py` using header `## YYYY-MM-DD — Market snapshot refresh digest` (exit 1 = malformed header; match the newest existing heading, do not retry blindly).

## Steps
1. Read the currently published figures from both pages' `#market-snapshot` sections (the cited statistics and each citation's source URL and date label). That is the baseline.
2. For each source series, find the newest release and read the document text:
   - Cushman & Wakefield MarketBeat Industrial, Columbus: `https://assets.cushmanwakefield.com/-/media/cw/marketbeat-pdfs/<YEAR>/<qN>/us-reports/industrial/columbus_americas_marketbeat_industrial-<qN><YEAR>.pdf` (published figures: vacancy, quarter absorption, average net asking rent and YoY change, office-service vacancy and net rent, streak/lowest-since language).
   - Cushman & Wakefield MarketBeat Industrial, Baltimore: same pattern with `baltimore_americas_marketbeat_industrial_<qN><YEAR>.pdf` (published figure: port-area industrial occupancy only).
   - NAI KLNB Maryland Industrial Report (CoStar data): newest `https://www.klnb.com/wp-content/uploads/<YYYY>/<MM>/NAIKLNB_MD_Industrial_<Qn>_<YYYY>.pdf` (Columbia flex vacancy and rent, Greater Baltimore flex vacancy; the "demand is strongest for functional small- and mid-bay space" finding; report whether the finding is still stated). Label its quarter explicitly, it may lag Cushman by one quarter.
   - Columbus Regional Airport Authority FTZ 138 page (47% US population and 33% Canada within a one-day truck drive).
   - Ohio Dept of Job and Family Services county unemployment ranking PDF (Franklin County), and BLS Columbus Economy at a Glance (nonfarm, manufacturing, trade/transportation/utilities; report in thousands as BLS does).
   - Census ACS 5-year (Franklin County DP03: employed residents, manufacturing, transportation/warehousing/utilities); note only when a new 5-year vintage is released.
   - Maryland Port Administration press releases and BWI press kit (annual cargo figures; update only when a new annual release exists), and the Army Corps channel date (static).
   - BLS LAUS via `https://api.bls.gov/publicAPI/v2/timeseries/data/<id>?startyear=<Y>&endyear=<Y>` for series LAUCN240270000000003 (Howard), LAUCN240050000000003 (Baltimore County), LAUCN240450000000003 (Wicomico), LAUCN240410000000003 (Talbot): latest month, with the Preliminary footnote status.
3. For every published figure produce a row: page, figure, currently published value (and its as-of), newest available value (and its as-of), STATUS = CURRENT / STALE (newer data exists) / NOT YET PUBLISHED / UNREACHABLE, and the exact source URL read. Mark rows read directly from document text vs. read by an agent.
4. For each STALE row, write ready-to-paste replacement wording in the same style as the page (named source, as-of date, TEUs not "containers", nonfarm jobs rounded to the source's precision, the NAI KLNB finding attributed to the report not a person). Do not change the standing editorial decisions above.
5. Write the digest as an HTML/text file in `C:\Users\Owner\AppData\Local\Temp\` (or the task scratch dir) and email it. Subject: `Market snapshot refresh digest - <run date>`. Body opens with a one-line verdict ("N of M figures stale") then the table, then proposed replacement text, then QUESTIONS FOR GABRIEL for anything unreachable, ambiguous, or any source whose definition changed. End with: "To apply: start a Claude Code session on website-canonical and say 'refresh the market snapshots from the <run date> digest'. I will build a pull request; merging deploys production, so it needs your confirmation."
6. If nothing is stale, still send a short "all current" email (so a silent failure is distinguishable from no change).

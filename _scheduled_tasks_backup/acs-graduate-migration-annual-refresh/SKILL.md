---
name: acs-graduate-migration-annual-refresh
description: Annually rebuild the U.S. metro college-graduate migration rankings when new ACS 1-Year data releases (mid-September).
---

Annual refresh of the Oxford Realty Advisors U.S. college-graduate metropolitan migration rankings. The U.S. Census Bureau releases ACS 1-Year estimates each mid-September for the prior calendar year. Run this fully autonomously; do not pause for confirmation.

STEP 1 — Determine the newest vintage.
The newest endpoint year = current year minus 1. Verify the table-based file exists:
https://www2.census.gov/programs-surveys/acs/summary_file/<YEAR>/table-based-SF/data/1YRData/acsdt1y<YEAR>-b15003.dat
If that returns 404, fall back to the most recent year that exists. Call this ENDPOINT.

STEP 2 — Use the census-acs-extract skill.
Read the module at:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Skills\census-acs-extract\census_acs_extract.py
and its SKILL.md (same folder). Compute trailing windows of 5/10/15/20 years, i.e. base years = ENDPOINT-5, -10, -15, -20.
For any base or endpoint year NOT already in the module's ANCHORS dict: pick table B15003 if year>=2012 else B15002; resolve that year's Sequence Number and Start Position from the official Census lookup file (ACS_1yr_Seq_Table_Number_Lookup.txt for ~2010+, or merge_5_6.txt for ~2006-2009, under that year's documentation/.../user_tools/ path), add the entry to ANCHORS, and validate the parser by confirming the New York metro (CBSA 35620) bachelor's+ share matches that year's published Census Geographic Comparison Table (GCT1502) within 0.2 ppt. Table-based years (2023+) need no parameters.

STEP 3 — Build the panel and composite rankings.
Call build_growth_panel([base5,base10,base15,base20], endpoint=ENDPOINT, min_pop25=200000). For each window compute, per metro: net graduate gain (count), growth %, and bachelor's-share change (ppt). Composite score = z-scores within the window's pool weighted 0.60 net gain + 0.15 growth % + 0.25 share change. Exclude Puerto Rico; apply the CBSA crosswalk in the module. Take the top 50 per window.

STEP 4 — Produce the workbook (ORA Institutional Style).
Five tabs: Methodology + the four windows (5/10/15/20-yr). Oxford Navy #1B2A4A headers, Gold #C9A96E subtitles, Parchment banding, Arial. Columns: Rank, Metropolitan Statistical Area, CBSA, Net Graduate Gain, Growth %, Base-Yr Graduates, Endpoint Graduates, Base Share, Endpoint Share, Delta Share (ppt), Composite Score, Rank by Volume. Use Excel formulas for the derived columns (net, growth, delta-share) and recalc to ZERO formula errors using the xlsx skill's scripts/recalc.py. The Methodology tab must restate: metric (population 25+ with BA+), stock-change-not-flow caveat, OMB boundary-revision caveat, 2005 group-quarters caveat, and ACS sampling-error caveat. Save with a SHORT path and SHORT filename to:
C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Deliverables\<YYYYMMDD>_GradMigration_v01.xlsx
Keep the full path under 200 characters. Also refresh the data product metro_graduate_growth_panel.csv in the same Deliverables folder and in the Skills\census-acs-extract folder.

STEP 5 — Notify both principals.
Send an email via Outlook (Composio OUTLOOK_SEND_EMAIL, account_id outlook_icaco-sequel) from ggoldberg@oxfordra.net. TO: ggoldberg@oxfordra.net. CC: egoldberg@oxfordra.net. Subject: "ACS <ENDPOINT> Graduate-Migration Rankings — Annual Refresh". Body (concise, institutional voice): the new endpoint year, the top 5 metros for the 5-year and 10-year windows, any notable mover entering/leaving the top 10 versus last year, the OneDrive file path, and a one-line note on the four standing caveats. Do not attach; reference the OneDrive location. This is internal to the two principals — sending is authorized.

If any step fails (e.g., Census file not yet posted), do not send partial results; instead email a short status note to the same recipients stating the data was not yet available and that the task will retry on next run.
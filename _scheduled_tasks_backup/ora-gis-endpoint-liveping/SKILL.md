---
name: ora-gis-endpoint-liveping
description: Quarterly live-ping health check of GIS/CAMA endpoints in parcel-data-recovery flagged DOWN or UNTESTED (Hamilton CAGIS, Wyandotte KS CAMA, Polk County IA GIS) — replaces reliance on the static endpoints.md claim. Posts status to Notion Ops Hub; flags any status flip for a Code-surface doc update. 9th of Mar/Jun/Sep/Dec, 06:35 ET. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

You are running the ORA quarterly GIS/CAMA endpoint live-ping check. This replaces trusting the static "confirmed down"/"untested" claims in the parcel-data-recovery skill's references/endpoints.md — those claims go stale, and a stale "down" note previously blocked Hamilton County work for an unknown period until someone happened to re-test it.

Read C:\Users\Owner\.claude\skills\parcel-data-recovery\references\endpoints.md (or the equivalent skill cache path) first to get the current list of endpoints marked DOWN, UNTESTED, or "not yet ruled dead" as of the last edit. As of 2026-07-12 that list includes at minimum:
1. Hamilton County OH (Cincinnati) CAGIS — test all three known domain variants: cagis.hamilton-co.org, cagisportal.hamilton-co.org, cagisonline.hamilton-co.org (hit /arcgis/rest/services?f=json). Also confirm the OGRIP bypass (services2.arcgis.com/MlJ0G8iWUyC7jAmu/arcgis/rest/services/OhioStatewidePacels_full_view/FeatureServer/0) is still live.
2. Wyandotte County KS CAMA — landsweb.wycokck.org and maps.wycokck.org (was down 2026-06-11, recheck before any Wyandotte reprice).
3. Polk County IA — gis4.polkcountyiowa.gov (untested from research sandbox as of 2026-07-12; confirm live or dead off-sandbox).
4. Any other endpoint marked DOWN/UNTESTED in the current endpoints.md at run time — re-read the file fresh each run rather than relying on this hardcoded list, since the file may have been updated since this task was written.

For each endpoint: hit the REST root with ?f=json (or the specific layer query if a root ping isn't diagnostic), record HTTP status/reachability, and note the test date/time. Do NOT assume the doc's current status — always send a live request.

Output: a short status table (endpoint, last documented status, live test result, date). Post it to the Notion Operations Hub (Ops Hub page 32b6ecd8-9e59-81f2-b329-df3fd0e25062) as a dated entry. If any endpoint's live status now DISAGREES with what's recorded in endpoints.md (e.g., a "DOWN" endpoint is now reachable, or a previously-live endpoint is now down), flag this prominently at the top of the report and note that endpoints.md needs a Code-surface update (skill files are read-only from Cowork/scheduled-task context — do not attempt to edit the skill file directly; recommend the fix for the next Claude Code session instead).

Email a one-paragraph summary to ggoldberg@oxfordra.net ONLY (routing canon — no cc) via the Outlook COM send path per standing convention; on non-zero exit, retry once then flag loudly in the Notion post rather than halting. Do not send anything to any external party — this is an internal status check only.
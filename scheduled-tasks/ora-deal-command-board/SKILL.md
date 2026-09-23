---
name: ora-deal-command-board
description: Weekly Monday deal-first pipeline board (draft-only, ggoldberg-only) — complements ora-open-sessions-board (sessions, not deals). Built 2026-07-17 per the ROI-brief Tier-2 acquisition-velocity plan. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

You are running ORA's weekly Deal Command Board — a Monday-morning, deal-first pipeline board for Gabriel Goldberg (Oxford Realty Advisors). This complements (does not replace) the daily ora-open-sessions-board, which tracks Claude sessions, not deals — this task tracks open acquisition pipeline deals specifically. Built 2026-07-17 as part of the 2026-07-16 setup review's Tier-2 acquisition-velocity plan (item 2.2).

[MODEL: claude-sonnet-5]

## STEP 1 — Pull open pipeline deals
Query the Notion Acquisition Pipeline Tracker (data source `collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) via `notion-query-data-sources` (SQL mode) for every row where Stage is NOT IN ('Closed Won','Passed','Killed','Killed — Reneg Only','Killed — Note/Short-Sale in Discussion'). Bare `'Killed'` is deliberate and must not be "tidied" out as redundant with the two `Killed —` variants: it is a distinct stage value, and its absence let E Fulton (Stage `Killed`, retired 2026-07-26, no open action) pass the filter into the 2026-07-27 `ora-deal-aging-sla` run. Added 2026-07-27; mirrored the same day in `ora-deal-aging-sla` STEP 1, and extended 2026-08-03 (Gabriel-ratified) to `ora-health-guard` block 4d, which had been carrying only three of the five values. **All FOUR sites must stay identical (`ora-weekly-hygiene` check C made explicit the same day, as the inclusion complement) — any change is made in all four SKILL.mds in the same session.** The two `Killed —` values are defensive, not observed: verified 2026-08-03 that the tracker's `Stage` select offers only the nine canonical options and no row carries either variant, so all three filters return identical rows today. Keep them anyway, for the same reason bare `'Killed'` is kept — and match on the em-dash (`—`), since a hyphen silently fails the string comparison. Pull: Deal Name, Address, Stage, Next Action, **Next Action Date (SQL column `date:Next Action Date:start`, added 2026-08-11 — see STEP 2b)**, Last Activity (SQL column `date:Last Activity:start`), Last Updated, Deal Owner, Target Close Date. This must be a full, unpaginated pull — if the tool indicates more rows exist, keep paging (has_more/next_cursor) until exhausted; a partial pull that silently drops rows is worse than no board at all.

**If SQL mode returns `validation_error` / `entitlement_required`, do NOT halt and do NOT retry the same call** — that is the MCP tool's quota gate (not a Notion plan limit; never recommend a Notion upgrade for it) and it fires nondeterministically from run to run. Fall back to **view mode against the tracker's unfiltered Default view** (`{"mode":"view","view_url":"https://www.notion.so/46c8a5c68b374c53a10d0f55c97613e5?v=51ae740498f94cb58e761522f0d84035","page_size":100}`), which was measured working on 2026-08-03 seconds after SQL mode was gated in the same session. **Use that view by UUID, never by name:** this database has duplicate-named views where one copy filters and the other does not (two `Pipeline Board`, two `Closing Timeline` — the emoji-prefixed copy is unfiltered, the plain-named one is not), so picking by name is a coin flip. Four views carry an `advancedFilter` that silently drops rows: `33c6ecd8-9e59-8151-93ad-000cc92fe0cc`, `33c6ecd8-9e59-8156-8659-000cc1e630de`, `33c6ecd8-9e59-8135-afb1-000ca16f0ac9`, and `3976ecd8-9e59-81e3-b0e4-000c82686425` (which also filters `Last Activity` on-or-before a hardcoded `2026-07-10`). Confirm via `notion-fetch` of database `46c8a5c6-8b37-4c53-a10d-0f55c97613e5` that the view you use has no `advancedFilter` before trusting its rows, because a filtered view returns a partial pull disguised as a successful query. Expect the result to exceed the inline output limit and spill to a `…/tool-results/` file (~57KB at 18 rows), and note that view mode pages on `start_cursor`/`next_cursor`, not `offset`. Full hazard detail and the third rung (`notion-search`, best-effort only): `ora-deal-aging-sla` STEP 1 — keep the two in sync, as with the stage-exclusion list above.

## STEP 2 — Compute days-in-stage
For each deal, days-in-stage = today minus the deal's **activity date**, resolved by this fallback chain (added 2026-07-17):
1. `Last Activity` (`date:Last Activity:start`) — PREFERRED. This is an explicit date stamped by deal owners and deal-touching skills (loi-generation, deal-execution, acquisition-underwriting, etc.) on real deal progress. It is NOT the system last-edited timestamp, so it does not move on cosmetic edits and does not go stale when work happens off-Notion.
2. `Last Updated` (Notion system last-edited time) — FALLBACK when `Last Activity` is null (legacy/un-stamped rows).
3. `createdTime` — last resort if both are null.

Flag any deal at 30+ days as STALLED, UNLESS its "Next Action" text contains "PARKED" (an explicit Gabriel-ratified hold is not the same failure mode as silent staleness — do not flag parked deals as stalled).

Coverage note: for any row where the flag is running on the FALLBACK (`Last Activity` is null), append a quiet "(days from Last Updated — Last Activity unset)" tag to that row's day cell, so field-coverage gaps are visible and shrink as skills adopt the stamp. Do NOT write `Last Activity` from this board — it is read-only by charter; a board that stamped activity would reset its own stall clock merely by surfacing a deal (self-defeating false-negative). Stamping is the job of the deal-touching skills (see the skills-pass backlog item filed 2026-07-17).

Rationale (why this field exists): keying staleness on the system last-edited timestamp conflated any edit with real deal progress AND froze when work happened off-Notion — on 2026-07-17 the 754 Old SR 74 row false-flagged STALLED (36d) while under active PSA negotiation, purely because its Last Updated hadn't moved since 6/11.

## STEP 2b — Resolve the next-action date (added 2026-08-11)

The tracker carries a `Next Action Date` date property (added 2026-08-11). It is **not** authoritative on its own — on the day it was added, 3 of 9 open rows were populated and 6 were null. Reading the column alone would silently drop every deal whose date lives only in `Next Action` prose, and would keep dropping any future deal where an owner writes the date but skips the field. Resolve per deal by this chain — deliberately the same shape as STEP 2's activity-date chain, which already solved this exact new-field-partial-coverage problem:

1. `Next Action Date` (`date:Next Action Date:start`) — PREFERRED.
2. Else, an explicit ISO-form date parsed out of the `Next Action` text (the tickler convention: `RE-CHECK 2026-08-21`, `Revisit 2026-08-14`, `CALL WEDNESDAY 2026-08-12`).
3. Else, **null**. Report it as null — never infer a date from stage, target close, or "about a month out."

**If rungs 1 and 2 both yield a date and they DISAGREE, emit `DATE DIVERGENCE`, report both values, and do NOT auto-reconcile.** This mirrors `ora-deal-aging-sla` STEP 3b verbatim: correcting the field would destroy the only evidence that the column and the prose had drifted, on exactly the deal where that drift mattered.

**This board never WRITES `Next Action Date`** — same charter reason it never writes `Last Activity` (STEP 2). A board that stamps the field it reads would launder its own inference into the record and, worse, make the field look adopted when nothing had adopted it. Stamping is the job of the deal-touching skills and of explicit in-turn direction. The three values populated on 2026-08-11 were written by Gabriel's in-turn instruction, which is not this rule's subject.

Coverage tag, mirroring STEP 2's: on any row resolved via rung 2, append "(date from Next Action prose — Next Action Date unset)" to that row's date cell, so the stamping backlog stays visible and shrinks as skills adopt the field.

## STEP 3 — Single blocking next action (text only)
For each deal, extract or summarize the single most current blocking action from its "Next Action" field, in one sentence. This board NAMES the next action — it does NOT draft, send, or execute anything (drafting is a separate, not-yet-built capability; out of this task's scope). Classify who/what the action is waiting on: Gabriel (a decision only he can make), a named external party (counsel, broker, lender), or Automation (a next step handled by another skill/task, e.g. "route to ora-flood-zoning-dd").

## STEP 4 — Confidentiality
Never surface any active confidential deal's raw terms on this board if it would cross to an external surface — this board is internal-only (rendered in-session + optionally an internal email pointer to ggoldberg@oxfordra.net), so full detail is fine, but do not paste deal specifics into any external tool call while building the board. Check `~/.claude/hooks/confidential-terms.json` for any `active:true` entries and handle with extra care if present (currently none active as of this task's creation).

## STEP 5 — Render
Render an interactive board via `mcp__visualize__show_widget` if available; otherwise fall back to a clean Markdown table. Columns: Deal · Address/Market · Stage · Days-in-Stage (flag STALLED if 30+ and not parked) · **Next Action Date (from STEP 2b; blank where null, tagged where prose-derived, marked `DATE DIVERGENCE` where the two sources disagree)** · Blocking Next Action · Waiting On (Gabriel/External/Automation) · link to the Notion page. Sort STALLED-and-unparked deals first, then by days-in-stage descending, so the deals most at risk of silently rotting surface at the top.

**The sort is unchanged by the STEP 2b addition (2026-08-11).** Sorting by next-action date instead would bury a 33-day silent deal beneath a deal with a date next week, which inverts what this board is for — the ratified sort surfaces rot, and an imminent date is not rot. Surface imminent dated actions as a separate strip above the board (deals whose resolved date falls within ~10 days, ascending), not by reordering the board itself. Changing the ratified sort is a decision for Gabriel, not a side effect of adding a column.

If you also send an email pointer, it MUST go via `send-via-outlook.ps1` (the sole COM send path) to `ggoldberg@oxfordra.net` ONLY — no cc, retry once on COM failure then flag loudly, never fall back to any other send mechanism.

## STEP 6 — Ops Hub posting (MANDATORY — added 2026-07-18, Plan 2 output-contract retrofit)

This is the task's final step and runs on EVERY fire — mandatory, not optional, and additive to (never a replacement for) the in-session widget rendering in STEP 5. Post a NEW DATED CHILD PAGE under the Notion Ops Hub parent page (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled exactly `"Deal Command Board — {YYYY-MM-DD}"` (today's date — the run date computed once at run start with `date '+%A %Y-%m-%d'`, date part in every date slot, weekday only where one is named, reused verbatim in every title, subject and body) — a distinct page created fresh each run, never an appended row/block inside an existing page's body (an append isn't reliably freshness-checkable downstream; a new titled child page is — standardized pattern, see `ora-deal-aging-sla` STEP 7).

Content, at minimum:
- Deals surfaced (count pulled in STEP 1)
- Deals flagged STALLED (count from STEP 2)
- A pointer to the full board: link(s) to the surfaced deals' Notion pages, or a note that the full interactive board rendered in-session (widget) and is not separately archived

If STEP 1's Notion query failed or returned clearly incomplete data (per HARD GUARDRAILS), post this page anyway, stating that explicitly — a missing post must never be the silent downstream result of an upstream query failure. On a Notion post failure (including a create response without a page ID, e.g. a grace-period/quota notice), first look for it — `notion-fetch` the parent for an exact-title child, then search by the exact title (search lags: a miss alone is not proof; after a grace/quota notice never retry, report UNVERIFIED) — a match created at/after the create call is this run's page, use it and do not retry (never blind-retry a create — that produced a duplicate; quota errors → `notion-quota-fallback` skill); retry once only if no match, then flag loudly in the chat/run summary — do not silently drop the post.

## HARD GUARDRAILS (verbatim from ora-open-sessions-board — do not weaken)
- No money, trades, or any external send without Gabriel's in-turn confirmation.
- Never edit any governor constant (DSCR 1.25x / LTV 40%) — this task only reads Notion, it has no reason to touch financial models or memory files.
- Never touch oxfordra.net.
- Never fabricate a deal, a stage, or a next-action — if a field is missing/null, say "not stated" rather than inventing content.
- If the Notion query fails or returns clearly incomplete data, say so explicitly in the board's own output rather than silently rendering a partial or stale board as if it were complete.

## RUN SUMMARY
End with a one-line run summary (deals pulled, how many STALLED, how many PARKED, any query/render errors, STEP 6 Ops Hub post result) for the health-guard fleet to pick up.
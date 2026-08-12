---
name: ora-deal-command-board
description: Weekly Monday deal-first pipeline board (draft-only, ggoldberg-only) — complements ora-open-sessions-board (sessions, not deals). Built 2026-07-17 per the ROI-brief Tier-2 acquisition-velocity plan. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

You are running ORA's weekly Deal Command Board — a Monday-morning, deal-first pipeline board for Gabriel Goldberg (Oxford Realty Advisors). This complements (does not replace) the daily ora-open-sessions-board, which tracks Claude sessions, not deals — this task tracks open acquisition pipeline deals specifically. Built 2026-07-17 as part of the 2026-07-16 setup review's Tier-2 acquisition-velocity plan (item 2.2).

[MODEL: claude-sonnet-5]

## STEP 1 — Pull open pipeline deals
Query the Notion Acquisition Pipeline Tracker (data source `collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) via `notion-query-data-sources` (SQL mode) for every row where Stage is NOT IN ('Closed Won','Passed','Killed','Killed — Reneg Only','Killed — Note/Short-Sale in Discussion'). Bare `'Killed'` is deliberate and must not be "tidied" out as redundant with the two `Killed —` variants: it is a distinct stage value, and its absence let E Fulton (Stage `Killed`, retired 2026-07-26, no open action) pass the filter into the 2026-07-27 `ora-deal-aging-sla` run. Added 2026-07-27; mirrored the same day in `ora-deal-aging-sla` STEP 1 — the two lists must stay identical. Pull: Deal Name, Address, Stage, Next Action, Last Activity (SQL column `date:Last Activity:start`), Last Updated, Deal Owner, Target Close Date. This must be a full, unpaginated pull — if the tool indicates more rows exist, keep paging (has_more/next_cursor) until exhausted; a partial pull that silently drops rows is worse than no board at all.

## STEP 2 — Compute days-in-stage
For each deal, days-in-stage = today minus the deal's **activity date**, resolved by this fallback chain (added 2026-07-17):
1. `Last Activity` (`date:Last Activity:start`) — PREFERRED. This is an explicit date stamped by deal owners and deal-touching skills (loi-generation, deal-execution, acquisition-underwriting, etc.) on real deal progress. It is NOT the system last-edited timestamp, so it does not move on cosmetic edits and does not go stale when work happens off-Notion.
2. `Last Updated` (Notion system last-edited time) — FALLBACK when `Last Activity` is null (legacy/un-stamped rows).
3. `createdTime` — last resort if both are null.

Flag any deal at 30+ days as STALLED, UNLESS its "Next Action" text contains "PARKED" (an explicit Gabriel-ratified hold is not the same failure mode as silent staleness — do not flag parked deals as stalled).

Coverage note: for any row where the flag is running on the FALLBACK (`Last Activity` is null), append a quiet "(days from Last Updated — Last Activity unset)" tag to that row's day cell, so field-coverage gaps are visible and shrink as skills adopt the stamp. Do NOT write `Last Activity` from this board — it is read-only by charter; a board that stamped activity would reset its own stall clock merely by surfacing a deal (self-defeating false-negative). Stamping is the job of the deal-touching skills (see the skills-pass backlog item filed 2026-07-17).

Rationale (why this field exists): keying staleness on the system last-edited timestamp conflated any edit with real deal progress AND froze when work happened off-Notion — on 2026-07-17 the 754 Old SR 74 row false-flagged STALLED (36d) while under active PSA negotiation, purely because its Last Updated hadn't moved since 6/11.

## STEP 3 — Single blocking next action (text only)
For each deal, extract or summarize the single most current blocking action from its "Next Action" field, in one sentence. This board NAMES the next action — it does NOT draft, send, or execute anything (drafting is a separate, not-yet-built capability; out of this task's scope). Classify who/what the action is waiting on: Gabriel (a decision only he can make), a named external party (counsel, broker, lender), or Automation (a next step handled by another skill/task, e.g. "route to ora-flood-zoning-dd").

## STEP 4 — Confidentiality
Never surface any active confidential deal's raw terms on this board if it would cross to an external surface — this board is internal-only (rendered in-session + optionally an internal email pointer to ggoldberg@oxfordra.net), so full detail is fine, but do not paste deal specifics into any external tool call while building the board. Check `~/.claude/hooks/confidential-terms.json` for any `active:true` entries and handle with extra care if present (currently none active as of this task's creation).

## STEP 5 — Render
Render an interactive board via `mcp__visualize__show_widget` if available; otherwise fall back to a clean Markdown table. Columns: Deal · Address/Market · Stage · Days-in-Stage (flag STALLED if 30+ and not parked) · Blocking Next Action · Waiting On (Gabriel/External/Automation) · link to the Notion page. Sort STALLED-and-unparked deals first, then by days-in-stage descending, so the deals most at risk of silently rotting surface at the top.

If you also send an email pointer, it MUST go via `send-via-outlook.ps1` (the sole COM send path) to `ggoldberg@oxfordra.net` ONLY — no cc, retry once on COM failure then flag loudly, never fall back to any other send mechanism.

## STEP 6 — Ops Hub posting (MANDATORY — added 2026-07-18, Plan 2 output-contract retrofit)

This is the task's final step and runs on EVERY fire — mandatory, not optional, and additive to (never a replacement for) the in-session widget rendering in STEP 5. Post a NEW DATED CHILD PAGE under the Notion Ops Hub parent page (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`), titled exactly `"Deal Command Board — {YYYY-MM-DD}"` (today's date) — a distinct page created fresh each run, never an appended row/block inside an existing page's body (an append isn't reliably freshness-checkable downstream; a new titled child page is — standardized pattern, see `ora-deal-aging-sla` STEP 7).

Content, at minimum:
- Deals surfaced (count pulled in STEP 1)
- Deals flagged STALLED (count from STEP 2)
- A pointer to the full board: link(s) to the surfaced deals' Notion pages, or a note that the full interactive board rendered in-session (widget) and is not separately archived

If STEP 1's Notion query failed or returned clearly incomplete data (per HARD GUARDRAILS), post this page anyway, stating that explicitly — a missing post must never be the silent downstream result of an upstream query failure. On a Notion post failure, retry once, then flag loudly in the chat/run summary — do not silently drop the post.

## HARD GUARDRAILS (verbatim from ora-open-sessions-board — do not weaken)
- No money, trades, or any external send without Gabriel's in-turn confirmation.
- Never edit any governor constant (DSCR 1.25x / LTV 40%) — this task only reads Notion, it has no reason to touch financial models or memory files.
- Never touch oxfordra.net.
- Never fabricate a deal, a stage, or a next-action — if a field is missing/null, say "not stated" rather than inventing content.
- If the Notion query fails or returns clearly incomplete data, say so explicitly in the board's own output rather than silently rendering a partial or stale board as if it were complete.

## RUN SUMMARY
End with a one-line run summary (deals pulled, how many STALLED, how many PARKED, any query/render errors, STEP 6 Ops Hub post result) for the health-guard fleet to pick up.
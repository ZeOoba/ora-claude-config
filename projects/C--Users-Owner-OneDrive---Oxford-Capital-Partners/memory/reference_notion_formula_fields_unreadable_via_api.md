---
name: reference_notion_formula_fields_unreadable_via_api
description: "Notion formula-type properties can't be read by any automated consumer of the Notion MCP -- confirmed against the Acquisition Pipeline Tracker's Action Overdue formula, 2026-08-13. Read before building any standing check that would gate logic on a formula column's value."
metadata:
  node_type: memory
  type: reference
  originSessionId: 1979c7ef-f501-40d6-b52e-d0a382f750a3
  modified: 2026-08-13T16:53:50.143Z
---

# Notion formula columns are opaque to the MCP -- for every row, not just one

**The finding (2026-08-13).** The Acquisition Pipeline Tracker (`collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`) carries a formula column `⏰ Action Overdue`. Investigating why 4484 Robertson Road's blown 2026-08-12 call date didn't show up on it surfaced a structural gap, not a formula-logic bug:

1. The data source schema marks all three formula columns (`Price Per SF`, `⏰ Action Overdue`, `Replacement Cost Ratio`) `notAvailableInQuerySql` -- SQL mode can't select them at all.
2. `notion-fetch` on the page, and `notion-query-data-sources` in **both** SQL mode and view mode, all return the same thing for a formula property: an unresolved `formulaResult://<data-source>/<page>/<code>` placeholder string, never the computed boolean/number/text. Verified directly against 4484 Robertson's row via all three call shapes the same session.
3. A repo-wide grep (`scheduled-tasks/*/SKILL.md`, `ora-skills/*/SKILL.md`) for `Action Overdue` turned up **zero** references -- nothing in the fleet has ever tried to read this column, presumably because whoever built it hit the same wall.

**What this means:** a Notion formula column can be a perfectly good *display* aid for a human looking at a database view, and simultaneously **completely unusable as an automation signal** through this MCP, regardless of whether the formula's own logic is correct. There is no known workaround (no resolver tool was found for `formulaCode://` or `formulaResult://` URIs in the loaded Notion tool set as of this date).

**How to apply:** if a standing check needs the thing a formula column is *displaying* (an overdue flag, a computed ratio, a derived price), don't try to query the formula -- pull the raw input columns via SQL/view mode and recompute the same logic in the skill itself. This is exactly the shape `ora-deal-aging-sla` STEP 3d already uses (recomputes overdue status from `Next Action Date` / `Last Activity` rather than reading `⏰ Action Overdue`), and it is the pattern to copy for any other Notion formula a future skill is tempted to depend on. Before trusting a *different* formula column's queryability, re-verify rather than assuming this finding generalizes automatically -- confirm the property still shows in that data source's `notAvailableInQuerySql` list, or that a fetch/query call on a live row still comes back as a `formulaResult://` placeholder.

Related: [[reference_notion_view_dsl_formula_filter_bug]] (a different formula-related Notion gotcha -- view-DSL filters on formula columns silently no-op; that one is about *filtering*, this one is about *reading the value at all*) · [[reference_ora_pm_critical_dates_feed_unreliable_2026-08-04]] (another case of a fleet building a workaround instead of trusting a purportedly-authoritative field).

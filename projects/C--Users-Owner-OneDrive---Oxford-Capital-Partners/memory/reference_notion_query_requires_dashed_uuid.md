---
name: reference-notion-query-requires-dashed-uuid
description: notion-query-data-sources rejects undashed collection UUIDs — several ORA SKILL.mds cite the undashed form and fail on first call
metadata: 
  node_type: memory
  type: reference
  originSessionId: efbb59f6-5cbe-497b-bbe0-a007f7b0cc40
  modified: 2026-07-24T14:50:25.047Z
---

`notion-query-data-sources` (SQL mode) requires the **dashed** data-source UUID. Passing the undashed form fails with `validation_error` / `sql_invalid`: *"table \"collection://<id>\" was not exposed for this request."* The error names the table, so it reads like a permissions or exposure problem rather than a formatting one — that's the trap.

- Works: `collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`
- Fails: `collection://bcfe4a037e614ac1a0bbc44174fa138b`

Recovery: `notion-fetch` the database ID and read the URL out of the `<data-source url="...">` tag, which always returns the dashed form.

FIXED 2026-07-24 (per Gabriel): `ora-deal-aging-sla` STEP 1 carried the undashed Acquisition Pipeline Tracker id from authoring, so every run before that date failed its first query and recovered by hand. Corrected to the dashed form in SKILL.md v1.1, with an inline "do not tidy the dashes out" warning.

Sweep result (two independent methods — `Grep` and a Python walk, since rg has false-negatived rooted at `scheduled-tasks` before): that was the **only** undashed `collection://` literal across `~/.claude/scheduled-tasks/`, `ora-skills`, and the LAMS `Documents/Claude/Scheduled` tree. Both trees verified clean afterward. No need to re-sweep unless a new skill hardcodes a collection id.

Related: [[reference_cc_scheduler_filepath_mechanism]] (editing SKILL.md IS authoritative — no re-registration needed for a text fix).

Related: [[reference_notion_view_dsl_formula_filter_bug]] · [[tech]]

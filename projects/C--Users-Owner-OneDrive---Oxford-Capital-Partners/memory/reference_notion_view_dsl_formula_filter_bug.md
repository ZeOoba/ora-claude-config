---
name: notion-view-dsl-formula-filter-bug
description: "The Notion MCP's create_view/update_view DSL cannot correctly filter on FORMULA-type properties — always mis-encodes them as a rollup-style \"every\" quantifier with a text resultFilter, producing a silent no-op that matches every row"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 86ec9edd-63ac-49e3-a01a-f5729bf946ca
  modified: 2026-07-22T13:50:05.242Z
---

Confirmed by direct testing 2026-07-22 while building the Tenant DB "Renewal Watch" view ([project_tenant_db_renewal_watch_view_2026-07-22.md](project_tenant_db_renewal_watch_view_2026-07-22.md)): any `FILTER "<formula property>" <op> <value>` — tried with `<=`, `=`, on both a number-output formula and a checkbox-output formula — gets encoded as:

```
{"propertyType":"formula","operator":"every","resultFilter":{"propertyType":"text","operator":"string_is","value":...}}
```

This is the Notion API's ROLLUP filter shape (`any`/`every`/`none` + `resultFilter`), not the FORMULA filter shape (`"formula":{"number":{...}}` / `{"checkbox":{...}}`). Applied to a scalar formula (not an actual rollup-over-relation), the "every" quantifier is vacuously true for every row — the filter becomes a no-op and returns the entire table regardless of the formula's real value. Confirmed empirically: a checkbox formula `= true` filter returned all ~140 rows instead of the expected subset.

Plain NUMBER/DATE/SELECT/CHECKBOX native-type properties filter correctly through the same DSL (`number_less_than_or_equal_to`, `date_is_on_or_before`, `enum_is_not`, `checkbox_is_not` all worked as expected).

Native DATE properties also do NOT support relative offsets through this DSL — `<= "+90d"` and `<= "next 90 days"` are silently accepted (no error) but function as invalid/unparseable literals and return zero matching rows. Only absolute ISO date literals (`"2026-10-20"`) work, and arithmetic syntax (`today()+90`) is a hard parse error ("Unexpected character: +").

**How to apply:** Never build a saved-view filter directly on a formula-output property (Months Remaining, Days to Expiration, Risk Flag, etc.) via this tool — it will silently pass validation and then match everything. Filter on the underlying native property instead (e.g. the source date/number/select field), using an absolute date threshold recomputed at build time. A view built this way needs periodic re-editing to keep the threshold current — see [project_tenant_db_renewal_watch_view_2026-07-22.md](project_tenant_db_renewal_watch_view_2026-07-22.md) for the recommended follow-up (piggyback the refresh on an existing scheduled task rather than a new one). Also: no programmatic view-delete tool exists in this MCP — throwaway/test views must be manually trashed in the Notion UI (rename them clearly first so they're identifiable).

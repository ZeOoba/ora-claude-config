---
name: reference_metrics_history_pattern_does_not_exist_2026-08-17
description: "A brain-repo 'Metrics History' / 'Category 4a/4b write-through' pattern for Leasing/Ops/Market, cited in a 2026-08-17 handoff prompt as already existing, was verified NOT to exist anywhere -- correct home for property-tax data is the existing property_tax_assessments table instead."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8c75df1a-cbf6-4a26-8e48-95447df2da42
  modified: 2026-08-17T20:32:52.571Z
---

A 2026-08-17 Cowork-to-Code handoff prompt (Tax & Settlement systemization
sprint) asserted that `oxford-brain-ingest`/`oxford-command-center` already
writes a "Metrics History" table for Leasing/Ops/Market data via a "Category
4a/4b write-through" pattern, sourced to the `monthly-close` skill's
changelog, and asked whether new property-tax-trend and 1031-exchange-chain
data should be added to it.

**Verified absent, not just unfound.** Grepped both repos (source + `oxford-
command-center/architecture/database-schema.md`, the repo's own schema-lock
doc) for "Metrics History", "metrics_history", "write-through", "Category
4a", "Category 4b": zero matches anywhere, code or docs. `oxford-brain-
ingest` (`C:\Users\Owner\oxford-brain-ingest`) turns out to hold **no code at
all** — it's a flat folder of ~30 CSV data exports, not an ingestion layer,
so it structurally cannot be the mechanism described. `monthly-close/
SKILL.md` does have a `## CATEGORY 4` section, but it's "QB MONTH-END
JOURNAL ENTRIES" — unrelated to Leasing/Ops/Market, no 4a/4b subdivision.

**What actually exists** in `oxford-command-center/data/warehouse/
finance.sqlite`: four separate, narrow, purpose-built tables (migrations
004, 011–013) — `property_occupancy`, `lease_events`, `prospect_demand_
events`, `market_series` — each with domain-specific columns/CHECK
constraints, not a generic category/metric/value envelope. Two of the four
(`lease_events`, `market_series`) are schema-only: present in the DB but
with **no live INSERT path anywhere** in `server/` or `scripts/` — dormant,
not fed by any skill or scheduled task. Forcing new metric types into any of
these four would be a schema mismatch.

**The actually-correct home for property-tax data** is a different,
already-live pair: `property_tax_assessments` + `tax_appeals`
(`server/warehouse/migrations/020_property_tax.sql`), with a working
importer (`scripts/import-assessments.ts`) and CSV template
(`docs/templates/property-tax-assessments.template.csv`). Nobody has run
that importer against the 2026-08-17 `CARRYING_COST_TREND` register data yet
— it still lives only in Cowork-project-only markdown, not in a Code-
accessible file. The companion 1031 exchange chain register has no existing
table anywhere in the brain repo and, per the handoff's own fallback
instruction, was left in the Cowork project as source of record rather than
forced into a schema that doesn't fit.

**Reusable lesson:** a handoff prompt's description of another system's
internal architecture is a claim, not ground truth — [[feedback_verify_before_repeating_session_claims]]
and [[feedback_absence_claims_need_verification_before_building]] both apply
here, but so does the inverse: an *existence* claim needs the same grep-
before-build discipline an absence claim does. Don't build against a named
pattern (table, script, doctrine section) without confirming it's there
first, in either direction.

Full session record: [[event_log]] 2026-08-17 "settlement-basis-extraction
skill committed; Metrics History brain-repo pattern found NOT to exist".
Data gaps surfaced in the same sprint: [[open-items-tracker]] OI-187
(Westerville ALTA illegible), OI-188 (Northwood no tax record).

---
name: xlsx-warehouse-importer
description: Use when a spreadsheet or JSON extract (broker loss runs, PCA/capex register, assessor export, dec pages, any xlsx a Cowork session produced) must be loaded into the oxford-command-center SQLite warehouse as a new importer script — scaffold, validation rules, property-id crosswalk, idempotency and test checklist. Trigger on: import this xlsx into the warehouse, new importer script, warehouse:import, load the register into the warehouse, loss-run importer, PCA importer, ingest extraction register, importer template. Pattern source is scripts/import-insurance-data.ts. Does NOT cover the P&L/QuickBooks ingest (ingest.ts), migrations (architect-owned) or surfaces that read the data.
license: ORA Internal
---

# xlsx-to-warehouse importer (v1.0)

The importer pattern has been built for assessments, insurance loss runs and dec pages, and is next needed for the PCA register. Reuse it; do not reinvent it. Reference implementation: `oxford-command-center/scripts/import-insurance-data.ts` (read it first, it is the spec). Sibling: `scripts/import-assessments.ts`.

## Preconditions (stop if any fails)

1. Target tables exist. Migrations and `src/contracts/` are **architect-owned** (repo CLAUDE.md §4): no importer ships ahead of an approved migration. Phase work needs Gabriel's approval (CLAUDE.md §3).
2. Source of record is decided (xlsx now vs Notion). Record it in the importer header.
3. Work in a worktree off fresh `origin/main` with its own `WAREHOUSE_DB`; never touch `data/warehouse/finance.sqlite` directly (CLAUDE.md §5, §9). Run `git status` first and treat every uncommitted file you did not create as locked.
4. Pipeline/acquired properties absent from `property-master` are handled per **Property ids** below, never by editing `CANON_PROPERTIES`.

## Shape: three layers, one file

```
scripts/import-<thing>.ts
  parse<Thing>Payload(payload, defaultSource) -> { rows, rejected[] }   // pure, no DB, no I/O, exported
  import<Thing>Rows(db, rows)                 -> counts                 // DB writes, exported
  import<Thing>(db, payload, source)          -> counts                 // parse + import, for tests
  parseArgs(argv) / main(argv)                                           // CLI
  if (process.argv[1]?.replace(/\\/g,'/').endsWith('scripts/import-<thing>.ts')) process.exit(main(...))
```

- **xlsx first becomes JSON.** Read the workbook with the project's existing xlsx reader (ExcelJS is already a dependency), map named columns to the same row shape the JSON mode accepts, and feed the one parser. Two input paths, one validator.
- Importing for tests must never open a DB or write (the direct-invocation guard above).
- Default DB: `process.env.WAREHOUSE_DB ?? data/warehouse/finance.sqlite`; accept `--db <path>`.
- Exit 0 on success, 1 on unreadable file, bad JSON, unopenable DB or DB error. Print one summary line per mode plus rejected/ignored counts.

## Validation rules (every importer)

- **Format failures are rejected and reported, never persisted and never auto-fixed.** Missing required field, wrong type, negative or non-finite money, non-ISO date. A human fixes the source file.
- **Dates are strict ISO `YYYY-MM-DD`** via `isIsoCalendarDate` (`server/warehouse/placeholder-data.ts`). A US `MM/DD/YYYY` or an Excel serial silently corrupts downstream year extraction. Convert Excel serials in the xlsx reader, then validate; reject anything that is not a real calendar day.
- Money ceilings share the loader's constant (`MAX_LOSS_EVENT_USD` pattern) so an accepted row is never coerced to $0 on read.
- Cross-field invariants are checked at the boundary (example: `deductible <= coverageLimit`). Do not patch the engine to mask bad input.
- Source flags travel with the row: `[OCR-UNVERIFIED]`, `[DERIVED]`, Verified = No, Confidence. Import carries flags; it does not fix or drop them.
- Blank beats inferred. Leave Funding Class `Unknown` and Lease Recovery `Unreviewed`; those are human tags.
- **Basis discipline:** estimates (consultant) and quotes/actuals (contractor) stay in separate tables or carry a Price Basis column. Never blend them into one aggregate. Capex reserve basis is neither Spine A NOI nor Spine B ledger; never sum it with NOI.

## Idempotency and isolation

- `INSERT OR IGNORE` against a natural-key `UNIQUE` plus the PRIMARY KEY; `changes === 0` means `ignored`, a re-run reports the same rows as ignored, not duplicated.
- Upserts that must preserve other columns use `UPDATE ... WHERE id = ?` on the matched row, never `INSERT OR REPLACE` (it mints a new AUTOINCREMENT id and wipes columns another mode wrote).
- Each row's write sits in its own try/catch **inside** one `db.transaction()`, so one bad row never rolls back the rest. A caught DB error also writes a `data_quality_issues` row (`kind='<domain>-check-violation'`) so the failure is auditable.
- Record provenance: source file path and `sha256` of the file on the report/header row, plus `ingested_by`.
- Mutually exclusive modes are rejected in `parseArgs`, not silently resolved.

## Property ids

Resolve register names through `server/warehouse/property-crosswalk.ts`, then `property_master`:

1. Known id → write it.
2. **Building inside a consolidated entity** (Banwick, Old Morrison and the other Sepich buildings): alias to `sepich-portfolio-columbus-oh-8-props`, matching the existing `parse.ts` alias. Keep the building name in a `location`/`building` column so per-building detail survives the entity-level key.
3. **Pipeline or acquired asset with no master row** (e.g. 3520 E Fulton): store `property_id = NULL` (FK-exempt, same as a portfolio-level loss) plus a `pipeline_ref` text column, and log a `data_quality_issues` row `kind='<domain>-pipeline-unmapped'`. Never invent an id and never add rows to `CANON_PROPERTIES` (ratified canon, "do not edit without a new ruling").
4. Present, non-blank id not in `property_master` and not covered by the rules above: skip and log `kind='<domain>-unknown-property'` (never insert, the FK would misattribute).

Confidential check before any row naming a deal: roster of record is `hooks/confidential-terms.json`; keep deal figures out of any public export.

## Tests (vitest, `tests/unit/`)

- Parser: one test per reject reason; a valid row; blank-optional handling.
- Importer: idempotent re-run (second run all `ignored`); unknown property to DQ row; NULL-property pipeline row; per-row isolation (one constraint violation does not block siblings); preserved-column check for upsert modes.
- CLI `parseArgs`: each mode, missing value, mutually exclusive flags.
- xlsx fixture: small checked-in workbook that exercises the reader (Excel-serial date, blank cells, flag columns).
- Assertions over live state are directional, never a hardcoded snapshot count.

## Done bar

`npm run gate` green in the worktree, tests above present, importer header documents modes, input shape, idempotency key and what is rejected vs persisted. Financial-decision consumers of the imported data (capital-allocation, IRR) need the `refute-financial-change` workflow before merge; the importer alone does not.

## Known instances

| Importer | Source | Notes |
|---|---|---|
| `import-assessments.ts` | county assessor CSV | original pattern |
| `import-insurance-data.ts` | loss-run JSON, dec pages, policies | three modes; reference implementation |
| `import-pca-register.ts` (planned) | `PCA-Extraction_Register` xlsx | plan: `docs/capital/2026-10-07-pca-capex-ledger-integration-plan.md`; source of record is the xlsx now, Notion later |

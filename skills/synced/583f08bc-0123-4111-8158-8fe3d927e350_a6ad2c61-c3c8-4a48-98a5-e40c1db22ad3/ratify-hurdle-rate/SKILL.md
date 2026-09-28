---
name: ratify-hurdle-rate
description: >
  Formally ratify the Oxford Realty Advisors unlevered IRR hurdle rate in the
  capital_config table — flipping hurdle_rate_ratification from 'proposed' to
  'ratified', stamping Gabriel's name and date, running the gate, and producing a
  durable audit memo. Use when Gabriel says: ratify hurdle rate, confirm hurdle rate,
  lock in IRR hurdle, ratify the 8%, make the hurdle rate official, sign off on hurdle
  rate, or capital allocation hurdle ratification. Requires migration 015_hurdle_rate.sql
  to be applied (adds hurdle_rate_* columns to capital_config). v1.3 (2026-08-03:
  audit-memo template stamped Gabriel as "Principal" against CLAUDE.md's ratified
  "VP Acquisitions" — corrected; caught by doctrine-integrity-probe Check 13)
---

# ratify-hurdle-rate

Formally ratify the ORA unlevered IRR hurdle rate. Updates the `capital_config` table's
`hurdle_rate_ratification` column from `proposed` → `ratified`, stamps Gabriel's name
and date, verifies the gate is clean, and emits a durable audit memo under
`docs/capital/`.

**Schema note:** migration 015_hurdle_rate.sql adds four columns to `capital_config`
(not a separate table): `hurdle_rate_pct`, `hurdle_rate_ratification`,
`hurdle_rate_ratified_by`, `hurdle_rate_ratified_date`.

---

## Pre-flight (run before any prompt to Gabriel)

**1. Confirm migration 015_hurdle_rate.sql has been applied.**

```python
import sqlite3
con = sqlite3.connect('C:/Users/Owner/oxford-command-center/data/warehouse/finance.sqlite')
cols = [r[1] for r in con.execute("PRAGMA table_info(capital_config)").fetchall()]
print(cols)
```

If `hurdle_rate_ratification` is NOT in the column list: STOP.

> "Migration 015_hurdle_rate.sql has not been applied yet. It is present on `main`
> (merged via PR #117) — run `npm run migrate` from oxford-command-center to apply
> it, then re-invoke this skill."

**2. Read the current proposed row.**

```python
row = con.execute(
    """SELECT version, hurdle_rate_pct, hurdle_rate_ratification,
              hurdle_rate_ratified_by, hurdle_rate_ratified_date
       FROM capital_config
       ORDER BY version DESC
       LIMIT 1"""
).fetchone()
print(row)
```

Capture: `hurdle_rate_pct` (decimal, e.g. 0.08), `hurdle_rate_ratification`, `version`.

If the query returns no rows: STOP.
> "capital_config is empty. Run `npm run migrate` from the oxford-command-center
> directory to seed the initial row."

If `hurdle_rate_ratification` is already `'ratified'`: STOP.
> "The hurdle rate is already ratified at [X]% (capital_config version [N]). Nothing
> to do."

---

## Step 1 — Confirm with Gabriel

Present this block verbatim before any write:

```
HURDLE RATE RATIFICATION
───────────────────────────────────────────
Current value  : [hurdle_rate_pct × 100]% unlevered IRR
Ratification   : proposed  →  ratified
Ratified by    : Gabriel Goldberg
Ratified date  : [YYYY-MM-DD]   ← today's date
Capital config : version [N] (row updated in-place)
DB             : oxford-command-center / capital_config
───────────────────────────────────────────
Proceed? (yes to confirm · no to abort · or enter a different rate, e.g. "7%")
```

**Accept:** "yes", "y", "confirm", "proceed" → `confirmed_rate` = the `hurdle_rate_pct`
read in Pre-flight (unchanged) → continue to Step 2.

**Modify rate:** Gabriel gives a different percentage (e.g. "7.5%") →
recompute to decimal (0.075), warn if outside [1%, 30%] ("Unusual value — confirm"),
re-present the block with the new value, wait for "yes" → `confirmed_rate` = the
recomputed decimal (0.075) → continue to Step 2.

**Abort:** any other input → STOP with no writes.

`confirmed_rate` is whatever value was last shown in a confirmation block that Gabriel
said "yes" to — carry it into Step 2 explicitly. Do NOT re-read `hurdle_rate_pct` from
the DB at Step 2 and assume it already matches: on the Modify-rate path it does not,
until Step 2's UPDATE writes it.

---

## Step 2 — Write ratification

```python
import sqlite3
from datetime import date

con = sqlite3.connect('C:/Users/Owner/oxford-command-center/data/warehouse/finance.sqlite')
today = date.today().isoformat()   # e.g. '2026-06-22'
# confirmed_rate: the decimal rate from Step 1's accepted confirmation block (e.g. 0.08,
# or 0.075 if Gabriel modified it). ALWAYS write it explicitly — never omit hurdle_rate_pct
# from the SET clause and assume the DB's existing value already matches; on the Modify-rate
# path it doesn't, and a memo asserting a rate the DB never received is a Hard Invariant 4
# breach (a ratified-but-wrong governor value).

con.execute(
    """UPDATE capital_config
       SET hurdle_rate_pct           = ?,
           hurdle_rate_ratification  = 'ratified',
           hurdle_rate_ratified_by   = 'Gabriel Goldberg',
           hurdle_rate_ratified_date = ?
       WHERE hurdle_rate_ratification = 'proposed'""",
    (confirmed_rate, today)
)
print(con.total_changes, "row(s) updated")
```

Then verify — BEFORE committing, so a failed assertion still leaves the DB untouched
(the read below runs on the same connection/transaction and sees the pending write):

```python
row = con.execute(
    """SELECT version, hurdle_rate_pct, hurdle_rate_ratification,
              hurdle_rate_ratified_by, hurdle_rate_ratified_date
       FROM capital_config
       ORDER BY version DESC
       LIMIT 1"""
).fetchone()
print(row)
assert row[1] == confirmed_rate, (
    f"hurdle_rate_pct in the DB ({row[1]}) does not match the value Gabriel confirmed "
    f"({confirmed_rate}) — the ratification memo must never assert a rate the DB doesn't hold."
)
con.commit()
```

The output MUST show `hurdle_rate_ratification = 'ratified'` AND `hurdle_rate_pct`
equal to `confirmed_rate`. If `total_changes` is 0, the column still shows `proposed`,
or the assertion above fails, STOP and surface the error. Do NOT proceed to the gate.

---

## Step 3 — Gate

```bash
cd "C:/Users/Owner/oxford-command-center" && npm run gate
```

All steps must be green: `governance`, `typecheck`, `lint`, `test`, `reconcile`,
`warehouse:verify`.

If any step fails: surface the exact failing step and error. Do NOT write the audit
memo until the gate is fully green.

---

## Step 4 — Audit memo

Create `docs/capital/hurdle-rate-ratification-[YYYY-MM-DD].md` inside the
oxford-command-center repo. Do NOT commit — leave integration to Gabriel.

```markdown
# ORA Hurdle Rate Ratification — [YYYY-MM-DD]

**Ratified by:** Gabriel Goldberg, VP Acquisitions, Oxford Realty Advisors
**Date:** [YYYY-MM-DD]
**Hurdle rate:** [X]% unlevered IRR (decimal: [0.XX])
**Ratification status:** proposed → ratified
**Capital config version:** [N]
**DB record:** `capital_config.hurdle_rate_*` columns · oxford-command-center warehouse SQLite

Oxford Realty Advisors formally adopts [X]% unlevered internal rate of return as
the minimum acceptable return threshold for capital allocation decisions. This value
supersedes the prior `proposed` state and is now the active hurdle rate governing
the Capital Allocation module. It may only be changed by re-invoking the
`ratify-hurdle-rate` skill and presenting Gabriel with an explicit confirmation block.
Modifying the underlying value without ratification is a CLAUDE.md §4 invariant breach.
```

Confirm the file was written, then report:

> "Hurdle rate ratified: [X]% unlevered IRR · [YYYY-MM-DD] · gate green.
> Audit memo: docs/capital/hurdle-rate-ratification-[YYYY-MM-DD].md (uncommitted)."

---

## Error reference

| Condition | Action |
|-----------|--------|
| `hurdle_rate_ratification` column missing from `capital_config` | STOP — run `npm run migrate` to apply 015_hurdle_rate.sql (already on `main`, PR #117) |
| `capital_config` empty | STOP — run `npm run migrate` to seed |
| Already `ratified` | STOP — surface current state, nothing to do |
| UPDATE affects 0 rows | STOP — surface error |
| Gate step fails | Surface exact error — do not write memo |
| Rate outside [1%, 30%] | Warn before writing, require explicit "yes" |
| `docs/capital/` dir missing | Create with `mkdir -p` before writing memo |

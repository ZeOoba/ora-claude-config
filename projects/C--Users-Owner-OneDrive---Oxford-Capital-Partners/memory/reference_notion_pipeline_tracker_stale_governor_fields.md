---
name: reference-notion-pipeline-tracker-stale-governor-fields
description: "The Notion Acquisition Pipeline Tracker's Replacement Cost Ratio formula was stale at $95/SF and its DSCR description asserted a stale, non-canonical per-property hard floor — both fixed 2026-08-11 on Gabriel's authorization. Records the fix, the API limits hit, and the drift risk that remains."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 89c314f4-a39e-43b4-8d1b-6b38d91774f7
  modified: 2026-08-11T23:00:17.660Z
---

Found 2026-08-11 during the weekly deal-sourcing scan; **fixed the same day on Gabriel's explicit
in-turn authorization** (Hard Invariant 4 — governor-adjacent, so it needed his say-so).

## What was wrong
1. **`Replacement Cost Ratio`** (formula) computed against a flat **$95/SF**. That is RCT v01-era.
   The ratified denominator is **RCT v03** (per-metro LOW $227.90–$253.83, ratified 2026-07-14), so
   every value the field produced after that date was wrong by roughly **2.5x** — and it rendered as
   a plausible ratio, so it never looked broken.
2. **`DSCR`** field description asserted a stale per-property hard floor — corrected from 1.75x → 1.25x. The ratified per-property governor is 1.25x.
   **In Notion that description is now BLANK, not restated as 1.25x**
   (the API cannot write descriptions — see *Traps*), so a human must still retype it. The same stale
   figure also propagated into several rows' Notes narrative (511 Industrial Mile, 754 Old SR 74) —
   historical text, left as-is.

## What was done
- Formula rewritten to key off the **`Market`** select, one RCT v03 LOW per metro. Markets with **no
  RCT v03 row — `Cleveland OH`, `Other`, `Louisville KY` — now return BLANK, not a number.** That is
  deliberate: refusing to compute beats emitting a wrong figure (Liberty Office Park is tagged
  `Other` and had been silently producing a number).
- DSCR's false description **cleared to empty**.

## Traps hit — save the next session the trial-and-error
- **This database runs the OLDER formula engine.** `ifs()` and `lets()` BOTH fail with
  `Type error with formula`. Only nested `if()` works. Select comparison (`prop("Market") == "Columbus OH"`)
  works fine — it was not the problem, despite being the obvious suspect.
- **`ALTER COLUMN … SET <type>` WIPES that property's description** as a side effect. That is how the
  DSCR text was cleared. It does **not** wipe data values — DSCR's three live figures (1.33 / 1.36 /
  1.63) were verified intact afterward.
- **Property descriptions CANNOT BE SET via MCP.** The DDL supports ADD/DROP/RENAME/ALTER COLUMN only;
  the tool's `description` param targets the *data source*, not a column. Descriptions can only be
  cleared (via the ALTER side effect) or written in the Notion UI.
- **Formula results are unreadable through the API** — they return as opaque `formulaResult://` refs,
  and the field is in `notAvailableInQuerySql`. The formula was verified to *validate and type-check*;
  the rendered numbers were cross-checked by hand, not read back.

## What still needs a human
- Both descriptions are now **blank**. Correct text must be typed in the Notion UI.
- **Louisville RCT row — CLOSED 2026-08-11, and it is SOURCED, not a proxy: `Louisville KY | 237.07 |
  263.41 | 289.75 | 135.28`** (clears $82.97/SF at <=1995, $94.83 at >=2005). Added to
  `acquisition-underwriting`, the `ora-deal-sourcing-scan` mirror, and this formula.
  ⚠️ **THE LESSON — I proxied when a sourced figure was already in the repo.** I first shipped a
  `[PROXY: Columbus]` row after failing to scrape C&W's flipbook (canvas-rendered, no text layer) and
  after `target-markets.json` v1.8 asserted in writing that "Louisville is NOT in the C&W guide." **That
  assertion is false**, and the real per-market extract had been sitting at
  `~/.claude/scheduled-tasks/ora-deal-sourcing-scan/skills/cw-2025-construction-costs.json` the entire
  time — 45 markets, `small25`/`med25`/`large25` each. Louisville small25 = $135.28.
  **CHECK THAT FILE FIRST for any per-market hard cost, before proxying or scraping.**
  Derivation (reproduces the table's own method): `b = ln(small25/med25) / ln(476400/109200)`, size
  premium `(109200/40000)^b`, `POINT = small25 x premium x 1.30 x 1.0487`, `LOW = 0.90 x POINT`. Refute-
  tested against all 8 source metros behind the other 9 rows — reproduced every ratified POINT and LOW
  to the cent. **Resolved 2026-08-12 (Gabriel):** target-markets.json's Louisville `replacement_cost`
  block — wrong on both the number ($143.46, Indianapolis proxy) and its stated reason — was DELETED
  (backup: `target-markets.v1.8-pre-rc-delete-20260812.json.bak`). **The other nine clusters KEEP their
  blocks by decision** — their numbers are correct and match the C&W hard costs behind RCT v03, and they
  carry provenance found nowhere else (2024 comparatives, YoY %, land $/acre, small-bay extrapolations).
  Louisville is now the only cluster with no `replacement_cost` key. Those nine are PROVENANCE, NEVER a
  denominator — RCT v03 remains the only one.
- **The drift risk is not eliminated, only relocated.** Doctrine says there is exactly ONE denominator
  and a second is a bug — this formula IS a second location, and it will go stale at RCT v04 exactly as
  $95 did at v03. **Standing rule: on any RCT revision, update this formula in the same change.**

Related: [[firm]] (governors) · verify against `acquisition-underwriting` SKILL.md, which WINS on any conflict.

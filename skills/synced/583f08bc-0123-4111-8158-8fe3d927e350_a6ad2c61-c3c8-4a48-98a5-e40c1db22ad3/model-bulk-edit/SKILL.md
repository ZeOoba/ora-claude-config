---
name: model-bulk-edit
description: "Safely change the same input across many ORA financial models at once, and audit workbooks whose formulas carry no cached values. Use when the user says: rebase the models, update the refi rate everywhere, change an assumption across all deals, bulk edit workbooks, propagate a constant to the models, sweep the underwriting models, or after any UNDERWRITING CONVENTIONS constant moves in acquisition-underwriting. Also the SOLE path for the cached-value audit -- trigger on: nulls in the QC gate, model reads blank, dead workbook, formulas but no values, why is DSCR empty. Encodes: archive-then-verify before any write, Excel COM with CalculateFullRebuild (NEVER openpyxl for writes -- it silently destroys every cached value), constant-vs-formula pre-check, and a mandatory post-write diff of every model against its archived original. Historical models for closed or passed deals are rebased only on Gabriel's explicit instruction. v1.1"
---

# model-bulk-edit — Oxford Realty Advisors

One input, many workbooks. This skill exists because the dangerous part of a bulk model
edit is never the edit — it is the write mechanism, the models you did not know existed,
and the ones whose verdict quietly moves.

**DRAFT-SAFE, NOT DECISION-SAFE.** This skill changes numbers that decisions were made on.
It never runs unprompted. Hard Invariant 4 governs: modifying financial models requires
Gabriel's explicit instruction, and that instruction covers the models named in it, not
every model the sweep happens to find.

## STEP 0 — Scope, and the historical-record question (ask BEFORE editing)

Enumerate candidates first and classify each as **live** (active pipeline, still being
underwritten) or **historical** (closed, passed, or superseded). A historical model is the
record of a decision that was actually made on the old assumption — rebasing it rewrites
that record. Notion's score-snapshot doctrine ("IMMUTABLE — re-scores get new rows, never
overwrite history") is the standing analogue.

Default: rebase live models, leave historical ones, and **report the split rather than
resolving it silently**. Gabriel may direct otherwise; a blanket "do them all" is a valid
instruction and is then simply followed — but the split still gets reported so he knows
what the instruction covered.

## STEP 1 — Constant or formula? (never skip)

For every target cell, open with `openpyxl.load_workbook(path, data_only=False)` and read
the *stored* value. A literal (`0.07`) is safe to overwrite. A formula (`=Inputs!$B$38`) is
a **dependent** — it follows its precedent and must NOT be written; overwriting it severs
the link and creates a second source of truth. Record which is which before any write.

Also capture, per model: the value cell's exact coordinate, its number format (a rate stored
as `0.07` under a `0.00%` format is 7%, not 7 basis points of confusion), and the label text
you matched on, so the mapping is auditable afterward.

## STEP 2 — Archive, hash-verified, BEFORE any write

Copy each original to `_archive\<YYYY-MM-DD>_<change-slug>\` beside the file itself, then
SHA256 both copies and assert equality. Never delete, never move the original out of place
(Hard Invariant 6). The archive is not a courtesy — STEP 5's diff is computed against it,
so a missing archive means the change cannot be verified at all.

## STEP 3 — Write via Excel COM. NEVER openpyxl.

**This is the rule the whole skill exists for.** `openpyxl` round-trips preserve formulas but
**discard every cached value in the workbook**. The models then read `None` to any consumer
using `data_only=True` — which is exactly what ORA's own QC Gate does — until a human opens
each file in Excel and saves it. A silent, portfolio-wide degradation.

```powershell
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
$xl.AskToUpdateLinks = $false; $xl.EnableEvents = $false
$wb = $xl.Workbooks.Open($path, 0, $false)
$cell = $wb.Worksheets.Item($sheet).Range($addr)
if ([Math]::Abs([double]$cell.Value2 - $expectedOld) -gt 1e-7) { <# SKIP, report #> }
$cell.Value2 = $newValue
$xl.CalculateFullRebuild()      # not Calculate() -- rebuild the dependency tree
$wb.Save(); $wb.Close($false)
```

**Assert the old value before writing it.** A cell that does not hold what you expected is a
mapping error, not an edit target — skip it and report, never write through the surprise.
`CalculateFullRebuild()` rather than `Calculate()`: the latter can leave stale dependents when
the tree itself changed.

Host-shell discipline applies (same rule as `package-and-stage-skill` step 3): run this from a
`.ps1` file via `powershell -NoProfile -ExecutionPolicy Bypass -File <path>`, never an inline
`-Command` one-shot — `$` tokens are stripped in transit. PowerShell 5.1 has no `&&`.

## STEP 4 — Long sweeps outrun the tool timeout

A recursive Excel/openpyxl walk over the Business tree takes minutes and the MCP call caps out
around 60s. Launch detached and poll a file rather than re-running and hoping:

```powershell
# quote EVERY path inside the argument string -- ORA's roots all contain spaces
$args = '"{0}" "{1}" --quiet' -f $script, $root
Start-Process -FilePath python -ArgumentList $args `
  -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow
```

**The arg-splitting trap, twice in one session.** `-ArgumentList @($script,$root,"--quiet")`
splits `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business` on its spaces, so the
script receives `C:\Users\Owner\OneDrive` as its root. It does not error — it walks a real
directory, finds almost nothing, and prints a confident `1 workbook(s) | 0 dead-or-partial`.
A sweep that reports a suspiciously small count audited the wrong tree; check the root before
believing the verdict. **If the detached-launcher pattern misbehaves at all, stop fighting it
and run the command directly in a terminal** — the harness is not the deliverable, and a
silent wrong-root result is worse than no result.

## STEP 5 — Diff every model against its archived original

Re-read live and archived copies with `data_only=True` and report, per model: the target cell
old → new, every metric that moved, and **explicitly, every metric that did not**. An unmoved
metric is a finding, not an absence of one — when refi proceeds hold flat under a rate cut, the
LTV ceiling is binding rather than DSCR, which is real information about the deal.

Then run the floor tests: for every DSCR row, report `PASS/BREACH` before and after and flag
any **floor state change**. A rebase that flips a Stage 1 floor has changed a verdict, and that
goes to Gabriel as a finding, not into a summary line.

Confirm `0 null cached values` across every touched workbook. If any appear, STEP 3 was done
wrong — fix the mechanism, do not paper over it by hand.

## STEP 6 — Cached-value audit (also runs standalone)

`scripts/cached_value_lint.py <root> [--quiet] [--json]` classifies every workbook. It opens each
one twice (formulas + cached values) with **`read_only=True`, which is load-bearing** — see the
v1.1 changelog entry for what happens without it.

| verdict | meaning |
|---|---|
| `OK` | formulas present, cached values present |
| `DEAD` | formulas present, **zero** cached — QC Gate reads nulls here |
| `PARTIAL` | some region never calculated |
| `NO-FORMULAS` | data-only sheet, nothing to cache |
| `UNREADABLE` | openpyxl could not open it — **unchecked, not clean** |

Exit 1 if anything is DEAD or PARTIAL. Remedy is Excel COM (or open-and-save), never an
openpyxl re-save — that is the cause, not the cure.

**`UNREADABLE` is not a pass.** Report the count every time. A sweep that says "no dead
workbooks" while 14 files failed to open has audited nothing about those 14.

## Done =

scope enumerated and split live-vs-historical, with the split REPORTED · every target cell
classified constant-vs-formula, dependents left alone · originals archived to
`_archive\<date>_<slug>\` and SHA256-verified before the first write · written via Excel COM
with `CalculateFullRebuild()`, never openpyxl · old value asserted per cell, surprises skipped
and reported · every touched model diffed against its archive, unmoved metrics reported
alongside moved ones · DSCR floor state reported before/after with any change flagged ·
`0 null cached values` confirmed · `UNREADABLE` count stated · an audit record written into the
archive folder naming authority, method, per-model deltas, and what was deliberately not done.

## Changelog

- v1.1 (2026-08-22, same day as v1.0 — shipped defect, found by running it): `cached_value_lint.py`
  loaded each workbook twice with openpyxl's **default full-object-tree mode**, holding both trees
  at once. Launched across the Business tree it reached **9.1 GB RSS** and exhausted the machine's
  paging file — an unrelated PowerShell call died with `0x800705AF, The paging file is too small`,
  and the process had to be killed by PID. Both loads now pass `read_only=True` and stream the two
  sheets in lockstep via `zip()`, with an explicit `gc.collect()` per file: measured peak **48 MB**,
  a ~190x reduction, flat regardless of workbook count. Also documented in STEP 4: `-ArgumentList`
  with an array splits ORA's space-containing roots, so the sweep silently walks the wrong tree and
  reports a confident tiny count — quote every path inside the argument string, and check the
  workbook count before believing any verdict. **The portfolio-wide sweep has still never completed**;
  the `125DouglasPike` DEAD finding stands alone and nothing else has been audited.
- v1.0 (2026-08-22): initial. Extracted from the refi-rate rebase (7.00% → 6.50%, 10 workbooks),
  which established every rule above the hard way: the openpyxl cached-value trap (caught before
  the write, not after), the constant-vs-formula pre-check (`125DouglasPike` Sensitivity!B9 is a
  dependent), the unmoved-metric finding (LTV binds, not DSCR), and `125DouglasPike` v2.0 sitting
  DEAD with null DSCRs that no QC run would have surfaced — which is what `cached_value_lint.py`
  now exists to catch.

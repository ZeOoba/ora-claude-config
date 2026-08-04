---
name: reference_onedrive_autosave_defeats_com_rollback
description: "On a OneDrive-hosted workbook, AutoSave commits COM writes immediately — Close($false) does NOT roll back a partial write, so there is no rollback to design for"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3a21fa0c-1eb5-4c06-b0c0-b5dce4253d70
  modified: 2026-08-04T00:31:52.919Z
---

The ORA Master Workbook is OneDrive-hosted, so Excel **AutoSave persists each COM write to disk as it happens**. A teardown of `$wb.Close($false)` therefore does **not** undo anything — it merely declines to add another explicit save on top of writes that already landed.

**Proven 2026-08-03.** A PowerShell script writing a multi-row accrual schedule threw partway through the loop (a COM binder quirk: `Cells.Item(r,c).Value2` rejects an `Int32`, binding to a String overload — use `Range("C$r").Value2` instead). The `finally` block ran `$wb.Close($false)` and reported `saved=False`. Reopening the file from disk showed the partial row still there: `A6` relabelled, `C6` left at 0. The rollback was an illusion.

This also **corrects the first version of SKILL note 1d(i)** (`ora-master-workbook-ingest`, committed `a9d03e0`, corrected same day in `a59821d`). That rule said a `$success` flag plus `Close($success)` prevents half-applied writes. It is necessary but not sufficient, and the incomplete version was the more dangerous one because it invited confidence in a protection that does not exist.

**How to apply, for any COM write to this workbook:**

- **Set `$wb.AutoSaveOn = $false` before any multi-cell edit** (wrap in `try` — the property throws on non-cloud workbooks).
- **Design for forward completion, not rollback.** If a write fails midway, finish it or explicitly repair it; do not assume closing without saving undoes anything. Read the on-disk state before deciding what repair is needed.
- **Keep the `$success` flag anyway.** It still prevents an explicit `Save()` of a known-bad state, which is a separate failure mode — that is how a genuinely half-applied multi-sheet change published an inflated Total Debt of $20,355,291 earlier the same day.
- **Back up to `Documents\Claude\_backups` first**, then diff formula-by-formula against the backup to establish ground truth; a workbook-wide error sweep (`UsedRange.SpecialCells(xlCellTypeFormulas, 16)` per sheet) catches collateral damage a targeted check misses.

Related: [[reference_onedrive_office_autosave_lock_no_owner_file]], [[00_system_of_record]].

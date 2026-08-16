---
name: reference-openpyxl-resave-breaks-exceljs-workbook-parse-2026-08-14
description: "An openpyxl re-save of the ORA Master Workbook writes absolute comment rel targets that crash exceljs, breaking EVERY snapshot task - not a transient file lock"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4a9393fa-b1d6-440e-9ad9-efe857f3717b
  modified: 2026-08-14T21:18:03.668Z
---

**2026-08-14, `ora-lease-snapshot-refresh` Exit 3.** `npx tsx scripts/lease-snapshot-drift-check.ts` died with:

```
TypeError: Cannot read properties of undefined (reading 'comments')
    at WorkSheetXform.reconcile (exceljs/lib/xlsx/xform/sheet/worksheet-xform.js:453)
    at async parseWorkbook (server/workbook/parse.ts:963)
```

**Root cause: the Master Workbook was last written by openpyxl 3.1.5, not Excel** (`docProps/app.xml` → `Microsoft Excel Compatible / Openpyxl 3.1.5`; `dc:creator` → `openpyxl`; `dcterms:modified` `2026-08-13T23:11:43Z` = 19:11 ET, matching file mtime).

openpyxl writes worksheet comment relationships with **absolute** targets and non-standard Ids:

```xml
<Relationship Type=".../comments"   Target="/xl/comments/comment1.xml"        Id="comments" />
<Relationship Type=".../vmlDrawing" Target="/xl/drawings/commentsDrawing1.vml" Id="anysvml" />
```

Excel writes them **relative** (`../comments/comment1.xml`, `rId1`). exceljs's `reconcile()` keys `options.comments` by the relative form, so the absolute lookup is `undefined` and `.comments` throws. On 08-14 this affected 26 rel entries across 13 sheets (1, 6, 14, 16, 17, 18, 19, 21, 22, 24, 26, 32, 34); **any one aborts the whole parse.**

**Do NOT misdiagnose this as a transient workbook lock or corruption.** Diagnostics that MISLEAD here:
- Zip integrity (`testzip`) is **clean**.
- All 13 `xl/comments/comment*.xml` parts are **present** — nothing is missing.
- No `~$` Excel lock file exists.
- A naive `../` → `xl/` rel-target normalization reports the parts "MISSING"; that label is an artifact of the check, not the defect. The parts exist; the *target style* is the defect.

**Blast radius is fleet-wide, not one task.** Every exceljs read of this workbook fails — including `ora-cc-snapshot-refresh`'s `npm run extract`. It does not self-heal; it recurs on every fire until the workbook is rewritten by Excel.

**Third consumer, different symptom string — the PUBLIC mirror (found 2026-08-14 10:45 ET).** The native "ORA Command Center - Mirror Deploy" hourly task also parses this workbook, via `npm run bake` (`scripts/bake-mirror.ts` → `server/workbook/parse.ts`). It had failed **9 consecutive hourly runs** since 2026-08-13 20:00:45 — the very next fire after the 19:11 openpyxl re-save — leaving brain.oxfordra.net ~15h stale. **Do not search for "Exit 3" or the raw TypeError here:** the deploy surfaces it only as `build:mirror failed (1)` (`lastTaskResult` 1, beacon `outcome=failed`), so the classifier verdict is `ALARM_SCRIPT_FAILED` and the exceljs message never reaches the alert. `tsc --noEmit` passes clean, which rules the `build` half out and points at `bake`. Confirm by parsing `$WORKBOOK_PATH` with exceljs directly. Mirror-side detail: [[reference-command-center-mirror-deploy-gap]].

**SECOND DEFECT, worse and silent — cached values stripped.** openpyxl does not evaluate formulas, so the re-save dropped the cached result of **14,711 of 14,715 formula cells** (only 4 survived). exceljs reads *cached* values, so had defect 1 not existed the parse would have "succeeded" and written **null for every computed figure** — rent, NOI, debt service, DSCR. The crash was protective. Any future "just normalize the rels and carry on" fix is therefore actively dangerous — it repairs the loud defect and unleashes the silent one.

**RESOLVED 2026-08-14 (Gabriel approved all 3 actions in-turn).**
1. **Workbook repaired.** Re-saved through Excel COM with `CalculateFullRebuild`. Rels back to relative (26 of 26), cached values 4 → 14,517, all 13 comment parts preserved. Broken copy preserved at `~/.claude/maintenance/_state/workbook-backups/Master_Workbook_PRE-EXCEL-RESAVE_openpyxl-broken_20260814.xlsx` (md5 `c4cc71d5…`) as the regression fixture. Snapshot regenerated: Exit 2, 138 leases, one real change (Hoodz of Delmarva 2026-09-30 → 2029-09-30); committed + pushed `6e7c5bd..75c039d`.
   - **Excel COM gotchas hit:** `Application.Calculation` cannot be set before a workbook is open (`0x800A03EC`); opening the file **on its OneDrive path failed** with "Cannot access" and `Sheets: 0` — repair a **local copy** and swap it back. A pre-existing `EXCEL.EXE` held **unsaved user work**, and Excel can host multiple Application objects in one process, so **never call `Quit()` without checking `Workbooks.Count` and whether you created the PID.**
2. **Writer identified — it is NOT a script.** It is the **`excel` MCP server** (`excel-mcp-server`, openpyxl 3.1.5), driven by a human-prompted interactive session (`ad99b71c-…jsonl`, 13 writes 23:07–23:11 UTC; last write 23:11:42.925Z vs file mtime 23:11:43Z). `excel_mcp/data.py:106` `load_workbook()` → `:130 wb.save(filepath)`. **Every mutating `mcp__excel__*` tool is a write path**, and `settings.json:94`'s blanket `mcp__excel__*` auto-approve means no prompt fires. The ban already existed in prose at `ora-master-workbook-ingest/SKILL.md:57` ("use Excel COM, never openpyxl") but is unreachable by an agent using an MCP tool. **Do not "fix the script" — there is none; the fix is access control.** **SUPERSEDED — enforcement is now LIVE (2026-08-14, Gabriel approved in-turn).** The staged `master-workbook-write-guard.py` (19 tests, still in session `4a9393fa`'s `scratchpad/pending-approval/`) was **NOT installed** and should not be — a second, narrower guard alongside the live one would only confuse. What shipped instead is `hooks/workbook-write-guard.py`, registered in `settings.json`, a strict superset: it covers the `mcp__excel__*` vector the staged copy covered **plus** the Bash `python -c "…openpyxl…save()"` vector that copy explicitly deferred as "a separate, larger change", plus native/DC file tools. 38 assertions; full 46-file hooks suite green; the sanctioned read path (`read_only=True`) and Excel COM both verified still working live.
   - An adversarial REFUTE pass found **3 real holes in the first draft, all of which the staged copy also has** — a path under an unlisted field name (`{"workbook": …}`), a nested path (`{"opts": {"filepath": …}}`), and a case-varied tool name. The staged copy's `offending_path()` scans a fixed `PATH_FIELDS` list at the top level with `startswith` and exact-basename equality; the shipped one scans every string at any depth, case-insensitively, under quote/caret normalization. All 3 are now regression tests.
   - **Detection half shipped too:** `maintenance/workbook-integrity-probe.py` (exit 0 clean / 1 CORRUPT / 2 could-not-evaluate), which covers the guard's honest ceiling — **value indirection**. That ceiling is not theoretical here: the armed `patch_workbook.py` noted below is exactly the uncatchable shape (`python patch_workbook.py` names neither a writer nor the workbook in the command text). Verified against a synthetic corrupt fixture: its CORRUPT verdict reproduces the exact exceljs failure string.
   - **`settings.json`'s blanket `mcp__excel__*` auto-approve is no longer the amplifier it was** — PreToolUse hooks run regardless of auto-approval, so the guard fires even with no prompt. Narrowing that allowlist is a separate call for Gabriel, not a prerequisite.
   - Doctrine loop closed: `ora-master-workbook-ingest/SKILL.md` §1c now points at both mechanisms, so the rule is no longer prose with nothing behind it.
3. **Detector shipped** — [PR #274](https://github.com/ZeOoba/oxford-command-center/pull/274): `server/workbook/openpyxl-integrity.ts` converts the opaque crash into a named refusal and refuses a cached-value-stripped workbook outright. Detector, deliberately not a normalizer, for the reason above. All 3 checks green (`gate`, `refute-required`, CodeRabbit); CodeRabbit filed **zero** inline comments.

**⚠️ Four measurement gotchas an adversarial REFUTE pass surfaced — all counter-intuitive, all verified against the two real files:**
- **`cell.result === undefined` does NOT mean "no cached value."** exceljs sets `model.result` under a *truthiness* test (`cell-xform.js:351`), so a formula caching the **empty string** (`=IF(B1="","",B1)`, an `<v/>` element) is indistinguishable from an uncached one. On the healthy workbook that is **517 of 17,318 cells (2.99%)** — only **12** are genuinely uncached. Never quote a "missing cached values" count as an exact uncached figure; it is an upper bound. This nearly shipped a guard that would hard-refuse the real workbook, and `server/brain.ts` would have swallowed the throw and still reported `status: 'fresh'`.
- **Defect 1 has more than one symptom.** The corrupt file carries **92** absolute rel targets (healthy: **0**), including **tables** (`/xl/tables/table1.xml`, sheets 10 and 13). Absolute *table* targets crash with `reading 'name'`, not `reading 'comments'` — comments merely reconcile first. Detect the CAUSE (scan the zip for `Target="/`), never the symptom string.
- **Formula counts differ by tool and both are "right":** openpyxl sees **14,715** (formula strings); exceljs sees **17,318** (13,886 master + 3,432 *shared* formulas, which openpyxl does not expand). Quote the tool with the count.
- **`data_only=True` + `save()` is a third, silent corruption** — formulas replaced by static values, `formulaCells` drops to 0, and any ratio-based check divides into a pass. Figures then freeze forever, which is worse than nulls because it looks alive.

**ALL THREE ACTIONS CLOSED 2026-08-14.** PR #274 **MERGED** (`864354f`); worktree and branch cleaned up.

**Armed `patch_workbook.py` ARCHIVED** (Gabriel instruction, in-turn) → `~/.claude/_archive/2026-08-14_armed-openpyxl-patch-workbook/` as `patch_workbook.py.ARCHIVED` (md5 `a684e288…`) with a README; original deleted from the scratchpad. It was never run with `--apply`. **⚠️ Its CONTENT is still live work, so do not read "archived" as "done":** it encodes the five debt-service edits Gabriel ruled on 2026-08-05, and item 1 (`Assumptions!B30` month-end constraint) is the still-open half of [[reference-els-eomonth-pair-fix-half-applied-2026-08-05]]. Re-do those via **Excel COM, never openpyxl**; the script's cell addresses, shape assertions, and before/after formulas remain a good spec.

**Staged `master-workbook-write-guard.py` was NOT installed — correctly.** Gabriel said "install the guard"; verification first showed `hooks/workbook-write-guard.py` had already shipped live (`settings.json:300-306`). A 13-case differential run gave **0 coverage gaps** — identical verdicts on all 9 block cases and all 4 allow cases — and the live guard additionally covers Bash, Write/Edit/MultiEdit/NotebookEdit, and DC file tools. It proved that live by **blocking the very Bash command written to test it** (the workbook name in shell text), the exact vector the staged copy deferred. Its own suite passes, incl. fail-open and never-exit-1. Installing the narrower copy alongside would have added zero protection and two hooks firing on the same calls. **Lesson: verify a "not yet done" memory claim before acting on it — another session had closed it in the interim.**

Instance of the risk behind the ratified master-workbook single-writer rule (`tech.md` §3d) — see [[project-master-workbook-single-writer-proposal-2026-07-25]] and [[project-master-workbook-no-single-writer-2026-07-24]].

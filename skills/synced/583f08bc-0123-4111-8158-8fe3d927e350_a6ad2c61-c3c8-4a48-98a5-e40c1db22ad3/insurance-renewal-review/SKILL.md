---
name: insurance-renewal-review
description: "Oxford Realty Advisors property insurance renewal review — extract carrier declarations (text-layer first, OCR only if needed), build a per-property premium history, decompose rate from exposure, diff each renewal against the prior term, reconcile trackers and named insureds against the declarations, and ship both an XLSX and an interactive HTML dashboard. Use when the user says: review insurance policies, insurance renewal review, how has insurance changed, premium history, shop our insurance, self-insure, insurance declarations, coverage changes, deductible options, insurance dashboard — or points at a folder of insurance PDFs/declarations. Also trigger when a folder holds scanned carrier declarations (Erie, Selective, Westchester/Chubb, Mesa, Hartford) and the user asks for trends, comparisons, or a renewal decision. v2.0 (2026-08-17: text-layer-first triage, dashboard deliverable, quoted-vs-realized check — see Changelog)."
---

# Insurance Renewal Review (ORA) — v2.0

Codifies the extraction/compare/flag pass built 2026-08-13 and materially extended 2026-08-17 (adding a 7th property, correcting two analytical errors, and reconciling three source workbooks against the declarations).

## Trigger phrases
"review insurance policies", "insurance renewal review", "how has insurance changed", "premium history", "shop our insurance", "should we self-insure", "insurance declarations", "coverage changes", "deductible options", "insurance dashboard" — or the user points at a folder of insurance PDFs/declarations and asks for trends, comparisons, or a renewal decision.

---

## Step 1 — Inventory and triage every file

- `find <folder> -type f` for a full inventory; one subfolder per property is the ORA convention.
- **`md5sum` every PDF up front.** Duplicate and renamed files are common (found: a byte-identical "#2" file misnamed as a second policy; a user uploading the same three files twice in one turn). Report duplicates explicitly — never silently treat them as two documents.
- **TEST FOR A TEXT LAYER BEFORE ASSUMING OCR.** This is the single highest-leverage step and v1.x got it wrong by assuming.

  ```
  pdfinfo file.pdf | head -6                 # Producer tells you a lot
  pdftotext -f 1 -l 1 file.pdf - | wc -c     # >500 bytes ⇒ real text layer
  ```

  Producer strings seen in this book:
  | Producer | Meaning |
  |---|---|
  | `Ricoh ... AFP2PDF` | **Native text** — Erie's own print system. `pdftotext -layout` works. Seconds, not minutes. |
  | `Aspose.Pdf` | Rasterized scan, no text layer. OCR required. |
  | `Microsoft: Print To PDF` | Rasterized scan. OCR required. Prohibited under ORA standards. |

  As of 2026-08-17, **1 of 38 PDFs** in the ORA folder is native text. That one file is the proof that the carrier *can* produce searchable declarations — cite it by name in the broker request (Step 11). Do not report "every PDF is a scan" without having run the check on every PDF.
- Check for `.msg` attachments — brokers forward missing endorsements this way. Extract with `extract-msg` (pip, `--break-system-packages`); list sender, date, subject, body, and every attachment; extract and read PDF attachments too. A `.msg` is often the ONLY place a mid-term amendment lives.
- **Full policy packets are mostly forms.** A 72-page "renewal" is typically 3 declaration pages plus a 68-page forms booklet. Locate the declaration pages first (they carry "Page N of M" and the policy number), then scan the remainder only for an amended dec, a premium change, or an "IMPORTANT NOTICE — SUMMARY OF CHANGES" form. Do not OCR 70 pages of boilerplate at full resolution.

## Step 2 — OCR ladder (only for image-only PDFs)

Full technical ladder (render dpi, tesseract vs. vision read, the mandatory ≥400 dpi re-render/confirm rule for dollar figures, and the 2-core/250-page timeout workaround): `references/ocr-and-extraction-checklist.md` § Step 2.

## Step 3 — Per-document extraction checklist

Full 10-item field checklist and carrier-specific gotchas: `references/ocr-and-extraction-checklist.md` § Step 3.

Additions since v1.1:
- **Record the property deductible AND the GL limit triplet for every term.** The deductible-for-limits trade (Step 7) is invisible unless both are captured every year.
- **A second premium line is not automatically an umbrella.** At 9620 State 350 the second line is a *standalone primary GL policy*, written because GL reads "Not Covered" under the property package. Putting it in an "Umbrella premium" column silently corrupts every umbrella-trend chart downstream. Check what the policy form actually is before assigning the column.
- **Note when a coverage line is absent entirely.** Two of seven ORA properties carry no excess layer at all. Absence is a finding; a blank cell is not.

## Step 4 — Build the premium history

- One row per property per policy year: package premium, umbrella premium, combined, YoY %, building limit/TIV, YoY TIV %, rate-per-$100-of-TIV (`=combined/TIV*100`), AOP deductible, basis note. **This decomposition is the whole point** — it separates genuine rate action from exposure growth. Inflation-guard-driven limit increases are NOT rate increases.
- **Report the like-for-like set separately from the portfolio total.** Only properties with a complete series across every year belong in the CAGR figures. Say which properties those are, in the chart subtitle, every time. A portfolio total that gains or loses a property between years is not a trend.
- Flag any YoY combined increase that outpaces the TIV increase by a wide margin — that is the push-back signal, not the raw dollar delta.
- Umbrella premiums moving independently of umbrella limits (limits flat, premium up double digits) is the highest-value anomaly to surface — it recurs across this book.
- **Compute book coverage: what fraction of total premium has declaration-level review?** The tracker will list entities whose declarations are not in the folder. Reviewing 6 of 12 entities is a 54%-reviewed book, and saying so is more honest than presenting the reviewed subset as "the portfolio."
- Build as an XLSX per the `xlsx` skill (ORA Style Guide colors, formulas not hardcoded results, `recalc.py` before shipping).

### openpyxl traps that cost a rebuild cycle (2026-08-17)

1. **`ws.cell(r, c, None)` is a no-op.** openpyxl only assigns when the value is not None. To clear a cell you must write `ws.cell(r, c).value = None`. Silently leaves stale formulas behind.
2. **`insert_rows()` does not shift merged ranges, and unmerging afterward destroys data.** The stale range now overlays whatever shifted into those rows; calling `unmerge_cells()` on it converts the non-anchor cells to empty. **Unmerge first, then insert, then re-merge at the shifted position:**
   ```python
   shift = [(m.min_row, m.min_col, m.max_row, m.max_col)
            for m in ws.merged_cells.ranges if m.min_row >= at_row]
   for m in list(ws.merged_cells.ranges):
       if m.min_row >= at_row: ws.unmerge_cells(str(m))
   ws.insert_rows(at_row, n)
   for r1, c1, r2, c2 in shift:
       ws.merge_cells(start_row=r1+n, start_column=c1, end_row=r2+n, end_column=c2)
   ```
3. **`insert_rows()` does not rewrite formula text.** Every relative formula below the insertion point still references its old row. After inserting, rebuild all per-row formulas from a row map rather than trusting the shift.
4. **Verify by recalculating, not by reading the formulas you just wrote.** `soffice --headless --convert-to xlsx` then read with `data_only=True` and assert the totals against an independent Python computation. A formula pointing at the wrong row produces a plausible number, not an error.

## Step 5 — Cross-check the umbrella's own paperwork

Every umbrella/BCL declaration carries a "Schedule of Underlying Insurance" listing the primary GL limits it sits above. **Check this against the actual current primary limits, not just the label.** Umbrellas are issued before the primary is finalized or amended mid-term, and the schedule can go stale by months while the premium still moves. Largest unresolved-cost item in this book: a 44% umbrella increase attaching above a primary the umbrella's own dec still showed as 5× lower than actual.

## Step 6 — Diff against the prior term

For every property, a change log: effective date, what changed, direction (Improvement / Reduction / Cost-only / Administrative / Exposure-added / Unresolved), premium impact if stated, and the specific source document. Never a general "the coverage changed."

Patterns worth naming when found:
- coinsurance → Agreed Value (real improvement, usually cheap);
- **a deductible increase traded for a liability-limit increase** — see Step 7, this is now a documented carrier pattern in this book, not a one-off;
- an inflation-guard line that stops printing (ambiguous — flag as "disappeared from the dec, unclear if actually removed"). Strengthen this when *other* properties in the same book visibly print their step-up: the silence becomes conspicuous rather than merely ambiguous;
- a location added then removed within one term (check the removal window for a coverage gap against whatever replaced it);
- an endorsement dropped from the Schedule of Forms between terms (e.g. EPP0222 wind/hail deductible) — a removal is as material as an addition and is only visible by diffing the form schedules.

**When bucketing changes for a chart, count distinct economic events, not log rows.** One event logged against two properties (e.g. a location removed from one policy and picked up by a tenant) is one event. State the row count and the event count separately.

## Step 7 — Deductible/retention options — READ THE HEADER FIRST

If a "Deductible Options" or similar quote tab exists in any tracker workbook, extract it verbatim into its own sheet and compute subtotals by line type using `SUMIFS`.

**Before computing anything, read the header row above the quote columns.** In this book it reads `Option 1 - GL limits $2m/4m` — meaning **every quoted tier is priced with general liability rebased to $2M/$4M**, not held at each policy's current limits. Consequences:

- For policies currently below that, the credit bundles a limits **upgrade** — the saving is real but is not a pure retention trade.
- For policies currently **above** it (this book had four labelled $5m/5m and $3m/3m), taking the credit could **cut** liability limits — at one property that would have unwound a $5M/$5M increase bought four months earlier.

Presenting the ladder without this header is the difference between a decision memo and a misleading one. **Get the assumed limits per policy per tier in writing before presenting any saving as achievable.**

Also check the quote tab for these, all of which occurred here:
- **duplicated rows** (one entity appeared twice, identically — a naive column sum double-counts it);
- **a subtotal that does not cover the whole sheet** (the only subtotal summed the first six entities; there was no book-wide total, so any "book" figure is a reconstruction — say so);
- **entity names and premiums that disagree with the companion tracker tab** (three different premiums for one policy-term across two workbooks).

Frame the output as a shop-vs-retain ladder with a breakeven (`annual saving ÷ additional retention per occurrence` = full-retention losses per year at which the saving is consumed). **Do not conclude "self-insure" or "don't"** — that call needs loss runs, which a declarations-only review never has. Say so explicitly as an open item.

## Step 8 — Quoted vs. realized: close the loop on last cycle's quotes

**New in v2.0, and the reason to keep this skill's outputs versioned.** When a prior cycle's deductible or limits quote has since *bound*, diff the quote against the issued declaration. This is the only way to learn whether the carrier's quoted credits are reliable.

Do it on a **like-for-like basis** or not at all:
- Match the **limits** assumed in the quote to the limits on the binder (see Step 7 — they are often not the same).
- Adjust for **exposure growth between quote and bind.** A quote struck against one term and bound a year later sits on a building limit that has stepped up 4–7%. Step the quoted premium by the TIV change before declaring a variance, and mark the adjustment `[computed]`.
- State the comparison base explicitly. Two different "current premium" figures for the same policy (a stale tracker figure and the issued figure) produce two different credits and one of them is wrong.

Worked example (2026-08-17): quoted $7,237 at a $25K deductible with GL rebased to $2M/$4M; bound a year later at $7,522 on exactly those terms with the building limit 5.02% higher. Stepping the quote by 5.02% implies ~$7,600 — the policy came in **under** the exposure-adjusted quote. **The carrier's quote held.** An earlier draft of this analysis compared the raw numbers, concluded the credit "came in 47% short," and attributed it to a bundled limits charge. That was wrong in both the arithmetic base and the causal claim. Match limits, adjust exposure, then compare.

## Step 9 — Reconcile the trackers AND the named-insured schedule

**9a — Premiums.** Renewal trackers are hand-maintained snapshots, not linked to declarations. Cross-check every premium against the declaration for that term. **The declaration wins.** Flag the row as corrected, cite the source, and never silently overwrite the tracker's history. Where multiple tracker workbooks exist, diff them against *each other* too — this book had three different premiums for one policy-term across two workbooks and two tabs. Where no declaration exists, leave the conflict **OPEN** rather than adjudicating by guess.

**9b — Named insureds, reconciled by LOCATION not by entity name.** The named-insured schedule is typically built *from* the tracker, so it inherits the tracker's entity names and cannot validate them. Reconcile against the **Location 1 address printed on each declaration**. Findings this surfaced:

- A policy issued to an entity **named for a different address entirely** (named insured "5242 Angola Road, LLC"; sole insured location 3034 Westerville Rd).
- **A name collision**: a second entity recorded as *formerly known as* that same name, both disregarded entities of the same parent with the same EIN — so neither the name nor the EIN disambiguates them.
- Legal-form conflicts (LLC vs. Inc across three documents for one property).
- Named insureds that differ **between the property and GL lines of the same asset**.
- Mailing addresses that are holdovers from a prior asset.
- **An owned entity in the schedule with no policy on any tracker line** — a potentially uninsured asset, and the highest-consequence item the reconciliation can produce. Always check the entity register *against* the insurance book in both directions; the missing row is the one that matters.

A named insured that does not match the titleholder is a coverage-denial argument at claim time. Rank these accordingly in Step 10.

## Step 10 — Rank data gaps by dollar consequence, not document order

Ranked punch list: missing base renewal declarations, missing SOVs, missing loss runs, missing mortgagee/loss-payee schedules where debt is known or suspected, entity-name conflicts, uninsured or unreviewed assets, and named-insured mailing-address drift. Rank by what it costs if wrong — a missing mortgagee on debt-encumbered collateral outranks a missing square-footage field, and a possibly-uninsured asset outranks everything.

## Step 11 — Deliverables

Standard output set for a full review — **both artifacts, every cycle**:

1. **Premium-history XLSX** — Summary, Coverage Changes, Deductible Options, Data Gaps & Actions, Source Index tabs. Session-output naming (`YYYY-MM-DD_Topic_DocType_v##.xlsx`) in the project's `/outputs/`. Master workbook updated in place; prior version copied to `/outputs/archive/` first (never deleted).
2. **Interactive HTML dashboard** — self-contained single file, delivered with `SendUserFile` and persisted with `create_artifact` so it survives the session and can be updated in place next cycle. Read the `dataviz` skill before writing any chart code. What this book needs, in order:
   - hero KPI tiles (all-in spend, like-for-like rate change, worst-priced asset, retention already taken, % of book unreviewed, open-item count);
   - **rate per $100 TIV by property, latest bound term**, with the book-blended rate as a reference line — the chart that makes a $1.4M and a $12.7M building comparable;
   - **indexed premium vs. TIV vs. rate** for the like-for-like set — the chart that proves rate from exposure;
   - **small multiples** for per-property premium history. Past ~5 properties a single multi-series line chart fails: with 7 series the categorical palette runs into reserved status colors, and the label stack collides. Facet instead, one panel per property on a shared vertical scale;
   - concentration (premium share vs. value share), umbrella YoY (diverging), the retention ladder, and coverage-change polarity.
   - Palette: validate with `dataviz`'s `scripts/validate_palette.js` in **both** light and dark against the actual surface colors. ORA navy/gold fail the chroma and lightness gates as *data* colors — keep them as chrome (masthead, rules, tile accents) and use the validated categorical palette for marks. Never assign a series the status red/amber/green.
3. **Rebuilt tracker XLSX** with a Conflicts Log tab and a Named Insured Audit tab (Step 9), as a NEW file — do not overwrite a user file in a non-Claude OneDrive business folder without permission.
4. **Draft-only broker data requests, one per broker.** Never send without explicit in-turn confirmation, regardless of how routine. Lead with the time-sensitive items (an anniversary inside 90 days; an unauthorized coverage change). Include: native-text PDFs going forward (name the one native file as proof it is possible), SOVs, 5-year loss runs, underwriting applications, missing base declarations, declarations for every unreviewed entity, the Step 7 limits question, and every re-rate question from Steps 5–6. If a prior draft exists, supersede it explicitly and say which items are carried forward.
5. **Housekeeping** — byte-identical duplicates move to a same-folder `/archive/` (never delete); ask permission first.
6. **Scheduled reconciliation.** If a renewal/lapse monitor exists, update rather than duplicate it. Check `list_scheduled_tasks` / `list_triggers` and the concurrent-writer check first, per `register-scheduled-task`. If the canonical registration MCP is not reachable on the current surface, **ask** which path to use rather than improvising — registering into the wrong fleet is silent.

## QC before presenting

- Every dollar figure traceable to a specific source document and, where it mattered, a ≥400 dpi re-render.
- **Independent recomputation of every derived figure**, not a re-read of the formula. Run an adversarial verification pass (subagent) against the source workbook before shipping: it caught a mislabelled premium column, an understated document count, a wrong band floor, and a self-contradicting open item in the 2026-08-17 cycle.
- No fabricated SF/construction/BPP/business-income figures where the dec format doesn't carry them — say "NOT SHOWN — format limitation."
- XLSX passes `recalc.py` / headless recalc with zero errors.
- Scope of any tracker correction stated explicitly: which properties were verified this pass vs. carried over unverified, and what fraction of the book that represents.
- Every CAGR and index states its member set.
- Screenshot the dashboard in light **and** dark and look at it before shipping — the palette validator checks color, not layout.

## Changelog

- **v2.0 (2026-08-17):** Text-layer test promoted to Step 1 with a producer-string table (assuming OCR wasted a full render pass on a natively-searchable file). Step 7 rewritten around the `Option 1 - GL limits $2m/4m` header trap plus duplicate-row / partial-subtotal / cross-workbook-disagreement checks. New Step 8 (quoted vs. realized, like-for-like) documenting a corrected analytical error. Step 9 split into premium reconciliation and named-insured-by-location reconciliation, with the uninsured-asset check. Step 11 makes the HTML dashboard a standard deliverable and specifies its chart set, the small-multiples threshold, and the palette rule. Added openpyxl traps to Step 4 and an adversarial-verification requirement to QC. Book-coverage metric added to Step 4.
- v1.1 (2026-08-15): size refactor — Steps 2–3 moved verbatim to `references/ocr-and-extraction-checklist.md`. Fixed a duplicate stacked YAML frontmatter block from v1.0.
- v1.0 (2026-08-13): initial. Built from the Insurance Policies Historical + Current portfolio review.

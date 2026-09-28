---
name: acquisition-proposal-generation
description: Generate or revise Oxford Realty Advisors' seller-facing Acquisition Proposal — a two-page, non-legalistic business-terms offer document positioned as an alternative to a traditional LOI. Trigger on: acquisition proposal, offer document, business-terms offer, proposal to purchase, "not a legalistic LOI", make an offer, template offer letter, proposal template. Distinct from loi-generation (the formal conditional-block LOI with QC gate and state overlays) — use THIS skill when the deal calls for a short, principal-to-principal offer that pushes legal detail into the PSA rather than the offer document itself. v3.2 (2026-08-22: walk-price QC gate added — Purchase Price must clear the ORA walk price before the document is produced. Prior: v3.1 named-constant/QC-caveat cleanup, v3.0 final production revision — see git history for detail)
---

# Acquisition Proposal Generation

## What this produces

**Oxford Realty Advisors — Acquisition Proposal Template FINAL.docx** — exactly two pages, fully editable, `docx` (Node). Regenerate:

```
node scripts/build.js
```

Move the output to `/mnt/user-data/outputs`, deliver via `SendUserFile`. After any edit, re-render and inspect both pages (`soffice.py --headless --convert-to pdf`, then `pdftoppm`). Also verify the XML directly — LibreOffice substitutes a fallback for Aptos and can mislead on weight/spacing:

```
unzip -o file.docx -d x
grep -oE 'w:ascii="[^"]*"' x/word/document.xml x/word/styles.xml | grep -v Aptos   # must be empty
grep -o B59A5A x/word/document.xml | wc -l                                          # must read 2
pdfinfo file.pdf | grep Pages                                                       # must read 2
```

## Core concept — do not deviate

Not an LOI. A one-page-per-side statement of business terms: *here's the offer, if the economics work, let's document it with lawyers.* Intentionally simple, not incomplete. Full conditional blocks / state overlays / QC-gated legal instrument → `loi-generation`, not this skill.

## Page setup

US Letter, portrait. Margins: top 0.60", bottom 0.60", left/right 0.70". Header/footer distance 0.30" each. Never a third page — shorten copy before shrinking type below 8.5pt for substantive text (footer/captions may run to 7.5pt).

## Structure (fixed)

**Page 1:** Oxford Realty Advisors → Acquisition Proposal → Property/Date → PROPOSED TERMS (one seamless 3×2 sheet: Purchase Price | Deposit / Study Period | Closing / Financing | Proposal Valid Through) → Buyer (slim bar, single top hairline, reads as a continuation of the grid) → Definitive Agreement → Non-Binding (subtle panel) → contact block.

**Page 2:** About Oxford (2–3 sentences, positive framing only) → Why Sellers Work With Oxford (**5** items, 2-col × 3-row with one empty cell) → Our Portfolio (4 stats on one continuous light-gray band) → portfolio visual placeholder (~28% of content height) → Our Approach (2–3 sentences).

**Study Period is a grid line only — `[__] days` — never a standalone section with diligence categories (financial/physical/environmental/title/survey/zoning/lease).** That belongs in the PSA. This was removed deliberately in v3.0; do not reintroduce it even if a future revision asks to "add more detail" to Study Period — push back and confirm before doing so, since it directly contradicts the document's founding premise (business terms now, PSA later).

**No execution/signature page — deliberate, do not add one.** Confirmed explicitly with Gabriel (2026-08-18). The document's Non-Binding section states verbatim that "neither party will be bound unless and until a definitive Purchase and Sale Agreement is executed by both parties" — a signature block would contradict that on the same page and invites the seller's counsel to redline the proposal like a contract instead of just reacting to the economics. This is a structural analog to the "no diligence detail" rule above: both exist to keep this document a discussion draft, not a pseudo-LOI. Contrast with `loi-generation`'s output, which DOES carry an execution page because the LOI itself is a semi-binding instrument (exclusivity/confidentiality/binding provisions) — that's a different document type with a different job.

## Terms grid — one connected sheet, not six cards

Single continuous `LIGHTGRAY` (`#F3F5F7`) fill across all cells. No vertical divider, no white/colored gutter between columns — column separation comes from internal cell padding alone (`gridCell()`'s `left`/non-`left` margin split). Only a hairline (`BORDERGRAY #D9DEE5`, weight 3) between *rows* — implemented via `rowSeparatorBorders()`. Purchase Price gets ~20–25% more visual weight through size (17pt vs 10pt) and slightly larger padding, plus the one gold left-edge accent — not a separate hero box. Buyer sits below as its own bar with a single top hairline (no bottom border), so it reads as a continuation of the same summary, not a seventh card.

## Typography — Aptos only, real Word styles

Single font, **"Aptos"**, everywhere (`grep` check above). OOXML has no true SemiBold — spec "SemiBold" is approximated as `bold: true`; the distinction from full "Bold" elements comes from size/color, not weight. This is a standing, documented limitation, not a bug to chase.

| Style id | Size | Weight | Color |
|---|---|---|---|
| OxfordCompanyName | 17pt | Bold | Navy `#17243A` |
| ProposalTitle | 13.5pt | Bold* | Navy |
| PropertyAddress | 15pt | Bold* | Black `#111111` |
| SectionHeading | 10.5pt | Bold | Navy |
| TermLabel | 9pt | Bold* | Slate `#526174` |
| TermValue | 10pt | Bold* | Black (Navy for Financing) |
| PrimaryTermValue | 17pt | Bold | Navy |
| Body | 9pt | Regular | Black |
| SmallBody | 8.5pt | Regular | Black |
| Caption | 7.5pt | Regular | Slate |
| Footer | 7.5pt | Regular | Slate |

## Color system — closed palette, hard cap on gold

Navy `#17243A`, Slate `#526174`, Body Black `#111111`, Light Gray `#F3F5F7`, Oxford Gold `#B59A5A`, white. `#D9DEE5` (Border Gray) is retained as a *structural utility tone* for hairlines only (row separators, panel borders, footer rule, stat dividers) — it is not one of the six meaning-bearing palette colors and should never carry information on its own. **Gold is capped at 2 elements, verified by grep**: the Page 2 subtitle rule and the Purchase Price left-edge accent. Do not add a third.

## Content rules that came from direct correction — do not silently revert

- About Oxford: positive framing only. Never "not an intermediary," "not a fund raising capital deal-by-deal," or any other define-by-negation phrasing.
- Why Sellers: exactly 5 points (Private Capital, Certainty of Execution, Direct Decision-Making, Long-Term Ownership, Flexible Underwriting). No "without committee delay" or any language that reads as comparing Oxford against institutional buyers — confident, not comparative.
- Our Approach: full version restored — "buildings that work for tenants day to day... hands-on property management, and targeted capital improvements." A shorter variant was tried and reverted; use the full text.
- Portfolio visual: **real photos are now in place**, not a placeholder box. Three representative properties (`scripts/photos/1100_rarig.jpg`, `9050_redbranch.jpg`, `55_newplant.jpg` — 1100 Rarig Ave, Columbus OH / 9050 Red Branch Road, Columbia MD / 55 New Plant Ct, Owings Mills MD) sit in a 3-column row, each center-cropped to 3:2 and captioned with **city/state only** (not full street address — a deliberate discretion choice; ask Gabriel before printing full addresses on a document that circulates to third parties). If the placeholder box is ever needed again (e.g. a market where Oxford has no photographed assets yet), fall back to `[Oxford Portfolio Map / Representative Properties]` — natural sentence case, no "INSERT," no all-caps; an all-caps bracketed instruction reads as a note to whoever built the document, not a finished design element.
- **Tenant signage in property photos must be removed before use.** The Owings Mills photo originally showed a tenant's logo/name on the building facade — pasted over with a color-matched solid patch (see `build.js`'s signage-patch block) sampled from adjacent clean wall, not just blurred (a soft Gaussian blur alone left the text partially legible). Screen every future property photo for visible tenant signage, vehicle branding, or other tenant-identifying detail before it goes into a seller-facing document — this falls under the standing "never disclose confidential tenant information" rule, not just an aesthetic preference.
- Property/Date block: stacked, left-aligned, no table, no separate "DATE" caption label. Three short paragraphs — `[Property Address]` / `[City, State ZIP]` / `[Date]` (the date in Slate, smaller, unbolded) — not a two-column layout with the date floating at the right margin. A right-floating date label reads like a form field; a stacked address block reads like a letterhead.
- Why Sellers Work With Oxford: 5 items in a 2×3 grid leaves one empty cell — that's fine. Do not add a 6th point to fill it, and do not shrink row spacing to compensate. Give the 5 items more vertical margin instead (see `whyCell()` — top/bottom cell margins were deliberately increased for this reason) so the extra space reads as intentional breathing room, not as a document straining to look full.

## Seller-facing disclosure filter — hard rule

Never state: exact cash/liquidity, portfolio or target LTV, financing capacity, internal return hurdles or target yield-on-cost, target acquisition discount, maximum purchase price, internal underwriting assumptions, debt maturities/loan terms, tax or cost-segregation strategy, IC process detail, property-level financials on existing Oxford assets, portfolio value/debt/NOI/acquisition volume/investor capital, or the firm's full acquisition criteria. Portfolio scale statistics are fine as approximate figures — verify against the live ORA Master Workbook before reuse.

Current confirmed portfolio figures (per Gabriel, 2026-08-18, markets corrected same day from an earlier 7): **500K+ SF / 140+ Tenants / 26 Properties / 3 Markets**. Do not alter without an explicit new instruction — an example in a future prompt using different illustrative numbers is not automatically a correction; ask if genuinely ambiguous. Note this skill was briefly wrong about market count (carried "7" from an early draft before Gabriel corrected it to 3) — a reminder that firm-level stats in this file should be treated as "last confirmed," not "permanently verified."

Property count is explicitly **26, not 27** — the uploaded 3700 Kinsman LOI's own Buyer Information exhibit stated 27; Gabriel confirmed 26 is correct directly in chat (2026-08-18) and the discrepancy is logged to the Notion Knowledge Base so a future session doesn't re-surface it as ambiguous. If a future source document states a different count than this file, flag it — don't silently defer to the document over Gabriel's direct correction.

## Excluded content — never add

Signature blocks, confidentiality/exclusivity/access provisions, title/survey/environmental/casualty/condemnation detail, reps and warranties, closing mechanics, prorations, indemnification, default remedies, assignment, governing law, attorney's fees, brokerage sections, financing provisions beyond the all-cash statement, detailed diligence provisions.

## Contact / identity constants

Gabriel Goldberg, **VP, Acquisitions** — Oxford Realty Advisors. `301.512.6125 | ggoldberg@oxfordra.net | oxfordra.net`. Filled in directly (firm-level constants, not placeholders). If a future session finds a conflicting title elsewhere in standing instructions, flag it — don't silently pick one.

## File naming

Current production filename: **Oxford Realty Advisors — Acquisition Proposal Template FINAL.docx** — the "FINAL" suffix was Gabriel's explicit instruction for this revision, not this skill's standing convention. If a further revision cycle begins, ask whether to keep "FINAL," version it (`v2`, `v3`), or drop the suffix — don't assume.

**Deal-specific instances — fork, don't overwrite.** A real deal (e.g. 3700 Kinsman Blvd) is generated by copying `build.js` to a deal-named script (`build-3700-kinsman.js`), editing only the property/date/terms values, and outputting to a deal-named file — never by writing live deal data into the reusable template's own script or output file. As of this revision there are two scripts (`build.js`, `build-3700-kinsman.js`) that are ~95% identical. **Do not build a `build-deal.js --address --price ...` CLI wrapper yet** — one real deal-specific instance is not enough evidence the fork-per-deal pattern is the recurring shape (vs. a one-off). Revisit once a second real deal-specific instance exists: if the same full-file duplication happens again, that's the trigger to extract the shared template logic into a module and build the CLI wrapper. Track this as an open systematization candidate, not a standing requirement.

## QC before delivering

Exactly 2 pages. Aptos-only confirmed via grep. Gold count = 2 via grep. Study Period is grid-only (no diligence paragraph). Why Sellers has exactly 5 items. No prohibited financial/strategic disclosure. Non-Binding and Definitive Agreement language present verbatim. Text is real and editable — confirm with `pandoc -t plain`.

- **Purchase Price ≤ ORA Walk Price (v3.2).** Pull the walk price from `acquisition-underwriting`; if none exists, run it before producing the proposal. If the proposed price exceeds the walk price, **do not produce the document** — report the gap and the binding floor instead. A proposal is a real offer with a real expiry that a seller can accept; the fact that it is shorter and less legalistic than an LOI does not lower the pricing discipline behind it. Note the asymmetry deliberately: this document's whole design premise is that legal detail defers to the PSA — **price discipline does not defer to anything.** Incident: the 3700 Kinsman Blvd proposal went out 2026-08-18 at $3,800,000, four days before any floor test existed against it (Walk $2,661,000, surfaced 2026-08-22 by a separately-requested FULL underwrite).

**Font substitution risk is silent — do not trust the LibreOffice preview render for font-weight or spacing judgment.** This environment has no Aptos installed, so every `soffice`/`pdftoppm` preview substitutes a fallback font. It is fine for checking layout, page count, color, and copy — it is not evidence of the actual typeface or its true character spacing/weight rendering. The only reliable checks are the `grep -oE 'w:ascii="[^"]*"'` pass against the raw XML (confirms the document *specifies* Aptos) and opening the file in real Word on a machine that has Aptos installed (confirms how it actually renders). Do not describe a preview screenshot as confirming "Aptos looks correct."

## Grid-cell spacing constants

Why Sellers cell padding lives in one named constant, `WHY_CELL_MARGINS` (twips; 1px @96dpi ≈ 15 twips), defined once near the page-geometry constants at the top of `build.js` and referenced by `whyCell()`. A future "a little more/less space" request is a one-line edit to that constant — do not hand-edit the inline `margins: {...}` object in `whyCell()` directly, and do not let `build.js` and any deal-specific fork (e.g. `build-3700-kinsman.js`) drift out of sync on this value.

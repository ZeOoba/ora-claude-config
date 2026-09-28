# Insurance Renewal Review — OCR Ladder & Extraction Checklist

Packaged with the skill (unlike `versions/`, which stays repo-only). Referenced from
`SKILL.md` Steps 2 and 3 — moved here verbatim 2026-08-15 as a size refactor, same
pattern as `register-scheduled-task`/`daily-brief`. No procedural change from the v1.0
content; only the location moved.

## Step 2 — OCR ladder (for scanned/image-only PDFs)

1. `pdftoppm -r 200 -png` to render pages (150–200 dpi is enough for triage; re-render the specific page at 400–600 dpi to confirm any dollar figure before reporting it — OCR misreads digits more than any other content class).
2. `tesseract page.png stdout --psm 6` for a first-pass read, OR use the Read tool directly on the rendered PNG (vision) — vision reading is more reliable for declarations pages with dense tabular layouts than tesseract alone. Cross-check the two when a figure matters.
3. **Every dollar figure that goes into a deliverable must be re-rendered at ≥400 dpi and visually confirmed** — this is not optional. State the confidence explicitly if a digit is genuinely ambiguous; never guess.
4. Two cores and ~250 pages of scans will time out a single serial render/OCR pass (observed: `pdftoppm` across a full folder exceeded a 120s tool timeout). Either background the render (`nohup ... &`, poll for completion) or split the work across parallel subagents by property folder — one agent per property folder is the natural split and lets 4–5 folders OCR concurrently instead of serially.

## Step 3 — Per-document extraction checklist

For every distinct policy document (package/property, umbrella/BCL, and any standalone GL/inland-marine), extract verbatim:

1. Named insured(s) and mailing address
2. Carrier / underwriting entity (note: Erie writes package business under **Erie Insurance Company** and umbrella business under a differently-named **Erie Insurance Exchange** — these are different underwriting entities on the same account; don't conflate them) and the agency/broker
3. Policy number and exact policy period
4. **Total premium** (the single most important field) — plus any per-line breakdown and the TRIA/terrorism charge if separately disclosed (Erie discloses this only as a token $2–$4 line on the TRIA disclosure form, IL985F/H — check that form specifically, it is not on the main declarations page)
5. Property coverage: building limit (or blanket limit across a location schedule), BPP, business income/rental value basis (Actual Loss Sustained is Erie's default, with a period-of-indemnity but usually no dollar cap — note this explicitly since it reads like a gap but is standard for this carrier), valuation basis (RC/ACV/Agreed Value), coinsurance %, inflation guard / automatic adjustment %
6. Deductibles (AOP, wind/hail — Erie commonly just says "Property deductible," meaning no separate wind number exists — say so rather than reporting "NOT SHOWN" as if it were an omission; named storm)
7. GL limits (each occurrence, aggregate, products/completed ops, personal & advertising injury, damage-to-premises-rented/fire legal, medical)
8. Umbrella/excess limits, premium, and its own schedule of underlying insurance (cross-check this against the actual primary limits — see Step 5)
9. Location/building schedule: every address, year built, class code, square footage/construction/sprinkler status IF the dec format carries it (Erie's blanket format usually does NOT print per-building SF/construction/sprinkler — say "NOT SHOWN — format limitation," not "gap," when that's structurally true of every year)
10. Endorsements, exclusions (esp. new ones — PFAS/CG4032, nuclear/CU2123, cyber/CAT203, abuse-molestation/CAT149 recur across the Erie book), loss payees/mortgagees/additional insureds

If a figure is illegible or absent: say "NOT LEGIBLE" or "NOT SHOWN" — never guess, never fabricate, never silently carry forward a prior year's number.

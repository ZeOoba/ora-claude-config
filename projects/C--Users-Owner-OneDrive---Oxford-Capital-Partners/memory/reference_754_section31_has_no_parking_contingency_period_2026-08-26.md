---
name: reference-754-section31-no-parking-contingency-period
description: 754 Old State Route 74 executed PSA has no "§31 Parking Contingency Period" — §31 is "Parking Modifications"; the governing dates are Sept 9 and Oct 9, 2026
metadata:
  type: reference
---

The 754 Old State Route 74 executed PSA (`PSA -- 754 Old State Rd Clean Executed 08-11-2026.pdf`) contains **no "§31 Parking Contingency Period."** §31 is titled **"Parking Modifications"** and creates only (a) a Purchaser obligation to file a Union Township PD Minor Amendment application "within 30 days of the Effective Date," and (b) a mutual covenant to amend the 1996 (O.R. Bk 848/Pg 715) and 2000 (O.R. Bk 1282/Pg 1835) easement agreements to grant the Exhibit D exclusive parking rights. No start date, no end date, no termination right.

The only period in the instrument is the **§4.1 Feasibility Period** — expiry tied to Union Township's approval or denial of the PD modification +30 days, capped at 60 days after the Effective Date. Fact Table P-046 and P-126 (both flagged Ambiguous) say the same.

**The two dates that actually govern**, keyed to the **August 10, 2026** Effective Date certified on the signature page:
- **September 9, 2026** — PD Minor Amendment filing deadline (P-044). The single most date-critical obligation in this PSA; missing it jeopardizes the entire Feasibility Period mechanism.
- **October 9, 2026** — Feasibility Period hard outer limit (P-045).

**Why this matters beyond the deal:** the 2026-08-12 `psa-reconciliation` DISPUTED banner on the Notion pipeline row affirmatively listed "new §31 Parking Contingency Period" as *corroborated*, alongside the correctly-corroborated §4.1 trigger. A remediation banner carried a drifted assertion forward for two weeks. Caught 2026-08-26 by `ora-psa-drift-watch`; a seventh DISPUTED banner was appended. **A prior banner's corroboration list is not itself verified — re-read the instrument.**

**Two method notes from the same run:**
1. The signature page carries signatures as raster images, so the PDF text layer renders the execution block blank and the Effective Date empty. A text-layer-only read falsely reports an unexecuted instrument. Render the page (PyMuPDF, ~170 dpi) and read it visually. Doing so also resolved the "Aug 10 vs Aug 11" question: the certification reads **August 10, 2026**; the opening recital reads "made this 11th day of August 2026" — a genuine internal conflict in the document (P-040), not a narrative error.
2. The Canonical Fact Table `20260812_754OldStateRoute74_PSA-Facts_v01.xlsx` is in the **deal-folder root**, not `/outputs/`. The Notion Next Action still points at `/outputs/` — only the four 20260812 cascade-instruction `.md` files live there.

Related: [[reference_metrics_history_pattern_does_not_exist_2026-08-17]]

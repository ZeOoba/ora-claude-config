# Extraction Edge Cases — Lease Abstraction Pipeline

Reference for handling non-standard document structures.

---

## Multi-Document Leases (Original + Amendments)

When a lease folder contains both an original lease and one or more amendments:

1. Identify the original lease first (earliest date, highest page count typically)
2. Process the original lease to establish the base 30-field dataset
3. For each amendment, extract only the fields that are **modified** — do not re-extract unchanged fields
4. In the XLSX, note in a "Document History" column: `Original (MM/DD/YYYY) + Amendment 1 (MM/DD/YYYY) + Amendment 2 (MM/DD/YYYY)`
5. For any field modified by amendment, note: `[Value] — per Amendment [N] dated [date]; original: [original value]`
6. Flag: 🔵 INFO — Multi-document lease — verify amendment chain is complete

---

## Side Letters and Letter Agreements

Side letters often contain economically significant modifications not referenced in the lease body (e.g., informal rent abatements, undisclosed tenant allowances, verbal agreements reduced to writing).

1. Process side letters as supplemental to the main lease
2. Identify which fields they modify
3. Apply the same conflict rule: extract both values, note source of each
4. Flag: 🟡 WARNING — Side letter detected — verify all terms are captured

---

## Missing Exhibits

When a lease references an exhibit (e.g., "Exhibit B — Rent Schedule") but the exhibit is not included in the document:

1. Mark the dependent field as `⚠️ EXHIBIT NOT FOUND — [Exhibit name] missing from file`
2. Do not estimate or assume the exhibit's contents
3. Flag: 🔴 CRITICAL — Missing exhibit — manual retrieval required
4. Note in Tab 6 (Skipped Files) that the exhibit was referenced but absent

---

## Ground Leases

Ground leases have inverted economics (tenant pays ground rent to landlord who owns land; tenant owns improvements). Key differences:

- Field 18 (Lease Type): Mark as "Ground Lease"
- Field 14 (Base rent schedule): Extract ground rent schedule — this is what ORA receives, not pays
- Field 11 (Extension options): Ground lease options are typically very long (25–99 years); extract as-is
- Field 30 (Condemnation/casualty): Ground lease condemnation provisions are more complex — extract exact language
- Derived metrics: NPV calculation still applies; flag as "Ground Lease — verify discount rate applicability"

---

## Master Lease Structures

When ORA is master tenant (leases entire property from a third party, then subleases to occupants):

- Field 1 (Landlord): The fee owner
- Field 2 (Tenant/Master Tenant): ORA entity
- Subleases: Process separately as individual tenant records
- Flag: 🔵 INFO — Master lease structure — ensure both master lease and subleases are in the batch

---

## Leases with No Expiration Date (Month-to-Month)

- Field 9 (Expiration): Mark as `MONTH-TO-MONTH`
- Field 10 (Total term): Mark as `MONTH-TO-MONTH — no fixed term`
- Derived metrics: Skip NPV and CAGR calculations; note N/A
- Flag: 🟡 WARNING — Month-to-month tenancy — no term certainty; recommend conversion to fixed term
- Months until expiration: Mark as `0 — at-will`; include in expiration heatmap under "Current Quarter"

---

## Leases in Non-English Languages

- Flag: 🔴 CRITICAL — Non-English document detected — human translation required before abstraction
- Do not attempt extraction. Log in Tab 6 with reason: "Non-English — translation required"

---

## Redlined / Draft Leases

If the document appears to be a draft or redline (tracked changes visible, "DRAFT" watermark, version numbering in filename):

- Flag: 🟡 WARNING — Draft or redlined document detected — verify this is the executed version
- Extract from the clean (accepted) text only, not proposed changes
- Note in the "Document History" column: `Draft — [version if stated] — verify executed lease`

---

## Extremely Short Documents (< 3 pages)

Short documents may be lease abstracts, summaries, or certificates of occupancy rather than executed leases.

- If < 3 pages and appears to be a summary rather than a lease: log in Tab 6 as "Not a lease — appears to be summary document"
- If < 3 pages and appears to be an executed lease (e.g., simple month-to-month agreement): process normally but flag: 🔵 INFO — Short-form lease — verify completeness

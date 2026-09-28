# PSA Fact Schema — Canonical 12-Section Structure

This is the authoritative schema for Oxford Realty Advisors' PSA Fact Table. Every PSA Reconciliation produces a workbook whose rows follow the identifiers, sections, and field names below. Do not rename fields. Add new fields only at the end of a section and assign the next Fact # in sequence.

Numbering convention: `P-###` for Fact IDs, zero-padded to 3 digits, monotonically increasing. Deleted facts are tombstoned (row retained, Value = "DEPRECATED", Note = reason) — never re-used.

## Data types

- **Text**: free-form UTF-8. Always stored in Excel as text even if numeric-looking (e.g., parcel IDs, instrument numbers).
- **Number**: stored as native Excel number; apply currency / SF / acreage / per-SF format per the field.
- **Date**: stored as Excel date serial; format `mm/dd/yyyy`.
- **Boolean**: `Yes` / `No` / `N/A` — always text, never TRUE/FALSE.
- **Enum**: one value from an explicit set — never a paraphrase.

---

## SECTION 1 — PARTIES (P-001 to P-015)

| Fact # | Field | Type | Typical PSA Source | Example (E Fulton) |
|---|---|---|---|---|
| P-001 | Purchaser — Contracting Entity | Text | Preamble | Oxford Capital Partners, LLC |
| P-002 | Purchaser — Trading Name / Notice Name | Text | §17 (Notice) | Oxford Realty Advisors, LLC |
| P-003 | Purchaser — Address (Notice) | Text | §17 | 9510 Persimmon Tree Road, Suite 200, Potomac, MD 20854 |
| P-004 | Purchaser — Principal / Attn | Text | §17 | Eric Goldberg, President |
| P-005 | Purchaser — Principal Email | Text | §17 | egoldberg@oxfordra.net |
| P-006 | Purchaser — Secondary Contact | Text | §17 (cc line) | Gabriel Goldberg — ggoldberg@oxfordra.net |
| P-007 | Buyer's Counsel — Firm | Text | §17 (with a copy to) | Protas, Spivok & Collins, LLC |
| P-008 | Buyer's Counsel — Attorney | Text | §17 | Philip J. Collins, Esq. |
| P-009 | Buyer's Counsel — Email | Text | §17 | pcollins@psclaw.net |
| P-010 | Seller — Entity | Text | Preamble | SIJ Partnership, LLC (Ohio LLC) |
| P-011 | Seller — Address (Notice) | Text | §17 | 3540 E. Fulton Street, Columbus, OH 43227 |
| P-012 | Seller — Signatory | Text | Signature block | Jodi Karmia |
| P-013 | Seller — Signatory Title | Text | Signature block | Partner |
| P-014 | Seller's Counsel — Firm + Attorneys + Emails | Text | §17 (with a copy to) | Strip Hoppers Leithart McGrath & Terlecky — A.C. Strip & Timothy J. McGrath — acs@columbuslawyer.net / tjm@columbuslawyer.net |
| P-015 | Broker(s) — Firm + Agent + Representing Party | Text | Brokerage article | Julie Cohen — The Robert Weiler Company — representing Seller; Seller pays under separate agreement |

---

## SECTION 2 — PROPERTY (P-016 to P-030)

| Fact # | Field | Type | Typical PSA Source | Example |
|---|---|---|---|---|
| P-016 | Property — Street Addresses | Text | Preamble + Exhibit A | 3492, 3530-3540 (north) + 3483, 3487, 3551-3561, 3585 (south) E Fulton St, Columbus, OH 43227 |
| P-017 | Parcel ID #1 | Text | Exhibit A | 090-005616 |
| P-018 | Parcel ID #2 | Text | Exhibit A | 010-085755 |
| P-019 | Parcel ID #3 | Text | Exhibit A | 010-099214 |
| P-020 | Parcel ID #4 | Text | Exhibit A | 010-004280 |
| P-021 | Parcel ID #5 | Text | Exhibit A | 010-099201 |
| P-022 | Parcel count | Number | Preamble | 5 |
| P-023 | Building count | Number | Preamble | 5 |
| P-024 | Total SF (governing) | Number | Preamble | 202,164 |
| P-025 | Total SF (exhibit component sum) | Number | Exhibit A tract component sum | 202,171 (flag variance) |
| P-026 | Total Acres | Number | Preamble / Exhibit A | 15.67 |
| P-027 | Jurisdiction #1 | Text | Exhibit A | City of Columbus |
| P-028 | Jurisdiction #2 (if multi) | Text | Exhibit A | Village of Whitehall |
| P-029 | Zoning by Jurisdiction | Text | Exhibit A + DD | Columbus M (Manufacturing) / Whitehall CCD (Community Crossroads District) |
| P-030 | Recorded Deed Reference | Text | Exhibit A header | Inst. #202209130130355 Franklin Co. OH (9/13/2022) |

---

## SECTION 3 — ECONOMICS (P-031 to P-045)

| Fact # | Field | Type | Typical PSA Source | Example |
|---|---|---|---|---|
| P-031 | Purchase Price | Number (USD) | §3 | $4,000,000.00 |
| P-032 | All-Cash? | Boolean | §5 / §3 | Yes |
| P-033 | Financing Contingency | Boolean | §4 or §6 | No |
| P-034 | Earnest Money Deposit | Number (USD) | §2.1 | $200,000.00 |
| P-035 | EMD Refundability | Text | §4.1 / §2 | Refundable during Feasibility Period; non-refundable post |
| P-036 | Escrow Agent | Text | §2.1 | Newmark Title Services, 150 East Broad St., 5th Floor, Columbus OH 43215, (614) 535-7201 |
| P-037 | Price per SF | Number | Derived (P-031 ÷ P-024) | $19.79 |
| P-038 | Price per Acre | Number | Derived (P-031 ÷ P-026) | $255,266 |
| P-039 | Environmental — Buyer Cap | Number (USD) | Environmental section | $100,000 |
| P-040 | Environmental — Seller Credit Max | Number (USD) | Environmental section | $25,000 |
| P-041 | Environmental — Termination Threshold | Number (USD) | Environmental section | $125,000 |
| P-042 | Closing Cost Allocation | Text (enum) | §8 | Split 50/50 (PSA §8.2) — NOT standard Franklin County custom |
| P-043 | Title Insurance Cost Allocation | Text | §7 | Split 50/50 |
| P-044 | Counsel Fees | Text (enum) | §8.1 | Each party own |
| P-045 | Broker Commission — Seller-paid? | Boolean | Brokerage article | Yes — Seller pays under separate agreement |

---

## SECTION 4 — KEY DATES (P-046 to P-062)

All dates derived from a single root input (Effective Date P-046). When re-running after an amendment, change only P-046 and let the rest recompute.

| Fact # | Field | Type | Derivation / Source |
|---|---|---|---|
| P-046 | Effective Date (root input) | Date | Latest signature block date |
| P-047 | Deposit Due | Date | Effective Date + 5 business days (§2.1) |
| P-048 | Seller Document Delivery Due (§4.3) | Date | Effective Date + 5 business days |
| P-049 | Seller Document Delivery Due (§6) | Date | Effective Date + 5 calendar days |
| P-050 | Seller Authority Package (§15.1.16) Due | Date | Effective Date + 5 calendar days — FP CLOCK PAUSED UNTIL DELIVERED |
| P-051 | Title Commitment Delivery | Date | Effective Date + 10 calendar days (§7) |
| P-052 | Phase II Order-By | Date | Effective Date + 5 calendar days (§4.3) |
| P-053 | Phase I Target Delivery | Date | Negotiated with consultant; track separately |
| P-054 | Phase II Target Delivery | Date | Negotiated with consultant; track separately |
| P-055 | FP Earliest Expiry | Date | Effective Date + 30 calendar days (§4.1) |
| P-056 | FP Hard Outer Limit | Date | Effective Date + 60 calendar days (§4.1) |
| P-057 | FP Actual Expiry | Date | Later of (P-055, Phase II receipt + 5 BD), capped at P-056 |
| P-058 | Closing Outer Cap — Explicit Date | Date | §9.1 ("but in no case beyond [BLANK]") — often BLANK; record as N/A and flag |
| P-059 | Closing Outer Cap — Source of Hard Stop | Text | Seller lender letter, calendar date, or "None — §9.1 blank" |
| P-060 | Target Close Date | Date | FP Actual Expiry + 5 days (§9.1) |
| P-061 | Proration Date | Date | §8.2 / §10 | Midnight before Closing (per §8.2) |
| P-062 | Offer Expiration (§26) | Date | §26 blank in execution version — typically moot |

---

## SECTION 5 — PSA MECHANICS (P-063 to P-078)

Each mechanics row is either "present" or "not present" for the executed PSA. If present, capture any numeric thresholds or named carve-outs.

| Fact # | Field | Type | Typical PSA Source | Notes |
|---|---|---|---|---|
| P-063 | AS-IS Conveyance? | Boolean | §25 | Yes, but carve-outs apply (see P-064) |
| P-064 | AS-IS Carve-Outs | Text | §25 | Express reps, vacancy/make-safe, §22 survival |
| P-065 | Material Adverse Change (MAC) Triggers | Text | §8 | 10% NOI drop · tenant loss >5K SF · material uninsured casualty · new liens · insurance lapse |
| P-066 | Vacancy Delivery Scope | Text | §9.2(d) | Specific buildings + SF to be delivered vacant |
| P-067 | Make-Safe Requirements | Text | §9.2(e) | Anchor bolts removed; ¼"+ steel plates; NEC-compliant electrical; plumbing capped/pressure-tested; drains functional; envelope sealed; floor patched/leveled; PE cert + unconditional lien waivers |
| P-068 | Seller Default Remedy | Text | §11.3 | Deposit return + out-of-pocket up to $75K (uncapped on Willful Default) OR specific performance |
| P-069 | Purchaser Default Remedy | Text | §11.2 | Seller retains Deposit; sole remedy |
| P-070 | Hazardous Materials Disclosure | Text | §15.1.10 | Seller HAS affirmatively disclosed property "may contain Hazardous Materials" |
| P-071 | §13 Violation Compliance Owner | Text (enum) | §13 | Seller (Seller complies with municipal violation notices at Closing) |
| P-072 | §15.1.16 Authority Package — FP Pause | Boolean | §15.1.16 | Yes (FP clock paused until Seller delivers authority pkg) |
| P-073 | Assignment by Purchaser | Text | §23 | Freely assignable to any entity |
| P-074 | Assignment by Seller | Text | §23 or silent | Typically silent / not permitted |
| P-075 | Seller §1031 Cooperation Provision | Boolean | §29 | Yes — Seller reserves right; Buyer cooperates at no cost |
| P-076 | Buyer §1031 Provision | Boolean | §29 or silent | Typically silent — confirm Buyer's intent separately |
| P-077 | Confidentiality — Permitted Disclosures | Text | §27 | Attorneys, accountants, mortgage holders, subpoena |
| P-078 | Governing Law | Text | §18 | State of Ohio |

---

## SECTION 6 — SURVIVAL & WARRANTIES (P-079 to P-086)

| Fact # | Field | Type | Typical PSA Source | Example |
|---|---|---|---|---|
| P-079 | General Reps Survival | Text / Months | §22(a) | 18 months |
| P-080 | Environmental Reps Survival | Text / Months | §22(b) | 36 months |
| P-081 | Fundamental Reps Survival (authority, title, liens, OFAC) | Text / Months | §22(c) | Indefinite |
| P-082 | Rep Basket / Threshold | Number or "None" | §22 or rep-specific | None (or $[threshold]) |
| P-083 | Rep Cap | Number or "None" | §22 | None (or $[cap]) |
| P-084 | OFAC Compliance Rep | Boolean | §15.1.13 | Yes |
| P-085 | No-Bankruptcy Rep (Seller) | Boolean | §15.1.1 | Yes |
| P-086 | Authority Rep | Boolean | §15.1.5 / §15.1.6 | Yes |

---

## SECTION 7 — LITIGATION & GOVERNMENT NOTICES (P-087 to P-099)

Populate one row per disclosed item. Numbering resets per deal — stay sequential in the table.

| Fact # | Field | Type | Typical Source | Example |
|---|---|---|---|---|
| P-087 | Case / Notice Type | Text (enum) | Exhibit F | Litigation / Lis Pendens / Agency Notice / Code Enforcement / Foreclosure |
| P-088 | Case Caption or Notice Title | Text | Exhibit F | City of Columbus v. SIJ Partnership LLC + Buckeye Recycling |
| P-089 | Case / Instrument Number | Text | Exhibit F | 2021 EVH 060406 / Inst. #202109240970710 / 25 CV 006289 |
| P-090 | Court / Agency | Text | Exhibit F | Franklin Co. Municipal Court, Environmental Division |
| P-091 | Filed Date | Date | Exhibit F | 8/31/2021 |
| P-092 | Current Status | Text | Exhibit F | Agreed Judgment 9/2/2022; Motion to Reopen filed 3/12/2026 alleging non-compliance |
| P-093 | Property-Specific? | Boolean | Exhibit F | Yes |
| P-094 | Seller §13 Cure Obligation? | Boolean | PSA §13 x Exhibit F | Yes |
| P-095 | Title-Impacting? | Boolean | Judgment lookup | Yes (Lis Pendens recorded) |
| P-096 | Co-Defendant Tenant? | Text | Exhibit F | Buckeye Recycling Center, Inc. |
| P-097 | Known Dollar Exposure | Number or N/A | Exhibit F / counsel memo | TBD |
| P-098 | Dismissed / Resolved? | Boolean | Exhibit F | No |
| P-099 | Action Required at Closing | Text | Derived | Attorney review; title commitment must extinguish Lis Pendens; escrow if uncured |

**Recurring subtypes to capture as separate rows:**
- Municipal code notices (per building / per citation)
- Zoning notices
- Graphics / signage code notices
- Environmental agency approvals or notices of violation
- Pending litigation (tort, contract, landlord-tenant, environmental)
- Foreclosure / lender actions
- Lis pendens / mechanic's lien / judgment

---

## SECTION 8 — TENANTS & LEASES (P-100 to P-119)

One row block per tenant. Allocate 4 rows per tenant across the same Fact # span (e.g., P-100 to P-103 = Tenant 1; P-104 to P-107 = Tenant 2). Use Field to differentiate.

Per tenant, capture:

| Field | Type | Source | Example (Buckeye) |
|---|---|---|---|
| Tenant Name | Text | Exhibit B / D | Buckeye Recycling |
| Premises Address | Text | Exhibit B | 3483-3485 E Fulton |
| Premises SF | Number | Exhibit B | 10,000 |
| Monthly Base Rent (Y1) | Number | Exhibit D | $4,018.85 |
| Annual Base Rent (Y1) | Number | Exhibit D | $48,226.25 |
| Escalation Structure | Text | Exhibit D | 3% every 2 yrs from Y5 |
| Expiration Date | Date | Exhibit B / D | 11/29/2030 |
| Options to Renew | Text | Exhibit D | 2 × 5-yr |
| Guarantor | Text | Exhibit B / lease | — |
| Security Deposit | Number | lease | $[amount] |
| In-Place at Close? | Boolean | §9.2(d) | Yes |
| Lease Cancellation Executed? | Boolean | separate doc | No |
| Body-vs-Exhibit Discrepancy Flag | Text | Reconciliation | e.g., "OotBox lease body states 12/31/2030; Exhibit D states 12/31/2031 — reconcile" |

---

## SECTION 9 — CLOSING DELIVERABLES (P-120 to P-135)

Each §9.3 (Seller) and §9.4 (Purchaser) deliverable as a discrete row.

| Fact # | Field | Type | Typical Source |
|---|---|---|---|
| P-120 | Special Warranty Deed (Seller) | Boolean | §9.3(a) |
| P-121 | Assignment of Leases (Seller) | Boolean | §9.3(b) + Exhibit C |
| P-122 | Owner's Affidavit & Gap Indemnity (Seller) | Boolean | §9.3(c) |
| P-123 | C/Os + Permits Transfer (Seller) | Boolean | §9.3(d) |
| P-124 | Proof of Tax Payment (Seller) | Boolean | §9.3(e) |
| P-125 | FIRPTA Non-Foreign Affidavit (Seller) | Boolean | §9.3(f) |
| P-126 | Substitute 1099-S (Seller) | Boolean | §9.3(g) |
| P-127 | Settlement Statement (Seller) | Boolean | §9.3(h) |
| P-128 | Authorizing Resolution (Seller) | Boolean | §9.3(i) |
| P-129 | Updated Certified Rent Roll (Seller) | Boolean | §9.3(k) |
| P-130 | Tenant Notification Letters (Seller) | Boolean | §9.3(l) + Exhibit E |
| P-131 | Bring-Down Certificate (Seller) | Boolean | §15.1.17 |
| P-132 | Purchase Price Wire (Purchaser) | Boolean | §9.4(a) |
| P-133 | Purchaser Settlement Statement (Purchaser) | Boolean | §9.4(b) |
| P-134 | Purchaser Entity Authority Package (Purchaser) | Boolean | §9.4(b) |
| P-135 | Other Title-Company-Required Docs (Purchaser) | Boolean | §9.4(b) |

---

## SECTION 10 — EXCLUSIONS (P-136 to P-142)

| Fact # | Field | Type | Typical Source | Example |
|---|---|---|---|---|
| P-136 | Excluded Equipment? | Boolean | §25.1 | Yes |
| P-137 | Excluded Equipment — Description | Text | §25.1 | Nutis Press / DigiCo printing presses, bindery, specialized manufacturing |
| P-138 | Excluded Equipment — Removal Cost to Buyer? | Text (enum) | §25.1 | None |
| P-139 | Excluded Fixtures vs. Personal Property | Text | §25.1 + schedule | Personal property + trade fixtures |
| P-140 | Post-Removal Restoration Obligation | Text | §25.1 + §9.2(e) | Yes — Seller repairs damage from removal; make-safe applies |
| P-141 | Pre-Closing Walkthrough Required? | Boolean | §9.2(e) or §25.1 | Yes (recommended) |
| P-142 | Tenant-Owned Equipment List | Text | Per-tenant lease | Reference lease exhibits |

---

## SECTION 11 — NOTICES & MISCELLANEOUS (P-143 to P-150)

| Fact # | Field | Type | Typical Source | Example |
|---|---|---|---|---|
| P-143 | Notice Delivery Methods | Text | §17 | Email OR certified mail return receipt OR Federal Express |
| P-144 | Notice Deemed-Received Rule | Text | §17 | Email: date of email; FedEx: next business day; certified mail: actual receipt |
| P-145 | Time is of the Essence | Boolean | §28 | Yes |
| P-146 | Electronic Signatures / Counterparts | Boolean | §21 | Yes |
| P-147 | Memorandum of Contract — Recordable? | Boolean | §21.10 | **No** (E Fulton PSA prohibits recording — note deviation from ORA standard) |
| P-148 | Dispute Resolution | Text | §20 | Prevailing party entitled to fees + costs |
| P-149 | Force Majeure / COVID-19 Tolling | Boolean | §21.11 | Yes |
| P-150 | Integration / Entire Agreement | Boolean | §21.2 | Yes |

---

## SECTION 12 — EXHIBITS (P-151+)

One row per exhibit referenced in the PSA. Confirm each is attached.

| Fact # | Field | Type | Example |
|---|---|---|---|
| P-151 | Exhibit A — Legal Description | Text | Attached — 15.67 AC across 6 Tracts |
| P-152 | Exhibit B — Existing Leases Schedule | Text | Attached — 3 tenants (Buckeye, OotBox, Rogers) |
| P-153 | Exhibit C — Assignment & Assumption of Leases (form) | Text | Attached |
| P-154 | Exhibit D — Rent Roll | Text | Attached |
| P-155 | Exhibit E — Tenant Notification Letter (form) | Text | Attached |
| P-156 | Exhibit F — Litigation and Government Notices | Text | Attached — see Section 7 detail |

If a PSA uses different exhibit letters (e.g., PSA with Exhibits G, H, I, J), map by content not label. Record the letter used in a Note.

---

## Row count expectations by deal complexity

| Deal | Approx. Rows |
|---|---|
| Single-parcel single-tenant industrial | ~95 |
| Multi-parcel multi-tenant industrial (typical Oxford deal) | ~125–155 |
| Portfolio transaction or dual-jurisdiction | 160+ |

A Fact Table under 90 rows for a multi-parcel deal almost certainly has omissions — review each section.

---

## Reconciliation memory

When re-running this skill after a PSA amendment, preserve the original Fact Table as v01 and produce v02. The v02 Fact Table carries an "Amendment Delta" column noting every row whose Value changed, with before/after. Downstream cascade packs built from v02 must reference v02 only — never mix.

# KRG form defect register

Clause-by-clause map of the **Kohr Royer Griffith, Inc. Management Agreement**,
executed 23 December 2020. Owner named as *Eric Goldberg*. Term stated as "Upon
closing estimated to be January 8, 2021 thru December 31, 2024," automatically
renewing for annual periods. Four pages.

Exhibit A properties (all Columbus, Ohio):

| # | Property |
|---|---|
| 1 | 2012 – 2026 Zettler Road |
| 2 | 2800 – 2826 Banwick Road |
| 3 | 384 – 420 Morrison Road |
| 4 | 4595 – 4601 E. 5th Avenue |
| 5 | 2000 – 2008 Zettler Road |

Source document is a **scanned image with no text layer**. All quotations below
are OCR-derived and were read against the page images. Any clause cited in a
counterparty markup must be re-verified against the executed original.

---

## Clause map

| Clause | Text (as read) | Checks | Position |
|---|---|---|---|
| §1 | "appoints the Agent **exclusively** to rent, lease, operate and manage" | P3, P3b | PM-1 |
| §1 | "shall automatically renew for annual periods" | P7 | PM-2 |
| §1 | "Either party may terminate this agreement with 60 day written notice" | P19 | PM-14 |
| §2(a) | "use diligence in the Management of the premises" — no standard of care, no performance metric | P24 | PM-7 |
| §2(b) | monthly statements; Owner funds deficits by the 15th; **1% per month** on unpaid balances | P8 | PM-4 |
| §2(c) | receipts deposited in "a national or state institution"; Agent not liable for bank failure | P23 | PM-5 |
| §2(d) | employees handling Owner's monies bonded at **$250,000** | P22 | PM-8 |
| §3(a) | "to sign, renew and/or cancel leases" | **P1** | PM-9 |
| §1 | leasing and management granted as one indivisible appointment | P3b | PM-1 |
| §3(a) | "utilize a leasing agent to market the premises" — at Owner's expense per §3 preamble | P20 | PM-11 |
| §3(a) | "institute and prosecute actions; evict tenants…; sue…; settle, compromise, and release" | **P6** | PM-10 |
| §3(b) | repairs/alterations/decorations; **$2,000** per-item approval threshold | P21 | PM-4 |
| §3(c) | utility and service contracts; "Owner to assume the obligation of any contract so entered into at the termination" | P13, P14 | PM-15 |
| §3(d) | "any such interest earned shall be kept by the Agent" | P9 | PM-5 |
| §4(a) | Owner saves Agent harmless from **all** damage suits; Agent named co-insured; Agent liable only for willful misconduct or gross negligence | **P2**, P17 | PM-6, PM-8 |
| §4(b) | Owner-initialed authority to pay mortgage, taxes, assessments, insurance from Owner's funds; Agent not responsible for postal delay late fees | — | — |
| §4(c)(1) | management: **4%** of "gross monies collected" or **$850** monthly, whichever greater | P10 | PM-3 |
| §4(c)(2) | leasing: **6%** of "gross lease value" for original leases; "Renewals to be handled by Owner" | **P4**, P29 | PM-11 |
| §4(c)(3) | modernization: fee "match[es] the Management fee percentage"; triggered by "extra time" | P11, P25 | PM-12 |
| §4(c)(4) | court appearance: **$45/hour** | P26 | PM-13 |
| §4(c)(5) | fire/flood rehabilitation: **10%** of gross billings collected from insurer | P12 | PM-13 |
| §4(c)(6) | sale support when KRG is not the listing agent: **$45/hour** | P26 | PM-13 |
| closing | "binding upon the successors and assigns of the Agent, and the heirs, administrators, executors, successors and assigns of the Owner" | P15 | PM-16 |
| preamble | Owner is "Eric Goldberg," an individual | P18 | PM-17 |
| Exhibit A | five address ranges; no parcel IDs, SF, or per-property entity | P30 | PM-17 |
| signature | no entity, no title, no capacity; dates partially illegible | P31 | PM-18 |

## Absences

Nine checks fire on what the agreement does not contain:

| Missing | Check | Position |
|---|---|---|
| Owner audit / books-and-records inspection right | P16 | PM-7 |
| Annual operating budget and variance reporting | P24 | PM-7 |
| Manager professional liability (E&O) insurance | P17 | PM-8 |
| Notice addresses and delivery method | P19 | PM-14 |
| Post-termination turnover obligations | P14 | PM-15 |
| Restriction on Agent assignment / change of control | P15 | PM-16 |
| Governing law, venue, attorney fees, jury waiver | P27 | PM-14 |
| Confidentiality covenant | P28 | PM-18 |
| Express no-tail covenant on leasing commissions | P29 | PM-11 |

The no-tail absence is the only one that currently favors Owner. It should be
converted to an express covenant rather than left to silence.

## Scan result

**31 of 32 checks FAIL** — 5 BLOCK, 15 HIGH, 10 MED, 1 LOW.

The only check that does not fire is **P5** (unfilled tokens) — this is an
executed document, not a draft. Every other check in the register fires. That is
the finding: a four-page form carries essentially none of the protections a
management agreement is supposed to contain.

Control: `tests/remediated_fixture.txt`, an agreement rewritten to PM-1 … PM-18,
scores **0 of 32**. The checks discriminate; the seed document is simply that
thin.

Extraction note: this document scores only under OCR. With `--no-ocr` the
scanner reports `UNREADABLE` and exits 2 — deliberately, since a zero-byte
extraction would otherwise present as a clean bill of health.

## Open questions the document cannot answer

1. **Is the $850 monthly minimum per property or per agreement?** Across five
   properties the difference is approximately $40,800 per year. Resolve from the
   QuickBooks billing history, not from the text.
2. **Which entity actually holds title to each of the five properties**, and has
   any of them been sold or transferred since 2020 without Exhibit A being
   amended?
3. **Is this agreement still in force**, and has any subsequent addendum,
   fee-schedule letter, or superseding agreement been executed? Six annual
   renewals have run.
4. **What service contracts has KRG entered on Owner's behalf** under §3(c)?
   Owner assumes all of them at termination and has never been given a schedule.

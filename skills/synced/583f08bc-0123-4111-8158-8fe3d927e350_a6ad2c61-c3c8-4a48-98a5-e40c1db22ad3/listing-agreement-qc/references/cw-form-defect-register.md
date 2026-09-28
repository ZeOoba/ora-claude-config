# Cushman & Wakefield listing form — defect register

Broker: **Cushman & Wakefield U.S., Inc.**
Form origin: DOCX metadata `creator = cshows`, `Company = Cushman and Wakefield, Inc.`
Team on ORA engagements: Zachary Rines, Benjamin Johnson, Domenic Skunda.
Signatory: Kevin Hughes, Managing Principal.

Two ORA engagements observed on this form:

| Engagement | Scope | Term | Executed |
|---|---|---|---|
| 3875-3883 E Livingston Ave (3883 Livingston LLC) | Sale + lease | 16 Apr 2026 – 31 Dec 2026 | Owner 21 Apr 2026 (Adobe Sign); broker 4 May 2026 (image, outside the Adobe transaction) |
| 2000-2002 Zettler Rd (Fairground Village Center LLC) | Sale only | 14 Aug 2026 – 31 Mar 2027 | Unexecuted as of 17 Aug 2026 |

Sentence-level diff of the two: **every sale-side clause is verbatim identical.**
The delta is confined to parties, property, dates, and the presence or absence of
the lease schedule.

---

## ORA markups already embedded in this form

These five are non-standard C&W terms previously negotiated by ORA. They appear
in both agreements word-for-word. **Confirm each survives on every future
engagement** — their absence is a regression, not a new negotiation.

| Location | Protection |
|---|---|
| §5 Commission | 180-day tail, extendable only on monthly written evidence of live negotiations, hard-capped at 270 days aggregate |
| §6 Outside brokers | Co-broker split dispute may not delay Owner's negotiations; Owner's exposure capped at the Schedule amount |
| §7 Representation | Broker has no authority to execute any lease, amendment, renewal or extension; Owner signs everything |
| Schedule, Computation of Total Sales Price | Gross price = cash at closing + assumed / subject-to debt principal; seller paper at present value, discount rate determined **by Owner in good faith** |
| Schedule, Purchase Option | Option-consideration commission credited dollar-for-dollar at closing; no double compensation |

## Defects surviving in the form

Scanner IDs map to `scripts/listing_qc.py`; positions map to
`references/standing-positions.md`.

| ID | Defect | Sev | Livingston | Zettler |
|---|---|---|---|---|
| L1 | Two conflicting definitions of gross sale price | BLOCK | ✗ | ✗ |
| L2 | No excluded-prospect carve-out | BLOCK | ✗ | ✗ |
| L3 | No affiliate / involuntary-transfer carve-out | BLOCK | ✗ | ✗ |
| L4 | Automatic 12-month post-expiration holdover | BLOCK | ✗ | ✗ |
| L5 | No Owner termination right during the primary term | BLOCK | ✗ | ✗ |
| L6 | Tail list captures prospects "submitted by any party" | BLOCK | ✗ | ✗ |
| L7 | Prospect-list delivery not a condition precedent | BLOCK | ✗ | ✗ |
| L10 | Lease machinery surviving in a sale-only instrument | HIGH | n/a | ✗ |
| L11 | No negative covenant barring a lease commission | HIGH | n/a | ✗ |
| L12 | Blanket dual-agency consent, "timely" undefined | HIGH | ✗ | ✗ |
| L13 | No Ohio agency disclosure form referenced | HIGH | ✗ | ✗ |
| L18 | Gross price sweeps in "release of existing liabilities" | HIGH | ✗ | ✗ |
| L19 | No lender-consent / encumbrance acknowledgment | HIGH | ✗ | ✗ |
| L20 | Owner entity name inconsistent preamble vs signature block | HIGH | — | ✗ |
| L21 | Hyphenated address range against a single parcel ID | HIGH | ✗ | ✗ |
| L22 | Mixed automatic and manual section numbering | MED | — | ✗ |
| L23 | Retroactive commencement | MED | ✗ | — |
| L24 | Running header reads "A PROPOSAL FOR" | LOW | — | ✗ |
| L25 | Typographical (ZIP spacing, space before comma, "Each party represent") | LOW | ✗ | ✗ |

Totals: **Livingston 14/25, Zettler 18/25.**

## Exposure arithmetic

**Maximum engagement exposure (Zettler as drafted).** Primary term 14 Aug 2026 →
31 Mar 2027, plus automatic 12-month holdover → 31 Mar 2028, plus the 270-day
tail → late Dec 2028. **≈ 2 years 4½ months on a 7½-month listing.**

**Commission schedule.** 6.00% of gross sale price with a cooperating broker
(3.0 / 3.0 split); 4.00% with none.

**What an omitted exclusion costs.** The subject parcel is a discrete 11,160 SF
freestanding warehouse (Franklin County parcel 010-015487, 0.916 acres, class
`COMMERCIAL WAREHOUSES`, acquired Feb 2021 for $1,000,000 = $89.61/SF). Its
occupant has given notice. The highest-probability buyer is one of the fifteen
ORA tenants immediately adjacent at 2018 Zettler Rd — several of whom already
occupy more square footage than the subject building. On a $1.5M sale to a tenant
ORA sourced itself, the unexcluded fee is **$60,000 at 4.00%** and **$90,000 at
6.00%**.

## Structural notes

- **No redline record.** Both files arrive with the ORA markups baked in and zero
  `<w:ins>`/`<w:del>` elements. There is no way to see what moved off the C&W
  standard form without the standard form. Request and archive it (deal-folder
  checklist item 8).
- **Execution evidence.** The Livingston Adobe Sign Final Audit Report
  (transaction `CBJCHBCAABAAmGMS6CT9bFxxVMPZqsdl_8aqSIP99J7w`) records document
  creation by Eric Goldberg, dispatch to Gabriel Goldberg, and Gabriel's
  e-signature on 2026-04-21 16:29:18 GMT — and nothing after. The broker's
  signature is a graphic on page 3 dated 5/4/26, applied outside the transaction.
  The audit report alone does not evidence C&W's execution.
- **Diff is not a gate.** Two engagements a year apart produced an identical
  sale-side text. Comparing a new listing to the last executed one returns "no
  changes," which reads as clearance and is not. Run the absolute scan.

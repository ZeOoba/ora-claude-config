# ORA Addendum House Style — baseline, mined from the live corpus

Source: five real ORA addenda reviewed 2026-08-14 (1100 Rarig Ave Unit K; 2203-2207 Northwood
Suite C1-2; 29000 Information Lane Unit 101; 9050 Red Branch Rd Suite C; 2808 Banwick Rd).
This is what ORA actually does today — the skill's job is to keep the parts that work and add
the scaffolding the corpus is missing (novation package, counterparts, notice addresses,
guaranty). Do not silently "improve" the parts that already work correctly.

## What the corpus already does right — keep it

- **Single terse template**, reused across every property: title line → one-sentence recital →
  labeled clauses → ratification sentence → signature blocks.
- **True minimal-amendment discipline** — no document restates an unchanged Prime Lease
  provision. Every file states only what's changing.
- **Canonical ratification sentence, verbatim across all five files:**
  *"All other terms of the Prime Lease will remain in effect."* Use this exact sentence; do not
  paraphrase it.
- **Generic clause labels, never Prime Lease section numbers** — "Termination," "Base Rent,"
  "Tenant," "Brokers," "Other Terms." This already satisfies Doctrine rule 4.
- **Escalation convention, where rent escalates:** 3% compounding, Lease-Year anniversary (not
  calendar year) — confirmed in three of three escalating addenda in the corpus. Confirm the
  actual negotiated rate per deal; don't hardcode 3% as a default without checking.
- Two structural rendering variants are both acceptable: free-standing labeled paragraphs
  (older files) or each clause wrapped in a 1×2 table (newer files). Either is fine; be
  consistent within one document.

## What the corpus is missing — this is the gap this skill exists to close

Confirmed absent, **without exception, across all five files**:

- Counterparts / electronic-signature clause
- Notice-address clause, for any party
- Security deposit disposition language
- Insurance reissuance/certificate language
- Guaranty language
- Real page breaks before signature pages — every file uses the literal text "(Signature Page to
  Follow)" or similar with no actual `w:br type="page"` behind it (a `lastRenderedPageBreak`
  artifact is not a forced break)

This means the acceptance-test file's defects (missing consent signatures, missing security
deposit disposition, missing insurance condition, missing notice address, unclaimed rent stub)
are not an isolated drafting slip — the template this office has been using has **no mechanism**
for any of that, so the defect reproduces on the next novation unless this skill's M3b package
is actually invoked. Do not treat M3b as optional boilerplate; it is the fix for a structural gap
in prior practice, not a stylistic add-on.

## Traceability defects observed — enforce against these

- **Ordinal drift between filename, body title, and document metadata Title field.** One file in
  the corpus has a metadata Title field reading "SIXTH ADDENDUM TO LEASE" while its body title
  and filename both say "Second Addendum" — almost certainly a cloned-template artifact never
  cleared. QC check 9 must read and compare all three (filename, body title, `core.xml` Title
  property), not just the body.
- **Blanket "and any subsequent addendums" catch-all** instead of enumerating actual prior
  amendment dates. Two files in the corpus use this phrasing even where it's the *first*
  addendum (logically vacuous) or where prior addenda demonstrably exist but aren't dated. This
  does not satisfy Doctrine rule 1 — always enumerate.
- **Rent-schedule tables not grammatically bound to the operative sentence.** One file in the
  corpus ties its table to the obligation explicitly ("...payable in equal monthly installments
  in accordance with the following schedule"); another has a structurally identical table with
  no such binding sentence — and that's precisely the file with the unclaimed stub-period defect.
  Always include the binding phrase.

## Metadata hygiene

Two files in the corpus carry a stray `core.xml` Title property reading "EXHIBIT 'D'" — leftover
from whatever template they were cloned from. Clear or correctly set the Title property on every
document this skill produces; it is part of QC check 9's traceability requirement, not a
cosmetic nicety (a stale Title field is exactly how the ordinal-drift defect above happened).

---
name: ora-loan-terms-reconciliation
description: Monthly (6th, 1:20 PM ET) — reconciles the hard-number loan terms carried in the loans-external-register Cowork artifact against the executed instruments (Note / Deed of Trust / Guaranty / lender amortization schedule). Read-only and flag-only: never edits the artifact, never auto-corrects a term (debt terms are governor-adjacent, Hard Invariant 4). Built 2026-08-17 after a late-charge grace period carried as "15 calendar days" in the register was found to contradict the executed 5600 Sunnyside Note's actual five (5) days — an error that sat unnoticed from July and surfaced only because a payment happened to land inside the gap. Posts to Notion Ops Hub as primary delivery; attempts COM email to ggoldberg only. [MODEL: claude-sonnet-5 | set 2026-08-17]
---

ORA LOAN TERMS RECONCILIATION — monthly drift check, register vs. executed instruments.

PURPOSE
The `loans-external-register` Cowork artifact carries transcribed loan terms that are STATIC — frozen at each card's stated sourcing date. Nothing re-reads them against the instruments they came from. This task closes that gap. Root incident (2026-08-17): the 5600 Sunnyside / Restoration Church receivable carried a late-charge grace period of "15 calendar days" when the executed Note §4 reads five (5). Under the wrong figure almost no payment looked late; under the correct one, five installments over the loan's life had cleared grace with $8,356.85 assessable. The error was introduced no later than July and was found only incidentally.

GUARD
Read-only and flag-only. NEVER edit the artifact, the register, or any loan term. NEVER auto-correct. Corrections to debt terms flow from the executed instrument through Gabriel's review, per Hard Invariant 4 (debt terms are DSCR/LTV governor-adjacent). Your output is a findings report, nothing else.

STEP 1 — Read the register
Read the artifact HTML at:
  C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Artifacts\loans-external-register\index.html
Parse the `LOANS` and `RECEIVABLES` arrays. For every entry, extract these HARD-NUMBER fields — the class where a wrong value is both cheap to verify and expensive to hold:
  - original principal
  - contract interest rate (and any stepped/reset rates)
  - stated monthly payment
  - maturity date
  - amortization term
  - late charge: percentage AND grace-period days
  - default rate
  - prepayment terms (lockout, penalty formula, open window)
  - guarantor name(s) and recourse percentage
Also capture each entry's `sources` list and the sourcing date asserted in its `amort.confidence` string.

STEP 2 — Locate the primary instrument for each loan
Search SharePoint via the M365 connector under Documents/Business/Loans External/, plus the cross-referenced property folders (some loans' documents live under the property folder, not the loan folder — the 5600 Sunnyside documents are filed under "5600 Sunnyside Ave", and its Loans External subfolder is empty). Primary instruments, in priority order: executed Note > Deed of Trust / Mortgage > Guaranty > lender-issued amortization schedule > loan application. A commitment letter, ChatGPT summary, or internal tracker is NOT a primary instrument and must never be used to confirm a term.

STEP 3 — Field-by-field comparison
For each field from Step 1, return exactly one verdict:
  - MATCH — register agrees with the instrument. Cite the section.
  - MISMATCH — register disagrees. Quote the instrument's actual language verbatim, give the register's value, and state the practical consequence of the error (as with the 15-vs-5-day grace, the consequence is usually more revealing than the delta itself).
  - UNVERIFIABLE — no primary instrument on file for that field. This is NOT a mismatch. The register already flags several of these (9050 Red Branch Road's Deed of Trust and Guaranty are not on file; covenant-level terms for loans whose folders hold only an amortization schedule). Report them as a standing documentation gap, and do not re-litigate ones the register already discloses unless something changed.
Never infer a term from a sibling loan's structure. Symetra's two facilities are similar but not identical, and "the other one says X" is not evidence.

STEP 4 — Amortization schedule freshness
For any loan whose register card cites an amortization schedule, check whether a newer copy exists in SharePoint than the one cited. A schedule updated since the register's sourcing date may record payments that change a current balance or a paid-through date. Report the file's modified date and flag if newer. Do not re-derive balances — just flag.

STEP 5 — Report
PRIMARY DELIVERY — Notion Operations Hub (page 32b6ecd8-9e59-81ed-b571-dfc871ab9f25). Create a dated entry titled "Loan Terms Reconciliation — YYYY-MM-DD" containing:
  - a per-loan table of field verdicts
  - every MISMATCH in full, with instrument quote, register value, and consequence
  - the UNVERIFIABLE standing-gap list
  - schedule-freshness flags
  - a QUESTIONS FOR GABRIEL section for anything ambiguous
SECONDARY — if and only if at least one MISMATCH was found, attempt an email via Outlook COM:
  powershell -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
  TO: ggoldberg@oxfordra.net ONLY. No cc — the cc to egoldberg@ is sanctioned for the ora-am-brief Daily Brief alone.
  Subject: "[ACTION REQUIRED] Loan terms drift — N mismatch(es) — YYYY-MM-DD"
  On non-zero exit: retry once, then note the failure loudly in the Notion entry and continue. Do NOT halt. The LAMS/Cowork fleet has historically had unreliable COM reach, which is why Notion is primary — an email failure is not a task failure.
A clean pass (zero MISMATCH) posts to Notion only and sends no email.

NEVER FABRICATE
If an instrument cannot be read, say so and mark the field UNVERIFIABLE. Do not guess at a term, do not fill from the internal tracker, and do not treat the register's own value as corroboration of itself. Route every genuine ambiguity to QUESTIONS FOR GABRIEL rather than resolving it silently.

RELATED
- `debt-management` skill v1.3+ — owns payoff-statement and covenant workflows; this task feeds it.
- `legal-intelligence` skill — use its extraction conventions when parsing instrument language; do not duplicate its logic here.
- `automation-health-monitor` — flag this task for coverage on its next list revision.
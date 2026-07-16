---
name: reference-quickbooks-financials
description: "QuickBooks access path (CloudVara RDP), .QBB un-parseability, and where entity financial statements actually live + which are image-only scans + operating-P&L basis per property. Moved out of MEMORY.md index 2026-06-09 (was inline content, violating one-line-per-entry rule)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d854efbd-b19f-4bfe-b5fa-79fb9d92e649
---

# QuickBooks Access & Entity Financial-Statement Sourcing

*Captured 2026-06-08; relocated from the MEMORY.md index 2026-06-09 (consolidation pass — index must hold pointers, not content).*

- **QB access = CloudVara hosted RDP** (window "Oxford CloudVara Gabriel Log-In", 20.110.1.50), QuickBooks Desktop **Pro Plus 2024**, company "Oxford Realty Advisors", admin-password gated. QB is NOT installed on the local PC — the RDP window renders on the local desktop, so computer-use CAN drive it (Gabriel enters credentials). See [[tech]] §6 (PM platforms / QB Desktop).
- **.QBB backups cannot be parsed offline** (verified): OLE2 container → zlib-compressed company file → AES-encrypted DB (decompressed entropy 7.999, zero plaintext). Only QB Desktop / Intuit SDK can read them → export-from-QB is the only route. Files in OneDrive "Quickbooks Backups -- CURRENT FILES/Actual Backups" (22 entities).
- **Existing statements are SCATTERED**, not in the (mostly empty) per-property "Financial Statements"/"Tax Documents" subfolders. They live in: per-property root folders; "Loans External/Loan Park National/Tax Documents" (1065s 2020–2023 for 1851 SCS, 6718, FVC, Fenton, Muirkirk); "Taxes Estimated + Returns/2024 Tax Returns" (per-entity 2024); "Taxes Rarig".
- **2023 federal 1065 returns for 1851 SCS, 6718, Fairground Village, Fenton are IMAGE-ONLY scans** (no text layer; need OCR or QB).
- **Operating P&L bases differ**: Yardi cash-flow (1900 N Broadway, 29000 Info Lane, Muirkirk 24-25), QuickBooks (5600 Sunnyside, 1100 Rarig, Muirkirk 21-23), Rent Manager (2203 Northwood, 5242 Angola), Form 8825 tax-basis (401 Sunburst, 6718, FVC, 7658 Fishel). **Muirkirk/9050 Red Branch has CONFLICTING QB vs Yardi 2023/2024 net income** — reconcile before external use.
- Consolidated draft built: `C:/Users/Owner/ora-financials-work/outputs/2026-06-08_ORA_ConsolidatedFinancials_OperatingLLCs_v0.1.xlsx` (16 operating LLCs; 14 w/ P&L, 5 w/ BS).

## 2026-06-09 — Deep folder sweep + Master WB findings (consolidated financials v0.3)

*Relocated here from the MEMORY.md index 2026-06-11 (Phase A remediation — index holds pointers, not content).*

- **Master Excel Template Company Wide -- Oxford.xlsx** ("eric spreadsheets/") = live operating model; **Property NOI tab** = current run-rate per property (round-number expenses = scenario estimates, not actuals). **Ownership: 1900 N Broadway 50%, 9050 Red Branch 50%, rest ~100%** (Assumptions tab named ranges Oxford_Share_*).
- **Sepich Portfolio (Zettler/Banwick/Morrison, Columbus) is owned by Fairground Village Center LLC** — property-level Rent Manager P&Ls in "Sepich Portfolio/" (Banwick+Morrison P&L 2023-2025: NOI 350,516 / 421,039 / 498,707 YTD; Columbus P&L 2025 income 1,170,585). Subsets of FVC — never add to entity-level.
- **5242 Angola Rd + 5333 Secor sold 07/2024** (settlement statement in 5333 folder) — their data correctly ends 2023.
- **1100 Rarig DRAFT 1065s live in "Taxes Rarig/"** (2024 + 2025). 2024 tax NI -236,822 vs QB accrual +21,530 — difference = one-time Sec481 deprec catch-up 217,346; rents tie at 224,571. Sch L chains 2023→2025 (TA 1,834,125 → 1,549,265 → 1,492,845).
- **EG Family LLC/55 New Plant**: "Operating Results 2020-2022" workbook books beneficiary distributions AS EXPENSES (600k in 2021) — NI badly distorted; flag whenever using.
- **9620 State 350 (Raytown, acq 10/2024) + 3034 Westerville (acq 09/2024) are NOT in the .QBB backup set**; Raytown has 2025 YTD operating statement (NI 19,788 thru 09/04/25); Westerville has only the seller's (Buckeye Best) 2024 stmt.
- Workbook now at v0.3: C:/Users/Owner/ora-financials-work/outputs/2026-06-09_ORA_ConsolidatedFinancials_OperatingLLCs_v0.3.xlsx (19 entities; new "Run-Rate & Property-Level" tab from Master WB).

## 2026-06-12 — PFI corpus audit (Property Financials folder, 32 files, all parsed)

- **`OneDrive…/Property Financials/` is Gabriel-ratified as the canonical P&L staging folder** (2024/2025/2026 YTD per property; 12 property tokens today). Audit: 339 distinct GL accounts; verified mapping seed at `oxford-command-center/docs/superpowers/specs/2026-06-12-pfi-account-mapping-seed.json`.
- **2203-2207 Northwood runs on AppFolio, not Rent Manager** (staged 2025 + 2026 YTD reports are AppFolio "Cash Flow" PDFs with text layers). They are NOT true P&Ls: 2025 books Owner Transfer $61,171 and Interest Expense $162,474 inside "Total Operating Expense" (stated "NOI" is after-debt-service); 2026 YTD has no RE taxes and net-negative insurance; both cash reconciliations don't tie; report covers the 3-building group (2207/2205 Northwood + 2203 Marvel Rd); header typo "Nothwood".
- **Distributions-booked-as-expenses is portfolio-wide, not just EG Family LLC:** 1100 Rarig 2024 books $25,000 "7402 Distribution to Owner" as a NON OPERATING EXPENSE under DEBT; Rent-Manager-style reports also count security-deposit receipts and unallocated prepays as INCOME. NOI from these reports must be re-derived, never taken as stated.
- 1851 South Club Solar = retained rooftop-solar entity; the 1851 South Club Drive building was SOLD (transfer notice to RLIF East LLC/RealTerm in the entity folder). Its three staged files are ~306 KB .xlsm macro workbooks (all others 12–19 KB .xlsx).

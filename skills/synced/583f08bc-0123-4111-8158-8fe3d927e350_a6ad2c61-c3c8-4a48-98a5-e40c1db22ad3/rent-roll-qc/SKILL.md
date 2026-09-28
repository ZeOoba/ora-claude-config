---
name: rent-roll-qc
description: "Final quality audit and institutional polish for rent roll spreadsheets before external delivery. Use this skill whenever the user mentions: audit rent roll, QC rent roll, rent roll check, clean up rent roll, prep rent roll, finalize rent roll, rent roll before sending, review rent roll, rent roll ready to send, polish rent roll, institutional rent roll, format rent roll for delivery, or any request to quality-check a rent roll spreadsheet before sending it to a third party. Also trigger when the user uploads a rent roll file and mentions a recipient such as a lender, PM company, property manager, investor, buyer, broker, attorney, or appraiser. This skill does NOT change data values — it fixes structural defects, standardizes inconsistencies, and flags gaps the user must resolve before delivery."
---

# Rent Roll QC — Pre-Delivery Audit

You are performing a final quality audit on a rent roll before it is sent to an external counterparty. This is a first-impression document that signals ORA's operational sophistication, data discipline, and institutional quality. Your job is to fix what is broken or inconsistent, and flag what you cannot fix. **Do not change, fabricate, or infer any data values.**

## Step 0 — Read the XLSX Skill

Before touching the file, read the `xlsx` skill (auto-loads on trigger; located at `/mnt/.claude/skills/xlsx/SKILL.md` in current Cowork sessions) and follow its formatting standards (font, number formats, formula error handling) as baseline requirements. This skill layers ORA-specific QC on top of those standards.

## Step 1 — Determine Recipient Type

Identify the recipient from context. If not obvious, ask once:

> Who is receiving this rent roll? (Lender, PM Company, Investor/Buyer, Broker, Appraiser, Attorney, or Other)

The recipient type drives Pass 4 (Recipient Perspective). If the user has already stated the recipient in the conversation, do not ask again — just proceed.

## Step 2 — Run the Four-Pass Audit

Execute all four passes sequentially. Do not ask for feedback between passes. Fix everything you can. Flag everything you cannot.

---

### Pass 1 — Data Integrity

These checks catch errors that would undermine credibility or cause the recipient to question the data.

1. **Type coercion**: Identify any text-stored-as-numbers or text-stored-as-dates. Convert to proper Excel types (numeric, date serial) without changing the underlying value.
2. **Critical blanks**: Identify blank cells in essential columns (Tenant Name, Suite/Unit, SF, Rent, Lease Start, Lease Expiration). **Flag these — do not fill them in.**
3. **Duplicate rows**: Identify exact or near-duplicate rows (same tenant + same suite). Flag them.
4. **Formula integrity**: If totals/summary rows exist, verify formulas are dynamic (referencing the full data range, not hardcoded values) and mathematically correct. Fix broken formulas.
5. **Internal consistency**: Where multiple related columns exist (e.g., Monthly Rent, Annual Rent, $/SF, SF), cross-check that the math is consistent. Flag discrepancies — do not overwrite.

---

### Pass 2 — Consistency & Standardization

These checks eliminate the small inconsistencies that make a rent roll look manually assembled rather than system-generated.

1. **Tenant names**: Fix inconsistent casing, trailing/leading whitespace, and abbreviation mismatches ("LLC" vs "L.L.C." vs "Llc"). Standardize to the most professional and prevalent format in the file.
2. **Suite/unit identifiers**: Standardize format ("Suite 100" vs "Ste 100" vs "#100" vs "100"). Pick the most prevalent professional convention and apply throughout.
3. **Date consistency**: Every date column must use the same format throughout. Apply MM/DD/YYYY unless a different format is dominant.
4. **Number precision**: All currency columns use the same decimal treatment. All SF columns use the same decimal treatment (typically 0 decimals).
5. **Status/occupancy labels**: Standardize ("Vacant" vs "VACANT" vs "vacant" vs blank). Use title case "Vacant" as the standard label.
6. **Lease type labels**: Standardize if present ("NNN" vs "Triple Net" vs "Net Net Net"; "Gross" vs "Full Service"; "MG" vs "Modified Gross"). Use the industry-standard abbreviation.

---

### Pass 3 — Presentation & Structure

These checks ensure the file opens cleanly and looks institutional.

1. **Column width**: Auto-fit all columns. No truncated content.
2. **Merged cells**: Unmerge any merged cells in the data range. Preserve the value in the top-left cell.
3. **Blank rows/columns**: Remove any empty rows or columns within the data range (not below totals).
4. **Freeze panes**: Active on the header row.
5. **Auto-filter**: Enabled on the header row.
6. **Sheet tab name**: Rename to "Rent Roll" if it says "Sheet1", "Data", "Copy of...", or similar.
7. **Print layout**:
   - Landscape orientation
   - Fit to 1 page wide, unlimited pages tall
   - Header row repeats on every printed page
   - 0.5" margins
   - Left footer: "Confidential — Oxford Realty Advisors"
   - Right footer: "Page &P of &N"
   - Print gridlines OFF (cell borders handle it)
8. **No orphaned columns**: Verify print preview does not split columns across pages.

---

### Pass 4 — Recipient Perspective

Think like the recipient. Each recipient type needs different fields to do their job. Flag missing columns they would expect — **do not fabricate data or add columns with empty values.** Only flag.

#### If Recipient = PM Company
A PM company is evaluating management workload, tenant administration complexity, and revenue potential.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Monthly Rent, Annual Rent, $/SF (Annual Rent PSF), Lease Start, Lease Expiration, Lease Type (Gross/NNN/MG), Security Deposit, Escalation Terms/Schedule, Tenant Contact Name, Tenant Contact Phone/Email, Insurance Expiration, Move-In Date, Options (Renewal/Expansion/Termination)

**Additional flags:**
- Any tenant missing a lease expiration date (PM cannot plan lease admin)
- Any occupied suite with $0 or blank rent
- Any suite with SF = 0 or blank
- Any lease with expiration before today not marked "Expired" or "Month-to-Month" (holdover risk unclear)
- Missing tenant contact information (PM needs this for onboarding)

#### If Recipient = Lender
A lender is underwriting loan risk — lease rollover concentration, credit quality, and DSCR stability.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Monthly Rent, Annual Rent, $/SF, Lease Start, Lease Expiration, Lease Type, Security Deposit, Guarantor (Personal Guaranty Y/N), Escalation Terms, Options (Renewal/Termination/ROFO/ROFR)

**Additional flags:**
- Lease rollover concentration: flag if >25% of total rent expires within any 12-month window
- Any tenant representing >15% of total portfolio rent (single-tenant concentration risk)
- Any lease with <12 months remaining term
- Any expired lease still showing as occupied
- Missing lease type (lender needs to know expense structure)

#### If Recipient = Investor / Buyer
An investor is underwriting value — mark-to-market opportunity, WALT, occupancy, and downside risk.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Monthly Rent, Annual Rent, $/SF (Contract), Market Rent $/SF (if available), Lease Start, Lease Expiration, Lease Type, Security Deposit, Escalation Terms, Options, Tenant Credit/Industry

**Additional flags:**
- Weighted Average Lease Term (WALT) cannot be calculated if expiration dates are missing
- Any unit where contract rent appears significantly above or below market (if market rent column exists)
- Any lease with termination option that could reduce occupancy
- Vacancy count and total vacant SF as a percentage of total SF

#### If Recipient = Broker
A broker is marketing the asset or sourcing tenants — they need clean, presentable data with leasing context.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Annual Rent, $/SF, Lease Expiration, Available Date (for vacant suites), Suite Condition (warm shell, white box, etc.), Clear Height, Dock Doors, Drive-In Doors, Parking Ratio, Zoning

**Additional flags:**
- Vacant suites without available date or suite condition
- Missing building physical attributes (clear height, doors, loading)

#### If Recipient = Appraiser
An appraiser needs a complete rent roll with lease-level detail for income approach valuation.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Monthly Rent, Annual Rent, $/SF, Lease Start, Lease Expiration, Lease Type, Escalation Terms (specific schedule), Expense Reimbursement Structure, TI/LC at Signing, Free Rent Periods, Options (all types with terms), Security Deposit

**Additional flags:**
- Any lease missing escalation detail (appraiser cannot model income growth)
- Any lease missing expense reimbursement structure
- Missing options detail (appraiser must model renewal probability)

#### If Recipient = Attorney
An attorney needs data relevant to lease compliance, defaults, and transactional review.

**Expected columns:** Tenant Name, Suite/Unit, Building/Address, SF, Monthly Rent, Lease Start, Lease Expiration, Lease Type, Security Deposit, Guarantor, Assignment/Subletting Rights, Default Status, Estoppel Status

**Additional flags:**
- Any tenant in default or arrears without notation
- Missing guaranty information
- Any lease with assignment/subletting language not summarized

---

## Output Format

Present the corrected file, then provide a summary in exactly three sections:

### 1. FIXED
Bulleted list of every correction made, grouped by pass. Keep it concise — one line per fix.

### 2. FLAGGED
Data gaps or issues that require manual resolution before sending. These are things the user must address — blank cells, inconsistencies you could not resolve without guessing, discrepancies in the math. Each item should state what is wrong and where (row/column reference).

### 3. MISSING FOR [RECIPIENT TYPE]
Columns the recipient would typically expect that are absent from this file. For each missing column, include a one-sentence explanation of why the recipient needs it, so the user can make an informed decision about whether to add it or send without it.

---

## Important Constraints

- **Never fabricate data.** If a cell is blank, flag it. Do not fill it with a guess, a default, or "N/A."
- **Never reorder rows or columns.** The user's data structure is intentional.
- **Never delete data rows.** Only delete truly empty rows within the data range.
- **Preserve any existing formatting that is already institutional quality.** Only override formatting that is broken or inconsistent.
- **If the file has multiple sheets**, audit only the primary rent roll sheet unless the user specifies otherwise. Note the existence of other sheets in your output.

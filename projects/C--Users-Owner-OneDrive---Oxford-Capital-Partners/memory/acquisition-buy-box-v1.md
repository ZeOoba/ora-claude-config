---
name: acquisition-buy-box-v1
description: "Canonical durable record of ORA's ratified acquisition Buy Box & Scorecard doctrine — schema v1.1, Rulings 1-5 + Amendments A-G, all ratified 2026-06-09 — extracted from acquisition-underwriting/SKILL.md v4.12. Created 2026-08-17 to close a gap where the ora-skill-store-drift-check task's step 2c has cited this exact memory key since 2026-06-20 and it never existed, silently SKIPPING that check on every run."
metadata:
  node_type: memory
  type: reference
  originSessionId: ora-skills-drift-check-remediation-2026-08-17
  modified: 2026-08-17T17:39:07.204Z
---

# ORA Acquisition Buy Box & Scorecard — canonical doctrine record (schema v1.1)

**Ratified: Gabriel Goldberg, 2026-06-09.** Source of truth for content: `acquisition-underwriting/SKILL.md`
(ora-skills repo), read at v4.12 (2026-08-15) on 2026-08-17. This memory file is the durable record
`ora-skill-store-drift-check` step 2c diffs the installed skill against — it existed only as an
*expected key* in two 2026-06-09/2026-06-20 build-brief docs before now; step 2c has been silently
SKIPPING the doctrine-ahead-of-skill check every run since inception because the key was never
created. Root-caused 2026-07-08, closed here 2026-08-17.

**Schema version: v1.1 — unchanged since ratification.** The skill's own header states this
explicitly as of v4.12: "scorecard weights are v1.1 and unchanged since [2026-06-09]." The skill
FILE has iterated to v4.12 across many procedural/documentation revisions; the Buy Box & Scorecard
*doctrine* itself (the numbers below) has not moved. See [[reference_skill_description_version_extraction_gotcha]]
for why "v1.1" in this skill's frontmatter names the *schema* revision, not the file revision — a
regex or session comparing "the skill's version" against this record must diff against v1.1, not v4.12.

## Governor values (Hard Invariant 4 — never move without Gabriel's explicit authorization)

- **DSCR floor (per-property):** post-refi DSCR must be **≥ 1.25x** at market-rate refi terms.
  Breach = flag (Ruling 5), not kill.
- **LTV ceiling (per-property refi sizing):** **≤ 65%** LTV at stabilized exit-cap value. Refi debt
  is sized to the LESSER of 65% LTV and 1.25x DSCR — the two are checked together, not independently.
- **LTV ceiling (portfolio-aggregate, Hard Invariant 4):** **≤ 40%**, checked at STAGE 2.3 against
  aggregate outstanding secured debt ÷ aggregate portfolio value at each asset's market exit cap.
  Breach = **LTV-FLAGGED (portfolio)** — flag, not kill, but requires Gabriel sign-off before LOI.
  Distinct from the per-property 65% ceiling: a single deal can refi to 65% while the portfolio in
  aggregate stays under 40% (ORA runs ~15% actual as of 2026-08).

## The five Calibration Rulings

1. **Ruling 1 — Yield floor scoring.** At the walk price, score Yield as-is: 0 pts when the YoC
   floor (stabilized YoC > 8%, prefer 10%+) binds. No midpoint adjustment.
2. **Ruling 2 — Mezzanine credit.** Partial SF credit only if conditioned + code-compliant egress +
   leasable. Credit % = expected mezz rent ÷ ground-floor rent, **capped at 75%**; otherwise 0%
   credit plus removal CapEx if dysfunctional.
3. **Ruling 3 — Entry-cluster satellite eligibility.** Entry clusters (non-established markets)
   earn NO satellite eligibility until ORA's first closed deal validates the cluster. Satellites are
   otherwise only eligible within 30 min of an ESTABLISHED cluster, Market points capped at half.
4. **Ruling 4 — Flood/FEMA land credit.** SFHA on the building pad = gate flag. SFHA on excess land
   = land valued at $0 in the basis test until a FEMA determination lands; report the verified-dry
   score as an upside band, not the base case.
5. **Ruling 5 — No hard kills.** Gate/floor breaches are FLAGS, screened as exceptions — never an
   automatic kill. Only Gabriel kills a deal. This is a deliberate divergence from bank/institutional
   CRE underwriting norms (which hard-gate environmental/structural/zoning defects) — it is the
   specific mechanism that lets ORA's all-cash, generational-hold family-office capital look at
   deals a bank or fiduciary fund must auto-reject. Do not let a future "institutional hardening"
   pass walk this back.

## The seven Amendments (A-G) — each names the SKILL.md section it governs

- **Amendment A — Stage 2 Scorecard (100 pts).** Quality + Economics + Combined, reported as all
  three, not just Combined.
- **Amendment B — Stage 2.2 P(exec) + Expected Score.** Pipeline-sort mechanism.
- **Amendment C — Stage 1 Floors.** Yield, Basis, DSCR, Carrying-cost — flags not kills per Ruling 5.
- **Amendment D — Stage 2.1 Tenancy Bear-Mode.** Checked on every screen.
- **Amendment E — Outcome Feedback.** Post-decision calibration-loop mechanism.
- **Amendment F — Exception Register + Tripwire.**
- **Amendment G — Stage -1 Intake Rules.** Mandatory before any score is quoted.

## Explicitly UNRATIFIED — do not treat as current Buy Box doctrine

These are live in the skill body as of v4.12 but are NOT part of the ratified v1.1 schema above —
each is tagged PROPOSED/pilot/pending in the skill's own text. Do not encode them as ratified Buy
Box content in any downstream consumer (deal-comparison, market-monitor, this check) until Gabriel
formally ratifies each:

- **FORG (Stage 2.8) — Functional Obsolescence & Durability Grade.** Pilot tier (A-D), logging
  mechanism fixed v4.10, but the tier system itself remains PROPOSED, not ratified.
- **Alternative Asset Class Track (Stage 2.9)** and the associated office/alt-class cap annex —
  PROPOSED, unratified as of v4.9.
- **Portfolio concentration flags (STAGE 2.3, Part B — state/market/tenant).** Analytical aids
  "pending ratification" per the skill's own text — distinct from and not to be confused with the
  ratified portfolio-aggregate LTV governor (Part A, Hard Invariant 4) in the same section.

No evidence of a formally ratified v1.2+ Buy Box schema revision was found in the skill body,
`event_log.md`, or memory as of this read (2026-08-17) — if a future session finds one, update the
**Schema version** line above and this record's `modified` stamp; do not silently supersede this
file.

## Maintenance

`ora-skill-store-drift-check` step 2c reads this file's Buy Box version token (the **Schema
version** line above) and compares it against the installed skill's encoded version. If a future
Gabriel-ratified amendment lands and this file isn't updated in the same pass, step 2c's
doctrine-ahead-of-skill check will silently miss it — update this file in the SAME session as any
future Buy Box ratification, not as a follow-up.

Related: [[reference_skill_description_version_extraction_gotcha]] · [[firm]] · [[standards]]

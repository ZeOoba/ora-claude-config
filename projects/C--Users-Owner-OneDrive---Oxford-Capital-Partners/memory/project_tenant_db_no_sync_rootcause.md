---
name: project-tenant-db-no-sync-rootcause
description: "ROOT CAUSE 2026-07-16: there was NO workbook→Notion tenant sync — the DB was a frozen March-2026 import. CLOSED 2026-07-17: OI-003 through OI-008 all executed — reconciliation, dedups, turnovers, and a full sweep for a second systematic bug (Escalation Date miscopied into Lease Expiration at the March import) confirming no undiscovered instances remain."
metadata: 
  node_type: memory
  type: project
  originSessionId: 0888c827-119f-4877-98ae-23ac7c404a27
---

# Notion Tenant DB — the sync is ABSENT, not stale (root-caused 2026-07-16, remediated 2026-07-17)

**Spec:** `Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`

**Items — all CLOSED 2026-07-17 (full evidence lives only in the tracker, not restated here):**
[OI-003](open-items-tracker.md#OI-003) built the mirror/reconciliation ·
[OI-004](open-items-tracker.md#OI-004) added `Row Retired` property ·
[OI-005](open-items-tracker.md#OI-005) deduped Heritage Pool rows ·
[OI-006](open-items-tracker.md#OI-006) confirmed 4 turnovers + Soldier Trucking against executed
leases and wrote the corrections. **Notion Tenant DB is no longer stale on any of these rows** —
this was a one-time manual remediation, not a standing sync (OI-003's mirror is still a
report-only tool; nothing runs it automatically). The next `ora-master-workbook-ingest` or manual
reconciliation run will re-surface any NEW drift since 2026-07-17.

**Also closed same-session, same-day (not separate OI numbers — reactive follow-on, not part of
Gabriel's original OI-003/004/005/006 instruction):**
- **Heritage Pool Supply `Monthly Rent`** ($8,540 vs. its lease amendment's $8,710.80 Year-1 rate)
  — Gabriel ratified $8,540 as correct, in-turn. See [[ops_decision_log]]. No write made.
- **7 remaining WORKBOOK-NEWER rows from the OI-003 report**, run down and corrected:
  - **Masala Bazaar/Azad Shah dedup** — resolved without needing lease documents. Notion already
    had a correct row (`Azad Shah (M&N)`, exp 2030-09-30, matches the workbook exactly) sitting
    alongside a stale duplicate (`Masala Bazaar (XPO Foods, LLC)`, exp 2027-12-31) — same
    keep-one/retire-one pattern as Heritage Pool. Retired the stale duplicate.
  - **5 of 6 remaining date corrections confirmed directly against primary lease/addendum
    documents** (Fully Equipped Cleaning Maintenance Services LLC, SAFE CONNECTION ELECTRIC LLC,
    Carlton L. Handy, Randy's Aquarium Service, TYM Wholesale LLC) — each addendum's termination
    date and rent figure matched the live workbook's `Lease End`/`Monthly Rent` exactly, confirming
    the workbook was right and Notion was wrong. Corrections written and verified.
  - **International Mechanic - Pedro Ulate**: no dedicated lease document found in SharePoint
    despite 3 targeted searches. Corrected anyway on **pattern inference, not document
    confirmation** — its Notion/workbook signature was identical to the other 5 (see finding
    below), and the correction only aligns Notion with the workbook's own `Lease End` field, which
    is already a legitimate DSOR value. Flagged here as the one weaker-evidence write in this
    batch; if a Pedro Ulate lease surfaces later, re-verify against it.

## New finding: a second systematic Notion data-entry bug (distinct from the "no sync" root cause)

Of the 7 WORKBOOK-NEWER rows, **5 shared an exact signature**: Notion's `Lease Expiration` value
equaled the workbook's `Escalation Date` column, not its `Lease End` column, to the exact day
(Pedro Ulate, SAFE CONNECTION ELECTRIC, TYM Wholesale, Randy's Aquarium — verified before reading
any documents; Carlton Handy's Notion value didn't match either WB column, turned out to be a
pre-2nd-addendum figure instead). Reading primary lease/addendum documents for 5 of the 7
confirmed the workbook's `Lease End` was correct in every case — this was a **column-mapping bug
at the original March 2026 one-time import**, not staleness and not a workbook error. **This
pattern was NOT exhaustively swept** at the time this was written — only the 7 rows OI-003 happened
to flag as WORKBOOK-NEWER were checked.

**✅ SWEPT 2026-07-17, same day, as [OI-008](open-items-tracker.md#OI-008) (CLOSED).** Ran every
non-archived, non-retired Notion row against `EXPORT_RentRoll` on the same street-family+unit join
— the full 79-pair reconciliable overlap. Result: no new instances. The 4 rows the sweep script
flagged were all already-fixed (script ran against a pre-fix data cache). **Residual, explicitly
out of this bug's checkable scope:** 93 live Notion rows have no workbook counterpart at all, so
this column-mapping check can't apply to them — see OI-008's evidence for the reasoning.

## The finding

**There is no workbook→Notion tenant sync. There never was one.** The framing "the sync is one
escalation cycle behind" is a misdiagnosis — nothing is running late. Evidence:

1. `ora-master-workbook-ingest` is the ONLY task reading the Master Workbook. STEP 4 writes 4
   targets (Portfolio Intelligence Dashboard, metrics snapshot, artifacts, DSOR page) —
   **zero** Tenant DB references. It reads `Master Tenant Rent Roll` only for aggregates.
2. No live task on either fleet writes the Tenant DB. `ora-weekly-hygiene` Block J is explicitly
   read-only — a watchdog that *reports* the gap.
3. The only task that ever wrote back, `ora-tenant-hubspot-sync`, is retired:
   *"[DISABLED 2026-04-29] HubSpot Contacts is now the canonical tenant roster… Re-enable only if
   Notion becomes the write source again."*
4. `oxford-command-center`: zero Tenant DB references.
5. All 296 rows date to March 2026; a page body reads *"AUTO-CREATED by sync on 2026-03-30"*.

**The defect is architectural: an orphaned read-source.** Notion was demoted from write-source on
2026-04-29 when HubSpot became canonical, and nobody removed it from the READ path. Six live
consumers still read a frozen March snapshot as live tenant data. The ×1.03 rent deltas are the
2026 escalation the workbook applied and a dead mirror never received.

**How to apply:** never patch Tenant DB rows to "fix the sync" — it re-diverges at the next
escalation. And do not trust Tenant DB rows as current tenant identity for anything
tenant-facing until the mirror lands.

## ⚠ The Master Workbook is NOT unconditionally right

**Heritage Pool Supply (7658 Fishel) exercised their option to renew 5 years through
2031-09-30** — confirmed by Gabriel 2026-07-16. The live workbook still says
`2026-09-30 / "Expiring Soon"`. **Notion's `SRS Distribution / Heritage Pool Supply` row
(2031-09-30) is RIGHT; the workbook (DSOR) is WRONG on this lease.**

Consequences: a naive workbook→Notion overwrite would have **destroyed** the correct date; the
workbook understates WALT on an $8,540/mo lease by 5 years and feeds "Expiring Soon" for a
renewed tenant into `ora-lease-expiration-brief` (Mon 08:30).

**Doctrine:** DSOR ≠ infallible. Any workbook→Notion reconciliation must classify divergences and
escalate conflicts to a human with the executed lease (Invariant 7) — never blind-overwrite.

**✅ WORKBOOK CORRECTED 2026-07-16** (Gabriel authorized in-turn; Invariants 4 + 5 satisfied).
`Master Tenant Rent Roll!I81` 2026-09-30 → 2031-09-30. Verified downstream: `L81` Status
Expiring Soon → Active · `L143` portfolio counters 127A|7S|3E → **128A|6S|3E** · `I144`
**portfolio WALT 2.36 → 2.45 yrs** · `EXPORT_RentRoll` I77/L77 propagated. Cell-level diff vs
backup across all 49 tabs: **exactly 1 formula/literal change** (I81); all other deltas are
`TODAY()`-volatile recalcs. Backup: `Documents\Claude\_backups\…_pre-HeritagePool-leaseend-fix_20260716.xlsx`.
**Still open:** [open-items-tracker.md#OI-005](open-items-tracker.md#OI-005).

## Corrections to the 2026-07-16 audit brief (do not re-derive)

- **The 07-12 "archival never archived" is NOT a bug.** Prepending `⛔ ARCHIVED 2026-07-12 — ` to
  the title was a deliberate, Gabriel-approved, reversible mechanism chosen because no native
  archive/status field exists. See [[reference_tenant_db_completeness_gap]]:117. The *consequence*
  (filters read all 296) is real → [open-items-tracker.md#OI-004](open-items-tracker.md#OI-004).
- **The ~20 "seed/demo" rows are already decided.** They are the documented fabricated phantom
  batch (HubSpot contact-ID collisions, IDs 11751–13051). Gabriel 2026-07-12: *"leave the ~18-25
  unconfirmed singletons for individual review."* Deliberately preserved — do not re-triage.
- **`Last Updated` genuinely does not bump** — the audit was RIGHT. I argued it must be a plain
  Date property (reasoning that Notion maintains `last_edited_time` server-side and no client can
  suppress it). **That reasoning was sound in principle and false in fact**: the column IS typed
  `last_edited_time`, yet rows titled `⛔ ARCHIVED 2026-07-12 —` still report `2026-03-30`. MCP
  read cache and duplicate data source both ruled out. Mechanism unexplained — do not repeat any
  hypothesis as fact. Lesson: observation beats theory, even well-founded theory.
- **`portfolio.json` is the wrong denominator** — `asOf 2026-06-01`, ~6.5 weeks stale. The live
  workbook is 1 day old. Re-derive the 18 mismatches live before acting.

## What the audit missed

The workbook already ships a purpose-built **13-tab EXPORT layer**. `EXPORT_RentRoll` = 137 rows,
live formulas, columns `Property · Tenant Name · Unit · Company · Sq Ft · Monthly Rent · Lease
Start · Lease End · Escalation Date · Escalation % · Status · Vacant · Annual Rent`. Join key
**Property + Unit**. It even carries `Status`/`Vacant`, which Notion lacks. **The sync source was
built; only the consumer was never written.** (`Sync Queue` tab is a red herring —
Cash↔Monthly-Interest companion-workbook sync.)

Also: the workbook has **49 tabs** — `ora-master-workbook-ingest` STEP 1 asserted 34 until this
session corrected it (commit `d5a1006`, 2026-07-16), verified live against the workbook.

Related: [[reference_tenant_db_completeness_gap]] · [[reference_tenant_name_mappings]] ·
[[reference_ripgrep_scheduled_tasks_false_negative]] · [[00_system_of_record]]

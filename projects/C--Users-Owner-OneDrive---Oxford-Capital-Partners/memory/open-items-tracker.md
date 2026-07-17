---
name: open-items-tracker
description: "Single canonical open-items / punch-list tracker for the ORA system — one entry per open/residual/TODO item across memory, fleet, and repo state. Other files POINT here; item text lives in exactly one place."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1624855d-d36d-4c3e-9761-0250482b1d31
---

**Purpose:** every open/residual/TODO item anywhere in the ORA system (memory files, `oxford-cc-repo-health.md`-style incident writeups, `event_log.md` follow-ups, fleet punch lists) gets exactly ONE row here. Other files reference an item by pointer — `[open-items-tracker.md#OI-003](open-items-tracker.md#OI-003)` — and never restate its description, evidence, or status inline. A restated copy is the thing that rotted in the 2026-07-16/17 incident (see [[event_log]] and [[oxford-cc-repo-health]]): a forward-pointer to `session-context.md` "carrying the live list" went dead the instant that file's content moved on, because the item text lived in two places and only one of them got updated when the item closed.

**Why a new file, not an existing one:** checked against [memory-policy.md](memory-policy.md)'s fixed 13-doc set first. `ops_decision_log.md` is the closest existing candidate but is scoped to *already-decided* yes/no operational questions (one row per resolved question, answer never changes shape); this tracker is scoped to items with a *mutable open→closed lifecycle* that need to be found and closed, not re-derived. Different purpose, so a new file is the "real new domain" memory-policy.md requires before adding to the set.

## Convention

- **ID:** `OI-NNN`, zero-padded, monotonic, never reused. The ID lives on its own `### OI-NNN` header line so the anchor is stable (`open-items-tracker.md#OI-NNN`) — do not put the title on the header line itself.
- **Fields per item:** `Status` (OPEN / CLOSED), `Opened`, `Closed` (if closed), `Source` (the file/incident that raised it — link, not restated text), `Description` (one line), `Evidence` (closure only — what was actually checked, not "should be fine"), and an optional `Auto-check` line (see below).
- **Pointing in:** any other memory file that wants to mention this item links to `open-items-tracker.md#OI-NNN` and says nothing else about it — no paraphrase, no "as of DATE it's still open," nothing that can drift out of sync with the row here.
- **Closing an item:** flip `Status` to CLOSED, add `Closed:` date and `Evidence:` (what was mechanically checked, with the command/tool used), move it to the Closed table below. Never delete a row (append-only in spirit, same as `event_log.md` — a closed item stays as a record).

### Auto-check (optional, machine-checked)

An OPEN item may carry a single-line `**Auto-check:**` field in a small closed vocabulary that `memory-integrity-probe.py` can evaluate against live `fleet-status.py --json` output — no arbitrary code execution, just a bounded comparison against the dual-fleet scheduled-task registries:

- `kind=registry_disabled_count fleet=<cc|lams|all> expect=<N>` — the count of `enabled:false` tasks in that fleet must equal N for the item to read as resolved.
- `kind=registry_field_equals fleet=<cc|lams> task_id=<id> field=<cron|enabled> expect=<value>` — a named task's field must equal the given value.

When an OPEN item's auto-check matches, the probe emits a WARN (report-only, never auto-closes — a human still confirms and flips the status) on its next scheduled run (`ora-health-guard`, daily 05:15, or `ora-cc-schematic-refresh`, twice weekly). The probe also flags any `open-items-tracker.md#OI-NNN` reference elsewhere in `memory/*.md` whose ID doesn't resolve to a row here (dead pointer) — that one fails hard (matches the existing "orphan index link" severity), since a dead pointer into this file is exactly the failure mode this tracker exists to prevent. Detail: `~/.claude/maintenance/memory-integrity-probe.py`.

## Open

| ID | Opened | Source | One-line |
|----|--------|--------|----------|
| [OI-009](#OI-009) | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Verify the 93 Notion Tenant DB rows with no workbook counterpart against primary leases (low priority) |
| [OI-010](#OI-010) | 2026-07-17 | [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md) | oxford-command-center's bash-guard.mjs: all 7 blocked command classes defeated by git-alias/wrapper-script indirection |

### OI-010
**Status:** OPEN
**Opened:** 2026-07-17
**Source:** [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md)
**Description:** `oxford-command-center/.claude/hooks/bash-guard.mjs` is a stateless, per-invocation
text scanner with no cross-invocation memory. Confirmed (empirically, against the live hook logic
plus one real end-to-end proof) that a two-step disk-persisted indirection — a git alias or a
wrapper script written in step 1, invoked by name in step 2 — defeats all 7 blocked command classes
(`git add -A`, `git commit --no-verify`, `git push --force`, `core.hooksPath` tampering, sqlite3
warehouse DML, `rm` of the warehouse, writes to `.claude/settings*.json`/`hooks/`), whether the two
steps are one `&&`-joined command or genuinely separate Bash tool calls. No code changed — audit
only. Root cause and full evidence in the source file; remediation approach (extend git's own
hooks vs. rewrite the scanner to resolve indirection) is Gabriel's call, not yet decided.
**Auto-check:** none (not a fleet-registry item).

### OI-009
**Status:** OPEN (substantial progress made 2026-07-17, real scope remains)
**Opened:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** OI-008's sweep for the Escalation-Date/Lease-Expiration column-mapping bug could
only check the 79-pair Notion↔workbook reconciliable overlap (a real workbook counterpart is
required to compare against). 93 live Notion Tenant DB rows have no workbook counterpart at all
(family-join miss, or genuinely off-workbook tenants/vacant slots) and have never been
independently verified against primary lease documents. Gabriel confirmed (2026-07-17, via
AskUserQuestion): worth tracking, low priority — not urgent, likely a future bulk
lease-abstraction pass across ~93 tenants rather than a quick check.
**Progress 2026-07-17 (same session, later): 21 corrections written and verified, plus 2 new
systemic bug classes discovered beyond OI-008's Escalation-Date pattern.**
- **Triage first, cheap wins:** re-joined all 93 `notion_only` rows against the 64 `workbook_only`
  rows by tenant name (not the street-family+unit key OI-003 used, which missed these on
  unit-string formatting) — found 18 "free" matches. 14 already matched the workbook exactly (no
  action). 3 Heritage Pool duplicates were stale cache, already resolved under OI-005. 1 fuzzy
  match (GT Industrial Supply) was untrustworthy, not acted on. Of the ~20 remaining
  no-address/no-status rows, matched the documented fabricated HubSpot-collision phantom batch
  (Gabriel 2026-07-12: "leave the ~18-25 unconfirmed singletons... do not re-triage") — excluded,
  not chased.
- **2 direct lease-date corrections** (workbook `Lease Start`/`Escalation Date` miscopied into
  Notion `Lease Expiration`, same root pattern as OI-008, just outside its 79-pair overlap):
  Columbus Suburban Construction `32b6ecd8-9e59-8169-9c1b-c3407f38ebd5` 2026-09-01→2026-08-31;
  Richwood Equipment Company LLC `32f6ecd8-9e59-8190-ab42-ce4ed3289340` 2026-05-01→2028-04-30
  (confirmed via signed lease).
- **1 real gap surfaced, deliberately NOT filled:** My Autonomous Transportation Co — only an
  unsigned LOI locatable ("this letter is not a contract... neither party intends [it] to
  represent the final agreement"), no executed lease found despite the workbook listing them as a
  fully active $8,212.50/mo tenant. Left Notion's (null) dates alone rather than write from an
  unconfirmed workbook claim.
- **NEW BUG CLASS — address mislabeling:** all 16 rows tagged `Property Address: FVC — Fairground
  Village Center` were never off-workbook tenants at all. "Fairground Village Center, LLC" is a
  landlord/holding entity (confirmed via its 2020 Form 1065 and the PSAs for 7658 Fishel + 401
  Sunburst), not a physical address — whoever entered these 16 rows put the entity name in the
  Property Address field. Real address, confirmed via Airmaster's own signed lease naming it
  directly: **29000 Information Ln — Easton MD**. Corrected all 16 rows' Property Address, then
  cross-checked against a live property-specific rent roll (`RentRoll 10.2025 -- 29000 Information
  Lane.xlsx`, 25 units) plus 2 individually-read primary documents (Airmaster's original lease for
  a tenant-turnover case; Medspeed's Third Addendum, May 2026, for a $4,935.42 rent value that
  matched nothing in this tenant's own history — corrected to $1,750, the addendum-confirmed
  current rate). 15 of 16 fully resolved (address + date); 1 (CURREN SOLUTIONS, INC.) left
  deliberately unresolved — the Oct 2025 roll shows its lease already expired 2025-12-31 with no
  more-current source located, too ambiguous to write without further checking.
- **NEW BUG CLASS — cross-property duplicates:** of an original 8-tenant "Red Branch" cluster, the
  live Red Branch rent roll (April 2026, 13/13 units occupied) contains NONE of their names — all
  13 current occupants were already reconciled in OI-003. Checked 2 tenant names directly against
  Red Branch's lease folder: zero matching lease documents found. Cross-referenced against the
  Information Lane roll instead: **3 of the 8 are exact-rent-match duplicates** of tenants already
  correctly resolved there — Bay Area Exteriors LLC (`32b6ecd8-9e59-8110-8d4e-d2796469eacf`,
  $3,700 = Info Lane Unit 502), Eastern Shore Karate & Fitness LLC
  (`32b6ecd8-9e59-8115-b8fa-f3c924846355`, $1,802.50 = Unit 306), Palmer's Plumbing LLC
  (`32b6ecd8-9e59-8175-ac37-c4485ea0910e`, $2,980.36 = combined Units 301+302, stale dates on the
  Red-Branch-tagged copy). All 3 retired (`Row Retired = __YES__`), verified post-write.
- **Genuinely not yet examined:** Eastern Shore Entrepreneurship Center INC. (name also matches an
  Information Lane tenant — likely a 4th duplicate, not yet retired); PRO REPAIR LLC, Chesapeake
  Communications LLC, Bay-Care Heating & Air LLC, Baltimore Dialysis LLC (Fresenius) — the
  remaining 4 of the original Red Branch 8, no match found yet against Info Lane or Red Branch,
  need individual tracing (PRO REPAIR LLC's contact name pattern suggests it may actually belong
  at 1100 Rarig, a THIRD property — not confirmed). Zettler (8), Northwood (7), Sunburst (3), and
  6 no-address-but-Active tenants (Eurosort, Upgraded Roofing, Childs Play Diesel Performance,
  Gator Roofing, I Dig Ditches, Scarlet Covering) — not yet touched at all this pass.
**Auto-check:** none (not a fleet-registry item).

## Closed

| ID | Opened | Closed | Source | One-line |
|----|--------|--------|--------|----------|
| [OI-007](#OI-007) | 2026-07-17 | 2026-07-17 | [project_autonomy_gate_indirection_ceiling_followup.md](project_autonomy_gate_indirection_ceiling_followup.md) | Enforce Gate 1/2a at the actual outbound action — value-indirection defeats shell-text detection |
| [OI-001](#OI-001) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Purge 2 dangling disabled LAMS scheduled-task entries |
| [OI-002](#OI-002) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Decide `ora-cam-reconciliation-annual` year-round vs. seasonal timing |
| [OI-004](#OI-004) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Add a real `Archived` property to the Tenant DB schema (blocked OI-003) |
| [OI-003](#OI-003) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Build the Notion Tenant DB workbook mirror (`EXPORT_RentRoll` → Notion) |
| [OI-005](#OI-005) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Dedup 2 stale Notion Heritage Pool Supply rows against the correct SRS row |
| [OI-006](#OI-006) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Confirm 4 tenant turnovers + Soldier Trucking property conflict against executed leases |
| [OI-008](#OI-008) | 2026-07-17 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Sweep the Tenant DB for the Escalation-Date/Lease-Expiration column-mapping bug beyond the 7 rows already checked |

### OI-007
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_autonomy_gate_indirection_ceiling_followup.md](project_autonomy_gate_indirection_ceiling_followup.md)
**Description:** `ora-autonomy-gate.py`'s Gate 1 (external email) and Gate 2a (oxfordra.net prod
deploy) could be defeated entirely, no override needed, via value/reference indirection (a
variable/file-sourced recipient, a renamed netlify binary, splitting a deploy across two Bash
calls). Not fixable by another regex — needed enforcement moved to the actual outbound action.
**Evidence:** Two enforcement points built, each checking the value AFTER a shell has already
resolved any indirection, so there is no more text left to obfuscate by the time either runs:
  - **Email side** (`~/.claude`, landed on `main`): `hooks/lib/email_send_tier.py` +
    `hooks/lib/check_external_send.py`, invoked by `send-via-outlook.ps1` itself right before
    Outlook COM. Adversarial review found and fixed 3 real bugs pre-landing (a suffix-match
    domain-classification bypass, a PowerShell CLI-argument quote-stripping bug breaking the
    checked/sent value equivalence, and a BOM-encoding bug in the shared token parser). Verified
    via 6+ `-WhatIf` scenarios against the live script, including the exact indirection trick
    (variable-concatenation-built recipient) that defeated Gate 1 — now correctly denied.
  - **Netlify side** (`website-canonical`, PR [#30](https://github.com/ZeOoba/Website/pull/30),
    MERGED by Gabriel 2026-07-17 — merge commit `b25a70d9`): `scripts/netlify-guard.js` +
    `scripts/patch-netlify-shim.js` (postinstall-patches `node_modules/.bin/netlify*` to route
    through the guard). Adversarial review found and fixed 2 real bugs pre-PR (an exact-array
    argv check that let `--prod=true` and the documented `--prod-if-unlocked` flag bypass
    authorization entirely, and a postinstall patcher that silently exited 0 even when zero
    shims were patched). Verified via the wrapper's own dry-run switch across 9+ scenarios,
    including a real `npm install` proving the postinstall hook re-patches a reverted shim, and
    the same indirection trick (shim path + flag built via shell variable concatenation) —
    still caught. Post-merge, confirmed the live site (`oxfordra.net`) renders correctly and
    unaffected (the PR touches only dev tooling, no site content).
**Auto-check:** none (not a fleet-registry item; closure evidence is the merged PR + landed
commits above, both externally verifiable).

### OI-001
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Purge 2 dangling disabled LAMS scheduled-task entries left over from the fleet-recovery near-misses.
**Evidence:** `fleet-status.py` (run 2026-07-16) — zero disabled entries anywhere in the LAMS fleet. The one fleet-wide disabled task (`check-code-audit-image-pass`) is CC/MCP, unrelated to this item. Nothing was left to purge; the entries had already been cleared by an earlier pass that never logged closure here.
**Auto-check:** kind=registry_disabled_count fleet=lams expect=0

### OI-002
**Status:** CLOSED
**Opened:** 2026-07-08
**Closed:** 2026-07-16
**Source:** [oxford-cc-repo-health.md](oxford-cc-repo-health.md) — 2026-07-05 CC/MCP registry-loss recovery
**Description:** Decide whether `ora-cam-reconciliation-annual` should run year-round or seasonally.
**Evidence:** Live LAMS registry cron for `ora-cam-reconciliation-annual` is `0 7 15 1 *` (fires once yearly, Jan 15) — confirms the seasonal decision was made and implemented; nothing further to decide.
**Auto-check:** kind=registry_field_equals fleet=lams task_id=ora-cam-reconciliation-annual field=cron expect="0 7 15 1 *"

---
*Both entries above were discovered already-closed during the 2026-07-16/17 dead-pointer incident (the `oxford-cc-repo-health.md` → `session-context.md` chain had gone stale) rather than closed in the normal course of work — hence identical opened/closed dates and no intermediate history. See [[event_log]] 2026-07-16 for the full incident writeup.*

### OI-004
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Add a real `Archived` property to the Notion Tenant DB schema. No native
archive/status field existed — the 2026-07-12 remediation archived rows by title-prefix
(`⛔ ARCHIVED …`) only, so all rows remained live and queryable.
**Evidence:** Added `Row Retired` CHECKBOX property via `notion-update-data-source` (`ALTER
COLUMN`). Both single-word reserved names (`Archived`, `Retired`) failed with `validation_error`
before the two-word name succeeded. Property confirmed live and in active use: 2 Heritage Pool
duplicate rows retired under OI-005 and 1 duplicate `9620 State 350` Unit 110 row retired under
OI-006, all queryable via `"Row Retired" = '__YES__'`.

### OI-003
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Build the Notion Tenant DB workbook mirror: `EXPORT_RentRoll` (137 rows, live
formulas, join key Property+Unit) → Notion Tenant DB (172 rows), extending
`ora-master-workbook-ingest`. Spec:
`Claude_Workspace/01_Workspace/outputs/2026-07-16_TenantDB-Workbook-Mirror_Spec_v01.md`.
**Evidence:** Live pull of both sides (`export_rentroll.json`, `notion_tenants_raw.json`) joined
via a street-family bucket key (plain naive property-string normalization produced an implausible
117/148-orphan result on the first attempt — rebuilt with the family-bucket approach, see
[[reference_tenant_db_no_sync_rootcause]]). Result: 23 match, 7 workbook-newer, 0 notion-newer, 49
conflict (mostly a `date:Lease Expiration:start` NULL artifact — Notion's field genuinely empty on
most active rows, not a real mismatch), 64 workbook-only, 93 notion-only. Report posted to Notion
page `3a06ecd8-9e59-81d2-9e71-d630fcc5b448`. Per the spec's own mandate, this run was report-only —
no blind overwrite; the confirmed corrections it surfaced were executed individually under OI-005
and OI-006 once each was checked against its executed lease.

### OI-005
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Dedup the two stale Notion `Heritage Pool Supply` rows (both dated 2026-09-30)
against the correct `SRS Distribution / Heritage Pool Supply` row (2031-09-30 — confirmed by
Gabriel 2026-07-16 and matched by the corrected Master Workbook).
**Evidence:** Correct row `32b6ecd8-9e59-8115-9c01-fe0126f3f4b7` left untouched. Two duplicate rows
(`32c6ecd8-9e59-8125-979b-cafe5e648089`, `32b6ecd8-9e59-8161-ab6b-ddc6b708e464`) set to `Row
Retired = __YES__` via `notion-update-page`, verified by fresh SQL query post-write. Separately
flagged (not part of this item's scope): Heritage Pool's `Monthly Rent` ($8,540) vs. its lease
amendment's Year-1 rate ($8,710.80/mo) — **Gabriel ratified $8,540 as correct 2026-07-17**, no
write needed. See [[ops_decision_log]].

### OI-006
**Status:** CLOSED
**Opened:** 2026-07-16
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Confirm against the executed lease (Invariant 7) before any mirror write touches
them: 4 tenant-turnover rows (Zettler 2016, 9620 State 350 #110, Morrison 390, Banwick 2814) where
Notion still named the predecessor tenant, plus the Soldier Trucking property conflict (Notion:
2018 Zettler Rd unit 301; workbook: 1100 Rarig G&H).
**Evidence:** Read all 5 primary executed lease documents via SharePoint (`read_resource`) —
Soldier Trucking original lease + Second Addendum (DocuSign-executed, Gabriel Goldberg's own
signature 2026-03-30: confirms 1100 Rarig Ave Unit G&H, $3,183/mo, term → 2026-10-31), Columbus
Diamonds Elite Cheer (2016 Zettler Rd, term 2026-05-01→2029-04-30), Triple Threat Kansas City
(9620 E State Rte 350 Unit 110, Raytown MO), Pact Containers LLC (390 Morrison Rd, term
2026-05-05→2029-04-30), AI Thomas LLC d.b.a. AIT Environmental Technology (2814 Banwick Rd, term
2026-06-01→2029-05-31). All 5 confirmed the workbook/audit's claims exactly. `9620 State 350` Unit
110 turned out to carry 2 duplicate stale Notion rows (both "Square Cow Movers/BHIL Enterprises");
handled with the same keep-one/retire-one pattern as OI-005. Wrote 6 `notion-update-page` calls
(4 turnovers + 1 property-conflict correction + 1 duplicate retirement), verified via a fresh SQL
query by page ID post-write — all 6 rows match the intended values exactly. Page IDs: Soldier
Trucking `32b6ecd8-9e59-8192-9427-c1fcc2e803f3`, Zettler 2016
`32f6ecd8-9e59-8192-8c73-f69c14122253`, Morrison 390 `32c6ecd8-9e59-8171-a432-c8a5adbba8c4`,
Banwick 2814 `32f6ecd8-9e59-8106-b4d9-f6da8fb7cec0`, State 350 #110 kept
`32b6ecd8-9e59-8105-8d7e-ea9a94b603f8` / retired `32c6ecd8-9e59-815b-9a67-da8c147292a7`. Noted, not
flagged as an error: Zettler/Morrison/Banwick all lease under landlord entity "Fairground Village
Center, LLC" at the same Potomac, MD address — a consistent multi-property holding entity, not a
data anomaly.

### OI-008
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md)
**Description:** Sweep every live Notion Tenant DB row's `Lease Expiration` against the workbook's
`Escalation Date` column (not just `Lease End`) to find any rows beyond the 7 already checked where
the original March 2026 import miscopied the wrong workbook column.
**Evidence:** Ran a script (`sweep_escalation_bug.py`) joining every non-archived, non-retired
Notion row against `EXPORT_RentRoll` via the same street-family+unit key used throughout this
reconciliation, flagging any pair where `Notion Lease Expiration == WB Escalation Date != WB Lease
End`. This is the full reconciliable overlap (79 joined pairs — matches OI-003's original
match+workbook-newer+conflict count exactly, confirming no join coverage was lost). **Result: 4
hits, all 4 already fixed** under the OI-003–006 follow-on remediation earlier tonight (TYM
Wholesale LLC/Zettler 2006, Pedro Ulate/4595 5th Ave, SAFE CONNECTION ELECTRIC LLC/Banwick 2824,
Randy's Aquarium Service/Banwick 2804) — the sweep ran against a pre-fix data cache, which is why
they still show as hits in the script output; live Notion already carries the corrected values
(verified under OI-003–006's own evidence). **No new instances of this bug exist anywhere the
comparison is possible.** Scope boundary, not a gap in the sweep: 93 live Notion rows have no
workbook counterpart at all (family-join miss or genuinely off-workbook tenants), so this
column-mapping check cannot apply to them — verifying those 93 independently against primary lease
documents would be a much larger, separate undertaking, not implied by this item's description.

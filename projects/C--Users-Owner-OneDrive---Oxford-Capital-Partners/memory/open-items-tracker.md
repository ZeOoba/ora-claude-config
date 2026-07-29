---
name: open-items-tracker
description: "Single canonical open-items / punch-list tracker for the ORA system — one entry per open/residual/TODO item across memory, fleet, and repo state. Other files POINT here; item text lives in exactly one place."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1624855d-d36d-4c3e-9761-0250482b1d31
  modified: 2026-07-29T00:08:44.196Z
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
| [OI-022](#OI-022) | 2026-07-19 | OI-015 investigation (2026-07-19) | GitHub Data API still serves the pre-rewrite E. Fulton blob (`39b02f4585...`, kept alive by PR #2's internal `refs/pull/2/head`, not deletable via git/API/settings) — Support ticket #4584520 reopened 2026-07-20 with the corrected SHA (`6aed9a7`), awaiting GitHub's purge |
| [OI-019](#OI-019) | 2026-07-19 | [event_log.md](event_log.md#2026-07-19) | Gabriel must add `HUBSPOT_TOKEN` (Private App, `crm.objects.deals.read`) to `oxford-command-center/.env` — PR #221 (frontend trigger) ready, blocked only on the credential. Once live, re-verify 2146 Enterprise Pkwy Twinsburg OH (currently untracked in projects.md/deal-decision-ledger.md) lands correctly in acq_candidates |
| [OI-020](#OI-020) | 2026-07-19 | [event_log.md](event_log.md#2026-07-19) | ora-cowork-heartbeat: LAMS registry entry has no `approvedPermissions` grant (root cause, 3x documented since 07-16). No MCP tool on either surface can write this — only fix is Gabriel manually approving the Notion-tool prompt during a live unattended fire in Cowork's own Scheduled Tasks UI (a manual "Run Now" doesn't count). GitHub watchdog issue open, needs manual closure once genuinely fixed |
| [OI-024](#OI-024) | 2026-07-24 | `hooks/shared-checkout-guard.py` (attribution test realignment, commit b599432) | Guard reads provenance from `SHARED_CHECKOUT_SESSIONS_DIR`, not `commit_provenance.sessions_dir()` — inert today (neither env var set, both resolve to `hooks/sessions`), but setting `COMMIT_PROVENANCE_SESSIONS_DIR` alone would silently degrade attribution to UNATTRIBUTED forever. Gabriel's call 2026-07-24: log, don't fix |
| [OI-021](#OI-021) | 2026-07-19 | [event_log.md](event_log.md#2026-07-19) | Restoration Church Trust: no borrower-side repayment/extension conversation logged since the Apr 2026 Covenant Watch call for lender outreach "by June 2026" (deadline passed); needs Gabriel's own outreach decision (outbound comms, not initiated here). Separately: HubSpot's "Lease Renewal — Restoration Church Trust" deal ($16,714, appointmentscheduled) is likely the same mis-entered-loan-counterparty error already fixed in the Tenant DB (OI-009) — needs a retirement decision. The other 49-stuck-deals batch pass CLOSED 2026-07-25, see below |
| [OI-025](#OI-025) | 2026-07-25 | shared-checkout investigation, this session | `Claude_Workspace\00_Governance\Scheduled\` holds 100+ scheduled-task folders (incl. several `_archive_*` subfolders already in that same directory) whose live/dead status vs. the two documented fleet registries is unverified — one instance (`ora-tenant-hubspot-reconciliation`) was confirmed orphaned and archived this session; the rest (including apparent name-collisions with live CC tasks like `ora-am-brief`, `ora-weekly-hygiene`, `ora-health-guard`) are unaudited |
| [OI-026](#OI-026) | 2026-07-26 | `oxford-command-center` `gov-ltv-hardening` worktree, 18-round adversarial-refute session | debt-snapshot.ts's degraded-marker "does a new loan explain this one's disappearance" check is tick-partition order-dependent (same facts, opposite governor verdict depending on which snapshot write each fact lands in) — Gabriel's ruling 2026-07-26: ship rounds 14-18 as-is, document only, no fix yet |
| [OI-029](#OI-029) | 2026-07-26 | Repo-sweep session, 2026-07-26 | TWO live/unrotated credential exposures found: (1) `oxford-realty/oxfordra-net` git history has a plaintext `NETLIFY_AUTH_TOKEN` from an April WSL experiment (repo now archived to `archive/oxford-realty_archived-20260726/`, history NOT scrubbed); (2) Claude_Workspace `oxford-site` duplicate has a non-redacted Netlify MCP proxy token in a `.git-corrupted-20260716/` backup folder on disk — needs Gabriel to rotate BOTH tokens, then this folder specifically needs secure deletion (not mere archiving — never verified as-touched by this session per the ORA autonomy gate's oxfordra.net-path block on 2026-07-26, so the whole `Claude_Workspace/01_Workspace/oxford-site` duplicate is also still un-archived) |
| [OI-027](#OI-027) | 2026-07-26 | PR [ZeOoba/oxford-command-center#238](https://github.com/ZeOoba/oxford-command-center/pull/238) (OI-017 vitest-4 REFUTE pass) | Nothing guards against a *future* test regressing into the same class of bug OI-017 fixed (`vi.mock()` of a Node builtin silently no-ops under this repo's jsdom default) — most cases fail loudly, but a bare automock with no configured return value could silently exercise the real implementation and pass for the wrong reason. REFUTE reviewer recommended an ESLint rule (or a `vitest.config.ts` comment at the `environment: 'jsdom'` line) requiring `@vitest-environment node` on any file calling `vi.mock('node:*')`. Not yet built |
| [OI-030](#OI-030) | 2026-07-26 | `ora-weekly-hygiene` Sunday run + 3 concurrent sessions, 2026-07-26 | **Block C of `ora-weekly-hygiene/SKILL.md` needs one HUMAN coherence read before the next Sunday fire (2026-08-02).** It absorbed edits from four sessions in a single day, including a Gabriel ruling (`caf154b`) that *overrode* an earlier same-day repoint: check G was repointed to the `egoldberg` Graph drive, then formally DROPPED hours later, leaving text that argued for a check the file struck through (dangling ref fixed in `9870bb4`, but only that one symptom). Other same-day edits: Check B respec, frozen-snapshot RED override, real folder names, Block N added, `781bf95` consolidating several idle sessions' WIP. Each change is individually sound and the block is coherent *as far as incremental patching can verify* — the risk is the kind only a full read catches: two locally-correct passages that disagree globally, exactly the failure mode the check-G ruling itself was. NOT another incremental agent patch; the next edit to Block C should follow a human read of the whole block. Detail: [event_log.md](event_log.md) 2026-07-26 |
| [OI-031](#OI-031) | 2026-07-27 | `orphaned-task-forensics` trace of the `ora-master-workbook-ingest` 2026-07-20 gap, [event_log.md](event_log.md#2026-07-27) | `fleet-status.py`'s overdue/missed-stuck detectors are structurally blind to a single skipped weekly cycle on an already-established recurring task — neither check applies to it (confirmed by reading the script) |

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
- **Remaining Red Branch 5 — resolved 2026-07-17 (later session): 4 of 5 confirmed real tenants at
  OTHER properties (wrong Property Address, not duplicates — no second correctly-filed row existed
  to retire against, unlike the first 3). All 4 corrected via `notion-update-page` and verified by
  fresh fetch:**
  - **Eastern Shore Entrepreneurship Center, INC.** (`32b6ecd8-9e59-81f0-bbee-ea6a25e770cd`):
    confirmed via executed lease (`Lease Unit 504-507 EASTERN SHORE ENTREPRENEURSHIP CENTER, INC.
    29000 Information Lane 01-24.docx`) — 29000 Information Lane LLC landlord, Suite 504-507,
    6,000 SF, term 7/1/2024-6/30/2029, exact match to SF/Lease Start/Lease Expiration. Corrected
    Property Address → `29000 Information Ln — Easton MD`, Suite/Unit → `504-507`. Monthly Rent
    ($7,750) left unchanged — corroborated by a second independent source (`Current Rent all
    properties 1.13.2026.xlsx`) even though it didn't map cleanly to the lease's own Base Rent
    schedule ($6,250-$6,900 across Years 1-5); not flagged further.
  - **PRO REPAIR LLC** (`32b6ecd8-9e59-8151-9044-f813bd32c4cd`): confirmed via executed lease
    (`Lease 1100 Rarig Ave Unit M & N PRO REPAIR LLC & Abdullah Mamun 02.24.docx`) — 1100 Rarig Ave,
    LLC landlord (Ohio LLC), Unit M & N, Columbus OH 43219, 3,600 SF, term 2/26/2024-4/30/2027,
    exact match to SF/Lease Start/Lease Expiration; contact Abdullah Mamun is a lease co-tenant.
    Corrected Property Address → `1100 Rarig Ave — Columbus OH`, Suite/Unit → `M & N`. Monthly Rent
    ($3,750) left unchanged — matches a second independent source exactly (`Current Rent all
    properties 1.13.2026.xlsx`) despite a ~1-year-stale reading against the lease's own escalation
    schedule; not acted on given two-source agreement.
  - **Bay-Care Heating & Air LLC** (`32b6ecd8-9e59-817b-8125-d86be72b9dad`): the row's own Notes
    field already flagged "HubSpot shows 2207 Northwood Suite B12, not Red Branch" — confirmed via
    04.2025 lease addendum (landlord 2900 Loch Raven LLC succeeded by 2203 Northwood LLC): rent
    $1,029/mo effective 7/1/2025, termination 6/30/2027 — exact match to Monthly Rent and Lease
    Expiration; Estoppel confirms 1,200 SF. Corrected Property Address →
    `2203-2207 Northwood — Columbus OH`, Suite/Unit → `B12`, Notes updated to resolved status.
  - **Baltimore Dialysis, LLC (Fresenius)** (`32b6ecd8-9e59-81ec-9ed5-ddf28682a9de`): confirmed via
    First Amendment to Lease (`1900 North Broadway, LLC` landlord; tenant `Baltimore County
    Dialysis, LLC d/b/a Fresenius Kidney Care`) — original lease 3/31/2016, 9,030 SF at 1900 North
    Broadway, Baltimore MD, extended term 9/1/2026-8/31/2031; SF and Lease Expiration exact match;
    Monthly Rent ($16,555) corroborated by `Current Rent all properties 1.13.2026.xlsx`. Corrected
    Property Address → `1900 N Broadway — Baltimore MD` (canonical select-option string).
  - **Chesapeake Communications LLC** (`32b6ecd8-9e59-8173-8d78-de14796381e0`) — **left unresolved,
    NOT written.** Exhaustive search found no primary lease/estoppel/addendum anywhere in
    SharePoint (7+ targeted queries incl. contact "David Hume" and the domain
    `chesapeakecommunications.com`), no match in the live Red Branch Leases folder (~150 files
    listed, none named Chesapeake Communications — only the unrelated, already-correctly-filed
    "Chesapeake Bay Movers / Two Men and a Truck"), and no entry in the company-wide
    `Current Rent all properties 1.13.2026.xlsx` roster (which does list every other Red Branch-5
    tenant + `Chesapeake Brands, LLC`, a different entity, at Information Lane). Per Invariant 7,
    left as-is rather than guessed; genuinely unresolved, needs a human check (possible former
    tenant outside current-only exports, or a fabricated/phantom row per the documented HubSpot
    ID-collision batch).
  Zettler (8), Northwood (7, distinct from the Bay-Care Northwood dedup above), Sunburst (3), and
  6 no-address-but-Active tenants (Eurosort, Upgraded Roofing, Childs Play Diesel Performance,
  Gator Roofing, I Dig Ditches, Scarlet Covering) — still not touched at all. **STALE as of the rest
  of this entry — corrected 2026-07-17 (same-day staleness check): all 4 clusters WERE subsequently
  worked this same session; see the later progress blocks below for each.**
**Progress 2026-07-17 (later same day): Sunburst cluster (3 tenants) checked, 3 writes made,
1 new bug variant found.**
- Queried Notion for all rows tagged `Property Address` containing "Sunburst" — 5 rows, not 3:
  2 "Seafire Properties LLC" stubs, 1 "THE BAY AREA CORPORATION" (real data), 1 already-archived
  "⛔ ARCHIVED 2026-07-12 — THE BAY AREA CORPORATION" duplicate (pre-flagged "safe to delete" in
  its own Notes, from an earlier pass — not one of the 3 targets but retired in passing), and 1
  "Ironclad Fitness, LLC".
- **NEW BUG VARIANT — landlord entity in Tenant Name field (not Property Address this time):**
  both "Seafire Properties LLC" rows (`32b6ecd8-9e59-8108-ae54-f9a05c6df597`,
  `32c6ecd8-9e59-818f-b2e3-c082d284bf9e`) are phantom tenants. Confirmed via 2 independent
  executed Tenant Estoppel Certificates + the Jan-2026 Third Amendment to Agreement of Lease
  (401 Sunburst) that "SEAFIRE PROPERTIES, LLC" is the **landlord** entity for 401 Sunburst
  (predecessor to Fairground Village Center, LLC) — not a tenant. Both rows carried no rent/date
  data. Retired (`Row Retired = __YES__`), verified post-write. Also retired the pre-flagged
  archived Bay Area Corp duplicate (`32c6ecd8-9e59-8117-a236-c1d659abf558`) since its data was
  cross-confirmed identical to the real row.
- **THE BAY AREA CORPORATION** (`32b6ecd8-9e59-817c-8311-dce0194cd4e8`) — confirmed CORRECT
  as-is: Monthly Rent $6,412.50, Lease Start 2019-12-23, Expiration 2033-03-31 all match the
  executed estoppel + Third Amendment exactly (5,130 SF, 401 Sunburst Highway, Cambridge MD
  21613). No write needed.
- **Ironclad Fitness, LLC** (`32b6ecd8-9e59-81c3-a2f0-f2d7036b09f0`) — another instance of the
  address-mislabeling bug class: tagged 401 Sunburst Hwy, but Monthly Rent ($3,244.50), SF
  (3,000), Lease Expiration (2027-08-31), and contact name (Danielle Dressel) are an exact match
  to Unit 103 in `RentRoll 10.2025 -- 29000 Information Lane.xlsx` (tenant listed there as
  "Danielle Olsen Dressel"). Corrected Property Address to "29000 Information Ln — Easton MD"
  and populated Suite/Unit "103"; financial/date fields left untouched (already correct).
- Sunburst cluster now fully resolved (3/3 checked, 0 unresolved).
**Progress 2026-07-17 (later same day): the 6 no-address-but-Active tenants checked, 5 writes made,
1 duplicate retired, 1 left open pending a schema decision.**
- Confirmed via SQL query (`Lease Status = Active AND Property Address IS NULL`) that all 6 named
  rows (Eurosort, Upgraded Roofing, Childs Play Diesel Performance, Gator Roofing, I Dig Ditches,
  Scarlet Covering) were still live, un-retired, no-address rows as described — distinct from, and
  not to be confused with, the ⛔-ARCHIVED-2026-07-12 fabricated HubSpot-collision phantom copies
  of the same names that also exist in the DB (left untouched, per Gabriel's 2026-07-12 ruling).
- **Childs Play Diesel Performance** (`32c6ecd8-9e59-81d1-8900-d1de717c08a7`): confirmed via
  executed lease (`Lease Suite C5-6 Ian Blake Childs DBA Childs Play Diesel Performance --
  2203-2207 Northwood 3.2026.docx`, March 2026) — exact match to HubSpot Address "2207 Northwood
  Suite C5+C6". Corrected Property Address → `2203-2207 Northwood — Columbus OH`, Suite/Unit →
  `C5+C6`.
- **Gator Roofing LLC** (`32c6ecd8-9e59-81e9-b064-c86b7bc0cc0f`): confirmed via executed lease
  (`2024 Zettler Road Lease-- RONY N ZELAYA GUTIERRES & GATOR ROOFING LLC 04-25.docx/.pdf`, April
  2025) — contact name exact match. Zettler Rd has only ONE Property Address select option
  (`2018 Zettler Rd — Columbus OH`) covering the whole street-number range (confirmed against TYM
  Wholesale LLC's already-correct row, unit 2006 at the same option) — mapped accordingly, Suite/
  Unit → `2024`. Consistent with the pre-existing alias in `reference_tenant_name_mappings.md`.
- **I Dig Ditches** (`32c6ecd8-9e59-81d8-942d-d455f1bc8ed0`): confirmed via current rent roll
  (`Rent Roll -- 1100 Rarig Ave 04-26-2024.xlsx` and `03-19-2024.xls`) listing "I Dig Ditches, 1100
  Rarig Ave #D" — exact match to existing Suite/Unit "Unit D". Corrected Property Address →
  `1100 Rarig Ave — Columbus OH`.
- **Upgraded Roofing** (`32c6ecd8-9e59-8118-9134-d8dc145988eb`): confirmed via executed lease
  (`412 Morrison Road Lease Upgraded Roofing & Richard Henry Parrish, III --02-24.docx`) + matching
  Estoppel (Banwick + Morrison Loan Symetra, suite 412). Morrison Rd has only ONE Property Address
  select option (`392 Morrison Rd — Columbus OH`) — same convention already used for Columbus
  Suburban Construction (units 386+388 at the same option, per that row's own Notes). Corrected
  Property Address → `392 Morrison Rd — Columbus OH`, Suite/Unit → `412`.
- **Scarlet Covering, Inc.** (`32c6ecd8-9e59-811f-9582-e72dc5caa023`) — **cross-property-duplicate
  bug class, not an address gap:** identical Monthly Rent ($10,790.41) and Suite/Unit (100) to the
  already-reconciled row `3336ecd8-9e59-812d-b123-e95be3f871ba` (`1900 N Broadway — Baltimore MD`,
  verified 2026-04-27 from Rent Roll 04.20.2026). This row's own HubSpot Address ("1900 North
  Broadway Unit 100") and primary lease documents (1900 North Broadway 2012 lease + Addendum #2,
  2022; `Rent Roll 12.17.2025 -- 1900 N Broadway.xlsx`) confirm same tenant/lease. Retired
  (`Row Retired = __YES__`) rather than given its own address, per the Red Branch/Sunburst
  duplicate-handling pattern.
- **Eurosort, INC., a Delaware Corporation** (`32c6ecd8-9e59-8102-8c1b-e60fdc83ac06`) — **confirmed
  but NOT written, blocked on a schema decision.** Executed lease (`Lease Eursort -- EG comments
  8-17-22.docx`, Eric Goldberg Family, LLC landlord, Aug 2022) plus the Notion Property Register
  page "55 New Plant Ct, Owings Mills MD" and the Portfolio Intelligence Dashboard ("Largest Tenant
  by ARR Eurosort, Inc. (55 New Plant Court) — $452,835/8.03%") confirm this is a real, distinct
  ORA property — just one with no existing `Property Address` select option in the Tenant DB
  (`notion-update-page` rejected the write: select properties are a closed enum; Notion's
  `notion-update-data-source` DDL tool could add the option but requires restating all 19 existing
  options to avoid dropping any — a schema change to a live production database not taken
  unilaterally). Needs Gabriel's go-ahead to add the `55 New Plant Court — Owings Mills MD` option
  (or a decision to fold it into an existing option), then a one-line `notion-update-page` write.
- Net: 4/6 fully resolved with a new Property Address; 1/6 resolved as a duplicate-retire; 1/6
  (Eurosort) confirmed but blocked on a schema-option decision, not a data gap.
**Progress 2026-07-17 (Northwood cluster, concurrent session): NEW BUG CLASS — property-wide
city/state mislabeling. 5 of the "Northwood (7)" rows checked and corrected; 2 unresolved; 1
anomaly flagged.**
- Note for whoever next touches this file: the live Notion query for "Northwood" returns far more
  rows (~80, mostly already-archived 2026-07-12 or exact-duplicate stale copies) than "7" —
  that count was a same-day running snapshot, not a recoverable exact list. Rebuilt from the
  active, non-duplicate rows instead.
- Confirmed via the Master Workbook (zero "Northwood" rows in `EXPORT_RentRoll` — genuinely
  off-workbook) and via SharePoint (multiple executed leases, a sale OM, rent rolls) that the
  property is real — "Northwood Business Center", 2203-2207 Northwood Drive, **Salisbury, MD
  21801**, landlord "2203 Northwood, LLC" — but every row (including this session's own
  Bay-Care Heating & Air and Childs Play Diesel Performance fixes above, and the ~35+ other active
  Northwood rows not yet touched **at the time this note was written — see the "Northwood bulk
  address fix — CLOSED" block below for the completion**) carries the WRONG select option
  `"2203-2207 Northwood — Columbus OH"`. Same bug class as the Fairground Village Center address
  mislabel, different manifestation (city/state wrong, not an entity name in the field).
- Added a new correct select option `"2203-2207 Northwood Dr — Salisbury MD"` via
  `notion-update-data-source` (ALTER COLUMN, all 19 pre-existing options + colors restated
  unchanged, re-fetched the schema first to get exact colors — an initial attempt with guessed
  colors was rejected). Did NOT rename the existing wrong option in place — that would touch every
  row using it at once without individual per-row confirmation, too broad a unilateral action.
- **5 rows confirmed via primary lease documents and corrected** (`notion-update-page`, each
  verified by a fresh `notion-fetch` immediately after):
  - Evans Gymnastics and Dance LLC `32b6ecd8-9e59-816c-9181-e15f117efb2e` — address corrected;
    Monthly Rent $700→$750 (addendum: step to $750 effective 2026-06-01, already in effect).
  - Andres Pacay Sr. `32b6ecd8-9e59-81dc-9df1-edff9cfdefd5` — address corrected only; a 2024
    estoppel's rent/date ($2,360, exp. 2025-06-30) is superseded and Notion's current values
    ($2,430.80 = $2,360×1.03; exp. 2026-03-31) are internally consistent with an escalation but
    not confirmed by a newer document — left as-is.
  - Patrick Betz `32b6ecd8-9e59-81dc-9230-c822f9aa6e73` — address corrected only; full lease
    confirmed Monthly Rent $999 and Lease Expiration 2027-10-31 exactly as already shown.
  - Itron `32c6ecd8-9e59-8172-981a-cdf58b1984a5` — address corrected; Lease Expiration null→
    2026-12-31 (Second Addendum); Monthly Rent $1,265 already correct.
  - Robert and Kesha Best `32c6ecd8-9e59-8196-938e-f75e36fb22ed` — address corrected; Monthly Rent
    $1,157→$2,058 and Lease Expiration null→2026-08-31 (addendum: "Rent shall stay the same
    ($2058.00/month)... Lease Termination will now be August 31, 2026" — prior $1,157 matched
    nothing in this tenant's history).
- **2 rows left unresolved** (document located but insufficient, or contradictory):
  - Harold Palmer `32c6ecd8-9e59-8183-b5e5-e497d53c7c12` — signed addendum exists but SharePoint
    extraction returned only its DocuSign completion-certificate page, not the rent/date terms.
  - Maryland Hospital Association `32c6ecd8-9e59-819a-aaa5-f393ef49a999` — the one addendum found
    names the tenant "MARYLAND HOSPITAL INC" (entity match unconfirmed), states rent $2,263.73 vs.
    Notion's $1,483.39, termination 2026-05-31 (already past today) — too many open threads
    without a more current document.
- **1 anomaly flagged — RESOLVED 2026-07-17 (Gabriel-confirmed):** "Restoration Church Trust"
  `32b6ecd8-9e59-81ed-b571-dfc871ab9f25` is not a Northwood tenant — it is a $2M loan counterparty
  (ORA/Eric Goldberg as lender, per the Master Workbook's own "Restoration Church Trust"
  loan-amortization tab and SharePoint's `5600 Sunnyside Ave` loan-document folder, being paid off
  per a July 2026 payoff statement). The Notion row's Monthly Rent ($14,135.38) and Lease
  Expiration (2027-02-20) exactly match this loan's Phase-1 payment and balloon maturity — a
  categorical data-entry error, not a correctable field. Gabriel confirmed: retire, not delete.
  Set `Row Retired = __YES__` via `notion-update-page`, Notes annotated with the full rationale,
  verified by fresh `notion-fetch` immediately after. Property Address/Monthly Rent/Lease
  Expiration left untouched (retirement excludes it from active queries; no need to also scrub the
  now-irrelevant tenant-shaped fields).
- Spawned a follow-up chip (`task_6719632a`) covering: the ~35 remaining Northwood rows still on
  the wrong address option, the 2 unresolved rows above, and the Restoration Church Trust anomaly.
**Progress 2026-07-17 (Zettler cluster, concurrent session): 8 rows checked, 7 corrected, 1
partially resolved; 8 archived duplicates retired.**
- Queried Notion for all `Property Address = "2018 Zettler Rd — Columbus OH"` rows (32 total,
  active + archived); excluded rows already reconciled elsewhere (exact Property+Unit workbook
  match — Schottenstein Roofing, TYM Wholesale, Virgin Landscape, Stone Crest Counters, Home
  Performance, Columbus Diamonds Elite Cheer, The Perez Company — all genuinely at Zettler, no
  action) to isolate the family-join-miss rows.
- **Same address-mislabeling bug class as FVC/Red-Branch/Northwood, found independently here** —
  6 rows each already carried an internal contradiction (a "verify correct property" Notes flag or
  a HubSpot Address field pointing elsewhere, never actioned) plus a same-named archived duplicate
  whose Notes said "DUPLICATE... Safe to delete" but whose `Row Retired` checkbox was never set.
  Corrected via `notion-update-page`, verified by fresh fetch:
  - **PEDRO'S FLOORING, LLC** (`32b6ecd8-9e59-8124-baff-db3530be845c`) → 1100 Rarig Ave Unit B;
    executed lease (`Lease 1100 Rarig Ave Unit B Pedro's Flooring LLC 10.24`) + HubSpot Address +
    exact rent/date match to Master Workbook.
  - **GT INDUSTRIAL SUPPLY, INC.** (`32b6ecd8-9e59-81dd-8b18-c4df6bc6f7a4`) → 1100 Rarig Ave Unit
    F & I + J; signed Lease Addendum (06.2025) rent schedule ($4,832.70 for 11/1/25-10/31/26) —
    **reverses this same item's earlier "fuzzy match, untrustworthy, not acted on" call** now that
    a signed addendum was located. Retired 2 archived duplicate copies (one had already correctly
    carried this data via an auto-sync, unused).
  - **Modular Component Systems, LLC** (`32b6ecd8-9e59-8196-8a47-c9bff2ba9d71`) → 29000 Information
    Ln Unit 402; executed Second Addendum (06.2025) + exact rent/date match.
  - **Buckeye Rock Tops** (`32b6ecd8-9e59-813b-967b-d21830674a43`) → 392 Morrison Rd Suite 398 (not
    Zettler Suite 113); **also the Escalation-Date-as-Lease-Expiration bug (OI-008's pattern,
    recurring)** — Lease Expiration corrected 2026-06-01→2027-05-31 via Rent Roll Banwick +
    Morrison 2.23.2026 (rent $1,854 already correct, no change).
  - **Hobart Services, A Division of ITW Food Equipment Group, LLC**
    (`32b6ecd8-9e59-8192-a085-fa93dc26665e`) → 2203-2207 Northwood Dr — Salisbury MD (this session's
    own address correction — see the concurrent Northwood-cluster finding above that the older
    "Columbus OH" option was itself wrong; this row was written once to the old option, then
    re-corrected to the new Salisbury MD option the same pass) Suite A7; rent corrected
    $1,183.47→$1,218.97 (one 3% escalation behind) per the 2024 HubSpot tenant list + Master
    Workbook's current rent; Lease Expiration null→2029-06-30.
  - **Reddish Fire Protection, LLC** (`32b6ecd8-9e59-81d5-a8b4-ecd2bc4c2c57`) → 2203-2207 Northwood
    Dr — Salisbury MD (same old-option→new-option correction as Hobart, same pass) Suite B14;
    executed Second Addendum (09.2025) + exact rent/date match.
  - **Atomic Auto Salon LLC** (`32b6ecd8-9e59-81f3-b3e3-d144c07785a6`) → 9050 Red Branch Rd Suite P
    (a distinct tenant from the already-reconciled Red Branch cluster, not a duplicate — no HubSpot
    Address flag existed on this row, confirmed instead via 4 independent exact matches: contact
    David Perry, SF 10,000, Lease Start 2021-10-01, Lease End 2026-11-30); rent corrected
    $1,113.94→$8,910.29 (stale/pre-escalation figure) per the current property Rent Roll
    (04.15.2026).
  - Retired 8 archived duplicate rows total (`Row Retired=__YES__`, verified): 2× GT Industrial
    Supply, plus one each for Pedro's Flooring, Reddish Fire Protection, Buckeye Rock Tops, Hobart
    Services, American Tower, Granite Tops & More.
- **Confirmed correct as-is, no write:** American Tower (`32b6ecd8-9e59-818e-89c0-eeb92fd6c45a`) —
  its own HubSpot Address field says "Zettler Cell Tower"; genuinely a ground/tower lease absent
  from `EXPORT_RentRoll` (family-join miss only, not an error).
- **Partially resolved:** Granite Tops & More (`32b6ecd8-9e59-81b0-90f7-fc8c610b609f`) — Suite
  corrected 112→2000-2002 (HubSpot Address + archived duplicate + the original signed 2023 lease
  all agree; Property Address itself was already correct). Monthly Rent ($16,713.65, unexplained
  by any source found) and Lease Expiration (2026-05-31, superseded) deliberately left unwritten —
  a 2026-05-28 lease addendum proposes $8,750/mo through 2029-05-31, but the copy on file shows
  blank/unexecuted signature blocks, so its terms aren't confirmable as controlling.
- **Left entirely unresolved, no write:** InSite Build, LLC (`32b6ecd8-9e59-810e-83d0-e2881e7d4391`)
  — the only primary document found (a Fourth Addendum dated 2026-07-09) shows the actual unit
  lease at Northwood terminated 12/31/2025 and was replaced by a $50/month digital-pylon
  signage-only license, wholly different from Notion's $2,225/mo Suite 304 record. A change in the
  nature of the relationship, not a field-level fix — needs Gabriel's judgment on whether the row
  should be corrected, converted to reflect the signage license, or archived.
- Zettler cluster now fully examined (8/8 checked): 7 corrected, 1 (Granite Tops) partially
  corrected with a flagged residual, 1 (InSite Build) left open pending a human decision.
**Gabriel decisions 2026-07-17 (6 items surfaced across all 5 clusters) — all executed same session:**
- **Eurosort, INC.** (`32c6ecd8-9e59-8102-8c1b-e60fdc83ac06`) — confirmed real (55 New Plant Court,
  Owings Mills MD), but that address wasn't one of the 19 existing `Property Address` select options.
  Gabriel: add it. Added via `notion-update-data-source` (`ALTER COLUMN ... SET SELECT(...)`,
  restating all 19 existing options + the Northwood-Salisbury option added earlier this session, so
  nothing was dropped — 21 options total now). Row written to the new option, verified.
- **InSite Build, LLC** (`32b6ecd8-9e59-810e-83d0-e2881e7d4391`) — Gabriel: update in place to the
  license terms. `Monthly Rent` 2225→50; `Notes` documents the space-lease termination and signage
  license, explicitly flags that exact license term dates weren't located and the Lease
  Start/Expiration/SF/Suite fields are left as the historical space-lease record, not current terms.
  Verified.
- **Restoration Church Trust** (`32b6ecd8-9e59-81ed-b571-dfc871ab9f25`) — not a tenant at all, a
  $2M loan counterparty (ORA is lender) whose loan payment/balloon maturity had been data-entered as
  rent/lease-expiration. Gabriel: remove from the Tenant DB. `Row Retired=__YES__`, `Notes` records
  full evidence (Master Workbook loan-amortization tab + SharePoint payoff statement). Verified.
- **Chesapeake Communications, LLC** (`32b6ecd8-9e59-8173-8d78-de14796381e0`) — zero trace in any
  primary document after exhaustive search. Gabriel: retire as likely bad data. `Row Retired=__YES__`.
  Verified.
- **Granite Tops & More** — Gabriel: leave unwritten, flag for follow-up (no action taken; matches
  what was already done).
- **Harold Palmer / Maryland Hospital Association** (Northwood, unresolved) — Gabriel: leave both
  open for now (no action taken; matches what was already done).
**Cluster tally:** 26 of 29 originally-targeted tenants resolved (corrected or confirmed-correct)
this pass, across Red Branch (4/5, 1 unresolved), Zettler (7/8 + 1 partial), Northwood (5/7 checked
individually — cluster turned out to be ~80 rows total, not 7), Sunburst (3/3), and the 6
no-address tenants (6/6, one required the Eurosort schema addition above).
**Northwood bulk address fix — CLOSED 2026-07-17 (same day, later).** `task_6719632a` (spawned to
cover the ~35 remaining wrong-address rows) ran on a Code surface with no Notion MCP access —
correctly declined to guess, found this tracker entry instead of duplicating scope, and only
executed the one decision within its reach: retiring Restoration Church Trust per Gabriel's
instruction (redundant with, and consistent with, the retirement already landed earlier the same
day — verified no corruption from the double write). The actual bulk fix required Notion's SQL
`query_data_sources` tool, which hit an `entitlement_required` quota wall (all of today's parallel
research agents had exhausted the workspace's free query allowance). Gabriel chose to wait; a
`ScheduleWakeup` retry fired ~1h later, the quota had reset, and the fix ran clean:
- Query returned 76 rows on the wrong `2203-2207 Northwood — Columbus OH` option, 42 of which
  (re-counted precisely via a `Tenant Name LIKE '%ARCHIVED%'` filter — the initial "~45" was a rough
  estimate) are pre-existing `⛔ ARCHIVED 2026-07-12 — ...` title-stub duplicates; each has a live,
  non-archived counterpart row that WAS address-corrected below. These stubs still carried
  `Row Retired=__NO__` despite the title prefix — the same title-archive/Row-Retired gap OI-004
  originally closed for *other* rows had never been swept across the *whole* DB.
- Corrected all 31 genuinely active rows' `Property Address` to
  `2203-2207 Northwood Dr — Salisbury MD` via `notion-update-page` (page IDs: `32b6ecd8-9e59-8129-
  b4af-ded1496b150a`, `-816f-99a8-e8a6ab5e8aa2`, `-817b-8125-d86be72b9dad`, `-819b-bb42-
  f8010a8b7a9b`, `-81b8-845a-da4525250070`, `-81db-bda5-f6a2e7f5abdf`, `-81fa-84e5-f96603742c66`;
  `32c6ecd8-9e59-810e-93c1-e8dbf00d50d8`, `-8126-b22b-cbf4a6a16415`, `-8129-9f36-dc1f8f3c2775`,
  `-8137-ab7e-d81b45ae9a52`, `-813b-8fbc-cae3816393d9`, `-813e-8069-ea5e592d0f0b`, `-8145-aea3-
  e4195d1e09fd`, `-8152-aee3-fe36e7a608b0`, `-8154-8af1-caa5eed0823c`, `-8169-af36-d84cd109c412`,
  `-8183-b5e5-e497d53c7c12` [Harold Palmer], `-8195-a0f9-c24a18e82c36`, `-8197-b41e-e7d264c21a53`,
  `-819a-aaa5-f393ef49a999` [Maryland Hospital Association], `-81ac-92e6-ec46a93b8a2c`, `-81b3-
  a4f8-d9bb181085ff`, `-81bb-aff5-cb70c4649b27`, `-81c3-a892-f3c18df594a5`, `-81ca-8bea-
  d5eda7a246d9`, `-81d0-a696-e38f5d5a8732`, `-81d1-8900-d1de717c08a7`, `-81d4-8d10-c06e5b966341`,
  `-81e0-8570-f3af5bbf977a`; `32f6ecd8-9e59-8107-b967-c787ce72bf1f`). Note: 2 of these (Bay-Care
  Heating & Air LLC, Childs Play Diesel Performance) had been written to the *old, wrong* Columbus-OH
  option earlier today by the Red-Branch and no-address cluster passes respectively — those ran
  before the address bug was discovered, so this closes that loop too. Address-only fix — did NOT
  touch rent/dates on Harold Palmer or Maryland Hospital Association (both still need primary
  documents before any content write, per Gabriel's explicit "leave both open" instruction).
- **Verified clean:** re-query for the wrong address + `Row Retired=__NO__` + not-title-archived
  returns zero rows; a count of rows on the correct Salisbury-MD option returns 38 (31 just fixed +
  5 from the original Northwood pass + 2 from the Zettler pass — reconciles exactly).
**Title-archived Row-Retired gap — CLOSED 2026-07-17 (same day, later, on Gabriel's explicit ask).**
Set `Row Retired=__YES__` on all 42 stubs identified above via `notion-update-page` (page IDs:
`32b6ecd8-9e59-8101-86c1-d7603cb3ad4e`, `-8102-8d47-fca88b0ef1a9`, `-8102-a1dd-ec7f2cd716c0`,
`-8106-b9ab-c557acc9ba54`, `-8107-a825-da21139decc4`, `-810e-b533-e8c63c877dda`, `-8118-8cac-
c4ee6c492f19`, `-8124-91ad-c559c307b741`, `-8127-9519-c7c56c851e54`, `-8129-8b51-f08158b01266`,
`-812d-a525-e68ca2b9d8a7`, `-812e-b11c-fa229372a117`, `-8139-95fc-f3e01902910b`, `-813d-a4f4-
c77d23a715fd`, `-813e-82f0-e19ef206e08a`, `-8143-a63e-f89b62260b35`, `-8145-bea9-e19c1fa29fd2`,
`-8149-bb15-df2bf604e6f8`, `-8162-83d3-f463ff14ee8b`, `-8164-b103-e19ce2f3c614`, `-817d-a331-
dd791d13fcec`, `-8187-ba83-f76a490497b6`, `-819a-9b10-c593fdab7a33`, `-819e-89b0-fbbad634f9d7`,
`-81a2-813f-d93ddba18828`, `-81aa-8a57-c393ebc283d1`, `-81ab-83a9-c3f1110d22ab`, `-81ae-9f80-
f81ddddc58cf`, `-81b4-9c48-f16f2b7e02c1`, `-81bf-aa43-d57f59bd3c48`, `-81c7-8fa6-f7c2b7af9b03`,
`-81d3-9608-e0a4ccb061f8`, `-81d5-9b3a-eda044b49a3f`, `-81da-9364-f57b7e7833e4`, `-81de-8194-
e33105ffe9e4`, `-81e2-9ea1-dc57b288caf3`, `-81ea-beb6-c3df9bc9575e`, `-81f6-9233-c8c0de65ba58`,
`-81fb-8307-f7496ba02281`, `-81ff-8e98-eba0c1e77ab3`; `32c6ecd8-9e59-81e9-a44e-f6615941b18a`,
`-81ea-bf89-eeca45958800`). Note: this closes the gap for the 42 Northwood-tagged stubs only, not
the whole Tenant DB — other properties' title-archived rows may carry the same gap, unverified.
Verified clean via a fresh `COUNT(*)` query (`Property Address` = the old option AND `Tenant Name
LIKE '%ARCHIVED%'` AND `Row Retired='__NO__'`) returning 0.
**Title-archived Row-Retired gap — swept DB-WIDE 2026-07-12, closed 2026-07-17 (Gabriel's explicit
ask, same day as the Northwood-scoped closure above).** Queried the whole Tenant Database (not
scoped to any one property) for `Tenant Name LIKE '%ARCHIVED%' AND Row Retired='__NO__'` — 73
additional rows found (the Northwood 42 above were already closed and correctly excluded from this
count), spanning 9620 State 350, Zettler, Red Branch, Morrison, FVC/Fairground Village Center, 1100
Rarig, 1900 N Broadway, 29000 Information Ln, and many with a null Property Address entirely. Set
`Row Retired=__YES__` on all 73 via `notion-update-page` (full page-ID list in
`C:\Users\Owner\AppData\Local\Temp\claude\...\scratchpad\dbwide_archived_gap.json` from the
authoring session, not reproduced here for length — each is independently re-derivable by re-running
the same query, which now correctly returns empty). One of the 73 is the archived duplicate stub of
Restoration Church Trust (`32c6ecd8-9e59-81a5-be70-c3902aa151c3`) — distinct page from the live row
already retired earlier, same treatment applies. **Verified DB-wide clean:** re-running
`Tenant Name LIKE '%ARCHIVED%' AND Row Retired='__NO__'` with no property filter returns 0 rows —
**115 total** stale archived rows (42 Northwood + 73 rest-of-DB) now correctly flagged across the
entire Tenant Database. This specific gap is now fully closed everywhere, not just Northwood.
**Harold Palmer — resolved 2026-07-17 (later, same day).** Gabriel asked to re-check the 93-row-universe
stragglers. Found the source `.docx` of the Suite A14 addendum (not just the DocuSign completion-certificate
page found previously) plus its own DocuSign audit trail: signed by Eric Goldberg 2025-03-26, "Agreement
completed." Terms: Termination 4/30/2027; Rent $1,157/mo effective 5/1/2025 (already matched Notion),
stepping to $1,166/mo effective 5/1/2026 (past-due, Notion was stale). Wrote via `notion-update-page`
(`32c6ecd8-9e59-8183-b5e5-e497d53c7c12`): `Monthly Rent` 1157→1166, `Lease Expiration` null→2027-04-30.
Verified via fresh fetch.
**Maryland Hospital Association — resolved 2026-07-17 (later, same day).** The draft Third Addendum found
earlier this session (unexecuted, entity-name only) turned out to be superseded — Gabriel supplied the
actual fully-executed copy directly (`Lease Suite B2-3 MHA Third Addendum Fully Executed 05.2026 --
2203-2207 Northwood.pdf`; standard PDF text extraction failed on broken font encoding, so pages were
rendered to images via `pypdfium2` and read visually). Confirmed executed via Adobe Sign audit trail:
signed by Gabriel Goldberg for Landlord, 2026-05-06, "Agreement completed." Terms match what Gabriel
stated directly: Termination extended to **6/30/2027** (not the 5/31/2027 read off the earlier draft —
the draft was not the final version); Rent **$2,332/mo effective 6/1/2026**. Wrote via `notion-update-page`
(`32c6ecd8-9e59-819a-aaa5-f393ef49a999`): `Monthly Rent` 1483.39→2332, `Lease Expiration` null→2027-06-30.
Verified via fresh fetch. **Tenant-rename question — decided 2026-07-17, closed.** This Third Addendum
also reassigns the Tenant under the Prime Lease from Maryland Hospital Association to "LogicQual Research
Institute, Inc." (an MHA affiliate per the tenant-termination-right clause), releasing MHA from all
obligations. Gabriel confirmed: keep `Tenant Name` as Maryland Hospital Association, no rename. Decision
recorded in the row's own `Notes`.
**Granite Tops rent/date — moot, resolved 2026-07-17 (later, same day).** The 5/28/2026 addendum
($8,750/mo, 11,160 SF, through 5/31/2029) was never executed and is now moot: Gabriel confirmed the
tenant is vacating end of month (2026-07-31). Wrote via `notion-update-page` (`32b6ecd8-9e59-81b0-90f7-
fc8c610b609f`): `Lease Status` → Notice Given, `Lease Expiration` 2026-05-31 (stale) → 2026-07-31 (vacate
date). `Monthly Rent` ($16,713.65, still unexplained by any source found) deliberately left as-is —
final figure is now a move-out reconciliation question, not a lease-terms question. Verified via fresh
fetch. Note: AR Balance shows $180.19 at 90+ days aged — not chased further, outside this item's scope.
**Progress 2026-07-26 (bounded batch, 12 tenants): the never-doc-verified remainder of the Northwood
bulk-address-fix population checked; 12/12 resolved (11 confirmed correct as-is, 1 corrected —
a NEW bug variant: cross-row contact-field contamination); 2 writes made, both verified by fresh fetch.**
- **Batch scope:** the 2026-07-17 Northwood bulk fix corrected `Property Address` only on 31 active
  rows — rent/dates/contacts on most had never been checked against any document. Queried the live
  DB (`Property Address LIKE '%Northwood%Salisbury%' AND Row Retired='__NO__'` → 31 rows), excluded
  the 9 already individually verified on 07-17 (Bay-Care, Childs Play, Evans, Harold Palmer, Hobart,
  Itron, MHA, Reddish, Robert & Kesha Best) and IWNS LLC (new 2026-07 row, outside the 93-row
  universe), and took 12 of the remaining 21: Online Auction, Adkins Towing, Anibal Morales,
  Peninsula Pressure Systems, William D. Smith, BEK General Contracting, BRITMAN CORPORATION,
  Sky Shield, Carlton L. Handy, Complete Cleaning, Louis Foxwell, Taron Tyree Walker.
- **Verification sources:** two independent rolls — `Current Rent all properties 1.13.2026.xlsx`
  (HubSpot-derived, read in full) and **`Rent Roll 7.20.2026.xlsx`** (egoldberg OneDrive root,
  Master-Workbook export, "As of July 20 2026 · 137 tenants · Active Scenario: Base" — 6 days old
  at check time) — plus primary documents where the rolls diverged.
- **NOTE FOR NEXT PASS — the notion_only premise has shifted:** Rent Roll 7.20.2026 (workbook
  lineage) now CONTAINS all 30 occupied 2207 Northwood units. The Master Workbook appears to have
  gained Northwood rows since the 07-17 "zero Northwood rows in EXPORT_RentRoll" finding — the
  93-row universe should be RE-DERIVED against the current workbook before the next batch.
- **9 confirmed correct, no write (exact match in BOTH rolls):** Adkins Towing (`32c6ecd8-9e59-8169-af36-d84cd109c412`,
  $835 / 1993-12-01 / exp 2024-09-01, genuinely Expired), Anibal Morales (`-813e-8069-ea5e592d0f0b`,
  $399 / exp 2024-09-01, Expired), Peninsula Pressure (`-8145-aea3-e4195d1e09fd`, $3,999 / exp
  2026-12-31 / 6,500 SF), BEK (`-81ca-8bea-d5eda7a246d9`), BRITMAN (`-8195-a0f9-c24a18e82c36`;
  executed-lease file also on record, 06.2025), Sky Shield (`-81bb-aff5-cb70c4649b27`; 09.2025 lease
  on record), Taron Walker (`-8137-ab7e-d81b45ae9a52`), Complete Cleaning (`-81c3-a892-f3c18df594a5`,
  $1,165.96 = Jan's $1,132 x1.03, escalation 2026-07-01 passed — 7.20 roll confirms exactly), Louis
  Foxwell (`-81ac-92e6-ec46a93b8a2c`, $1,854 = $1,800 x1.03, same pattern, 7.20 roll confirms).
- **2 confirmed correct via primary document (Jan roll was stale, no write needed):**
  - **Carlton L. Handy** (`32f6ecd8-9e59-8107-b967-c787ce72bf1f`): Second Addendum (`Lease Suite A4
    Carlton Handy Addendum #2 -- 2203-2207 Northwood 04.2025.docx`) states termination 2027-02-28,
    rent $1,166 effective 2026-06-01 — exact match to Notion and the 7.20 roll (docx copy has blank
    signature blocks, but terms are live in the workbook roll).
  - **William D. Smith** (`32c6ecd8-9e59-813b-8fbc-cae3816393d9`): Addendum (`Lease Suite A11-12 + C3
    William Smith Addendum`) confirms A11-12 extended to 2031-04-30, $1,925 + $725 (C3) = $2,650/mo
    effective 2026-05-01, 3% from 2027-05-01 — exact match to Notion/7.20 roll; Jan roll ($2,568.40 /
    exp 2026-04-30 / 2,400 SF) was pre-addendum. Notes annotated (verified by fresh fetch) with the
    nuance that **Unit C3 is month-to-month** — the 2031 expiration covers A11-12 only. Data fields
    untouched.
- **1 corrected — NEW BUG VARIANT, cross-row contact-field contamination:** **Online Auction**
  (`32c6ecd8-9e59-8197-b41e-e7d264c21a53`, Suite B5). Lease fields ($999 / 2025-11-01 / 2027-10-31)
  exact-match both rolls AND the primary lease (`Lease Suite B5 Patrick Andre Betz -- 2203-2207
  Northwood 10.2025(2).docx`, signed date 10/9/2025, term 11/1/2025-10/31/2027, $11,988/yr) — but the
  row's Primary Contact / Contact Email / Contact Phone / HubSpot Address / HubSpot Contact all
  belonged to **Styled + Staged Interiors** (Lauren Meikle, Morrison 420 — a different tenant with
  its own correct row `32b6ecd8-9e59-817f-afce-dc12f510cc62`). Corrected to Patrick Betz
  (schoolbetz@gmail.com, +14436141854, HubSpot contact 162494267501, HubSpot Address "2207 Northwood
  Suite B5") on two agreeing independent sources: the Jan-2026 HubSpot-derived export and the retired
  duplicate row `Patrick Betz` (`32b6ecd8-9e59-81dc-9230-c822f9aa6e73`, retired 2026-07-21, which
  carried the same email/phone + the real Betz HubSpot record). Verified by fresh fetch. (That
  duplicate's 07-21 retirement also resolves what would otherwise be a same-property duplicate pair.)
- **FLAG, not actioned — A3/A4 turnover in progress:** draft (unexecuted, blank-dated) leases created
  7/20-7/22/2026 in the Northwood Leases folder show Sky Shield (Lagana) moving A3→A4 and Grails TCG,
  LLC taking A3 — implying a Carlton Handy departure ahead of his 2027-02-28 term. Notion's Sky Shield
  (A3, exp 2026-09-30) and Carlton Handy (A4, exp 2027-02-28) rows reflect the currently-executed
  state and were left as-is; re-check once those leases execute.
- **Incidental (not claimed as resolved):** the other 9 live never-verified Northwood rows (Austin
  Walter Ventures, Cosmic Spice, DDR Enterprise, Delmarva Business Solutions, Delmarva Riders,
  Hermiston, STOIC FARMS, Terrone White, Tony Kevin Davis) were roll-diffed in passing — all 9 agree
  with the 7.20.2026 roll (4 reflect 2026 renewals/escalations vs the stale Jan roll: Cosmic Spice
  $1,215/2028-06-30, DDR $1,183/2027-04-30, Delmarva Business 2029-06-30, Terrone White
  $1,050/2027-03-31). Easy wins for the next batch, but not individually doc-confirmed here.
**Real scope still remaining:** Chesapeake Communications (retired rather than traced, unchanged);
CURREN SOLUTIONS (Information Lane, still unresolved from 07-17); My Autonomous Transportation Co
(no executed lease located, gap unfilled); the 9 roll-diffed-only Northwood rows above; and whatever
the re-derived notion_only universe (see the 07-26 note — the workbook now carries Northwood) still
contains outside the worked clusters. This item stays OPEN, not closed.
**Auto-check:** none (not a fleet-registry item).

### OI-015
**Status:** CLOSED — verified clean, no purge needed
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep first run (2026-07-18, manual + supervised); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Original finding (superseded, see Evidence below):** the sweep + fix-commit `866480f`'s own note
both claimed real E. Fulton `CONFIDENTIAL_TERMS` tokens (committed to `.env.example` at `c4c69a8`,
2026-06-06) were "still in git history ... on the remote until a separate history purge is run."
**Evidence (2026-07-19):** a completely fresh clone directly from `github.com/ZeOoba/ora-pm` (bypassing
any local object cache) shows commit `c4c69a8` already contains only placeholders
(`example-term,another-example,third-example`), and `git log -p --all` across every reachable commit
and branch in that fresh clone returns zero matches for any real term variant. **The reachable,
clonable, browsable history is genuinely clean — no history rewrite/force-push was needed or performed.**
The original finding was based on a stale signal: a local dangling/unreachable blob
(`39b02f4585cc6357876423d04d5c3fcee65793b0`) that was mistaken for "still in history" — it was never
part of any current ref and has since been pruned locally. **No purge action was taken; none was needed.**
**Residual (tracked separately, see OI-022):** that same blob IS still directly retrievable via GitHub's
Git Data API (confirmed: `gh api repos/ZeOoba/ora-pm/git/blobs/39b02f45...` returns its content), because
it's kept alive server-side by `refs/pull/2/head` (PR #2's GitHub-managed ref, which cannot be deleted
via git push, the repo API, or repo settings — this is a documented GitHub platform limitation, not a
per-repo config issue). This is a distinct problem from "is it in the history anyone would ever see" —
it requires a GitHub Support request, not a git operation. Spun off as OI-022.
**Auto-check:** none.

### OI-022
**Status:** OPEN — submitted, awaiting GitHub Support action (ticket #4584520, reopened 2026-07-20 with corrected SHA)
**Opened:** 2026-07-19
**Source:** OI-015 investigation (2026-07-19)
**Description:** the original (pre-rewrite) blob containing real E. Fulton `CONFIDENTIAL_TERMS` values
is still directly retrievable via GitHub's Git Data API (`gh api repos/ZeOoba/ora-pm/git/blobs/<sha>`),
even though it's unreachable from any current branch/tag and does not appear in any clone or the repo's
normal browsable history. Root cause: it's kept alive by `refs/pull/2/head`, a GitHub-internal ref for
the (closed, merged) PR #2 that originally carried the sensitive commit — these refs cannot be deleted
by the repo owner via git push, the REST/GraphQL API, or repo settings; there is no self-service
mechanism. The only documented remediation is a GitHub Support request asking them to purge the
cached/orphaned objects tied to this PR. Repo confirmed private with 0 forks (via API), so a
support-side purge should fully resolve the exposure.
**Not a live credential** (E. Fulton declassified 2026-07-09) — low urgency, but a real residual
exposure path (anyone who obtains the exact blob SHA, e.g. from an old CI log, webhook payload, or
browser cache, can retrieve the real terms via the API regardless of the rewrite on `main`).
**SUBMITTED 2026-07-19.** Gabriel authorized submission; sent via his own authenticated GitHub
session (Claude in Chrome) since this requires account login, not an API. **GitHub Support ticket
#4584520, status: open**, category Repositories → Repository features → Branches (closest available
fit; no dedicated "sensitive data removal" category exists in the structured form — full detail
carried in the ticket body). GitHub's own AI triage on the request confirmed the diagnosis matches
their documented "Removing sensitive data from a repository" process exactly (PR-ref dereference +
server-side GC).
**CORRECTION 2026-07-20 — original ticket cited the wrong SHA.** GitHub Support replied
(2026-07-20) that their tooling found the cited commit `c4c69a8` still referenced on `main`,
`chore/gitattributes-normalize-eol`, `recovery/2026-07-05-object-db-loss`, and PRs #5/#6 — which
read as a new exposure. Re-verified before acting (fresh clone + `gh api .../contents/.env.example`,
independently matching): `c4c69a8` has **only ever held placeholder text**; it's a clean squash-merge
of PR #2 and is a legitimate ancestor of `main` (that's why it shows up everywhere — normal ancestry,
not exposure). The real sensitive commit is a different SHA, **`6aed9a7`** (the pre-squash head of
PR #2, found via `git log --find-object=39b02f4585...` against `refs/pull/2/head`), which is *not*
reachable from `main`, any branch, or PR #5/#6 — confirmed via `git merge-base --is-ancestor`. The
`c4c69a8` misattribution originated in fix-commit `866480f`'s own message (2026-07-16) and propagated
into the original support-ticket text.
**Net effect: no branch/PR cleanup needed anywhere — OI-015's "reachable history is genuinely clean"
conclusion stands, confirmed a second time.** Replied to ticket #4584520 (2026-07-20, Gabriel
authorized) correcting the SHA to `6aed9a7`, confirming `main`/branches/#5/#6 are unaffected, and
asking GitHub to purge `6aed9a7` / blob `39b02f4585cc6357876423d04d5c3fcee65793b0` via the
strip-internal-references option (preserves PR #2 comment history). Ticket reopened to **status:
open**, 3 comments. Awaiting GitHub's action on the corrected SHA.
**Auto-check:** none.

### OI-016
**Status:** CLOSED
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Description:** ora-pm (pinned SHA `f47bbe0`) depended directly on `hono` <=4.12.24, which carried HIGH
advisories: path-traversal via encoded backslash `%5C` on Windows (not reachable — the app runs on the
Cloudflare Workers Linux edge), CORS middleware reflecting any Origin with credentials when `origin`
defaults to wildcard, and AWS-Lambda-adapter Set-Cookie merging. Effective severity MEDIUM: portal auth
is Bearer-token (Authorization header), not cookie-based, which limits the CORS-credential vector.
**Evidence:** `hono` bumped 4.12.23→4.12.31, commit `c300867` on `main` (landed by Gabriel directly).
Verified via `npm audit` — the finding no longer appears.
**Auto-check:** none.

### OI-017
**Status:** CLOSED
**Opened:** 2026-07-18
**Source:** ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b`
**Description:** Build/test/deploy toolchain CVEs in both repos, none reachable from a production, tenant,
or public request path. ora-pm (SHA `f47bbe0`): vitest CRITICAL (UI-server arbitrary file read/exec — only
when the Vitest UI server is listening, i.e. local dev/test), plus vite/esbuild/wrangler/ws/undici
HIGH/MOD. oxford-command-center (SHA `306a67f`): concurrently→shell-quote CRITICAL (dev script runner),
vitest CRITICAL, @huggingface/transformers→onnxruntime-node→adm-zip HIGH (crafted-ZIP 4GB DoS; only the
localhost-only brain server, reachable only on untrusted ZIP input), exceljs→uuid MOD. All fixes are
semver-major. Effective operational risk LOW; tracked for a batched toolchain-bump pass, not urgent.
**Progress 2026-07-19:** rather than the flagged semver-major top-level bumps, used targeted `overrides`
on the specific vulnerable transitive packages only (adm-zip/uuid/esbuild in oxford-command-center,
esbuild/undici/ws in ora-pm) — resolves 11 of 13 originally-flagged CVE instances with zero top-level
version changes. Both verified: full `gate:ci` green in oxford-command-center (typecheck/lint/test/
build/bundle-budget); `tsc --noEmit` clean + 185/185 tests in ora-pm. PRs: `ZeOoba/oxford-command-center#220`,
`ZeOoba/ora-pm#5` (neither merged yet — pending review).
**Residual, not fixed:** in both repos, `vitest@2.x`'s own internally-bundled `vite@5.x` (via `vite-node`)
still carries 3 CVEs (path traversal, NTLM hash disclosure on Windows, `fs.deny` bypass on Windows). A
scoped override forcing `vite@6.x` under `vitest` specifically was attempted in both repos and rejected
by npm as an invalid tree — `vitest@2.x` doesn't tolerate `vite@6.x` internally. The only real fix is
`vitest` 2.x→4.1.10 (semver-major), which needs its own dedicated cross-repo compatibility pass. Still
dev-server-only, never reachable from production — kept LOW effective severity, still not urgent.
**Progress 2026-07-19 (later): ora-pm side FULLY resolved.** Bumped `vitest` 2.x→4.1.10 (added to PR #5) —
clean migration, no config changes needed, `tsc --noEmit` clean, 185/185 tests unchanged, `npm audit`
now 0 vulnerabilities (was 9 at OI-017's opening). **oxford-command-center side attempted, reverted.**
The same bump surfaced a systemic incompatibility, not contained to one file: 24 of 41 tests in
`tests/unit/governance-check.test.ts` failed across nearly every describe block, tracing to
`vi.mock('node:fs')` automocking no longer producing usable mock functions under vitest 4. An explicit
factory-function mock fixed the crash but surfaced a second-order issue — mocks set via a helper
function (vs. inline in the test body) silently failed to reach the module under test. Given this
repo's 2828 tests cover live financial-data reconciliation (NOI, capital allocation, warehouse sync),
reverted rather than force an incompletely-understood mocking regression through; PR #220 stays scoped
to its original, already-verified overrides-only fix. oxford-command-center's 3 residual CVEs need a
dedicated vitest-4 migration pass across the whole test suite's mocking patterns — real follow-up work,
not a drive-by fix. ora-pm: fully closed (0 vulnerabilities). oxford-command-center: 3 residual, LOW
effective severity, not urgent.
**Refresh 2026-07-22 (ora-appsec-sweep weekly, SHAs ora-pm `1b304e8` / occ `85d3151`):** re-verified via
`npm audit`. **ora-pm no longer 0-vulns** — 2 new HIGH surfaced: `wrangler@3.114.17`→`sharp@0.33.5`→
libvips (CVE-2026-33327/33328/35590/35591), published after the 07-19 close. Fix requires `wrangler`
>4.16.1 (semver-major); sharp is not directly overridable to a patched libvips. Deploy/build tooling
only — never in the Cloudflare Workers request path. Not urgent, batch with the next wrangler bump.
**occ residual confirmed still open (9 advisories total: 1 CRIT / 6 HIGH / 2 MOD):** the vitest→vite
chain (vitest CRITICAL UI-server file-read/exec + vite path-traversal / NTLM-disclosure / `fs.deny`-bypass
HIGH) is the same vitest-4 migration blocker documented above; plus js-yaml / brace-expansion / fast-uri
HIGH (transitive, DoS/host-confusion, `fixAvailable`) and `@huggingface/transformers`→sharp/libvips HIGH
(**no fix available yet** — monitor). All bounded by occ's localhost-only (`127.0.0.1`) bind; none
tenant- or network-reachable. No new OI opened — same repo+check bucket as this item.
**Progress 2026-07-26: ora-pm wrangler/sharp side RESOLVED — PR `ZeOoba/ora-pm#7` open, awaiting
Gabriel's merge.** On arrival, verified reality first: PR #5 (overrides + vitest 4.1.10) and #6
(undici 7.28.0 downgrade) both already MERGED, main at `809fbe3`, tree clean — the wrangler bump was
genuinely new work, done in an isolated worktree (`../ora-pm-oi017-wrangler`, branch
`fix/oi-017-wrangler-bump`), main checkout untouched. Bumped `wrangler` ^3.78.0 (3.114.17) →
^4.114.0; miniflare 4 pulls **sharp 0.35.2** (patched — advisory range <0.35.0), clearing all 4
libvips CVEs (2026-33327/33328/35590/35591). Two knock-ons handled: `@cloudflare/workers-types`
^4→^5.20260722.1 (wrangler 4 peerOptional hard-fails npm resolution on v4; typecheck clean against
v5) and the `esbuild ^0.25.0` override REMOVED — it existed solely to lift wrangler 3's pinned
esbuild 0.17.19 past its CVE (#5's fix); wrangler 4 pins its own 0.28.1 and vite resolves 0.25.12,
so no consumer <0.25 remains (verified via `npm ls esbuild`). undici/ws overrides kept as-is
(deploy-safe pin from #6; miniflare 4 resolves undici 7.29.0 / ws 8.21.1 under them).
**Audit evidence:** baseline at `809fbe3` was actually **5 vulns (3 HIGH / 2 MOD)**, not the sweep's
2 — two NEW advisories published since 07-22: postcss ≤8.5.17 HIGH (GHSA-r28c-9q8g-f849, vite
transitive) and react-router 6.0.0–7.17.0 MOD ×2 (GHSA-wrjc-x8rr-h8h6 open redirect +
GHSA-337j-9hxr-rhxg SSR hydration). postcss fixed in the same PR via in-range lockfile refresh
8.5.15→8.5.23 (no package.json change). **After: 2 MOD** (react-router only).
**Verification (all in the worktree, wrangler 4 tree):** `tsc --noEmit` clean · 185/185 tests
(32 files, vitest 4.1.10 — matches last known-good) · vite production build green · `npx wrangler
pages functions build` compiles the `functions/` worker under 4.114.0 (closest local proxy for the
CI `pages deploy` step, chosen deliberately given #6's undici-broke-deploy history). `wrangler.toml`
needs no changes. Flagged in the PR: first wrangler-4 deploy fires on merge (CI deploys main to
Cloudflare Pages) — watch that Actions step.
**Residuals, item stays OPEN:** (1) react-router 6.x MOD ×2 — prod dependency of the tenant portal,
real fix is semver-major 6→7, needs its own pass (SSR-hydration advisory not applicable, app is
client-rendered; open redirect is the live one, MOD); (2) oxford-command-center's 9 advisories —
unchanged, still blocked on the dedicated vitest-4 mocking-migration pass documented above, NOT
touched this session (out of scope).
**Progress 2026-07-26 (later): occ vitest-4 blocker ROOT-CAUSED and fixed in a branch — ready to ship
pending REFUTE pass, deliberately NOT merged.** L5 investigation in isolated worktree
`../oxford-command-center-oi017-vitest4-investigation`, branch `investigate/oi017-vitest4-migration`
(PUSHED to origin, commit `a7a5ad7` on base `ac34d88`). The 07-19 "systemic mocking regression" was
neither systemic nor a mocking regression: under vitest 4, `vi.mock()` of Node builtins (`node:fs`)
is a **silent no-op in the jsdom environment** (this repo's global default) — the module under test
receives the REAL fs, so mocks never intercept. Isolated by controlled experiment: same test, same
setup file, both pools (forks/threads) — `--environment=node` works (both `fs` and `node:fs`
namespaces become mocks), jsdom never does; even `{ spy: true }` and factory variants no-op under
jsdom. This retroactively explains BOTH 07-19 symptoms: "automock produces unusable mock functions"
(the exports were the real, un-mockable fs functions → `mockReturnValue is not a function`) and
"helper-set mocks silently not reaching the module under test" (they were set on mock objects the
real-fs-importing module never saw — never a hoisting/helper-timing issue). Entire fix: bump
vitest+@vitest/coverage-v8 to 4.1.10 and add `// @vitest-environment node` to
`tests/unit/governance-check.test.ts` (a pure Node-script test where jsdom was wrong anyway) —
zero mock restructuring, 5 lines + deps. governance-check.test.ts is the ONLY builtin-mocking test
file in the repo (verified by grep; the other 13 `vi.mock` users mock local modules and are
unaffected). **Evidence:** baseline 41/41 green under v2 at `ac34d88` → 41/41 fail under 4.1.10
unpatched (same TypeError as 07-19) → 41/41 green with pragma; **full suite 244 files / 3101 tests
green** (suite grew from 2828 since 07-19); tsc clean · eslint clean · check:dev-css clean · vite
build green · bundle budget green. Two failures appeared once under a concurrent-load gate run
(capital-allocation-api `beforeAll` 10s import timeout; bash-guard perf assertion 2009 ms vs 2000 ms
— a 9 ms miss) and both re-ran green in isolation: load flakes, not vitest-4 regressions.
**Security effect:** `npm audit` in the branch: vitest CRITICAL + all 3 vitest→vite HIGHs GONE, 0
criticals remain. Remaining 9 advisories are UNRELATED chains: brace-expansion/fast-uri/js-yaml/
postcss (all `fixAvailable` via plain `npm audit fix`), react-router MOD ×2 + @hono/node-server MOD
(semver-major), sharp/libvips HIGH (no fix — monitor). **Decision: small, well-understood,
safely-shippable — but per doctrine this is financial-decision-repo test infrastructure, so it needs
the mandatory adversarial REFUTE pass before merge; not merged by the investigating session. Next
step: REFUTE pass on branch `investigate/oi017-vitest4-migration`, then PR + merge, then a plain
`npm audit fix` pass for the 4 non-breaking advisories.** Item stays OPEN.
**Progress 2026-07-26 (later still): ora-pm react-router residual RESOLVED-pending-merge — PR
`ZeOoba/ora-pm#9` open, awaiting Gabriel's merge. DECISION: proceed now, but to v8.3.0, not v7.**
L5 investigation in isolated worktree (`../ora-pm-oi017-rr7-investigation`, branch
`investigate/oi017-react-router-7`, base `92b4b45` = merged #7; main untouched). Baseline
re-verified first: tsc clean, 185/185, `npm audit` 2 MOD. Why not v7 (every option tested
empirically in the worktree, not guessed): HEAD's lockfile already resolves ^6.26.0 to **6.30.4**
(latest 6.x) — still flagged, no in-range escape; the 2 MOD advisories are patched only at ≥7.17.1;
but react-router ≥7.12.0 carries **GHSA-qwww-vcr4-c8h2** (HIGH, RSC-mode CSRF, published 07-24,
patched ONLY in react-router@8.3.0 per the GitHub advisory API — and never in any react-router-dom
release, since that package was removed in v8). Installing react-router-dom@7.18.1 was tried:
audit trades 2 MOD for 2 HIGH. v8.3.0 is the only 0-findings endpoint. The HIGH is inapplicable
here ("only affects... unstable RSC APIs" — ora-pm has no RSC/SSR/loaders/actions), but the
dashboard fix and the real fix coincide at v8. Migration cost trivial by construction (context7
v7/v8 upgrade docs + code recon): no `future` flags anywhere, all `Link`/`navigate` targets
absolute (v7_relativeSplatPath flip has nothing to bite), so the whole diff is imports —
`'react-router-dom'`→`'react-router'` in 20 files + `RouterProvider` from `'react-router/dom'`
(22 files, 39+/53−, zero behavior lines). **Evidence on the final tree:** tsc clean · 185/185
(vitest 4.1.10) · vite prod build green · `wrangler pages functions build` compiles (functions/
has zero react-router usage) · `npm audit` **0 vulnerabilities** · browser smoke on the built app:
`/login` renders identical to the v6 baseline, zero console errors. Worktree removed after push;
branch lives locally + on origin; PR #9 notes the first v8 deploy fires on merge (watch the Pages
Action, per #7 precedent).
**NEW DEFECT FOUND (separate follow-up, NOT caused by the bump): the tenant portal is blank in
PRODUCTION today.** `https://ora-pm.pages.dev/portal/login` renders an empty `#root` — reproduced
identically on v6 local build, v8 local build, and live prod (admin `/login` renders fine, so not
env-specific). Root cause: descendant `<Routes>` in `src/portal/PortalRouter.tsx` use absolute
`/portal/...` paths that can never match the splat remainder under the `/portal/*` parent, so the
subtree renders null with no console error; the 185-test suite never renders the router, so nothing
caught it. Spawned as its own task chip (fix relative paths + add a router-rendering test).
Tenant-payment revenue path — high priority. Item stays OPEN: ora-pm PR #9 unmerged; portal
blank-render defect open; occ side per the block above.
**Progress 2026-07-26 (REFUTE pass): occ vitest-4 fix CONFIRMED SAFE — PR
`ZeOoba/oxford-command-center#238` open, awaiting Gabriel's merge.** Independent adversarial REFUTE
pass (reviewer did not write the fix) actively tried to break `investigate/oi017-vitest4-migration`
and failed on every axis. (1) **Rebased** onto current main `f511d5f` (clean, `a7a5ad7`→`99a63e9`;
main had grown 19 new brain/anomaly-floor tests written under vitest 2) and re-ran everything fresh:
**245 files / 3120 tests, 3119 green**; sole failure was bash-guard's wall-clock perf assertion
(3464 ms vs 2000 ms) — the same pre-existing load flake `f511d5f`'s own commit message documents
under vitest 2; 68/68 green in isolation, exit 0. typecheck 0 · lint 0 · vite build green · bundle
budget green (entry 92.5 kB < 250 kB). (2) **jsdom-masking refuted:** `scripts/governance-check.ts`
imports only `node:fs`+`node:path`, zero DOM references in 481 lines; the pragma matches the ~45
test files already carrying `@vitest-environment node`. (3) **Other-mock spot-check refuted:**
governance-check is the ONLY builtin-mocking file; the two jsdom-default local-module mockers were
positively verified to still INTERCEPT, not merely pass (`brain.test.ts` injects `parseError`
through the mocked parse module + asserts mock-captured overlay writes; `topbar.test.tsx` asserts
`data-testid` markers that exist only in the mock components). (4) **Audit re-verified fresh, not
trusted:** branch = 9 vulns (3 MOD / 6 HIGH), **0 critical**, no vitest/vite chain; main baseline
re-run same day = 30 vulns incl. 1 CRITICAL + the vitest/vite advisories. **Residual flagged in the
PR (not blocking):** the pragma fixes the file, not the class — a future bare-automock of a Node
builtin under jsdom could silently run real fs and pass for the wrong reason (configured mocks fail
loudly with the TypeError); recommended follow-up: ESLint rule or vitest.config comment requiring
the node pragma for `vi.mock('node:*')` files. **Mechanics:** force-push of the rebased branch is
guard-denied (destructive-git hard deny), so the rebased state was pushed as new branch
`oi017-vitest4-migration-rebased` (original branch preserved on origin); PR #238 targets main from
it. NOT merged — financial-decision repo, Gabriel merges. After merge: the plain `npm audit fix`
pass for the 4 fixAvailable advisories (brace-expansion/fast-uri/js-yaml/postcss) remains queued
per the 07-26 investigation block.
**CLOSED-OUT 2026-07-26 (both PRs merged same day, Gabriel):** `ZeOoba/ora-pm#9` merged (`68fe84d`) —
deploy verified (production confirmed serving `68fe84d` via `wrangler pages deployment list`, `/api`
401 auth-gated, admin `/login` 200, no regression); ora-pm side of OI-017 is now fully clear, **0
vulnerabilities**. `ZeOoba/oxford-command-center#238` merged (`e7446cc`) — no auto-deploy exists for
this repo (verified: `ci.yml`/`full-gate-selfhosted.yml`/`order-fragility.yml` are gate/canary jobs
only, no deploy step; the brain mirror ships only via a separate manual `scripts/deploy-mirror.ps1`
run per the `/ship` doctrine), so this merge is main-only, nothing went live. **Item's original CVE
scope is now resolved: the vitest/vite CRITICAL+HIGH chain that blocked this item since 07-18 is
gone in both repos.** Two things remain, deliberately NOT rolled into this item's closure: (1) occ's
queued non-breaking `npm audit fix` pass (4 advisories: brace-expansion/fast-uri/js-yaml/postcss) —
trivial but still real financial-repo code, needs its own small PR+gate, not done unprompted this
session; (2) the ora-pm blank tenant-portal defect — tracked as its own task chip, already running
in a separate Gabriel-directed session, not part of this CVE item's scope to begin with.
**Closed:** 2026-07-26
**Evidence:** `npm audit` on ora-pm main (post-#9) = 0 vulnerabilities; `npm audit` on oxford-command-center
main (post-#238) = 9 vulns / 0 critical (down from 30 incl. 1 CRITICAL pre-merge), with the vitest/vite
chain that opened this item entirely gone. Both PRs confirmed MERGED via `gh pr view --json state`;
ora-pm deploy confirmed live via `wrangler pages deployment list` + a 401/200 health check.
**Auto-check:** none.

### OI-024
**Status:** OPEN (logged, deliberately not fixed)
**Opened:** 2026-07-24
**Source:** `hooks/shared-checkout-guard.py`; found while realigning its attribution tests (commit b599432,
see [feedback_shared_checkout_guard_session_attribution_unreliable.md](feedback_shared_checkout_guard_session_attribution_unreliable.md))
**Description:** `_attribute_wip()` resolves the provenance directory from `SHARED_CHECKOUT_SESSIONS_DIR`
(falling back to a hardcoded `hooks/sessions`) rather than importing `commit_provenance.sessions_dir()`,
which resolves `COMMIT_PROVENANCE_SESSIONS_DIR`. `hooks/lib/commit_provenance.py`'s own docstring states
the recorder and every reader MUST agree on the storage location "or every comparison silently misses" —
this third consumer agrees only by coincidence of defaults.
**Why inert today:** neither env var is set anywhere in `settings.json`; both resolve to
`C:/Users/Owner/.claude/hooks/sessions`, and 35 live `touched-files.txt` confirm the recorder writes there.
The naming branch is verified working in production.
**Failure mode if it ever bites:** setting `COMMIT_PROVENANCE_SESSIONS_DIR` alone (or the reverse) points
the guard at an empty directory. It degrades honestly — always UNATTRIBUTED, never a *wrong* name — but
permanently and silently, with no signal that attribution has stopped working.
**Fix if taken up:** import `sessions_dir` from `commit_provenance` and use it for the provenance read
only, keeping `SHARED_CHECKOUT_SESSIONS_DIR` for the warn-marker (two different concerns currently sharing
one variable). Note the tests rely on the current coupling to stay self-contained, so they'd need the
provenance var set too. Being security-gate code, this needs the mandatory adversarial REFUTE pass.
**Decision:** Gabriel 2026-07-24 — log, don't fix. Fails open, unreachable in the current configuration,
and not worth a guard edit inside a test-only change.
**Auto-check:** none.

### OI-021
**Status:** OPEN — Restoration Church Trust lender-outreach decision remains; both HubSpot sub-item and the renewal-pipeline batch pass are CLOSED
**Opened:** 2026-07-19
**Source:** [event_log.md](event_log.md#2026-07-19)
**Restoration Church Trust lender outreach (still open):** draft outreach letter prepared 2026-07-25
(confirms repayment/extension intent ahead of the 2027-02-20 balloon, closing the missed June-2026
Covenant Watch checkpoint) — send blocked on a real recipient contact. Checked Notion (Loan Portfolio
Tracker, Critical Deadlines Tracker), the one associated HubSpot deal, and Outlook mail history: no
borrower contact name or email exists anywhere in the system, only internal loan-tracking data. Needs
Gabriel to supply the actual contact before send (not guessed, per Invariant 7).
**HubSpot mis-entered deal — CLOSED 2026-07-25 (Gabriel's explicit go-ahead).** "Lease Renewal —
Restoration Church Trust" ($16,714, was `appointmentscheduled`) confirmed as the same
mis-entered-loan-counterparty pattern as OI-009 (a loan, not a lease, entered as a tenant renewal
deal). Retired via `manage_crm_objects`: `dealstage` → `closedlost`, `dealname` prefixed
`RETIRED (data-entry error, see open-items-tracker.md OI-021) —`. Verified post-write via
`get_crm_objects`.
**Renewal-pipeline batch pass — CLOSED 2026-07-25.** A `/debug` pass on Command Center's lease-alert
bug (separate incident, see [[project_master_workbook_no_single_writer_2026-07-24]]) surfaced this
item; chased it down the same session. Before touching anything, found the monthly
`ora-tenant-hubspot-reconciliation` sweep (2026-07-22, Notion "HubSpot-Tenant Reconciliation — July
2026") had already evidence-checked all 50 deals and narrowed the real open set to 8 items (down from
"49 stuck") — re-doing that work by hand was avoided. Chased the 8 via primary documents
(SharePoint leases/addenda, Adobe Sign audit trails, Gabriel's direct confirmation for one) and wrote
7 of the 8 to HubSpot (`closedwon`/`closedlost` + corrected `closedate`), each independently verified
post-write via `get_crm_objects`:
- **William D. Smith** → `closedwon` 2031-04-30 (Adobe Sign fully executed 2026-04-20, both parties).
- **State of MO, Dept. of Agriculture** → `closedwon` 2026-12-31 (official state renewal letter,
  2026-07-10, confirms both the date and — via its own return address — that the CHURN
  geo-mislabel flagged by the 07-22 reconciliation had already self-corrected; verified live, no write
  needed).
- **Cosmic Spice & Specialty Foods** → `closedwon` 2028-06-30 (Third Addendum, terms match live
  records exactly).
- **MLC Academy Maryland** → `closedwon` 2029-09-30 (Sixth Addendum, Adobe Sign fully executed
  2026-04-09 — NOT the 2031-09-30 figure from an unsigned draft found earlier the same session; that
  draft is Kareem Syed's still-pending Cricket DC LLC amendment request, 07-17, currently stalled on
  Gabriel's own diligence ask re: the entity's Inactive SDAT status).
- **FIRST STUDENT** → `closedlost` (turnover, confirmed by Gabriel directly: replaced by My Autonomous
  Transportation Co — matches the DSOR canonical page's own "single-tenant turnover" note; MATCo's own
  lease remains a separate, already-tracked gap under OI-009, unsigned LOI only).
- **Velcani Construction** → `closedlost` (turnover, replaced by Richwood Equipment Co LLC 2026-05-01,
  confirmed via 3 independent Notion sources).
- **Consult and Management** → `closedlost` (defaulted on rent, vacated end of March 2026, escalated
  to collections).
The 8th item, MLC's tenant-identity/term question, resolved to the same MLC row above once the
executed-vs-draft distinction was sorted — no separate action needed.
The other ~37 deals still sitting in `appointmentscheduled` are NOT a data problem — their embedded
dates match current lease-ends exactly, they're just legitimately not-yet-due (furthest out to 2027)
with no automated stage-advancement. That's a policy/tooling gap (when should a deal leave
`appointmentscheduled`?), not a data item — not fixed here, would need Gabriel's terms first.
**Auto-check:** none.

### OI-025
**Status:** OPEN — one instance confirmed and remediated; full population unaudited
**Opened:** 2026-07-25
**Source:** shared-checkout investigation, this session (Gabriel asked to investigate the dirty-`~/.claude`-checkout flag raised at the end of the prior turn)
**Description:** while porting two skill-spec changes (HubSpot idle-deal flag + tracker-output redirect) into `ora-tenant-hubspot-reconciliation`, discovered the edit had first landed on `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\00_Governance\Scheduled\ora-tenant-hubspot-reconciliation\SKILL.md` — a path that is NOT one of the two documented live registry locations (`tech.md` §3: CC/MCP = `~\.claude\scheduled-tasks\`, LAMS = `OneDrive…\Documents\Claude\Scheduled\`). Confirmed via `list_scheduled_tasks` that the task's real registered `path` is the CC/MCP copy; the Claude_Workspace copy drives nothing. Listing that directory found **100+ task folders** — active-looking names matching live CC registry tasks (`ora-am-brief`, `ora-weekly-hygiene`, `ora-health-guard`, `ora-pm-ledger`, etc.), clearly one-off/completed check-* and investigate-* folders, and four pre-existing `_archive_2026-0[6-7]-*` subfolders already inside this same directory — i.e. someone has been using this location as a working/archival area for some time, but no memory file documents its relationship to the two-fleet doctrine.
**Action taken 2026-07-25:** archived the confirmed-orphaned `ora-tenant-hubspot-reconciliation` folder to a new `_archive_2026-07-25_orphans\` subfolder in place (moved, not deleted, matching the directory's own existing convention). Did NOT touch or audit the other 100+ folders — that's a materially larger task than this session's scope (a single-skill investigation), and several of the plausible-looking "live" names need a careful diff-against-canonical pass, not a bulk move.
**Action taken 2026-07-26 (batch 1 of the recommended bounded sweep):** re-verified the live CC/MCP roster directly via `list_scheduled_tasks` (27 entries incl. 2 pending one-time) rather than trusting a pasted snapshot. Audited 10 NOT-yet-audited folders, all with names that don't match either fleet's live roster:
- **Archived to new `_archive_2026-07-26_orphans\`** (all (a) STALE ORPHAN — each folder's SKILL.md self-describes as a one-time/self-disabling diagnostic or reconnaissance task, none appear in the live CC/MCP registry, and the underlying subject matter is independently confirmed resolved elsewhere): `canary-model-check-temp` (one-time model-ID canary, result already consumed), `check-appsec-sweep-beacon-pickup` (one-time LAMS-fleet SKILL.md-edit-pickup check, dated 2026-07-20/21), `check-code-audit-image-pass` (one-time check-in on a since-concluded concurrent website-image session), `check-dirty-files-session-pr` (self-described "PAUSED — event overtaken... retire fully"; also independently confirmed as a "resolved/completed one-time task" and archived under the *separate* `~/.claude/scheduled-tasks/` canonical location per `event_log.md` line ~41, same date), `check-shared-checkout-settled-140pm` (one-time 2026-07-24 checkout-settlement check tied to the now-CLOSED `project_config_corruption_recurrence_closed_2026-07-25.md` thread; also independently archived under the canonical `~/.claude/scheduled-tasks/` location per the same `event_log.md` line), `continue-cc-setup-optimization-batch-2c-3` (one-time continuation of Batches 2c/3 of the `spicy-crunching-starlight.md` plan; confirmed shipped — `registry-write-guard` and `connector-drift-probe.py` both exist and are documented live in `tech.md` §3b / the connector-roster markers), `investigate-plan-gate-worktree` (one-time reconnaissance of the `plan-gate-and-site-markers` worktree; confirmed the worktree no longer exists on disk — already torn down), `heartbeat-beacon-recovery-check` and `heartbeat-check-backup-verify` (one-time 2026-07-17 Cowork-heartbeat diagnostics; both independently confirmed already deleted from the registry and archived under the canonical `~/.claude/scheduled-tasks/_archive_2026-07-18_retired/` location per `event_log.md` line ~854 — these Claude_Workspace copies were leftover duplicates never cleaned up here).
- **Flagged (c) AMBIGUOUS — left untouched, needs Gabriel's call:** `linkedin-insight-tag-followup` — a one-time reminder task (name matches no live-fleet entry, so not a canonical-copy question) whose underlying subject — retrieving the real LinkedIn Insight Tag Partner ID for oxfordra.net, blocked on a LinkedIn Campaign Manager 2FA propagation gate — is confirmed STILL open per `event_log.md` ("LinkedIn Insight partner ID is still the placeholder `XXXXXXX` across all 16 analytics snippets") and is NOT tracked anywhere else in this tracker. This folder may be the only remaining pointer to that open item; recommend Gabriel decide whether to (i) fold it into a proper OI/tracker entry and then archive this folder, or (ii) leave the folder as the tracking mechanism for now. Not archived.
- **No (b) legitimate-secondary-copy cases in this batch** — none of the 10 audited names matched a live registry task.
**Incidental finding 2026-07-26 (not part of this batch, flagged not acted on):** the previously-archived `ora-tenant-hubspot-reconciliation` folder (see 2026-07-25 action above) has **reappeared at the top level** of this same directory, with content that hashes differently from (and is larger than) the archived copy in `_archive_2026-07-25_orphans\` — most likely a OneDrive Files-on-Demand sync artifact from this canonical (egoldberg-account-syncing) checkout catching up after the prior move, consistent with the documented [Memory Scope Fragmentation](reference_memory_scope_fragmentation.md) pattern, but not confirmed. Per this task's explicit instruction, did NOT re-touch or re-archive it this pass. Flagging for a follow-up session to (a) confirm whether this is a transient sync artifact that will self-resolve, or a genuine re-write from another account/session, and (b) reconcile which content (archived 7,028-byte copy vs. reappeared 11,656-byte copy) is actually current before taking any action.
**Action taken 2026-07-26 (batch 2 of the recommended bounded sweep):** cross-referenced the legacy `_REGISTRY.md` in this same directory (a periodic manual snapshot, last updated 2026-07-09, explicitly self-described as non-authoritative) against the live directory listing to surface candidates beyond the two batch-1 named recommendations, then re-verified the live CC/MCP roster fresh via `list_scheduled_tasks` (30 entries incl. one-time) before classifying. Audited 12 folders total:
- **Archived to `_archive_2026-07-26_orphans\`** (all (a) STALE ORPHAN, each verified by reading its own SKILL.md, not name-pattern alone):
  - `ora-setup-review-closeout-recheck` and `ora-uw-northridge-brockton-full` — the two batch-1-recommended candidates; both self-describe as one-time tasks tied to a single 2026-07-17 chip-claim/underwriting event, independently confirmed already-retired/deleted-from-registry per `event_log.md` line ~854.
  - `loopnet-autoreply` — recurring 3x/daily task pinned entirely to `mcp__composio-ora__OUTLOOK_REPLY_EMAIL`; Composio-ora is fully removed (confirmed 2026-06-11 per `tech.md` §4) and this task is on `_REGISTRY.md`'s own "4 inbox sweeps" retired list.
  - `ora-setup-audit`, `ora-dormant-thread-revival`, `ora-weekly-tooling-intel-sweep` — each self-describes `RETIRED 2026-06-16 (strategic audit kill list)` directly in its own SKILL.md frontmatter, not just an external doc's claim.
  - `zapier-trial-cancel`, `zapier-trial-reminder` — one-time May 2026 Zapier-trial decision tasks pinned to the since-removed Composio/Rube routing; Zapier itself fully retired 2026-07-16 (`tech.md` §4).
  - `hard-delete-zapier-trial-reminder`, `hard-delete-composio-may10-checkpoint` — self-describe `[ONE-TIME 2026-05-31]` / `[ONE-TIME 2026-05-10]`, both already-fired self-archiving cleanup tasks for the two Zapier items above.
- **Flagged (c) AMBIGUOUS — left untouched, needs Gabriel's call (new finding, not a simple stale-orphan case):** `ora-annual-budget-kickoff` and `ora-cash-position-snapshot`. `_REGISTRY.md` lists both among its "4 Gabriel-ratified-unneeded (2026-06-11)" retirements — but unlike the three `RETIRED 2026-06-16` folders above, NEITHER folder's own SKILL.md says it's retired, and the newer `ora-operations-extensions` plugin's `annual-cycle` and `cash-position-monitor` skills explicitly claim to "power" scheduled tasks of these exact names. Neither task appears in the current live CC/MCP roster or either fleet's pending-one-time list, so if the newer skills' claim is accurate, this is a live registration GAP (a designed seasonal/recurring task never re-registered after the 2026-06-11 retirement), not a stale-folder cleanup — archiving would risk deleting the only surviving spec for a task Gabriel may want live. Needs a decision: were these two deliberately superseded by the ora-operations-extensions build, or should they be re-registered?
- **No (b) legitimate-secondary-copy cases in this batch** — none of the 12 audited names matched a live registry task.
**Running total:** 23 of ~100+ folders audited across 3 passes (1 on 2026-07-25; 10 on 2026-07-26 batch 1, 9 archived + 1 flagged; 12 on 2026-07-26 batch 2, 10 archived + 2 flagged); 20 folders now archived total (1 + 9 + 10) across `_archive_2026-07-25_orphans\` and `_archive_2026-07-26_orphans\`; 3 flagged (c) AMBIGUOUS and left in place (`linkedin-insight-tag-followup`, `ora-annual-budget-kickoff`, `ora-cash-position-snapshot`). 89 folders remain at top level (86 genuinely unaudited + the 3 ambiguous ones above). Further bounded batches (5-10/pass) remain — do NOT close this item until the full population is classified.
**Not yet done:** the remaining 86 unaudited folders (including all names that DO match a live registry task — `ora-am-brief`, `ora-pm-ledger`, `ora-health-guard`, etc. — which need the more careful (b)-vs-(c) diff-against-canonical treatment both passes so far deliberately deferred) still need classification. Recommend continuing the bounded sweep (5-10 folders/pass, mirroring `ora-weekly-hygiene` Block F's pattern), and prioritizing the still-unresolved `ora-pm-ledger` question specifically: a same-named folder was archived as an orphan in `_archive_2026-07-12_orphans\` yet a new `ora-pm-ledger` folder reappeared at top level the very next day (2026-07-13) — the same reappearance pattern observed for `ora-tenant-hubspot-reconciliation` above — which should be treated as (c) AMBIGUOUS, not re-archived on autopilot, until that recurrence pattern itself is understood.
**Auto-check:** none.

### OI-030
**Status:** OPEN
**Opened:** 2026-07-26
**Source:** `ora-weekly-hygiene` Sunday run + 3 concurrent sessions, 2026-07-26 (see [event_log.md](event_log.md) 2026-07-26)
**Description:** `ora-weekly-hygiene/SKILL.md` Block C absorbed edits from four concurrent sessions in
a single day, including a Gabriel ruling (`caf154b`) that overrode an earlier same-day repoint:
check G was repointed to the `egoldberg` Graph drive, then formally DROPPED hours later, leaving
text that argued for a check the file struck through (dangling ref fixed in `9870bb4`, but only
that one symptom). Other same-day edits: Check B respec, frozen-snapshot RED override, real
folder names, Block N added, `781bf95` consolidating several idle sessions' WIP. Each change is
individually sound and the block is coherent as far as incremental patching can verify — the risk
is the kind only a full read catches: two locally-correct passages that disagree globally, exactly
the failure mode the check-G ruling itself was.
**Why not fixed yet:** the next edit to Block C should follow a full human read, not another
incremental agent patch. Due before the next Sunday fire (2026-08-02).
**Auto-check:** none.

### OI-032
**Status:** CLOSED
**Opened:** 2026-07-28
**Closed:** 2026-07-28
**Source:** Code-surface usage-limit audit, handed to Cowork for cross-surface follow-up, 2026-07-28
**Description:** `searchfit-seo` is installed TWICE in Cowork's plugin registry
(`...\583f08bc.../rpm\manifest.json`) — `plugin_01814pKq2AozUbEdjvGZw5os` (installed 2026-07-08,
marketplace "My Uploads") and `plugin_016u9h5nGGKuX18riDTJ7otg` (installed 2026-07-24, marketplace
"knowledge-work-plugins", displayName "SearchFit SEO"). Both show `installationPreference:
"available"`, doubling every searchfit-seo skill/agent in the listing. Not in active use per
Gabriel (2026-07-28 usage-limit audit). No supported tool exists to uninstall from either surface —
Cowork's manifest.json has no enable/disable boolean (unlike Code's `skillOverrides`), and hand-
editing it blind was correctly declined as an unverified-schema write.
**Evidence:** Gabriel confirmed (in-turn, 2026-07-28) he uninstalled both `searchfit-seo` entries
manually via Settings → Capabilities, per the candidate fix below. Not independently re-verified
against the live manifest.json (no tool access to that surface from Code) — trust the direct report.

### OI-033
**Status:** OPEN
**Opened:** 2026-07-28
**Source:** Cowork-surface follow-up to the Code-surface usage-limit audit, 2026-07-28
**Description:** LAMS/Cowork scheduled task `ora-tenant-contact-gap-sweep` (weekly Monday) carries
no `[MODEL: ...]` tag at all in its description — the sole untagged task in an otherwise
27/28-tagged LAMS fleet (re-verified 2026-07-28, all 27 tagged tasks still `claude-sonnet-5`,
including 5 set after the ~2026-07-25 Opus 5 rollout — LAMS shows no model drift, unlike CC/MCP).
**Candidate fix (not built):** tag it `[MODEL: claude-sonnet-5 | set 2026-07-28]` via
`update_scheduled_task` from a Cowork-surface session (LAMS registry writes need the matching MCP,
not reachable from Code) per [[reference_scheduled_task_model_standard]]'s tagging convention.
**Auto-check:** none.

## Closed

| ID | Opened | Closed | Source | One-line |
|----|--------|--------|--------|----------|
| [OI-028](#OI-028) | 2026-07-26 | 2026-07-26 | `hooks/git-prepush-hook-tests-gate.py` GIT_TRACE root-cause + fix, commit `0d4b974` | Root cause: NOT the network push (0.54s) — the pre-push hook-tests gate ran ~54 tracked test files SEQUENTIALLY, 137s wall-clock, measured directly. Parallelized (bounded ThreadPoolExecutor, 8 workers) → 137s to ~38-42s across 4 runs, 0 failures. TDD + adversarial REFUTE review (1 real finding fixed: a load-sensitive wall-clock test assertion, replaced with a structural sweep-line overlap proof); re-review NOT REFUTED. Built in isolated worktree, Gabriel-confirmed merge |
| [OI-023](#OI-023) | 2026-07-21 | 2026-07-22 | oxford-command-center `parse.ts`/`conditions.ts` (ora-pm-ledger 2026-07-21 divergence audit) | Snapshot provenance `asOf` now reads the workbook's own dateline (PR #231) — meta 2026-07-17 / cash 2026-07-10 live-verified; `?? s.meta.asOf` fallback audit: all alerting paths pass explicit run dates, last omitting caller wired |
| [OI-018](#OI-018) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run — supervised re-run (2026-07-18) | ora-pm HIGH IDOR on `/api/stripe/{customer,setup-intent,payment-intent}` RESOLVED — session-ownership guards (portal.ts/autopay pattern) landed in `c705531`, 185/185 green, adversarial refute pass run |
| [OI-013](#OI-013) | 2026-07-17 | 2026-07-17 | [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) | Second `oxford-site` git clone was a known, already-repaired legacy checkout (Gabriel, 2026-07-16) — not a live risk; leaked deploy token already purged + rotated same day |
| [OI-012](#OI-012) | 2026-07-17 | 2026-07-17 | ora-deal-command-board SKILL.md STEP 2 | Stamp `Last Activity` from deal-touching skills so the board's stall flag is authoritative — field+board+3 skills stamped, Save-skill reimport of all 3 confirmed by Gabriel, PENDING_REIMPORT.md cleared |
| [OI-011](#OI-011) | 2026-07-17 | 2026-07-17 | [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md) | bash-guard.mjs: core.hooksPath read/write + cp guard-path source/dest false positives fixed |
| [OI-010](#OI-010) | 2026-07-17 | 2026-07-17 | [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md) | bash-guard.mjs: closed git-alias/wrapper-script indirection across all 7 blocked command classes |
| [OI-007](#OI-007) | 2026-07-17 | 2026-07-17 | [project_autonomy_gate_indirection_ceiling_followup.md](project_autonomy_gate_indirection_ceiling_followup.md) | Enforce Gate 1/2a at the actual outbound action — value-indirection defeats shell-text detection |
| [OI-001](#OI-001) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Purge 2 dangling disabled LAMS scheduled-task entries |
| [OI-002](#OI-002) | 2026-07-08 | 2026-07-16 | [oxford-cc-repo-health.md](oxford-cc-repo-health.md) | Decide `ora-cam-reconciliation-annual` year-round vs. seasonal timing |
| [OI-004](#OI-004) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Add a real `Archived` property to the Tenant DB schema (blocked OI-003) |
| [OI-003](#OI-003) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Build the Notion Tenant DB workbook mirror (`EXPORT_RentRoll` → Notion) |
| [OI-005](#OI-005) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Dedup 2 stale Notion Heritage Pool Supply rows against the correct SRS row |
| [OI-006](#OI-006) | 2026-07-16 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Confirm 4 tenant turnovers + Soldier Trucking property conflict against executed leases |
| [OI-008](#OI-008) | 2026-07-17 | 2026-07-17 | [project_tenant_db_no_sync_rootcause.md](project_tenant_db_no_sync_rootcause.md) | Sweep the Tenant DB for the Escalation-Date/Lease-Expiration column-mapping bug beyond the 7 rows already checked |
| [OI-014](#OI-014) | 2026-07-17 | 2026-07-17 | [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) | Confirm no ora-pm git clone inside any OneDrive sync root (real repo at C:\Users\Owner\ora-pm) |
| [OI-015](#OI-015) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b` | Reachable/clonable ora-pm git history confirmed genuinely clean of real E. Fulton terms — no history rewrite needed; residual (a dangling blob still served via GitHub's Data API) spun off as OI-022 |
| [OI-017](#OI-017) | 2026-07-18 | 2026-07-26 | ora-appsec-sweep first run (2026-07-18) | ora-pm + oxford-command-center toolchain CVEs — both repos' vitest/vite CRITICAL+HIGH chain cleared (ora-pm 0 vulns; occ 30→9, 0 critical); wrangler/sharp and react-router (v8.3.0) also resolved on ora-pm. Residual npm-audit-fix pass on occ and the unrelated blank-tenant-portal defect tracked separately, not part of this item |
| [OI-016](#OI-016) | 2026-07-18 | 2026-07-19 | ora-appsec-sweep first run (2026-07-18) | ora-pm: `hono` bumped 4.12.23→4.12.31 (commit `c300867`), resolved HIGH CORS/Set-Cookie/path-traversal advisories; verified via `npm audit` |

### OI-028
**Status:** CLOSED (RESOLVED)
**Opened:** 2026-07-26
**Closed:** 2026-07-26
**Source:** `hooks/git-prepush-hook-tests-gate.py` GIT_TRACE root-cause + fix, commit `0d4b974`; repo-housekeeping follow-up session, 2026-07-26 (see [event_log.md](event_log.md) 2026-07-26)
**Description:** A live `git push` from the `~/.claude` checkout appeared to stall for well over two minutes with no visible progress, raising suspicion of a network or Git remote problem.
**Resolution:** `GIT_TRACE`/`GIT_TRACE_PERFORMANCE` on a live `git push` isolated the delay precisely: the pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran ~54 tracked test files SEQUENTIALLY, 137s wall-clock measured directly — the actual network push (`send-pack`) that ran immediately after took 0.54s. It was never the network call. Fix: `run_suite()` now dispatches to a bounded `ThreadPoolExecutor` (8 workers) instead of a for-loop, reassembling results into original discovery order regardless of completion order.
**Evidence:** TDD in an isolated worktree (`worktrees/prepush-gate-parallelize`); real-world result 137s → 38–42s across 4 measured runs, 0 failures. Mandatory adversarial REFUTE pass (hooks/** override/auth logic) via the `security-auditor` subagent found one real defect on the first draft — a new perf test asserted a wall-clock threshold while itself running as one of the ~54 concurrently-gated files on a real push, reintroducing a load-sensitive flake-block risk with no retry path — fixed per the reviewer's own suggestion (structural sweep-line max-overlap proof instead of a timing threshold); re-review returned NOT REFUTED. Landed via `git merge --ff-only` into the live `~/.claude` checkout only after Gabriel's explicit in-turn "Good to merge" confirmation (config-write-guard requires it for any hooks/** write). Tracker closed same day, commit `b0b9ffd`.
**Note:** reproduced once more later 2026-07-26 during a 21-item consolidated commit/push (pre-push gate passed clean in seconds; the push itself then took noticeably longer before `git fetch origin main` confirmed `origin/main` landed) — same standing workaround (verify landing via fetch, not client exit code) applied; not a regression of the fix itself.
**Auto-check:** none.

### OI-023
**Status:** CLOSED
**Opened:** 2026-07-21
**Closed:** 2026-07-22
**Source:** oxford-command-center `server/workbook/parse.ts:457/585/628` + `src/analytics/conditions.ts:199` (raised during the ora-pm-ledger 2026-07-21 rent-roll divergence audit)
**Description:** The Command Center portfolio snapshot wrote `meta.asOf = WORKBOOK_AS_OF` (a June-pinned config constant), so `portfolio.json` / TopBar / module "As of" badges reported `2026-06-01` while the rent-roll data was July-current (137 tenants; the workbook's own header read "As of July 17, 2026"). Latent second concern: the `?? s.meta.asOf` day-count fallback (`conditions.ts:199`, `critical-dates.ts:47`, `renewals.ts:34`, `tenants.ts:118`) would compute lease/balloon/insurance "days out" from the frozen June date (~50d skew) for any caller omitting an explicit run-date reference.
**Resolution:** PR [#231](https://github.com/ZeOoba/oxford-command-center/pull/231) (branch `fix/oi-023-snapshot-asof`, commit `d199287`, isolated worktree). `parse.ts` gained `datelineToIso()` + `sheetDataAsOf()`: `meta.asOf`/`cash.asOf`/`assumptions.asOf` now read each sheet's own cached "As of …" header — per-sheet because the Cash Balances dateline is data-derived (MAX of Cash Data dates) and legitimately differs from the rent roll's TODAY()-cached stamp. Missing dateline → fallback with a `DataQualityFlag` warn (loud, not silent). `parseTasks` monthCol deliberately stays on `WORKBOOK_AS_OF` (test-locked). Day-count audit: every production alerting path already passed an explicit run date; the one omitting caller (`brain.setTenantNote` → `tenantScorecards`, ids-only) now passes `referenceDate()` — and the fallback value itself can no longer freeze, since it tracks the workbook's dateline.
**Evidence:** TDD red→green (`tests/unit/workbook-asof.test.ts`, 9 cases: per-sheet datelines, cached-formula unwrap, loud fallback flags, monthCol isolation; red run showed `expected '2026-07-17', received '2026-06-01'`). Full `npm run gate` exit 0 in the worktree: governance + typecheck 0 (3 tsconfigs) + lint 0 + 241 files / 2,964 tests + reconcile (live workbook via the new parser) + warehouse:verify. Live parse of the real Master Workbook: `meta.asOf 2026-07-17`, `cash.asOf 2026-07-10`, 137 leases, zero degradation flags. Adversarial REFUTE run (mandated, financial-decision-adjacent): caught one real break (brain.test.ts partial config mock missing `referenceDate`) — fixed, 13/13; TODAY()-stamp timing edges documented as accepted in-code/PR. `Refute-Reviewed:` commit trailer present (repo `check:refute` gate). PR merge is Gabriel's; item scope (label decouple + fallback audit) is complete and mechanically verified.

### OI-018
**Status:** CLOSED (RESOLVED)
**Opened:** 2026-07-18
**Closed:** 2026-07-19
**Source:** ora-appsec-sweep — supervised re-run (2026-07-18); Notion Ops Hub row `3a26ecd8-9e59-81be-8060-c83b9405e987`. Re-run re-pinned oxford-command-center at `01e288d` (prior first-run row `3a26ecd8-9e59-81e4-85d4-d08d0d5d920b` pinned the older `306a67f`); net-new finding not in OI-015/016/017.
**Description:** ora-pm (pinned SHA `f47bbe0`) — HIGH broken object-level authorization (IDOR) on the
tenant-facing Stripe router `server/routes/stripe.ts`. All three routes (`POST /api/stripe/customer`,
`/setup-intent`, `/payment-intent`) apply `tenantAuthMiddleware` (authenticates the JWT, sets
`tenantUserId`) but then read `tenant_id` (and `lease_id` on `/payment-intent`) from the request BODY and
use them directly, with NO check that the resource belongs to the authenticated session. The DB client
(`server/db/client.ts` `getDb`) uses `SUPABASE_SERVICE_ROLE_KEY`, so RLS is bypassed — there is no
row-level safety net. `/api/stripe` is also in `index.ts` `ADMIN_EXEMPT`, so no admin gate either.
Impact (attacker = any authenticated portfolio tenant): `/customer` discloses/creates another tenant's
`stripe_customer_id`; `/setup-intent` returns a SetupIntent `client_secret` bound to a victim's Stripe
customer; `/payment-intent` inserts a `payments` row against an arbitrary `lease_id`, corrupting AR
ledger balances. Contrast the correct pattern already used elsewhere: `server/routes/portal.ts` derives
the tenant via `.eq('auth_user_id', userId)`, and the `/portal/autopay` handler has an explicit
"IDOR guard" (`lease.tenant_id !== tenant.id → 404`). The Stripe router is the inconsistent gap.
NOTE: this directly CONTRADICTS the prior first-run's (d)-CLEAN / "no IDOR" claim (Notion row
`3a26ecd8...`) — the prior run appears to have checked only the portal routes and missed the separate
Stripe router.
**Evidence:** RESOLVED 2026-07-19, ora-pm commit `c705531fa7f2e861199477ceb6db21ba6b57fc66` (`main`,
local — not pushed). All 3 endpoints now resolve the authenticated tenant via
`.eq('auth_user_id', tenantUserId)` and 403 a mismatched body `tenant_id` before any Stripe call/DB
write; `/payment-intent` additionally verifies `leases.tenant_id === tenant.id` (404) — exactly the
portal.ts / `/portal/autopay` convention. Router-wide `use('/*', tenantAuthMiddleware)` added. TDD
red-first (5 rejection tests returned 200 pre-fix); 7 new tests; full suite 185/185 (was 178/178),
tsc clean. Independent context-blind adversarial REFUTE pass found no runtime bypass; its 3 hardening
findings (arg-blind test mock, missing route-wiring test, body-id reuse in writes) all landed in the
same commit — regression-detection proven by temporarily reverting one guard (4 tests red).
**Auto-check:** none.

### OI-013
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) — surfaced incidentally during the OI-014 ora-pm sweep
**Description:** An exhaustive `.git`-marker sweep of all three OneDrive roots (run for OI-014,
scoped to `ora-pm`) also turned up a live git clone at `Claude_Workspace/01_Workspace/oxford-site/.git`
inside the business OneDrive root. CLAUDE.md documents `C:\Users\Owner\oxford-site` as *the*
no-git deploy copy (`website-canonical` is the canonical repo). This second, git-tracked
`oxford-site` sitting inside OneDrive sync scope is a different location than what's documented —
is it a stray clone, an intentional second deploy copy, or leftover from an old workflow?
**Evidence:** Not a mystery — a known, already-resolved legacy artifact. `Claude_Workspace/
01_Workspace/oxford-site` is a pre-`website-canonical` standalone working directory whose `.git`
corrupted via a OneDrive sync issue (isolated to 2026-07-05, per directory mtimes). Gabriel
personally repaired and closed this out **2026-07-16 — a full day before this item was opened**;
the tracker was simply behind, not flagging a live risk. That day's work (2 commits, `git log`
confirms `8c97652` then `9095cb7`, both authored `Gabriel Goldberg <ggoldberg@oxfordra.net>`):
1. Re-initialized git from the intact working tree after confirming it byte-identical against an
   external non-OneDrive backup (`C:\Users\Owner\_archive-non-onedrive\
   oxford-site-workspace-backup-20260716`). Explicitly confirmed this checkout diverges materially
   from `website-canonical` (275 vs 648 files) — not a live parallel source, deliberately left
   unreconciled pending direction.
2. Found a leaked, live Netlify MCP deploy token hardcoded in `run-deploy.bat` during the repair.
   Fully remediated same day per `event_log.md`'s own dedicated "CLOSED" entry: purged from git
   history via a clean re-clone (twice — a forensic-archive copy initially survived the first
   pass), redacted on disk, and the actual token **rotated at Netlify** (revoked under Authorized
   Applications, MCP connector reconnected and verified live).
3. Archived all stale/superseded content into a gitignored `archive/` folder, leaving this
   checkout "a thin config shell... `website-canonical` remains the actively maintained source for
   oxfordra.net" (his own commit message).

Independently re-verified this session, not just taken on the commit messages' word: `git remote
-v` on the live checkout returns empty (no push target, can't accidentally deploy from here);
`.netlify/` directory is empty (no deploy wiring); the redacted token is not recoverable from the
live git object store (`git fsck --unreachable --no-reflogs` empty, no reflog, the commit hash the
redaction message cites doesn't resolve), the corrupted store (`.git-corrupted-20260716`, per its
own recovery-commit analysis its surviving pack held zero commit objects), or the archived
filesystem copy of `run-deploy.bat` (shows `REDACTED`, confirmed via direct grep). Nothing
outstanding — investigated and closed same session it was surfaced.
**Auto-check:** none.

### OI-012
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** ora-deal-command-board SKILL.md STEP 2 (raised during the 2026-07-17 board run)
**Description:** `ora-deal-command-board`'s STALLED flag keyed on Notion's system last-edited
timestamp (`Last Updated`), which both (a) conflated any edit with real deal progress and (b) froze
when deal work happened off-Notion — on 2026-07-17 the 754 Old SR 74 row false-flagged STALLED (36d)
while its PSA was in active negotiation, purely because `Last Updated` hadn't moved since 6/11.
**Already landed this session (NOT the open part):** added a `Last Activity` DATE property to the
Acquisition Pipeline Tracker (`bcfe4a03-...`, via `notion-update-data-source`); backfilled all 7 open
rows; rewrote board STEP 1/STEP 2 to read `Last Activity` with a `Last Updated` → `createdTime`
fallback chain and to tag any row still running on the fallback. **The open part:** the field is only
authoritative once the deal-touching skills stamp `Last Activity = today` when they act on a tracked
row. Update these 5 (Cowork skills — supervised single-writer pass, verify `git log`/`git status` on
`ora-skills` before editing each SKILL.md): `deal-execution` (PSA turns), `loi-generation` (LOI
sent/countered), `acquisition-underwriting` (screen/underwrite), `deal-comparison`, `owner-outreach`.
Same one-line stamp pattern each. Do NOT add the stamp to `ora-deal-command-board` itself — it is
read-only by charter; a board that stamped activity would reset its own stall clock merely by
surfacing a deal. Acceptance: a deal under active off-Notion work does not flag STALLED; a genuinely
dormant deal still flags at 30d; the board never writes `Last Activity`.
**Progress 2026-07-17 (skills pass executed):** Ground truth on which skills actually WRITE the
tracker corrected the original 5-skill list. Edited + committed the source in `ora-skills`
(authoritative repo, single-writer verified clean before start), branch `board-last-activity-stamp`,
commit `643dd9f`, additive only:
- **loi-generation** — stamps `Last Activity=today` when logging "LOI Out".
- **deal-execution** — new standing "NOTION PIPELINE STAMPING" rule covering PSA generation (WF1),
  inbound-PSA/redline review (WF2A), and closing. This was the actual 754 gap: deal-execution
  previously touched the tracker ONLY at closing, so weeks of live PSA turns never bumped the row.
- **acquisition-underwriting** — stamps when it updates an existing tracker row in-place (it
  primarily logs to the Deal Sourcing Log, not the pipeline tracker, so this is its only tracker write).
- **deal-comparison — NOT edited (scope correction):** it is read-only, never writes the tracker;
  inventing a write just to stamp would be scope creep. Dropped from the stamp list.
**Residuals (why still OPEN):** (1) **owner-outreach — RESOLVED 2026-07-17 (source recovered; needs
no stamp).** It had been orphaned (loadable as `anthropic-skills:owner-outreach` but no source in the
repo/workspace/`~/.claude`/git history). Recovered byte-exact from the live runtime store — invoking
the skill surfaced its base dir `AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/…/skills/owner-outreach`
(the runtime IS on disk, just under a nested session path an earlier `find` missed) — and committed
to `ora-skills` (`owner-outreach/SKILL.md`, v1.0 2026-07-11, desc 1012/1024, commit `5dda2cd`).
Reading the recovered source settled the stamping question: **owner-outreach writes the Notion Owner
Outreach Queue DB (off-market first-touch), NOT the Acquisition Pipeline Tracker — so the
`Last Activity` stamp does not apply to it, same as deal-comparison.** Repo now matches the runtime,
so it was cleared from `_staging/PENDING_REIMPORT.md` (no reimport needed). **Stamping scope is thus
fully resolved:** only loi-generation / deal-execution / acquisition-underwriting write the tracker
and all three are stamped; deal-comparison and owner-outreach correctly excluded. (2) **Deployment not
complete:** the post-commit hook staged all 3 skills in `_staging/PENDING_REIMPORT.md`; going live in
the Cowork runtime needs `package_skills.py` → present `.skill` → **manual Save-skill click** (GUI,
not headless), then `pending_reimport.py clear <skill>`. Until then the Monday
`ora-skill-store-drift-check` will flag repo↔store drift. (3) ~~Branch `board-last-activity-stamp` is
committed locally, not merged to main or pushed — awaiting Gabriel's review/merge.~~ **Stale —
corrected 2026-07-17 (Code-surface verification):** `git branch -vv` on `ora-skills` shows
`board-last-activity-stamp` at `5dda2cd`, identical to `main`; `git log main..board-last-activity-stamp`
returns zero commits (fully merged); `git log origin/main..main` also returns zero commits and
`git rev-parse origin/main main` return the same SHA (`main` fully pushed). The branch is not a
residual — this note was simply stale by the time of closure. This correction itself committed to
`~/.claude` `main` (commit `8c58559`) and pushed to `origin/main` (`ora-claude-config`, verified via
`git status -sb` showing no ahead/behind and `git ls-remote origin main` matching local HEAD) —
tracker text and remote now consistent, nothing further outstanding on OI-012.
**Progress 2026-07-17 (reimport attempt, blocked):** Re-verified `_staging/PENDING_REIMPORT.md` still
listed all 3 (`acquisition-underwriting`, `deal-execution`, `loi-generation`, pending since
2026-07-17T18:17Z, commit `643dd9f`). Packaged `acquisition-underwriting.skill` successfully via
`package_skills.py` (fresh file confirmed in `_staging/out/`). Then found this machine
(LAPTOP-CSHSCBE6) has **no Claude Desktop app installed** — absent from the computer-use
`request_access` allowlist and from `AppData\Local\Programs`, `AppData\Local\AnthropicClaude`,
`Program Files`, `Program Files (x86)`, and Start Menu shortcuts. Gabriel confirmed (2026-07-17, via
AskUserQuestion): **stop here** — do not guess an alternate app name or assume the Desktop app is on
another device. `deal-execution` and `loi-generation` were NOT packaged (no point building `.skill`
files with the GUI step unreachable). All 3 remain pending; none cleared. **Open part now includes:**
locate which device/session actually hosts the Cowork Claude Desktop app's Save-skill flow before
retrying this residual.
**Closure 2026-07-17 (Cowork session, Desktop app located on the Cowork-hosting machine):**
Re-verified `_staging/PENDING_REIMPORT.md` still listed all 3 skills unchanged (pending since
2026-07-17T18:17Z, commit `643dd9f`) before starting — confirmed no other session had cleared any of
them. Packaged all 3 via `tools/package_skills.py C:\Users\Owner\ora-skills\_staging\out
<skill-name>`, each verified fresh via `get_file_info` immediately after build:
`acquisition-underwriting.skill` (50,017 bytes, 2 entries: SKILL.md + target-markets.json, built
18:42Z), `deal-execution.skill` (42-point QC gate confirmed by the packager, 1 entry: SKILL.md, built
18:45Z), `loi-generation.skill` (2,782,431 bytes, 5 entries incl. the 16-point QC gate and the
condensed LOI template, built 18:46Z). The GUI Save-skill click itself could not be performed by the
agent — computer-use's `request_access` refused control of Claude's own window outright (a hard,
non-overridable guard against an agent operating its own interface/permissions), confirming this
step is manual regardless of session type. Handed off the 3 `.skill` files and import instructions to
Gabriel; Gabriel confirmed all 3 imported ("all done"). On that confirmation, ran
`python tools/pending_reimport.py clear <skill>` for all 3 in sequence — each returned
`pending_reimport: cleared <skill>` — then re-read `_staging/PENDING_REIMPORT.md`: the file no longer
exists (the clear script deletes it once the pending list empties), the definitive zero-pending
state. Stamping scope (loi-generation/deal-execution/acquisition-underwriting) was already committed
at `643dd9f`; only the runtime-cache resync remained, and that is now closed. **Residual outside this
item's scope, not blocking closure — since resolved:** branch `board-last-activity-stamp`'s
merge-to-main-and-push status was flagged as not re-verified this session; separately confirmed later
the same session (`ora-skills` `main` HEAD `5dda2cd` == `origin/main` `5dda2cd` via `git fetch` +
`git rev-parse`) — already merged to main and already pushed, nothing outstanding.
**Auto-check:** none (not a fleet-registry item; closure evidence is the cleared
`pending_reimport.py` runs plus the deleted `PENDING_REIMPORT.md`, both reproducible by re-running
`python tools/pending_reimport.py clear <skill>` — a no-op / "already cleared" result confirms state).

### OI-011
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md)
**Description:** Found during OI-010's adversarial review, deliberately NOT fixed there to keep that
change scoped to the indirection fix. Both were pre-existing (present before OI-010 touched the
file), false-positive-only (annoyance, not a security gap at the time): (1) `git config --get
core.hooksPath` (a pure read) was denied identically to an actual write — check (d) never
distinguished read from set. (2) `cp .claude/settings.json /tmp/backup.json` (reading FROM the
guard file to back it up) was denied identically to overwriting it — the mv/cp check matched the
guard path anywhere in the segment, not just as the destination, despite its own comment saying
"as an argument (destination)".
**Evidence:** Fixed on `oxford-command-center` `main`, commit `8006a15`. Check (d) now
distinguishes mutation from read: any trailing token after `core.hooksPath`'s position counts as a
value being set (regardless of leading dash — no `--` separator required by real git) UNLESS the
command carries an explicit `--get`/`--get-all`/`--get-regexp`/`--get-urlmatch` flag, where a
trailing token is git's own value-pattern filter, not a value. `--unset`/`--add`/`--replace-all`
and the `-c core.hooksPath=` inline form still always deny. Check (g)'s mv/cp guard now treats `mv`
and `cp` differently: `mv` still denies the guard path in either argument position (source-position
mv removes/neutralizes the file, same severity as `rm`), while `cp` denies only the destination
argument via a new `cpGuardWrite()` helper covering the plain 2-arg form and all 3
`-t`/`--target-directory` shapes (short flag, `=`-attached, space-separated) plus unambiguous
long-option abbreviations. **3 rounds of adversarial review** (mandatory per CLAUDE.md for
`hooks/**` security-gate code) found and fixed 3 real bypasses before landing, each confirmed
against the live hook and then regression-tested: a dash-prefixed `core.hooksPath` value (`git
config core.hooksPath -evilhooks`) defeating the initial read/write classifier; `cp
--target-dir=.claude/hooks/ evil.mjs` (GNU abbreviation) missed by the initial destination-only
detection; `cp --target-directory .claude/hooks/ evil.mjs` (space-separated, real GNU cp behavior)
missed by the round-1 fix. Round 3 found nothing further. 68 tests in `bash-guard.test.ts` (was 64),
full project suite 231 files/2792 tests green, typecheck 0, lint 0. Landed via isolated worktree,
fast-forward merge (matching the OI-010 convention), verified zero collateral impact on the main
checkout.
**Auto-check:** none (not a fleet-registry item; closure evidence is the landed commit above,
externally verifiable via `git log`).

### OI-010
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [project_bash_guard_indirection_gap.md](project_bash_guard_indirection_gap.md)
**Description:** `oxford-command-center/.claude/hooks/bash-guard.mjs` is a stateless, per-invocation
text scanner with no cross-invocation memory. A two-step disk-persisted indirection — a git alias or
a wrapper script written in step 1, invoked by name in step 2 — defeated all 7 blocked command
classes, whether the two steps were one `&&`-joined command or genuinely separate Bash tool calls.
**Evidence:** Fixed on `oxford-command-center` `main`, commit `60c45ed`. Resolves both indirection
layers into one expanded text every existing check scans: git aliases via `git config --get`
(skipping known builtins), inline `git -c alias.X=value` one-shot overrides, and script content read
through a widened set of invocation forms (sh/bash/zsh/dash/ksh, source/dot, stdin redirection,
direct execution, case-insensitive, quoted paths with spaces) with best-effort positional-parameter
and simple-variable substitution inside that content. Three rounds of independent adversarial review
(3 parallel agents, each personally re-verified) found and fixed real bugs before landing: git global
options (`-c`/`-C`/`--git-dir=`/`-p`/`--no-pager`) breaking alias-candidate detection entirely; an
exponential subprocess-spawn blowup from a plausible chained-alias config (4-8s+ stalls on every
Bash call, fixed via a 16-lookup shared budget); a backtracking-prone lazy regex costing ~10s on a
crafted unterminated-quote payload (fixed via length-bounded `{0,4096}?` matches, applied
consistently including to the pre-existing `sh -c`/`$()`/backtick extraction whose exposure this fix
increased); and a quote-handling bug where substituting a variable inside double quotes left stale
quote characters, hiding the result from the downstream commit-message quote-blanking logic. Proved
several bypasses end-to-end (not just hook-logic-level) before fixing: a git alias genuinely staged
an untracked file via `add -A`; a direct-executable and a variable-built-verb wrapper genuinely
deleted a `data/warehouse` test directory. 59 new/updated tests (regression + adversarial-finding
coverage + timing guards locking in both DoS fixes); full project suite 231 files/2783 tests green,
typecheck 0, lint 0. Landed via isolated worktree, fast-forward merge, verified zero collateral
impact on the main checkout. Accepted, documented limits (same architectural ceiling as OI-007):
arbitrary shell constructs beyond simple literal variable assignment — command substitution,
arithmetic, exported variables, control flow, >3-level nested wrappers, >64KB scripts — are not
resolved, since closing those for real needs the same shift OI-007 used (verify the actual outbound
action/repo state), not another regex. 2 unrelated pre-existing false positives found during review,
deliberately not fixed here to keep scope tight: tracked as [OI-011](#OI-011).
**Auto-check:** none (not a fleet-registry item; closure evidence is the landed commit above,
externally verifiable via `git log`).

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

### OI-014
**Status:** CLOSED
**Opened:** 2026-07-17
**Closed:** 2026-07-17
**Source:** [reference_onedrive_business_scope.md](reference_onedrive_business_scope.md) — migration Phase B4 unsynced-export check
**Description:** Confirm no `ora-pm` git clone lives inside OneDrive sync scope (business root,
its `(1)`-suffixed twin, and the plain personal OneDrive root) — superseding an earlier depth-4-only
Glob negative, which per [[feedback_verify_negative_glob_results]] isn't sufficient proof on its own.
**Evidence:** Exhaustive `.git`-marker search, no depth cap, hidden entries included, across all
three OneDrive roots, via two independently-implemented tools (Bash `find -name .git`, PowerShell
`Get-ChildItem -Recurse -Force -Filter .git`) — both agreed exactly: zero `ora-pm` hits anywhere.
Two unrelated `.git` markers turned up (an already-archived third ora-skills clone at
`Claude_Workspace/01_Workspace/_archive/2026-07-09_third-ora-skills-clone/skills/.git`, expected
and already resolved; and a **live** `oxford-site` clone at
`Claude_Workspace/01_Workspace/oxford-site/.git`, distinct from the documented no-git deploy copy
at `C:\Users\Owner\oxford-site` — flagged separately, out of this item's ora-pm scope, tracked as
[OI-013](#OI-013)). `Claude_Workspace/00_Governance/Scheduled/ora-pm-ledger`
confirmed NOT a repo (task folder only, no `.git`). Real `ora-pm` repo confirmed live at
`C:\Users\Owner\ora-pm`.
**Auto-check:** none (not a fleet-registry item).

### OI-031
**Status:** OPEN
**Opened:** 2026-07-27
**Source:** `orphaned-task-forensics` trace of the `ora-master-workbook-ingest` 2026-07-20 silent
gap, [event_log.md](event_log.md#2026-07-27)
**Description:** `fleet-status.py`'s missed-cycle detectors are structurally blind to an
already-established recurring task silently skipping a single scheduled fire — confirmed by
reading the script directly (`C:\Users\Owner\.claude\maintenance\fleet-status.py`). "Overdue"
(`never_ran_overdue`) only fires for a RECURRING task that has NEVER fired even once (a
cadence-buffer heuristic meant for brand-new tasks). "Missed/stuck" (`expired_needs_attention`)
applies only to expired ONE-TIME tasks. Throttle-skip tracking catches a task that fired and got
rate-limited, not one that never attempted to fire at all. None of the three checks can detect
"this weekly/monthly task has run before, is still enabled, but silently missed this one cycle" —
exactly the gap that let `ora-master-workbook-ingest`'s 2026-07-20 Monday fire go unnoticed for a
full week despite the fleet's own Monday-afternoon schematic-refresh snapshot reporting "0
overdue, 0 missed/stuck" that same day.
**Candidate fix (not built):** extend `fleet-status.py` with a per-task expected-fire-window
check for tasks that HAVE fired before, comparing `lastRunAt` against the most recent
cron-predicate fire time (mirroring `automation-health-monitor`'s Step 0.5 `expectedFireTime`
walk-backward logic, already implemented for the LAMS fleet) — flagging MISSED/OUT-OF-WINDOW
the same way that step does, rather than only checking never-fired-at-all or expired-one-time
states.
**Auto-check:** none (a tooling-logic gap, not a fleet-registry state comparable to the closed
Auto-check vocabulary above).

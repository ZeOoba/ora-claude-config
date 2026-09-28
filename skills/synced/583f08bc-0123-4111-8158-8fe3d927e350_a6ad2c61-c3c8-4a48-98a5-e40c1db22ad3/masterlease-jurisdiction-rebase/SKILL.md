---
name: masterlease-jurisdiction-rebase
description: "Rebase Oxford Realty Advisors jurisdiction-conformed Master Lease property templates onto a new master revision in one command, and generate state-conformed (MD/MO) property templates from the OH-anchored master. Use whenever the user mentions: new master lease version, rebase the lease templates, regenerate the MD/MO templates, jurisdiction overlay, conform the lease to a state, state-conformed lease template, update property lease forms, lease template for Easton / Salisbury / Northwood / Raytown / Columbia, or uploads a new ORA_MasterLease_ShallowBayIndustrial_v*.docx. Also use when adding a NEW property or state overlay, or converting a property to NNN. Edits the master DOCX in place with asserted-count substitutions. Companion to lease-form-qc (which QCs drafted leases); this skill produces the templates leases are drafted FROM. v1.7"
---

# Master Lease Jurisdiction Rebase — Oxford Realty Advisors

One-command regeneration of state-conformed property lease templates whenever the
controlled master (`ORA_MasterLease_ShallowBayIndustrial_v*.docx`) revs. Built from the
2026-08-03 conformance session, where it produced the MD-EAS / MD-SBY / MO-RAY v2.2
variants and then rebased them onto v2.4 with zero manual edits.

## Why this exists

The 2026-08-03 propagation audit proved that hand-copying leases spreads defects
(34–36/39 failures on every executed lease; ZIP cross-contamination between properties).
The same failure mode applies to templates: hand-porting jurisdictional edits onto each
new master revision silently drops or duplicates clauses. This engine applies every
jurisdictional change as an **asserted-count substitution** — if an anchor string moved
or vanished in the new master, the run fails loudly and names the anchor, instead of
producing a quietly wrong template.

## Canonical master — the drift rule

**Never build from a cached or knowledge-store copy of the master.** Version drift
happened twice on 2026-08-03 (a v2.1 cache was used while v2.4 was canonical).

- Canonical location: **`Business/Leases All properties/` (egoldberg's OneDrive/SharePoint),
  pinned 2026-08-03 by Gabriel.** Always pull the highest version number present in that
  folder before a rebase run — never rely on a cached copy from this project's Knowledge
  files, a prior session, or any other knowledge-store source (see the
  v2.1-cache-while-v2.4-was-canonical incident above). Superseded revisions live in that
  folder's `/archive/` subfolders and are excluded from the highest-version scan.
  If the connected SharePoint search tool doesn't index that path on a given surface
  (observed 2026-08-04 — the connector resolved the folder to 9050 Red Branch Road's own
  lease archive, not the portfolio master), fall back to this skill's bundled
  `scripts/fixtures/ORA_MasterLease_ShallowBayIndustrial_v2.6_TEMPLATE.docx`, which the
  test suite validates against canonical v2.6 — but say so explicitly in the output and
  flag that production use should be confirmed against the live copy first.
- Freshness check before any run: compare the version string in the supplied master's
  filename (`v2.5` etc.) against the newest version mentioned anywhere in the session
  and in this skill's changelog. If the supplied master is not the highest version
  known, stop and ask which is canonical.
- The six ratified standing lease positions (2026-08-03, carried in `lease-form-qc`)
  are baked into the master. This skill must never alter them: modified gross /
  calendar base year · co-tenancy not guaranty · 1.0× deposit · 10% late fee + 18%
  default interest (savings clause is allowed and included; silent reduction is not) ·
  flat Hazardous Materials ban · no extension option. **Exception:** the expense-recovery
  structure (modified gross vs. NNN) may be overridden per property via the
  `lease_structure` config field — see below — on Gabriel's explicit, sourced direction
  only. The other five positions have no override mechanism.

## How to run

```bash
python3 scripts/rebase.py --master <path/to/ORA_MasterLease_..._vX.Y_TEMPLATE.docx> \
    --property MD-EAS --out <session-scratch-dir>
# or all configured properties:
python3 scripts/rebase.py --master <master.docx> --all --out <session-scratch-dir>
```

`--out` is ALWAYS passed explicitly, pointed at session scratch — never omitted, never
the canonical OneDrive folder (see Workspace & output hygiene).

Outputs `ORA_MasterLease_ShallowBay_<property>_vX.Y_TEMPLATE.docx` per property —
the master edited in place (python-docx cross-run splice), so native formatting,
numbering, styles, headers and exhibits survive untouched.

The script:
1. Loads `config/properties.json` (property facts) and `config/state_overlays.json`
   (state law tables).
2. Applies every substitution with an expected match count; any mismatch aborts with
   the anchor named.
3. If the property's config sets `"lease_structure": "NNN"`, rewrites the modified-gross
   OPERATING COSTS AND TAXES article into a full NNN structure (Operating Costs + Taxes
   + Insurance, no base year) — see "NNN override" below. Otherwise the master's default
   modified-gross / calendar-base-year language is left untouched.
4. Inserts the Maximum Lawful Rate savings clause after Counterparts (cloned styling;
   skipped if already present).
5. Post-checks: zero residue of the master's anchor state, zero unfilled entity/state
   tokens, savings clause present and positioned, state statutes at expected counts;
   for NNN properties, zero residual `[BASE YEAR]` token and the OPERATING COSTS, TAXES
   AND INSURANCE heading and Insurance defined term both present.

## Workspace & output hygiene (v1.4 — the 2026-08-04 sweep rule)

Root cause of the 2026-08-04 superseded-file sweep: ~450 of 491 files removed from
`Business/Leases All properties/` were build debris (working copies, extractions,
node_modules, eval logs, .tmp/.lock files) that sessions had created inside the
canonical business folder. Binding rules for every run of this skill (and the model
for any ORA skill that builds artifacts):

1. **All working artifacts go to session scratch/outputs, never the OneDrive business
   folder.** Working copies, text extractions, diffs, page renders, npm/python scratch
   dirs, node_modules, eval logs, tmp files — none of these are ever created under
   `Business/Leases All properties/` or any other OneDrive business path. The canonical
   folder receives exactly two classes of file from a run: final
   `ORA_MasterLease_ShallowBay_*_TEMPLATE.docx` outputs and the run memo.
2. **No short-name working copies.** Never copy the master or a property template to an
   abbreviated name (`MD-EAS_v2.4.docx`, `OH_v2.4.1.docx`, …) — this is how hash-identical
   duplicates of canonical templates ended up loose at the folder root on 2026-08-03.
   Reference canonical files by full path. If a tool requires a writable local copy, make
   it in session scratch under the unmodified canonical filename and remove it at run end.
3. **`--out` is explicit, always.** Point it at session scratch, run QC there, then move
   the verified finals to the canonical folder. The script's historical default
   (`--out .`) wrote into whatever directory the session happened to be in — the source
   of the root-level debris. (Source patch pending; see changelog.)
4. **End-of-run sweep.** Before closing, list anything the run created in the canonical
   folder that is not a final template or the run memo, and move it to that folder's
   `/archive/` (never delete — ORA invariant 6). Superseded prior-version templates
   displaced by the run's outputs are moved to `/archive/` in the same sweep.

## NNN override (per property, opt-in only)

The master's default is modified gross with a calendar base year (ratified position #1).
A property runs full NNN instead only when its `config/properties.json` entry sets
`"lease_structure": "NNN"` — omit the field entirely for the default. Set it only on
Gabriel's explicit, sourced direction that the property's leasing practice is NNN; never
infer it from a single executed lease without confirming it's the property's standing
practice.

**MD-COL (9050 Red Branch Road, Columbia MD)** is the first and, as of this writing,
only NNN property (added 2026-08-04). Gabriel confirmed the building runs NNN leases
building-wide, consistent with the executed LINERX LLC / Eddie Woo Park lease (Suite
D+E) and Muirkirk Properties' own NNN form in continuous use across ~16 suites since at
least 2011. The override rewrites Section 4 (OPERATING COSTS AND TAXES → OPERATING
COSTS, TAXES AND INSURANCE) to drop the base-year stop and add an explicit `"Insurance"`
defined term — the OH-anchored master folds insurance into the generic Operating Costs
definition, but 9050's own paper always separated Taxes / Insurance / CAM as three
distinct pass-through categories, so the override matches that structure rather than
inventing a new one. No other ratified position is touched by the override: co-tenancy,
1.0× deposit, 10%/18% + savings clause, flat Hazardous Materials ban, and no extension
option all still apply on MD-COL exactly as on every other property.

Implementation: `nnn_text_rules()` + `convert_to_nnn()` in `scripts/rebase.py`, applied
between `build_rules()` and `insert_savings_clause()`. Anchors are keyed to the master's
original (modified-gross) Section 4 text and fail loudly the same way as `build_rules()`
on drift. The new Insurance definition paragraph is inserted into the blank spacer
paragraph two paragraphs after the Taxes definition, with its list numbering (`numPr`/
`pStyle`) copied from the Operating Costs paragraph so it renders in sequence as `(iii)`
rather than as an unnumbered, unindented paragraph — this was the one non-obvious defect
in the first hand-built version of this conversion (2026-08-04) and is why the automated
version copies `pPr` explicitly rather than leaving the target paragraph's default style.

## When a run fails (anchor drift)

An assertion failure means the new master changed the anchor text — that is the system
working. Diff the new master against the prior one (pandoc to text is fine), update the
anchor in `scripts/rebase.py` or the configs, note the change in the changelog below,
and re-run. Never loosen an assertion to "0 or 1" to make a run pass.

## Adding a property or state

- New property in MD/MO: add an entry to `config/properties.json` (entity from the
  executed-lease record or the ratified LLC roster — never invented; SF from the
  Portfolio Basis workbook / Master Workbook; PM block from executed-lease practice,
  tokens where unknown). `entity_state` is REQUIRED and must be sourced from the
  Articles of Organization, the ratified LLC roster, or an executed lease's recital —
  the engine fails closed without it. Formation state is frequently but not always the
  property state; assuming it silently was a defect caught in the 2026-08-03 evals.
  `lease_structure` is OPTIONAL — omit for the modified-gross default; set to `"NNN"`
  only per the NNN override rule above.
- New state (IN/WI/KS/TN are pre-listed as RESEARCH-REQUIRED): complete the state's
  entry in `config/state_overlays.json` with fresh statutory research — UETA citation,
  possession/eviction statutes, holdover statute, environmental overlay, parcel-number
  nomenclature, plus any state-specific clause (Maryland's §3-101(e) memorandum-of-lease
  proviso is the model, keyed by the `extra_no_recording` field). Do not copy another
  state's citations as scaffolding; an empty field fails closed.

## Facts provenance (do not re-derive from leases)

Entity names (29000 INFORMATION LANE, LLC · 2203 NORTHWOOD, LLC · 9620 STATE 350, LLC ·
Muirkirk Properties, LLC) were sourced from executed leases / the ORA Entity Structure DB.
Building SF (48,000 / 53,700 / 34,560 / 90,000) from the Portfolio Basis workbook / ORA
Property Register. Salisbury ZIP 21801 from an executed lease — county verification still
open. 9050 Red Branch Road's Howard County SDAT Tax Account No. is unresolved — direct
SDAT query did not return content programmatically as of 2026-08-04; left tokenized.
ZIPs, suites, parcel/tax-account numbers, per-building Northwood RSF, and the Raytown PM
block are deliberately tokenized: fill at drafting time from the county record or PM
agreement, and run `lease-form-qc` on every drafted lease before it leaves the office.

## Single-tenant variant (added v1.6)

`"variant": "single-tenant"` in a `config/properties.json` entry (currently only
**OH-ST-NNN**, paired with `"lease_structure": "NNN"`) regenerates the
OH-SingleTenant-NNN template family from the master: entire-building demise
(incl. paved/yard areas), 100% Proportionate Share, gross-up and "Tenant's
Allocation" removed, exclusive parking, tenant site-services maintenance
addendum — then the NNN conversion and savings clause. Variant entries stay
generic-tokenized (no entity/premises/PM fills; tokens fill at drafting time),
skip the state-overlay gate (the family is anchored to the master's own state),
and get their own post-check branch (token/residue/marker assertions). Delta set
recovered 2026-08-04 by paragraph diff of the v2.4.1 variant against its v2.4.1
base; engine output verified text-identical to the hand-built v2.6 canonical.
Relocation clause (h) is retained as an inert option by ratified judgment call.

## Shared tracked-change editor (added v1.5)

`scripts/ora_docx_redline.py` — the reusable asserted-count tracked-change editor
(`replace` / `insert_after` / `insert_paragraphs_after` ops from a JSON spec, real
`<w:ins>`/`<w:del>` with author+date). Use it for every master revision instead of
rebuilding the machinery ad hoc (it was reimplemented three times across the v2.3,
v2.5 and v2.6 builds before extraction). Anchors must sit inside one `<w:t>` (run
`merge_runs.py` first); always validate output with the docx skill's `validate.py
--original --author`. ANCHOR DRIFT failures follow the same never-loosen rule as
`rebase.py`.

## Changelog

- v1.7 (2026-08-24): Description trimmed to restore headroom (was 1003/1024,
  headroom 21 -- close-out work-order item 4). Dropped the dated
  anti-contamination and single-tenant-variant version-history parentheticals;
  no trigger vocabulary or rule clause removed. `description_budget.py` now
  reports headroom 174.

- v1.6 (2026-08-04): Single-tenant variant support. `single_tenant_rules()` /
  `convert_to_single_tenant()` + `variant` config field + OH-ST-NNN entry;
  `rebase_one`, `post_check`, `main()` and the parity test all branch on the
  variant; `--all` now emits five templates. First run's ST_ALLOC_DEF constant
  fired ANCHOR DRIFT against the real master (reconstructed from memory instead
  of extracted) — corrected from the document text; the never-loosen discipline
  working as designed. 6/6 tests green; engine variant output text-identical to
  the 2026-08-04 hand-built canonical.

- v1.5 (2026-08-04): Phase-3 close of the v2.5→v2.6 revision cycle. (1) Parity fixture
  swapped v2.5 → v2.6 (accepted-changes copy of the redline master); v2.6 rebase of all
  four properties ran with ZERO anchor drift — no rekey needed, v1.3 anchor set carries
  forward unchanged. (2) `--out` is now `required=True` in packaged source — closes the
  v1.4 PENDING one-liner. (3) `scripts/ora_docx_redline.py` added (see section above).
  All 6 tests green against the v2.6 fixture.

- v1.4 (2026-08-04): Workspace & output hygiene section added after the 2026-08-04
  superseded-file sweep of `Business/Leases All properties/` (491 files; ~450 were
  session build debris — `mlr2/` with node_modules, `mjr-*` eval workspaces, short-name
  template copies at the folder root). Rules: working artifacts in session scratch only;
  no short-name copies; `--out` always explicit; end-of-run debris sweep to `/archive/`.
  **PENDING source patch (ora-skills repo, Code surface):** `scripts/rebase.py`
  `--out` default `"."` → `required=True` — one line, `main()` argparse block. *(Applied
  in the v1.5 packaged source; repo-side port still pending.)* Runtime
  SKILL.md updated ahead of source per the v1.1.2 reconciliation precedent; reconcile on
  the next package-and-stage run and clear the PENDING_REIMPORT note. No anchors,
  configs, or engine behavior changed in v1.4.

- v1.3 (2026-08-04): Anchors rekeyed to master v2.5 (the external-review adjudication
  build: 18 edits + 4 ratified gate adoptions). Changes: `[LANDLORD ENTITY]` 3->4 and
  entity clause 2->3 (Basic Lease Information page adds one each); PM-block anchors
  are now the tokens `[MANAGER STREET ADDRESS]` / `[MANAGER CITY, STATE ZIP]` (master
  pre-tokenized — the old Columbus literals are gone); new BLI fill rules (premises
  line, building/parcel line built from `building_def` + `parcel_reference`); NNN mode
  neutralizes the BLI Base Year line ("Not applicable — full NNN"); `rebase_one` now
  fills the footer lease-identifier `[PREMISES ADDRESS]`; parity fixture swapped to
  v2.5 (v2.4.1 fixture retired per anchor-drift discipline); all 6 tests green; all
  four properties (MD-EAS, MD-SBY, MO-RAY, MD-COL) rebased 0-of-46 on lease-form-qc
  v2.2. The v2.5 master's venue clause is deliberately tokenless ("county in which the
  Project is located") — no venue overlay needed per state.

- v1.2 (2026-08-04): Added the per-property `lease_structure` NNN override (opt-in only,
  never inferred) and the MD-COL (9050 Red Branch Road, Columbia MD) property entry —
  first non-modified-gross property in the registry, confirmed by Gabriel against the
  executed LINERX LLC/Eddie Woo Park lease and the building's ~15-year NNN practice.
  `nnn_text_rules()` / `convert_to_nnn()` added to `scripts/rebase.py`; `post_check()`
  extended with NNN-specific residue/heading checks. Extracted the per-property pipeline
  (`build_rules` + optional `convert_to_nnn` + `insert_savings_clause`) into a single
  `rebase_one()` used by both `main()` and `test_rebase.py` — the first version of this
  change added the NNN step to `main()` only, and `ParityAgainstKnownMasterTests`
  (which called `apply()`/`insert_savings_clause()` directly, duplicating the pipeline
  rather than reusing it) caught the omission by failing its own post-check on MD-COL.
  Fixed by removing the duplication rather than patching the test in place — the same
  anti-drift principle this skill applies to leases, applied to itself. Also documents
  the SharePoint canonical-master-location fallback to the bundled fixture, observed
  2026-08-04 when the connected search tool didn't index the pinned path on the Cowork
  surface.
- v1.1.2 (2026-08-03): canonical master location resolved — Gabriel pinned
  `Business/Leases All properties/` (egoldberg's OneDrive/SharePoint); both v2.4 and
  the v2.4.1 typo-fix companion parked there same day. Closes the UNRESOLVED gap this
  section carried since v1.0. Resolved independently on both surfaces — Code-surface
  close-out, and a Cowork-surface hand-edit applied directly to the packaged `.skill`
  ahead of the Code-surface source — with divergent prose; reconciled here so the two
  surfaces stop drifting.
- v1.1.1 (2026-08-03, Code-surface close-out): dropped the `Demised Premisess` fix-up
  rule from `build_rules` — v2.4.1 (the typo-fix companion master, uploaded same
  session) already corrects the spelling upstream, so the rule's own "drop this rule
  once fixed upstream" comment now applies. Caught by the new parity test running
  against the real v2.4.1 fixture: the rule's asserted count (1) found 0 matches,
  correctly firing ANCHOR DRIFT rather than silently passing. Anchors rekeyed to
  v2.4.1. Do not re-add a 0-or-1-tolerant version of this rule — retire fix-up rules
  once the upstream master absorbs them, per this skill's own anchor-drift discipline.
- v1.1 (2026-08-03): Eval-loop fixes. (1) Article-aware entity clause — "an Indiana /
  an Ohio limited liability company" (first vowel-initial state through the engine
  produced "a Indiana"); "a Utah" special-cased by sound. (2) `entity_state` is now a
  separate, sourced, REQUIRED config field — the engine no longer assumes the LLC is
  formed in the property state, and fails closed when the field is missing. All three
  current entities' formation states sourced from executed-lease recitals. (3) Version
  parser tolerates suffixed master filenames (e.g., v2.5-DRAFT) and no longer emits a
  doubled "v" on unparseable names.
- v1.0 (2026-08-03): Engine extracted from the v2.2 build + v2.4 rebase session.
  Anchors keyed to master v2.4. MD (Talbot/Wicomico) and MO (Jackson) overlays ratified;
  IN/WI/KS/TN stubs fail closed pending research.
